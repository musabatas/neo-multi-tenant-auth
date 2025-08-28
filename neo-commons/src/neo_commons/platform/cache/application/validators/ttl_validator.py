"""TTL validator.

ONLY TTL validation - validates cache TTL values with business rules
and optimal caching strategies.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from typing import List, Optional

from ...core.value_objects.cache_ttl import CacheTTL


@dataclass
class TTLValidationResult:
    """Result of TTL validation."""
    
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    recommendations: List[str]
    ttl_seconds: Optional[int] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.recommendations is None:
            self.recommendations = []


class TTLValidator:
    """TTL validator with business rules and caching strategy optimization.
    
    Validates TTL values with:
    - Business rule validation (minimum/maximum TTL constraints)
    - Performance validation (optimal TTL ranges for different data types)
    - Memory efficiency validation (TTL impact on cache size)
    - Consistency validation (TTL patterns across related data)
    - Strategy recommendations (appropriate TTL for use cases)
    """
    
    # TTL constraints (in seconds)
    MIN_TTL = 1                    # 1 second minimum (excluding special values)
    MAX_TTL = 30 * 24 * 3600       # 30 days maximum
    
    # Recommended TTL ranges for different data types
    RECOMMENDED_RANGES = {
        "session": (15 * 60, 4 * 3600),        # 15 minutes to 4 hours
        "user_data": (5 * 60, 2 * 3600),       # 5 minutes to 2 hours
        "configuration": (10 * 60, 24 * 3600), # 10 minutes to 1 day
        "static_data": (1 * 3600, 7 * 24 * 3600), # 1 hour to 7 days
        "computed": (1 * 60, 30 * 60),         # 1 minute to 30 minutes
        "temporary": (30, 5 * 60),              # 30 seconds to 5 minutes
    }
    
    # Performance thresholds
    VERY_SHORT_THRESHOLD = 30       # Very short TTL (< 30s)
    SHORT_THRESHOLD = 5 * 60        # Short TTL (< 5m)
    LONG_THRESHOLD = 24 * 3600      # Long TTL (> 1d)
    VERY_LONG_THRESHOLD = 7 * 24 * 3600  # Very long TTL (> 7d)
    
    def __init__(
        self,
        min_ttl: Optional[int] = None,
        max_ttl: Optional[int] = None,
        allow_never_expire: bool = True,
        allow_instant_expire: bool = True
    ):
        """Initialize TTL validator.
        
        Args:
            min_ttl: Minimum allowed TTL in seconds
            max_ttl: Maximum allowed TTL in seconds
            allow_never_expire: Whether to allow never-expire TTL
            allow_instant_expire: Whether to allow instant-expire TTL
        """
        self.min_ttl = min_ttl or self.MIN_TTL
        self.max_ttl = max_ttl or self.MAX_TTL
        self.allow_never_expire = allow_never_expire
        self.allow_instant_expire = allow_instant_expire
    
    def validate(self, ttl_seconds: int) -> TTLValidationResult:
        """Validate TTL value with comprehensive rules.
        
        Args:
            ttl_seconds: TTL value in seconds to validate
            
        Returns:
            Validation result with errors, warnings, and recommendations
        """
        errors = []
        warnings = []
        recommendations = []
        
        # Basic validation (let CacheTTL handle basic validation)
        try:
            cache_ttl = CacheTTL(ttl_seconds)
        except ValueError as e:
            return TTLValidationResult(
                is_valid=False,
                errors=[str(e)],
                warnings=[],
                recommendations=[],
                ttl_seconds=ttl_seconds
            )
        
        # Special values validation
        self._validate_special_values(cache_ttl, errors, warnings)
        
        # Range validation
        if not cache_ttl.is_never_expire() and not cache_ttl.is_instant_expire():
            self._validate_range(ttl_seconds, errors, warnings)
            self._validate_performance_implications(ttl_seconds, warnings, recommendations)
            self._generate_strategy_recommendations(ttl_seconds, recommendations)
        
        return TTLValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            recommendations=recommendations,
            ttl_seconds=ttl_seconds
        )
    
    def validate_for_data_type(self, ttl_seconds: int, data_type: str) -> TTLValidationResult:
        """Validate TTL for specific data type with targeted recommendations.
        
        Args:
            ttl_seconds: TTL value in seconds
            data_type: Type of data being cached
            
        Returns:
            Validation result with data-type specific recommendations
        """
        result = self.validate(ttl_seconds)
        
        # Add data-type specific recommendations
        if data_type in self.RECOMMENDED_RANGES:
            min_rec, max_rec = self.RECOMMENDED_RANGES[data_type]
            
            if not (min_rec <= ttl_seconds <= max_rec):
                if ttl_seconds != CacheTTL.NEVER_EXPIRE:
                    result.recommendations.append(
                        f"For {data_type} data, recommended TTL range is "
                        f"{min_rec}-{max_rec} seconds ({self._format_duration(min_rec)} - "
                        f"{self._format_duration(max_rec)})"
                    )
        
        return result
    
    def validate_strict(self, ttl_seconds: int) -> None:
        """Strict validation that raises exception on any error.
        
        Args:
            ttl_seconds: TTL value to validate
            
        Raises:
            ValueError: If validation fails
        """
        result = self.validate(ttl_seconds)
        
        if not result.is_valid:
            raise ValueError(f"TTL validation failed: {'; '.join(result.errors)}")
    
    def _validate_special_values(
        self, 
        cache_ttl: CacheTTL, 
        errors: List[str], 
        warnings: List[str]
    ) -> None:
        """Validate special TTL values."""
        if cache_ttl.is_never_expire() and not self.allow_never_expire:
            errors.append("Never-expire TTL not allowed")
        
        if cache_ttl.is_instant_expire() and not self.allow_instant_expire:
            errors.append("Instant-expire TTL not allowed")
        
        if cache_ttl.is_never_expire():
            warnings.append("Never-expire TTL may cause memory leaks if not managed properly")
        
        if cache_ttl.is_instant_expire():
            warnings.append("Instant-expire TTL effectively disables caching")
    
    def _validate_range(
        self, 
        ttl_seconds: int, 
        errors: List[str], 
        warnings: List[str]
    ) -> None:
        """Validate TTL range constraints."""
        if ttl_seconds < self.min_ttl:
            errors.append(f"TTL below minimum: {ttl_seconds} < {self.min_ttl}")
        
        if ttl_seconds > self.max_ttl:
            errors.append(f"TTL exceeds maximum: {ttl_seconds} > {self.max_ttl}")
    
    def _validate_performance_implications(
        self, 
        ttl_seconds: int, 
        warnings: List[str], 
        recommendations: List[str]
    ) -> None:
        """Validate performance implications of TTL value."""
        if ttl_seconds < self.VERY_SHORT_THRESHOLD:
            warnings.append(
                f"Very short TTL ({self._format_duration(ttl_seconds)}) "
                "may cause excessive cache churn"
            )
            recommendations.append("Consider increasing TTL to reduce cache overhead")
        
        elif ttl_seconds < self.SHORT_THRESHOLD:
            recommendations.append(
                "Short TTL ensures data freshness but increases cache misses"
            )
        
        elif ttl_seconds > self.VERY_LONG_THRESHOLD:
            warnings.append(
                f"Very long TTL ({self._format_duration(ttl_seconds)}) "
                "may cause stale data issues"
            )
            recommendations.append("Consider implementing cache invalidation strategies")
        
        elif ttl_seconds > self.LONG_THRESHOLD:
            recommendations.append(
                "Long TTL improves performance but may serve stale data"
            )
    
    def _generate_strategy_recommendations(
        self, 
        ttl_seconds: int, 
        recommendations: List[str]
    ) -> None:
        """Generate caching strategy recommendations."""
        if ttl_seconds < 60:
            recommendations.append("Short TTL suitable for frequently changing data")
        elif ttl_seconds < 3600:
            recommendations.append("Medium TTL good for balance between freshness and performance")
        elif ttl_seconds < 24 * 3600:
            recommendations.append("Long TTL suitable for relatively stable data")
        else:
            recommendations.append("Very long TTL appropriate for rarely changing data")
        
        # Add specific strategy recommendations
        if self.VERY_SHORT_THRESHOLD <= ttl_seconds <= self.SHORT_THRESHOLD:
            recommendations.append("Consider cache warming strategies for frequently accessed data")
        
        if ttl_seconds >= self.LONG_THRESHOLD:
            recommendations.append("Implement cache invalidation triggers for data consistency")
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m"
        elif seconds < 86400:
            return f"{seconds // 3600}h"
        else:
            return f"{seconds // 86400}d"


# Factory function for dependency injection
def create_ttl_validator(
    min_ttl: Optional[int] = None,
    max_ttl: Optional[int] = None,
    allow_never_expire: bool = True,
    allow_instant_expire: bool = True
) -> TTLValidator:
    """Create TTL validator with configuration.
    
    Args:
        min_ttl: Minimum allowed TTL in seconds
        max_ttl: Maximum allowed TTL in seconds
        allow_never_expire: Whether to allow never-expire TTL
        allow_instant_expire: Whether to allow instant-expire TTL
        
    Returns:
        Configured TTL validator
    """
    return TTLValidator(
        min_ttl=min_ttl,
        max_ttl=max_ttl,
        allow_never_expire=allow_never_expire,
        allow_instant_expire=allow_instant_expire
    )