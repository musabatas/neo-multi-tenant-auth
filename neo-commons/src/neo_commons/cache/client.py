"""
Redis cache client and utilities for NeoMultiTenant services.
"""
import json
import pickle
import os
from typing import Optional, Any, Union, List, Dict
from datetime import timedelta
import redis.asyncio as redis
from redis.asyncio import Redis, ConnectionPool
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages Redis cache operations."""
    
    def __init__(
        self, 
        redis_url: Optional[str] = None,
        key_prefix: Optional[str] = None,
        decode_responses: bool = True,
        pool_size: int = 50,
        default_ttl: int = 300
    ):
        """Initialize CacheManager.
        
        Args:
            redis_url: Redis connection URL (defaults to REDIS_URL env var)
            key_prefix: Prefix for all cache keys (defaults to app name)
            decode_responses: Whether to decode Redis responses to strings
            pool_size: Maximum connections in pool
            default_ttl: Default TTL for cache entries in seconds
        """
        self.redis_client: Optional[Redis] = None
        self.pool: Optional[ConnectionPool] = None
        self.redis_url = redis_url or os.getenv("REDIS_URL", "")
        self.key_prefix = key_prefix or f"{os.getenv('APP_NAME', 'neo-commons')}:"
        self.decode_responses = decode_responses
        self.pool_size = pool_size
        self.default_ttl = default_ttl
        self.is_available = False  # Track Redis availability
        self.connection_attempted = False  # Track if we've tried to connect
        
    async def connect(self) -> Optional[Redis]:
        """Create and return Redis connection.
        
        Returns None if Redis is not configured or unavailable.
        """
        # Skip if already attempted and failed
        if self.connection_attempted and not self.is_available:
            return None
            
        if self.redis_client is None:
            # Check if Redis URL is configured
            if not self.redis_url:
                # Redis not configured
                if not self.connection_attempted:
                    logger.info(
                        "Redis URL not configured (REDIS_URL environment variable not set). "
                        "Running without cache - this will impact performance! "
                        "Set REDIS_URL to enable caching for better performance."
                    )
                    self.connection_attempted = True
                return None
            
            try:
                logger.info("Creating Redis connection pool...")
                
                self.pool = ConnectionPool.from_url(
                    self.redis_url,
                    max_connections=self.pool_size,
                    decode_responses=self.decode_responses,
                    health_check_interval=30
                )
                
                self.redis_client = Redis(connection_pool=self.pool)
                
                # Test connection
                await self.redis_client.ping()
                logger.info("Redis connection established successfully")
                self.is_available = True
                self.connection_attempted = True
                
            except Exception as e:
                logger.warning(
                    f"Redis connection failed: {e}. "
                    "Running without cache - this will impact performance!"
                )
                self.is_available = False
                self.connection_attempted = True
                
                # Clean up failed connection
                if self.redis_client:
                    try:
                        await self.redis_client.close()
                    except:
                        pass
                if self.pool:
                    try:
                        await self.pool.disconnect()
                    except:
                        pass
                    
                self.redis_client = None
                self.pool = None
                return None
            
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
        if not client:
            # Redis not available, return None (cache miss)
            return None
            
        full_key = self._make_key(key, namespace)
        
        try:
            value = await client.get(full_key)
            
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
            # Redis not available, return False (cache write failed)
            return False
            
        full_key = self._make_key(key, namespace)
        
        if ttl is None:
            ttl = self.default_ttl
        
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
            
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for key {full_key}: {e}")
            return False
    
    async def delete(self, key: str, namespace: Optional[str] = None) -> bool:
        """Delete value from cache."""
        client = await self.connect()
        if not client:
            # Redis not available, return False
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
            # Redis not available, return 0
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
            # Redis not available, return False
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
            # Redis not available, return False
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
            # Redis not available, return None
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
            # Redis not available, return None
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
            # Redis not available, return empty dict
            return {}
            
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
        if not client:
            # Redis not available, return False
            return False
        
        if ttl is None:
            ttl = self.default_ttl
        
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
            if not client:
                # Redis not available
                return False
            await client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get cache status information."""
        return {
            "redis_configured": bool(self.redis_url),
            "redis_available": self.is_available,
            "connection_attempted": self.connection_attempted,
            "redis_url": self.redis_url if self.redis_url else None,
            "performance_impact": not self.is_available,
            "warnings": [
                "Redis not configured - set REDIS_URL environment variable",
                "Using database for all operations (no caching)",
                "Performance may be significantly impacted",
                "Permission checks will be slower (no cache)",
                "Token validation will be slower (repeated external calls)"
            ] if not self.is_available else []
        }
    
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
            # Redis not available, return 0
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
            # Redis not available, return empty set
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
            # Redis not available, return 0
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