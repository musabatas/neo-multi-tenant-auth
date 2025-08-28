"""Cache size value object.

ONLY size constraints - size tracking for memory management with
automatic conversion and validation.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CacheSize:
    """Cache size value object.
    
    Size tracking for memory management with automatic conversion
    and validation for optimal cache behavior.
    
    Features:
    - Byte-level precision
    - Automatic unit conversion  
    - Size constraint validation
    - Memory usage calculations
    - Comparison operations
    """
    
    bytes: int
    
    # Size constants (in bytes)
    KB = 1024
    MB = 1024 * 1024
    GB = 1024 * 1024 * 1024
    
    # Size limits
    MIN_SIZE = 0
    MAX_SIZE = 1 * GB  # 1GB per entry limit
    
    def __post_init__(self):
        """Validate cache size."""
        if self.bytes < self.MIN_SIZE:
            raise ValueError(f"Cache size cannot be negative: {self.bytes}")
        
        if self.bytes > self.MAX_SIZE:
            raise ValueError(f"Cache size exceeds maximum: {self.bytes} > {self.MAX_SIZE}")
    
    @classmethod
    def zero(cls) -> "CacheSize":
        """Create zero-size entry."""
        return cls(0)
    
    @classmethod
    def from_kb(cls, kilobytes: float) -> "CacheSize":
        """Create size from kilobytes."""
        if kilobytes < 0:
            raise ValueError("Kilobytes cannot be negative")
        return cls(int(kilobytes * cls.KB))
    
    @classmethod
    def from_mb(cls, megabytes: float) -> "CacheSize":
        """Create size from megabytes."""
        if megabytes < 0:
            raise ValueError("Megabytes cannot be negative")
        return cls(int(megabytes * cls.MB))
    
    @classmethod
    def from_string(cls, size_str: str) -> "CacheSize":
        """Create size from string representation (e.g., '1KB', '5MB')."""
        size_str = size_str.strip().upper()
        
        if size_str.endswith('B'):
            return cls(int(size_str[:-1]))
        elif size_str.endswith('KB'):
            return cls.from_kb(float(size_str[:-2]))
        elif size_str.endswith('MB'):
            return cls.from_mb(float(size_str[:-2]))
        elif size_str.endswith('GB'):
            gb_value = float(size_str[:-2])
            return cls(int(gb_value * cls.GB))
        else:
            # Assume bytes if no unit
            return cls(int(size_str))
    
    @classmethod
    def estimate_json_size(cls, data: str) -> "CacheSize":
        """Estimate size of JSON string data."""
        # Simple estimation: UTF-8 encoding
        return cls(len(data.encode('utf-8')))
    
    @classmethod
    def estimate_object_size(cls, obj) -> "CacheSize":
        """Rough estimation of Python object size."""
        import sys
        return cls(sys.getsizeof(obj))
    
    def to_kb(self) -> float:
        """Convert to kilobytes."""
        return self.bytes / self.KB
    
    def to_mb(self) -> float:
        """Convert to megabytes."""
        return self.bytes / self.MB
    
    def to_gb(self) -> float:
        """Convert to gigabytes."""
        return self.bytes / self.GB
    
    def is_zero(self) -> bool:
        """Check if size is zero."""
        return self.bytes == 0
    
    def is_small(self, threshold_kb: float = 1.0) -> bool:
        """Check if size is smaller than threshold."""
        return self.to_kb() < threshold_kb
    
    def is_large(self, threshold_mb: float = 1.0) -> bool:
        """Check if size is larger than threshold."""
        return self.to_mb() > threshold_mb
    
    def add(self, other: "CacheSize") -> "CacheSize":
        """Add another cache size."""
        return CacheSize(self.bytes + other.bytes)
    
    def subtract(self, other: "CacheSize") -> "CacheSize":
        """Subtract another cache size."""
        result = self.bytes - other.bytes
        return CacheSize(max(0, result))  # Don't go below zero
    
    def percentage_of(self, total: "CacheSize") -> float:
        """Calculate percentage of total size."""
        if total.bytes == 0:
            return 0.0
        return (self.bytes / total.bytes) * 100.0
    
    def human_readable(self) -> str:
        """Human-readable size representation."""
        if self.bytes < self.KB:
            return f"{self.bytes}B"
        elif self.bytes < self.MB:
            return f"{self.to_kb():.1f}KB"
        elif self.bytes < self.GB:
            return f"{self.to_mb():.1f}MB"
        else:
            return f"{self.to_gb():.2f}GB"
    
    def __add__(self, other: "CacheSize") -> "CacheSize":
        """Add operator support."""
        return self.add(other)
    
    def __sub__(self, other: "CacheSize") -> "CacheSize":
        """Subtract operator support."""
        return self.subtract(other)
    
    def __lt__(self, other: "CacheSize") -> bool:
        """Less than comparison."""
        return self.bytes < other.bytes
    
    def __le__(self, other: "CacheSize") -> bool:
        """Less than or equal comparison."""
        return self.bytes <= other.bytes
    
    def __gt__(self, other: "CacheSize") -> bool:
        """Greater than comparison."""
        return self.bytes > other.bytes
    
    def __ge__(self, other: "CacheSize") -> bool:
        """Greater than or equal comparison."""
        return self.bytes >= other.bytes
    
    def __str__(self) -> str:
        """String representation."""
        return self.human_readable()