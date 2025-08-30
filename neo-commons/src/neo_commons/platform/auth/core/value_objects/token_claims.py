"""Token claims value object with JWT claims parsing and validation."""

import json
import base64
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union


@dataclass(frozen=True)
class TokenClaims:
    """JWT token claims value object with parsing and validation.
    
    Handles ONLY token claims representation and standard JWT validation.
    Does not perform authentication logic - that's handled by services.
    """
    
    raw_claims: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate token claims structure."""
        if not isinstance(self.raw_claims, dict):
            raise TypeError("Token claims must be a dictionary")
        
        # Validate standard JWT claims if present
        self._validate_standard_claims()
    
    def _validate_standard_claims(self) -> None:
        """Validate standard JWT claims format."""
        # Validate 'exp' (expiration time)
        if 'exp' in self.raw_claims:
            if not isinstance(self.raw_claims['exp'], (int, float)):
                raise ValueError("'exp' claim must be a numeric timestamp")
        
        # Validate 'iat' (issued at)
        if 'iat' in self.raw_claims:
            if not isinstance(self.raw_claims['iat'], (int, float)):
                raise ValueError("'iat' claim must be a numeric timestamp")
        
        # Validate 'nbf' (not before)
        if 'nbf' in self.raw_claims:
            if not isinstance(self.raw_claims['nbf'], (int, float)):
                raise ValueError("'nbf' claim must be a numeric timestamp")
        
        # Validate 'aud' (audience)
        if 'aud' in self.raw_claims:
            aud = self.raw_claims['aud']
            if not isinstance(aud, (str, list)):
                raise ValueError("'aud' claim must be a string or list of strings")
            if isinstance(aud, list):
                if not all(isinstance(item, str) for item in aud):
                    raise ValueError("All items in 'aud' list must be strings")
        
        # Validate 'iss' (issuer)
        if 'iss' in self.raw_claims:
            if not isinstance(self.raw_claims['iss'], str):
                raise ValueError("'iss' claim must be a string")
        
        # Validate 'sub' (subject)
        if 'sub' in self.raw_claims:
            if not isinstance(self.raw_claims['sub'], str):
                raise ValueError("'sub' claim must be a string")
    
    @classmethod
    def from_jwt_payload(cls, payload: str) -> 'TokenClaims':
        """Create TokenClaims from JWT payload string.
        
        Args:
            payload: Base64-encoded JWT payload
            
        Returns:
            TokenClaims instance
            
        Raises:
            ValueError: If payload cannot be decoded
        """
        try:
            # Add padding if needed for base64 decoding
            payload_padded = payload + '=' * (4 - len(payload) % 4)
            decoded_bytes = base64.urlsafe_b64decode(payload_padded)
            claims_dict = json.loads(decoded_bytes.decode('utf-8'))
            return cls(raw_claims=claims_dict)
        except Exception as e:
            raise ValueError(f"Cannot decode JWT payload: {e}") from e
    
    @property
    def subject(self) -> Optional[str]:
        """Get subject (sub) claim."""
        return self.raw_claims.get('sub')
    
    @property
    def issuer(self) -> Optional[str]:
        """Get issuer (iss) claim."""
        return self.raw_claims.get('iss')
    
    @property
    def audience(self) -> Optional[Union[str, List[str]]]:
        """Get audience (aud) claim."""
        return self.raw_claims.get('aud')
    
    @property
    def expiration(self) -> Optional[datetime]:
        """Get expiration time as datetime."""
        exp = self.raw_claims.get('exp')
        if exp is None:
            return None
        return datetime.fromtimestamp(exp, timezone.utc)
    
    @property
    def issued_at(self) -> Optional[datetime]:
        """Get issued at time as datetime."""
        iat = self.raw_claims.get('iat')
        if iat is None:
            return None
        return datetime.fromtimestamp(iat, timezone.utc)
    
    @property
    def not_before(self) -> Optional[datetime]:
        """Get not before time as datetime."""
        nbf = self.raw_claims.get('nbf')
        if nbf is None:
            return None
        return datetime.fromtimestamp(nbf, timezone.utc)
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired based on exp claim."""
        exp = self.expiration
        if exp is None:
            return False  # No expiration claim
        return datetime.now(timezone.utc) >= exp
    
    @property
    def is_not_yet_valid(self) -> bool:
        """Check if token is not yet valid based on nbf claim."""
        nbf = self.not_before
        if nbf is None:
            return False  # No not-before claim
        return datetime.now(timezone.utc) < nbf
    
    def get_claim(self, claim_name: str, default: Any = None) -> Any:
        """Get specific claim value with default."""
        return self.raw_claims.get(claim_name, default)
    
    def has_claim(self, claim_name: str) -> bool:
        """Check if claim exists."""
        return claim_name in self.raw_claims
    
    def get_custom_claims(self) -> Dict[str, Any]:
        """Get non-standard claims (excluding JWT reserved claims)."""
        reserved_claims = {
            'iss', 'sub', 'aud', 'exp', 'nbf', 'iat', 'jti'
        }
        return {
            k: v for k, v in self.raw_claims.items()
            if k not in reserved_claims
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return dict(self.raw_claims)
    
    def __str__(self) -> str:
        """String representation."""
        return f"TokenClaims(claims={len(self.raw_claims)})"
    
    def __repr__(self) -> str:
        """Debug representation."""
        return f"TokenClaims(raw_claims={self.raw_claims})"