"""User logout event."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from ....core.value_objects.identifiers import UserId, TenantId
from ..value_objects import SessionId, RealmIdentifier


@dataclass(frozen=True)
class UserLoggedOut:
    """Event fired when user logs out or session ends.
    
    Represents ONLY user logout occurrence.
    Contains all necessary data for cleanup and audit.
    """
    
    # Core Event Data
    user_id: UserId
    tenant_id: Optional[TenantId]
    realm_id: Optional[RealmIdentifier] = None
    session_id: Optional[SessionId] = None
    
    # Logout Context
    logout_reason: str = "user_initiated"  # user_initiated, expired, revoked, admin_action, security
    logout_method: str = "manual"  # manual, automatic, forced
    
    # Session Information
    session_duration_seconds: Optional[int] = None
    last_activity_at: Optional[datetime] = None
    
    # Security Context
    was_forced: bool = False
    revoked_by_admin: bool = False
    security_incident: bool = False
    
    # Cleanup Context
    tokens_revoked: bool = False
    cache_cleared: bool = False
    sessions_invalidated: int = 0
    
    # Event Metadata
    event_timestamp: datetime = None
    event_source: str = "auth_service"
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
        
        if self.last_activity_at and self.last_activity_at.tzinfo is None:
            object.__setattr__(
                self, 'last_activity_at', 
                self.last_activity_at.replace(tzinfo=timezone.utc)
            )
        
        # Set default metadata
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})
    
    @property
    def event_type(self) -> str:
        """Get event type identifier."""
        return "user_logged_out"
    
    @property
    def is_security_logout(self) -> bool:
        """Check if logout was due to security reasons."""
        return (
            self.security_incident or
            self.was_forced or
            self.logout_reason in ['security', 'suspicious_activity', 'breach']
        )
    
    @property
    def requires_audit(self) -> bool:
        """Check if logout requires audit logging."""
        return (
            self.is_security_logout or
            self.revoked_by_admin or
            self.logout_reason in ['admin_action', 'forced', 'security']
        )
    
    @property
    def cleanup_completed(self) -> bool:
        """Check if cleanup was completed successfully."""
        return self.tokens_revoked and self.cache_cleared
    
    @property
    def logout_category(self) -> str:
        """Get logout category for analytics."""
        if self.is_security_logout:
            return "security"
        elif self.logout_reason == "expired":
            return "expiration"
        elif self.logout_reason == "admin_action":
            return "administrative"
        else:
            return "normal"
    
    @property
    def session_duration_minutes(self) -> Optional[int]:
        """Get session duration in minutes."""
        if self.session_duration_seconds is not None:
            return self.session_duration_seconds // 60
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            'event_type': self.event_type,
            'user_id': str(self.user_id.value),
            'tenant_id': str(self.tenant_id.value) if self.tenant_id else None,
            'realm_id': str(self.realm_id.value) if self.realm_id else None,
            'session_id': str(self.session_id.value) if self.session_id else None,
            'logout_reason': self.logout_reason,
            'logout_method': self.logout_method,
            'session_duration_seconds': self.session_duration_seconds,
            'session_duration_minutes': self.session_duration_minutes,
            'last_activity_at': self.last_activity_at.isoformat() if self.last_activity_at else None,
            'was_forced': self.was_forced,
            'revoked_by_admin': self.revoked_by_admin,
            'security_incident': self.security_incident,
            'tokens_revoked': self.tokens_revoked,
            'cache_cleared': self.cache_cleared,
            'sessions_invalidated': self.sessions_invalidated,
            'event_timestamp': self.event_timestamp.isoformat(),
            'event_source': self.event_source,
            'correlation_id': self.correlation_id,
            'metadata': self.metadata,
            'is_security_logout': self.is_security_logout,
            'requires_audit': self.requires_audit,
            'cleanup_completed': self.cleanup_completed,
            'logout_category': self.logout_category
        }
    
    def __str__(self) -> str:
        """String representation."""
        return f"UserLoggedOut({self.user_id}, reason={self.logout_reason}, security={self.is_security_logout})"
    
    def __repr__(self) -> str:
        """Debug representation."""
        return (
            f"UserLoggedOut(user_id={self.user_id}, tenant_id={self.tenant_id}, "
            f"logout_reason={self.logout_reason}, was_forced={self.was_forced})"
        )