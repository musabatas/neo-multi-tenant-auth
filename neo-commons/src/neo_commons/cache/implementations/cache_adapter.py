"""
Cache Service Adapter for Protocol Compatibility

Provides compatibility between TenantAwareCacheService and the basic CacheServiceProtocol
used by neo-commons auth wrappers.
"""

from typing import Any, Optional
from loguru import logger

from ..protocols import TenantAwareCacheProtocol
from ...auth.protocols import CacheServiceProtocol


class CacheServiceAdapter:
    """
    Adapter to make TenantAwareCacheService compatible with CacheServiceProtocol.
    
    This adapter bridges the gap between the tenant-aware cache service 
    and the simpler cache protocol expected by auth wrappers.
    """
    
    def __init__(self, tenant_aware_cache: TenantAwareCacheProtocol, default_tenant_id: Optional[str] = None):
        """
        Initialize the cache adapter.
        
        Args:
            tenant_aware_cache: The tenant-aware cache service instance
            default_tenant_id: Optional default tenant ID for all operations
        """
        self.cache = tenant_aware_cache
        self.default_tenant_id = default_tenant_id
    
    async def get(self, key: str) -> Any:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        return await self.cache.get(key, tenant_id=self.default_tenant_id)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        ttl = ttl or 3600  # Default TTL
        await self.cache.set(key, value, tenant_id=self.default_tenant_id, ttl=ttl)
    
    async def delete(self, key: str) -> None:
        """
        Delete value from cache.
        
        Args:
            key: Cache key to delete
        """
        await self.cache.delete(key, tenant_id=self.default_tenant_id)
    
    async def health_check(self) -> bool:
        """
        Check cache service health.
        
        Returns:
            True if cache is healthy
        """
        return await self.cache.health_check()


def create_cache_adapter(
    tenant_aware_cache: TenantAwareCacheProtocol, 
    default_tenant_id: Optional[str] = None
) -> CacheServiceAdapter:
    """
    Create a cache service adapter for protocol compatibility.
    
    Args:
        tenant_aware_cache: The tenant-aware cache service instance
        default_tenant_id: Optional default tenant ID for all operations
        
    Returns:
        Configured CacheServiceAdapter instance
    """
    return CacheServiceAdapter(tenant_aware_cache, default_tenant_id)