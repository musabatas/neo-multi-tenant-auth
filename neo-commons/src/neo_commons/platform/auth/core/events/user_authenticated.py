"""User authentication success event."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from ....core.value_objects.identifiers import UserId, TenantId
from ..value_objects import SessionId, RealmIdentifier


@dataclass(frozen=True)
class UserAuthenticated:
    """Event fired when user successfully authenticates.
    
    Represents ONLY successful authentication occurrence.
    Contains all necessary data for event handlers.
    """
    
    # Core Event Data
    user_id: UserId
    tenant_id: Optional[TenantId]
    realm_id: Optional[RealmIdentifier] = None
    session_id: Optional[SessionId] = None
    
    # Authentication Context
    authentication_method: str = "password"  # password, mfa, sso, api_key
    mfa_verified: bool = False
    
    # User Information
    email: Optional[str] = None
    username: Optional[str] = None
    display_name: Optional[str] = None
    
    # Session Context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_info: Dict[str, Any] = None
    
    # Risk Context
    risk_score: float = 0.0
    risk_indicators: Dict[str, Any] = None
    
    # Event Metadata
    event_timestamp: datetime = None
    event_source: str = "auth_service"
    correlation_id: Optional[str] = None
    
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
        
        # Set default empty dicts
        if self.device_info is None:
            object.__setattr__(self, 'device_info', {})
        
        if self.risk_indicators is None:
            object.__setattr__(self, 'risk_indicators', {})
    
    @property
    def event_type(self) -> str:
        """Get event type identifier."""
        return "user_authenticated"
    
    @property
    def is_high_risk(self) -> bool:
        """Check if authentication has high risk score."""
        return self.risk_score >= 0.7
    
    @property
    def requires_notification(self) -> bool:
        """Check if authentication requires notification."""
        return self.is_high_risk or bool(self.risk_indicators)
    
    @property
    def is_mfa_authentication(self) -> bool:
        """Check if this was an MFA authentication."""
        return self.authentication_method in ['mfa', 'totp', 'sms', 'email'] or self.mfa_verified
    
    @property
    def authentication_source(self) -> str:
        """Get authentication source description."""
        if self.authentication_method == "sso":
            return f"SSO via {self.realm_id.value if self.realm_id else 'unknown'}"
        elif self.is_mfa_authentication:
            return f"MFA ({self.authentication_method})"
        else:
            return self.authentication_method.title()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            'event_type': self.event_type,
            'user_id': str(self.user_id.value),
            'tenant_id': str(self.tenant_id.value) if self.tenant_id else None,
            'realm_id': str(self.realm_id.value) if self.realm_id else None,
            'session_id': str(self.session_id.value) if self.session_id else None,
            'authentication_method': self.authentication_method,
            'mfa_verified': self.mfa_verified,
            'email': self.email,
            'username': self.username,
            'display_name': self.display_name,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'device_info': self.device_info,
            'risk_score': self.risk_score,
            'risk_indicators': self.risk_indicators,
            'event_timestamp': self.event_timestamp.isoformat(),
            'event_source': self.event_source,
            'correlation_id': self.correlation_id,
            'is_high_risk': self.is_high_risk,
            'requires_notification': self.requires_notification,
            'is_mfa_authentication': self.is_mfa_authentication,
            'authentication_source': self.authentication_source
        }
    
    def __str__(self) -> str:
        """String representation."""
        user_display = self.display_name or self.email or str(self.user_id.value)
        return f"UserAuthenticated({user_display}, method={self.authentication_method}, risk={self.risk_score:.2f})"
    
    def __repr__(self) -> str:
        """Debug representation."""
        return (
            f"UserAuthenticated(user_id={self.user_id}, tenant_id={self.tenant_id}, "
            f"authentication_method={self.authentication_method}, mfa_verified={self.mfa_verified})"
        )