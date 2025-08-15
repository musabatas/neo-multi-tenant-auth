"""
Redis cache client for NeoMultiTenant services.

Streamlined cache manager with operations split into separate modules.
"""
import os
from typing import Optional, Any, List, Dict
from redis.asyncio import Redis
import logging

from .redis_operations import RedisOperations, RedisConnectionManager

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages Redis cache operations with graceful degradation."""
    
    def __init__(
        self, 
        redis_url: Optional[str] = None,
        key_prefix: Optional[str] = None,
        decode_responses: bool = True,
        pool_size: int = 50,
        default_ttl: int = 300
    ):
        """Initialize CacheManager."""
        self.redis_url = redis_url or os.getenv("REDIS_URL", "")
        self.key_prefix = key_prefix or f"{os.getenv('APP_NAME', 'neo-commons')}:"
        self.default_ttl = default_ttl
        
        # Initialize connection manager
        self._conn_manager = RedisConnectionManager(
            self.redis_url,
            pool_size,
            decode_responses
        )
        
        # Initialize operations helper
        self._ops = RedisOperations()
        
    @property
    def is_available(self) -> bool:
        """Check if Redis is available."""
        return self._conn_manager.is_available
        
    @property
    def connection_attempted(self) -> bool:
        """Check if connection was attempted."""
        return self._conn_manager.connection_attempted
        
    async def connect(self) -> Optional[Redis]:
        """Create and return Redis connection."""
        return await self._conn_manager.create_connection()
    
    async def disconnect(self):
        """Close Redis connection."""
        await self._conn_manager.disconnect()
    
    def _make_key(self, key: str, namespace: Optional[str] = None) -> str:
        """Create a namespaced cache key."""
        return self._ops.make_key(key, self.key_prefix, namespace)
    
    async def get(
        self, 
        key: str, 
        namespace: Optional[str] = None,
        deserialize: bool = True
    ) -> Optional[Any]:
        """Get value from cache."""
        client = await self.connect()
        if not client:
            return None
            
        full_key = self._make_key(key, namespace)
        
        try:
            value = await client.get(full_key)
            return self._ops.deserialize_value(value, deserialize)
        except Exception as e:
            logger.error(f"Cache get error for key {full_key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: Optional[str] = None,
        serialize: bool = True
    ) -> bool:
        """Set value in cache."""
        client = await self.connect()
        if not client:
            return False
            
        full_key = self._make_key(key, namespace)
        
        if ttl is None:
            ttl = self.default_ttl
        
        try:
            serialized_value = self._ops.serialize_value(value, serialize)
            
            if ttl > 0:
                await client.setex(full_key, ttl, serialized_value)
            else:
                await client.set(full_key, serialized_value)
            
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {full_key}: {e}")
            return False
    
    async def delete(self, key: str, namespace: Optional[str] = None) -> bool:
        """Delete value from cache."""
        client = await self.connect()
        if not client:
            return False
            
        full_key = self._make_key(key, namespace)
        
        try:
            result = await client.delete(full_key)
            return result > 0
        except Exception as e:
            logger.error(f"Cache delete error for key {full_key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str, namespace: Optional[str] = None) -> int:
        """Delete all keys matching a pattern."""
        client = await self.connect()
        if not client:
            return 0
            
        full_pattern = self._make_key(pattern, namespace)
        
        try:
            keys = []
            async for key in client.scan_iter(match=full_pattern):
                keys.append(key)
            
            if keys:
                return await client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error for {full_pattern}: {e}")
            return 0
    
    async def exists(self, key: str, namespace: Optional[str] = None) -> bool:
        """Check if key exists in cache."""
        client = await self.connect()
        if not client:
            return False
            
        full_key = self._make_key(key, namespace)
        
        try:
            return await client.exists(full_key) > 0
        except Exception as e:
            logger.error(f"Cache exists error for key {full_key}: {e}")
            return False
    
    async def expire(
        self, 
        key: str, 
        ttl: int, 
        namespace: Optional[str] = None
    ) -> bool:
        """Set expiration time for a key."""
        client = await self.connect()
        if not client:
            return False
            
        full_key = self._make_key(key, namespace)
        
        try:
            return await client.expire(full_key, ttl)
        except Exception as e:
            logger.error(f"Cache expire error for key {full_key}: {e}")
            return False
    
    async def increment(
        self, 
        key: str, 
        amount: int = 1,
        namespace: Optional[str] = None
    ) -> Optional[int]:
        """Increment a counter in cache."""
        client = await self.connect()
        if not client:
            return None
            
        full_key = self._make_key(key, namespace)
        
        try:
            return await client.incrby(full_key, amount)
        except Exception as e:
            logger.error(f"Cache increment error for key {full_key}: {e}")
            return None
    
    async def decrement(
        self, 
        key: str, 
        amount: int = 1,
        namespace: Optional[str] = None
    ) -> Optional[int]:
        """Decrement a counter in cache."""
        client = await self.connect()
        if not client:
            return None
            
        full_key = self._make_key(key, namespace)
        
        try:
            return await client.decrby(full_key, amount)
        except Exception as e:
            logger.error(f"Cache decrement error for key {full_key}: {e}")
            return None
    
    async def get_many(
        self, 
        keys: List[str], 
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get multiple values from cache."""
        client = await self.connect()
        if not client:
            return {}
            
        full_keys = [self._make_key(key, namespace) for key in keys]
        
        try:
            values = await client.mget(full_keys)
            return self._ops.process_multi_get_result(keys, values)
        except Exception as e:
            logger.error(f"Cache get_many error: {e}")
            return {}
    
    async def set_many(
        self,
        mapping: Dict[str, Any],
        ttl: Optional[int] = None,
        namespace: Optional[str] = None
    ) -> bool:
        """Set multiple values in cache."""
        client = await self.connect()
        if not client:
            return False
        
        if ttl is None:
            ttl = self.default_ttl
        
        try:
            pipe = client.pipeline()
            
            for key, value in mapping.items():
                full_key = self._make_key(key, namespace)
                serialized_value = self._ops.serialize_value(value, serialize=True)
                
                if ttl > 0:
                    pipe.setex(full_key, ttl, serialized_value)
                else:
                    pipe.set(full_key, serialized_value)
            
            await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Check Redis health."""
        return await self._conn_manager.health_check()
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get cache status information."""
        return self._ops.get_cache_status_info(
            self.redis_url,
            self.is_available,
            self.connection_attempted
        )
    
    # Redis Set operations
    async def sadd(
        self, 
        key: str, 
        *values, 
        namespace: Optional[str] = None
    ) -> int:
        """Add one or more members to a set."""
        client = await self.connect()
        if not client:
            return 0
            
        full_key = self._make_key(key, namespace)
        
        try:
            return await client.sadd(full_key, *values)
        except Exception as e:
            logger.error(f"Cache sadd error for key {full_key}: {e}")
            return 0
    
    async def smembers(
        self, 
        key: str, 
        namespace: Optional[str] = None
    ) -> set:
        """Get all members of a set."""
        client = await self.connect()
        if not client:
            return set()
            
        full_key = self._make_key(key, namespace)
        
        try:
            return await client.smembers(full_key)
        except Exception as e:
            logger.error(f"Cache smembers error for key {full_key}: {e}")
            return set()
    
    async def srem(
        self, 
        key: str, 
        *values, 
        namespace: Optional[str] = None
    ) -> int:
        """Remove one or more members from a set."""
        client = await self.connect()
        if not client:
            return 0
            
        full_key = self._make_key(key, namespace)
        
        try:
            return await client.srem(full_key, *values)
        except Exception as e:
            logger.error(f"Cache srem error for key {full_key}: {e}")
            return 0


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache(
    redis_url: Optional[str] = None,
    key_prefix: Optional[str] = None,
    **kwargs
) -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(redis_url, key_prefix, **kwargs)
    return _cache_manager


async def init_cache(
    redis_url: Optional[str] = None,
    key_prefix: Optional[str] = None,
    **kwargs
):
    """Initialize cache connection."""
    logger.info("Initializing cache...")
    cache = get_cache(redis_url, key_prefix, **kwargs)
    client = await cache.connect()
    
    if client:
        logger.info("Cache initialization complete - Redis is available")
    else:
        logger.warning(
            "Cache initialization skipped - Redis is not available. "
            "Application will run without caching. "
            "This may impact performance significantly for:"
            "\n  - Permission checks (normally cached)"
            "\n  - Token validation (repeated external calls)"
            "\n  - Rate limiting (if implemented)"
        )


async def close_cache():
    """Close cache connection."""
    global _cache_manager
    if _cache_manager and _cache_manager.is_available:
        logger.info("Closing cache connection...")
        await _cache_manager.disconnect()
        logger.info("Cache connection closed")
    else:
        logger.debug("No cache connection to close")