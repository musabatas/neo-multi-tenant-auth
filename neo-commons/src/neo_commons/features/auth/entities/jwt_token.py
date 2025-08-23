"""JWT token entity."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from ....core.value_objects.identifiers import TokenId


@dataclass(frozen=True)
class JWTToken:
    """JWT token with metadata."""
    
    # Token data
    access_token: str
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    refresh_expires_in: Optional[int] = None
    scope: Optional[str] = None
    
    # Token metadata
    token_id: Optional[TokenId] = None
    issued_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # Additional claims
    claims: Dict = None
    
    def __post_init__(self):
        """Initialize computed fields."""
        if not self.access_token:
            raise ValueError("access_token is required")
        
        # Set defaults using object.__setattr__ since dataclass is frozen
        if self.claims is None:
            object.__setattr__(self, 'claims', {})
        
        if self.issued_at is None:
            object.__setattr__(self, 'issued_at', datetime.now(timezone.utc))
        
        # Calculate expires_at if expires_in is provided
        if self.expires_at is None and self.expires_in is not None:
            expires_at = self.issued_at + timedelta(seconds=self.expires_in)
            object.__setattr__(self, 'expires_at', expires_at)
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) >= self.expires_at
    
    @property
    def time_until_expiry(self) -> Optional[int]:
        """Get seconds until token expires."""
        if self.expires_at is None:
            return None
        
        delta = self.expires_at - datetime.now(timezone.utc)
        return max(0, int(delta.total_seconds()))
    
    @property
    def is_refresh_token_expired(self) -> bool:
        """Check if refresh token is expired."""
        if not self.refresh_token or not self.refresh_expires_in:
            return True
        
        refresh_expires_at = self.issued_at + timedelta(
            seconds=self.refresh_expires_in
        )
        return datetime.now(timezone.utc) >= refresh_expires_at
    
    def get_claim(self, claim_name: str, default=None):
        """Get a specific claim from the token."""
        return self.claims.get(claim_name, default)
    
    def has_claim(self, claim_name: str) -> bool:
        """Check if token has a specific claim."""
        return claim_name in self.claims
    
    def to_dict(self) -> Dict:
        """Convert token to dictionary."""
        result = {
            'access_token': self.access_token,
            'token_type': self.token_type,
        }
        
        if self.expires_in is not None:
            result['expires_in'] = self.expires_in
            
        if self.refresh_token:
            result['refresh_token'] = self.refresh_token
            
        if self.refresh_expires_in is not None:
            result['refresh_expires_in'] = self.refresh_expires_in
            
        if self.scope:
            result['scope'] = self.scope
        
        return result
    
    @classmethod
    def from_keycloak_response(cls, response: Dict) -> 'JWTToken':
        """Create JWTToken from Keycloak token response."""
        return cls(
            access_token=response['access_token'],
            token_type=response.get('token_type', 'Bearer'),
            expires_in=response.get('expires_in'),
            refresh_token=response.get('refresh_token'),
            refresh_expires_in=response.get('refresh_expires_in'),
            scope=response.get('scope'),
        )
    
    def create_refresh_copy(self, new_access_token: str, new_expires_in: int) -> 'JWTToken':
        """Create a new token with refreshed access token."""
        return JWTToken(
            access_token=new_access_token,
            token_type=self.token_type,
            expires_in=new_expires_in,
            refresh_token=self.refresh_token,  # Keep same refresh token
            refresh_expires_in=self.refresh_expires_in,
            scope=self.scope,
            token_id=self.token_id,
            claims=self.claims.copy() if self.claims else {},
        )