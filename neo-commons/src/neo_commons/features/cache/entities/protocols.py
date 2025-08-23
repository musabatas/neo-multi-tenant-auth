"""Cache protocols for neo-commons.

This module defines the protocol interfaces for caching functionality,
supporting dynamic implementations, multi-tenancy, and enterprise features.
"""

from abc import abstractmethod
from typing import (
    Protocol, 
    runtime_checkable, 
    Optional, 
    Dict, 
    Any, 
    List, 
    Set, 
    Union,
    AsyncContextManager,
    Callable,
    TypeVar,
    Generic
)
from datetime import datetime, timedelta
from enum import Enum
import asyncio

T = TypeVar('T')
K = TypeVar('K')  # Key type
V = TypeVar('V')  # Value type


class CacheBackend(str, Enum):
    """Supported cache backend types."""
    MEMORY = "memory"
    REDIS = "redis" 
    REDIS_CLUSTER = "redis_cluster"
    MEMCACHED = "memcached"
    HYBRID = "hybrid"


class CacheStrategy(str, Enum):
    """Cache invalidation strategies."""
    TTL = "ttl"
    LRU = "lru"
    LFU = "lfu"
    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"
    REFRESH_AHEAD = "refresh_ahead"


class SerializationFormat(str, Enum):
    """Serialization formats for cache values."""
    JSON = "json"
    PICKLE = "pickle"
    MSGPACK = "msgpack"
    PROTOBUF = "protobuf"
    PLAIN_TEXT = "plain_text"


@runtime_checkable
class CacheKey(Protocol):
    """Protocol for cache key generation and management."""
    
    @abstractmethod
    def build(self, *args: Any, **kwargs: Any) -> str:
        """Build a cache key from arguments."""
        ...
    
    @abstractmethod
    def parse(self, key: str) -> Dict[str, Any]:
        """Parse a cache key back to components."""
        ...
    
    @abstractmethod
    def validate(self, key: str) -> bool:
        """Validate cache key format."""
        ...
    
    @property
    @abstractmethod
    def prefix(self) -> str:
        """Get the key prefix."""
        ...


@runtime_checkable
class CacheSerializer(Protocol[T]):
    """Protocol for cache value serialization."""
    
    @abstractmethod
    async def serialize(self, value: T) -> bytes:
        """Serialize value to bytes."""
        ...
    
    @abstractmethod
    async def deserialize(self, data: bytes) -> T:
        """Deserialize bytes to value."""
        ...
    
    @property
    @abstractmethod
    def format(self) -> SerializationFormat:
        """Get serialization format."""
        ...


@runtime_checkable
class CacheCompressor(Protocol):
    """Protocol for cache value compression."""
    
    @abstractmethod
    async def compress(self, data: bytes) -> bytes:
        """Compress data."""
        ...
    
    @abstractmethod
    async def decompress(self, data: bytes) -> bytes:
        """Decompress data."""
        ...
    
    @property
    @abstractmethod
    def algorithm(self) -> str:
        """Get compression algorithm name."""
        ...


@runtime_checkable
class CacheMetrics(Protocol):
    """Protocol for cache performance metrics."""
    
    @abstractmethod
    async def record_hit(self, key: str) -> None:
        """Record cache hit."""
        ...
    
    @abstractmethod
    async def record_miss(self, key: str) -> None:
        """Record cache miss."""
        ...
    
    @abstractmethod
    async def record_set(self, key: str, size_bytes: int) -> None:
        """Record cache set operation."""
        ...
    
    @abstractmethod
    async def record_delete(self, key: str) -> None:
        """Record cache delete operation."""
        ...
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        ...


@runtime_checkable
class CacheEvents(Protocol):
    """Protocol for cache event handling."""
    
    @abstractmethod
    async def on_hit(self, key: str, value: Any) -> None:
        """Called on cache hit."""
        ...
    
    @abstractmethod
    async def on_miss(self, key: str) -> None:
        """Called on cache miss."""
        ...
    
    @abstractmethod
    async def on_set(self, key: str, value: Any, ttl: Optional[int]) -> None:
        """Called on cache set."""
        ...
    
    @abstractmethod
    async def on_delete(self, key: str) -> None:
        """Called on cache delete."""
        ...
    
    @abstractmethod
    async def on_expire(self, key: str) -> None:
        """Called on cache expiration."""
        ...


