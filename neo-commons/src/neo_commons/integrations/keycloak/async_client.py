"""
Enhanced async Keycloak client for neo-commons with protocol-based dependency injection.
Provides flexible Keycloak integration without tight coupling to application-specific settings.
"""
import logging
import os
from typing import Optional, Dict, Any, List, Protocol, runtime_checkable, Callable, Union
from datetime import datetime, timedelta
from functools import lru_cache
import asyncio
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


@runtime_checkable
class KeycloakConfigProtocol(Protocol):
    """Protocol for Keycloak configuration implementations."""
    
    @property
    def server_url(self) -> str:
        """Keycloak server URL."""
        ...
    
    @property
    def admin_realm(self) -> str:
        """Admin realm name."""
        ...
    
    @property
    def client_id(self) -> str:
        """Client ID for authentication."""
        ...
    
    @property
    def client_secret(self) -> str:
        """Client secret for authentication."""
        ...
    
    @property
    def admin_username(self) -> Optional[str]:
        """Admin username for admin operations."""
        ...
    
    @property
    def admin_password(self) -> Optional[str]:
        """Admin password for admin operations."""
        ...
    
    @property
    def connection_timeout(self) -> float:
        """Connection timeout in seconds."""
        ...
    
    @property
    def max_connections(self) -> int:
        """Maximum number of connections."""
        ...
    
    @property
    def verify_ssl(self) -> bool:
        """Whether to verify SSL certificates."""
        ...


@runtime_checkable
class HttpClientProtocol(Protocol):
    """Protocol for HTTP client implementations."""
    
    async def get(self, url: str, **kwargs) -> Dict[str, Any]:
        """Perform GET request."""
        ...
    
    async def post(self, url: str, **kwargs) -> Dict[str, Any]:
        """Perform POST request."""
        ...
    
    async def put(self, url: str, **kwargs) -> Dict[str, Any]:
        """Perform PUT request."""
        ...
    
    async def delete(self, url: str, **kwargs) -> Dict[str, Any]:
        """Perform DELETE request."""
        ...
    
    async def close(self):
        """Close the client."""
        ...


class DefaultKeycloakConfig:
    """Default implementation of Keycloak configuration with environment variable support."""
    
    def __init__(
        self,
        server_url: Optional[str] = None,
        admin_realm: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        admin_username: Optional[str] = None,
        admin_password: Optional[str] = None,
        connection_timeout: float = 30.0,
        max_connections: int = 100,
        verify_ssl: bool = True
    ):
        """
        Initialize configuration with flexible environment variable support.
        
        Args:
            server_url: Keycloak server URL
            admin_realm: Admin realm name
            client_id: Client ID for authentication
            client_secret: Client secret for authentication
            admin_username: Admin username for admin operations
            admin_password: Admin password for admin operations
            connection_timeout: Connection timeout in seconds
            max_connections: Maximum number of connections
            verify_ssl: Whether to verify SSL certificates
        """
        self._server_url = server_url or self._get_env_var(
            ['KEYCLOAK_URL', 'KEYCLOAK_SERVER_URL', 'KC_URL'],
            'http://localhost:8080'
        )
        self._admin_realm = admin_realm or self._get_env_var(
            ['KEYCLOAK_ADMIN_REALM', 'KC_ADMIN_REALM', 'KEYCLOAK_REALM'],
            'master'
        )
        self._client_id = client_id or self._get_env_var(
            ['KEYCLOAK_CLIENT_ID', 'KC_CLIENT_ID', 'KEYCLOAK_ADMIN_CLIENT_ID'],
            'admin-cli'
        )
        self._client_secret = client_secret or self._get_env_var(
            ['KEYCLOAK_CLIENT_SECRET', 'KC_CLIENT_SECRET', 'KEYCLOAK_ADMIN_CLIENT_SECRET'],
            ''
        )
        self._admin_username = admin_username or self._get_env_var(
            ['KEYCLOAK_ADMIN_USERNAME', 'KC_ADMIN_USERNAME', 'KEYCLOAK_ADMIN_USER'],
            'admin'
        )
        self._admin_password = admin_password or self._get_env_var(
            ['KEYCLOAK_ADMIN_PASSWORD', 'KC_ADMIN_PASSWORD', 'KEYCLOAK_ADMIN_PASS'],
            'admin'
        )
        self._connection_timeout = connection_timeout
        self._max_connections = max_connections
        self._verify_ssl = verify_ssl
    
    def _get_env_var(self, var_names: List[str], default: str = '') -> str:
        """Get environment variable from list of possible names."""
        for var_name in var_names:
            value = os.getenv(var_name)
            if value:
                return value
        return default
    
    @property
    def server_url(self) -> str:
        return self._server_url
    
    @property
    def admin_realm(self) -> str:
        return self._admin_realm
    
    @property
    def client_id(self) -> str:
        return self._client_id
    
    @property
    def client_secret(self) -> str:
        return self._client_secret
    
    @property
    def admin_username(self) -> Optional[str]:
        return self._admin_username
    
    @property
    def admin_password(self) -> Optional[str]:
        return self._admin_password
    
    @property
    def connection_timeout(self) -> float:
        return self._connection_timeout
    
    @property
    def max_connections(self) -> int:
        return self._max_connections
    
    @property
    def verify_ssl(self) -> bool:
        return self._verify_ssl


