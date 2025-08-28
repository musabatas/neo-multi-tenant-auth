"""Cache key validator.

ONLY key validation - validates cache keys with business rules
and advanced validation patterns.

Following maximum separation architecture - one file = one purpose.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Set

from ...core.value_objects.cache_key import CacheKey
from ...core.exceptions.cache_key_invalid import CacheKeyInvalid


@dataclass
class CacheKeyValidationResult:
    """Result of cache key validation."""
    
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    key: Optional[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class CacheKeyValidator:
    """Cache key validator with business rules and advanced patterns.
    
    Validates cache keys with:
    - Business rule validation (naming patterns, reserved words)
    - Security validation (injection prevention, safe characters)
    - Performance validation (optimal key patterns for caching)
    - Namespace validation (proper hierarchical structure)
    - Custom validation rules and patterns
    """
    
    # Reserved key prefixes (cannot be used by applications)
    RESERVED_PREFIXES = {
        "system:", "internal:", "cache:", "meta:", "admin:", 
        "monitor:", "health:", "config:", "debug:"
    }
    
    # Dangerous patterns (potential security issues)
    DANGEROUS_PATTERNS = [
        re.compile(r'\.\.'),          # Path traversal
        re.compile(r'[<>"\']'),       # Injection characters
        re.compile(r'[\x00-\x1f]'),   # Control characters
        re.compile(r'\\[rnt]'),       # Escape sequences
    ]
    
    # Performance anti-patterns
    PERFORMANCE_ANTI_PATTERNS = [
        re.compile(r':{3,}'),         # Multiple consecutive colons
        re.compile(r'[._-]{3,}'),     # Multiple consecutive separators
        re.compile(r'^\d+$'),         # Pure numeric keys (poor distribution)
    ]
    
    # Recommended patterns for good cache distribution
    GOOD_PATTERNS = [
        re.compile(r'^[a-z]+:[a-zA-Z0-9_-]+'),  # namespace:identifier pattern
        re.compile(r'^[a-z]+:[0-9]+:[a-z]+'),   # namespace:id:type pattern
    ]
    
    def __init__(
        self,
        max_depth: int = 10,
        allow_reserved: bool = False,
        custom_reserved_prefixes: Optional[Set[str]] = None
    ):
        """Initialize cache key validator.
        
        Args:
            max_depth: Maximum hierarchical depth allowed
            allow_reserved: Whether to allow reserved prefixes
            custom_reserved_prefixes: Additional reserved prefixes
        """
        self.max_depth = max_depth
        self.allow_reserved = allow_reserved
        self.reserved_prefixes = self.RESERVED_PREFIXES.copy()
        
        if custom_reserved_prefixes:
            self.reserved_prefixes.update(custom_reserved_prefixes)
    
    def validate(self, key: str) -> CacheKeyValidationResult:
        """Validate cache key with comprehensive rules.
        
        Args:
            key: Cache key string to validate
            
        Returns:
            Validation result with errors and warnings
        """
        errors = []
        warnings = []
        
        # Basic validation (let CacheKey handle this)
        try:
            cache_key = CacheKey(key)
        except ValueError as e:
            return CacheKeyValidationResult(
                is_valid=False,
                errors=[str(e)],
                warnings=[],
                key=key
            )
        
        # Business rule validation
        self._validate_reserved_prefixes(key, errors, warnings)
        self._validate_security_patterns(key, errors, warnings)
        self._validate_performance_patterns(key, errors, warnings)
        self._validate_hierarchical_depth(cache_key, errors, warnings)
        self._validate_naming_conventions(key, errors, warnings)
        
        # Generate performance recommendations
        self._generate_performance_warnings(key, warnings)
        
        return CacheKeyValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            key=key
        )
    
    def validate_strict(self, key: str) -> None:
        """Strict validation that raises exception on any error.
        
        Args:
            key: Cache key to validate
            
        Raises:
            CacheKeyInvalid: If validation fails
        """
        result = self.validate(key)
        
        if not result.is_valid:
            raise CacheKeyInvalid(
                key=key,
                reason=f"Key validation failed: {'; '.join(result.errors)}"
            )
    
    def _validate_reserved_prefixes(
        self, 
        key: str, 
        errors: List[str], 
        warnings: List[str]
    ) -> None:
        """Validate against reserved prefixes."""
        if not self.allow_reserved:
            for prefix in self.reserved_prefixes:
                if key.startswith(prefix):
                    errors.append(f"Key uses reserved prefix: {prefix}")
                    break
    
    def _validate_security_patterns(
        self, 
        key: str, 
        errors: List[str], 
        warnings: List[str]
    ) -> None:
        """Validate against security anti-patterns."""
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern.search(key):
                errors.append(f"Key contains dangerous pattern: {pattern.pattern}")
    
    def _validate_performance_patterns(
        self, 
        key: str, 
        errors: List[str], 
        warnings: List[str]
    ) -> None:
        """Validate against performance anti-patterns."""
        for pattern in self.PERFORMANCE_ANTI_PATTERNS:
            if pattern.search(key):
                warnings.append(f"Key contains performance anti-pattern: {pattern.pattern}")
    
    def _validate_hierarchical_depth(
        self, 
        cache_key: CacheKey, 
        errors: List[str], 
        warnings: List[str]
    ) -> None:
        """Validate hierarchical depth."""
        depth = cache_key.get_depth()
        
        if depth > self.max_depth:
            errors.append(f"Key depth exceeds maximum: {depth} > {self.max_depth}")
        elif depth > self.max_depth * 0.8:  # 80% of max depth
            warnings.append(f"Key depth approaching maximum: {depth} (max: {self.max_depth})")
    
    def _validate_naming_conventions(
        self, 
        key: str, 
        errors: List[str], 
        warnings: List[str]
    ) -> None:
        """Validate naming conventions."""
        # Check for consistent separator usage
        if ':' in key and '_' in key and '-' in key:
            warnings.append("Key uses multiple separator types (consider consistency)")
        
        # Check for proper namespace usage
        parts = key.split(':')
        if len(parts) > 1:
            namespace = parts[0]
            if not namespace.islower():
                warnings.append("Namespace should be lowercase for consistency")
            
            if len(namespace) < 2:
                warnings.append("Namespace too short, consider more descriptive name")
    
    def _generate_performance_warnings(self, key: str, warnings: List[str]) -> None:
        """Generate performance optimization warnings."""
        # Check if key follows good patterns
        follows_good_pattern = any(
            pattern.match(key) for pattern in self.GOOD_PATTERNS
        )
        
        if not follows_good_pattern and ':' in key:
            warnings.append("Consider using namespace:identifier pattern for better cache distribution")
        
        # Check for very long keys
        if len(key) > 100:  # Less than max but still long
            warnings.append("Long keys may impact cache performance")
        
        # Check for very short keys (may cause collisions)
        if len(key) < 5:
            warnings.append("Very short keys may increase collision probability")


# Factory function for dependency injection
def create_cache_key_validator(
    max_depth: int = 10,
    allow_reserved: bool = False,
    custom_reserved_prefixes: Optional[Set[str]] = None
) -> CacheKeyValidator:
    """Create cache key validator with configuration.
    
    Args:
        max_depth: Maximum hierarchical depth allowed
        allow_reserved: Whether to allow reserved prefixes
        custom_reserved_prefixes: Additional reserved prefixes
        
    Returns:
        Configured cache key validator
    """
    return CacheKeyValidator(
        max_depth=max_depth,
        allow_reserved=allow_reserved,
        custom_reserved_prefixes=custom_reserved_prefixes
    )