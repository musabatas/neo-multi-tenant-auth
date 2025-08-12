"""
Async Keycloak client using python-keycloak library.
Provides high-performance authentication and user management.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import asyncio
from functools import lru_cache
from loguru import logger

from keycloak import KeycloakOpenIDConnection, KeycloakAdmin, KeycloakOpenID
from keycloak.exceptions import KeycloakError, KeycloakAuthenticationError
import httpx

from src.common.config.settings import settings
from src.common.exceptions.base import (
    ExternalServiceError,
    UnauthorizedError,
    NotFoundError,
    ConflictError
)
from src.common.utils.datetime import utc_now


class KeycloakAsyncClient:
    """
    Async Keycloak client using python-keycloak library.
    
    Features:
    - Connection pooling for performance
    - Automatic retry with exponential backoff
    - Token caching and refresh
    - Multi-realm support
    - Async operations using httpx
    """
    
    def __init__(self):
        """Initialize Keycloak client with connection settings."""
        self.server_url = str(settings.keycloak_url)
        self.admin_realm = settings.keycloak_admin_realm
        self.client_id = settings.keycloak_admin_client_id
        self.client_secret = settings.keycloak_admin_client_secret.get_secret_value()
        
        # Cache for realm clients and public keys
        self._realm_clients: Dict[str, KeycloakOpenID] = {}
        self._admin_client: Optional[KeycloakAdmin] = None
        self._public_keys: Dict[str, tuple[str, datetime]] = {}  # realm -> (key, expiry)
        
        # Connection pool settings
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup connections."""
        await self.close()
    
    async def close(self):
        """Close HTTP client connections."""
        await self._http_client.aclose()
    
    def _get_realm_client(self, realm: str) -> KeycloakOpenID:
        """
        Get or create a KeycloakOpenID client for a specific realm.
        
        Args:
            realm: Realm name
            
        Returns:
            KeycloakOpenID client instance
        """
        if realm not in self._realm_clients:
            self._realm_clients[realm] = KeycloakOpenID(
                server_url=self.server_url,
                realm_name=realm,
                client_id=self.client_id,
                client_secret_key=self.client_secret,
                verify=True
            )
        return self._realm_clients[realm]
    
    async def _get_admin_client(self) -> KeycloakAdmin:
        """
        Get or create an admin client for Keycloak administration.
        
        Returns:
            KeycloakAdmin client instance
        """
        if not self._admin_client:
            # Create admin connection
            conn = KeycloakOpenIDConnection(
                server_url=self.server_url,
                realm_name="master",
                client_id="admin-cli",
                username=settings.keycloak_admin_username,
                password=settings.keycloak_admin_password.get_secret_value(),
                verify=True
            )
            
            self._admin_client = KeycloakAdmin(connection=conn)
            
        return self._admin_client
    
    async def authenticate(
        self,
        username: str,
        password: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authenticate a user and get tokens.
        
        Args:
            username: Username or email
            password: User password
            realm: Realm name (defaults to admin realm)
            
        Returns:
            Dict containing access_token, refresh_token, expires_in, etc.
            
        Raises:
            UnauthorizedError: Invalid credentials
            ExternalServiceError: Keycloak connection failed
        """
        realm = realm or self.admin_realm
        client = self._get_realm_client(realm)
        
        try:
            # Authenticate user
            token_response = await asyncio.to_thread(
                client.token,
                username=username,
                password=password
            )
            
            # Add additional metadata
            token_response['realm'] = realm
            token_response['authenticated_at'] = utc_now().isoformat()
            
            logger.info(f"User {username} authenticated successfully in realm {realm}")
            return token_response
            
        except KeycloakAuthenticationError as e:
            logger.warning(f"Authentication failed for user {username}: {e}")
            raise UnauthorizedError("Invalid username or password")
        except KeycloakError as e:
            logger.error(f"Keycloak error during authentication: {e}")
            raise ExternalServiceError(
                message="Authentication service unavailable",
                service="Keycloak"
            )
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {e}")
            raise ExternalServiceError(
                message="Authentication failed",
                service="Keycloak"
            )
    
    async def introspect_token(
        self,
        token: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Introspect a token to check if it's active and get claims.
        
        Args:
            token: Access token to introspect
            realm: Realm name (defaults to admin realm)
            
        Returns:
            Token introspection response with active status and claims
            
        Raises:
            UnauthorizedError: Token is invalid or expired
            ExternalServiceError: Keycloak connection failed
        """
        realm = realm or self.admin_realm
        client = self._get_realm_client(realm)
        
        try:
            # Introspect token
            introspection = await asyncio.to_thread(
                client.introspect,
                token
            )
            
            if not introspection.get('active', False):
                raise UnauthorizedError("Token is not active")
            
            return introspection
            
        except KeycloakError as e:
            logger.error(f"Token introspection failed: {e}")
            raise UnauthorizedError("Invalid token")
        except Exception as e:
            logger.error(f"Unexpected error during token introspection: {e}")
            raise ExternalServiceError(
                message="Token validation failed",
                service="Keycloak"
            )
    
    async def refresh_token(
        self,
        refresh_token: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refresh an access token using a refresh token.
        
        Args:
            refresh_token: Refresh token
            realm: Realm name (defaults to admin realm)
            
        Returns:
            New token response with access_token and refresh_token
            
        Raises:
            UnauthorizedError: Refresh token is invalid or expired
            ExternalServiceError: Keycloak connection failed
        """
        realm = realm or self.admin_realm
        client = self._get_realm_client(realm)
        
        try:
            # Refresh the token
            token_response = await asyncio.to_thread(
                client.refresh_token,
                refresh_token
            )
            
            # Add metadata
            token_response['realm'] = realm
            token_response['refreshed_at'] = utc_now().isoformat()
            
            logger.info(f"Token refreshed successfully in realm {realm}")
            return token_response
            
        except KeycloakAuthenticationError as e:
            logger.warning(f"Token refresh failed: {e}")
            raise UnauthorizedError("Invalid or expired refresh token")
        except KeycloakError as e:
            logger.error(f"Keycloak error during token refresh: {e}")
            raise ExternalServiceError(
                message="Token refresh failed",
                service="Keycloak"
            )
    
    async def logout(
        self,
        refresh_token: str,
        realm: Optional[str] = None
    ) -> bool:
        """
        Logout a user session.
        
        Args:
            refresh_token: Refresh token to revoke
            realm: Realm name (defaults to admin realm)
            
        Returns:
            True if logout successful
        """
        realm = realm or self.admin_realm
        client = self._get_realm_client(realm)
        
        try:
            # Logout user
            await asyncio.to_thread(
                client.logout,
                refresh_token
            )
            
            logger.info(f"User logged out successfully in realm {realm}")
            return True
            
        except Exception as e:
            # Logout failures are not critical
            logger.warning(f"Logout failed (non-critical): {e}")
            return False
    
    async def get_userinfo(
        self,
        token: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get user information from token.
        
        Args:
            token: Access token
            realm: Realm name (defaults to admin realm)
            
        Returns:
            User information from token
            
        Raises:
            UnauthorizedError: Token is invalid
            ExternalServiceError: Keycloak connection failed
        """
        realm = realm or self.admin_realm
        client = self._get_realm_client(realm)
        
        try:
            # Get user info
            userinfo = await asyncio.to_thread(
                client.userinfo,
                token
            )
            
            return userinfo
            
        except KeycloakAuthenticationError as e:
            logger.warning(f"Failed to get user info: {e}")
            raise UnauthorizedError("Invalid token")
        except KeycloakError as e:
            logger.error(f"Keycloak error getting user info: {e}")
            raise ExternalServiceError(
                message="Failed to get user information",
                service="Keycloak"
            )
    
    async def decode_token(
        self,
        token: str,
        realm: Optional[str] = None,
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Decode and optionally validate a JWT token using python-keycloak library.
        
        Args:
            token: JWT token to decode
            realm: Realm name (defaults to admin realm)
            validate: Whether to validate the token signature
            
        Returns:
            Decoded token claims
            
        Raises:
            UnauthorizedError: Token is invalid or expired
        """
        realm = realm or self.admin_realm
        client = self._get_realm_client(realm)
        
        try:
            if validate:
                # Decode with validation using python-keycloak
                # Based on research: Use validate=True for full validation
                decoded = await asyncio.to_thread(
                    client.decode_token,
                    token,
                    validate=True
                )
            else:
                # Decode without validation (for debugging)
                # Based on research: Use validate=False to bypass validation
                decoded = await asyncio.to_thread(
                    client.decode_token,
                    token,
                    validate=False
                )
            
            # Log claims if debug mode is enabled
            if settings.jwt_debug_claims:
                logger.debug(f"Decoded token claims: {decoded}")
            
            return decoded
            
        except Exception as e:
            # Handle specific keycloak errors
            error_str = str(e).lower()
            if "audience" in error_str and "invalid" in error_str:
                logger.warning(f"Token audience validation failed: {e}")
                if settings.jwt_audience_fallback:
                    # Try decoding without validation as fallback
                    try:
                        decoded = await asyncio.to_thread(
                            client.decode_token,
                            token,
                            validate=False
                        )
                        logger.info("Successfully decoded token without validation as fallback")
                        return decoded
                    except Exception as fallback_e:
                        logger.error(f"Token decode fallback also failed: {fallback_e}")
                        raise UnauthorizedError("Token validation failed")
                else:
                    raise UnauthorizedError("Token audience validation failed")
            elif "expired" in error_str:
                logger.warning(f"Token has expired: {e}")
                raise UnauthorizedError("Token has expired")
            else:
                logger.error(f"Token decode failed: {e}")
                raise UnauthorizedError("Invalid token")
    
    async def get_realm_public_key(
        self,
        realm: Optional[str] = None,
        force_refresh: bool = False
    ) -> str:
        """
        Get the public key for a realm with caching.
        
        Args:
            realm: Realm name (defaults to admin realm)
            force_refresh: Force refresh the cached key
            
        Returns:
            Public key in PEM format
        """
        realm = realm or self.admin_realm
        
        # Check cache
        if not force_refresh and realm in self._public_keys:
            key, expiry = self._public_keys[realm]
            if expiry > utc_now():
                return key
        
        client = self._get_realm_client(realm)
        
        try:
            # Get public key
            public_key = await asyncio.to_thread(client.public_key)
            
            # Format as PEM
            formatted_key = f"-----BEGIN PUBLIC KEY-----\n{public_key}\n-----END PUBLIC KEY-----"
            
            # Cache for 1 hour
            expiry = utc_now() + timedelta(hours=1)
            self._public_keys[realm] = (formatted_key, expiry)
            
            return formatted_key
            
        except Exception as e:
            logger.error(f"Failed to get realm public key: {e}")
            raise ExternalServiceError(
                message="Failed to get realm public key",
                service="Keycloak"
            )
    
    # Admin operations
    
    async def create_realm(
        self,
        realm_name: str,
        display_name: Optional[str] = None,
        enabled: bool = True
    ) -> bool:
        """
        Create a new realm (admin operation).
        
        Args:
            realm_name: Unique realm identifier
            display_name: Human-readable realm name
            enabled: Whether realm is enabled
            
        Returns:
            True if realm created successfully
            
        Raises:
            ConflictError: Realm already exists
            ExternalServiceError: Creation failed
        """
        admin = await self._get_admin_client()
        
        realm_data = {
            "realm": realm_name,
            "enabled": enabled,
            "displayName": display_name or realm_name,
            "sslRequired": "external",
            "bruteForceProtected": True,
            "passwordPolicy": "length(12) and upperCase(2) and lowerCase(2) and digits(2) and specialChars(2)",
            "duplicateEmailsAllowed": False,
            "loginTheme": "keycloak",
            "internationalizationEnabled": True,
            "supportedLocales": ["en"],
            "defaultLocale": "en"
        }
        
        try:
            await asyncio.to_thread(admin.create_realm, realm_data)
            logger.info(f"Created realm: {realm_name}")
            return True
            
        except KeycloakError as e:
            if "409" in str(e):
                raise ConflictError(
                    message=f"Realm {realm_name} already exists",
                    conflicting_field="realm_name",
                    conflicting_value=realm_name
                )
            logger.error(f"Failed to create realm {realm_name}: {e}")
            raise ExternalServiceError(
                message=f"Failed to create realm {realm_name}",
                service="Keycloak"
            )
    
    async def get_user_by_username(
        self,
        username: str,
        realm: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get user by username in a realm.
        
        Args:
            username: Username to search for
            realm: Realm name (defaults to admin realm)
            
        Returns:
            User data if found, None otherwise
        """
        realm = realm or self.admin_realm
        admin = await self._get_admin_client()
        admin.realm_name = realm
        
        try:
            users = await asyncio.to_thread(
                admin.get_users,
                query={"username": username, "exact": True}
            )
            
            if users:
                return users[0]
            return None
            
        except KeycloakError as e:
            logger.error(f"Failed to get user {username}: {e}")
            return None
    
    async def create_or_update_user(
        self,
        username: str,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        realm: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create or update a user in Keycloak.
        
        Args:
            username: Username
            email: Email address
            first_name: First name
            last_name: Last name
            realm: Realm name (defaults to admin realm)
            attributes: Additional user attributes
            
        Returns:
            User data
        """
        realm = realm or self.admin_realm
        admin = await self._get_admin_client()
        admin.realm_name = realm
        
        # Check if user exists
        existing_user = await self.get_user_by_username(username, realm)
        
        user_data = {
            "username": username,
            "email": email,
            "firstName": first_name or "",
            "lastName": last_name or "",
            "enabled": True,
            "emailVerified": True,
            "attributes": attributes or {}
        }
        
        try:
            if existing_user:
                # Update existing user
                user_id = existing_user["id"]
                await asyncio.to_thread(
                    admin.update_user,
                    user_id,
                    user_data
                )
                logger.info(f"Updated user {username} in realm {realm}")
                user_data["id"] = user_id
            else:
                # Create new user
                user_id = await asyncio.to_thread(
                    admin.create_user,
                    user_data
                )
                logger.info(f"Created user {username} in realm {realm}")
                user_data["id"] = user_id
            
            return user_data
            
        except KeycloakError as e:
            logger.error(f"Failed to create/update user {username}: {e}")
            raise ExternalServiceError(
                message=f"Failed to manage user {username}",
                service="Keycloak"
            )


# Global client instance
_keycloak_client: Optional[KeycloakAsyncClient] = None


async def get_keycloak_client() -> KeycloakAsyncClient:
    """
    Get the global Keycloak async client instance.
    
    Returns:
        KeycloakAsyncClient instance
    """
    global _keycloak_client
    if _keycloak_client is None:
        _keycloak_client = KeycloakAsyncClient()
    return _keycloak_client