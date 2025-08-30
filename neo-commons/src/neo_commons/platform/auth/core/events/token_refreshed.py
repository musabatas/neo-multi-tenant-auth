"""Token refresh success event."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from ....core.value_objects.identifiers import UserId, TenantId
from ..value_objects import AccessToken, RefreshToken, SessionId


@dataclass(frozen=True)
class TokenRefreshed:
    """Event fired when token is successfully refreshed.
    
    Represents ONLY token refresh occurrence.
    Contains all necessary data for token lifecycle tracking.
    """
    
    # Core Event Data
    user_id: UserId
    tenant_id: Optional[TenantId]
    session_id: Optional[SessionId] = None
    
    # Token Information
    old_access_token: Optional[AccessToken] = None
    new_access_token: Optional[AccessToken] = None
    refresh_token: Optional[RefreshToken] = None
    
    # Token Lifecycle
    old_token_expires_at: Optional[datetime] = None
    new_token_expires_at: Optional[datetime] = None
    refresh_token_expires_at: Optional[datetime] = None
    
    # Refresh Context
    refresh_reason: str = "token_expired"  # token_expired, proactive_refresh, user_request
    refresh_method: str = "automatic"  # automatic, manual, background
    
    # Security Context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    risk_score: float = 0.0
    
    # Performance Context
    refresh_duration_ms: Optional[int] = None
    cache_hit: bool = False
    
    # Event Metadata
    event_timestamp: datetime = None
    event_source: str = "token_service"
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
        
        # Ensure expiration timestamps are timezone aware
        if self.old_token_expires_at and self.old_token_expires_at.tzinfo is None:
            object.__setattr__(
                self, 'old_token_expires_at', 
                self.old_token_expires_at.replace(tzinfo=timezone.utc)
            )
        
        if self.new_token_expires_at and self.new_token_expires_at.tzinfo is None:
            object.__setattr__(
                self, 'new_token_expires_at', 
                self.new_token_expires_at.replace(tzinfo=timezone.utc)
            )
        
        if self.refresh_token_expires_at and self.refresh_token_expires_at.tzinfo is None:
            object.__setattr__(
                self, 'refresh_token_expires_at', 
                self.refresh_token_expires_at.replace(tzinfo=timezone.utc)
            )
        
        # Set default metadata
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})
    
    @property
    def event_type(self) -> str:
        """Get event type identifier."""
        return "token_refreshed"
    
    @property
    def is_proactive_refresh(self) -> bool:
        """Check if refresh was proactive (before expiration)."""
        return self.refresh_reason == "proactive_refresh"
    
    @property
    def is_high_risk(self) -> bool:
        """Check if refresh has high risk score."""
        return self.risk_score >= 0.7
    
    @property
    def token_lifespan_seconds(self) -> Optional[int]:
        """Get new token lifespan in seconds."""
        if self.new_token_expires_at and self.event_timestamp:
            delta = self.new_token_expires_at - self.event_timestamp
            return max(0, int(delta.total_seconds()))
        return None
    
    @property
    def token_lifespan_minutes(self) -> Optional[int]:
        """Get new token lifespan in minutes."""
        lifespan = self.token_lifespan_seconds
        return lifespan // 60 if lifespan is not None else None
    
    @property
    def refresh_performance_category(self) -> str:
        """Get refresh performance category."""
        if self.refresh_duration_ms is None:
            return "unknown"
        elif self.refresh_duration_ms < 100:
            return "fast"
        elif self.refresh_duration_ms < 500:
            return "normal"
        elif self.refresh_duration_ms < 1000:
            return "slow"
        else:
            return "very_slow"
    
    @property
    def requires_monitoring(self) -> bool:
        """Check if refresh requires monitoring attention."""
        return (
            self.is_high_risk or
            self.refresh_duration_ms and self.refresh_duration_ms > 1000 or
            self.refresh_reason == "user_request"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            'event_type': self.event_type,
            'user_id': str(self.user_id.value),
            'tenant_id': str(self.tenant_id.value) if self.tenant_id else None,
            'session_id': str(self.session_id.value) if self.session_id else None,
            'old_access_token': str(self.old_access_token.value) if self.old_access_token else None,
            'new_access_token': str(self.new_access_token.value) if self.new_access_token else None,
            'refresh_token': str(self.refresh_token.value) if self.refresh_token else None,
            'old_token_expires_at': self.old_token_expires_at.isoformat() if self.old_token_expires_at else None,
            'new_token_expires_at': self.new_token_expires_at.isoformat() if self.new_token_expires_at else None,
            'refresh_token_expires_at': self.refresh_token_expires_at.isoformat() if self.refresh_token_expires_at else None,
            'refresh_reason': self.refresh_reason,
            'refresh_method': self.refresh_method,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'risk_score': self.risk_score,
            'refresh_duration_ms': self.refresh_duration_ms,
            'cache_hit': self.cache_hit,
            'event_timestamp': self.event_timestamp.isoformat(),
            'event_source': self.event_source,
            'correlation_id': self.correlation_id,
            'metadata': self.metadata,
            'is_proactive_refresh': self.is_proactive_refresh,
            'is_high_risk': self.is_high_risk,
            'token_lifespan_seconds': self.token_lifespan_seconds,
            'token_lifespan_minutes': self.token_lifespan_minutes,
            'refresh_performance_category': self.refresh_performance_category,
            'requires_monitoring': self.requires_monitoring
        }
    
    def __str__(self) -> str:
        """String representation."""
        return f"TokenRefreshed({self.user_id}, reason={self.refresh_reason}, duration={self.refresh_duration_ms}ms)"
    
    def __repr__(self) -> str:
        """Debug representation."""
        return (
            f"TokenRefreshed(user_id={self.user_id}, tenant_id={self.tenant_id}, "
            f"refresh_reason={self.refresh_reason}, risk_score={self.risk_score})"
        )