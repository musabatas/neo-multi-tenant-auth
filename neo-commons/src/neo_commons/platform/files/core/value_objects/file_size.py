"""File size value object.

ONLY file size - represents validated file size with formatting utilities,
comparison operations, and human-readable display.

Following maximum separation architecture - one file = one purpose.
"""

import math
from dataclasses import dataclass
from typing import Union

@dataclass(frozen=True)
class FileSize:
    """File size value object.
    
    Represents a file size in bytes with validation, formatting utilities,
    and comparison operations. Provides human-readable formatting and
    supports various size unit conversions.
    
    Features:
    - Validates non-negative size values
    - Human-readable formatting (KB, MB, GB, etc.)
    - Size comparison operations
    - Unit conversion utilities
    - Memory-efficient storage
    """
    
    value: int  # Size in bytes
    
    # Size unit constants
    BYTE = 1
    KILOBYTE = 1024
    MEGABYTE = 1024 ** 2
    GIGABYTE = 1024 ** 3
    TERABYTE = 1024 ** 4
    PETABYTE = 1024 ** 5
    
    # Unit names for formatting
    UNIT_NAMES = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    
    def __post_init__(self):
        """Validate file size value."""
        if not isinstance(self.value, int):
            raise ValueError(f"FileSize must be an integer, got {type(self.value).__name__}")
        
        if self.value < 0:
            raise ValueError(f"File size cannot be negative: {self.value}")
        
        # Check for reasonable maximum (1 PB = 1024^5 bytes)
        if self.value > self.PETABYTE:
            raise ValueError(f"File size too large: {self.value} bytes > 1 PB")
    
    @classmethod
    def zero(cls) -> 'FileSize':
        """Create a zero-size file size."""
        return cls(0)
    
    @classmethod
    def from_bytes(cls, bytes_value: int) -> 'FileSize':
        """Create FileSize from bytes value."""
        return cls(bytes_value)
    
    @classmethod
    def from_kilobytes(cls, kb_value: Union[int, float]) -> 'FileSize':
        """Create FileSize from kilobytes."""
        return cls(int(kb_value * cls.KILOBYTE))
    
    @classmethod
    def from_megabytes(cls, mb_value: Union[int, float]) -> 'FileSize':
        """Create FileSize from megabytes."""
        return cls(int(mb_value * cls.MEGABYTE))
    
    @classmethod
    def from_gigabytes(cls, gb_value: Union[int, float]) -> 'FileSize':
        """Create FileSize from gigabytes."""
        return cls(int(gb_value * cls.GIGABYTE))
    
    @classmethod
    def from_human_readable(cls, size_str: str) -> 'FileSize':
        """Create FileSize from human-readable string (e.g., '10 MB', '1.5GB')."""
        size_str = size_str.strip().upper()
        
        # Extract number and unit
        import re
        match = re.match(r'^(\d+(?:\.\d+)?)\s*([KMGT]?B?)$', size_str)
        if not match:
            raise ValueError(f"Invalid size format: {size_str}")
        
        number_str, unit = match.groups()
        number = float(number_str)
        
        # Convert based on unit
        unit_multipliers = {
            'B': cls.BYTE,
            'KB': cls.KILOBYTE,
            'MB': cls.MEGABYTE, 
            'GB': cls.GIGABYTE,
            'TB': cls.TERABYTE,
            'PB': cls.PETABYTE,
        }
        
        multiplier = unit_multipliers.get(unit, cls.BYTE)
        return cls(int(number * multiplier))
    
    def to_bytes(self) -> int:
        """Get size in bytes."""
        return self.value
    
    def to_kilobytes(self) -> float:
        """Get size in kilobytes."""
        return self.value / self.KILOBYTE
    
    def to_megabytes(self) -> float:
        """Get size in megabytes.""" 
        return self.value / self.MEGABYTE
    
    def to_gigabytes(self) -> float:
        """Get size in gigabytes."""
        return self.value / self.GIGABYTE
    
    def to_terabytes(self) -> float:
        """Get size in terabytes."""
        return self.value / self.TERABYTE
    
    def format_human_readable(self, precision: int = 2) -> str:
        """Format size in human-readable form with appropriate units."""
        if self.value == 0:
            return "0 B"
        
        # Find appropriate unit
        unit_index = min(
            int(math.log(self.value) / math.log(1024)),
            len(self.UNIT_NAMES) - 1
        )
        
        unit_size = 1024 ** unit_index
        size_in_unit = self.value / unit_size
        unit_name = self.UNIT_NAMES[unit_index]
        
        # Format with appropriate precision
        if size_in_unit == int(size_in_unit):
            return f"{int(size_in_unit)} {unit_name}"
        else:
            return f"{size_in_unit:.{precision}f} {unit_name}"
    
    def format_bytes_with_separators(self) -> str:
        """Format bytes with thousands separators (e.g., '1,234,567 bytes')."""
        return f"{self.value:,} bytes"
    
    def is_zero(self) -> bool:
        """Check if size is zero."""
        return self.value == 0
    
    def is_empty(self) -> bool:
        """Alias for is_zero() for semantic clarity."""
        return self.is_zero()
    
    def exceeds(self, other: 'FileSize') -> bool:
        """Check if this size exceeds another size."""
        return self.value > other.value
    
    def fits_in(self, other: 'FileSize') -> bool:
        """Check if this size fits within another size limit."""
        return self.value <= other.value
    
    def add(self, other: 'FileSize') -> 'FileSize':
        """Add another file size to this one."""
        return FileSize(self.value + other.value)
    
    def subtract(self, other: 'FileSize') -> 'FileSize':
        """Subtract another file size from this one."""
        result = self.value - other.value
        if result < 0:
            result = 0  # Don't allow negative file sizes
        return FileSize(result)
    
    def multiply(self, factor: Union[int, float]) -> 'FileSize':
        """Multiply file size by a factor."""
        if factor < 0:
            raise ValueError("Size multiplier cannot be negative")
        return FileSize(int(self.value * factor))
    
    def percentage_of(self, total: 'FileSize') -> float:
        """Calculate what percentage this size is of a total size."""
        if total.value == 0:
            return 0.0
        return (self.value / total.value) * 100
    
    # Comparison operators
    def __lt__(self, other: 'FileSize') -> bool:
        """Less than comparison."""
        if not isinstance(other, FileSize):
            return NotImplemented
        return self.value < other.value
    
    def __le__(self, other: 'FileSize') -> bool:
        """Less than or equal comparison."""
        if not isinstance(other, FileSize):
            return NotImplemented
        return self.value <= other.value
    
    def __gt__(self, other: 'FileSize') -> bool:
        """Greater than comparison."""
        if not isinstance(other, FileSize):
            return NotImplemented
        return self.value > other.value
    
    def __ge__(self, other: 'FileSize') -> bool:
        """Greater than or equal comparison."""
        if not isinstance(other, FileSize):
            return NotImplemented
        return self.value >= other.value
    
    # Arithmetic operators
    def __add__(self, other: 'FileSize') -> 'FileSize':
        """Addition operator."""
        if not isinstance(other, FileSize):
            return NotImplemented
        return self.add(other)
    
    def __sub__(self, other: 'FileSize') -> 'FileSize':
        """Subtraction operator."""
        if not isinstance(other, FileSize):
            return NotImplemented
        return self.subtract(other)
    
    def __mul__(self, factor: Union[int, float]) -> 'FileSize':
        """Multiplication operator."""
        if not isinstance(factor, (int, float)):
            return NotImplemented
        return self.multiply(factor)
    
    def __rmul__(self, factor: Union[int, float]) -> 'FileSize':
        """Reverse multiplication operator."""
        return self.__mul__(factor)
    
    def __str__(self) -> str:
        """String representation for display."""
        return self.format_human_readable()
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"FileSize({self.value})"