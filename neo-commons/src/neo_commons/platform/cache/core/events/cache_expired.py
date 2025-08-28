"""Cache expired event.

ONLY expiration events - cache lifecycle event for expiration
tracking and event-driven cache warming.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from ..value_objects.cache_key import CacheKey
from ..entities.cache_namespace import CacheNamespace


class ExpirationTrigger(Enum):
    """What triggered the expiration detection."""
    
    ACCESS = "access"           # Detected during access attempt
    CLEANUP = "cleanup"         # Detected during cleanup task
    MONITORING = "monitoring"   # Detected during monitoring
    EVICTION = "eviction"      # Detected during eviction process


@dataclass(frozen=True)
class CacheExpired:
    """Cache expired domain event.
    
    Fired when cache entries expire based on TTL.
    Used for expiration tracking, cache warming triggers,
    and TTL effectiveness analysis.
    """
    
    # Event identity
    event_id: str
    timestamp: datetime
    
    # Cache context
    key: CacheKey
    namespace: CacheNamespace
    
    # Expiration details
    trigger: ExpirationTrigger
    expired_at: datetime  # When entry actually expired
    detected_at: datetime  # When expiration was detected
    
    # Entry context (before expiration)
    entry_age_seconds: int
    original_ttl_seconds: Optional[int] = None
    access_count: Optional[int] = None
    entry_size_bytes: Optional[int] = None
    last_access_at: Optional[datetime] = None
    
    # Access context
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    
    # Additional context
    metadata: Optional[Dict[str, Any]] = None
    
    def get_event_type(self) -> str:
        """Get event type identifier."""
        return "cache.expired"
    
    def get_detection_delay_seconds(self) -> float:
        """Get delay between expiration and detection."""
        return (self.detected_at - self.expired_at).total_seconds()
    
    def was_detected_on_access(self) -> bool:
        """Check if expiration was detected during access."""
        return self.trigger == ExpirationTrigger.ACCESS
    
    def was_detected_by_cleanup(self) -> bool:
        """Check if expiration was detected by cleanup task."""
        return self.trigger == ExpirationTrigger.CLEANUP
    
    def was_long_lived(self, threshold_seconds: int = 3600) -> bool:
        """Check if entry lived longer than threshold."""
        return self.entry_age_seconds >= threshold_seconds
    
    def was_frequently_accessed(self, threshold: int = 10) -> bool:
        """Check if expired entry was frequently accessed."""
        return self.access_count is not None and self.access_count >= threshold
    
    def was_recently_accessed(self, threshold_seconds: int = 300) -> bool:
        """Check if entry was accessed recently before expiration."""
        if self.last_access_at is None:
            return False
        
        time_since_access = (self.expired_at - self.last_access_at).total_seconds()
        return time_since_access <= threshold_seconds
    
    def had_short_ttl(self, threshold_seconds: int = 300) -> bool:
        """Check if entry had a short TTL."""
        return (
            self.original_ttl_seconds is not None and
            self.original_ttl_seconds <= threshold_seconds
        )
    
    def is_candidate_for_warming(self) -> bool:
        """Check if expired entry is candidate for cache warming."""
        return (
            self.was_frequently_accessed() and
            self.was_recently_accessed() and
            not self.had_short_ttl()
        )
    
    def get_expiration_category(self) -> str:
        """Get expiration category for analysis."""
        if self.was_recently_accessed() and self.was_frequently_accessed():
            return "premature"  # Expired but still being used
        elif self.was_long_lived() and self.access_count and self.access_count > 0:
            return "natural"    # Normal expiration after good usage
        elif self.access_count == 0 or self.access_count is None:
            return "unused"     # Never accessed after caching
        else:
            return "normal"     # Standard expiration
    
    def get_detection_efficiency(self) -> str:
        """Get detection efficiency category."""
        delay = self.get_detection_delay_seconds()
        
        if delay <= 60:  # Within 1 minute
            return "excellent"
        elif delay <= 300:  # Within 5 minutes
            return "good"
        elif delay <= 1800:  # Within 30 minutes
            return "acceptable"
        else:
            return "poor"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_type": self.get_event_type(),
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "key": str(self.key),
            "namespace": str(self.namespace),
            "trigger": self.trigger.value,
            "expired_at": self.expired_at.isoformat(),
            "detected_at": self.detected_at.isoformat(),
            "detection_delay_seconds": self.get_detection_delay_seconds(),
            "entry_age_seconds": self.entry_age_seconds,
            "original_ttl_seconds": self.original_ttl_seconds,
            "access_count": self.access_count,
            "entry_size_bytes": self.entry_size_bytes,
            "last_access_at": self.last_access_at.isoformat() if self.last_access_at else None,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "expiration_category": self.get_expiration_category(),
            "detection_efficiency": self.get_detection_efficiency(),
            "warming_candidate": self.is_candidate_for_warming(),
            "metadata": self.metadata
        }