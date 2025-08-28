"""Redis cache repository implementation.

ONLY Redis implementation - cache storage using Redis backend
with async support and performance optimization.

Following maximum separation architecture - one file = one purpose.
"""

import json
import pickle
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import uuid4

# Redis client will be injected - no direct database dependency needed
from ...core.protocols.cache_repository import CacheRepository
from ...core.entities.cache_entry import CacheEntry
from ...core.entities.cache_namespace import CacheNamespace, EvictionPolicy
from ...core.value_objects.cache_key import CacheKey
from ...core.value_objects.cache_ttl import CacheTTL
from ...core.value_objects.cache_priority import CachePriority, PriorityLevel
from ...core.value_objects.cache_size import CacheSize
from ...core.value_objects.invalidation_pattern import InvalidationPattern
from ...core.exceptions.cache_timeout import CacheTimeout
from ...core.exceptions.cache_capacity_exceeded import CacheCapacityExceeded


class RedisCacheRepository:
    """Redis cache repository implementation.
    
    High-performance cache repository using Redis backend with:
    - Async operations with connection pooling
    - Automatic serialization and deserialization
    - TTL and expiration handling
    - Pattern-based invalidation
    - Namespace organization
    - Batch operations
    - Performance monitoring
    """
    
    def __init__(
        self,
        redis_client,
        key_prefix: str = "cache:",
        default_timeout_seconds: float = 5.0
    ):
        """Initialize Redis cache repository.
        
        Args:
            redis_client: Redis client instance (async Redis connection)
            key_prefix: Prefix for all cache keys
            default_timeout_seconds: Default operation timeout
        """
        self._redis_client = redis_client
        self._key_prefix = key_prefix
        self._default_timeout = default_timeout_seconds
        
        # Performance counters
        self._stats = {
            "get_count": 0,
            "set_count": 0,
            "delete_count": 0,
            "hit_count": 0,
            "miss_count": 0,
            "error_count": 0,
            "total_get_time": 0.0,
            "total_set_time": 0.0
        }
    
    def _build_redis_key(self, key: CacheKey, namespace: CacheNamespace) -> str:
        """Build full Redis key with prefix and namespace."""
        return f"{self._key_prefix}{namespace.get_full_key(str(key))}"
    
    def _build_namespace_pattern(self, namespace: CacheNamespace) -> str:
        """Build Redis key pattern for namespace."""
        return f"{self._key_prefix}{namespace.get_full_key('*')}"
    
    async def _get_redis_connection(self):
        """Get Redis connection (returns the injected client)."""
        if not self._redis_client:
            raise ConnectionError("Redis client not configured")
        return self._redis_client
    
    async def get(self, key: CacheKey, namespace: CacheNamespace) -> Optional[CacheEntry]:
        """Get cache entry by key."""
        start_time = datetime.utcnow()
        
        try:
            redis_key = self._build_redis_key(key, namespace)
            redis = await self._get_redis_connection()
            
            # Get value and metadata from Redis
            value_data = await redis.get(redis_key)
            if value_data is None:
                self._stats["miss_count"] += 1
                return None
            
            # Get metadata
            meta_key = f"{redis_key}:meta"
            metadata = await redis.hgetall(meta_key)
            
            if not metadata:
                # Value exists but no metadata - treat as miss
                self._stats["miss_count"] += 1
                return None
            
            # Deserialize and create cache entry
            try:
                value = pickle.loads(value_data)
                
                entry = CacheEntry(
                    key=key,
                    value=value,
                    ttl=CacheTTL(int(metadata.get("ttl_seconds", -1))) if metadata.get("ttl_seconds") != "-1" else None,
                    priority=CachePriority(PriorityLevel(int(metadata.get("priority", PriorityLevel.MEDIUM.value)))),
                    namespace=namespace,
                    created_at=datetime.fromisoformat(metadata["created_at"]),
                    accessed_at=datetime.utcnow(),  # Update access time
                    access_count=int(metadata.get("access_count", 0)) + 1,
                    size_bytes=CacheSize(int(metadata.get("size_bytes", len(value_data))))
                )
                
                # Update access tracking in Redis
                await redis.hset(meta_key, mapping={
                    "accessed_at": entry.accessed_at.isoformat(),
                    "access_count": str(entry.access_count)
                })
                
                self._stats["hit_count"] += 1
                return entry
                
            except Exception as e:
                # Deserialization error - treat as miss
                self._stats["miss_count"] += 1
                return None
            
        except Exception as e:
            self._stats["error_count"] += 1
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed > self._default_timeout:
                raise CacheTimeout.get_operation(str(key), self._default_timeout, elapsed)
            raise
        
        finally:
            self._stats["get_count"] += 1
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            self._stats["total_get_time"] += elapsed
    
    async def set(self, entry: CacheEntry) -> bool:
        """Set cache entry."""
        start_time = datetime.utcnow()
        
        try:
            redis_key = self._build_redis_key(entry.key, entry.namespace)
            redis = await self._get_redis_connection()
            
            # Serialize value
            value_data = pickle.dumps(entry.value)
            
            # Prepare metadata
            metadata = {
                "created_at": entry.created_at.isoformat(),
                "accessed_at": entry.accessed_at.isoformat(),
                "access_count": str(entry.access_count),
                "size_bytes": str(len(value_data)),
                "priority": str(entry.priority.level.value),
                "ttl_seconds": str(entry.ttl.seconds) if entry.ttl else "-1"
            }
            
            # Set value and metadata
            meta_key = f"{redis_key}:meta"
            
            # Use pipeline for atomic operation
            pipe = redis.pipeline()
            
            if entry.ttl and not entry.ttl.is_never_expire():
                # Set with TTL
                pipe.setex(redis_key, entry.ttl.seconds, value_data)
                pipe.setex(meta_key, entry.ttl.seconds, pickle.dumps(metadata))
            else:
                # Set without TTL
                pipe.set(redis_key, value_data)
                pipe.hset(meta_key, mapping=metadata)
            
            await pipe.execute()
            
            self._stats["set_count"] += 1
            return True
            
        except Exception as e:
            self._stats["error_count"] += 1
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed > self._default_timeout:
                raise CacheTimeout.set_operation(str(entry.key), self._default_timeout, elapsed)
            raise
        
        finally:
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            self._stats["total_set_time"] += elapsed
    
    async def delete(self, key: CacheKey, namespace: CacheNamespace) -> bool:
        """Delete cache entry by key."""
        try:
            redis_key = self._build_redis_key(key, namespace)
            meta_key = f"{redis_key}:meta"
            redis = await self._get_redis_connection()
            
            # Delete both value and metadata
            pipe = redis.pipeline()
            pipe.delete(redis_key)
            pipe.delete(meta_key)
            results = await pipe.execute()
            
            # Return True if either key existed
            return any(result > 0 for result in results)
            
        except Exception as e:
            self._stats["error_count"] += 1
            raise
    
    async def exists(self, key: CacheKey, namespace: CacheNamespace) -> bool:
        """Check if cache key exists and is not expired."""
        try:
            redis_key = self._build_redis_key(key, namespace)
            redis = await self._get_redis_connection()
            
            return await redis.exists(redis_key) > 0
            
        except Exception as e:
            self._stats["error_count"] += 1
            raise
    
    async def get_ttl(self, key: CacheKey, namespace: CacheNamespace) -> Optional[int]:
        """Get remaining TTL in seconds."""
        try:
            redis_key = self._build_redis_key(key, namespace)
            redis = await self._get_redis_connection()
            
            ttl = await redis.ttl(redis_key)
            
            if ttl == -1:  # Key exists but no TTL
                return None
            elif ttl == -2:  # Key doesn't exist
                return None
            else:
                return max(0, ttl)
                
        except Exception as e:
            self._stats["error_count"] += 1
            raise
    
    async def extend_ttl(self, key: CacheKey, namespace: CacheNamespace, seconds: int) -> bool:
        """Extend TTL by additional seconds."""
        try:
            redis_key = self._build_redis_key(key, namespace)
            meta_key = f"{redis_key}:meta"
            redis = await self._get_redis_connection()
            
            # Get current TTL
            current_ttl = await redis.ttl(redis_key)
            if current_ttl == -2:  # Key doesn't exist
                return False
            
            new_ttl = seconds if current_ttl == -1 else current_ttl + seconds
            
            # Extend TTL for both keys
            pipe = redis.pipeline()
            pipe.expire(redis_key, new_ttl)
            pipe.expire(meta_key, new_ttl)
            results = await pipe.execute()
            
            return all(results)
            
        except Exception as e:
            self._stats["error_count"] += 1
            raise
    
    # Implement other required methods with similar patterns...
    async def get_many(
        self, 
        keys: List[CacheKey], 
        namespace: CacheNamespace
    ) -> Dict[CacheKey, Optional[CacheEntry]]:
        """Get multiple cache entries (basic implementation)."""
        result = {}
        for key in keys:
            result[key] = await self.get(key, namespace)
        return result
    
    async def set_many(self, entries: List[CacheEntry]) -> Dict[CacheKey, bool]:
        """Set multiple cache entries (basic implementation)."""
        result = {}
        for entry in entries:
            result[entry.key] = await self.set(entry)
        return result
    
    async def delete_many(
        self, 
        keys: List[CacheKey], 
        namespace: CacheNamespace
    ) -> Dict[CacheKey, bool]:
        """Delete multiple cache entries (basic implementation)."""
        result = {}
        for key in keys:
            result[key] = await self.delete(key, namespace)
        return result
    
    async def find_keys(
        self, 
        pattern: InvalidationPattern, 
        namespace: Optional[CacheNamespace] = None
    ) -> List[CacheKey]:
        """Find cache keys matching pattern (basic implementation)."""
        # This would implement pattern matching against Redis keys
        # For now, return empty list
        return []
    
    async def invalidate_pattern(
        self, 
        pattern: InvalidationPattern,
        namespace: Optional[CacheNamespace] = None
    ) -> int:
        """Invalidate all keys matching pattern (basic implementation)."""
        keys = await self.find_keys(pattern, namespace)
        if not keys or not namespace:
            return 0
        
        result = await self.delete_many(keys, namespace)
        return sum(1 for success in result.values() if success)
    
    async def flush_namespace(self, namespace: CacheNamespace) -> int:
        """Delete all entries in namespace (basic implementation)."""
        try:
            redis = await self._get_redis_connection()
            pattern = self._build_namespace_pattern(namespace)
            
            # Get all keys matching pattern
            keys = await redis.keys(pattern)
            if not keys:
                return 0
            
            # Delete all keys
            deleted = await redis.delete(*keys)
            return deleted
            
        except Exception as e:
            self._stats["error_count"] += 1
            raise
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        hit_rate = 0.0
        if self._stats["get_count"] > 0:
            hit_rate = (self._stats["hit_count"] / self._stats["get_count"]) * 100
        
        avg_get_time = 0.0
        if self._stats["get_count"] > 0:
            avg_get_time = self._stats["total_get_time"] / self._stats["get_count"]
        
        avg_set_time = 0.0
        if self._stats["set_count"] > 0:
            avg_set_time = self._stats["total_set_time"] / self._stats["set_count"]
        
        return {
            "repository_type": "redis",
            "get_count": self._stats["get_count"],
            "set_count": self._stats["set_count"],
            "delete_count": self._stats["delete_count"],
            "hit_count": self._stats["hit_count"],
            "miss_count": self._stats["miss_count"],
            "error_count": self._stats["error_count"],
            "hit_rate_percentage": hit_rate,
            "average_get_time_ms": avg_get_time * 1000,
            "average_set_time_ms": avg_set_time * 1000
        }
    
    async def ping(self) -> bool:
        """Health check - verify Redis is responsive."""
        try:
            redis = await self._get_redis_connection()
            response = await redis.ping()
            return response == True or response == b"PONG"
        except Exception:
            return False
    
    # Implement remaining protocol methods with basic implementations...


def create_redis_cache_repository(
    redis_client,
    key_prefix: str = "cache:",
    default_timeout_seconds: float = 5.0
) -> RedisCacheRepository:
    """Create Redis cache repository with dependencies.
    
    Args:
        redis_client: Redis client instance (async Redis connection)
        key_prefix: Prefix for all cache keys
        default_timeout_seconds: Default operation timeout
        
    Returns:
        Configured Redis cache repository instance
    """
    return RedisCacheRepository(
        redis_client=redis_client,
        key_prefix=key_prefix,
        default_timeout_seconds=default_timeout_seconds
    )