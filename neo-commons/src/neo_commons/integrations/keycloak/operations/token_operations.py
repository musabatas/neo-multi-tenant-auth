"""
Token operations for Keycloak integration.

Handles authentication, token introspection, refresh, and logout operations.
"""
import logging
from typing import Optional, Dict, Any

from ..protocols.protocols import KeycloakTokenProtocol
from ..clients.base_client import BaseKeycloakClient

logger = logging.getLogger(__name__)


class KeycloakTokenOperations(BaseKeycloakClient, KeycloakTokenProtocol):
    """Token operations implementation for Keycloak."""
    
    async def authenticate(
        self,
        username: str,
        password: str,
        realm: Optional[str] = None,
        client_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authenticate user and get tokens.
        
        Args:
            username: User's username
            password: User's password
            realm: Realm name (defaults to admin realm)
            client_id: Client ID (defaults to configured client)
            
        Returns:
            Dictionary containing access_token, refresh_token, and metadata
        """
        realm = realm or self.config.admin_realm
        client_id = client_id or self.config.client_id
        
        cache_key = self._get_cache_key("auth", realm, username)
        
        # Check cache first (but not for passwords)
        # Note: We don't cache authentication results for security
        
        logger.info(f"Authenticating user {username} in realm {realm}")
        
        try:
            client = self._get_realm_client(realm)
            if not client:
                raise ValueError("Failed to create realm client")
            
            # Use python-keycloak for authentication
            token_response = await self._retry_operation(
                client.token,
                username=username,
                password=password
            )
            
            # Enhance response with metadata
            enhanced_response = {
                **token_response,
                "realm": realm,
                "client_id": client_id,
                "username": username,
                "authenticated_at": logger.info("Authentication successful"),
                "expires_in": token_response.get("expires_in", 300)
            }
            
            logger.info(f"User {username} authenticated successfully in realm {realm}")
            return enhanced_response
            
        except Exception as e:
            logger.error(f"Authentication failed for user {username} in realm {realm}: {e}")
            raise
    
    async def introspect_token(
        self,
        token: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Introspect token validity and get token information.
        
        Args:
            token: Access token to introspect
            realm: Realm name (defaults to admin realm)
            
        Returns:
            Token introspection result
        """
        realm = realm or self.config.admin_realm
        
        # Create cache key based on token hash (first 16 chars for security)
        token_hash = hash(token)
        cache_key = self._get_cache_key("introspect", realm, str(token_hash))
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        logger.debug(f"Introspecting token in realm {realm}")
        
        try:
            client = self._get_realm_client(realm)
            if not client:
                raise ValueError("Failed to create realm client")
            
            # Use python-keycloak for introspection
            introspection_result = await self._retry_operation(
                client.introspect,
                token=token
            )
            
            # Enhance response with metadata
            enhanced_result = {
                **introspection_result,
                "realm": realm,
                "introspected_at": logger.debug("Token introspection successful")
            }
            
            # Cache the result if token is active
            if enhanced_result.get("active", False):
                self._set_cache(cache_key, enhanced_result)
            
            logger.debug(f"Token introspection completed for realm {realm}")
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Token introspection failed in realm {realm}: {e}")
            raise
    
    async def refresh_token(
        self,
        refresh_token: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token
            realm: Realm name (defaults to admin realm)
            
        Returns:
            New token set
        """
        realm = realm or self.config.admin_realm
        
        logger.debug(f"Refreshing token in realm {realm}")
        
        try:
            client = self._get_realm_client(realm)
            if not client:
                raise ValueError("Failed to create realm client")
            
            # Use python-keycloak for token refresh
            refresh_response = await self._retry_operation(
                client.refresh_token,
                refresh_token=refresh_token
            )
            
            # Enhance response with metadata
            enhanced_response = {
                **refresh_response,
                "realm": realm,
                "refreshed_at": logger.debug("Token refresh successful"),
                "expires_in": refresh_response.get("expires_in", 300)
            }
            
            logger.debug(f"Token refreshed successfully in realm {realm}")
            return enhanced_response
            
        except Exception as e:
            logger.error(f"Token refresh failed in realm {realm}: {e}")
            raise
    
    async def logout(
        self,
        refresh_token: str,
        realm: Optional[str] = None
    ) -> bool:
        """
        Logout user by invalidating tokens.
        
        Args:
            refresh_token: Refresh token to invalidate
            realm: Realm name (defaults to admin realm)
            
        Returns:
            True if logout was successful
        """
        realm = realm or self.config.admin_realm
        
        logger.info(f"Logging out user in realm {realm}")
        
        try:
            client = self._get_realm_client(realm)
            if not client:
                raise ValueError("Failed to create realm client")
            
            # Use python-keycloak for logout
            await self._retry_operation(
                client.logout,
                refresh_token=refresh_token
            )
            
            logger.info(f"User logged out successfully in realm {realm}")
            return True
            
        except Exception as e:
            logger.error(f"Logout failed in realm {realm}: {e}")
            # Don't re-raise logout errors - it's better to return False
            return False
    
    async def get_userinfo(
        self,
        access_token: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get user information from access token.
        
        Args:
            access_token: Valid access token
            realm: Realm name (defaults to admin realm)
            
        Returns:
            User information
        """
        realm = realm or self.config.admin_realm
        
        # Create cache key based on token hash
        token_hash = hash(access_token)
        cache_key = self._get_cache_key("userinfo", realm, str(token_hash))
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        logger.debug(f"Getting user info in realm {realm}")
        
        try:
            client = self._get_realm_client(realm)
            if not client:
                raise ValueError("Failed to create realm client")
            
            # Use python-keycloak for userinfo
            userinfo = await self._retry_operation(
                client.userinfo,
                token=access_token
            )
            
            # Enhance response with metadata
            enhanced_userinfo = {
                **userinfo,
                "realm": realm,
                "retrieved_at": logger.debug("User info retrieval successful")
            }
            
            # Cache the result
            self._set_cache(cache_key, enhanced_userinfo)
            
            logger.debug(f"User info retrieved successfully in realm {realm}")
            return enhanced_userinfo
            
        except Exception as e:
            logger.error(f"User info retrieval failed in realm {realm}: {e}")
            raise
    
    async def decode_token(
        self,
        token: str,
        realm: Optional[str] = None,
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Decode and optionally validate JWT token.
        
        Args:
            token: JWT token to decode
            realm: Realm name (defaults to admin realm)
            validate: Whether to validate token signature
            
        Returns:
            Decoded token payload
        """
        realm = realm or self.config.admin_realm
        
        logger.debug(f"Decoding token for realm {realm}")
        
        try:
            client = self._get_realm_client(realm)
            if not client:
                raise ValueError("Failed to create realm client")
            
            if validate:
                # Get realm public key for validation
                public_key = await self.get_realm_public_key(realm)
                if not public_key:
                    raise ValueError("Failed to get realm public key")
                
                # Decode and validate token
                decoded_token = await self._retry_operation(
                    client.decode_token,
                    token=token,
                    key=public_key,
                    options={"verify_signature": True, "verify_aud": False, "verify_exp": True}
                )
            else:
                # Decode without validation
                decoded_token = await self._retry_operation(
                    client.decode_token,
                    token=token,
                    options={"verify_signature": False, "verify_aud": False, "verify_exp": False}
                )
            
            # Enhance response with metadata
            enhanced_token = {
                **decoded_token,
                "realm": realm,
                "decoded_at": logger.debug("Token decoded successfully"),
                "validated": validate
            }
            
            logger.debug(f"Token decoded successfully for realm {realm}")
            return enhanced_token
            
        except Exception as e:
            logger.error(f"Token decode failed for realm {realm}: {e}")
            raise
    
    async def get_realm_public_key(
        self,
        realm: str
    ) -> str:
        """
        Get realm public key for token validation.
        
        Args:
            realm: Realm name
            
        Returns:
            Public key string
        """
        cache_key = self._get_cache_key("public_key", realm, "key")
        
        # Check cache first (public keys change infrequently)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result.get("key", "")
        
        logger.debug(f"Getting public key for realm {realm}")
        
        try:
            client = self._get_realm_client(realm)
            if not client:
                raise ValueError("Failed to create realm client")
            
            # Get public key
            public_key = await self._retry_operation(
                client.public_key
            )
            
            # Cache the key
            key_data = {
                "key": public_key,
                "realm": realm,
                "retrieved_at": logger.debug("Public key retrieval successful")
            }
            self._set_cache(cache_key, key_data)
            
            logger.debug(f"Public key retrieved successfully for realm {realm}")
            return public_key
            
        except Exception as e:
            logger.error(f"Public key retrieval failed for realm {realm}: {e}")
            raise