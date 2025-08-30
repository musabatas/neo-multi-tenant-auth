"""Token metadata domain entity."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Set
from ..value_objects import AccessToken, RefreshToken, TokenClaims


@dataclass
class TokenMetadata:
    """Token metadata entity for tracking token lifecycle and properties.
    
    Handles ONLY token metadata representation and analysis.
    Does not perform token operations - that's handled by token services.
    """
    
    # Token Identity
    access_token: Optional[AccessToken] = None
    refresh_token: Optional[RefreshToken] = None
    token_claims: Optional[TokenClaims] = None
    
    # Token Lifecycle
    issued_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    not_before: Optional[datetime] = None
    
    # Token Properties
    token_type: str = "Bearer"
    scope: Set[str] = field(default_factory=set)
    audience: Set[str] = field(default_factory=set)
    issuer: Optional[str] = None
    
    # Cryptographic Info
    algorithm: Optional[str] = None
    key_id: Optional[str] = None
    signature_valid: Optional[bool] = None
    
    # Usage Tracking
    first_used_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    
    # Security Context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    risk_indicators: Set[str] = field(default_factory=set)
    
    # Additional Metadata
    custom_claims: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    
    def __post_init__(self) -> None:
        """Initialize token metadata from claims if available."""
        if self.token_claims and not self.issued_at:
            self._extract_metadata_from_claims()
        
        # Ensure timezone awareness
        self._ensure_timezone_awareness()
    
    def _extract_metadata_from_claims(self) -> None:
        """Extract metadata from token claims."""
        if not self.token_claims:
            return
        
        # Standard JWT claims
        if self.token_claims.issued_at:
            self.issued_at = self.token_claims.issued_at
        
        if self.token_claims.expiration:
            self.expires_at = self.token_claims.expiration
        
        if self.token_claims.not_before:
            self.not_before = self.token_claims.not_before
        
        if self.token_claims.issuer:
            self.issuer = self.token_claims.issuer
        
        # Audience handling
        if self.token_claims.audience:
            if isinstance(self.token_claims.audience, str):
                self.audience.add(self.token_claims.audience)
            elif isinstance(self.token_claims.audience, list):
                self.audience.update(self.token_claims.audience)
        
        # Scope handling
        scope_claim = self.token_claims.get_claim('scope')
        if scope_claim:
            if isinstance(scope_claim, str):
                self.scope.update(scope_claim.split())
            elif isinstance(scope_claim, list):
                self.scope.update(scope_claim)
        
        # Custom claims
        self.custom_claims.update(self.token_claims.get_custom_claims())
    
    def _ensure_timezone_awareness(self) -> None:
        """Ensure all datetime fields are timezone-aware."""
        timestamp_fields = [
            'issued_at', 'expires_at', 'not_before', 
            'first_used_at', 'last_used_at'
        ]
        
        for field_name in timestamp_fields:
            timestamp = getattr(self, field_name)
            if timestamp and timestamp.tzinfo is None:
                setattr(self, field_name, timestamp.replace(tzinfo=timezone.utc))
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) >= self.expires_at
    
    @property
    def is_not_yet_valid(self) -> bool:
        """Check if token is not yet valid (nbf claim)."""
        if not self.not_before:
            return False
        return datetime.now(timezone.utc) < self.not_before
    
    @property
    def is_valid_time_wise(self) -> bool:
        """Check if token is valid based on time claims."""
        return not self.is_expired and not self.is_not_yet_valid
    
    @property
    def seconds_until_expiry(self) -> Optional[int]:
        """Get seconds until token expires."""
        if not self.expires_at:
            return None
        
        if self.is_expired:
            return 0
        
        delta = self.expires_at - datetime.now(timezone.utc)
        return max(0, int(delta.total_seconds()))
    
    @property
    def age_in_seconds(self) -> Optional[int]:
        """Get token age in seconds."""
        if not self.issued_at:
            return None
        
        delta = datetime.now(timezone.utc) - self.issued_at
        return int(delta.total_seconds())
    
    @property
    def lifetime_seconds(self) -> Optional[int]:
        """Get token lifetime in seconds."""
        if not self.issued_at or not self.expires_at:
            return None
        
        delta = self.expires_at - self.issued_at
        return int(delta.total_seconds())
    
    @property
    def is_fresh(self, max_age_seconds: int = 300) -> bool:
        """Check if token is fresh (recently issued).
        
        Args:
            max_age_seconds: Maximum age to consider fresh (default 5 minutes)
        """
        age = self.age_in_seconds
        return age is not None and age <= max_age_seconds
    
    @property
    def has_suspicious_activity(self) -> bool:
        """Check if token has suspicious activity indicators."""
        return len(self.risk_indicators) > 0
    
    def record_usage(
        self, 
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """Record token usage.
        
        Args:
            ip_address: Client IP address
            user_agent: Client user agent
        """
        now = datetime.now(timezone.utc)
        
        if self.usage_count == 0:
            self.first_used_at = now
        
        self.last_used_at = now
        self.usage_count += 1
        
        # Update security context
        if ip_address:
            if self.ip_address and self.ip_address != ip_address:
                self.risk_indicators.add("ip_address_change")
            self.ip_address = ip_address
        
        if user_agent:
            if self.user_agent and self.user_agent != user_agent:
                self.risk_indicators.add("user_agent_change")
            self.user_agent = user_agent
    
    def add_risk_indicator(self, indicator: str, details: Optional[str] = None) -> None:
        """Add a risk indicator.
        
        Args:
            indicator: Risk indicator identifier
            details: Additional details about the risk
        """
        self.risk_indicators.add(indicator)
        
        if details:
            risk_details = self.custom_claims.get('risk_details', {})
            risk_details[indicator] = details
            self.custom_claims['risk_details'] = risk_details
    
    def add_scope(self, scope: str) -> None:
        """Add a scope to the token."""
        self.scope.add(scope)
    
    def remove_scope(self, scope: str) -> None:
        """Remove a scope from the token."""
        self.scope.discard(scope)
    
    def has_scope(self, scope: str) -> bool:
        """Check if token has a specific scope."""
        return scope in self.scope
    
    def add_audience(self, audience: str) -> None:
        """Add an audience to the token."""
        self.audience.add(audience)
    
    def has_audience(self, audience: str) -> bool:
        """Check if token has a specific audience."""
        return audience in self.audience
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the token."""
        self.tags.add(tag.lower())
    
    def has_tag(self, tag: str) -> bool:
        """Check if token has a specific tag."""
        return tag.lower() in self.tags
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'token_type': self.token_type,
            'issued_at': self.issued_at.isoformat() if self.issued_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'not_before': self.not_before.isoformat() if self.not_before else None,
            'scope': list(self.scope),
            'audience': list(self.audience),
            'issuer': self.issuer,
            'algorithm': self.algorithm,
            'key_id': self.key_id,
            'signature_valid': self.signature_valid,
            'first_used_at': self.first_used_at.isoformat() if self.first_used_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'usage_count': self.usage_count,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'risk_indicators': list(self.risk_indicators),
            'custom_claims': self.custom_claims,
            'tags': list(self.tags),
            'is_expired': self.is_expired,
            'is_not_yet_valid': self.is_not_yet_valid,
            'is_valid_time_wise': self.is_valid_time_wise,
            'seconds_until_expiry': self.seconds_until_expiry,
            'age_in_seconds': self.age_in_seconds,
            'lifetime_seconds': self.lifetime_seconds,
            'is_fresh': self.is_fresh,
            'has_suspicious_activity': self.has_suspicious_activity
        }
    
    def __str__(self) -> str:
        """String representation."""
        status = "valid" if self.is_valid_time_wise else "invalid"
        return f"TokenMetadata(type={self.token_type}, status={status}, usage={self.usage_count})"
    
    def __repr__(self) -> str:
        """Debug representation."""
        return (
            f"TokenMetadata(token_type={self.token_type}, "
            f"expires_at={self.expires_at}, usage_count={self.usage_count})"
        )