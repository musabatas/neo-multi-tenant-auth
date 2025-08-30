"""Authentication session domain entity."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Set
from ....core.value_objects.identifiers import UserId, TenantId
from ..value_objects import SessionId


@dataclass
class AuthSession:
    """Authentication session entity.
    
    Handles ONLY authentication session state and lifecycle.
    Does not manage session storage - that's handled by session managers.
    """
    
    # Core Identity
    session_id: SessionId
    user_id: UserId
    tenant_id: Optional[TenantId] = None
    
    # Session Lifecycle
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    last_activity_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Session State
    is_active: bool = True
    revoked_at: Optional[datetime] = None
    revoke_reason: Optional[str] = None
    
    # Session Context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_info: Dict[str, Any] = field(default_factory=dict)
    
    # Authentication Context
    authentication_method: str = "password"
    mfa_verified: bool = False
    risk_score: float = 0.0
    
    # Session Data
    session_data: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    
    def __post_init__(self) -> None:
        """Validate session entity after initialization."""
        # Ensure timezone awareness for timestamps
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)
        
        if self.expires_at and self.expires_at.tzinfo is None:
            self.expires_at = self.expires_at.replace(tzinfo=timezone.utc)
        
        if self.last_activity_at.tzinfo is None:
            self.last_activity_at = self.last_activity_at.replace(tzinfo=timezone.utc)
        
        if self.revoked_at and self.revoked_at.tzinfo is None:
            self.revoked_at = self.revoked_at.replace(tzinfo=timezone.utc)
        
        # Validate risk score
        if not (0.0 <= self.risk_score <= 1.0):
            raise ValueError("Risk score must be between 0.0 and 1.0")
        
        # Ensure consistency
        if self.revoked_at and self.is_active:
            self.is_active = False
    
    @property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) >= self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if session is valid (active and not expired)."""
        return self.is_active and not self.is_expired
    
    @property
    def seconds_until_expiry(self) -> Optional[int]:
        """Get seconds until session expires."""
        if not self.expires_at:
            return None
        
        if self.is_expired:
            return 0
        
        delta = self.expires_at - datetime.now(timezone.utc)
        return max(0, int(delta.total_seconds()))
    
    @property
    def seconds_since_activity(self) -> int:
        """Get seconds since last activity."""
        delta = datetime.now(timezone.utc) - self.last_activity_at
        return int(delta.total_seconds())
    
    @property
    def session_duration_seconds(self) -> int:
        """Get total session duration in seconds."""
        end_time = self.revoked_at or datetime.now(timezone.utc)
        delta = end_time - self.created_at
        return int(delta.total_seconds())
    
    @property
    def is_high_risk(self) -> bool:
        """Check if session has high risk score."""
        return self.risk_score >= 0.7
    
    @property
    def requires_mfa(self) -> bool:
        """Check if session requires MFA verification."""
        return self.is_high_risk or 'mfa_required' in self.tags
    
    def update_activity(self, extend_expiry: bool = True) -> None:
        """Update last activity timestamp.
        
        Args:
            extend_expiry: Whether to extend session expiration
        """
        self.last_activity_at = datetime.now(timezone.utc)
        
        if extend_expiry and self.expires_at:
            # Extend by the same duration as the original session
            original_duration = self.expires_at - self.created_at
            self.expires_at = self.last_activity_at + original_duration
    
    def revoke(self, reason: str = "manual_revocation") -> None:
        """Revoke the session.
        
        Args:
            reason: Reason for revocation
        """
        self.is_active = False
        self.revoked_at = datetime.now(timezone.utc)
        self.revoke_reason = reason
        self.tags.add("revoked")
    
    def extend_expiry(self, seconds: int) -> None:
        """Extend session expiration by specified seconds.
        
        Args:
            seconds: Seconds to extend expiration
        """
        if not self.expires_at:
            # If no expiration was set, set one now
            self.expires_at = datetime.now(timezone.utc) + timezone.utc.localize(
                datetime.fromtimestamp(seconds)
            ).replace(tzinfo=None)
        else:
            from datetime import timedelta
            self.expires_at += timedelta(seconds=seconds)
    
    def update_risk_score(self, new_score: float, reason: Optional[str] = None) -> None:
        """Update session risk score.
        
        Args:
            new_score: New risk score (0.0 to 1.0)
            reason: Reason for risk score change
        """
        if not (0.0 <= new_score <= 1.0):
            raise ValueError("Risk score must be between 0.0 and 1.0")
        
        old_score = self.risk_score
        self.risk_score = new_score
        
        # Add risk-related tags
        if new_score >= 0.7:
            self.tags.add("high_risk")
        elif new_score >= 0.4:
            self.tags.add("medium_risk")
        else:
            self.tags.add("low_risk")
        
        # Store risk change in session data if reason provided
        if reason:
            risk_history = self.session_data.get('risk_history', [])
            risk_history.append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'old_score': old_score,
                'new_score': new_score,
                'reason': reason
            })
            self.session_data['risk_history'] = risk_history
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the session."""
        self.tags.add(tag.lower())
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the session."""
        self.tags.discard(tag.lower())
    
    def has_tag(self, tag: str) -> bool:
        """Check if session has a specific tag."""
        return tag.lower() in self.tags
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary representation."""
        return {
            'session_id': str(self.session_id.value),
            'user_id': str(self.user_id.value),
            'tenant_id': str(self.tenant_id.value) if self.tenant_id else None,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_activity_at': self.last_activity_at.isoformat(),
            'is_active': self.is_active,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
            'revoke_reason': self.revoke_reason,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'device_info': self.device_info,
            'authentication_method': self.authentication_method,
            'mfa_verified': self.mfa_verified,
            'risk_score': self.risk_score,
            'session_data': self.session_data,
            'tags': list(self.tags),
            'is_expired': self.is_expired,
            'is_valid': self.is_valid,
            'seconds_until_expiry': self.seconds_until_expiry,
            'seconds_since_activity': self.seconds_since_activity,
            'session_duration_seconds': self.session_duration_seconds
        }
    
    def __str__(self) -> str:
        """String representation."""
        status = "valid" if self.is_valid else "invalid"
        return f"AuthSession({self.session_id}, user={self.user_id}, status={status})"
    
    def __repr__(self) -> str:
        """Debug representation."""
        return (
            f"AuthSession(session_id={self.session_id}, user_id={self.user_id}, "
            f"tenant_id={self.tenant_id}, is_active={self.is_active}, "
            f"expires_at={self.expires_at})"
        )