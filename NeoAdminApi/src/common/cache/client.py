"""
Redis cache client and utilities.

MIGRATED TO NEO-COMMONS: Now using neo-commons CacheService with NeoAdminApi-specific extensions.
Import compatibility maintained - all existing imports continue to work.
"""
from typing import Optional, Any, Union, List, Dict
from loguru import logger

from src.common.config.settings import settings

# NEO-COMMONS IMPORT: Use neo-commons CacheService as base
from neo_commons.cache.client import CacheManager as NeoCommonsCacheManager


class CacheManager(NeoCommonsCacheManager):
    """
    NeoAdminApi cache manager extending neo-commons CacheService.
    
    Maintains backward compatibility while leveraging neo-commons infrastructure.
    Adds NeoAdminApi-specific features like metadata tracking and specialized TTLs.
    """
    
    def __init__(self):
        """Initialize with NeoAdminApi-specific settings."""
        # Initialize neo-commons CacheService with NeoAdminApi settings
        redis_url = str(settings.redis_url) if settings.redis_url else None
        super().__init__(
            redis_url=redis_url,
            pool_size=settings.cache_pool_size,
            decode_responses=settings.cache_decode_responses,
            key_prefix=settings.get_cache_key_prefix,
            default_ttl=settings.cache_ttl_default
        )
    
    async def get(
        self, 
        key: str, 
        namespace: Optional[str] = None,
        deserialize: bool = True
    ) -> Optional[Any]:
        """Get value from cache with NeoAdminApi metadata tracking."""
        # Use neo-commons get method
        result = await super().get(key, namespace=namespace)
        
        # Track cache operation for NeoAdminApi metadata
        try:
            from src.common.utils.metadata import track_cache_operation
            if result is None:
                track_cache_operation('miss')
            else:
                track_cache_operation('hit')
        except ImportError:
            pass  # Metadata system not available
        
        return result
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: Optional[str] = None,
        serialize: bool = True
    ) -> bool:
        """Set value in cache with NeoAdminApi metadata tracking."""
        # Use NeoAdminApi-specific TTLs if not specified
        if ttl is None:
            ttl = settings.cache_ttl_default
        
        # Use neo-commons set method
        result = await super().set(key, value, namespace=namespace, ttl=ttl)
        
        # Track cache set operation for NeoAdminApi metadata
        try:
            from src.common.utils.metadata import track_cache_operation
            track_cache_operation('set')
        except ImportError:
            pass  # Metadata system not available
        
        return result
    
    async def delete(self, key: str, namespace: Optional[str] = None) -> bool:
        """Delete value from cache using neo-commons."""
        return await super().delete(key, namespace=namespace)
    
    async def delete_pattern(self, pattern: str, namespace: Optional[str] = None) -> int:
        """Delete all keys matching a pattern using neo-commons."""
        return await super().delete_pattern(pattern, namespace=namespace)
    
    async def exists(self, key: str, namespace: Optional[str] = None) -> bool:
        """Check if key exists in cache using neo-commons."""
        return await super().exists(key, namespace=namespace)
    
    async def expire(
        self, 
        key: str, 
        ttl: int, 
        namespace: Optional[str] = None
    ) -> bool:
        """Set expiration time for a key using neo-commons."""
        return await super().expire(key, ttl, namespace=namespace)
    
    async def increment(
        self, 
        key: str, 
        amount: int = 1,
        namespace: Optional[str] = None
    ) -> Optional[int]:
        """Increment a counter in cache using neo-commons."""
        return await super().increment(key, amount, namespace=namespace)
    
    async def decrement(
        self, 
        key: str, 
        amount: int = 1,
        namespace: Optional[str] = None
    ) -> Optional[int]:
        """Decrement a counter in cache using neo-commons."""
        return await super().decrement(key, amount, namespace=namespace)
    
    async def get_many(
        self, 
        keys: List[str], 
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get multiple values from cache using neo-commons."""
        return await super().get_many(keys, namespace=namespace)
    
    async def set_many(
        self,
        mapping: Dict[str, Any],
        ttl: Optional[int] = None,
        namespace: Optional[str] = None
    ) -> bool:
        """Set multiple values in cache using neo-commons."""
        if ttl is None:
            ttl = settings.cache_ttl_default
        return await super().set_many(mapping, ttl=ttl, namespace=namespace)
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get NeoAdminApi-specific cache status information."""
        base_status = super().get_status()
        
        # Add NeoAdminApi-specific status information
        return {
            **base_status,
            "neoadminapi_ttl_settings": {
                "default": settings.cache_ttl_default,
                "permissions": settings.cache_ttl_permissions,
                "tenant": settings.cache_ttl_tenant
            },
            "performance_impact": not base_status.get("is_available", False),
            "neoadminapi_warnings": [
                "Redis not configured - set REDIS_URL environment variable",
                "Using database for all operations (no caching)",
                "Performance may be significantly impacted",
                "Permission checks will be slower (no 10-minute cache)",
                "Tenant lookups will be slower (no 10-minute cache)"
            ] if not base_status.get("is_available", False) else []
        }
    
    # Redis Set operations using neo-commons
    async def sadd(
        self, 
        key: str, 
        *values, 
        namespace: Optional[str] = None
    ) -> int:
        """Add one or more members to a set using neo-commons."""
        return await super().sadd(key, *values, namespace=namespace)
    
    async def smembers(
        self, 
        key: str, 
        namespace: Optional[str] = None
    ) -> set:
        """Get all members of a set using neo-commons."""
        return await super().smembers(key, namespace=namespace)
    
    async def srem(
        self, 
        key: str, 
        *values, 
        namespace: Optional[str] = None
    ) -> int:
        """Remove one or more members from a set using neo-commons."""
        return await super().srem(key, *values, namespace=namespace)


# BACKWARD COMPATIBILITY: Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


async def init_cache():
    """Initialize cache connection."""
    logger.info("Initializing cache...")
    cache = get_cache()
    await cache.connect()
    
    status = cache.get_cache_status()
    if status.get("is_available", False):
        logger.info("Cache initialization complete - Redis is available")
    else:
        logger.warning(
            "Cache initialization skipped - Redis is not available. "
            "Application will run without caching. "
            "This may impact performance significantly for: "
            "Permission checks (normally cached for 10 minutes), "
            "Tenant lookups (normally cached for 10 minutes), "
            "Token validation (repeated Keycloak calls), "
            "Rate limiting (if implemented)"
        )


async def close_cache():
    """Close cache connection."""
    cache = get_cache()
    status = cache.get_cache_status()
    if status.get("is_available", False):
        logger.info("Closing cache connection...")
        await cache.disconnect()
        logger.info("Cache connection closed")
    else:
        logger.debug("No cache connection to close")