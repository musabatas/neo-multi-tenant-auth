"""Cache capacity exceeded exception.

ONLY capacity errors - exception raised when cache capacity
limits are exceeded.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Optional


class CacheCapacityExceeded(Exception):
    """Cache capacity exceeded error.
    
    Raised when cache operations would exceed capacity limits:
    - Maximum number of entries reached
    - Memory limit exceeded
    - Namespace capacity limits reached
    - Size limits for individual entries
    """
    
    def __init__(
        self, 
        capacity_type: str,
        current_value: int,
        limit_value: int,
        operation: str,
        error_code: Optional[str] = None,
        details: Optional[dict] = None
    ):
        """Initialize cache capacity exceeded error.
        
        Args:
            capacity_type: Type of capacity exceeded (entries, memory, size)
            current_value: Current capacity usage
            limit_value: Maximum allowed capacity
            operation: Operation that would exceed capacity
            error_code: Optional machine-readable error code
            details: Optional additional error details
        """
        self.capacity_type = capacity_type
        self.current_value = current_value
        self.limit_value = limit_value
        self.operation = operation
        self.error_code = error_code or "CACHE_CAPACITY_EXCEEDED"
        self.details = details or {}
        
        message = (
            f"Cache {capacity_type} capacity exceeded during {operation}: "
            f"{current_value} >= {limit_value}"
        )
        
        super().__init__(message)
    
    @classmethod
    def max_entries(
        cls, 
        current_entries: int,
        max_entries: int,
        namespace: Optional[str] = None
    ) -> "CacheCapacityExceeded":
        """Create exception for maximum entries exceeded."""
        details = {}
        if namespace:
            details["namespace"] = namespace
            
        return cls(
            capacity_type="entries",
            current_value=current_entries,
            limit_value=max_entries,
            operation="set",
            error_code="CACHE_MAX_ENTRIES_EXCEEDED",
            details=details
        )
    
    @classmethod
    def memory_limit(
        cls, 
        current_memory_bytes: int,
        max_memory_bytes: int,
        namespace: Optional[str] = None
    ) -> "CacheCapacityExceeded":
        """Create exception for memory limit exceeded."""
        details = {
            "current_memory_mb": current_memory_bytes / (1024 * 1024),
            "max_memory_mb": max_memory_bytes / (1024 * 1024)
        }
        
        if namespace:
            details["namespace"] = namespace
            
        return cls(
            capacity_type="memory",
            current_value=current_memory_bytes,
            limit_value=max_memory_bytes,
            operation="set",
            error_code="CACHE_MEMORY_LIMIT_EXCEEDED",
            details=details
        )
    
    @classmethod
    def entry_size_limit(
        cls, 
        entry_size_bytes: int,
        max_entry_size_bytes: int,
        key: str
    ) -> "CacheCapacityExceeded":
        """Create exception for entry size limit exceeded."""
        return cls(
            capacity_type="entry_size",
            current_value=entry_size_bytes,
            limit_value=max_entry_size_bytes,
            operation="set",
            error_code="CACHE_ENTRY_SIZE_EXCEEDED",
            details={
                "key": key,
                "entry_size_kb": entry_size_bytes / 1024,
                "max_entry_size_kb": max_entry_size_bytes / 1024
            }
        )
    
    @classmethod
    def namespace_capacity(
        cls, 
        namespace: str,
        current_entries: int,
        max_entries: int
    ) -> "CacheCapacityExceeded":
        """Create exception for namespace capacity exceeded."""
        return cls(
            capacity_type="namespace_entries",
            current_value=current_entries,
            limit_value=max_entries,
            operation="set",
            error_code="CACHE_NAMESPACE_CAPACITY_EXCEEDED",
            details={"namespace": namespace}
        )
    
    @classmethod
    def key_length_limit(
        cls, 
        key: str,
        key_length: int,
        max_key_length: int
    ) -> "CacheCapacityExceeded":
        """Create exception for key length limit exceeded."""
        return cls(
            capacity_type="key_length",
            current_value=key_length,
            limit_value=max_key_length,
            operation="set",
            error_code="CACHE_KEY_LENGTH_EXCEEDED",
            details={"key": key}
        )
    
    def get_utilization_percentage(self) -> float:
        """Get capacity utilization as percentage."""
        if self.limit_value == 0:
            return 100.0
        return (self.current_value / self.limit_value) * 100.0
    
    def get_overflow_amount(self) -> int:
        """Get amount by which capacity was exceeded."""
        return max(0, self.current_value - self.limit_value)
    
    def is_severe_overflow(self, threshold_percentage: float = 20.0) -> bool:
        """Check if overflow is severe (significantly over limit)."""
        if self.limit_value == 0:
            return True
        
        overflow_percentage = (self.get_overflow_amount() / self.limit_value) * 100.0
        return overflow_percentage >= threshold_percentage
    
    def get_capacity_category(self) -> str:
        """Get capacity category for monitoring."""
        utilization = self.get_utilization_percentage()
        
        if utilization >= 150:
            return "severe_overflow"
        elif utilization >= 120:
            return "moderate_overflow"
        elif utilization >= 100:
            return "minor_overflow"
        else:
            return "at_limit"
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary for serialization."""
        return {
            "error_type": "CacheCapacityExceeded",
            "error_code": self.error_code,
            "capacity_type": self.capacity_type,
            "current_value": self.current_value,
            "limit_value": self.limit_value,
            "operation": self.operation,
            "utilization_percentage": self.get_utilization_percentage(),
            "overflow_amount": self.get_overflow_amount(),
            "capacity_category": self.get_capacity_category(),
            "is_severe": self.is_severe_overflow(),
            "details": self.details
        }