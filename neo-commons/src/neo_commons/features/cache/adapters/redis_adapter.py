"""Redis cache backend adapter for neo-commons."""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Set, AsyncContextManager
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

try:
    import redis.asyncio as redis
    from redis.asyncio import Redis, ConnectionPool, RedisCluster
    from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
except ImportError:
    redis = None
    Redis = None
    ConnectionPool = None
    RedisCluster = None
    RedisError = Exception
    RedisConnectionError = Exception

from ..entities.protocols import (
    CacheBackendAdapter, 
    CacheTransaction,
    DistributedCache,
    CacheMetrics,
    CacheEvents
)
from ..entities.config import CacheBackendConfig, CacheInstanceConfig
from ....core.exceptions.infrastructure import (
    CacheError,
    CacheConnectionError,
    CacheTimeoutError,
    CacheSerializationError
)

logger = logging.getLogger(__name__)


class RedisTransaction:
    """Redis transaction implementation."""
    
    def __init__(self, redis_client: Redis):
        self.redis_client = redis_client
        self.transaction = None
        self._operations = []
    
    async def begin(self) -> None:
        """Begin Redis transaction."""
        try:
            self.transaction = self.redis_client.pipeline(transaction=True)
        except Exception as e:
            raise CacheError(f"Failed to begin transaction: {e}")
    
    async def commit(self) -> None:
        """Commit Redis transaction."""
        if not self.transaction:
            raise CacheError("No active transaction")
        
        try:
            await self.transaction.execute()
            self.transaction = None
            self._operations.clear()
        except Exception as e:
            raise CacheError(f"Failed to commit transaction: {e}")
    
    async def rollback(self) -> None:
        """Rollback Redis transaction."""
        if self.transaction:
            self.transaction.reset()
            self.transaction = None
            self._operations.clear()
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in transaction."""
        if not self.transaction:
            raise CacheError("No active transaction")
        
        self.transaction.set(key, value, ex=ttl)
        self._operations.append(("set", key, value, ttl))
    
    async def delete(self, key: str) -> None:
        """Delete key in transaction."""
        if not self.transaction:
            raise CacheError("No active transaction")
        
        self.transaction.delete(key)
        self._operations.append(("delete", key))


class RedisDistributedLock:
    """Redis distributed lock implementation."""
    
    def __init__(self, redis_client: Redis, key: str, timeout: int = 10):
        self.redis_client = redis_client
        self.key = f"lock:{key}"
        self.timeout = timeout
        self.acquired = False
        self._lock_value = None
    
    async def __aenter__(self) -> bool:
        """Acquire lock."""
        import uuid
        self._lock_value = str(uuid.uuid4())
        
        try:
            result = await self.redis_client.set(
                self.key, 
                self._lock_value, 
                nx=True, 
                ex=self.timeout
            )
            self.acquired = bool(result)
            return self.acquired
        except Exception as e:
            logger.error(f"Failed to acquire lock {self.key}: {e}")
            return False
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release lock."""
        if self.acquired and self._lock_value:
            try:
                # Use Lua script to ensure atomic release
                lua_script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
                """
                await self.redis_client.eval(lua_script, 1, self.key, self._lock_value)
            except Exception as e:
                logger.error(f"Failed to release lock {self.key}: {e}")
            finally:
                self.acquired = False
                self._lock_value = None


class RedisDistributedCache(DistributedCache):
    """Redis distributed cache implementation."""
    
    def __init__(self, redis_client: Redis, node_id: Optional[str] = None):
        self.redis_client = redis_client
        self.node_id = node_id or "default"
        self._event_subscribers = []
    
    async def acquire_lock(self, key: str, timeout: int = 10) -> AsyncContextManager[bool]:
        """Acquire distributed lock."""
        return RedisDistributedLock(self.redis_client, key, timeout)
    
    async def notify_invalidation(self, key: str) -> None:
        """Notify other nodes of invalidation."""
        try:
            message = {
                "type": "invalidation",
                "key": key,
                "node_id": self.node_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.redis_client.publish("cache:events", json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to notify invalidation for {key}: {e}")
    
    async def notify_update(self, key: str, value: Any) -> None:
        """Notify other nodes of update."""
        try:
            message = {
                "type": "update",
                "key": key,
                "node_id": self.node_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.redis_client.publish("cache:events", json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to notify update for {key}: {e}")
    
    async def subscribe_events(self, callback: callable) -> None:
        """Subscribe to distributed events."""
        self._event_subscribers.append(callback)
        
        async def event_handler():
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe("cache:events")
            
            try:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        try:
                            event_data = json.loads(message["data"])
                            # Don't process our own events
                            if event_data.get("node_id") != self.node_id:
                                for subscriber in self._event_subscribers:
                                    await subscriber(event_data)
                        except Exception as e:
                            logger.error(f"Failed to process cache event: {e}")
            finally:
                await pubsub.unsubscribe("cache:events")
        
        # Start event handler in background
        asyncio.create_task(event_handler())
    
    async def get_cluster_info(self) -> Dict[str, Any]:
        """Get cluster information."""
        try:
            info = await self.redis_client.info()
            return {
                "node_id": self.node_id,
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory": info.get("used_memory"),
                "used_memory_human": info.get("used_memory_human"),
                "keyspace": {k: v for k, v in info.items() if k.startswith("db")},
            }
        except Exception as e:
            logger.error(f"Failed to get cluster info: {e}")
            return {"error": str(e)}


class RedisCacheMetrics(CacheMetrics):
    """Redis cache metrics implementation."""
    
    def __init__(self, redis_client: Redis, prefix: str = "cache:metrics"):
        self.redis_client = redis_client
        self.prefix = prefix
    
    async def record_hit(self, key: str) -> None:
        """Record cache hit."""
        try:
            await self.redis_client.hincrby(f"{self.prefix}:hits", key, 1)
            await self.redis_client.incr(f"{self.prefix}:total_hits")
        except Exception as e:
            logger.error(f"Failed to record hit for {key}: {e}")
    
    async def record_miss(self, key: str) -> None:
        """Record cache miss."""
        try:
            await self.redis_client.hincrby(f"{self.prefix}:misses", key, 1)
            await self.redis_client.incr(f"{self.prefix}:total_misses")
        except Exception as e:
            logger.error(f"Failed to record miss for {key}: {e}")
    
    async def record_set(self, key: str, size_bytes: int) -> None:
        """Record cache set operation."""
        try:
            await self.redis_client.hincrby(f"{self.prefix}:sets", key, 1)
            await self.redis_client.hincrby(f"{self.prefix}:sizes", key, size_bytes)
            await self.redis_client.incr(f"{self.prefix}:total_sets")
        except Exception as e:
            logger.error(f"Failed to record set for {key}: {e}")
    
    async def record_delete(self, key: str) -> None:
        """Record cache delete operation."""
        try:
            await self.redis_client.hincrby(f"{self.prefix}:deletes", key, 1)
            await self.redis_client.incr(f"{self.prefix}:total_deletes")
        except Exception as e:
            logger.error(f"Failed to record delete for {key}: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            pipe = self.redis_client.pipeline()
            pipe.get(f"{self.prefix}:total_hits")
            pipe.get(f"{self.prefix}:total_misses")
            pipe.get(f"{self.prefix}:total_sets")
            pipe.get(f"{self.prefix}:total_deletes")
            pipe.hlen(f"{self.prefix}:hits")
            pipe.hlen(f"{self.prefix}:misses")
            
            results = await pipe.execute()
            
            total_hits = int(results[0] or 0)
            total_misses = int(results[1] or 0)
            total_sets = int(results[2] or 0)
            total_deletes = int(results[3] or 0)
            unique_hit_keys = int(results[4] or 0)
            unique_miss_keys = int(results[5] or 0)
            
            total_requests = total_hits + total_misses
            hit_rate = (total_hits / total_requests) if total_requests > 0 else 0.0
            
            return {
                "total_hits": total_hits,
                "total_misses": total_misses,
                "total_sets": total_sets,
                "total_deletes": total_deletes,
                "hit_rate": hit_rate,
                "miss_rate": 1.0 - hit_rate,
                "unique_hit_keys": unique_hit_keys,
                "unique_miss_keys": unique_miss_keys,
                "total_requests": total_requests
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"error": str(e)}


class RedisCacheEvents(CacheEvents):
    """Redis cache events implementation."""
    
    def __init__(self, redis_client: Redis):
        self.redis_client = redis_client
        self._callbacks = {
            "hit": [],
            "miss": [],
            "set": [],
            "delete": [],
            "expire": []
        }
    
    async def on_hit(self, key: str, value: Any) -> None:
        """Called on cache hit."""
        for callback in self._callbacks["hit"]:
            try:
                await callback(key, value)
            except Exception as e:
                logger.error(f"Error in hit callback: {e}")
    
    async def on_miss(self, key: str) -> None:
        """Called on cache miss."""
        for callback in self._callbacks["miss"]:
            try:
                await callback(key)
            except Exception as e:
                logger.error(f"Error in miss callback: {e}")
    
    async def on_set(self, key: str, value: Any, ttl: Optional[int]) -> None:
        """Called on cache set."""
        for callback in self._callbacks["set"]:
            try:
                await callback(key, value, ttl)
            except Exception as e:
                logger.error(f"Error in set callback: {e}")
    
    async def on_delete(self, key: str) -> None:
        """Called on cache delete."""
        for callback in self._callbacks["delete"]:
            try:
                await callback(key)
            except Exception as e:
                logger.error(f"Error in delete callback: {e}")
    
    async def on_expire(self, key: str) -> None:
        """Called on cache expiration."""
        for callback in self._callbacks["expire"]:
            try:
                await callback(key)
            except Exception as e:
                logger.error(f"Error in expire callback: {e}")
    
    def add_callback(self, event_type: str, callback: callable) -> None:
        """Add event callback."""
        if event_type in self._callbacks:
            self._callbacks[event_type].append(callback)


class RedisAdapter(CacheBackendAdapter[str, bytes]):
    """Redis cache backend adapter."""
    
    def __init__(self, config: CacheBackendConfig):
        if redis is None:
            raise ImportError("redis package is required for RedisAdapter")
        
        self.config = config
        self.redis_client: Optional[Redis] = None
        self.connection_pool: Optional[ConnectionPool] = None
        self._is_cluster = config.backend_type.value == "redis_cluster"
        self._connected = False
        
        # Optional components
        self.metrics: Optional[RedisCacheMetrics] = None
        self.events: Optional[RedisCacheEvents] = None
        self.distributed: Optional[RedisDistributedCache] = None
    
    async def connect(self) -> None:
        """Connect to Redis."""
        if self._connected:
            return
        
        try:
            if self._is_cluster:
                # Redis Cluster setup
                if not self.config.cluster_nodes:
                    raise CacheConnectionError("Cluster nodes not configured")
                
                startup_nodes = []
                for node in self.config.cluster_nodes:
                    host, port = node.split(":")
                    startup_nodes.append({"host": host, "port": int(port)})
                
                self.redis_client = RedisCluster(
                    startup_nodes=startup_nodes,
                    password=self.config.password,
                    ssl=self.config.ssl,
                    max_connections_per_node=self.config.max_connections_per_node,
                    socket_timeout=self.config.command_timeout,
                    socket_connect_timeout=self.config.connection_timeout,
                    retry_on_timeout=True,
                    require_full_coverage=self.config.cluster_require_full_coverage,
                )
            else:
                # Single Redis instance
                connection_kwargs = self.config.to_connection_kwargs()
                
                self.connection_pool = ConnectionPool(**connection_kwargs)
                self.redis_client = Redis(connection_pool=self.connection_pool)
            
            # Test connection
            await self.redis_client.ping()
            self._connected = True
            
            # Initialize optional components
            if hasattr(self.config, 'enable_metrics') and self.config.enable_metrics:
                self.metrics = RedisCacheMetrics(self.redis_client)
            
            if hasattr(self.config, 'enable_events') and self.config.enable_events:
                self.events = RedisCacheEvents(self.redis_client)
            
            if hasattr(self.config, 'enable_distributed') and self.config.enable_distributed:
                node_id = getattr(self.config, 'node_id', None)
                self.distributed = RedisDistributedCache(self.redis_client, node_id)
            
            logger.info(f"Connected to Redis: {self.config.host}:{self.config.port}")
            
        except Exception as e:
            raise CacheConnectionError(f"Failed to connect to Redis: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis_client:
            try:
                await self.redis_client.aclose()
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")
            finally:
                self.redis_client = None
                self._connected = False
    
    async def get(self, key: str) -> Optional[bytes]:
        """Get value by key."""
        await self._ensure_connected()
        
        try:
            result = await self.redis_client.get(key)
            
            if result is not None:
                if self.metrics:
                    await self.metrics.record_hit(key)
                if self.events:
                    await self.events.on_hit(key, result)
                return result
            else:
                if self.metrics:
                    await self.metrics.record_miss(key)
                if self.events:
                    await self.events.on_miss(key)
                return None
                
        except RedisError as e:
            raise CacheError(f"Redis get error for key {key}: {e}")
        except Exception as e:
            raise CacheError(f"Unexpected error getting key {key}: {e}")
    
    async def set(self, key: str, value: bytes, ttl: Optional[int] = None) -> None:
        """Set key-value pair with optional TTL."""
        await self._ensure_connected()
        
        try:
            effective_ttl = ttl or self.config.default_ttl
            
            await self.redis_client.set(
                key, 
                value, 
                ex=effective_ttl if effective_ttl > 0 else None
            )
            
            if self.metrics:
                await self.metrics.record_set(key, len(value))
            if self.events:
                await self.events.on_set(key, value, effective_ttl)
            if self.distributed:
                await self.distributed.notify_update(key, value)
                
        except RedisError as e:
            raise CacheError(f"Redis set error for key {key}: {e}")
        except Exception as e:
            raise CacheError(f"Unexpected error setting key {key}: {e}")
    
    async def delete(self, key: str) -> bool:
        """Delete key and return whether it existed."""
        await self._ensure_connected()
        
        try:
            result = await self.redis_client.delete(key)
            existed = result > 0
            
            if existed:
                if self.metrics:
                    await self.metrics.record_delete(key)
                if self.events:
                    await self.events.on_delete(key)
                if self.distributed:
                    await self.distributed.notify_invalidation(key)
            
            return existed
            
        except RedisError as e:
            raise CacheError(f"Redis delete error for key {key}: {e}")
        except Exception as e:
            raise CacheError(f"Unexpected error deleting key {key}: {e}")

    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern.
        
        Args:
            pattern: Redis key pattern (e.g., "auth:*", "tenant:123:*")
            
        Returns:
            Number of keys deleted
        """
        await self._ensure_connected()
        
        try:
            # Get all keys matching the pattern
            keys = await self.redis_client.keys(pattern)
            
            if not keys:
                return 0
            
            # Delete all matching keys
            deleted_count = await self.redis_client.delete(*keys)
            
            return deleted_count
            
        except RedisError as e:
            raise CacheError(f"Redis delete pattern error: {e}")
        except Exception as e:
            raise CacheError(f"Unexpected error deleting keys by pattern: {e}")
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        await self._ensure_connected()
        
        try:
            result = await self.redis_client.exists(key)
            return result > 0
        except RedisError as e:
            raise CacheError(f"Redis exists error for key {key}: {e}")
        except Exception as e:
            raise CacheError(f"Unexpected error checking key {key}: {e}")
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key."""
        await self._ensure_connected()
        
        try:
            result = await self.redis_client.expire(key, ttl)
            return bool(result)
        except RedisError as e:
            raise CacheError(f"Redis expire error for key {key}: {e}")
        except Exception as e:
            raise CacheError(f"Unexpected error setting TTL for key {key}: {e}")
    
    async def ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL for key."""
        await self._ensure_connected()
        
        try:
            result = await self.redis_client.ttl(key)
            if result == -2:  # Key doesn't exist
                return None
            elif result == -1:  # Key exists but no TTL
                return None
            else:
                return result
        except RedisError as e:
            raise CacheError(f"Redis TTL error for key {key}: {e}")
        except Exception as e:
            raise CacheError(f"Unexpected error getting TTL for key {key}: {e}")
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        await self._ensure_connected()
        
        try:
            await self.redis_client.flushdb()
        except RedisError as e:
            raise CacheError(f"Redis clear error: {e}")
        except Exception as e:
            raise CacheError(f"Unexpected error clearing cache: {e}")
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        await self._ensure_connected()
        
        try:
            keys = await self.redis_client.keys(pattern)
            return [key.decode() if isinstance(key, bytes) else key for key in keys]
        except RedisError as e:
            raise CacheError(f"Redis keys error with pattern {pattern}: {e}")
        except Exception as e:
            raise CacheError(f"Unexpected error getting keys with pattern {pattern}: {e}")
    
    async def size(self) -> int:
        """Get cache size (number of keys)."""
        await self._ensure_connected()
        
        try:
            return await self.redis_client.dbsize()
        except RedisError as e:
            raise CacheError(f"Redis size error: {e}")
        except Exception as e:
            raise CacheError(f"Unexpected error getting cache size: {e}")
    
    async def info(self) -> Dict[str, Any]:
        """Get cache backend information."""
        await self._ensure_connected()
        
        try:
            info = await self.redis_client.info()
            return {
                "backend_type": self.config.backend_type.value,
                "host": self.config.host,
                "port": self.config.port,
                "database": self.config.database,
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory": info.get("used_memory"),
                "used_memory_human": info.get("used_memory_human"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "is_cluster": self._is_cluster,
                "connected": self._connected,
            }
        except RedisError as e:
            raise CacheError(f"Redis info error: {e}")
        except Exception as e:
            raise CacheError(f"Unexpected error getting cache info: {e}")
    
    async def pipeline(self) -> AsyncContextManager:
        """Get Redis pipeline for batch operations."""
        await self._ensure_connected()
        
        @asynccontextmanager
        async def _pipeline():
            pipe = self.redis_client.pipeline()
            try:
                yield pipe
                await pipe.execute()
            except Exception as e:
                pipe.reset()
                raise CacheError(f"Pipeline error: {e}")
        
        return _pipeline()
    
    async def transaction(self) -> AsyncContextManager[CacheTransaction]:
        """Start cache transaction."""
        await self._ensure_connected()
        
        @asynccontextmanager
        async def _transaction():
            trans = RedisTransaction(self.redis_client)
            try:
                await trans.begin()
                yield trans
                await trans.commit()
            except Exception as e:
                await trans.rollback()
                raise CacheError(f"Transaction error: {e}")
        
        return _transaction()
    
    async def health_check(self) -> bool:
        """Check Redis health."""
        try:
            if not self._connected:
                return False
            
            await self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    async def _ensure_connected(self) -> None:
        """Ensure Redis connection is active."""
        if not self._connected:
            await self.connect()
        
        # Test connection periodically
        try:
            await self.redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis connection lost, reconnecting: {e}")
            self._connected = False
            await self.connect()


class RedisClusterAdapter(RedisAdapter):
    """Redis Cluster cache backend adapter."""
    
    def __init__(self, config: CacheBackendConfig):
        super().__init__(config)
        self._is_cluster = True
    
    async def info(self) -> Dict[str, Any]:
        """Get Redis cluster information."""
        base_info = await super().info()
        
        if self._is_cluster and self.redis_client:
            try:
                cluster_info = await self.redis_client.cluster_info()
                base_info.update({
                    "cluster_state": cluster_info.get("cluster_state"),
                    "cluster_slots_assigned": cluster_info.get("cluster_slots_assigned"),
                    "cluster_slots_ok": cluster_info.get("cluster_slots_ok"),
                    "cluster_known_nodes": cluster_info.get("cluster_known_nodes"),
                    "cluster_size": cluster_info.get("cluster_size"),
                })
            except Exception as e:
                logger.error(f"Failed to get cluster info: {e}")
        
        return base_info