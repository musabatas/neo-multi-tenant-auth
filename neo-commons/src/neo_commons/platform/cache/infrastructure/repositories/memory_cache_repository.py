"""Memory cache repository.

ONLY in-memory implementation - implements cache storage in memory
for development, testing, and single-instance deployments.

Following maximum separation architecture - one file = one purpose.
"""

import asyncio
import time
from collections import defaultdict, OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from weakref import WeakSet

from ...core.entities.cache_entry import CacheEntry
from ...core.entities.cache_namespace import CacheNamespace, EvictionPolicy
from ...core.value_objects.cache_key import CacheKey
from ...core.value_objects.invalidation_pattern import InvalidationPattern


class MemoryCache:
    """Thread-safe in-memory cache storage."""
    
    def __init__(self):
        self._cache: Dict[str, CacheEntry] = OrderedDict()
        self._namespace_data: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0,
            "expired_cleanups": 0,
            "total_memory_bytes": 0,
        }
        self._lock = asyncio.Lock()
        self._observers: WeakSet = WeakSet()
        
    async def get(self, full_key: str) -> Optional[CacheEntry]:
        """Get cache entry by full key."""
        async with self._lock:
            entry = self._cache.get(full_key)
            
            if entry is None:
                self._stats["misses"] += 1
                return None
                
            # Check expiration
            if entry.is_expired():
                # Remove expired entry
                del self._cache[full_key]
                self._stats["expired_cleanups"] += 1
                self._stats["misses"] += 1
                return None
            
            # Update access tracking
            entry.touch()
            
            # Move to end for LRU tracking
            self._cache.move_to_end(full_key)
            
            self._stats["hits"] += 1
            return entry
            
    async def set(self, full_key: str, entry: CacheEntry) -> bool:
        """Set cache entry."""
        async with self._lock:
            # Remove existing entry if it exists
            if full_key in self._cache:
                del self._cache[full_key]
            
            # Add new entry
            self._cache[full_key] = entry
            self._stats["sets"] += 1
            
            # Update memory usage estimate
            self._update_memory_stats()
            
            return True
    
    async def delete(self, full_key: str) -> bool:
        """Delete cache entry by full key."""
        async with self._lock:
            if full_key in self._cache:
                del self._cache[full_key]
                self._stats["deletes"] += 1
                self._update_memory_stats()
                return True
            return False
    
    async def exists(self, full_key: str) -> bool:
        """Check if key exists and is not expired."""
        entry = await self.get(full_key)
        return entry is not None
    
    async def get_all_keys(self) -> List[str]:
        """Get all non-expired keys."""
        async with self._lock:
            # Clean expired entries first
            await self._cleanup_expired()
            return list(self._cache.keys())
    
    async def find_keys_by_pattern(self, pattern: InvalidationPattern) -> List[str]:
        """Find keys matching pattern."""
        async with self._lock:
            # Clean expired entries first  
            await self._cleanup_expired()
            
            matching_keys = []
            compiled_regex = pattern.get_compiled_regex()
            
            for key in self._cache.keys():
                if compiled_regex:
                    if compiled_regex.search(key):
                        matching_keys.append(key)
                elif pattern.matches(key):
                    matching_keys.append(key)
                    
            return matching_keys
    
    async def delete_by_pattern(self, pattern: InvalidationPattern) -> int:
        """Delete all keys matching pattern."""
        matching_keys = await self.find_keys_by_pattern(pattern)
        
        async with self._lock:
            deleted_count = 0
            for key in matching_keys:
                if key in self._cache:
                    del self._cache[key]
                    deleted_count += 1
            
            self._stats["deletes"] += deleted_count
            self._update_memory_stats()
            return deleted_count
    
    async def flush_namespace(self, namespace_key: str) -> int:
        """Delete all entries in namespace."""
        namespace_prefix = f"{namespace_key}:"
        pattern = InvalidationPattern.prefix(namespace_prefix)
        return await self.delete_by_pattern(pattern)
    
    async def get_size(self) -> int:
        """Get total number of entries."""
        async with self._lock:
            await self._cleanup_expired()
            return len(self._cache)
    
    async def get_memory_usage(self) -> int:
        """Get estimated memory usage in bytes."""
        return self._stats["total_memory_bytes"]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        async with self._lock:
            await self._cleanup_expired()
            
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0.0
            
            return {
                **self._stats,
                "total_keys": len(self._cache),
                "hit_rate_percent": hit_rate,
                "total_requests": total_requests,
            }
    
    async def cleanup_expired(self) -> int:
        """Remove all expired entries."""
        async with self._lock:
            return await self._cleanup_expired()
    
    async def clear(self):
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            self._namespace_data.clear()
            self._stats["deletes"] += 1  # Count as single delete operation
            self._update_memory_stats()
    
    async def _cleanup_expired(self) -> int:
        """Internal method to clean up expired entries."""
        expired_keys = []
        
        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            self._stats["expired_cleanups"] += len(expired_keys)
            self._update_memory_stats()
        
        return len(expired_keys)
    
    def _update_memory_stats(self):
        """Update memory usage statistics (rough estimate)."""
        total_bytes = 0
        
        for entry in self._cache.values():
            # Rough estimation: string overhead + value size + metadata
            total_bytes += len(str(entry.key)) * 4  # Unicode overhead
            total_bytes += entry.size_bytes.bytes if entry.size_bytes else 100  # Value estimate
            total_bytes += 200  # Metadata overhead estimate
        
        self._stats["total_memory_bytes"] = total_bytes


