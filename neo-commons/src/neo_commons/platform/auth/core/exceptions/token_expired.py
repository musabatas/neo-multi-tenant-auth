"""Token expiration exception with timestamp information."""

from datetime import datetime, timezone
from typing import Optional
from ....core.exceptions.base import DomainException


class TokenExpired(DomainException):
    """Exception raised when a token has expired.
    
    Handles ONLY token expiration representation with timestamp context.
    Does not perform token validation - that's handled by validators.
    """
    
    def __init__(
        self,
        message: str = "Token has expired",
        *,
        expired_at: Optional[datetime] = None,
        current_time: Optional[datetime] = None,
        token_type: str = "access_token",
        grace_period_seconds: Optional[int] = None
    ) -> None:
        """Initialize token expiration exception.
        
        Args:
            message: Human-readable error message
            expired_at: When the token expired (UTC)
            current_time: Current time when expiration was detected (UTC)
            token_type: Type of token that expired (access_token, refresh_token, etc.)
            grace_period_seconds: Grace period that was allowed, if any
        """
        super().__init__(message)
        
        self.expired_at = expired_at
        self.current_time = current_time or datetime.now(timezone.utc)
        self.token_type = token_type
        self.grace_period_seconds = grace_period_seconds
        
        # Ensure timezone awareness
        if self.expired_at and self.expired_at.tzinfo is None:
            self.expired_at = self.expired_at.replace(tzinfo=timezone.utc)
        
        if self.current_time.tzinfo is None:
            self.current_time = self.current_time.replace(tzinfo=timezone.utc)
        
        # Add structured data for logging
        self.details = {
            'token_type': self.token_type,
            'expired_at': self.expired_at.isoformat() if self.expired_at else None,
            'current_time': self.current_time.isoformat(),
            'seconds_expired': self.seconds_expired,
            'grace_period_seconds': self.grace_period_seconds,
            'within_grace_period': self.is_within_grace_period
        }
    
    @property
    def seconds_expired(self) -> Optional[int]:
        """Get number of seconds since token expired."""
        if self.expired_at is None:
            return None
        
        delta = self.current_time - self.expired_at
        return max(0, int(delta.total_seconds()))
    
    @property
    def is_within_grace_period(self) -> bool:
        """Check if expiration is within grace period."""
        if self.grace_period_seconds is None or self.seconds_expired is None:
            return False
        
        return self.seconds_expired <= self.grace_period_seconds
    
    @property
    def time_until_hard_expiry(self) -> Optional[int]:
        """Get seconds until hard expiry (after grace period)."""
        if not self.is_within_grace_period or self.seconds_expired is None:
            return 0
        
        return self.grace_period_seconds - self.seconds_expired
    
    @classmethod
    def from_jwt_claims(
        cls,
        exp_timestamp: float,
        token_type: str = "access_token",
        grace_period_seconds: Optional[int] = None
    ) -> 'TokenExpired':
        """Create exception from JWT expiration timestamp.
        
        Args:
            exp_timestamp: JWT 'exp' claim timestamp
            token_type: Type of token
            grace_period_seconds: Grace period to allow
            
        Returns:
            TokenExpired exception instance
        """
        expired_at = datetime.fromtimestamp(exp_timestamp, timezone.utc)
        current_time = datetime.now(timezone.utc)
        
        seconds_expired = int((current_time - expired_at).total_seconds())
        
        if grace_period_seconds and seconds_expired <= grace_period_seconds:
            message = f"{token_type.replace('_', ' ').title()} expired {seconds_expired}s ago (within {grace_period_seconds}s grace period)"
        else:
            message = f"{token_type.replace('_', ' ').title()} expired {seconds_expired}s ago"
        
        return cls(
            message=message,
            expired_at=expired_at,
            current_time=current_time,
            token_type=token_type,
            grace_period_seconds=grace_period_seconds
        )
    
    @classmethod
    def refresh_token_expired(
        cls,
        expired_at: datetime,
        grace_period_seconds: Optional[int] = None
    ) -> 'TokenExpired':
        """Create exception for expired refresh token."""
        return cls(
            message="Refresh token has expired",
            expired_at=expired_at,
            token_type="refresh_token",
            grace_period_seconds=grace_period_seconds
        )
    
    @classmethod
    def session_token_expired(
        cls,
        expired_at: datetime,
        session_id: Optional[str] = None
    ) -> 'TokenExpired':
        """Create exception for expired session token."""
        message = "Session token has expired"
        if session_id:
            # Mask session ID for security
            masked_id = f"{session_id[:6]}...{session_id[-6:]}" if len(session_id) > 12 else "***"
            message += f" (session: {masked_id})"
        
        return cls(
            message=message,
            expired_at=expired_at,
            token_type="session_token"
        )
    
    def __str__(self) -> str:
        """String representation with expiration details."""
        base_msg = super().__str__()
        
        if self.seconds_expired is not None:
            if self.is_within_grace_period:
                return f"{base_msg} ({self.seconds_expired}s ago, within grace period)"
            else:
                return f"{base_msg} ({self.seconds_expired}s ago)"
        
        return base_msg