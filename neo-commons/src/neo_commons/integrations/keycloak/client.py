"""
Enhanced Keycloak client for neo-commons library.
Protocol-based dependency injection with improved modularity and reusability.
"""
import os
from typing import Optional, Dict, Any, List, Protocol, runtime_checkable
import httpx
import logging
from jose import jwt, JWTError

from neo_commons.exceptions.base import (
    ExternalServiceError,
    UnauthorizedError,
    NotFoundError
)

logger = logging.getLogger(__name__)


@runtime_checkable
class TokenValidationConfigProtocol(Protocol):
    """Protocol for token validation configuration."""
    
    def get_jwt_algorithm(self) -> str:
        """Get JWT algorithm for validation."""
        ...
    
    def get_jwt_audience(self) -> Optional[str]:
        """Get expected JWT audience."""
        ...
    
    def is_jwt_audience_verification_enabled(self) -> bool:
        """Check if audience verification is enabled."""
        ...
    
    def should_fallback_without_audience(self) -> bool:
        """Check if fallback without audience is allowed."""
        ...
    
    def is_debug_claims_enabled(self) -> bool:
        """Check if debug claims logging is enabled."""
        ...


class DefaultTokenValidationConfig:
    """Default implementation of token validation configuration."""
    
    def __init__(
        self,
        jwt_algorithm: str = "RS256",
        jwt_audience: Optional[str] = None,
        jwt_verify_audience: bool = True,
        jwt_audience_fallback: bool = True,
        jwt_debug_claims: bool = False
    ):
        self._jwt_algorithm = jwt_algorithm
        self._jwt_audience = jwt_audience
        self._jwt_verify_audience = jwt_verify_audience
        self._jwt_audience_fallback = jwt_audience_fallback
        self._jwt_debug_claims = jwt_debug_claims
    
    def get_jwt_algorithm(self) -> str:
        return self._jwt_algorithm
    
    def get_jwt_audience(self) -> Optional[str]:
        return self._jwt_audience
    
    def is_jwt_audience_verification_enabled(self) -> bool:
        return self._jwt_verify_audience
    
    def should_fallback_without_audience(self) -> bool:
        return self._jwt_audience_fallback
    
    def is_debug_claims_enabled(self) -> bool:
        return self._jwt_debug_claims


@runtime_checkable  
class HttpClientProtocol(Protocol):
    """Protocol for HTTP client implementations."""
    
    async def post(
        self, 
        url: str, 
        data: Optional[Dict[str, Any]] = None, 
        json: Optional[Dict[str, Any]] = None, 
        headers: Optional[Dict[str, str]] = None
    ) -> Any:
        """Make a POST request."""
        ...
    
    async def get(
        self, 
        url: str, 
        params: Optional[Dict[str, Any]] = None, 
        headers: Optional[Dict[str, str]] = None
    ) -> Any:
        """Make a GET request."""
        ...
    
    async def put(
        self, 
        url: str, 
        json: Optional[Dict[str, Any]] = None, 
        headers: Optional[Dict[str, str]] = None
    ) -> Any:
        """Make a PUT request."""
        ...
    
    async def delete(
        self, 
        url: str, 
        headers: Optional[Dict[str, str]] = None
    ) -> Any:
        """Make a DELETE request."""
        ...


