"""Tenant-aware cache implementation for multi-tenant applications."""

import logging
from typing import Optional, Any, List
from datetime import datetime, timedelta

from ...cache.entities.protocols import Cache
from ....core.exceptions.infrastructure import CacheError

logger = logging.getLogger(__name__)


class TenantCache:
    """Tenant-aware cache wrapper that provides tenant-specific caching operations."""
    
    def __init__(self, 
                 cache: Cache,
                 tenant_prefix: str = "tenant",
                 default_ttl: int = 3600):
        """
        Initialize tenant cache.
        
        Args:
            cache: Underlying cache implementation
            tenant_prefix: Prefix for tenant-specific keys
            default_ttl: Default time-to-live for cache entries in seconds
        """
        self._cache = cache
        self._tenant_prefix = tenant_prefix
        self._default_ttl = default_ttl
        self._connected = False
    
    async def connect(self) -> None:
        """Connect to the underlying cache."""
        if not self._connected:
            await self._cache.connect()
            self._connected = True
            logger.info("TenantCache connected successfully")
    
    async def disconnect(self) -> None:
        """Disconnect from the underlying cache."""
        if self._connected:
            await self._cache.disconnect()
            self._connected = False
            logger.info("TenantCache disconnected")
    
    def _make_key(self, key: str, tenant_id: Optional[str] = None) -> str:
        """Create a tenant-specific cache key."""
        if tenant_id:
            return f"{self._tenant_prefix}:{tenant_id}:{key}"
        return key
    
    def _make_tenant_schema_key(self, tenant_id: str) -> str:
        """Create a cache key for tenant schema."""
        return f"schema:{tenant_id}"
    
    # Generic cache operations
    
    async def get(self, key: str, tenant_id: Optional[str] = None) -> Optional[Any]:
        """Get value from cache with optional tenant scoping."""
        try:
            cache_key = self._make_key(key, tenant_id)
            return await self._cache.get(cache_key)
        except Exception as e:
            logger.error(f"Failed to get cache key {key}: {e}")
            return None
    
    async def set(self, 
                  key: str, 
                  value: Any, 
                  ttl: Optional[int] = None,
                  tenant_id: Optional[str] = None) -> None:
        """Set value in cache with optional tenant scoping."""
        try:
            cache_key = self._make_key(key, tenant_id)
            effective_ttl = ttl or self._default_ttl
            await self._cache.set(cache_key, value, ttl=effective_ttl)
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            raise CacheError(f"Failed to set cache key {key}: {e}")
    
    async def delete(self, key: str, tenant_id: Optional[str] = None) -> bool:
        """Delete value from cache with optional tenant scoping."""
        try:
            cache_key = self._make_key(key, tenant_id)
            return await self._cache.delete(cache_key)
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        try:
            # Get all keys matching pattern
            keys = await self._cache.keys(pattern)
            
            # Delete all matching keys
            deleted_count = 0
            for key in keys:
                if await self._cache.delete(key):
                    deleted_count += 1
            
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete keys with pattern {pattern}: {e}")
            return 0
    
    async def exists(self, key: str, tenant_id: Optional[str] = None) -> bool:
        """Check if key exists in cache."""
        try:
            cache_key = self._make_key(key, tenant_id)
            return await self._cache.exists(cache_key)
        except Exception as e:
            logger.error(f"Failed to check existence of cache key {key}: {e}")
            return False
    
    async def clear_tenant(self, tenant_id: str) -> int:
        """Clear all cache entries for a specific tenant."""
        try:
            pattern = f"{self._tenant_prefix}:{tenant_id}:*"
            return await self.delete_pattern(pattern)
        except Exception as e:
            logger.error(f"Failed to clear tenant cache for {tenant_id}: {e}")
            return 0
    
    # Tenant schema-specific operations
    
    async def get_tenant_schema(self, tenant_id: str) -> Optional[str]:
        """Get cached schema name for a tenant."""
        try:
            cache_key = self._make_tenant_schema_key(tenant_id)
            return await self._cache.get(cache_key)
        except Exception as e:
            logger.error(f"Failed to get tenant schema for {tenant_id}: {e}")
            return None
    
    async def set_tenant_schema(self, tenant_id: str, schema_name: str) -> None:
        """Cache schema name for a tenant."""
        try:
            cache_key = self._make_tenant_schema_key(tenant_id)
            # Tenant schemas are relatively stable, cache for longer
            await self._cache.set(cache_key, schema_name, ttl=7200)  # 2 hours
        except Exception as e:
            logger.error(f"Failed to set tenant schema for {tenant_id}: {e}")
            raise CacheError(f"Failed to cache tenant schema: {e}")
    
    async def invalidate_tenant_schema(self, tenant_id: str) -> bool:
        """Invalidate cached schema for a tenant."""
        try:
            cache_key = self._make_tenant_schema_key(tenant_id)
            return await self._cache.delete(cache_key)
        except Exception as e:
            logger.error(f"Failed to invalidate tenant schema for {tenant_id}: {e}")
            return False
    
    # Health and maintenance operations
    
    async def health_check(self) -> bool:
        """Check if the tenant cache is healthy."""
        try:
            return await self._cache.health_check()
        except Exception as e:
            logger.error(f"TenantCache health check failed: {e}")
            return False
    
    async def get_stats(self) -> dict:
        """Get cache statistics."""
        try:
            base_stats = await self._cache.info()
            return {
                "tenant_cache": True,
                "tenant_prefix": self._tenant_prefix,
                "default_ttl": self._default_ttl,
                "connected": self._connected,
                **base_stats
            }
        except Exception as e:
            logger.error(f"Failed to get tenant cache stats: {e}")
            return {
                "tenant_cache": True,
                "error": str(e),
                "connected": self._connected
            }