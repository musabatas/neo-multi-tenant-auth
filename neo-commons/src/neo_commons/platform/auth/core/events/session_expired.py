"""Session expiration event."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from ....core.value_objects.identifiers import UserId, TenantId
from ..value_objects import SessionId, RealmIdentifier


@dataclass(frozen=True)
class SessionExpired:
    """Event fired when user session expires.
    
    Represents ONLY session expiration occurrence.
    Contains all necessary data for cleanup and user notification.
    """
    
    # Core Event Data
    user_id: UserId
    tenant_id: Optional[TenantId]
    realm_id: Optional[RealmIdentifier] = None
    session_id: Optional[SessionId] = None
    
    # Expiration Context
    expiration_reason: str = "idle_timeout"  # idle_timeout, max_lifetime, inactivity, forced
    expiration_type: str = "automatic"  # automatic, manual, security
    
    # Session Information
    session_created_at: Optional[datetime] = None
    session_last_activity_at: Optional[datetime] = None
    session_duration_seconds: Optional[int] = None
    idle_duration_seconds: Optional[int] = None
    
    # Configuration Context
    configured_idle_timeout: Optional[int] = None
    configured_max_lifetime: Optional[int] = None
    was_remember_me: bool = False
    
    # Cleanup Context
    tokens_invalidated: bool = False
    cache_cleared: bool = False
    related_sessions_count: int = 0
    related_sessions_expired: int = 0
    
    # Event Metadata
    event_timestamp: datetime = None
    event_source: str = "session_manager"
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self) -> None:
        """Initialize event after creation."""
        # Set default timestamp
        if self.event_timestamp is None:
            object.__setattr__(self, 'event_timestamp', datetime.now(timezone.utc))
        
        # Ensure timezone awareness
        if self.event_timestamp.tzinfo is None:
            object.__setattr__(
                self, 'event_timestamp', 
                self.event_timestamp.replace(tzinfo=timezone.utc)
            )
        
        if self.session_created_at and self.session_created_at.tzinfo is None:
            object.__setattr__(
                self, 'session_created_at', 
                self.session_created_at.replace(tzinfo=timezone.utc)
            )
        
        if self.session_last_activity_at and self.session_last_activity_at.tzinfo is None:
            object.__setattr__(
                self, 'session_last_activity_at', 
                self.session_last_activity_at.replace(tzinfo=timezone.utc)
            )
        
        # Set default metadata
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})
        
        # Calculate session duration if timestamps available
        if self.session_duration_seconds is None and self.session_created_at:
            duration = self.event_timestamp - self.session_created_at
            object.__setattr__(self, 'session_duration_seconds', int(duration.total_seconds()))
        
        # Calculate idle duration if last activity available
        if self.idle_duration_seconds is None and self.session_last_activity_at:
            idle_duration = self.event_timestamp - self.session_last_activity_at
            object.__setattr__(self, 'idle_duration_seconds', int(idle_duration.total_seconds()))
    
    @property
    def event_type(self) -> str:
        """Get event type identifier."""
        return "session_expired"
    
    @property
    def is_security_expiration(self) -> bool:
        """Check if expiration was for security reasons."""
        return self.expiration_type == "security" or self.expiration_reason == "forced"
    
    @property
    def is_idle_expiration(self) -> bool:
        """Check if expiration was due to inactivity."""
        return self.expiration_reason in ["idle_timeout", "inactivity"]
    
    @property
    def is_lifetime_expiration(self) -> bool:
        """Check if expiration was due to maximum lifetime."""
        return self.expiration_reason == "max_lifetime"
    
    @property
    def session_duration_minutes(self) -> Optional[int]:
        """Get session duration in minutes."""
        if self.session_duration_seconds is not None:
            return self.session_duration_seconds // 60
        return None
    
    @property
    def session_duration_hours(self) -> Optional[float]:
        """Get session duration in hours."""
        if self.session_duration_seconds is not None:
            return self.session_duration_seconds / 3600
        return None
    
    @property
    def idle_duration_minutes(self) -> Optional[int]:
        """Get idle duration in minutes."""
        if self.idle_duration_seconds is not None:
            return self.idle_duration_seconds // 60
        return None
    
    @property
    def cleanup_completed(self) -> bool:
        """Check if cleanup was completed successfully."""
        return self.tokens_invalidated and self.cache_cleared
    
    @property
    def exceeded_idle_timeout(self) -> bool:
        """Check if idle timeout was exceeded."""
        if self.configured_idle_timeout is None or self.idle_duration_seconds is None:
            return False
        return self.idle_duration_seconds >= self.configured_idle_timeout
    
    @property
    def exceeded_max_lifetime(self) -> bool:
        """Check if max lifetime was exceeded."""
        if self.configured_max_lifetime is None or self.session_duration_seconds is None:
            return False
        return self.session_duration_seconds >= self.configured_max_lifetime
    
    @property
    def expiration_category(self) -> str:
        """Get expiration category for analytics."""
        if self.is_security_expiration:
            return "security"
        elif self.is_idle_expiration:
            return "inactivity"
        elif self.is_lifetime_expiration:
            return "lifetime"
        else:
            return "other"
    
    @property
    def requires_notification(self) -> bool:
        """Check if expiration requires user notification."""
        return (
            self.is_security_expiration or
            self.was_remember_me or
            self.related_sessions_expired > 0
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            'event_type': self.event_type,
            'user_id': str(self.user_id.value),
            'tenant_id': str(self.tenant_id.value) if self.tenant_id else None,
            'realm_id': str(self.realm_id.value) if self.realm_id else None,
            'session_id': str(self.session_id.value) if self.session_id else None,
            'expiration_reason': self.expiration_reason,
            'expiration_type': self.expiration_type,
            'session_created_at': self.session_created_at.isoformat() if self.session_created_at else None,
            'session_last_activity_at': self.session_last_activity_at.isoformat() if self.session_last_activity_at else None,
            'session_duration_seconds': self.session_duration_seconds,
            'session_duration_minutes': self.session_duration_minutes,
            'session_duration_hours': self.session_duration_hours,
            'idle_duration_seconds': self.idle_duration_seconds,
            'idle_duration_minutes': self.idle_duration_minutes,
            'configured_idle_timeout': self.configured_idle_timeout,
            'configured_max_lifetime': self.configured_max_lifetime,
            'was_remember_me': self.was_remember_me,
            'tokens_invalidated': self.tokens_invalidated,
            'cache_cleared': self.cache_cleared,
            'related_sessions_count': self.related_sessions_count,
            'related_sessions_expired': self.related_sessions_expired,
            'event_timestamp': self.event_timestamp.isoformat(),
            'event_source': self.event_source,
            'correlation_id': self.correlation_id,
            'metadata': self.metadata,
            'is_security_expiration': self.is_security_expiration,
            'is_idle_expiration': self.is_idle_expiration,
            'is_lifetime_expiration': self.is_lifetime_expiration,
            'cleanup_completed': self.cleanup_completed,
            'exceeded_idle_timeout': self.exceeded_idle_timeout,
            'exceeded_max_lifetime': self.exceeded_max_lifetime,
            'expiration_category': self.expiration_category,
            'requires_notification': self.requires_notification
        }
    
    def __str__(self) -> str:
        """String representation."""
        return f"SessionExpired({self.user_id}, reason={self.expiration_reason}, duration={self.session_duration_minutes}min)"
    
    def __repr__(self) -> str:
        """Debug representation."""
        return (
            f"SessionExpired(user_id={self.user_id}, tenant_id={self.tenant_id}, "
            f"expiration_reason={self.expiration_reason}, session_duration_seconds={self.session_duration_seconds})"
        )