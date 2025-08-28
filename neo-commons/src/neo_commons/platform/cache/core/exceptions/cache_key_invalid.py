"""Cache key invalid exception.

ONLY key validation errors - exception raised when cache key
validation fails.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Optional


class CacheKeyInvalid(ValueError):
    """Cache key validation error.
    
    Raised when cache key fails validation rules such as:
    - Empty or null key
    - Key too long or too short
    - Invalid characters in key
    - Malformed hierarchical key structure
    """
    
    def __init__(
        self, 
        key: str, 
        reason: str,
        error_code: Optional[str] = None,
        details: Optional[dict] = None
    ):
        """Initialize cache key validation error.
        
        Args:
            key: The invalid cache key
            reason: Human-readable reason for validation failure
            error_code: Optional machine-readable error code
            details: Optional additional error details
        """
        self.key = key
        self.reason = reason
        self.error_code = error_code or "CACHE_KEY_INVALID"
        self.details = details or {}
        
        super().__init__(f"Invalid cache key '{key}': {reason}")
    
    @classmethod
    def empty_key(cls) -> "CacheKeyInvalid":
        """Create exception for empty cache key."""
        return cls(
            key="",
            reason="Cache key cannot be empty",
            error_code="CACHE_KEY_EMPTY"
        )
    
    @classmethod
    def too_long(cls, key: str, max_length: int) -> "CacheKeyInvalid":
        """Create exception for key that is too long."""
        return cls(
            key=key,
            reason=f"Cache key exceeds maximum length of {max_length} characters",
            error_code="CACHE_KEY_TOO_LONG",
            details={"key_length": len(key), "max_length": max_length}
        )
    
    @classmethod
    def too_short(cls, key: str, min_length: int) -> "CacheKeyInvalid":
        """Create exception for key that is too short."""
        return cls(
            key=key,
            reason=f"Cache key must be at least {min_length} characters",
            error_code="CACHE_KEY_TOO_SHORT",
            details={"key_length": len(key), "min_length": min_length}
        )
    
    @classmethod
    def invalid_characters(cls, key: str, invalid_chars: str) -> "CacheKeyInvalid":
        """Create exception for key with invalid characters."""
        return cls(
            key=key,
            reason=f"Cache key contains invalid characters: {invalid_chars}",
            error_code="CACHE_KEY_INVALID_CHARS",
            details={"invalid_characters": invalid_chars}
        )
    
    @classmethod
    def malformed_hierarchy(cls, key: str, issue: str) -> "CacheKeyInvalid":
        """Create exception for malformed hierarchical key."""
        return cls(
            key=key,
            reason=f"Malformed hierarchical cache key: {issue}",
            error_code="CACHE_KEY_MALFORMED_HIERARCHY",
            details={"hierarchy_issue": issue}
        )
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary for serialization."""
        return {
            "error_type": "CacheKeyInvalid",
            "error_code": self.error_code,
            "key": self.key,
            "reason": self.reason,
            "details": self.details
        }