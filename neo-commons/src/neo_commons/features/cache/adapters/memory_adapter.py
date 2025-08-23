"""Memory cache backend adapter for neo-commons."""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Set, AsyncContextManager
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import OrderedDict
from contextlib import asynccontextmanager
import threading
import weakref

from ..entities.protocols import (
    CacheBackendAdapter,
    CacheTransaction,
    CacheMetrics,
    CacheEvents,
    CacheStrategy
)
from ..entities.config import CacheBackendConfig, CacheInstanceConfig
from ....core.exceptions.infrastructure import (
    CacheError,
    CacheKeyError
)

logger = logging.getLogger(__name__)


@dataclass
class MemoryCacheEntry:
    """Memory cache entry with metadata."""
    value: bytes
    created_at: float
    expires_at: Optional[float] = None
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    size_bytes: int = field(init=False)
    tags: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        self.size_bytes = len(self.value) if self.value else 0
    
    @property
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
    
    @property
    def ttl(self) -> Optional[int]:
        """Get remaining TTL in seconds."""
        if self.expires_at is None:
            return None
        remaining = self.expires_at - time.time()
        return max(0, int(remaining)) if remaining > 0 else 0
    
    def access(self) -> None:
        """Record access to this entry."""
        self.access_count += 1
        self.last_accessed = time.time()
    
    def update_ttl(self, ttl: int) -> None:
        """Update TTL for this entry."""
        if ttl > 0:
            self.expires_at = time.time() + ttl
        else:
            self.expires_at = None


class MemoryCacheTransaction:
    """Memory cache transaction implementation."""
    
    def __init__(self, cache_store: Dict[str, MemoryCacheEntry]):
        self.cache_store = cache_store
        self._operations = []
        self._committed = False
        self._rollback_data = {}
    
    async def begin(self) -> None:
        """Begin transaction by backing up current state."""
        self._operations.clear()
        self._rollback_data.clear()
        self._committed = False
    
    async def commit(self) -> None:
        """Commit all operations."""
        if self._committed:
            return
        
        try:
            # All operations are already applied to the store
            # Just mark as committed
            self._committed = True
            self._operations.clear()
            self._rollback_data.clear()
        except Exception as e:
            raise CacheError(f"Failed to commit transaction: {e}")
    
    async def rollback(self) -> None:
        """Rollback all operations."""
        if self._committed:
            return
        
        try:
            # Restore backed up values
            for key, original_value in self._rollback_data.items():
                if original_value is None:
                    self.cache_store.pop(key, None)
                else:
                    self.cache_store[key] = original_value
            
            self._operations.clear()
            self._rollback_data.clear()
        except Exception as e:
            logger.error(f"Failed to rollback transaction: {e}")
    
    async def set(self, key: str, value: bytes, ttl: Optional[int] = None) -> None:
        """Set value in transaction."""
        # Backup original value for rollback
        if key not in self._rollback_data:
            self._rollback_data[key] = self.cache_store.get(key)
        
        # Create new entry
        expires_at = time.time() + ttl if ttl and ttl > 0 else None
        entry = MemoryCacheEntry(
            value=value,
            created_at=time.time(),
            expires_at=expires_at
        )
        
        self.cache_store[key] = entry
        self._operations.append(("set", key, value, ttl))
    
    async def delete(self, key: str) -> None:
        """Delete key in transaction."""
        # Backup original value for rollback
        if key not in self._rollback_data:
            self._rollback_data[key] = self.cache_store.get(key)
        
        self.cache_store.pop(key, None)
        self._operations.append(("delete", key))


class MemoryCacheMetrics(CacheMetrics):
    """Memory cache metrics implementation."""
    
    def __init__(self):
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "hit_keys": set(),
            "miss_keys": set(),
        }
        self._lock = threading.Lock()
    
    async def record_hit(self, key: str) -> None:
        """Record cache hit."""
        with self._lock:
            self._stats["hits"] += 1
            self._stats["hit_keys"].add(key)
    
    async def record_miss(self, key: str) -> None:
        """Record cache miss."""
        with self._lock:
            self._stats["misses"] += 1
            self._stats["miss_keys"].add(key)
    
    async def record_set(self, key: str, size_bytes: int) -> None:
        """Record cache set operation."""
        with self._lock:
            self._stats["sets"] += 1
    
    async def record_delete(self, key: str) -> None:
        """Record cache delete operation."""
        with self._lock:
            self._stats["deletes"] += 1
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total_requests) if total_requests > 0 else 0.0
            
            return {
                "total_hits": self._stats["hits"],
                "total_misses": self._stats["misses"],
                "total_sets": self._stats["sets"],
                "total_deletes": self._stats["deletes"],
                "hit_rate": hit_rate,
                "miss_rate": 1.0 - hit_rate,
                "unique_hit_keys": len(self._stats["hit_keys"]),
                "unique_miss_keys": len(self._stats["miss_keys"]),
                "total_requests": total_requests
            }


