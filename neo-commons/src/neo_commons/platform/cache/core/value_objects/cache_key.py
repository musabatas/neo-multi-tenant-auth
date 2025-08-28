"""Cache key value object.

ONLY key validation - immutable cache key with validation, supports
hierarchical keys and pattern matching for invalidation.

Following maximum separation architecture - one file = one purpose.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CacheKey:
    """Cache key value object.
    
    Immutable cache key with validation and pattern matching support.
    
    Features:
    - Hierarchical keys (user:123:profile)
    - Pattern matching for invalidation
    - Length and character restrictions
    - Namespace-aware key generation
    - Validation and sanitization
    """
    
    value: str
    
    # Key constraints
    MAX_LENGTH = 250
    MIN_LENGTH = 1
    
    # Valid characters pattern
    VALID_PATTERN = re.compile(r'^[a-zA-Z0-9._:/-]+$')
    
    def __post_init__(self):
        """Validate cache key on creation."""
        if not self.value:
            raise ValueError("Cache key cannot be empty")
        
        if len(self.value) < self.MIN_LENGTH:
            raise ValueError(f"Cache key too short, minimum {self.MIN_LENGTH} characters")
        
        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(f"Cache key too long, maximum {self.MAX_LENGTH} characters")
        
        if not self.VALID_PATTERN.match(self.value):
            raise ValueError(
                "Cache key contains invalid characters. "
                "Only alphanumeric, dot, underscore, colon, slash, and hyphen allowed"
            )
    
    @classmethod
    def from_parts(cls, *parts: str) -> "CacheKey":
        """Create cache key from multiple parts joined with colon."""
        if not parts:
            raise ValueError("At least one part required")
        
        # Filter out empty parts and join with colon
        clean_parts = [str(part).strip() for part in parts if str(part).strip()]
        if not clean_parts:
            raise ValueError("No valid parts provided")
        
        return cls(":".join(clean_parts))
    
    @classmethod
    def user_key(cls, user_id: str, key: str) -> "CacheKey":
        """Create user-specific cache key."""
        return cls.from_parts("user", user_id, key)
    
    @classmethod
    def tenant_key(cls, tenant_id: str, key: str) -> "CacheKey":
        """Create tenant-specific cache key."""
        return cls.from_parts("tenant", tenant_id, key)
    
    @classmethod
    def session_key(cls, session_id: str, key: str) -> "CacheKey":
        """Create session-specific cache key."""
        return cls.from_parts("session", session_id, key)
    
    def matches_pattern(self, pattern: str) -> bool:
        """Check if key matches given wildcard pattern."""
        # Convert wildcard pattern to regex
        regex_pattern = pattern.replace("*", ".*").replace("?", ".")
        return bool(re.match(f"^{regex_pattern}$", self.value))
    
    def get_parts(self) -> list[str]:
        """Get key parts split by colon."""
        return self.value.split(":")
    
    def get_prefix(self) -> Optional[str]:
        """Get key prefix (first part before colon)."""
        parts = self.get_parts()
        return parts[0] if parts else None
    
    def starts_with(self, prefix: str) -> bool:
        """Check if key starts with given prefix."""
        return self.value.startswith(prefix)
    
    def ends_with(self, suffix: str) -> bool:
        """Check if key ends with given suffix."""
        return self.value.endswith(suffix)
    
    def contains(self, substring: str) -> bool:
        """Check if key contains given substring."""
        return substring in self.value
    
    def get_depth(self) -> int:
        """Get hierarchical depth (number of colon separators + 1)."""
        return len(self.get_parts())
    
    def to_string(self) -> str:
        """Get string representation."""
        return self.value
    
    def __str__(self) -> str:
        """String representation."""
        return self.value