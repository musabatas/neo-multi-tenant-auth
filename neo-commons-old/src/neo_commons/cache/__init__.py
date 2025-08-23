"""
Cache layer utilities for the NeoMultiTenant platform.

This module provides enterprise-grade caching patterns with:
- Tenant-aware cache isolation for multi-tenancy
- Redis-based high-performance caching with connection pooling
- Automatic cache invalidation strategies
- Type-safe cache operations with protocol-based design
- TTL management and expiration handling

Quick Start:
    # Basic caching
    from neo_commons.cache import CacheManager
    
    cache = CacheManager.create_redis_cache()
    
    # Simple get/set operations
    await cache.set("user:123", user_data, ttl=300)
    user = await cache.get("user:123")
    
    # Tenant-aware caching
    from neo_commons.cache import TenantAwareCacheService
    
    tenant_cache = TenantAwareCacheService(cache, tenant_id="tenant-123")
    
    # Automatically prefixes keys with tenant context
    await tenant_cache.set("permissions:user:456", permissions, ttl=60)
    permissions = await tenant_cache.get("permissions:user:456")
    
    # Cache patterns with invalidation
    from neo_commons.cache.implementations import CacheServiceAdapter
    
    @cache_adapter.cached(key="user:{user_id}", ttl=300)
    async def get_user(user_id: str):
        return await database.fetch_user(user_id)
    
    # Invalidate related caches
    await cache_adapter.invalidate_pattern("user:*")

Caching Strategies:
    - Write-through: Data written to cache and database simultaneously
    - Write-behind: Data written to cache immediately, database asynchronously  
    - Cache-aside: Application manages cache population and invalidation
    - TTL-based: Automatic expiration for time-sensitive data
    - Tag-based: Group-based invalidation using cache tags

Performance Features:
    - Connection pooling for Redis with configurable pool sizes
    - Pipelining for batch operations to reduce network overhead
    - Compression for large values to optimize memory usage
    - Tenant isolation to prevent cache key collisions
    - Metrics collection for cache hit/miss ratios and performance monitoring
"""

from .client import CacheManager, CacheConfig
from .protocols import TenantAwareCacheProtocol, CacheManagerProtocol
from .implementations import TenantAwareCacheService

__all__ = [
    "CacheManager", 
    "CacheConfig",
    "TenantAwareCacheProtocol",
    "CacheManagerProtocol", 
    "TenantAwareCacheService",
]