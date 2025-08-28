"""Cache repository protocol.

ONLY cache storage contract - defines interface for cache storage
implementations with async support.

Following maximum separation architecture - one file = one purpose.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from typing_extensions import Protocol, runtime_checkable

from ..entities.cache_entry import CacheEntry
from ..entities.cache_namespace import CacheNamespace
from ..value_objects.cache_key import CacheKey
from ..value_objects.invalidation_pattern import InvalidationPattern


@runtime_checkable
class CacheRepository(Protocol):
    """Cache repository protocol.
    
    Defines interface for cache storage implementations with support for:
    - Basic CRUD operations (get, set, delete)
    - Batch operations for efficiency
    - Pattern-based invalidation
    - Namespace management
    - TTL and expiration handling
    - Transaction support
    - Health monitoring
    """
    
    async def get(self, key: CacheKey, namespace: CacheNamespace) -> Optional[CacheEntry]:
        """Get cache entry by key.
        
        Returns None if key doesn't exist or has expired.
        Automatically updates access tracking.
        """
        ...
    
    async def set(self, entry: CacheEntry) -> bool:
        """Set cache entry.
        
        Returns True if successfully stored, False otherwise.
        Handles TTL setting and namespace organization.
        """
        ...
    
    async def delete(self, key: CacheKey, namespace: CacheNamespace) -> bool:
        """Delete cache entry by key.
        
        Returns True if key existed and was deleted, False if key didn't exist.
        """
        ...
    
    async def exists(self, key: CacheKey, namespace: CacheNamespace) -> bool:
        """Check if cache key exists and is not expired."""
        ...
    
    async def get_ttl(self, key: CacheKey, namespace: CacheNamespace) -> Optional[int]:
        """Get remaining TTL in seconds.
        
        Returns None if key doesn't exist or never expires.
        Returns 0 if expired but not yet cleaned up.
        """
        ...
    
    async def extend_ttl(self, key: CacheKey, namespace: CacheNamespace, seconds: int) -> bool:
        """Extend TTL by additional seconds.
        
        Returns True if TTL was extended, False if key doesn't exist.
        """
        ...
    
    # Batch operations
    async def get_many(
        self, 
        keys: List[CacheKey], 
        namespace: CacheNamespace
    ) -> Dict[CacheKey, Optional[CacheEntry]]:
        """Get multiple cache entries.
        
        Returns dictionary mapping keys to entries (None for missing/expired).
        More efficient than individual get calls.
        """
        ...
    
    async def set_many(self, entries: List[CacheEntry]) -> Dict[CacheKey, bool]:
        """Set multiple cache entries.
        
        Returns dictionary mapping keys to success status.
        Atomic operation where possible.
        """
        ...
    
    async def delete_many(
        self, 
        keys: List[CacheKey], 
        namespace: CacheNamespace
    ) -> Dict[CacheKey, bool]:
        """Delete multiple cache entries.
        
        Returns dictionary mapping keys to deletion status.
        """
        ...
    
    # Pattern operations
    async def find_keys(
        self, 
        pattern: InvalidationPattern, 
        namespace: Optional[CacheNamespace] = None
    ) -> List[CacheKey]:
        """Find cache keys matching pattern.
        
        Supports wildcard and regex patterns.
        If namespace is None, searches across all namespaces.
        """
        ...
    
    async def invalidate_pattern(
        self, 
        pattern: InvalidationPattern,
        namespace: Optional[CacheNamespace] = None
    ) -> int:
        """Invalidate all keys matching pattern.
        
        Returns number of keys invalidated.
        If namespace is None, invalidates across all namespaces.
        """
        ...
    
    # Namespace operations
    async def flush_namespace(self, namespace: CacheNamespace) -> int:
        """Delete all entries in namespace.
        
        Returns number of entries deleted.
        """
        ...
    
    async def get_namespace_size(self, namespace: CacheNamespace) -> int:
        """Get number of entries in namespace."""
        ...
    
    async def get_namespace_memory(self, namespace: CacheNamespace) -> int:
        """Get memory usage of namespace in bytes."""
        ...
    
    async def list_namespaces(self) -> List[CacheNamespace]:
        """List all available namespaces."""
        ...
    
    # Statistics and monitoring
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns dictionary with metrics like:
        - total_keys: Total number of cached keys
        - total_memory: Total memory usage in bytes
        - hit_rate: Cache hit rate percentage
        - eviction_count: Number of evicted entries
        - expired_count: Number of expired entries
        """
        ...
    
    async def get_info(self) -> Dict[str, Any]:
        """Get cache implementation information.
        
        Returns implementation-specific info like:
        - version: Cache backend version
        - memory_limit: Maximum memory limit
        - eviction_policy: Current eviction policy
        - connection_status: Connection health
        """
        ...
    
    async def ping(self) -> bool:
        """Health check - verify cache is responsive.
        
        Returns True if cache is healthy and responsive.
        """
        ...
    
    # Transaction support (optional)
    async def begin_transaction(self) -> Any:
        """Begin cache transaction if supported.
        
        Returns transaction context or None if not supported.
        """
        ...
    
    async def commit_transaction(self, transaction: Any) -> bool:
        """Commit cache transaction.
        
        Returns True if committed successfully.
        """
        ...
    
    async def rollback_transaction(self, transaction: Any) -> bool:
        """Rollback cache transaction.
        
        Returns True if rolled back successfully.
        """
        ...
    
    # Cleanup operations
    async def cleanup_expired(self) -> int:
        """Remove expired entries.
        
        Returns number of entries cleaned up.
        Usually called by background tasks.
        """
        ...
    
    async def optimize(self) -> bool:
        """Optimize cache storage.
        
        Implementation-specific optimization like compaction.
        Returns True if optimization completed successfully.
        """
        ...