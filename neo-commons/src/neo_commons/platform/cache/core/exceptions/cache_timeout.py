"""Cache timeout exception.

ONLY timeout errors - exception raised when cache operations
exceed time limits.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Optional


class CacheTimeout(TimeoutError):
    """Cache operation timeout error.
    
    Raised when cache operations exceed configured timeout limits:
    - Get operations taking too long
    - Set operations not completing
    - Batch operations timing out
    - Connection timeouts to cache backend
    """
    
    def __init__(
        self, 
        operation: str,
        timeout_seconds: float,
        elapsed_seconds: Optional[float] = None,
        error_code: Optional[str] = None,
        details: Optional[dict] = None
    ):
        """Initialize cache timeout error.
        
        Args:
            operation: The cache operation that timed out
            timeout_seconds: The configured timeout limit
            elapsed_seconds: Actual time elapsed before timeout
            error_code: Optional machine-readable error code
            details: Optional additional error details
        """
        self.operation = operation
        self.timeout_seconds = timeout_seconds
        self.elapsed_seconds = elapsed_seconds
        self.error_code = error_code or "CACHE_TIMEOUT"
        self.details = details or {}
        
        message = f"Cache {operation} operation timed out after {timeout_seconds}s"
        if elapsed_seconds:
            message += f" (elapsed: {elapsed_seconds:.2f}s)"
        
        super().__init__(message)
    
    @classmethod
    def get_operation(
        cls, 
        key: str, 
        timeout_seconds: float,
        elapsed_seconds: Optional[float] = None
    ) -> "CacheTimeout":
        """Create timeout exception for get operation."""
        return cls(
            operation="get",
            timeout_seconds=timeout_seconds,
            elapsed_seconds=elapsed_seconds,
            error_code="CACHE_GET_TIMEOUT",
            details={"key": key}
        )
    
    @classmethod
    def set_operation(
        cls, 
        key: str, 
        timeout_seconds: float,
        elapsed_seconds: Optional[float] = None
    ) -> "CacheTimeout":
        """Create timeout exception for set operation."""
        return cls(
            operation="set",
            timeout_seconds=timeout_seconds,
            elapsed_seconds=elapsed_seconds,
            error_code="CACHE_SET_TIMEOUT",
            details={"key": key}
        )
    
    @classmethod
    def delete_operation(
        cls, 
        key: str, 
        timeout_seconds: float,
        elapsed_seconds: Optional[float] = None
    ) -> "CacheTimeout":
        """Create timeout exception for delete operation."""
        return cls(
            operation="delete",
            timeout_seconds=timeout_seconds,
            elapsed_seconds=elapsed_seconds,
            error_code="CACHE_DELETE_TIMEOUT",
            details={"key": key}
        )
    
    @classmethod
    def batch_operation(
        cls, 
        operation_type: str,
        key_count: int,
        timeout_seconds: float,
        elapsed_seconds: Optional[float] = None
    ) -> "CacheTimeout":
        """Create timeout exception for batch operation."""
        return cls(
            operation=f"batch_{operation_type}",
            timeout_seconds=timeout_seconds,
            elapsed_seconds=elapsed_seconds,
            error_code="CACHE_BATCH_TIMEOUT",
            details={
                "operation_type": operation_type,
                "key_count": key_count
            }
        )
    
    @classmethod
    def connection_timeout(
        cls, 
        backend: str,
        timeout_seconds: float,
        elapsed_seconds: Optional[float] = None
    ) -> "CacheTimeout":
        """Create timeout exception for connection."""
        return cls(
            operation="connect",
            timeout_seconds=timeout_seconds,
            elapsed_seconds=elapsed_seconds,
            error_code="CACHE_CONNECTION_TIMEOUT",
            details={"backend": backend}
        )
    
    @classmethod
    def invalidation_timeout(
        cls, 
        pattern: str,
        timeout_seconds: float,
        elapsed_seconds: Optional[float] = None
    ) -> "CacheTimeout":
        """Create timeout exception for invalidation operation."""
        return cls(
            operation="invalidation",
            timeout_seconds=timeout_seconds,
            elapsed_seconds=elapsed_seconds,
            error_code="CACHE_INVALIDATION_TIMEOUT",
            details={"pattern": pattern}
        )
    
    def is_severe(self, threshold_multiplier: float = 2.0) -> bool:
        """Check if timeout is severe (much longer than expected)."""
        if self.elapsed_seconds is None:
            return True  # Unknown elapsed time is concerning
        
        return self.elapsed_seconds >= (self.timeout_seconds * threshold_multiplier)
    
    def get_performance_impact(self) -> str:
        """Get performance impact category."""
        if self.elapsed_seconds is None:
            return "unknown"
        
        ratio = self.elapsed_seconds / self.timeout_seconds
        
        if ratio >= 2.0:
            return "severe"
        elif ratio >= 1.5:
            return "high"
        elif ratio >= 1.2:
            return "moderate"
        else:
            return "low"
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary for serialization."""
        return {
            "error_type": "CacheTimeout",
            "error_code": self.error_code,
            "operation": self.operation,
            "timeout_seconds": self.timeout_seconds,
            "elapsed_seconds": self.elapsed_seconds,
            "performance_impact": self.get_performance_impact(),
            "is_severe": self.is_severe(),
            "details": self.details
        }