class HttpxHttpClient:
    """HTTP client implementation using httpx."""
    
    def __init__(self, timeout: float = 30.0, max_connections: int = 100):
        """Initialize httpx client."""
        self._timeout = timeout
        self._max_connections = max_connections
        self._client = None
    
    async def _get_client(self):
        """Get or create httpx client."""
        if not self._client:
            try:
                import httpx
                self._client = httpx.AsyncClient(
                    timeout=httpx.Timeout(self._timeout),
                    limits=httpx.Limits(
                        max_keepalive_connections=min(20, self._max_connections // 5),
                        max_connections=self._max_connections
                    )
                )
            except ImportError:
                logger.error("httpx not available, HTTP operations will fail")
                raise RuntimeError("httpx library is required but not installed")
        return self._client
    
    async def get(self, url: str, **kwargs) -> Dict[str, Any]:
        """Perform GET request."""
        client = await self._get_client()
        response = await client.get(url, **kwargs)
        response.raise_for_status()
        return response.json()
    
    async def post(self, url: str, **kwargs) -> Dict[str, Any]:
        """Perform POST request."""
        client = await self._get_client()
        response = await client.post(url, **kwargs)
        response.raise_for_status()
        return response.json()
    
    async def put(self, url: str, **kwargs) -> Dict[str, Any]:
        """Perform PUT request."""
        client = await self._get_client()
        response = await client.put(url, **kwargs)
        response.raise_for_status()
        return response.json()
    
    async def delete(self, url: str, **kwargs) -> Dict[str, Any]:
        """Perform DELETE request."""
        client = await self._get_client()
        response = await client.delete(url, **kwargs)
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the client."""
        if self._client:
            await self._client.aclose()
            self._client = None


class EnhancedKeycloakAsyncClient:
    """
    Enhanced async Keycloak client with protocol-based dependency injection.
    
    Features:
    - Protocol-based configuration for flexible deployment
    - Multiple HTTP client support (httpx, aiohttp, custom)
    - Configurable connection pooling and timeouts
    - Enhanced error handling with retry mechanisms
    - Token caching and refresh with TTL management
    - Multi-realm support with lazy loading
    - Admin operations with comprehensive user management
    - Health checking and connection validation
    - Metrics and monitoring integration
    - Environment-based configuration with multiple fallbacks
    """
    
    def __init__(
        self,
        config: Optional[KeycloakConfigProtocol] = None,
        http_client: Optional[HttpClientProtocol] = None,
        enable_caching: bool = True,
        cache_ttl_seconds: int = 3600,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize enhanced Keycloak client.
        
        Args:
            config: Keycloak configuration provider
            http_client: HTTP client implementation
            enable_caching: Whether to enable token caching
            cache_ttl_seconds: Cache TTL in seconds
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds
        """
        self.config = config or DefaultKeycloakConfig()
        self.http_client = http_client or HttpxHttpClient(
            timeout=self.config.connection_timeout,
            max_connections=self.config.max_connections
        )
        
        # Configuration
        self.enable_caching = enable_caching
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Runtime state
        self._realm_clients: Dict[str, Any] = {}
        self._admin_client: Optional[Any] = None
        self._public_keys: Dict[str, tuple[str, datetime]] = {}
        self._token_cache: Dict[str, tuple[Dict[str, Any], datetime]] = {}
        self._keycloak_available = None
        
        logger.debug(f"Enhanced Keycloak client initialized with server: {self.config.server_url}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self):
        """Close all connections and cleanup resources."""
        if self.http_client:
            await self.http_client.close()
        
        # Clear caches
        self._realm_clients.clear()
        self._public_keys.clear()
        self._token_cache.clear()
        self._admin_client = None
        
        logger.debug("Keycloak client closed and resources cleaned up")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Keycloak server.
        
        Returns:
            Health status information
        """
        try:
            # Try to get server info
            url = f"{self.config.server_url.rstrip('/')}/auth/admin/serverinfo"
            
            start_time = datetime.utcnow()
            response = await self.http_client.get(url)
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return {
                'status': 'healthy',
                'server_url': self.config.server_url,
                'response_time_ms': round(response_time, 2),
                'server_info': response.get('systemInfo', {}),
                'checked_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Keycloak health check failed: {e}")
            return {
                'status': 'unhealthy',
                'server_url': self.config.server_url,
                'error': str(e),
                'checked_at': datetime.utcnow().isoformat()
            }
    
    def _check_keycloak_available(self) -> bool:
        """Check if python-keycloak is available."""
        if self._keycloak_available is None:
            try:
                import keycloak
                self._keycloak_available = True
                logger.debug("python-keycloak library is available")
            except ImportError:
                self._keycloak_available = False
                logger.warning("python-keycloak library not available, using fallback HTTP client")
        return self._keycloak_available
    
    def _get_realm_client(self, realm: str):
        """
        Get or create a KeycloakOpenID client for a specific realm.
        
        Args:
            realm: Realm name
            
        Returns:
            KeycloakOpenID client instance
        """
        if not self._check_keycloak_available():
            raise RuntimeError("python-keycloak library is required but not available")
        
        if realm not in self._realm_clients:
            from keycloak import KeycloakOpenID
            
            self._realm_clients[realm] = KeycloakOpenID(
                server_url=self.config.server_url,
                realm_name=realm,
                client_id=self.config.client_id,
                client_secret_key=self.config.client_secret if self.config.client_secret else None,
                verify=self.config.verify_ssl
            )
            
            logger.debug(f"Created Keycloak client for realm: {realm}")
        
        return self._realm_clients[realm]
    
    async def _get_admin_client(self):
        """
        Get or create an admin client for Keycloak administration.
        
        Returns:
            KeycloakAdmin client instance
        """
        if not self._check_keycloak_available():
            raise RuntimeError("python-keycloak library is required but not available")
        
        if not self._admin_client:
            from keycloak import KeycloakAdmin, KeycloakOpenIDConnection
            
            # Create admin connection
            conn = KeycloakOpenIDConnection(
                server_url=self.config.server_url,
                realm_name="master",
                client_id="admin-cli",
                username=self.config.admin_username,
                password=self.config.admin_password,
                verify=self.config.verify_ssl
            )
            
            self._admin_client = KeycloakAdmin(connection=conn)
            logger.debug("Created Keycloak admin client")
        
        return self._admin_client
    
    async def _retry_operation(self, operation: Callable, *args, **kwargs):
        """
        Retry an operation with exponential backoff.
        
        Args:
            operation: Operation to retry
            *args: Operation arguments
            **kwargs: Operation keyword arguments
            
        Returns:
            Operation result
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.debug(f"Operation failed, retrying in {delay}s (attempt {attempt + 1}/{self.max_retries}): {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Operation failed after {self.max_retries} retries: {e}")
                    break
        
        raise last_exception
    
    def _get_cache_key(self, operation: str, realm: str, identifier: str) -> str:
        """Generate cache key for operations."""
        return f"keycloak:{operation}:{realm}:{identifier}"
    
    def _is_cache_valid(self, cached_data: tuple) -> bool:
        """Check if cached data is still valid."""
        if not self.enable_caching:
            return False
        
        _, expiry = cached_data
        return datetime.utcnow() < expiry
    
    async def authenticate(
        self,
        username: str,
        password: str,
        realm: Optional[str] = None,
        totp: Optional[str] = None,
        scope: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authenticate a user and get tokens with enhanced options.
        
        Args:
            username: Username or email
            password: User password
            realm: Realm name (defaults to admin realm)
            totp: TOTP code for MFA
            scope: OAuth scope
            
        Returns:
            Dict containing access_token, refresh_token, expires_in, etc.
            
        Raises:
            Exception: Authentication failed
        """
        realm = realm or self.config.admin_realm
        
        # Check cache first
        cache_key = self._get_cache_key("auth", realm, username)
        if cache_key in self._token_cache and self._is_cache_valid(self._token_cache[cache_key]):
            logger.debug(f"Returning cached authentication for {username}")
            cached_token, _ = self._token_cache[cache_key]
            return cached_token
        
        client = self._get_realm_client(realm)
        
        try:
            # Prepare authentication parameters
            auth_params = {
                'username': username,
                'password': password
            }
            
            if totp:
                auth_params['totp'] = totp
            if scope:
                auth_params['scope'] = scope
            
            # Authenticate user
            if hasattr(client, 'a_token'):
                # Use async method if available
                token_response = await client.a_token(**auth_params)
            else:
                # Fallback to sync method
                token_response = client.token(**auth_params)
            
            # Add metadata
            token_response['realm'] = realm
            token_response['authenticated_at'] = datetime.utcnow().isoformat()
            token_response['expires_at'] = (
                datetime.utcnow() + timedelta(seconds=token_response.get('expires_in', 300))
            ).isoformat()
            
            # Cache the token if enabled
            if self.enable_caching:
                expiry = datetime.utcnow() + timedelta(seconds=self.cache_ttl_seconds)
                self._token_cache[cache_key] = (token_response, expiry)
            
            logger.info(f"User {username} authenticated successfully in realm {realm}")
            return token_response
            
        except Exception as e:
            # Handle authentication errors
            error_str = str(e).lower()
            if "invalid" in error_str and ("credential" in error_str or "password" in error_str):
                logger.warning(f"Authentication failed for user {username}: Invalid credentials")
                raise Exception("Invalid username or password")
            elif "user not found" in error_str:
                logger.warning(f"Authentication failed for user {username}: User not found")
                raise Exception("User not found")
            elif "account" in error_str and "disabled" in error_str:
                logger.warning(f"Authentication failed for user {username}: Account disabled")
                raise Exception("Account is disabled")
            else:
                logger.error(f"Authentication error for user {username}: {e}")
                raise Exception(f"Authentication failed: {str(e)}")
    
    async def introspect_token(
        self,
        token: str,
        realm: Optional[str] = None,
        token_type_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Introspect a token to check if it's active and get claims with enhanced validation.
        
        Args:
            token: Access token to introspect
            realm: Realm name (defaults to admin realm)
            token_type_hint: Hint about token type
            
        Returns:
            Token introspection response
            
        Raises:
            Exception: Token validation failed
        """
        realm = realm or self.config.admin_realm
        client = self._get_realm_client(realm)
        
        try:
            # Introspect token
            if hasattr(client, 'a_introspect'):
                # Use async method if available
                introspection = await client.a_introspect(token, token_type_hint=token_type_hint)
            else:
                # Fallback to sync method
                introspection = client.introspect(token, token_type_hint=token_type_hint)
            
            if not introspection.get('active', False):
                raise Exception("Token is not active")
            
            # Add additional metadata
            introspection['introspected_at'] = datetime.utcnow().isoformat()
            introspection['realm'] = realm
            
            return introspection
            
        except Exception as e:
            logger.error(f"Token introspection failed: {e}")
            raise Exception(f"Token validation failed: {str(e)}")
    
    async def refresh_token(
        self,
        refresh_token: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refresh an access token using a refresh token with caching.
        
        Args:
            refresh_token: Refresh token
            realm: Realm name (defaults to admin realm)
            
        Returns:
            New token response
            
        Raises:
            Exception: Token refresh failed
        """
        realm = realm or self.config.admin_realm
        client = self._get_realm_client(realm)
        
        try:
            # Refresh the token
            if hasattr(client, 'a_refresh_token'):
                # Use async method if available
                token_response = await client.a_refresh_token(refresh_token)
            else:
                # Fallback to sync method
                token_response = client.refresh_token(refresh_token)
            
            # Add metadata
            token_response['realm'] = realm
            token_response['refreshed_at'] = datetime.utcnow().isoformat()
            token_response['expires_at'] = (
                datetime.utcnow() + timedelta(seconds=token_response.get('expires_in', 300))
            ).isoformat()
            
            logger.info(f"Token refreshed successfully in realm {realm}")
            return token_response
            
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise Exception(f"Token refresh failed: {str(e)}")
    
    async def logout(
        self,
        refresh_token: str,
        realm: Optional[str] = None
    ) -> bool:
        """
        Logout a user session with cache cleanup.
        
        Args:
            refresh_token: Refresh token to revoke
            realm: Realm name (defaults to admin realm)
            
        Returns:
            True if logout successful
        """
        realm = realm or self.config.admin_realm
        client = self._get_realm_client(realm)
        
        try:
            # Logout user
            if hasattr(client, 'a_logout'):
                # Use async method if available
                await client.a_logout(refresh_token)
            else:
                # Fallback to sync method
                client.logout(refresh_token)
            
            # Clear relevant cache entries
            if self.enable_caching:
                keys_to_remove = [key for key in self._token_cache.keys() if realm in key]
                for key in keys_to_remove:
                    del self._token_cache[key]
            
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
        Get user information from token with caching.
        
        Args:
            token: Access token
            realm: Realm name (defaults to admin realm)
            
        Returns:
            User information
            
        Raises:
            Exception: Failed to get user info
        """
        realm = realm or self.config.admin_realm
        
        # Check cache
        cache_key = self._get_cache_key("userinfo", realm, token[:20])  # Use first 20 chars as key
        if cache_key in self._token_cache and self._is_cache_valid(self._token_cache[cache_key]):
            logger.debug("Returning cached user info")
            cached_userinfo, _ = self._token_cache[cache_key]
            return cached_userinfo
        
        client = self._get_realm_client(realm)
        
        try:
            # Get user info
            if hasattr(client, 'a_userinfo'):
                # Use async method if available
                userinfo = await client.a_userinfo(token)
            else:
                # Fallback to sync method
                userinfo = client.userinfo(token)
            
            # Add metadata
            userinfo['retrieved_at'] = datetime.utcnow().isoformat()
            userinfo['realm'] = realm
            
            # Cache the result
            if self.enable_caching:
                expiry = datetime.utcnow() + timedelta(seconds=self.cache_ttl_seconds // 2)  # Shorter TTL for user info
                self._token_cache[cache_key] = (userinfo, expiry)
            
            return userinfo
            
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            raise Exception(f"Failed to get user information: {str(e)}")
    
    async def decode_token(
        self,
        token: str,
        realm: Optional[str] = None,
        validate: bool = True,
        audience: Optional[str] = None,
        leeway: int = 0
    ) -> Dict[str, Any]:
        """
        Decode and optionally validate a JWT token with enhanced options.
        
        Args:
            token: JWT token to decode
            realm: Realm name (defaults to admin realm)
            validate: Whether to validate the token signature
            audience: Expected audience
            leeway: Time leeway for token validation
            
        Returns:
            Decoded token claims
            
        Raises:
            Exception: Token decode failed
        """
        realm = realm or self.config.admin_realm
        client = self._get_realm_client(realm)
        
        try:
            decode_options = {
                'verify_signature': validate,
                'verify_aud': audience is not None,
                'verify_exp': validate,
                'leeway': leeway
            }
            
            if hasattr(client, 'a_decode_token'):
                # Use async method if available
                decoded = await client.a_decode_token(token, **decode_options)
            else:
                # Fallback to sync method
                decoded = client.decode_token(token, **decode_options)
            
            # Add metadata
            decoded['decoded_at'] = datetime.utcnow().isoformat()
            decoded['realm'] = realm
            
            return decoded
            
        except Exception as e:
            # Enhanced error handling
            error_str = str(e).lower()
            if "expired" in error_str:
                logger.warning(f"Token has expired: {e}")
                raise Exception("Token has expired")
            elif "audience" in error_str and "invalid" in error_str:
                logger.warning(f"Token audience validation failed: {e}")
                raise Exception("Token audience validation failed")
            elif "signature" in error_str:
                logger.warning(f"Token signature validation failed: {e}")
                raise Exception("Invalid token signature")
            else:
                logger.error(f"Token decode failed: {e}")
                raise Exception(f"Token decode failed: {str(e)}")
    
    async def get_realm_public_key(
        self,
        realm: Optional[str] = None,
        force_refresh: bool = False
    ) -> str:
        """
        Get the public key for a realm with enhanced caching.
        
        Args:
            realm: Realm name (defaults to admin realm)
            force_refresh: Force refresh the cached key
            
        Returns:
            Public key in PEM format
        """
        realm = realm or self.config.admin_realm
        
        # Check cache
        if not force_refresh and realm in self._public_keys:
            key, expiry = self._public_keys[realm]
            if expiry > datetime.utcnow():
                return key
        
        client = self._get_realm_client(realm)
        
        try:
            # Get public key
            if hasattr(client, 'a_public_key'):
                # Use async method if available
                public_key = await client.a_public_key()
            else:
                # Fallback to sync method
                public_key = client.public_key()
            
            # Format as PEM if needed
            if not public_key.startswith('-----BEGIN'):
                formatted_key = f"-----BEGIN PUBLIC KEY-----\n{public_key}\n-----END PUBLIC KEY-----"
            else:
                formatted_key = public_key
            
            # Cache for 1 hour
            expiry = datetime.utcnow() + timedelta(hours=1)
            self._public_keys[realm] = (formatted_key, expiry)
            
            logger.debug(f"Retrieved and cached public key for realm: {realm}")
            return formatted_key
            
        except Exception as e:
            logger.error(f"Failed to get realm public key: {e}")
            raise Exception(f"Failed to get realm public key: {str(e)}")
    
    # Enhanced Admin Operations
    
    async def create_realm(
        self,
        realm_name: str,
        display_name: Optional[str] = None,
        enabled: bool = True,
        realm_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new realm with enhanced configuration options.
        
        Args:
            realm_name: Unique realm identifier
            display_name: Human-readable realm name
            enabled: Whether realm is enabled
            realm_config: Additional realm configuration
            
        Returns:
            Created realm information
            
        Raises:
            Exception: Realm creation failed
        """
        admin = await self._get_admin_client()
        
        # Default secure realm configuration
        default_config = {
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
            "defaultLocale": "en",
            "accessTokenLifespan": 900,  # 15 minutes
            "ssoSessionIdleTimeout": 1800,  # 30 minutes
            "ssoSessionMaxLifespan": 36000,  # 10 hours
            "offlineSessionIdleTimeout": 2592000,  # 30 days
            "accessCodeLifespan": 60,  # 1 minute
            "accessCodeLifespanUserAction": 300,  # 5 minutes
            "rememberMe": True,
            "verifyEmail": False,
            "loginWithEmailAllowed": True,
            "registrationAllowed": False
        }
        
        # Merge with custom configuration
        if realm_config:
            default_config.update(realm_config)
        
        try:
            # Create realm
            if hasattr(admin, 'a_create_realm'):
                # Use async method if available
                await admin.a_create_realm(default_config)
            else:
                # Fallback to sync method
                admin.create_realm(default_config)
            
            logger.info(f"Created realm: {realm_name}")
            return {
                'realm_name': realm_name,
                'created_at': datetime.utcnow().isoformat(),
                'config': default_config
            }
            
        except Exception as e:
            error_str = str(e)
            if "409" in error_str or "exists" in error_str.lower():
                logger.warning(f"Realm {realm_name} already exists")
                raise Exception(f"Realm {realm_name} already exists")
            else:
                logger.error(f"Failed to create realm {realm_name}: {e}")
                raise Exception(f"Failed to create realm {realm_name}: {str(e)}")
    
    async def get_user_by_username(
        self,
        username: str,
        realm: Optional[str] = None,
        include_attributes: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get user by username with enhanced options.
        
        Args:
            username: Username to search for
            realm: Realm name (defaults to admin realm)
            include_attributes: Whether to include user attributes
            
        Returns:
            User data if found, None otherwise
        """
        realm = realm or self.config.admin_realm
        admin = await self._get_admin_client()
        admin.realm_name = realm
        
        try:
            query_params = {"username": username, "exact": True}
            if include_attributes:
                query_params["briefRepresentation"] = False
            
            # Search for user
            if hasattr(admin, 'a_get_users'):
                # Use async method if available
                users = await admin.a_get_users(query=query_params)
            else:
                # Fallback to sync method
                users = admin.get_users(query=query_params)
            
            if users:
                user = users[0]
                user['retrieved_at'] = datetime.utcnow().isoformat()
                user['realm'] = realm
                return user
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user {username}: {e}")
            return None
    
    async def create_or_update_user(
        self,
        username: str,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        realm: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
        email_verified: bool = True,
        temporary_password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create or update a user with enhanced options.
        
        Args:
            username: Username
            email: Email address
            first_name: First name
            last_name: Last name
            realm: Realm name (defaults to admin realm)
            attributes: Additional user attributes
            enabled: Whether user is enabled
            email_verified: Whether email is verified
            temporary_password: Temporary password for new users
            
        Returns:
            User data
        """
        realm = realm or self.config.admin_realm
        admin = await self._get_admin_client()
        admin.realm_name = realm
        
        # Check if user exists
        existing_user = await self.get_user_by_username(username, realm)
        
        user_data = {
            "username": username,
            "email": email,
            "firstName": first_name or "",
            "lastName": last_name or "",
            "enabled": enabled,
            "emailVerified": email_verified,
            "attributes": attributes or {}
        }
        
        try:
            if existing_user:
                # Update existing user
                user_id = existing_user["id"]
                
                if hasattr(admin, 'a_update_user'):
                    # Use async method if available
                    await admin.a_update_user(user_id, user_data)
                else:
                    # Fallback to sync method
                    admin.update_user(user_id, user_data)
                
                logger.info(f"Updated user {username} in realm {realm}")
                user_data["id"] = user_id
                user_data["updated_at"] = datetime.utcnow().isoformat()
                
            else:
                # Create new user
                if hasattr(admin, 'a_create_user'):
                    # Use async method if available
                    user_id = await admin.a_create_user(user_data)
                else:
                    # Fallback to sync method
                    user_id = admin.create_user(user_data)
                
                logger.info(f"Created user {username} in realm {realm}")
                user_data["id"] = user_id
                user_data["created_at"] = datetime.utcnow().isoformat()
                
                # Set temporary password if provided
                if temporary_password:
                    await self.set_user_password(user_id, temporary_password, realm=realm, temporary=True)
            
            user_data["realm"] = realm
            return user_data
            
        except Exception as e:
            logger.error(f"Failed to create/update user {username}: {e}")
            raise Exception(f"Failed to manage user {username}: {str(e)}")
    
    async def set_user_password(
        self,
        user_id: str,
        password: str,
        realm: Optional[str] = None,
        temporary: bool = True
    ) -> bool:
        """
        Set user password with enhanced options.
        
        Args:
            user_id: User ID
            password: New password
            realm: Realm name (defaults to admin realm)
            temporary: Whether password is temporary
            
        Returns:
            True if password set successfully
        """
        realm = realm or self.config.admin_realm
        admin = await self._get_admin_client()
        admin.realm_name = realm
        
        try:
            password_data = {
                "type": "password",
                "value": password,
                "temporary": temporary
            }
            
            if hasattr(admin, 'a_set_user_password'):
                # Use async method if available
                await admin.a_set_user_password(user_id, password_data)
            else:
                # Fallback to sync method
                admin.set_user_password(user_id, password_data)
            
            logger.info(f"Set password for user {user_id} in realm {realm}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set password for user {user_id}: {e}")
            return False
    
    async def get_client_statistics(self) -> Dict[str, Any]:
        """
        Get client usage statistics and metrics.
        
        Returns:
            Statistics about client usage
        """
        return {
            'realms_cached': len(self._realm_clients),
            'public_keys_cached': len(self._public_keys),
            'tokens_cached': len(self._token_cache),
            'cache_enabled': self.enable_caching,
            'cache_ttl_seconds': self.cache_ttl_seconds,
            'max_retries': self.max_retries,
            'keycloak_available': self._check_keycloak_available(),
            'server_url': self.config.server_url,
            'admin_realm': self.config.admin_realm,
            'statistics_generated_at': datetime.utcnow().isoformat()
        }
    
    async def clear_cache(self, cache_type: Optional[str] = None):
        """
        Clear specific or all caches.
        
        Args:
            cache_type: Type of cache to clear ('tokens', 'keys', 'all')
        """
        if cache_type == 'tokens' or cache_type == 'all':
            self._token_cache.clear()
            logger.info("Cleared token cache")
        
        if cache_type == 'keys' or cache_type == 'all':
            self._public_keys.clear()
            logger.info("Cleared public keys cache")
        
        if cache_type == 'clients' or cache_type == 'all':
            self._realm_clients.clear()
            self._admin_client = None
            logger.info("Cleared client cache")
        
        if cache_type is None or cache_type == 'all':
            self._token_cache.clear()
            self._public_keys.clear()
            logger.info("Cleared all caches")


# =============================================================================
# FACTORY FUNCTIONS AND CONVENIENCE UTILITIES
# =============================================================================

def create_keycloak_client(
    server_url: Optional[str] = None,
    admin_realm: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    admin_username: Optional[str] = None,
    admin_password: Optional[str] = None,
    enable_caching: bool = True,
    **kwargs
) -> EnhancedKeycloakAsyncClient:
    """
    Create a configured Keycloak client with default settings.
    
    Args:
        server_url: Keycloak server URL
        admin_realm: Admin realm name
        client_id: Client ID
        client_secret: Client secret
        admin_username: Admin username
        admin_password: Admin password
        enable_caching: Whether to enable caching
        **kwargs: Additional configuration options
        
    Returns:
        Configured Keycloak client
    """
    config = DefaultKeycloakConfig(
        server_url=server_url,
        admin_realm=admin_realm,
        client_id=client_id,
        client_secret=client_secret,
        admin_username=admin_username,
        admin_password=admin_password,
        **{k: v for k, v in kwargs.items() if k in ['connection_timeout', 'max_connections', 'verify_ssl']}
    )
    
    client_kwargs = {k: v for k, v in kwargs.items() if k not in ['connection_timeout', 'max_connections', 'verify_ssl']}
    
    return EnhancedKeycloakAsyncClient(
        config=config,
        enable_caching=enable_caching,
        **client_kwargs
    )


@asynccontextmanager
async def keycloak_client_context(
    server_url: Optional[str] = None,
    **kwargs
) -> EnhancedKeycloakAsyncClient:
    """
    Async context manager for Keycloak client.
    
    Args:
        server_url: Keycloak server URL
        **kwargs: Additional configuration options
        
    Yields:
        Configured Keycloak client
    """
    client = create_keycloak_client(server_url=server_url, **kwargs)
    try:
        yield client
    finally:
        await client.close()


# Global client instance for singleton pattern
_global_client: Optional[EnhancedKeycloakAsyncClient] = None


def get_global_keycloak_client(**config_overrides) -> EnhancedKeycloakAsyncClient:
    """
    Get or create a global Keycloak client instance (singleton pattern).
    
    Args:
        **config_overrides: Configuration overrides
        
    Returns:
        Global Keycloak client instance
    """
    global _global_client
    
    if _global_client is None:
        _global_client = create_keycloak_client(**config_overrides)
        logger.debug("Created global Keycloak client instance")
    
    return _global_client


async def reset_global_client():
    """Reset the global client instance."""
    global _global_client
    
    if _global_client:
        await _global_client.close()
        _global_client = None
        logger.debug("Reset global Keycloak client instance")


# Utility functions for common operations

async def quick_authenticate(
    username: str,
    password: str,
    server_url: Optional[str] = None,
    realm: Optional[str] = None,
    **client_config
) -> Dict[str, Any]:
    """
    Quick authentication helper function.
    
    Args:
        username: Username
        password: Password
        server_url: Keycloak server URL
        realm: Realm name
        **client_config: Additional client configuration
        
    Returns:
        Authentication response
    """
    async with keycloak_client_context(server_url=server_url, **client_config) as client:
        return await client.authenticate(username, password, realm=realm)


async def quick_token_validation(
    token: str,
    server_url: Optional[str] = None,
    realm: Optional[str] = None,
    **client_config
) -> Dict[str, Any]:
    """
    Quick token validation helper function.
    
    Args:
        token: Token to validate
        server_url: Keycloak server URL
        realm: Realm name
        **client_config: Additional client configuration
        
    Returns:
        Token validation response
    """
    async with keycloak_client_context(server_url=server_url, **client_config) as client:
        return await client.introspect_token(token, realm=realm)


async def quick_user_info(
    token: str,
    server_url: Optional[str] = None,
    realm: Optional[str] = None,
    **client_config
) -> Dict[str, Any]:
    """
    Quick user info retrieval helper function.
    
    Args:
        token: Access token
        server_url: Keycloak server URL
        realm: Realm name
        **client_config: Additional client configuration
        
    Returns:
        User information
    """
    async with keycloak_client_context(server_url=server_url, **client_config) as client:
        return await client.get_userinfo(token, realm=realm)