class KeycloakClient:
    """
    Enhanced Keycloak client for neo-commons with protocol-based dependency injection.
    
    Features:
    - Environment variable flexibility for different deployment scenarios
    - Protocol-based configuration for maximum reusability
    - Enhanced token validation with fallback strategies
    - Comprehensive error handling and logging
    - Multi-realm support for tenant isolation
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        admin_realm: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        admin_username: Optional[str] = None,
        admin_password: Optional[str] = None,
        token_validation_config: Optional[TokenValidationConfigProtocol] = None,
        http_client: Optional[HttpClientProtocol] = None
    ):
        """
        Initialize Keycloak client with flexible configuration.
        
        Args:
            base_url: Keycloak base URL (supports multiple env vars)
            admin_realm: Admin realm name (supports multiple env vars)
            client_id: Admin client ID (supports multiple env vars)
            client_secret: Admin client secret (supports multiple env vars)
            admin_username: Admin username (supports multiple env vars)
            admin_password: Admin password (supports multiple env vars)
            token_validation_config: Token validation configuration
            http_client: HTTP client implementation
        """
        # Flexible environment variable support
        self.base_url = base_url or self._get_env_var([
            'KEYCLOAK_URL',
            'KEYCLOAK_BASE_URL', 
            'NEO_KEYCLOAK_URL',
            'APP_KEYCLOAK_URL'
        ], 'http://localhost:8080')
        
        self.admin_realm = admin_realm or self._get_env_var([
            'KEYCLOAK_ADMIN_REALM',
            'NEO_KEYCLOAK_ADMIN_REALM',
            'APP_KEYCLOAK_ADMIN_REALM'
        ], 'master')
        
        self.client_id = client_id or self._get_env_var([
            'KEYCLOAK_ADMIN_CLIENT_ID',
            'NEO_KEYCLOAK_ADMIN_CLIENT_ID',
            'APP_KEYCLOAK_ADMIN_CLIENT_ID'
        ], 'admin-cli')
        
        self.client_secret = client_secret or self._get_env_var([
            'KEYCLOAK_ADMIN_CLIENT_SECRET',
            'NEO_KEYCLOAK_ADMIN_CLIENT_SECRET', 
            'APP_KEYCLOAK_ADMIN_CLIENT_SECRET'
        ])
        
        self.admin_username = admin_username or self._get_env_var([
            'KEYCLOAK_ADMIN_USERNAME',
            'KEYCLOAK_ADMIN_USER',
            'NEO_KEYCLOAK_ADMIN_USERNAME',
            'APP_KEYCLOAK_ADMIN_USERNAME'
        ])
        
        self.admin_password = admin_password or self._get_env_var([
            'KEYCLOAK_ADMIN_PASSWORD',
            'NEO_KEYCLOAK_ADMIN_PASSWORD',
            'APP_KEYCLOAK_ADMIN_PASSWORD'
        ])
        
        # Configuration dependencies
        self.token_config = token_validation_config or DefaultTokenValidationConfig()
        self.http_client = http_client
        
        # Cache for tokens and keys
        self._admin_token: Optional[str] = None
        self._public_keys: Dict[str, str] = {}
        
        logger.info(f"Initialized KeycloakClient with base_url: {self.base_url}")
    
    def _get_env_var(self, var_names: List[str], default: Optional[str] = None) -> Optional[str]:
        """
        Get environment variable with multiple name fallbacks.
        
        Args:
            var_names: List of environment variable names to try
            default: Default value if none found
            
        Returns:
            Environment variable value or default
        """
        for var_name in var_names:
            value = os.environ.get(var_name)
            if value:
                return value
        return default
    
    async def _get_admin_token(self) -> str:
        """
        Get admin access token for Keycloak API with enhanced error handling.
        
        Returns:
            Admin access token
            
        Raises:
            ExternalServiceError: Authentication failed
        """
        if self._admin_token:
            # TODO: Check token expiry and refresh if needed
            return self._admin_token
        
        token_url = f"{self.base_url}/realms/{self.admin_realm}/protocol/openid-connect/token"
        
        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "username": self.admin_username,
            "password": self.admin_password
        }
        
        # Add client secret if available
        if self.client_secret:
            data["client_secret"] = self.client_secret
        
        try:
            if self.http_client:
                response = await self.http_client.post(token_url, data=data)
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.post(token_url, data=data)
            
            response.raise_for_status()
            token_data = response.json()
            self._admin_token = token_data["access_token"]
            
            logger.debug("Successfully obtained admin token")
            return self._admin_token
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to get Keycloak admin token: {e}")
            raise ExternalServiceError(
                message="Failed to authenticate with Keycloak",
                service="Keycloak",
                details={"endpoint": token_url, "error": str(e)}
            )
    
    async def get_realm_public_key(self, realm: str, force_refresh: bool = False) -> str:
        """
        Get public key for a realm with caching.
        
        Args:
            realm: Realm name
            force_refresh: Force refresh of cached key
            
        Returns:
            Formatted public key
            
        Raises:
            ExternalServiceError: Failed to get public key
        """
        if not force_refresh and realm in self._public_keys:
            return self._public_keys[realm]
        
        url = f"{self.base_url}/realms/{realm}"
        
        try:
            if self.http_client:
                response = await self.http_client.get(url)
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url)
            
            response.raise_for_status()
            data = response.json()
            
            # Format the public key
            public_key = data.get("public_key", "")
            if not public_key:
                raise ExternalServiceError(
                    message=f"No public key found for realm {realm}",
                    service="Keycloak"
                )
            
            formatted_key = f"-----BEGIN PUBLIC KEY-----\n{public_key}\n-----END PUBLIC KEY-----"
            self._public_keys[realm] = formatted_key
            
            logger.debug(f"Retrieved public key for realm: {realm}")
            return formatted_key
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to get realm public key for {realm}: {e}")
            raise ExternalServiceError(
                message=f"Failed to get realm public key for {realm}",
                service="Keycloak",
                details={"realm": realm, "endpoint": url, "error": str(e)}
            )
    
    async def validate_token(self, token: str, realm: str) -> Dict[str, Any]:
        """
        Validate JWT token with enhanced error handling and fallback strategies.
        
        Args:
            token: JWT token to validate
            realm: Realm for validation
            
        Returns:
            Decoded token claims
            
        Raises:
            UnauthorizedError: Invalid or expired token
        """
        try:
            # Get public key for the realm
            public_key = await self.get_realm_public_key(realm)
            
            # Prepare decode arguments
            decode_kwargs = {
                "key": public_key,
                "algorithms": [self.token_config.get_jwt_algorithm()],
                "issuer": f"{self.base_url}/realms/{realm}"
            }
            
            # Add audience if verification is enabled
            if self.token_config.is_jwt_audience_verification_enabled():
                audience = self.token_config.get_jwt_audience()
                if audience:
                    decode_kwargs["audience"] = audience
            
            try:
                decoded = jwt.decode(token, **decode_kwargs)
                logger.debug(f"Successfully validated token for realm: {realm}")
                return decoded
                
            except JWTError as e:
                if "Invalid audience" in str(e) and self.token_config.should_fallback_without_audience():
                    # Fallback: Try without audience validation
                    logger.warning(f"Audience validation failed for realm {realm}, trying without audience verification: {e}")
                    
                    # Remove audience and disable verification
                    decode_kwargs.pop("audience", None)
                    decode_kwargs["options"] = {"verify_aud": False}
                    
                    try:
                        decoded = jwt.decode(token, **decode_kwargs)
                        
                        # Debug logging if enabled
                        if self.token_config.is_debug_claims_enabled():
                            token_aud = decoded.get('aud', 'not_present')
                            expected_aud = self.token_config.get_jwt_audience()
                            logger.debug(f"Token audience: {token_aud}, Expected: {expected_aud}")
                        
                        return decoded
                        
                    except JWTError as fallback_error:
                        # Log debugging information
                        logger.error(f"Fallback validation failed for realm {realm}: {fallback_error}")
                        logger.error(f"Expected issuer: {decode_kwargs.get('issuer')}")
                        
                        # Try to decode without verification for debugging
                        try:
                            unverified_claims = jwt.decode(
                                token,
                                options={"verify_signature": False, "verify_aud": False, "verify_iss": False}
                            )
                            logger.error(f"Actual token issuer: {unverified_claims.get('iss', 'not_present')}")
                            logger.error(f"Actual token audience: {unverified_claims.get('aud', 'not_present')}")
                        except Exception as debug_error:
                            logger.error(f"Could not decode token for debugging: {debug_error}")
                        
                        raise fallback_error
                else:
                    raise
            
        except JWTError as e:
            if "expired" in str(e).lower():
                raise UnauthorizedError("Token has expired")
            logger.error(f"Invalid token for realm {realm}: {e}")
            raise UnauthorizedError(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Token validation error for realm {realm}: {e}")
            raise UnauthorizedError(f"Token validation failed: {str(e)}")
    
    async def create_realm(
        self, 
        realm_name: str, 
        display_name: Optional[str] = None,
        realm_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new realm with enhanced configuration options.
        
        Args:
            realm_name: Name of the realm
            display_name: Display name for the realm
            realm_config: Additional realm configuration
            
        Returns:
            Created realm data
            
        Raises:
            ExternalServiceError: Failed to create realm
        """
        admin_token = await self._get_admin_token()
        url = f"{self.base_url}/admin/realms"
        
        # Base realm configuration
        realm_data = {
            "realm": realm_name,
            "enabled": True,
            "displayName": display_name or realm_name,
            "sslRequired": "external",
            "bruteForceProtected": True,
            "passwordPolicy": "length(8) and upperCase(1) and lowerCase(1) and digits(1) and specialChars(1)",
            "duplicateEmailsAllowed": False,
            "loginTheme": "keycloak",
            "adminTheme": "keycloak",
            "emailTheme": "keycloak",
            "internationalizationEnabled": True,
            "supportedLocales": ["en"],
            "defaultLocale": "en"
        }
        
        # Merge additional configuration
        if realm_config:
            realm_data.update(realm_config)
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        try:
            if self.http_client:
                response = await self.http_client.post(url, json=realm_data, headers=headers)
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, json=realm_data, headers=headers)
            
            if response.status_code == 201:
                logger.info(f"Created realm: {realm_name}")
                return realm_data
            elif response.status_code == 409:
                logger.warning(f"Realm {realm_name} already exists")
                return realm_data
            else:
                response.raise_for_status()
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to create realm {realm_name}: {e}")
            raise ExternalServiceError(
                message=f"Failed to create realm {realm_name}",
                service="Keycloak",
                details={"realm": realm_name, "error": str(e)}
            )
    
    async def create_client(
        self, 
        realm: str, 
        client_id: str,
        client_name: Optional[str] = None,
        redirect_uris: Optional[List[str]] = None,
        client_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a client in a realm with enhanced configuration options.
        
        Args:
            realm: Realm name
            client_id: Client ID
            client_name: Client display name
            redirect_uris: Allowed redirect URIs
            client_config: Additional client configuration
            
        Returns:
            Created client data
            
        Raises:
            ExternalServiceError: Failed to create client
        """
        admin_token = await self._get_admin_token()
        url = f"{self.base_url}/admin/realms/{realm}/clients"
        
        # Base client configuration
        client_data = {
            "clientId": client_id,
            "name": client_name or client_id,
            "enabled": True,
            "protocol": "openid-connect",
            "publicClient": False,
            "standardFlowEnabled": True,
            "directAccessGrantsEnabled": True,
            "serviceAccountsEnabled": True,
            "authorizationServicesEnabled": False,
            "redirectUris": redirect_uris or ["*"],
            "webOrigins": ["*"],
            "attributes": {
                "saml.force.post.binding": "false",
                "saml.multivalued.roles": "false",
                "oauth2.device.authorization.grant.enabled": "false",
                "oidc.ciba.grant.enabled": "false"
            }
        }
        
        # Merge additional configuration
        if client_config:
            client_data.update(client_config)
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        try:
            if self.http_client:
                response = await self.http_client.post(url, json=client_data, headers=headers)
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, json=client_data, headers=headers)
            
            if response.status_code == 201:
                logger.info(f"Created client {client_id} in realm {realm}")
                
                # Get the created client details
                location = response.headers.get("Location")
                if location:
                    if self.http_client:
                        client_response = await self.http_client.get(location, headers=headers)
                    else:
                        async with httpx.AsyncClient() as client:
                            client_response = await client.get(location, headers=headers)
                    return client_response.json()
                return client_data
                
            elif response.status_code == 409:
                logger.warning(f"Client {client_id} already exists in realm {realm}")
                return client_data
            else:
                response.raise_for_status()
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to create client {client_id} in realm {realm}: {e}")
            raise ExternalServiceError(
                message=f"Failed to create client {client_id}",
                service="Keycloak",
                details={"realm": realm, "client_id": client_id, "error": str(e)}
            )
    
    async def create_user(
        self,
        realm: str,
        username: str,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        password: Optional[str] = None,
        enabled: bool = True,
        user_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a user in a realm with enhanced configuration options.
        
        Args:
            realm: Realm name
            username: Username
            email: Email address
            first_name: First name
            last_name: Last name
            password: User password
            enabled: Whether user is enabled
            user_config: Additional user configuration
            
        Returns:
            Created user data
            
        Raises:
            ExternalServiceError: Failed to create user
        """
        admin_token = await self._get_admin_token()
        url = f"{self.base_url}/admin/realms/{realm}/users"
        
        # Base user configuration
        user_data = {
            "username": username,
            "email": email,
            "firstName": first_name or "",
            "lastName": last_name or "",
            "enabled": enabled,
            "emailVerified": False,
            "credentials": []
        }
        
        # Add password if provided
        if password:
            user_data["credentials"] = [{
                "type": "password",
                "value": password,
                "temporary": False
            }]
        
        # Merge additional configuration
        if user_config:
            user_data.update(user_config)
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        try:
            if self.http_client:
                response = await self.http_client.post(url, json=user_data, headers=headers)
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, json=user_data, headers=headers)
            
            if response.status_code == 201:
                logger.info(f"Created user {username} in realm {realm}")
                
                # Get the created user ID from Location header
                location = response.headers.get("Location")
                if location:
                    user_id = location.split("/")[-1]
                    user_data["id"] = user_id
                return user_data
                
            elif response.status_code == 409:
                logger.warning(f"User {username} already exists in realm {realm}")
                return user_data
            else:
                response.raise_for_status()
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to create user {username} in realm {realm}: {e}")
            raise ExternalServiceError(
                message=f"Failed to create user {username}",
                service="Keycloak",
                details={"realm": realm, "username": username, "error": str(e)}
            )
    
    async def get_user(self, realm: str, user_id: str) -> Dict[str, Any]:
        """
        Get user details by ID.
        
        Args:
            realm: Realm name
            user_id: User ID
            
        Returns:
            User details
            
        Raises:
            NotFoundError: User not found
            ExternalServiceError: Failed to get user
        """
        admin_token = await self._get_admin_token()
        url = f"{self.base_url}/admin/realms/{realm}/users/{user_id}"
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        try:
            if self.http_client:
                response = await self.http_client.get(url, headers=headers)
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, headers=headers)
            
            if response.status_code == 404:
                raise NotFoundError("User", user_id)
                
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to get user {user_id} in realm {realm}: {e}")
            raise ExternalServiceError(
                message=f"Failed to get user {user_id}",
                service="Keycloak",
                details={"realm": realm, "user_id": user_id, "error": str(e)}
            )
    
    async def get_user_by_username(self, realm: str, username: str) -> Optional[Dict[str, Any]]:
        """
        Get user details by username.
        
        Args:
            realm: Realm name
            username: Username
            
        Returns:
            User details or None if not found
            
        Raises:
            ExternalServiceError: Failed to get user
        """
        admin_token = await self._get_admin_token()
        url = f"{self.base_url}/admin/realms/{realm}/users"
        headers = {"Authorization": f"Bearer {admin_token}"}
        params = {"username": username, "exact": "true"}
        
        try:
            if self.http_client:
                response = await self.http_client.get(url, params=params, headers=headers)
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, params=params, headers=headers)
            
            response.raise_for_status()
            users = response.json()
            
            if users:
                return users[0]
            return None
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to get user by username {username} in realm {realm}: {e}")
            raise ExternalServiceError(
                message=f"Failed to get user {username}",
                service="Keycloak",
                details={"realm": realm, "username": username, "error": str(e)}
            )
    
    async def update_user(
        self,
        realm: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update user details.
        
        Args:
            realm: Realm name
            user_id: User ID
            updates: Fields to update
            
        Returns:
            Updated user data
            
        Raises:
            NotFoundError: User not found
            ExternalServiceError: Failed to update user
        """
        admin_token = await self._get_admin_token()
        url = f"{self.base_url}/admin/realms/{realm}/users/{user_id}"
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        try:
            if self.http_client:
                response = await self.http_client.put(url, json=updates, headers=headers)
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.put(url, json=updates, headers=headers)
            
            if response.status_code == 404:
                raise NotFoundError("User", user_id)
                
            response.raise_for_status()
            logger.info(f"Updated user {user_id} in realm {realm}")
            return updates
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to update user {user_id} in realm {realm}: {e}")
            raise ExternalServiceError(
                message=f"Failed to update user {user_id}",
                service="Keycloak",
                details={"realm": realm, "user_id": user_id, "error": str(e)}
            )
    
    async def delete_user(self, realm: str, user_id: str) -> bool:
        """
        Delete a user.
        
        Args:
            realm: Realm name
            user_id: User ID
            
        Returns:
            True if deletion successful
            
        Raises:
            NotFoundError: User not found
            ExternalServiceError: Failed to delete user
        """
        admin_token = await self._get_admin_token()
        url = f"{self.base_url}/admin/realms/{realm}/users/{user_id}"
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        try:
            if self.http_client:
                response = await self.http_client.delete(url, headers=headers)
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.delete(url, headers=headers)
            
            if response.status_code == 404:
                raise NotFoundError("User", user_id)
                
            response.raise_for_status()
            logger.info(f"Deleted user {user_id} from realm {realm}")
            return True
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to delete user {user_id} in realm {realm}: {e}")
            raise ExternalServiceError(
                message=f"Failed to delete user {user_id}",
                service="Keycloak",
                details={"realm": realm, "user_id": user_id, "error": str(e)}
            )
    
    async def authenticate(
        self,
        realm: str,
        username: str,
        password: str,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authenticate a user and get tokens.
        
        Args:
            realm: Realm name
            username: Username
            password: Password
            client_id: Optional client ID override
            client_secret: Optional client secret override
            
        Returns:
            Authentication response with tokens
            
        Raises:
            UnauthorizedError: Invalid credentials
        """
        token_url = f"{self.base_url}/realms/{realm}/protocol/openid-connect/token"
        
        data = {
            "grant_type": "password",
            "username": username,
            "password": password,
            "client_id": client_id or self.client_id
        }
        
        # Add client secret if available
        secret = client_secret or (self.client_secret if client_id == self.client_id else None)
        if secret:
            data["client_secret"] = secret
        
        try:
            if self.http_client:
                response = await self.http_client.post(token_url, data=data)
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.post(token_url, data=data)
            
            if response.status_code == 401:
                raise UnauthorizedError("Invalid username or password")
                
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"Authentication failed for user {username} in realm {realm}: {e}")
            raise UnauthorizedError("Authentication failed")
    
    async def refresh_token(
        self, 
        realm: str, 
        refresh_token: str,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refresh an access token.
        
        Args:
            realm: Realm name
            refresh_token: Refresh token
            client_id: Optional client ID override
            client_secret: Optional client secret override
            
        Returns:
            New tokens
            
        Raises:
            UnauthorizedError: Invalid or expired refresh token
        """
        token_url = f"{self.base_url}/realms/{realm}/protocol/openid-connect/token"
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id or self.client_id
        }
        
        # Add client secret if available
        secret = client_secret or self.client_secret
        if secret:
            data["client_secret"] = secret
        
        try:
            if self.http_client:
                response = await self.http_client.post(token_url, data=data)
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.post(token_url, data=data)
            
            if response.status_code == 401:
                raise UnauthorizedError("Invalid or expired refresh token")
                
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"Token refresh failed in realm {realm}: {e}")
            raise UnauthorizedError("Token refresh failed")
    
    async def logout(
        self, 
        realm: str, 
        refresh_token: str,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None
    ) -> bool:
        """
        Logout a user session.
        
        Args:
            realm: Realm name
            refresh_token: Refresh token
            client_id: Optional client ID override
            client_secret: Optional client secret override
            
        Returns:
            True if logout successful
        """
        logout_url = f"{self.base_url}/realms/{realm}/protocol/openid-connect/logout"
        
        data = {
            "refresh_token": refresh_token,
            "client_id": client_id or self.client_id
        }
        
        # Add client secret if available
        secret = client_secret or self.client_secret
        if secret:
            data["client_secret"] = secret
        
        try:
            if self.http_client:
                response = await self.http_client.post(logout_url, data=data)
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.post(logout_url, data=data)
            
            response.raise_for_status()
            logger.info(f"Successfully logged out user session in realm {realm}")
            return True
            
        except httpx.HTTPError as e:
            logger.error(f"Logout failed in realm {realm}: {e}")
            # Logout failures are not critical
            return False
    
    def clear_cache(self):
        """Clear cached tokens and public keys."""
        self._admin_token = None
        self._public_keys.clear()
        logger.info("Cleared KeycloakClient cache")


# Factory function for creating client instances
def create_keycloak_client(
    base_url: Optional[str] = None,
    admin_realm: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    admin_username: Optional[str] = None,
    admin_password: Optional[str] = None,
    token_validation_config: Optional[TokenValidationConfigProtocol] = None,
    http_client: Optional[HttpClientProtocol] = None
) -> KeycloakClient:
    """
    Factory function to create a KeycloakClient instance.
    
    Args:
        base_url: Keycloak base URL
        admin_realm: Admin realm name
        client_id: Admin client ID
        client_secret: Admin client secret
        admin_username: Admin username
        admin_password: Admin password
        token_validation_config: Token validation configuration
        http_client: HTTP client implementation
        
    Returns:
        Configured KeycloakClient instance
    """
    return KeycloakClient(
        base_url=base_url,
        admin_realm=admin_realm,
        client_id=client_id,
        client_secret=client_secret,
        admin_username=admin_username,
        admin_password=admin_password,
        token_validation_config=token_validation_config,
        http_client=http_client
    )


# Global client instance for singleton usage (optional pattern)
_global_keycloak_client: Optional[KeycloakClient] = None


def get_keycloak_client() -> KeycloakClient:
    """
    Get the global Keycloak client instance (singleton pattern).
    
    Returns:
        Global KeycloakClient instance
    """
    global _global_keycloak_client
    if _global_keycloak_client is None:
        _global_keycloak_client = create_keycloak_client()
    return _global_keycloak_client


def set_global_keycloak_client(client: KeycloakClient):
    """
    Set the global Keycloak client instance.
    
    Args:
        client: KeycloakClient instance to use globally
    """
    global _global_keycloak_client
    _global_keycloak_client = client