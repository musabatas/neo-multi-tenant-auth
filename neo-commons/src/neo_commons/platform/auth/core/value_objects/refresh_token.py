"""Refresh token value object with validation and expiration handling."""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True)
class RefreshToken:
    """Refresh token value object with validation and expiration tracking.
    
    Handles ONLY refresh token representation and basic validation.
    Does not perform actual refresh operations - that's handled by services.
    """
    
    value: str
    expires_at: Optional[datetime] = None
    
    def __post_init__(self) -> None:
        """Validate refresh token format and expiration."""
        if not self.value:
            raise ValueError("Refresh token cannot be empty")
        
        if not isinstance(self.value, str):
            raise TypeError("Refresh token must be a string")
        
        # Validate minimum length for security
        if len(self.value) < 16:
            raise ValueError("Refresh token must be at least 16 characters")
        
        # Check for valid characters (alphanumeric, hyphens, underscores)
        valid_pattern = re.compile(r'^[A-Za-z0-9_-]+$')
        if not valid_pattern.match(self.value):
            raise ValueError("Refresh token contains invalid characters")
        
        # Validate expiration if provided
        if self.expires_at is not None:
            if not isinstance(self.expires_at, datetime):
                raise TypeError("expires_at must be a datetime object")
            
            # Ensure timezone awareness
            if self.expires_at.tzinfo is None:
                # Assume UTC if no timezone provided
                object.__setattr__(self, 'expires_at', self.expires_at.replace(tzinfo=timezone.utc))
    
    @property
    def is_expired(self) -> bool:
        """Check if refresh token is expired."""
        if self.expires_at is None:
            return False  # No expiration set
        
        return datetime.now(timezone.utc) >= self.expires_at
    
    @property
    def expires_in_seconds(self) -> Optional[int]:
        """Get seconds until expiration, None if no expiration."""
        if self.expires_at is None:
            return None
        
        delta = self.expires_at - datetime.now(timezone.utc)
        return max(0, int(delta.total_seconds()))
    
    def mask_for_logging(self) -> str:
        """Return masked token safe for logging."""
        if len(self.value) <= 20:
            return "***"
        return f"{self.value[:8]}...{self.value[-8:]}"
    
    def is_valid_format(self) -> bool:
        """Check if token has valid format without throwing exceptions."""
        try:
            # Re-run validation logic
            if not self.value or not isinstance(self.value, str):
                return False
            if len(self.value) < 16:
                return False
            valid_pattern = re.compile(r'^[A-Za-z0-9_-]+$')
            return valid_pattern.match(self.value) is not None
        except Exception:
            return False
    
    def __str__(self) -> str:
        """String representation (masked for security)."""
        expiry_str = f", expires_at={self.expires_at}" if self.expires_at else ""
        return f"RefreshToken({self.mask_for_logging()}{expiry_str})"
    
    def __repr__(self) -> str:
        """Debug representation (masked for security)."""
        return f"RefreshToken(value='{self.mask_for_logging()}', expires_at={self.expires_at})"