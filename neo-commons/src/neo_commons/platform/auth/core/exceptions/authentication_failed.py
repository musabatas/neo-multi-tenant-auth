"""Authentication failure exception with context."""

from typing import Optional, Dict, Any
from ....core.exceptions.base import DomainException


class AuthenticationFailed(DomainException):
    """Exception raised when authentication fails.
    
    Handles ONLY authentication failure representation with context.
    Does not perform authentication logic - that's handled by services.
    """
    
    def __init__(
        self, 
        message: str = "Authentication failed",
        *,
        username: Optional[str] = None,
        realm: Optional[str] = None,
        reason: Optional[str] = None,
        retry_after: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize authentication failure exception.
        
        Args:
            message: Human-readable error message
            username: Username that failed authentication (masked for security)
            realm: Realm where authentication was attempted
            reason: Specific reason for failure (e.g., invalid_credentials, account_locked)
            retry_after: Seconds to wait before retry (for rate limiting)
            context: Additional context for debugging
        """
        super().__init__(message)
        
        self.username = self._mask_username(username) if username else None
        self.realm = realm
        self.reason = reason
        self.retry_after = retry_after
        self.context = context or {}
        
        # Add context to exception for structured logging
        self.details = {
            'username': self.username,
            'realm': self.realm,
            'reason': self.reason,
            'retry_after': self.retry_after,
            **self.context
        }
    
    def _mask_username(self, username: str) -> str:
        """Mask username for security in logs."""
        if not username or len(username) <= 4:
            return "***"
        
        # Show first 2 and last 2 characters, mask the rest
        return f"{username[:2]}...{username[-2:]}"
    
    @property
    def is_retryable(self) -> bool:
        """Check if authentication can be retried."""
        non_retryable_reasons = {
            'invalid_credentials',
            'account_disabled', 
            'account_locked',
            'invalid_realm',
            'realm_disabled'
        }
        
        return self.reason not in non_retryable_reasons
    
    @property
    def is_rate_limited(self) -> bool:
        """Check if failure is due to rate limiting."""
        return self.retry_after is not None and self.retry_after > 0
    
    @property
    def is_credential_issue(self) -> bool:
        """Check if failure is due to credential problems."""
        credential_reasons = {
            'invalid_credentials',
            'invalid_password',
            'invalid_username',
            'credentials_expired'
        }
        
        return self.reason in credential_reasons
    
    @property
    def is_account_issue(self) -> bool:
        """Check if failure is due to account problems."""
        account_reasons = {
            'account_disabled',
            'account_locked', 
            'account_expired',
            'account_not_found'
        }
        
        return self.reason in account_reasons
    
    @classmethod
    def invalid_credentials(
        cls,
        username: Optional[str] = None,
        realm: Optional[str] = None
    ) -> 'AuthenticationFailed':
        """Create exception for invalid credentials."""
        return cls(
            message="Invalid username or password",
            username=username,
            realm=realm,
            reason="invalid_credentials"
        )
    
    @classmethod
    def account_locked(
        cls,
        username: Optional[str] = None,
        realm: Optional[str] = None,
        unlock_time: Optional[int] = None
    ) -> 'AuthenticationFailed':
        """Create exception for locked account."""
        message = "Account is temporarily locked"
        if unlock_time:
            message += f" for {unlock_time} seconds"
            
        return cls(
            message=message,
            username=username,
            realm=realm,
            reason="account_locked",
            retry_after=unlock_time
        )
    
    @classmethod
    def rate_limited(
        cls,
        retry_after: int,
        username: Optional[str] = None,
        realm: Optional[str] = None
    ) -> 'AuthenticationFailed':
        """Create exception for rate limiting."""
        return cls(
            message=f"Too many authentication attempts. Retry in {retry_after} seconds",
            username=username,
            realm=realm,
            reason="rate_limited",
            retry_after=retry_after
        )
    
    @classmethod
    def realm_not_available(
        cls,
        realm: str,
        username: Optional[str] = None
    ) -> 'AuthenticationFailed':
        """Create exception for unavailable realm."""
        return cls(
            message=f"Authentication realm '{realm}' is not available",
            username=username,
            realm=realm,
            reason="realm_unavailable"
        )
    
    def __str__(self) -> str:
        """String representation with context."""
        base_msg = super().__str__()
        
        context_parts = []
        if self.username:
            context_parts.append(f"username={self.username}")
        if self.realm:
            context_parts.append(f"realm={self.realm}")
        if self.reason:
            context_parts.append(f"reason={self.reason}")
        
        if context_parts:
            return f"{base_msg} ({', '.join(context_parts)})"
        
        return base_msg