class MemoryCacheEvents(CacheEvents):
    """Memory cache events implementation."""
    
    def __init__(self):
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


class MemoryAdapter(CacheBackendAdapter[str, bytes]):
    """Memory cache backend adapter with LRU eviction and TTL support."""
    
    def __init__(self, config: CacheBackendConfig, max_size: int = 1000):
        self.config = config
        self.max_size = max_size
        self.strategy = getattr(config, 'eviction_policy', 'lru')
        
        # Thread-safe storage
        self._store: Dict[str, MemoryCacheEntry] = {}
        self._access_order: OrderedDict[str, None] = OrderedDict()
        self._lock = asyncio.Lock()
        
        # Optional components
        self.metrics: Optional[MemoryCacheMetrics] = None
        self.events: Optional[MemoryCacheEvents] = None
        
        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_interval = 60  # seconds
        
        # Size tracking
        self._total_size_bytes = 0
        self._max_memory_bytes = getattr(config, 'max_memory_mb', 100) * 1024 * 1024
    
    async def connect(self) -> None:
        """Initialize memory cache."""
        if hasattr(self.config, 'enable_metrics') and self.config.enable_metrics:
            self.metrics = MemoryCacheMetrics()
        
        if hasattr(self.config, 'enable_events') and self.config.enable_events:
            self.events = MemoryCacheEvents()
        
        # Start background cleanup task
        self._cleanup_task = asyncio.create_task(self._background_cleanup())
        
        logger.info(f"Memory cache initialized with max_size={self.max_size}")
    
    async def disconnect(self) -> None:
        """Cleanup memory cache."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        async with self._lock:
            self._store.clear()
            self._access_order.clear()
            self._total_size_bytes = 0
    
    async def get(self, key: str) -> Optional[bytes]:
        """Get value by key."""
        async with self._lock:
            entry = self._store.get(key)
            
            if entry is None:
                if self.metrics:
                    await self.metrics.record_miss(key)
                if self.events:
                    await self.events.on_miss(key)
                return None
            
            # Check expiration
            if entry.is_expired:
                await self._remove_entry(key)
                if self.metrics:
                    await self.metrics.record_miss(key)
                if self.events:
                    await self.events.on_miss(key)
                    await self.events.on_expire(key)
                return None
            
            # Update access info
            entry.access()
            self._update_access_order(key)
            
            if self.metrics:
                await self.metrics.record_hit(key)
            if self.events:
                await self.events.on_hit(key, entry.value)
            
            return entry.value
    
    async def set(self, key: str, value: bytes, ttl: Optional[int] = None) -> None:
        """Set key-value pair with optional TTL."""
        async with self._lock:
            # Remove existing entry if present
            if key in self._store:
                await self._remove_entry(key)
            
            # Create new entry
            expires_at = time.time() + ttl if ttl and ttl > 0 else None
            entry = MemoryCacheEntry(
                value=value,
                created_at=time.time(),
                expires_at=expires_at
            )
            
            # Check if we need to evict entries
            await self._ensure_capacity(entry.size_bytes)
            
            # Add new entry
            self._store[key] = entry
            self._access_order[key] = None
            self._total_size_bytes += entry.size_bytes
            
            if self.metrics:
                await self.metrics.record_set(key, len(value))
            if self.events:
                await self.events.on_set(key, value, ttl)
    
    async def delete(self, key: str) -> bool:
        """Delete key and return whether it existed."""
        async with self._lock:
            if key in self._store:
                await self._remove_entry(key)
                if self.metrics:
                    await self.metrics.record_delete(key)
                if self.events:
                    await self.events.on_delete(key)
                return True
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists (and not expired)."""
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return False
            
            if entry.is_expired:
                await self._remove_entry(key)
                return False
            
            return True
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key."""
        async with self._lock:
            entry = self._store.get(key)
            if entry is None or entry.is_expired:
                return False
            
            entry.update_ttl(ttl)
            return True
    
    async def ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL for key."""
        async with self._lock:
            entry = self._store.get(key)
            if entry is None or entry.is_expired:
                return None
            
            return entry.ttl
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._store.clear()
            self._access_order.clear()
            self._total_size_bytes = 0
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        import fnmatch
        
        async with self._lock:
            # Clean expired entries first
            await self._cleanup_expired()
            
            all_keys = list(self._store.keys())
            if pattern == "*":
                return all_keys
            
            return [key for key in all_keys if fnmatch.fnmatch(key, pattern)]
    
    async def size(self) -> int:
        """Get cache size (number of keys)."""
        async with self._lock:
            await self._cleanup_expired()
            return len(self._store)
    
    async def info(self) -> Dict[str, Any]:
        """Get cache backend information."""
        async with self._lock:
            await self._cleanup_expired()
            
            total_entries = len(self._store)
            avg_size = self._total_size_bytes / total_entries if total_entries > 0 else 0
            
            # Calculate entry age statistics
            current_time = time.time()
            ages = [current_time - entry.created_at for entry in self._store.values()]
            avg_age = sum(ages) / len(ages) if ages else 0
            
            return {
                "backend_type": self.config.backend_type.value,
                "total_entries": total_entries,
                "max_entries": self.max_size,
                "total_size_bytes": self._total_size_bytes,
                "max_size_bytes": self._max_memory_bytes,
                "average_entry_size": avg_size,
                "average_age_seconds": avg_age,
                "eviction_policy": self.strategy,
                "memory_usage_percent": (self._total_size_bytes / self._max_memory_bytes) * 100,
                "capacity_usage_percent": (total_entries / self.max_size) * 100,
            }
    
    async def transaction(self) -> AsyncContextManager[CacheTransaction]:
        """Start cache transaction."""
        @asynccontextmanager
        async def _transaction():
            trans = MemoryCacheTransaction(self._store)
            try:
                await trans.begin()
                yield trans
                await trans.commit()
            except Exception as e:
                await trans.rollback()
                raise CacheError(f"Transaction error: {e}")
        
        return _transaction()
    
    async def health_check(self) -> bool:
        """Check memory cache health."""
        try:
            # Simple health check - verify we can access the store
            async with self._lock:
                return True
        except Exception as e:
            logger.error(f"Memory cache health check failed: {e}")
            return False
    
    async def _remove_entry(self, key: str) -> None:
        """Remove entry from store and update size tracking."""
        entry = self._store.pop(key, None)
        if entry:
            self._total_size_bytes -= entry.size_bytes
        self._access_order.pop(key, None)
    
    def _update_access_order(self, key: str) -> None:
        """Update access order for LRU eviction."""
        if key in self._access_order:
            del self._access_order[key]
        self._access_order[key] = None
    
    async def _ensure_capacity(self, new_entry_size: int) -> None:
        """Ensure we have capacity for a new entry."""
        # Check memory limit
        while (self._total_size_bytes + new_entry_size > self._max_memory_bytes and 
               self._store):
            await self._evict_one()
        
        # Check entry count limit
        while len(self._store) >= self.max_size and self._store:
            await self._evict_one()
    
    async def _evict_one(self) -> None:
        """Evict one entry based on strategy."""
        if not self._store:
            return
        
        if self.strategy.lower() == 'lru':
            # Evict least recently used
            key = next(iter(self._access_order))
            await self._remove_entry(key)
        elif self.strategy.lower() == 'lfu':
            # Evict least frequently used
            min_key = min(self._store.keys(), 
                         key=lambda k: self._store[k].access_count)
            await self._remove_entry(min_key)
        else:
            # Default to LRU
            key = next(iter(self._access_order))
            await self._remove_entry(key)
    
    async def _cleanup_expired(self) -> None:
        """Remove all expired entries."""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._store.items()
            if entry.expires_at and entry.expires_at <= current_time
        ]
        
        for key in expired_keys:
            await self._remove_entry(key)
            if self.events:
                await self.events.on_expire(key)
    
    async def _background_cleanup(self) -> None:
        """Background task to clean up expired entries."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                async with self._lock:
                    await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background cleanup: {e}")
                await asyncio.sleep(self._cleanup_interval)


class LRUMemoryAdapter(MemoryAdapter):
    """Memory adapter with strict LRU eviction."""
    
    def __init__(self, config: CacheBackendConfig, max_size: int = 1000):
        super().__init__(config, max_size)
        self.strategy = 'lru'


class LFUMemoryAdapter(MemoryAdapter):
    """Memory adapter with LFU eviction."""
    
    def __init__(self, config: CacheBackendConfig, max_size: int = 1000):
        super().__init__(config, max_size)
        self.strategy = 'lfu'