"""Cache miss event.

ONLY miss events - cache access outcome event for performance
tracking and cache effectiveness analysis.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from ..value_objects.cache_key import CacheKey
from ..entities.cache_namespace import CacheNamespace


class MissReason(Enum):
    """Reasons for cache miss."""
    
    NOT_FOUND = "not_found"       # Key never cached
    EXPIRED = "expired"           # Key expired
    EVICTED = "evicted"          # Key was evicted
    INVALIDATED = "invalidated"   # Key was invalidated
    ERROR = "error"              # Cache error occurred


@dataclass(frozen=True)
class CacheMiss:
    """Cache miss domain event.
    
    Fired when cache lookup fails to find a valid cached value.
    Used for performance tracking, cache effectiveness analysis,
    and identifying optimization opportunities.
    """
    
    # Event identity
    event_id: str
    timestamp: datetime
    
    # Cache context
    key: CacheKey
    namespace: CacheNamespace
    
    # Miss details
    reason: MissReason
    lookup_time_ms: float
    
    # Access context
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    
    # Additional context
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def get_event_type(self) -> str:
        """Get event type identifier."""
        return "cache.miss"
    
    def is_cacheable_miss(self) -> bool:
        """Check if miss represents a cacheable opportunity."""
        return self.reason in [MissReason.NOT_FOUND, MissReason.EXPIRED, MissReason.EVICTED]
    
    def is_error_miss(self) -> bool:
        """Check if miss was due to cache error."""
        return self.reason == MissReason.ERROR
    
    def is_slow_miss(self, threshold_ms: float = 5.0) -> bool:
        """Check if miss lookup was slow."""
        return self.lookup_time_ms > threshold_ms
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_type": self.get_event_type(),
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "key": str(self.key),
            "namespace": str(self.namespace),
            "reason": self.reason.value,
            "lookup_time_ms": self.lookup_time_ms,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "error_message": self.error_message,
            "cacheable": self.is_cacheable_miss(),
            "metadata": self.metadata
        }