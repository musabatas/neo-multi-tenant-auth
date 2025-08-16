"""
CacheService implementation for NeoAdminApi.

Protocol-compliant wrapper around existing cache client for neo-commons integration.
"""
from typing import Any, Optional, List, Dict, Union
import json
from loguru import logger

from neo_commons.auth.protocols import CacheServiceProtocol
from src.common.cache.client import get_cache


class NeoAdminCacheService:
    """
    CacheService implementation for NeoAdminApi.
    
    Wraps the existing Redis cache client to provide protocol compliance.
    """
    
    def __init__(self):
        """Initialize cache service."""
        self.cache = get_cache()
    
    async def get(
        self,
        key: str,
        tenant_id: Optional[str] = None
    ) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            tenant_id: Optional tenant ID for namespacing
            
        Returns:
            Cached value if found, None otherwise
        """
        try:
            # Build namespaced key
            cache_key = self._build_key(key, tenant_id)
            
            # Get from cache
            value = await self.cache.get(cache_key)
            
            if value is not None:
                # Try to deserialize JSON
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    # Return raw value if not JSON
                    return value
            
            return None
            
        except Exception as e:
            logger.error(f"Cache get failed for key {key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        tenant_id: Optional[str] = None,
        ttl: int = 3600
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            tenant_id: Optional tenant ID for namespacing
            ttl: Time to live in seconds
            
        Returns:
            True if successful
        """
        try:
            # Build namespaced key
            cache_key = self._build_key(key, tenant_id)
            
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, default=str)
            else:
                serialized_value = str(value)
            
            # Set in cache
            await self.cache.set(cache_key, serialized_value, ttl=ttl)
            return True
            
        except Exception as e:
            logger.error(f"Cache set failed for key {key}: {e}")
            return False
    
    async def delete(
        self,
        key: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            tenant_id: Optional tenant ID for namespacing
            
        Returns:
            True if successful
        """
        try:
            # Build namespaced key
            cache_key = self._build_key(key, tenant_id)
            
            # Delete from cache
            await self.cache.delete(cache_key)
            return True
            
        except Exception as e:
            logger.error(f"Cache delete failed for key {key}: {e}")
            return False
    
    async def exists(
        self,
        key: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            tenant_id: Optional tenant ID for namespacing
            
        Returns:
            True if key exists
        """
        try:
            # Build namespaced key
            cache_key = self._build_key(key, tenant_id)
            
            # Check existence
            return await self.cache.exists(cache_key)
            
        except Exception as e:
            logger.error(f"Cache exists check failed for key {key}: {e}")
            return False
    
    async def expire(
        self,
        key: str,
        ttl: int,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Set expiration for key.
        
        Args:
            key: Cache key
            ttl: Time to live in seconds
            tenant_id: Optional tenant ID for namespacing
            
        Returns:
            True if successful
        """
        try:
            # Build namespaced key
            cache_key = self._build_key(key, tenant_id)
            
            # Set expiration
            await self.cache.expire(cache_key, ttl)
            return True
            
        except Exception as e:
            logger.error(f"Cache expire failed for key {key}: {e}")
            return False
    
    async def ttl(
        self,
        key: str,
        tenant_id: Optional[str] = None
    ) -> int:
        """
        Get time to live for key.
        
        Args:
            key: Cache key
            tenant_id: Optional tenant ID for namespacing
            
        Returns:
            TTL in seconds, -1 if no expiry, -2 if key doesn't exist
        """
        try:
            # Build namespaced key
            cache_key = self._build_key(key, tenant_id)
            
            # Get TTL
            return await self.cache.ttl(cache_key)
            
        except Exception as e:
            logger.error(f"Cache TTL check failed for key {key}: {e}")
            return -2
    
    async def increment(
        self,
        key: str,
        amount: int = 1,
        tenant_id: Optional[str] = None
    ) -> int:
        """
        Increment numeric value in cache.
        
        Args:
            key: Cache key
            amount: Amount to increment by
            tenant_id: Optional tenant ID for namespacing
            
        Returns:
            New value after increment
        """
        try:
            # Build namespaced key
            cache_key = self._build_key(key, tenant_id)
            
            # Increment value
            if hasattr(self.cache, 'incr'):
                if amount == 1:
                    return await self.cache.incr(cache_key)
                else:
                    return await self.cache.incrby(cache_key, amount)
            else:
                # Fallback for basic cache implementations
                current = await self.get(key, tenant_id) or 0
                new_value = int(current) + amount
                await self.set(key, new_value, tenant_id)
                return new_value
                
        except Exception as e:
            logger.error(f"Cache increment failed for key {key}: {e}")
            return 0
    
    async def decrement(
        self,
        key: str,
        amount: int = 1,
        tenant_id: Optional[str] = None
    ) -> int:
        """
        Decrement numeric value in cache.
        
        Args:
            key: Cache key
            amount: Amount to decrement by
            tenant_id: Optional tenant ID for namespacing
            
        Returns:
            New value after decrement
        """
        try:
            # Build namespaced key
            cache_key = self._build_key(key, tenant_id)
            
            # Decrement value
            if hasattr(self.cache, 'decr'):
                if amount == 1:
                    return await self.cache.decr(cache_key)
                else:
                    return await self.cache.decrby(cache_key, amount)
            else:
                # Fallback for basic cache implementations
                current = await self.get(key, tenant_id) or 0
                new_value = int(current) - amount
                await self.set(key, new_value, tenant_id)
                return new_value
                
        except Exception as e:
            logger.error(f"Cache decrement failed for key {key}: {e}")
            return 0
    
    async def keys(
        self,
        pattern: str,
        tenant_id: Optional[str] = None
    ) -> List[str]:
        """
        Get keys matching pattern.
        
        Args:
            pattern: Key pattern (supports wildcards)
            tenant_id: Optional tenant ID for namespacing
            
        Returns:
            List of matching keys
        """
        try:
            # Build namespaced pattern
            search_pattern = self._build_key(pattern, tenant_id)
            
            # Get matching keys
            if hasattr(self.cache, 'keys'):
                keys = await self.cache.keys(search_pattern)
                # Remove namespace prefix from results
                namespace_prefix = self._build_key("", tenant_id)
                return [key.replace(namespace_prefix, "", 1) for key in keys]
            else:
                logger.warning("Cache keys operation not supported")
                return []
                
        except Exception as e:
            logger.error(f"Cache keys search failed for pattern {pattern}: {e}")
            return []
    
    async def clear_pattern(
        self,
        pattern: str,
        tenant_id: Optional[str] = None
    ) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Key pattern (supports wildcards)
            tenant_id: Optional tenant ID for namespacing
            
        Returns:
            Number of keys deleted
        """
        try:
            # Get matching keys
            keys = await self.keys(pattern, tenant_id)
            
            # Delete each key
            deleted_count = 0
            for key in keys:
                if await self.delete(key, tenant_id):
                    deleted_count += 1
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cache pattern clear failed for pattern {pattern}: {e}")
            return 0
    
    async def health_check(self) -> bool:
        """
        Check cache service health.
        
        Returns:
            True if cache is healthy
        """
        try:
            # Test basic operations
            test_key = "health_check_test"
            test_value = "test_value"
            
            # Set, get, and delete test value
            await self.set(test_key, test_value, ttl=10)
            retrieved = await self.get(test_key)
            await self.delete(test_key)
            
            return retrieved == test_value
            
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return False
    
    def _build_key(self, key: str, tenant_id: Optional[str] = None) -> str:
        """
        Build namespaced cache key.
        
        Args:
            key: Base key
            tenant_id: Optional tenant ID for namespacing
            
        Returns:
            Namespaced key
        """
        if tenant_id:
            return f"tenant:{tenant_id}:{key}"
        else:
            return f"platform:{key}"
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics if available.
        
        Returns:
            Cache statistics
        """
        try:
            # Try to get basic stats
            stats = {}
            
            if hasattr(self.cache, 'info'):
                # Redis-specific info
                info = await self.cache.info()
                stats.update(info)
            
            # Add basic health status
            stats["healthy"] = await self.health_check()
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"healthy": False, "error": str(e)}