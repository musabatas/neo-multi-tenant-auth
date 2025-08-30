"""Session ID value object with validation and generation."""

import re
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class SessionId:
    """Session identifier value object with validation.
    
    Handles ONLY session ID representation and validation.
    Does not manage session lifecycle - that's handled by session managers.
    """
    
    value: str
    
    # Class constants for validation
    MIN_LENGTH: ClassVar[int] = 16
    MAX_LENGTH: ClassVar[int] = 255
    
    def __post_init__(self) -> None:
        """Validate session ID format and security requirements."""
        if not self.value:
            raise ValueError("Session ID cannot be empty")
        
        if not isinstance(self.value, str):
            raise TypeError("Session ID must be a string")
        
        # Validate length for security
        if len(self.value) < self.MIN_LENGTH:
            raise ValueError(f"Session ID must be at least {self.MIN_LENGTH} characters")
        
        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(f"Session ID cannot exceed {self.MAX_LENGTH} characters")
        
        # Validate character set (alphanumeric, hyphens, underscores)
        valid_pattern = re.compile(r'^[A-Za-z0-9_-]+$')
        if not valid_pattern.match(self.value):
            raise ValueError("Session ID contains invalid characters (only alphanumeric, hyphens, and underscores allowed)")
        
        # Security check: ensure sufficient entropy
        if self._has_low_entropy():
            raise ValueError("Session ID has insufficient entropy for security")
    
    def _has_low_entropy(self) -> bool:
        """Check if session ID has low entropy (security risk)."""
        # Check for common weak patterns
        
        # All same character
        if len(set(self.value)) == 1:
            return True
        
        # Sequential characters (abc, 123, etc.)
        if self._is_sequential():
            return True
        
        # Repeated patterns (abcabc, 123123, etc.)
        if self._has_repeated_pattern():
            return True
        
        # Too few unique characters relative to length
        unique_chars = len(set(self.value))
        if len(self.value) > 20 and unique_chars < 8:
            return True
        
        return False
    
    def _is_sequential(self) -> bool:
        """Check if string contains sequential characters."""
        if len(self.value) < 4:
            return False
        
        for i in range(len(self.value) - 3):
            substring = self.value[i:i+4]
            # Check if all characters are consecutive ASCII values
            ascii_values = [ord(c) for c in substring]
            if all(ascii_values[j] == ascii_values[j-1] + 1 for j in range(1, len(ascii_values))):
                return True
        
        return False
    
    def _has_repeated_pattern(self) -> bool:
        """Check if string has repeated patterns."""
        if len(self.value) < 8:
            return False
        
        # Check for patterns of length 2-8
        for pattern_length in range(2, min(9, len(self.value) // 2 + 1)):
            pattern = self.value[:pattern_length]
            if self.value == pattern * (len(self.value) // pattern_length):
                return True
        
        return False
    
    @classmethod
    def generate(cls) -> 'SessionId':
        """Generate a cryptographically secure session ID.
        
        Returns:
            New SessionId instance with secure random value
        """
        import secrets
        import string
        
        # Generate 32 character random string (high entropy)
        alphabet = string.ascii_letters + string.digits + '_-'
        session_value = ''.join(secrets.choice(alphabet) for _ in range(32))
        
        return cls(session_value)
    
    @classmethod
    def from_uuid(cls) -> 'SessionId':
        """Generate session ID from UUID v7 (time-ordered).
        
        Returns:
            New SessionId instance from UUID
        """
        from ....utils.uuid import generate_uuid_v7
        
        uuid_value = generate_uuid_v7()
        # Use hex representation without hyphens
        session_value = uuid_value.hex
        
        return cls(session_value)
    
    def mask_for_logging(self) -> str:
        """Return masked session ID safe for logging."""
        if len(self.value) <= 20:
            return "***"
        return f"{self.value[:6]}...{self.value[-6:]}"
    
    def is_valid_format(self) -> bool:
        """Check if session ID has valid format without throwing exceptions."""
        try:
            # Re-run validation logic
            if not self.value or not isinstance(self.value, str):
                return False
            if len(self.value) < self.MIN_LENGTH or len(self.value) > self.MAX_LENGTH:
                return False
            
            valid_pattern = re.compile(r'^[A-Za-z0-9_-]+$')
            if not valid_pattern.match(self.value):
                return False
                
            return not self._has_low_entropy()
        except Exception:
            return False
    
    def __str__(self) -> str:
        """String representation (masked for security)."""
        return f"SessionId({self.mask_for_logging()})"
    
    def __repr__(self) -> str:
        """Debug representation (masked for security)."""
        return f"SessionId(value='{self.mask_for_logging()}')"