class MemoryCacheRepository:
    """Memory-based cache repository implementation.
    
    Features:
    - In-memory storage with thread safety
    - TTL expiration handling
    - Pattern-based invalidation
    - LRU eviction policy
    - Statistics and monitoring
    - Namespace support
    - Development/testing optimized
    """
    
    def __init__(self, max_entries: int = 10000):
        """Initialize memory cache repository.
        
        Args:
            max_entries: Maximum number of entries before eviction
        """
        self._cache = MemoryCache()
        self._max_entries = max_entries
        self._namespaces: Dict[str, CacheNamespace] = {}
        self._is_healthy = True
        
    def _get_full_key(self, key: CacheKey, namespace: CacheNamespace) -> str:
        """Generate full cache key with namespace."""
        return namespace.get_full_key(key.value)
    
    async def get(self, key: CacheKey, namespace: CacheNamespace) -> Optional[CacheEntry]:
        """Get cache entry by key."""
        full_key = self._get_full_key(key, namespace)
        return await self._cache.get(full_key)
    
    async def set(self, entry: CacheEntry) -> bool:
        """Set cache entry."""
        full_key = self._get_full_key(entry.key, entry.namespace)
        
        # Check capacity and evict if necessary
        current_size = await self._cache.get_size()
        if current_size >= self._max_entries:
            await self._evict_entries(1)
        
        # Store namespace reference
        namespace_key = str(entry.namespace)
        if namespace_key not in self._namespaces:
            self._namespaces[namespace_key] = entry.namespace
        
        return await self._cache.set(full_key, entry)
    
    async def delete(self, key: CacheKey, namespace: CacheNamespace) -> bool:
        """Delete cache entry by key."""
        full_key = self._get_full_key(key, namespace)
        return await self._cache.delete(full_key)
    
    async def exists(self, key: CacheKey, namespace: CacheNamespace) -> bool:
        """Check if cache key exists and is not expired."""
        full_key = self._get_full_key(key, namespace)
        return await self._cache.exists(full_key)
    
    async def get_ttl(self, key: CacheKey, namespace: CacheNamespace) -> Optional[int]:
        """Get remaining TTL in seconds."""
        entry = await self.get(key, namespace)
        if entry is None:
            return None
        
        return entry.time_until_expiry()
    
    async def extend_ttl(self, key: CacheKey, namespace: CacheNamespace, seconds: int) -> bool:
        """Extend TTL by additional seconds."""
        entry = await self.get(key, namespace)
        if entry is None:
            return False
        
        if entry.ttl:
            # Create new TTL with extended time
            from ...core.value_objects.cache_ttl import CacheTTL
            new_ttl = CacheTTL(entry.ttl.seconds + seconds)
            entry.ttl = new_ttl
            
            # Update the entry
            return await self.set(entry)
        
        return False
    
    # Batch operations
    async def get_many(
        self, 
        keys: List[CacheKey], 
        namespace: CacheNamespace
    ) -> Dict[CacheKey, Optional[CacheEntry]]:
        """Get multiple cache entries."""
        results = {}
        
        for key in keys:
            entry = await self.get(key, namespace)
            results[key] = entry
            
        return results
    
    async def set_many(self, entries: List[CacheEntry]) -> Dict[CacheKey, bool]:
        """Set multiple cache entries."""
        results = {}
        
        for entry in entries:
            success = await self.set(entry)
            results[entry.key] = success
            
        return results
    
    async def delete_many(
        self, 
        keys: List[CacheKey], 
        namespace: CacheNamespace
    ) -> Dict[CacheKey, bool]:
        """Delete multiple cache entries."""
        results = {}
        
        for key in keys:
            success = await self.delete(key, namespace)
            results[key] = success
            
        return results
    
    # Pattern operations
    async def find_keys(
        self, 
        pattern: InvalidationPattern, 
        namespace: Optional[CacheNamespace] = None
    ) -> List[CacheKey]:
        """Find cache keys matching pattern."""
        if namespace:
            # Add namespace prefix to pattern
            namespace_prefix = f"{namespace}:"
            if pattern.pattern_type.value == "prefix":
                adjusted_pattern = InvalidationPattern.prefix(f"{namespace_prefix}{pattern.pattern}")
            else:
                adjusted_pattern = InvalidationPattern.wildcard(f"{namespace_prefix}{pattern.pattern}")
        else:
            adjusted_pattern = pattern
        
        matching_full_keys = await self._cache.find_keys_by_pattern(adjusted_pattern)
        
        # Convert back to CacheKey objects, removing namespace prefix
        cache_keys = []
        for full_key in matching_full_keys:
            if namespace:
                namespace_prefix = f"{namespace}:"
                if full_key.startswith(namespace_prefix):
                    key_value = full_key[len(namespace_prefix):]
                    cache_keys.append(CacheKey(key_value))
            else:
                # Extract key part after namespace
                parts = full_key.split(":", 2)
                if len(parts) >= 2:
                    key_value = ":".join(parts[2:]) if len(parts) > 2 else parts[1]
                    cache_keys.append(CacheKey(key_value))
                    
        return cache_keys
    
    async def invalidate_pattern(
        self, 
        pattern: InvalidationPattern,
        namespace: Optional[CacheNamespace] = None
    ) -> int:
        """Invalidate all keys matching pattern."""
        if namespace:
            namespace_prefix = f"{namespace}:"
            adjusted_pattern = InvalidationPattern.prefix(f"{namespace_prefix}{pattern.pattern}")
        else:
            adjusted_pattern = pattern
        
        return await self._cache.delete_by_pattern(adjusted_pattern)
    
    # Namespace operations
    async def flush_namespace(self, namespace: CacheNamespace) -> int:
        """Delete all entries in namespace."""
        namespace_key = str(namespace)
        deleted_count = await self._cache.flush_namespace(namespace_key)
        
        # Remove namespace reference
        if namespace_key in self._namespaces:
            del self._namespaces[namespace_key]
        
        return deleted_count
    
    async def get_namespace_size(self, namespace: CacheNamespace) -> int:
        """Get number of entries in namespace."""
        namespace_pattern = InvalidationPattern.prefix(f"{namespace}:")
        matching_keys = await self._cache.find_keys_by_pattern(namespace_pattern)
        return len(matching_keys)
    
    async def get_namespace_memory(self, namespace: CacheNamespace) -> int:
        """Get memory usage of namespace in bytes (rough estimate)."""
        namespace_pattern = InvalidationPattern.prefix(f"{namespace}:")
        matching_keys = await self._cache.find_keys_by_pattern(namespace_pattern)
        
        total_bytes = 0
        for key in matching_keys:
            entry = await self._cache.get(key)
            if entry:
                total_bytes += entry.size_bytes.bytes if entry.size_bytes else 100
        
        return total_bytes
    
    async def list_namespaces(self) -> List[CacheNamespace]:
        """List all available namespaces."""
        return list(self._namespaces.values())
    
    # Statistics and monitoring
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        base_stats = await self._cache.get_stats()
        
        return {
            **base_stats,
            "implementation": "memory",
            "max_entries": self._max_entries,
            "namespace_count": len(self._namespaces),
            "eviction_policy": "lru",
            "memory_limit_bytes": None,  # No hard limit in memory implementation
        }
    
    async def get_info(self) -> Dict[str, Any]:
        """Get cache implementation information."""
        return {
            "implementation": "memory",
            "version": "1.0.0",
            "memory_limit": None,
            "max_entries": self._max_entries,
            "eviction_policy": "lru",
            "connection_status": "healthy" if self._is_healthy else "unhealthy",
            "features": [
                "ttl_support",
                "pattern_invalidation", 
                "namespace_support",
                "batch_operations",
                "statistics",
                "thread_safe",
            ],
            "thread_safe": True,
            "persistent": False,
            "distributed": False,
        }
    
    async def ping(self) -> bool:
        """Health check - verify cache is responsive."""
        try:
            # Simple operation to test responsiveness
            test_key = CacheKey("__health_check__")
            test_namespace = CacheNamespace(
                name="system",
                description="Health check",
                default_ttl=None,
                max_entries=1,
                eviction_policy=EvictionPolicy.LRU
            )
            
            # Quick set and get test
            from datetime import datetime, timezone
            from ...core.value_objects.cache_priority import CachePriority
            from ...core.value_objects.cache_size import CacheSize
            
            test_entry = CacheEntry(
                key=test_key,
                value="health_check",
                ttl=None,
                priority=CachePriority.low(),
                namespace=test_namespace,
                created_at=datetime.now(timezone.utc),
                accessed_at=datetime.now(timezone.utc),
                access_count=0,
                size_bytes=CacheSize(12)
            )
            
            await self.set(test_entry)
            result = await self.get(test_key, test_namespace)
            await self.delete(test_key, test_namespace)
            
            self._is_healthy = result is not None
            return self._is_healthy
            
        except Exception:
            self._is_healthy = False
            return False
    
    # Transaction support (simple implementation)
    async def begin_transaction(self) -> Any:
        """Begin cache transaction - simple implementation returns None."""
        return None  # Memory implementation doesn't need transactions
    
    async def commit_transaction(self, transaction: Any) -> bool:
        """Commit cache transaction."""
        return True  # Always succeeds in memory implementation
    
    async def rollback_transaction(self, transaction: Any) -> bool:
        """Rollback cache transaction."""
        return True  # Always succeeds in memory implementation
    
    # Cleanup operations
    async def cleanup_expired(self) -> int:
        """Remove expired entries."""
        return await self._cache.cleanup_expired()
    
    async def optimize(self) -> bool:
        """Optimize cache storage."""
        # Clean up expired entries
        await self.cleanup_expired()
        
        # No other optimization needed for memory implementation
        return True
    
    async def _evict_entries(self, count: int) -> int:
        """Evict entries based on LRU policy."""
        evicted = 0
        all_keys = await self._cache.get_all_keys()
        
        # Memory cache already maintains LRU order, so evict from beginning
        for i in range(min(count, len(all_keys))):
            key = all_keys[i]
            await self._cache.delete(key)
            evicted += 1
        
        return evicted


# Factory function for dependency injection
def create_memory_cache_repository(
    max_entries: int = 10000
) -> MemoryCacheRepository:
    """Create memory cache repository with configuration.
    
    Args:
        max_entries: Maximum number of entries before eviction
        
    Returns:
        Configured memory cache repository
    """
    return MemoryCacheRepository(max_entries=max_entries)