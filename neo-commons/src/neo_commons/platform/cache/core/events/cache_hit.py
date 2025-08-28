"""Cache hit event.

ONLY hit events - cache access outcome event for performance
tracking and access pattern analysis.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from ..value_objects.cache_key import CacheKey
from ..entities.cache_namespace import CacheNamespace


@dataclass(frozen=True)
class CacheHit:
    """Cache hit domain event.
    
    Fired when cache lookup successfully finds and returns a cached value.
    Used for performance tracking, access pattern analysis, and cache
    effectiveness metrics.
    """
    
    # Event identity
    event_id: str
    timestamp: datetime
    
    # Cache context
    key: CacheKey
    namespace: CacheNamespace
    
    # Performance metrics
    lookup_time_ms: float
    value_size_bytes: int
    
    # Access context
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    
    # Cache entry metadata
    entry_age_seconds: Optional[int] = None
    access_count: Optional[int] = None
    ttl_remaining_seconds: Optional[int] = None
    
    # Additional context
    metadata: Optional[Dict[str, Any]] = None
    
    def get_event_type(self) -> str:
        """Get event type identifier."""
        return "cache.hit"
    
    def is_recent_hit(self, threshold_seconds: int = 60) -> bool:
        """Check if hit is recent within threshold."""
        age = (datetime.utcnow() - self.timestamp).total_seconds()
        return age <= threshold_seconds
    
    def is_fast_hit(self, threshold_ms: float = 1.0) -> bool:
        """Check if hit was fast (sub-millisecond)."""
        return self.lookup_time_ms <= threshold_ms
    
    def is_large_value(self, threshold_bytes: int = 1024) -> bool:
        """Check if cached value is large."""
        return self.value_size_bytes >= threshold_bytes
    
    def is_frequently_accessed(self, threshold_count: int = 10) -> bool:
        """Check if entry is frequently accessed."""
        return self.access_count is not None and self.access_count >= threshold_count
    
    def is_expiring_soon(self, threshold_seconds: int = 300) -> bool:
        """Check if entry is expiring soon (within 5 minutes by default)."""
        return (
            self.ttl_remaining_seconds is not None and
            self.ttl_remaining_seconds <= threshold_seconds
        )
    
    def get_performance_category(self) -> str:
        """Get performance category based on lookup time."""
        if self.lookup_time_ms <= 1.0:
            return "excellent"
        elif self.lookup_time_ms <= 5.0:
            return "good"
        elif self.lookup_time_ms <= 10.0:
            return "acceptable"
        else:
            return "slow"
    
    def get_value_size_category(self) -> str:
        """Get value size category."""
        if self.value_size_bytes < 1024:  # < 1KB
            return "small"
        elif self.value_size_bytes < 10 * 1024:  # < 10KB
            return "medium"
        elif self.value_size_bytes < 100 * 1024:  # < 100KB
            return "large"
        else:
            return "very_large"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_type": self.get_event_type(),
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "key": str(self.key),
            "namespace": str(self.namespace),
            "lookup_time_ms": self.lookup_time_ms,
            "value_size_bytes": self.value_size_bytes,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "entry_age_seconds": self.entry_age_seconds,
            "access_count": self.access_count,
            "ttl_remaining_seconds": self.ttl_remaining_seconds,
            "performance_category": self.get_performance_category(),
            "value_size_category": self.get_value_size_category(),
            "metadata": self.metadata
        }