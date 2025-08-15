"""
Configuration implementations for Keycloak integration.

Provides default configuration and HTTP client implementations.
"""
import logging
import os
from typing import Optional, Dict, Any
import httpx

from ..protocols.protocols import KeycloakConfigProtocol, HttpClientProtocol

logger = logging.getLogger(__name__)


class DefaultKeycloakConfig(KeycloakConfigProtocol):
    """
    Default Keycloak configuration implementation with environment variable support.
    
    Provides flexible configuration with multiple fallback mechanisms.
    """
    
    def __init__(
        self,
        server_url: Optional[str] = None,
        admin_realm: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        admin_username: Optional[str] = None,
        admin_password: Optional[str] = None,
        connection_timeout: Optional[int] = None,
        max_connections: Optional[int] = None,
        verify_ssl: Optional[bool] = None
    ):
        """Initialize configuration with explicit values or environment fallbacks."""
        self._server_url = server_url
        self._admin_realm = admin_realm
        self._client_id = client_id
        self._client_secret = client_secret
        self._admin_username = admin_username
        self._admin_password = admin_password
        self._connection_timeout = connection_timeout
        self._max_connections = max_connections
        self._verify_ssl = verify_ssl
        
        # Log configuration status
        self._log_config_status()
    
    def _log_config_status(self):
        """Log configuration status without sensitive data."""
        config_sources = {
            'server_url': 'explicit' if self._server_url else 'env',
            'admin_realm': 'explicit' if self._admin_realm else 'env',
            'client_id': 'explicit' if self._client_id else 'env',
            'client_secret': 'explicit' if self._client_secret else 'env',
            'admin_username': 'explicit' if self._admin_username else 'env',
            'admin_password': 'explicit' if self._admin_password else 'env'
        }
        
        logger.info(f"Keycloak config initialized with sources: {config_sources}")
        
        # Warn about missing critical configuration
        missing_config = []
        if not self.server_url:
            missing_config.append('server_url')
        if not self.client_id:
            missing_config.append('client_id')
        if not self.client_secret:
            missing_config.append('client_secret')
        
        if missing_config:
            logger.warning(
                f"Missing Keycloak configuration: {missing_config}. "
                "Some operations may fail without proper configuration."
            )
    
    @property
    def server_url(self) -> str:
        """Keycloak server URL."""
        url = self._server_url or os.getenv(
            "KEYCLOAK_SERVER_URL", 
            os.getenv("KEYCLOAK_URL", "")
        )
        # Ensure no trailing slash
        return url.rstrip('/') if url else ""
    
    @property
    def admin_realm(self) -> str:
        """Admin realm name."""
        return self._admin_realm or os.getenv(
            "KEYCLOAK_ADMIN_REALM", 
            os.getenv("KEYCLOAK_REALM", "master")
        )
    
    @property
    def client_id(self) -> str:
        """Client ID for authentication."""
        return self._client_id or os.getenv(
            "KEYCLOAK_CLIENT_ID", 
            os.getenv("KEYCLOAK_ADMIN_CLIENT_ID", "")
        )
    
    @property
    def client_secret(self) -> str:
        """Client secret for authentication."""
        return self._client_secret or os.getenv(
            "KEYCLOAK_CLIENT_SECRET", 
            os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET", "")
        )
    
    @property
    def admin_username(self) -> Optional[str]:
        """Admin username for admin operations."""
        return self._admin_username or os.getenv(
            "KEYCLOAK_ADMIN_USERNAME", 
            os.getenv("KEYCLOAK_ADMIN", None)
        )
    
    @property
    def admin_password(self) -> Optional[str]:
        """Admin password for admin operations."""
        return self._admin_password or os.getenv(
            "KEYCLOAK_ADMIN_PASSWORD", 
            None
        )
    
    @property
    def connection_timeout(self) -> int:
        """Connection timeout in seconds."""
        if self._connection_timeout is not None:
            return self._connection_timeout
        return int(os.getenv("KEYCLOAK_CONNECTION_TIMEOUT", "30"))
    
    @property
    def max_connections(self) -> int:
        """Maximum number of connections."""
        if self._max_connections is not None:
            return self._max_connections
        return int(os.getenv("KEYCLOAK_MAX_CONNECTIONS", "100"))
    
    @property
    def verify_ssl(self) -> bool:
        """Whether to verify SSL certificates."""
        if self._verify_ssl is not None:
            return self._verify_ssl
        return os.getenv("KEYCLOAK_VERIFY_SSL", "true").lower() == "true"
    
    def is_fully_configured(self) -> bool:
        """Check if all required configuration is present."""
        required_fields = [self.server_url, self.client_id, self.client_secret]
        return all(field.strip() for field in required_fields if field)
    
    def get_auth_url(self, realm: Optional[str] = None) -> str:
        """Get authentication URL for realm."""
        realm = realm or self.admin_realm
        return f"{self.server_url}/realms/{realm}/protocol/openid-connect/auth"
    
    def get_token_url(self, realm: Optional[str] = None) -> str:
        """Get token endpoint URL for realm."""
        realm = realm or self.admin_realm
        return f"{self.server_url}/realms/{realm}/protocol/openid-connect/token"
    
    def get_userinfo_url(self, realm: Optional[str] = None) -> str:
        """Get userinfo endpoint URL for realm."""
        realm = realm or self.admin_realm
        return f"{self.server_url}/realms/{realm}/protocol/openid-connect/userinfo"
    
    def get_admin_url(self, path: str = "") -> str:
        """Get admin API URL."""
        base_url = f"{self.server_url}/admin/realms"
        return f"{base_url}/{path.lstrip('/')}" if path else base_url