@runtime_checkable
class CacheBackendAdapter(Protocol[K, V]):
    """Protocol for cache backend implementations."""
    
    @abstractmethod
    async def get(self, key: K) -> Optional[V]:
        """Get value by key."""
        ...
    
    @abstractmethod
    async def set(self, key: K, value: V, ttl: Optional[int] = None) -> None:
        """Set key-value pair with optional TTL."""
        ...
    
    @abstractmethod
    async def delete(self, key: K) -> bool:
        """Delete key and return whether it existed."""
        ...
    
    @abstractmethod
    async def exists(self, key: K) -> bool:
        """Check if key exists."""
        ...
    
    @abstractmethod
    async def expire(self, key: K, ttl: int) -> bool:
        """Set TTL for existing key."""
        ...
    
    @abstractmethod
    async def ttl(self, key: K) -> Optional[int]:
        """Get remaining TTL for key."""
        ...
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries."""
        ...
    
    @abstractmethod
    async def keys(self, pattern: str = "*") -> List[K]:
        """Get keys matching pattern."""
        ...
    
    @abstractmethod
    async def size(self) -> int:
        """Get cache size (number of keys)."""
        ...
    
    @abstractmethod
    async def info(self) -> Dict[str, Any]:
        """Get cache backend information."""
        ...


@runtime_checkable
class CacheTransaction(Protocol):
    """Protocol for cache transactions."""
    
    @abstractmethod
    async def begin(self) -> None:
        """Begin transaction."""
        ...
    
    @abstractmethod
    async def commit(self) -> None:
        """Commit transaction."""
        ...
    
    @abstractmethod
    async def rollback(self) -> None:
        """Rollback transaction."""
        ...
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in transaction."""
        ...
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete key in transaction."""
        ...


@runtime_checkable
class CacheInvalidation(Protocol):
    """Protocol for cache invalidation strategies."""
    
    @abstractmethod
    async def invalidate_key(self, key: str) -> None:
        """Invalidate a specific key."""
        ...
    
    @abstractmethod
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate keys matching pattern."""
        ...
    
    @abstractmethod
    async def invalidate_tags(self, tags: List[str]) -> int:
        """Invalidate keys by tags."""
        ...
    
    @abstractmethod
    async def schedule_invalidation(self, key: str, when: datetime) -> None:
        """Schedule future invalidation."""
        ...
    
    @abstractmethod
    async def bulk_invalidate(self, keys: List[str]) -> int:
        """Bulk invalidate multiple keys."""
        ...


@runtime_checkable
class CacheWarmup(Protocol):
    """Protocol for cache warming strategies."""
    
    @abstractmethod
    async def warmup_key(self, key: str, loader: Callable) -> Any:
        """Warmup a specific key."""
        ...
    
    @abstractmethod
    async def warmup_pattern(self, pattern: str, loader: Callable) -> int:
        """Warmup keys matching pattern."""
        ...
    
    @abstractmethod
    async def schedule_warmup(self, key: str, loader: Callable, when: datetime) -> None:
        """Schedule future warmup."""
        ...
    
    @abstractmethod
    async def bulk_warmup(self, items: Dict[str, Callable]) -> int:
        """Bulk warmup multiple keys."""
        ...


@runtime_checkable
class DistributedCache(Protocol):
    """Protocol for distributed cache coordination."""
    
    @abstractmethod
    async def acquire_lock(self, key: str, timeout: int = 10) -> AsyncContextManager[bool]:
        """Acquire distributed lock."""
        ...
    
    @abstractmethod
    async def notify_invalidation(self, key: str) -> None:
        """Notify other nodes of invalidation."""
        ...
    
    @abstractmethod
    async def notify_update(self, key: str, value: Any) -> None:
        """Notify other nodes of update."""
        ...
    
    @abstractmethod
    async def subscribe_events(self, callback: Callable) -> None:
        """Subscribe to distributed events."""
        ...
    
    @abstractmethod
    async def get_cluster_info(self) -> Dict[str, Any]:
        """Get cluster information."""
        ...


