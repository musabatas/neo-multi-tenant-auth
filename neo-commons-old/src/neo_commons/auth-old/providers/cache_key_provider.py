"""
Cache Key Provider Implementation

Provides service-namespaced cache key generation for multi-service deployments.
Supports tenant isolation and prevents cache conflicts between services.
"""

from typing import Optional
from ..protocols import CacheKeyProviderProtocol


class DefaultCacheKeyProvider:
    """
    Default cache key provider with service namespacing.
    
    Generates cache keys with consistent patterns and service isolation.
    """
    
    def __init__(self, service_name: str = "neocommons"):
        """
        Initialize cache key provider.
        
        Args:
            service_name: Service name for cache key namespacing
        """
        self.service_name = service_name
    
    def get_token_cache_key(self, user_id: str, session_id: str) -> str:
        """Generate cache key for user tokens."""
        return f"{self.service_name}:auth:token:{user_id}:{session_id}"
    
    def get_introspection_cache_key(self, token_hash: str) -> str:
        """Generate cache key for token introspection results."""
        return f"{self.service_name}:auth:introspect:{token_hash}"
    
    def get_public_key_cache_key(self, realm: str) -> str:
        """Generate cache key for realm public keys."""
        return f"{self.service_name}:auth:realm:{realm}:public_key"
    
    def get_permission_cache_key(self, user_id: str, tenant_id: Optional[str] = None) -> str:
        """Generate cache key for user permissions."""
        if tenant_id:
            return f"{self.service_name}:auth:perms:{tenant_id}:{user_id}"
        return f"{self.service_name}:auth:perms:platform:{user_id}"
    
    def get_revocation_cache_key(self, token_hash: str) -> str:
        """Generate cache key for revoked tokens."""
        return f"{self.service_name}:auth:revoked:{token_hash}"


class AdminCacheKeyProvider(DefaultCacheKeyProvider):
    """Cache key provider for admin service with platform-specific patterns."""
    
    def __init__(self):
        super().__init__(service_name="admin")
    
    def get_permission_cache_key(self, user_id: str, tenant_id: Optional[str] = None) -> str:
        """Admin service uses platform permissions by default."""
        return f"{self.service_name}:auth:perms:platform:{user_id}"


class TenantCacheKeyProvider(DefaultCacheKeyProvider):
    """Cache key provider for tenant service with tenant-specific patterns."""
    
    def __init__(self):
        super().__init__(service_name="tenant")
    
    def get_permission_cache_key(self, user_id: str, tenant_id: Optional[str] = None) -> str:
        """Tenant service requires tenant_id for all permission caching."""
        if not tenant_id:
            raise ValueError("tenant_id is required for tenant service permission caching")
        return f"{self.service_name}:auth:perms:{tenant_id}:{user_id}"