class HttpxHttpClient(HttpClientProtocol):
    """
    HTTP client implementation using httpx with async support.
    
    Provides connection pooling, timeouts, and proper resource management.
    """
    
    def __init__(
        self, 
        timeout: int = 30,
        max_connections: int = 100,
        verify_ssl: bool = True
    ):
        """Initialize httpx client with configuration."""
        self.timeout = timeout
        self.max_connections = max_connections
        self.verify_ssl = verify_ssl
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info(
            f"HttpxHttpClient initialized: timeout={timeout}s, "
            f"max_connections={max_connections}, verify_ssl={verify_ssl}"
        )
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create httpx client."""
        if self._client is None:
            limits = httpx.Limits(
                max_connections=self.max_connections,
                max_keepalive_connections=self.max_connections // 2
            )
            
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=limits,
                verify=self.verify_ssl,
                follow_redirects=True
            )
            logger.debug("Created new httpx AsyncClient")
        
        return self._client
    
    async def get(
        self, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make GET request."""
        client = await self._get_client()
        
        try:
            response = await client.get(
                url, 
                headers=headers,
                params=params,
                **kwargs
            )
            response.raise_for_status()
            
            # Handle different content types
            content_type = response.headers.get('content-type', '').lower()
            if 'application/json' in content_type:
                return response.json()
            else:
                return {'content': response.text, 'status_code': response.status_code}
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP GET error for {url}: {e}")
            raise
    
    async def post(
        self, 
        url: str, 
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make POST request."""
        client = await self._get_client()
        
        try:
            # Determine content type and prepare data
            if headers and headers.get('content-type') == 'application/x-www-form-urlencoded':
                response = await client.post(url, data=data, headers=headers, **kwargs)
            else:
                response = await client.post(url, json=data, headers=headers, **kwargs)
            
            response.raise_for_status()
            
            # Handle different content types
            content_type = response.headers.get('content-type', '').lower()
            if 'application/json' in content_type:
                return response.json()
            else:
                return {'content': response.text, 'status_code': response.status_code}
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP POST error for {url}: {e}")
            raise
    
    async def put(
        self, 
        url: str, 
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make PUT request."""
        client = await self._get_client()
        
        try:
            response = await client.put(url, json=data, headers=headers, **kwargs)
            response.raise_for_status()
            
            # Handle different content types
            content_type = response.headers.get('content-type', '').lower()
            if 'application/json' in content_type:
                return response.json()
            else:
                return {'content': response.text, 'status_code': response.status_code}
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP PUT error for {url}: {e}")
            raise
    
    async def delete(
        self, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make DELETE request."""
        client = await self._get_client()
        
        try:
            response = await client.delete(url, headers=headers, **kwargs)
            response.raise_for_status()
            
            return {'status_code': response.status_code, 'success': True}
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP DELETE error for {url}: {e}")
            raise
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug("HttpxHttpClient closed")