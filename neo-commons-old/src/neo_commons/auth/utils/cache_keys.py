"""
Cache Key Provider Implementation for Neo-Commons

Provides service-namespaced cache key generation for multi-service deployments.
Supports tenant isolation and prevents cache conflicts between services.
"""

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class CacheKeyProviderProtocol(Protocol):
    """Protocol for cache key generation."""
    
    def get_token_cache_key(self, user_id: str, session_id: str) -> str:
        """Generate cache key for user tokens."""
        ...
    
    def get_introspection_cache_key(self, token_hash: str) -> str:
        """Generate cache key for token introspection results."""
        ...
    
    def get_public_key_cache_key(self, realm: str) -> str:
        """Generate cache key for realm public keys."""
        ...
    
    def get_permission_cache_key(self, user_id: str, tenant_id: Optional[str] = None) -> str:
        """Generate cache key for user permissions."""
        ...
    
    def get_revocation_cache_key(self, token_hash: str) -> str:
        """Generate cache key for revoked tokens."""
        ...


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
    
    def get_realm_public_key_cache_key(self, realm: str) -> str:
        """Generate cache key for realm public keys (alias for compatibility)."""
        return self.get_public_key_cache_key(realm)
    
    def get_permission_cache_key(self, user_id: str, tenant_id: Optional[str] = None) -> str:
        """Generate cache key for user permissions."""
        if tenant_id:
            return f"{self.service_name}:auth:perms:{tenant_id}:{user_id}"
        return f"{self.service_name}:auth:perms:platform:{user_id}"
    
    def get_revocation_cache_key(self, token_hash: str) -> str:
        """Generate cache key for revoked tokens."""
        return f"{self.service_name}:auth:revoked:{token_hash}"
    
    def get_token_validation_key(self, token_hash: str, realm: str) -> str:
        """Generate cache key for token validation results."""
        return f"{self.service_name}:auth:validation:{realm}:{token_hash}"
    
    def get_session_cache_key(self, session_id: str, session_type: str = "guest") -> str:
        """Generate cache key for session data."""
        return f"{self.service_name}:session:{session_type}:{session_id}"
    
    def get_user_identity_cache_key(self, external_id: str, provider: str = "keycloak") -> str:
        """Generate cache key for user identity mapping."""
        return f"{self.service_name}:identity:{provider}:{external_id}"


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


# Factory function for dependency injection
def create_cache_key_provider(service_name: str = "neocommons") -> DefaultCacheKeyProvider:
    """
    Create a cache key provider instance.
    
    Args:
        service_name: Service name for cache key namespacing
        
    Returns:
        Configured DefaultCacheKeyProvider instance
    """
    return DefaultCacheKeyProvider(service_name=service_name)


def create_admin_cache_key_provider() -> AdminCacheKeyProvider:
    """Create an admin-specific cache key provider."""
    return AdminCacheKeyProvider()


def create_tenant_cache_key_provider() -> TenantCacheKeyProvider:
    """Create a tenant-specific cache key provider."""
    return TenantCacheKeyProvider()


__all__ = [
    "CacheKeyProviderProtocol",
    "DefaultCacheKeyProvider",
    "AdminCacheKeyProvider",
    "TenantCacheKeyProvider",
    "create_cache_key_provider",
    "create_admin_cache_key_provider",
    "create_tenant_cache_key_provider",
]