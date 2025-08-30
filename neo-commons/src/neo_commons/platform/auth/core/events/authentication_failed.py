"""Authentication failure event."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from ....core.value_objects.identifiers import UserId, TenantId
from ..value_objects import RealmIdentifier


@dataclass(frozen=True)
class AuthenticationFailedEvent:
    """Event fired when authentication attempt fails.
    
    Represents ONLY authentication failure occurrence.
    Contains all necessary data for security monitoring and rate limiting.
    """
    
    # Core Event Data
    attempted_user_id: Optional[UserId] = None
    attempted_email: Optional[str] = None
    attempted_username: Optional[str] = None
    tenant_id: Optional[TenantId] = None
    realm_id: Optional[RealmIdentifier] = None
    
    # Failure Context
    failure_reason: str = "invalid_credentials"  # invalid_credentials, account_locked, mfa_failed, token_expired
    failure_type: str = "authentication"  # authentication, authorization, validation
    failure_stage: str = "credential_check"  # credential_check, mfa_verification, token_validation
    
    # Security Context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_fingerprint: Optional[str] = None
    
    # Attack Context
    is_brute_force: bool = False
    attempt_count: int = 1
    consecutive_failures: int = 1
    failure_window_minutes: int = 5
    
    # Rate Limiting Context
    rate_limit_applied: bool = False
    rate_limit_duration_seconds: Optional[int] = None
    account_locked: bool = False
    lock_duration_seconds: Optional[int] = None
    
    # Risk Assessment
    risk_score: float = 0.0
    risk_indicators: List[str] = None
    suspicious_patterns: List[str] = None
    
    # Response Context
    block_further_attempts: bool = False
    notify_admin: bool = False
    require_captcha: bool = False
    
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
        
        # Set default empty lists
        if self.risk_indicators is None:
            object.__setattr__(self, 'risk_indicators', [])
        
        if self.suspicious_patterns is None:
            object.__setattr__(self, 'suspicious_patterns', [])
        
        # Set default metadata
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})
        
        # Update risk score based on failure context
        self._calculate_risk_score()
    
    def _calculate_risk_score(self) -> None:
        """Calculate risk score based on failure context."""
        base_score = 0.1  # Base risk for any auth failure
        
        # Failure type adjustments
        if self.failure_reason == "account_locked":
            base_score += 0.2
        elif self.failure_reason == "mfa_failed":
            base_score += 0.3
        elif self.failure_reason == "invalid_credentials":
            base_score += 0.1
        
        # Brute force adjustments
        if self.is_brute_force:
            base_score += 0.4
        
        # Consecutive failure adjustments
        if self.consecutive_failures > 5:
            base_score += 0.3
        elif self.consecutive_failures > 3:
            base_score += 0.2
        
        # Suspicious pattern adjustments
        if len(self.suspicious_patterns) > 2:
            base_score += 0.3
        elif len(self.suspicious_patterns) > 0:
            base_score += 0.1
        
        # Cap at 1.0
        calculated_score = min(1.0, base_score)
        
        # Only update if no explicit risk score was provided
        if self.risk_score == 0.0:
            object.__setattr__(self, 'risk_score', calculated_score)
    
    @property
    def event_type(self) -> str:
        """Get event type identifier."""
        return "authentication_failed"
    
    @property
    def is_high_risk(self) -> bool:
        """Check if failure has high risk score."""
        return self.risk_score >= 0.7
    
    @property
    def is_critical_failure(self) -> bool:
        """Check if failure is critical (requires immediate attention)."""
        return (
            self.is_high_risk or
            self.is_brute_force or
            self.consecutive_failures >= 10 or
            self.account_locked
        )
    
    @property
    def requires_investigation(self) -> bool:
        """Check if failure requires security investigation."""
        return (
            self.is_critical_failure or
            len(self.suspicious_patterns) > 1 or
            self.notify_admin or
            self.failure_reason in ["account_locked", "security_breach"]
        )
    
    @property
    def attempted_identity(self) -> str:
        """Get attempted identity for logging."""
        if self.attempted_email:
            return self.attempted_email
        elif self.attempted_username:
            return self.attempted_username
        elif self.attempted_user_id:
            return str(self.attempted_user_id.value)
        else:
            return "unknown"
    
    @property
    def failure_category(self) -> str:
        """Get failure category for analytics."""
        if self.is_brute_force:
            return "brute_force"
        elif self.failure_reason == "account_locked":
            return "account_locked"
        elif self.failure_reason == "mfa_failed":
            return "mfa_failure"
        elif self.consecutive_failures > 3:
            return "repeated_failure"
        else:
            return "single_failure"
    
    @property
    def rate_limit_duration_minutes(self) -> Optional[int]:
        """Get rate limit duration in minutes."""
        if self.rate_limit_duration_seconds is not None:
            return self.rate_limit_duration_seconds // 60
        return None
    
    @property
    def lock_duration_minutes(self) -> Optional[int]:
        """Get lock duration in minutes."""
        if self.lock_duration_seconds is not None:
            return self.lock_duration_seconds // 60
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            'event_type': self.event_type,
            'attempted_user_id': str(self.attempted_user_id.value) if self.attempted_user_id else None,
            'attempted_email': self.attempted_email,
            'attempted_username': self.attempted_username,
            'tenant_id': str(self.tenant_id.value) if self.tenant_id else None,
            'realm_id': str(self.realm_id.value) if self.realm_id else None,
            'failure_reason': self.failure_reason,
            'failure_type': self.failure_type,
            'failure_stage': self.failure_stage,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'device_fingerprint': self.device_fingerprint,
            'is_brute_force': self.is_brute_force,
            'attempt_count': self.attempt_count,
            'consecutive_failures': self.consecutive_failures,
            'failure_window_minutes': self.failure_window_minutes,
            'rate_limit_applied': self.rate_limit_applied,
            'rate_limit_duration_seconds': self.rate_limit_duration_seconds,
            'rate_limit_duration_minutes': self.rate_limit_duration_minutes,
            'account_locked': self.account_locked,
            'lock_duration_seconds': self.lock_duration_seconds,
            'lock_duration_minutes': self.lock_duration_minutes,
            'risk_score': self.risk_score,
            'risk_indicators': self.risk_indicators,
            'suspicious_patterns': self.suspicious_patterns,
            'block_further_attempts': self.block_further_attempts,
            'notify_admin': self.notify_admin,
            'require_captcha': self.require_captcha,
            'event_timestamp': self.event_timestamp.isoformat(),
            'event_source': self.event_source,
            'correlation_id': self.correlation_id,
            'metadata': self.metadata,
            'attempted_identity': self.attempted_identity,
            'is_high_risk': self.is_high_risk,
            'is_critical_failure': self.is_critical_failure,
            'requires_investigation': self.requires_investigation,
            'failure_category': self.failure_category
        }
    
    def __str__(self) -> str:
        """String representation."""
        return f"AuthenticationFailed({self.attempted_identity}, reason={self.failure_reason}, risk={self.risk_score:.2f})"
    
    def __repr__(self) -> str:
        """Debug representation."""
        return (
            f"AuthenticationFailedEvent(attempted_identity={self.attempted_identity}, "
            f"failure_reason={self.failure_reason}, consecutive_failures={self.consecutive_failures})"
        )