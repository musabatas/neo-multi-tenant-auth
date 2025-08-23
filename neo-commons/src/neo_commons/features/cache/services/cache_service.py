"""Cache service - simplified for Redis and in-memory cache only."""

import logging
from typing import Dict, List, Optional, Any, TypeVar

from ..entities.protocols import Cache
from ..entities.config import CacheSettings
from ....core.value_objects import TenantId
from ....core.exceptions import ValidationError

logger = logging.getLogger(__name__)
T = TypeVar('T')


class CacheService:
    """Simplified cache service for Redis and in-memory cache."""
    
    def __init__(self, 
                 default_cache: Cache,
                 settings: Optional[CacheSettings] = None):
        self.default_cache = default_cache
        self.settings = settings or CacheSettings()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the cache service."""
        if self._initialized:
            return
        
        try:
            await self.default_cache.connect()
            self._initialized = True
            logger.info("Cache service initialized successfully")
            
        except Exception as e:
            raise ValidationError(f"Failed to initialize cache service: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown the cache service."""
        if not self._initialized:
            return
        
        try:
            await self.default_cache.disconnect()
            self._initialized = False
            logger.info("Cache service shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during cache service shutdown: {e}")
    
    # High-level cache operations
    
    async def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """Get value from cache."""
        if not self._initialized:
            await self.initialize()
        # RedisAdapter doesn't support default parameter
        result = await self.default_cache.get(key)
        return result if result is not None else default
    
    async def set(self, 
                 key: str, 
                 value: T, 
                 ttl: Optional[int] = None,
                 tags: Optional[List[str]] = None) -> None:
        """Set value in cache."""
        if not self._initialized:
            await self.initialize()
        # RedisAdapter doesn't support tags, so we ignore them for now
        await self.default_cache.set(key, value, ttl)
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self._initialized:
            await self.initialize()
        return await self.default_cache.delete(key)
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        if not self._initialized:
            await self.initialize()
        return await self.default_cache.delete_pattern(pattern)
    
    # Tenant-aware operations
    
    async def get_tenant_key(self, tenant_id: str, key: str) -> str:
        """Build tenant-specific cache key."""
        return f"tenant:{tenant_id}:{key}"
    
    async def get_tenant_value(self, 
                              tenant_id: str, 
                              key: str, 
                              default: Optional[T] = None) -> Optional[T]:
        """Get tenant-specific value."""
        tenant_key = await self.get_tenant_key(tenant_id, key)
        return await self.get(tenant_key, default)
    
    async def set_tenant_value(self, 
                              tenant_id: str, 
                              key: str, 
                              value: T, 
                              ttl: Optional[int] = None) -> None:
        """Set tenant-specific value."""
        tenant_key = await self.get_tenant_key(tenant_id, key)
        await self.set(tenant_key, value, ttl)
    
    async def invalidate_tenant(self, tenant_id: str) -> int:
        """Invalidate all cache entries for a tenant."""
        pattern = f"tenant:{tenant_id}:*"
        return await self.delete_pattern(pattern)
    
    # Health and monitoring
    
    async def health_check(self) -> Dict[str, Any]:
        """Get cache health status."""
        try:
            if not self._initialized:
                return {"healthy": False, "error": "Cache not initialized"}
                
            healthy = await self.default_cache.health_check()
            return {"healthy": healthy}
            
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return {"healthy": False, "error": str(e)}
    
    async def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            if not self._initialized:
                return {"error": "Cache not initialized"}
                
            return await self.default_cache.stats()
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"error": str(e)}