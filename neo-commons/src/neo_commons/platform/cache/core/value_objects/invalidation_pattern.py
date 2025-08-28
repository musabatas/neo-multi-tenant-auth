"""Invalidation pattern value object.

ONLY pattern matching - pattern matching for cache invalidation with
wildcard and regex support.

Following maximum separation architecture - one file = one purpose.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PatternType(Enum):
    """Types of invalidation patterns supported."""
    
    EXACT = "exact"       # Exact string match
    WILDCARD = "wildcard" # Wildcard pattern with * and ?
    REGEX = "regex"       # Regular expression pattern
    PREFIX = "prefix"     # Prefix matching
    SUFFIX = "suffix"     # Suffix matching


@dataclass(frozen=True)
class InvalidationPattern:
    """Invalidation pattern value object.
    
    Pattern matching for cache invalidation with wildcard and regex support.
    
    Features:
    - Multiple pattern types (exact, wildcard, regex, prefix, suffix)
    - Pattern validation and compilation
    - Efficient matching against cache keys
    - Case-sensitive and case-insensitive matching
    - Pattern optimization for performance
    """
    
    pattern: str
    pattern_type: PatternType
    case_sensitive: bool = True
    
    def __post_init__(self):
        """Validate invalidation pattern."""
        if not self.pattern:
            raise ValueError("Pattern cannot be empty")
        
        # Validate regex patterns at creation time
        if self.pattern_type == PatternType.REGEX:
            try:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                re.compile(self.pattern, flags)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
    
    @classmethod
    def exact(cls, pattern: str, case_sensitive: bool = True) -> "InvalidationPattern":
        """Create exact match pattern."""
        return cls(pattern, PatternType.EXACT, case_sensitive)
    
    @classmethod
    def wildcard(cls, pattern: str, case_sensitive: bool = True) -> "InvalidationPattern":
        """Create wildcard pattern (* and ? supported)."""
        return cls(pattern, PatternType.WILDCARD, case_sensitive)
    
    @classmethod
    def regex(cls, pattern: str, case_sensitive: bool = True) -> "InvalidationPattern":
        """Create regex pattern."""
        return cls(pattern, PatternType.REGEX, case_sensitive)
    
    @classmethod
    def prefix(cls, prefix: str, case_sensitive: bool = True) -> "InvalidationPattern":
        """Create prefix matching pattern."""
        return cls(prefix, PatternType.PREFIX, case_sensitive)
    
    @classmethod
    def suffix(cls, suffix: str, case_sensitive: bool = True) -> "InvalidationPattern":
        """Create suffix matching pattern."""
        return cls(suffix, PatternType.SUFFIX, case_sensitive)
    
    @classmethod
    def user_keys(cls, user_id: str) -> "InvalidationPattern":
        """Create pattern to match all user keys."""
        return cls.prefix(f"user:{user_id}:")
    
    @classmethod
    def tenant_keys(cls, tenant_id: str) -> "InvalidationPattern":
        """Create pattern to match all tenant keys."""
        return cls.prefix(f"tenant:{tenant_id}:")
    
    @classmethod
    def session_keys(cls, session_id: str) -> "InvalidationPattern":
        """Create pattern to match all session keys.""" 
        return cls.prefix(f"session:{session_id}:")
    
    def matches(self, cache_key: str) -> bool:
        """Check if cache key matches this pattern."""
        # Apply case sensitivity
        key_to_match = cache_key if self.case_sensitive else cache_key.lower()
        pattern_to_use = self.pattern if self.case_sensitive else self.pattern.lower()
        
        if self.pattern_type == PatternType.EXACT:
            return key_to_match == pattern_to_use
        
        elif self.pattern_type == PatternType.PREFIX:
            return key_to_match.startswith(pattern_to_use)
        
        elif self.pattern_type == PatternType.SUFFIX:
            return key_to_match.endswith(pattern_to_use)
        
        elif self.pattern_type == PatternType.WILDCARD:
            # Convert wildcard to regex
            regex_pattern = pattern_to_use.replace("*", ".*").replace("?", ".")
            flags = 0 if self.case_sensitive else re.IGNORECASE
            return bool(re.match(f"^{regex_pattern}$", key_to_match, flags))
        
        elif self.pattern_type == PatternType.REGEX:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            return bool(re.search(pattern_to_use, key_to_match, flags))
        
        return False
    
    def get_compiled_regex(self) -> Optional[re.Pattern]:
        """Get compiled regex pattern for efficient matching."""
        flags = 0 if self.case_sensitive else re.IGNORECASE
        
        if self.pattern_type == PatternType.EXACT:
            pattern_to_use = self.pattern if self.case_sensitive else self.pattern.lower()
            return re.compile(f"^{re.escape(pattern_to_use)}$", flags)
        
        elif self.pattern_type == PatternType.PREFIX:
            pattern_to_use = self.pattern if self.case_sensitive else self.pattern.lower()
            return re.compile(f"^{re.escape(pattern_to_use)}", flags)
        
        elif self.pattern_type == PatternType.SUFFIX:
            pattern_to_use = self.pattern if self.case_sensitive else self.pattern.lower()
            return re.compile(f"{re.escape(pattern_to_use)}$", flags)
        
        elif self.pattern_type == PatternType.WILDCARD:
            pattern_to_use = self.pattern if self.case_sensitive else self.pattern.lower()
            regex_pattern = pattern_to_use.replace("*", ".*").replace("?", ".")
            return re.compile(f"^{regex_pattern}$", flags)
        
        elif self.pattern_type == PatternType.REGEX:
            pattern_to_use = self.pattern if self.case_sensitive else self.pattern.lower()
            return re.compile(pattern_to_use, flags)
        
        return None
    
    def estimate_selectivity(self) -> float:
        """Estimate pattern selectivity (0.0 = very selective, 1.0 = matches everything)."""
        if self.pattern_type == PatternType.EXACT:
            return 0.0  # Very selective
        
        elif self.pattern_type == PatternType.PREFIX:
            # Longer prefixes are more selective
            return max(0.1, 1.0 - (len(self.pattern) / 100.0))
        
        elif self.pattern_type == PatternType.SUFFIX:
            # Longer suffixes are more selective  
            return max(0.1, 1.0 - (len(self.pattern) / 100.0))
        
        elif self.pattern_type == PatternType.WILDCARD:
            # Count wildcards - more wildcards = less selective
            wildcard_count = self.pattern.count("*") + self.pattern.count("?")
            return min(0.9, 0.2 + (wildcard_count * 0.2))
        
        elif self.pattern_type == PatternType.REGEX:
            # Complex estimation - assume medium selectivity
            return 0.5
        
        return 0.5
    
    def __str__(self) -> str:
        """String representation."""
        sensitivity = "case-sensitive" if self.case_sensitive else "case-insensitive"
        return f"{self.pattern_type.value}:'{self.pattern}' ({sensitivity})"