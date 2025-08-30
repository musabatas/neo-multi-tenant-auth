"""Access token value object with JWT validation."""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional


@dataclass(frozen=True)
class AccessToken:
    """JWT access token value object with format validation.
    
    Handles ONLY access token representation and basic validation.
    Does not perform cryptographic validation - that's handled by validators.
    """
    
    value: str
    
    def __post_init__(self) -> None:
        """Validate access token format."""
        if not self.value:
            raise ValueError("Access token cannot be empty")
        
        if not isinstance(self.value, str):
            raise TypeError("Access token must be a string")
        
        # Basic JWT format validation (3 parts separated by dots)
        parts = self.value.split('.')
        if len(parts) != 3:
            raise ValueError("Access token must be in JWT format (header.payload.signature)")
        
        # Check each part is base64-like (contains only valid characters)
        base64_pattern = re.compile(r'^[A-Za-z0-9_-]+$')
        for i, part in enumerate(parts):
            if not part:
                raise ValueError(f"JWT part {i+1} cannot be empty")
            if not base64_pattern.match(part):
                raise ValueError(f"JWT part {i+1} contains invalid characters")
    
    @property
    def header(self) -> str:
        """Get JWT header part."""
        return self.value.split('.')[0]
    
    @property 
    def payload(self) -> str:
        """Get JWT payload part."""
        return self.value.split('.')[1]
    
    @property
    def signature(self) -> str:
        """Get JWT signature part."""
        return self.value.split('.')[2]
    
    @property
    def unsigned_token(self) -> str:
        """Get unsigned token (header.payload) for signature validation."""
        parts = self.value.split('.')
        return f"{parts[0]}.{parts[1]}"
    
    def mask_for_logging(self) -> str:
        """Return masked token safe for logging."""
        if len(self.value) <= 20:
            return "***"
        return f"{self.value[:8]}...{self.value[-8:]}"
    
    def __str__(self) -> str:
        """String representation (masked for security)."""
        return f"AccessToken({self.mask_for_logging()})"
    
    def __repr__(self) -> str:
        """Debug representation (masked for security)."""
        return f"AccessToken(value='{self.mask_for_logging()}')"