@runtime_checkable
class TenantAwareCache(Protocol):
    """Protocol for tenant-aware caching."""
    
    @abstractmethod
    async def get_tenant_key(self, tenant_id: str, key: str) -> str:
        """Build tenant-specific key."""
        ...
    
    @abstractmethod
    async def invalidate_tenant(self, tenant_id: str) -> int:
        """Invalidate all cache for tenant."""
        ...
    
    @abstractmethod
    async def get_tenant_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get cache stats for tenant."""
        ...
    
    @abstractmethod
    async def set_tenant_quota(self, tenant_id: str, max_keys: int, max_memory: int) -> None:
        """Set cache quota for tenant."""
        ...
    
    @abstractmethod
    async def check_tenant_quota(self, tenant_id: str) -> Dict[str, Any]:
        """Check tenant quota usage."""
        ...


@runtime_checkable
class Cache(Protocol[T]):
    """Main cache protocol combining all cache functionality."""
    
    # Basic operations
    @abstractmethod
    async def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """Get value by key."""
        ...
    
    @abstractmethod
    async def set(self, key: str, value: T, ttl: Optional[int] = None, tags: Optional[List[str]] = None) -> None:
        """Set key-value pair."""
        ...
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key."""
        ...
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        ...
    
    # Advanced operations
    @abstractmethod
    async def get_or_set(self, key: str, loader: Callable, ttl: Optional[int] = None) -> T:
        """Get value or set using loader function."""
        ...
    
    @abstractmethod
    async def get_many(self, keys: List[str]) -> Dict[str, Optional[T]]:
        """Get multiple values."""
        ...
    
    @abstractmethod
    async def set_many(self, items: Dict[str, T], ttl: Optional[int] = None) -> None:
        """Set multiple key-value pairs."""
        ...
    
    @abstractmethod
    async def delete_many(self, keys: List[str]) -> int:
        """Delete multiple keys."""
        ...
    
    # Pattern operations
    @abstractmethod
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        ...
    
    @abstractmethod
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        ...
    
    # TTL operations
    @abstractmethod
    async def ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL."""
        ...
    
    @abstractmethod
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key."""
        ...
    
    @abstractmethod
    async def persist(self, key: str) -> bool:
        """Remove TTL from key."""
        ...
    
    # Transaction support
    @abstractmethod
    async def transaction(self) -> AsyncContextManager[CacheTransaction]:
        """Start cache transaction."""
        ...
    
    # Management operations
    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries."""
        ...
    
    @abstractmethod
    async def size(self) -> int:
        """Get cache size."""
        ...
    
    @abstractmethod
    async def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        ...
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check cache health."""
        ...
    
    @abstractmethod
    async def close(self) -> None:
        """Close cache connections."""
        ...


@runtime_checkable
class CacheFactory(Protocol):
    """Protocol for cache factory implementations."""
    
    @abstractmethod
    async def create_cache(self, 
                          name: str,
                          backend: CacheBackend,
                          config: Dict[str, Any]) -> Cache:
        """Create cache instance."""
        ...
    
    @abstractmethod
    async def get_cache(self, name: str) -> Optional[Cache]:
        """Get existing cache instance."""
        ...
    
    @abstractmethod
    async def list_caches(self) -> List[str]:
        """List all cache instances."""
        ...
    
    @abstractmethod
    async def destroy_cache(self, name: str) -> None:
        """Destroy cache instance."""
        ...


@runtime_checkable
class CacheRegistry(Protocol):
    """Protocol for cache registry management."""
    
    @abstractmethod
    async def register_cache(self, name: str, cache: Cache) -> None:
        """Register cache instance."""
        ...
    
    @abstractmethod
    async def unregister_cache(self, name: str) -> None:
        """Unregister cache instance."""
        ...
    
    @abstractmethod
    async def get_cache(self, name: str) -> Optional[Cache]:
        """Get cache by name."""
        ...
    
    @abstractmethod
    async def get_default_cache(self) -> Cache:
        """Get default cache instance."""
        ...
    
    @abstractmethod
    async def list_caches(self) -> Dict[str, Cache]:
        """List all registered caches."""
        ...
    
    @abstractmethod
    async def configure_default(self, name: str) -> None:
        """Set default cache."""
        ...