"""Cache invalidated event.

ONLY invalidation events - cache lifecycle event for invalidation
reason tracking and cascade invalidation support.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from ..value_objects.cache_key import CacheKey
from ..entities.cache_namespace import CacheNamespace


class InvalidationReason(Enum):
    """Reasons for cache invalidation."""
    
    MANUAL = "manual"             # Manual invalidation
    PATTERN = "pattern"           # Pattern-based invalidation
    DEPENDENCY = "dependency"     # Dependency-based cascade
    EVENT_DRIVEN = "event_driven" # Event-triggered invalidation
    NAMESPACE_FLUSH = "namespace_flush" # Namespace was flushed
    SCHEDULED = "scheduled"       # Scheduled invalidation
    SYSTEM = "system"            # System-initiated invalidation


@dataclass(frozen=True)
class CacheInvalidated:
    """Cache invalidated domain event.
    
    Fired when cache entries are invalidated for any reason.
    Used for invalidation reason tracking, cascade invalidation support,
    and event-driven cache warming.
    """
    
    # Event identity
    event_id: str
    timestamp: datetime
    
    # Cache context
    key: CacheKey
    namespace: CacheNamespace
    
    # Invalidation details
    reason: InvalidationReason
    triggered_by: Optional[str] = None  # User ID, system, or trigger ID
    
    # Cascade context
    cascade_source: Optional[CacheKey] = None
    cascade_level: int = 0  # 0 = root invalidation, 1+ = cascade levels
    
    # Access context
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    
    # Entry context (before invalidation)
    entry_age_seconds: Optional[int] = None
    entry_size_bytes: Optional[int] = None
    access_count: Optional[int] = None
    
    # Batch context
    batch_id: Optional[str] = None
    batch_size: Optional[int] = None
    
    # Additional context
    metadata: Optional[Dict[str, Any]] = None
    
    def get_event_type(self) -> str:
        """Get event type identifier."""
        return "cache.invalidated"
    
    def is_root_invalidation(self) -> bool:
        """Check if this is a root invalidation (not cascaded)."""
        return self.cascade_level == 0
    
    def is_cascade_invalidation(self) -> bool:
        """Check if this is a cascade invalidation."""
        return self.cascade_level > 0
    
    def is_batch_invalidation(self) -> bool:
        """Check if this is part of a batch invalidation."""
        return self.batch_id is not None
    
    def is_user_initiated(self) -> bool:
        """Check if invalidation was user-initiated."""
        return self.reason == InvalidationReason.MANUAL and self.user_id is not None
    
    def is_system_initiated(self) -> bool:
        """Check if invalidation was system-initiated."""
        return self.reason == InvalidationReason.SYSTEM
    
    def is_event_driven(self) -> bool:
        """Check if invalidation was event-driven."""
        return self.reason == InvalidationReason.EVENT_DRIVEN
    
    def was_frequently_accessed(self, threshold: int = 10) -> bool:
        """Check if invalidated entry was frequently accessed."""
        return self.access_count is not None and self.access_count >= threshold
    
    def was_large_entry(self, threshold_bytes: int = 10240) -> bool:
        """Check if invalidated entry was large."""
        return self.entry_size_bytes is not None and self.entry_size_bytes >= threshold_bytes
    
    def was_old_entry(self, threshold_seconds: int = 3600) -> bool:
        """Check if invalidated entry was old."""
        return self.entry_age_seconds is not None and self.entry_age_seconds >= threshold_seconds
    
    def get_invalidation_impact(self) -> str:
        """Get invalidation impact category."""
        if self.is_batch_invalidation() and self.batch_size and self.batch_size > 100:
            return "high"
        elif self.was_frequently_accessed() or self.was_large_entry():
            return "medium"
        else:
            return "low"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_type": self.get_event_type(),
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "key": str(self.key),
            "namespace": str(self.namespace),
            "reason": self.reason.value,
            "triggered_by": self.triggered_by,
            "cascade_source": str(self.cascade_source) if self.cascade_source else None,
            "cascade_level": self.cascade_level,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "entry_age_seconds": self.entry_age_seconds,
            "entry_size_bytes": self.entry_size_bytes,
            "access_count": self.access_count,
            "batch_id": self.batch_id,
            "batch_size": self.batch_size,
            "invalidation_impact": self.get_invalidation_impact(),
            "is_cascade": self.is_cascade_invalidation(),
            "metadata": self.metadata
        }