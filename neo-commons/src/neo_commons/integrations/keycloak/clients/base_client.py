"""
Base Keycloak client with core functionality.

Provides common functionality for all Keycloak operations.
"""
import logging
import asyncio
from typing import Optional, Dict, Any, Callable, Tuple
from datetime import datetime, timedelta
from functools import lru_cache
from contextlib import asynccontextmanager

from ..protocols.protocols import KeycloakConfigProtocol, HttpClientProtocol
from ..config.config import DefaultKeycloakConfig, HttpxHttpClient

logger = logging.getLogger(__name__)


class BaseKeycloakClient:
    """
    Base Keycloak client with core functionality.
    
    Provides caching, retry logic, and common operations.
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
        """Initialize base client."""
        self.config = config or DefaultKeycloakConfig()
        self.http_client = http_client or HttpxHttpClient(
            timeout=self.config.connection_timeout,
            max_connections=self.config.max_connections,
            verify_ssl=self.config.verify_ssl
        )
        
        # Configuration
        self.enable_caching = enable_caching
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Internal state
        self._token_cache: Dict[str, Tuple[datetime, Dict[str, Any]]] = {}
        self._realm_clients: Dict[str, Any] = {}
        self._admin_client = None
        self._is_closed = False
        
        logger.info("BaseKeycloakClient initialized")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self):
        """Close the client and clean up resources."""
        if not self._is_closed:
            logger.info("Closing BaseKeycloakClient...")
            
            # Close HTTP client
            await self.http_client.close()
            
            # Clear caches
            self._token_cache.clear()
            self._realm_clients.clear()
            self._admin_client = None
            
            self._is_closed = True
            logger.info("BaseKeycloakClient closed")
    
    def _check_keycloak_available(self) -> bool:
        """Check if Keycloak is properly configured."""
        if not self.config.server_url:
            logger.warning("Keycloak server URL not configured")
            return False
        
        if not self.config.client_id:
            logger.warning("Keycloak client ID not configured")
            return False
        
        if not self.config.client_secret:
            logger.warning("Keycloak client secret not configured")
            return False
        
        return True
    
    @lru_cache(maxsize=10)
    def _get_realm_client(self, realm: str):
        """Get or create realm client with caching."""
        if not self._check_keycloak_available():
            return None
        
        if realm not in self._realm_clients:
            try:
                from keycloak import KeycloakOpenID
                
                client = KeycloakOpenID(
                    server_url=self.config.server_url,
                    client_id=self.config.client_id,
                    realm_name=realm,
                    client_secret_key=self.config.client_secret,
                    verify=self.config.verify_ssl
                )
                
                self._realm_clients[realm] = client
                logger.debug(f"Created realm client for {realm}")
                
            except Exception as e:
                logger.error(f"Failed to create realm client for {realm}: {e}")
                return None
        
        return self._realm_clients.get(realm)
    
    async def _get_admin_client(self):
        """Get or create admin client."""
        if not self._check_keycloak_available():
            return None
        
        if self._admin_client is None:
            try:
                from keycloak import KeycloakAdmin
                
                # Try username/password first
                if self.config.admin_username and self.config.admin_password:
                    self._admin_client = KeycloakAdmin(
                        server_url=self.config.server_url,
                        username=self.config.admin_username,
                        password=self.config.admin_password,
                        realm_name=self.config.admin_realm,
                        verify=self.config.verify_ssl
                    )
                else:
                    # Fall back to client credentials
                    self._admin_client = KeycloakAdmin(
                        server_url=self.config.server_url,
                        client_id=self.config.client_id,
                        client_secret_key=self.config.client_secret,
                        realm_name=self.config.admin_realm,
                        verify=self.config.verify_ssl
                    )
                
                logger.debug("Created admin client")
                
            except Exception as e:
                logger.error(f"Failed to create admin client: {e}")
                return None
        
        return self._admin_client
    
    async def _retry_operation(self, operation: Callable, *args, **kwargs):
        """Retry operation with exponential backoff."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(operation):
                    return await operation(*args, **kwargs)
                else:
                    return operation(*args, **kwargs)
                    
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Operation failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Operation failed after {self.max_retries + 1} attempts: {e}")
        
        raise last_exception
    
    def _get_cache_key(self, operation: str, realm: str, identifier: str) -> str:
        """Generate cache key for operation."""
        return f"{operation}:{realm}:{identifier}"
    
    def _is_cache_valid(self, cached_data: tuple) -> bool:
        """Check if cached data is still valid."""
        if not cached_data or len(cached_data) != 2:
            return False
        
        timestamp, data = cached_data
        return datetime.now() < timestamp + timedelta(seconds=self.cache_ttl_seconds)
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache if valid."""
        if not self.enable_caching:
            return None
        
        cached_data = self._token_cache.get(cache_key)
        if cached_data and self._is_cache_valid(cached_data):
            logger.debug(f"Cache hit for {cache_key}")
            return cached_data[1]
        
        # Clean up expired cache entry
        if cached_data:
            del self._token_cache[cache_key]
        
        return None
    
    def _set_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """Set data in cache with timestamp."""
        if self.enable_caching:
            self._token_cache[cache_key] = (datetime.now(), data)
            logger.debug(f"Cached data for {cache_key}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Keycloak health and configuration."""
        health_status = {
            "keycloak_available": False,
            "configuration_valid": False,
            "admin_client_ready": False,
            "server_url": self.config.server_url,
            "admin_realm": self.config.admin_realm,
            "client_configured": bool(self.config.client_id),
            "timestamp": datetime.now().isoformat(),
            "errors": []
        }
        
        try:
            # Check configuration
            if not self._check_keycloak_available():
                health_status["errors"].append("Keycloak not properly configured")
                return health_status
            
            health_status["configuration_valid"] = True
            
            # Test server connectivity
            test_url = f"{self.config.server_url}/realms/{self.config.admin_realm}"
            try:
                await self.http_client.get(test_url)
                health_status["keycloak_available"] = True
            except Exception as e:
                health_status["errors"].append(f"Server not reachable: {e}")
                return health_status
            
            # Test admin client
            try:
                admin_client = await self._get_admin_client()
                if admin_client:
                    health_status["admin_client_ready"] = True
                else:
                    health_status["errors"].append("Admin client creation failed")
            except Exception as e:
                health_status["errors"].append(f"Admin client error: {e}")
            
        except Exception as e:
            health_status["errors"].append(f"Health check failed: {e}")
            logger.error(f"Health check error: {e}")
        
        return health_status
    
    async def clear_cache(self, cache_type: Optional[str] = None) -> bool:
        """Clear client cache."""
        try:
            if cache_type == "tokens" or cache_type is None:
                self._token_cache.clear()
                logger.info("Token cache cleared")
            
            if cache_type == "clients" or cache_type is None:
                self._realm_clients.clear()
                self._admin_client = None
                logger.info("Client cache cleared")
            
            return True
            
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
            return False