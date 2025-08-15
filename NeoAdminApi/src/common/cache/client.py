"""
Redis cache client and utilities.

Service wrapper that imports from neo-commons and provides NeoAdminApi-specific
cache functionality while maintaining backward compatibility.
"""

from typing import Optional, Any
from loguru import logger

# Import from neo-commons
from neo_commons.cache.client import CacheManager as NeoCacheManager, CacheConfig

# Import service-specific settings
from src.common.config.settings import settings


class AdminCacheConfig:
    """Service-specific cache configuration for NeoAdminApi."""
    
    @property
    def is_cache_enabled(self) -> bool:
        return settings.is_cache_enabled
    
    @property
    def redis_url(self) -> Optional[str]:
        return str(settings.redis_url) if settings.redis_url else None
    
    @property
    def redis_pool_size(self) -> int:
        return settings.redis_pool_size
    
    @property
    def redis_decode_responses(self) -> bool:
        return settings.redis_decode_responses
    
    @property
    def cache_ttl_default(self) -> int:
        return settings.cache_ttl_default
    
    def get_cache_key_prefix(self) -> str:
        return settings.get_cache_key_prefix()


class CacheManager(NeoCacheManager):
    """
    Service wrapper for NeoAdminApi that extends neo-commons CacheManager.
    
    Provides NeoAdminApi-specific cache functionality while maintaining
    full compatibility with existing code.
    """
    
    def __init__(self):
        # Initialize with service-specific configuration
        config = AdminCacheConfig()
        super().__init__(config)
    
    async def get(
        self, 
        key: str, 
        namespace: Optional[str] = None,
        deserialize: bool = True
    ) -> Optional[Any]:
        """Get value from cache with metadata tracking."""
        # Get result from neo-commons
        result = await super().get(key, namespace, deserialize)
        
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
        """Set value in cache with metadata tracking."""
        # Set using neo-commons
        success = await super().set(key, value, ttl, namespace, serialize)
        
        # Track cache set operation for NeoAdminApi metadata
        if success:
            try:
                from src.common.utils.metadata import track_cache_operation
                track_cache_operation('set')
            except ImportError:
                pass  # Metadata system not available
        
        return success
    


# Global cache manager instance
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
    client = await cache.connect()
    
    if client:
        logger.info("Cache initialization complete - Redis is available")
    else:
        logger.warning(
            "Cache initialization skipped - Redis is not available. "
            "Application will run without caching. "
            "This may impact performance significantly for:"
            "\n  - Permission checks (normally cached for 10 minutes)"
            "\n  - Tenant lookups (normally cached for 10 minutes)"
            "\n  - Token validation (repeated Keycloak calls)"
            "\n  - Rate limiting (if implemented)"
        )


async def close_cache():
    """Close cache connection."""
    cache = get_cache()
    if cache.is_available:
        logger.info("Closing cache connection...")
        await cache.disconnect()
        logger.info("Cache connection closed")
    else:
        logger.debug("No cache connection to close")