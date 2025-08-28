"""Cache entry domain entity.

ONLY cache entry entity - represents a cached item with lifecycle
management, TTL handling, and access tracking for optimal cache behavior.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from ..value_objects.cache_key import CacheKey
from ..value_objects.cache_ttl import CacheTTL
from ..value_objects.cache_priority import CachePriority
from ..value_objects.cache_size import CacheSize
from .cache_namespace import CacheNamespace


@dataclass
class CacheEntry:
    """Cache entry domain entity.
    
    Represents a cached item with lifecycle management, TTL handling,
    and access tracking for optimal cache behavior.
    
    Each cache entry contains:
    - Unique key for identification
    - Value of any type (serialized when stored)
    - TTL for expiration control
    - Priority for eviction decisions
    - Namespace for logical grouping
    - Timestamps for lifecycle tracking
    - Access metrics for optimization
    - Size tracking for memory management
    """
    
    # Core identity and content
    key: CacheKey
    value: Any
    
    # Cache behavior configuration
    ttl: Optional[CacheTTL]
    priority: CachePriority
    namespace: CacheNamespace
    
    # Lifecycle tracking
    created_at: datetime
    accessed_at: datetime
    access_count: int
    
    # Resource management
    size_bytes: CacheSize
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired based on TTL."""
        if self.ttl is None:
            return False
            
        return self.ttl.is_expired(self.created_at)
    
    def touch(self) -> None:
        """Update access timestamp and increment access count."""
        self.accessed_at = datetime.utcnow()
        self.access_count += 1
    
    def time_until_expiry(self) -> Optional[int]:
        """Get seconds until entry expires, None if no TTL."""
        if self.ttl is None:
            return None
            
        return self.ttl.seconds_until_expiry(self.created_at)
    
    def access_frequency(self, time_window_seconds: int = 3600) -> float:
        """Calculate access frequency per hour."""
        time_since_creation = (datetime.utcnow() - self.created_at).total_seconds()
        
        if time_since_creation <= 0:
            return 0.0
            
        # Normalize to per-hour frequency
        return (self.access_count / time_since_creation) * 3600
    
    def __eq__(self, other) -> bool:
        """Compare cache entries by key."""
        if not isinstance(other, CacheEntry):
            return False
        return self.key == other.key
    
    def __hash__(self) -> int:
        """Hash cache entry by key."""
        return hash(self.key)