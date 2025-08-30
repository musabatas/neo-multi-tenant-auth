"""Session validation failure exception."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from ....core.exceptions.base import DomainException


class SessionInvalid(DomainException):
    """Exception raised when session validation fails.
    
    Handles ONLY session validation failure representation.
    Does not manage session state - that's handled by session managers.
    """
    
    def __init__(
        self,
        message: str = "Session is invalid",
        *,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        reason: Optional[str] = None,
        expired_at: Optional[datetime] = None,
        last_activity: Optional[datetime] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize session validation failure exception.
        
        Args:
            message: Human-readable error message
            session_id: Session identifier (masked for security)
            user_id: User identifier associated with session
            reason: Specific reason for invalidity
            expired_at: When session expired, if applicable
            last_activity: Last recorded activity timestamp
            context: Additional context for debugging
        """
        super().__init__(message)
        
        self.session_id = self._mask_session_id(session_id) if session_id else None
        self.user_id = user_id
        self.reason = reason
        self.expired_at = expired_at
        self.last_activity = last_activity
        self.context = context or {}
        
        # Ensure timezone awareness for timestamps
        if self.expired_at and self.expired_at.tzinfo is None:
            self.expired_at = self.expired_at.replace(tzinfo=timezone.utc)
        
        if self.last_activity and self.last_activity.tzinfo is None:
            self.last_activity = self.last_activity.replace(tzinfo=timezone.utc)
        
        # Add structured data for logging and monitoring
        self.details = {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'reason': self.reason,
            'expired_at': self.expired_at.isoformat() if self.expired_at else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'is_expired': self.is_expired,
            'is_inactive': self.is_inactive,
            **self.context
        }
    
    def _mask_session_id(self, session_id: str) -> str:
        """Mask session ID for security in logs."""
        if not session_id or len(session_id) <= 12:
            return "***"
        
        return f"{session_id[:6]}...{session_id[-6:]}"
    
    @property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return self.reason == "expired" or (
            self.expired_at is not None and
            datetime.now(timezone.utc) >= self.expired_at
        )
    
    @property
    def is_inactive(self) -> bool:
        """Check if session is invalid due to inactivity."""
        return self.reason == "inactive" or self.reason == "timeout"
    
    @property
    def is_revoked(self) -> bool:
        """Check if session was explicitly revoked."""
        return self.reason == "revoked" or self.reason == "logged_out"
    
    @property
    def is_not_found(self) -> bool:
        """Check if session was not found."""
        return self.reason == "not_found" or self.reason == "missing"
    
    @property
    def is_corrupted(self) -> bool:
        """Check if session data is corrupted."""
        return self.reason == "corrupted" or self.reason == "invalid_data"
    
    @property
    def seconds_since_activity(self) -> Optional[int]:
        """Get seconds since last activity."""
        if self.last_activity is None:
            return None
        
        delta = datetime.now(timezone.utc) - self.last_activity
        return int(delta.total_seconds())
    
    @property
    def seconds_until_expiry(self) -> Optional[int]:
        """Get seconds until session expires."""
        if self.expired_at is None:
            return None
        
        if self.is_expired:
            return 0
        
        delta = self.expired_at - datetime.now(timezone.utc)
        return max(0, int(delta.total_seconds()))
    
    @classmethod
    def expired(
        cls,
        session_id: str,
        expired_at: datetime,
        user_id: Optional[str] = None
    ) -> 'SessionInvalid':
        """Create exception for expired session."""
        seconds_expired = int((datetime.now(timezone.utc) - expired_at).total_seconds())
        
        return cls(
            message=f"Session expired {seconds_expired} seconds ago",
            session_id=session_id,
            user_id=user_id,
            reason="expired",
            expired_at=expired_at
        )
    
    @classmethod
    def not_found(
        cls,
        session_id: str,
        user_id: Optional[str] = None
    ) -> 'SessionInvalid':
        """Create exception for session not found."""
        return cls(
            message="Session not found",
            session_id=session_id,
            user_id=user_id,
            reason="not_found"
        )
    
    @classmethod
    def revoked(
        cls,
        session_id: str,
        user_id: Optional[str] = None,
        revoke_reason: Optional[str] = None
    ) -> 'SessionInvalid':
        """Create exception for revoked session."""
        message = "Session has been revoked"
        if revoke_reason:
            message += f": {revoke_reason}"
        
        return cls(
            message=message,
            session_id=session_id,
            user_id=user_id,
            reason="revoked",
            context={'revoke_reason': revoke_reason}
        )
    
    @classmethod
    def inactive_timeout(
        cls,
        session_id: str,
        last_activity: datetime,
        timeout_seconds: int,
        user_id: Optional[str] = None
    ) -> 'SessionInvalid':
        """Create exception for inactive session timeout."""
        inactive_seconds = int((datetime.now(timezone.utc) - last_activity).total_seconds())
        
        return cls(
            message=f"Session timed out after {inactive_seconds}s of inactivity (limit: {timeout_seconds}s)",
            session_id=session_id,
            user_id=user_id,
            reason="inactive",
            last_activity=last_activity,
            context={'timeout_seconds': timeout_seconds, 'inactive_seconds': inactive_seconds}
        )
    
    @classmethod
    def corrupted_data(
        cls,
        session_id: str,
        corruption_details: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> 'SessionInvalid':
        """Create exception for corrupted session data."""
        message = "Session data is corrupted"
        if corruption_details:
            message += f": {corruption_details}"
        
        return cls(
            message=message,
            session_id=session_id,
            user_id=user_id,
            reason="corrupted",
            context={'corruption_details': corruption_details}
        )
    
    @classmethod
    def security_violation(
        cls,
        session_id: str,
        violation_type: str,
        user_id: Optional[str] = None
    ) -> 'SessionInvalid':
        """Create exception for security violation."""
        return cls(
            message=f"Session invalidated due to security violation: {violation_type}",
            session_id=session_id,
            user_id=user_id,
            reason="security_violation",
            context={'violation_type': violation_type}
        )
    
    def __str__(self) -> str:
        """String representation with session context."""
        base_msg = super().__str__()
        
        context_parts = []
        if self.session_id:
            context_parts.append(f"session={self.session_id}")
        if self.user_id:
            context_parts.append(f"user={self.user_id}")
        if self.reason:
            context_parts.append(f"reason={self.reason}")
        
        if context_parts:
            return f"{base_msg} ({', '.join(context_parts)})"
        
        return base_msg