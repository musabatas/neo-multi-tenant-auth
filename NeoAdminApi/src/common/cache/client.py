"""
Redis cache client and utilities.
"""
import json
import pickle
from typing import Optional, Any, Union, List, Dict
from datetime import timedelta
import redis.asyncio as redis
from redis.asyncio import Redis, ConnectionPool
from loguru import logger

from src.common.config.settings import settings


class CacheManager:
    """Manages Redis cache operations."""
    
    def __init__(self):
        self.redis_client: Optional[Redis] = None
        self.pool: Optional[ConnectionPool] = None
        self.key_prefix = settings.get_cache_key_prefix()
        
    async def connect(self) -> Redis:
        """Create and return Redis connection."""
        if self.redis_client is None:
            logger.info("Creating Redis connection pool...")
            
            # Parse Redis URL
            redis_url = str(settings.redis_url)
            
            self.pool = ConnectionPool.from_url(
                redis_url,
                max_connections=settings.redis_pool_size,
                decode_responses=settings.redis_decode_responses,
                health_check_interval=30
            )
            
            self.redis_client = Redis(connection_pool=self.pool)
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis connection established successfully")
            
        return self.redis_client
    
    async def disconnect(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            if self.pool:
                await self.pool.disconnect()
            self.redis_client = None
            self.pool = None
            logger.info("Redis connection closed")
    
    def _make_key(self, key: str, namespace: Optional[str] = None) -> str:
        """Create a namespaced cache key."""
        if namespace:
            return f"{self.key_prefix}{namespace}:{key}"
        return f"{self.key_prefix}{key}"
    
    async def get(
        self, 
        key: str, 
        namespace: Optional[str] = None,
        deserialize: bool = True
    ) -> Optional[Any]:
        """Get value from cache."""
        client = await self.connect()
        full_key = self._make_key(key, namespace)
        
        try:
            value = await client.get(full_key)
            
            # Track cache operation for metadata
            try:
                from src.common.utils.metadata import track_cache_operation
                if value is None:
                    track_cache_operation('miss')
                else:
                    track_cache_operation('hit')
            except ImportError:
                pass  # Metadata system not available
            
            if value is None:
                return None
            
            if deserialize and isinstance(value, str):
                try:
                    # Try JSON first
                    return json.loads(value)
                except json.JSONDecodeError:
                    # Return as string if not JSON
                    return value
            elif deserialize and isinstance(value, bytes):
                try:
                    # Try pickle for bytes
                    return pickle.loads(value)
                except:
                    return value.decode('utf-8')
            
            return value
            
        except Exception as e:
            logger.error(f"Cache get error for key {full_key}: {e}")
            # Track miss on error
            try:
                from src.common.utils.metadata import track_cache_operation
                track_cache_operation('miss')
            except ImportError:
                pass
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
        full_key = self._make_key(key, namespace)
        
        if ttl is None:
            ttl = settings.cache_ttl_default
        
        try:
            if serialize:
                if isinstance(value, (dict, list, tuple)):
                    value = json.dumps(value)
                elif not isinstance(value, (str, bytes, int, float)):
                    value = pickle.dumps(value)
            
            if ttl > 0:
                await client.setex(full_key, ttl, value)
            else:
                await client.set(full_key, value)
            
            # Track cache set operation for metadata
            try:
                from src.common.utils.metadata import track_cache_operation
                track_cache_operation('set')
            except ImportError:
                pass  # Metadata system not available
            
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for key {full_key}: {e}")
            return False
    
    async def delete(self, key: str, namespace: Optional[str] = None) -> bool:
        """Delete value from cache."""
        client = await self.connect()
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
        full_keys = [self._make_key(key, namespace) for key in keys]
        
        try:
            values = await client.mget(full_keys)
            result = {}
            
            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = json.loads(value) if isinstance(value, str) else value
                    except:
                        result[key] = value
            
            return result
            
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
        
        if ttl is None:
            ttl = settings.cache_ttl_default
        
        try:
            pipe = client.pipeline()
            
            for key, value in mapping.items():
                full_key = self._make_key(key, namespace)
                
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                
                if ttl > 0:
                    pipe.setex(full_key, ttl, value)
                else:
                    pipe.set(full_key, value)
            
            await pipe.execute()
            return True
            
        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Check Redis health."""
        try:
            client = await self.connect()
            await client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    # Redis Set operations
    async def sadd(
        self, 
        key: str, 
        *values, 
        namespace: Optional[str] = None
    ) -> int:
        """Add one or more members to a set."""
        client = await self.connect()
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
        full_key = self._make_key(key, namespace)
        
        try:
            return await client.srem(full_key, *values)
        except Exception as e:
            logger.error(f"Cache srem error for key {full_key}: {e}")
            return 0
    
    async def expire(
        self, 
        key: str, 
        ttl: int, 
        namespace: Optional[str] = None
    ) -> bool:
        """Set TTL on a key."""
        client = await self.connect()
        full_key = self._make_key(key, namespace)
        
        try:
            return await client.expire(full_key, ttl)
        except Exception as e:
            logger.error(f"Cache expire error for key {full_key}: {e}")
            return False


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
    await cache.connect()
    logger.info("Cache initialization complete")


async def close_cache():
    """Close cache connection."""
    logger.info("Closing cache connection...")
    cache = get_cache()
    await cache.disconnect()
    logger.info("Cache connection closed")