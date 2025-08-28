"""Cache size validator.

ONLY size validation - validates cache entry sizes with memory management
and performance optimization rules.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from typing import Any, List, Optional

from ...core.value_objects.cache_size import CacheSize


@dataclass
class SizeValidationResult:
    """Result of cache size validation."""
    
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    recommendations: List[str]
    size_bytes: int
    size_human: str
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.recommendations is None:
            self.recommendations = []


class SizeValidator:
    """Cache size validator with memory management and performance optimization.
    
    Validates cache entry sizes with:
    - Memory management validation (size limits, memory efficiency)
    - Performance validation (optimal size ranges for cache operations)
    - Storage efficiency validation (compression recommendations)
    - Resource usage validation (prevent memory exhaustion)
    - Serialization impact analysis (size vs performance trade-offs)
    """
    
    # Size thresholds (in bytes)
    TINY_THRESHOLD = 1024            # 1KB - tiny entries
    SMALL_THRESHOLD = 10 * 1024      # 10KB - small entries  
    MEDIUM_THRESHOLD = 100 * 1024    # 100KB - medium entries
    LARGE_THRESHOLD = 1024 * 1024    # 1MB - large entries
    HUGE_THRESHOLD = 10 * 1024 * 1024 # 10MB - huge entries
    
    # Performance impact thresholds
    SERIALIZATION_THRESHOLD = 50 * 1024    # 50KB - serialization becomes expensive
    NETWORK_THRESHOLD = 100 * 1024         # 100KB - network transfer impact
    MEMORY_THRESHOLD = 1024 * 1024         # 1MB - significant memory usage
    
    # Default size limits
    DEFAULT_MAX_SIZE = 100 * 1024 * 1024   # 100MB per entry
    DEFAULT_WARN_SIZE = 10 * 1024 * 1024   # 10MB warning threshold
    
    def __init__(
        self,
        max_size_bytes: Optional[int] = None,
        warn_size_bytes: Optional[int] = None,
        allow_zero_size: bool = True,
        enable_compression_recommendations: bool = True
    ):
        """Initialize cache size validator.
        
        Args:
            max_size_bytes: Maximum allowed size in bytes
            warn_size_bytes: Size threshold for warnings
            allow_zero_size: Whether to allow zero-size entries
            enable_compression_recommendations: Whether to suggest compression
        """
        self.max_size_bytes = max_size_bytes or self.DEFAULT_MAX_SIZE
        self.warn_size_bytes = warn_size_bytes or self.DEFAULT_WARN_SIZE
        self.allow_zero_size = allow_zero_size
        self.enable_compression_recommendations = enable_compression_recommendations
    
    def validate(self, size_bytes: int) -> SizeValidationResult:
        """Validate cache entry size with comprehensive rules.
        
        Args:
            size_bytes: Size in bytes to validate
            
        Returns:
            Validation result with errors, warnings, and recommendations
        """
        errors = []
        warnings = []
        recommendations = []
        
        # Basic validation (let CacheSize handle basic validation)
        try:
            cache_size = CacheSize(size_bytes)
            size_human = cache_size.human_readable()
        except ValueError as e:
            return SizeValidationResult(
                is_valid=False,
                errors=[str(e)],
                warnings=[],
                recommendations=[],
                size_bytes=size_bytes,
                size_human="invalid"
            )
        
        # Size range validation
        self._validate_size_range(size_bytes, errors, warnings)
        
        # Performance impact validation
        self._validate_performance_impact(size_bytes, warnings, recommendations)
        
        # Memory efficiency recommendations
        self._generate_efficiency_recommendations(size_bytes, recommendations)
        
        # Storage strategy recommendations
        self._generate_storage_recommendations(size_bytes, recommendations)
        
        return SizeValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            recommendations=recommendations,
            size_bytes=size_bytes,
            size_human=size_human
        )
    
    def validate_with_value(self, value: Any) -> SizeValidationResult:
        """Validate cache entry by estimating value size.
        
        Args:
            value: Value to cache (size will be estimated)
            
        Returns:
            Validation result with size estimation
        """
        # Estimate size using CacheSize utility
        estimated_size = CacheSize.estimate_object_size(value)
        result = self.validate(estimated_size.bytes)
        
        # Add estimation notice
        result.recommendations.insert(0, "Size estimated - actual serialized size may differ")
        
        return result
    
    def validate_strict(self, size_bytes: int) -> None:
        """Strict validation that raises exception on any error.
        
        Args:
            size_bytes: Size to validate
            
        Raises:
            ValueError: If validation fails
        """
        result = self.validate(size_bytes)
        
        if not result.is_valid:
            raise ValueError(f"Size validation failed: {'; '.join(result.errors)}")
    
    def _validate_size_range(
        self, 
        size_bytes: int, 
        errors: List[str], 
        warnings: List[str]
    ) -> None:
        """Validate size range constraints."""
        if size_bytes == 0 and not self.allow_zero_size:
            errors.append("Zero-size entries not allowed")
        
        if size_bytes > self.max_size_bytes:
            errors.append(
                f"Size exceeds maximum: {CacheSize(size_bytes).human_readable()} > "
                f"{CacheSize(self.max_size_bytes).human_readable()}"
            )
        
        if size_bytes > self.warn_size_bytes:
            warnings.append(
                f"Large cache entry: {CacheSize(size_bytes).human_readable()} "
                "may impact performance"
            )
    
    def _validate_performance_impact(
        self, 
        size_bytes: int, 
        warnings: List[str], 
        recommendations: List[str]
    ) -> None:
        """Validate performance implications of entry size."""
        if size_bytes >= self.MEMORY_THRESHOLD:
            warnings.append(
                f"Large entry ({CacheSize(size_bytes).human_readable()}) "
                "will consume significant memory"
            )
            recommendations.append("Consider splitting large data into smaller cache entries")
        
        if size_bytes >= self.NETWORK_THRESHOLD:
            warnings.append("Large entries increase network transfer time in distributed caches")
            recommendations.append("Consider compression for network-transferred cache entries")
        
        if size_bytes >= self.SERIALIZATION_THRESHOLD:
            warnings.append("Large entries increase serialization/deserialization overhead")
            recommendations.append("Consider binary serialization formats for large data")
        
        if size_bytes >= self.HUGE_THRESHOLD:
            warnings.append("Extremely large entries may cause cache eviction of many smaller entries")
            recommendations.append("Evaluate if this data should be cached or stored elsewhere")
    
    def _generate_efficiency_recommendations(
        self, 
        size_bytes: int, 
        recommendations: List[str]
    ) -> None:
        """Generate memory efficiency recommendations."""
        if size_bytes <= self.TINY_THRESHOLD:
            recommendations.append("Small entry - efficient for frequent access patterns")
        
        elif size_bytes <= self.SMALL_THRESHOLD:
            recommendations.append("Good size for general caching - balanced memory usage")
        
        elif size_bytes <= self.MEDIUM_THRESHOLD:
            recommendations.append("Medium entry - consider access frequency vs memory usage")
            
        elif size_bytes <= self.LARGE_THRESHOLD:
            recommendations.append("Large entry - ensure high cache hit rate justifies memory usage")
            
        else:
            recommendations.append("Very large entry - verify caching is the right solution")
    
    def _generate_storage_recommendations(
        self, 
        size_bytes: int, 
        recommendations: List[str]
    ) -> None:
        """Generate storage strategy recommendations."""
        if not self.enable_compression_recommendations:
            return
        
        if size_bytes >= self.LARGE_THRESHOLD:
            recommendations.append("Consider compression for entries > 1MB")
            recommendations.append("Evaluate compression algorithms (gzip, lz4, zstd)")
        
        if size_bytes >= self.HUGE_THRESHOLD:
            recommendations.append("Consider external storage with cache pointers for very large data")
            recommendations.append("Implement lazy loading strategies for large cached objects")
        
        # Data type specific recommendations
        if size_bytes >= self.MEDIUM_THRESHOLD:
            recommendations.append("For JSON data: consider MessagePack or similar binary formats")
            recommendations.append("For images/files: store references instead of raw data")


class CacheValueSizeEstimator:
    """Utility class for estimating cache value sizes before caching."""
    
    @staticmethod
    def estimate_json_size(data: str) -> int:
        """Estimate size of JSON string data."""
        return CacheSize.estimate_json_size(data).bytes
    
    @staticmethod
    def estimate_object_size(obj: Any) -> int:
        """Estimate size of Python object."""
        return CacheSize.estimate_object_size(obj).bytes
    
    @staticmethod
    def estimate_serialized_size(obj: Any, serializer_overhead: float = 1.2) -> int:
        """Estimate size after serialization with overhead factor."""
        base_size = CacheSize.estimate_object_size(obj).bytes
        return int(base_size * serializer_overhead)


# Factory function for dependency injection
def create_size_validator(
    max_size_bytes: Optional[int] = None,
    warn_size_bytes: Optional[int] = None,
    allow_zero_size: bool = True,
    enable_compression_recommendations: bool = True
) -> SizeValidator:
    """Create cache size validator with configuration.
    
    Args:
        max_size_bytes: Maximum allowed size in bytes
        warn_size_bytes: Size threshold for warnings
        allow_zero_size: Whether to allow zero-size entries
        enable_compression_recommendations: Whether to suggest compression
        
    Returns:
        Configured cache size validator
    """
    return SizeValidator(
        max_size_bytes=max_size_bytes,
        warn_size_bytes=warn_size_bytes,
        allow_zero_size=allow_zero_size,
        enable_compression_recommendations=enable_compression_recommendations
    )