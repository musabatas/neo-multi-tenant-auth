"""Redis cache adapter for authentication platform."""

import json
import logging
from typing import Any, Dict, List, Optional, Set, Union
from datetime import datetime, timezone, timedelta

from ...core.exceptions import CacheError

logger = logging.getLogger(__name__)


class RedisCacheAdapter:
    """Redis cache adapter following maximum separation principle.
    
    Handles ONLY Redis caching operations for authentication platform.
    Does not handle token validation, session management, or other auth logic.
    """
    
    def __init__(
        self,
        redis_client,
        key_prefix: str = "auth_cache",
        default_ttl_seconds: int = 300
    ):
        """Initialize Redis cache adapter.
        
        Args:
            redis_client: Redis client instance
            key_prefix: Prefix for cache keys
            default_ttl_seconds: Default TTL for cached items
        """
        if not redis_client:
            raise ValueError("Redis client is required")
        if default_ttl_seconds <= 0:
            raise ValueError("Default TTL must be positive")
            
        self.redis_client = redis_client
        self.key_prefix = key_prefix
        self.default_ttl_seconds = default_ttl_seconds
        
        # Statistics
        self._operations = 0
        self._errors = 0
    
    def _make_cache_key(self, key: str) -> str:
        """Create full cache key with prefix.
        
        Args:
            key: Base cache key
            
        Returns:
            Full cache key string
        """
        return f"{self.key_prefix}:{key}"
    
    def _serialize_value(self, value: Any) -> str:
        """Serialize value for Redis storage.
        
        Args:
            value: Value to serialize
            
        Returns:
            JSON string representation
        """
        try:
            # Add metadata for deserialization
            cache_data = {
                "value": value,
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "type": type(value).__name__
            }
            return json.dumps(cache_data, default=str)
        except Exception as e:
            logger.error(f"Failed to serialize cache value: {e}")
            raise CacheError(
                "Value serialization failed",
                context={"error": str(e), "value_type": type(value).__name__}
            )
    
    def _deserialize_value(self, data: str) -> Any:
        """Deserialize value from Redis storage.
        
        Args:
            data: JSON string representation
            
        Returns:
            Deserialized value
        """
        try:
            cache_data = json.loads(data)
            
            # Return the actual value
            if isinstance(cache_data, dict) and "value" in cache_data:
                return cache_data["value"]
            else:
                # Backward compatibility for direct values
                return cache_data
                
        except Exception as e:
            logger.warning(f"Failed to deserialize cache value: {e}")
            # Return raw data as fallback
            return data
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        cache_key = self._make_cache_key(key)
        
        try:
            self._operations += 1
            logger.debug(f"Getting value from Redis cache: {cache_key}")
            
            data = await self.redis_client.get(cache_key)
            
            if data is None:
                logger.debug(f"Cache miss: {cache_key}")
                return None
            
            value = self._deserialize_value(data)
            logger.debug(f"Cache hit: {cache_key}")
            return value
            
        except Exception as e:
            self._errors += 1
            logger.error(f"Failed to get value from cache {cache_key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if None)
            
        Returns:
            True if value was set successfully
        """
        cache_key = self._make_cache_key(key)
        ttl = ttl or self.default_ttl_seconds
        
        try:
            self._operations += 1
            logger.debug(f"Setting value in Redis cache: {cache_key} with TTL {ttl}s")
            
            serialized_data = self._serialize_value(value)
            
            if ttl > 0:
                result = await self.redis_client.setex(cache_key, ttl, serialized_data)
            else:
                result = await self.redis_client.set(cache_key, serialized_data)
            
            logger.debug(f"Successfully set cache value: {cache_key}")
            return True
            
        except CacheError:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            self._errors += 1
            logger.error(f"Failed to set cache value {cache_key}: {e}")
            raise CacheError(
                "Failed to set cache value",
                context={"key": key, "ttl": ttl, "error": str(e)}
            )
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if value was deleted
        """
        cache_key = self._make_cache_key(key)
        
        try:
            self._operations += 1
            logger.debug(f"Deleting value from Redis cache: {cache_key}")
            
            result = await self.redis_client.delete(cache_key)
            
            if result:
                logger.debug(f"Successfully deleted cache value: {cache_key}")
            else:
                logger.debug(f"Cache value not found for deletion: {cache_key}")
            
            return bool(result)
            
        except Exception as e:
            self._errors += 1
            logger.warning(f"Failed to delete cache value {cache_key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists
        """
        cache_key = self._make_cache_key(key)
        
        try:
            self._operations += 1
            result = await self.redis_client.exists(cache_key)
            return bool(result)
            
        except Exception as e:
            self._errors += 1
            logger.warning(f"Failed to check cache key existence {cache_key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing cache key.
        
        Args:
            key: Cache key
            ttl: Time to live in seconds
            
        Returns:
            True if TTL was set successfully
        """
        cache_key = self._make_cache_key(key)
        
        try:
            self._operations += 1
            logger.debug(f"Setting TTL for cache key: {cache_key} to {ttl}s")
            
            result = await self.redis_client.expire(cache_key, ttl)
            
            if result:
                logger.debug(f"Successfully set TTL for cache key: {cache_key}")
            else:
                logger.debug(f"Cache key not found for TTL setting: {cache_key}")
            
            return bool(result)
            
        except Exception as e:
            self._errors += 1
            logger.warning(f"Failed to set TTL for cache key {cache_key}: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Get TTL for cache key.
        
        Args:
            key: Cache key
            
        Returns:
            TTL in seconds (-1 if no expiration, -2 if key doesn't exist)
        """
        cache_key = self._make_cache_key(key)
        
        try:
            self._operations += 1
            result = await self.redis_client.ttl(cache_key)
            return result
            
        except Exception as e:
            self._errors += 1
            logger.warning(f"Failed to get TTL for cache key {cache_key}: {e}")
            return -2
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment numeric value in cache.
        
        Args:
            key: Cache key
            amount: Amount to increment by
            
        Returns:
            New value after increment
        """
        cache_key = self._make_cache_key(key)
        
        try:
            self._operations += 1
            logger.debug(f"Incrementing cache value: {cache_key} by {amount}")
            
            result = await self.redis_client.incrby(cache_key, amount)
            
            logger.debug(f"Successfully incremented cache value: {cache_key} to {result}")
            return result
            
        except Exception as e:
            self._errors += 1
            logger.error(f"Failed to increment cache value {cache_key}: {e}")
            raise CacheError(
                "Failed to increment cache value",
                context={"key": key, "amount": amount, "error": str(e)}
            )
    
    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement numeric value in cache.
        
        Args:
            key: Cache key
            amount: Amount to decrement by
            
        Returns:
            New value after decrement
        """
        return await self.increment(key, -amount)
    
    async def get_multi(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache.
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dictionary mapping keys to their values
        """
        if not keys:
            return {}
        
        cache_keys = [self._make_cache_key(key) for key in keys]
        
        try:
            self._operations += 1
            logger.debug(f"Getting multiple values from Redis cache: {len(keys)} keys")
            
            values = await self.redis_client.mget(*cache_keys)
            
            result = {}
            for i, (original_key, value) in enumerate(zip(keys, values)):
                if value is not None:
                    try:
                        result[original_key] = self._deserialize_value(value)
                    except Exception as e:
                        logger.warning(f"Failed to deserialize cached value for {original_key}: {e}")
                        continue
            
            logger.debug(f"Successfully retrieved {len(result)} values from cache")
            return result
            
        except Exception as e:
            self._errors += 1
            logger.error(f"Failed to get multiple cache values: {e}")
            return {}
    
    async def set_multi(
        self,
        items: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Set multiple values in cache.
        
        Args:
            items: Dictionary mapping keys to values
            ttl: Time to live in seconds (uses default if None)
            
        Returns:
            True if all values were set successfully
        """
        if not items:
            return True
        
        ttl = ttl or self.default_ttl_seconds
        
        try:
            self._operations += 1
            logger.debug(f"Setting multiple values in Redis cache: {len(items)} items with TTL {ttl}s")
            
            # Use pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            
            for key, value in items.items():
                cache_key = self._make_cache_key(key)
                serialized_data = self._serialize_value(value)
                
                if ttl > 0:
                    pipe.setex(cache_key, ttl, serialized_data)
                else:
                    pipe.set(cache_key, serialized_data)
            
            await pipe.execute()
            
            logger.debug(f"Successfully set {len(items)} cache values")
            return True
            
        except Exception as e:
            self._errors += 1
            logger.error(f"Failed to set multiple cache values: {e}")
            raise CacheError(
                "Failed to set multiple cache values",
                context={"count": len(items), "ttl": ttl, "error": str(e)}
            )
    
    async def delete_multi(self, keys: List[str]) -> int:
        """Delete multiple values from cache.
        
        Args:
            keys: List of cache keys
            
        Returns:
            Number of keys deleted
        """
        if not keys:
            return 0
        
        cache_keys = [self._make_cache_key(key) for key in keys]
        
        try:
            self._operations += 1
            logger.debug(f"Deleting multiple values from Redis cache: {len(keys)} keys")
            
            result = await self.redis_client.delete(*cache_keys)
            
            logger.debug(f"Successfully deleted {result} cache values")
            return result
            
        except Exception as e:
            self._errors += 1
            logger.warning(f"Failed to delete multiple cache values: {e}")
            return 0
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern.
        
        Args:
            pattern: Pattern to match (supports * wildcards)
            
        Returns:
            Number of keys deleted
        """
        full_pattern = self._make_cache_key(pattern)
        
        try:
            self._operations += 1
            logger.warning(f"Clearing cache keys matching pattern: {full_pattern}")
            
            deleted_count = 0
            
            # Scan for matching keys
            async for key in self.redis_client.scan_iter(match=full_pattern):
                try:
                    if await self.redis_client.delete(key):
                        deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete key {key}: {e}")
                    continue
            
            logger.warning(f"Cleared {deleted_count} cache keys matching pattern: {pattern}")
            return deleted_count
            
        except Exception as e:
            self._errors += 1
            logger.error(f"Failed to clear cache pattern {pattern}: {e}")
            return 0
    
    async def clear_all(self) -> bool:
        """Clear all cache keys with the configured prefix.
        
        Returns:
            True if clearing was successful
        """
        try:
            logger.warning(f"Clearing all cache keys with prefix: {self.key_prefix}")
            
            deleted_count = await self.clear_pattern("*")
            
            logger.warning(f"Cleared {deleted_count} total cache keys")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear all cache keys: {e}")
            return False
    
    async def get_keys(self, pattern: str = "*") -> List[str]:
        """Get all cache keys matching pattern.
        
        Args:
            pattern: Pattern to match (supports * wildcards)
            
        Returns:
            List of matching cache keys (without prefix)
        """
        full_pattern = self._make_cache_key(pattern)
        
        try:
            self._operations += 1
            logger.debug(f"Getting cache keys matching pattern: {full_pattern}")
            
            keys = []
            prefix_len = len(self.key_prefix) + 1  # +1 for the colon separator
            
            async for key in self.redis_client.scan_iter(match=full_pattern):
                # Remove prefix and return original key
                key_str = key.decode() if isinstance(key, bytes) else key
                if key_str.startswith(f"{self.key_prefix}:"):
                    original_key = key_str[prefix_len:]
                    keys.append(original_key)
            
            logger.debug(f"Found {len(keys)} cache keys matching pattern: {pattern}")
            return keys
            
        except Exception as e:
            self._errors += 1
            logger.warning(f"Failed to get cache keys for pattern {pattern}: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache adapter statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        error_rate = self._errors / self._operations if self._operations > 0 else 0
        
        return {
            "operations": self._operations,
            "errors": self._errors,
            "error_rate": error_rate,
            "key_prefix": self.key_prefix,
            "default_ttl_seconds": self.default_ttl_seconds
        }