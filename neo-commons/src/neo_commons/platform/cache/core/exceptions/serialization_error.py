"""Serialization error exception.

ONLY serialization errors - exception for cache value serialization failures
with detailed error context and recovery suggestions.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Any, Optional, Dict


class SerializationError(Exception):
    """Cache serialization error.
    
    Raised when cache value cannot be serialized to bytes.
    Provides detailed error context and recovery suggestions.
    """
    
    def __init__(
        self,
        message: str,
        value: Any = None,
        serializer_type: Optional[str] = None,
        original_error: Optional[Exception] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize serialization error.
        
        Args:
            message: Error description
            value: Value that failed to serialize (if safe to include)
            serializer_type: Type of serializer that failed
            original_error: Original underlying exception
            metadata: Additional error context
        """
        super().__init__(message)
        self.value = value
        self.serializer_type = serializer_type
        self.original_error = original_error
        self.metadata = metadata or {}
    
    def get_error_code(self) -> str:
        """Get structured error code."""
        return "CACHE_SERIALIZATION_ERROR"
    
    def get_error_details(self) -> Dict[str, Any]:
        """Get detailed error information."""
        details = {
            "error_code": self.get_error_code(),
            "message": str(self),
            "serializer_type": self.serializer_type,
            "metadata": self.metadata
        }
        
        if self.original_error:
            details["original_error"] = {
                "type": type(self.original_error).__name__,
                "message": str(self.original_error)
            }
        
        if self.value is not None:
            try:
                details["value_type"] = type(self.value).__name__
                details["value_repr"] = repr(self.value)[:100]  # Truncate for safety
            except Exception:
                details["value_type"] = "unknown"
                details["value_repr"] = "unavailable"
        
        return details
    
    def is_recoverable(self) -> bool:
        """Check if error might be recoverable with different serializer."""
        # Some serialization errors might be recoverable by trying different serializer
        if self.original_error:
            # Type errors often indicate wrong serializer choice
            if isinstance(self.original_error, (TypeError, AttributeError)):
                return True
            # Import errors might indicate missing dependencies
            if isinstance(self.original_error, ImportError):
                return False
        return False
    
    def get_recovery_suggestions(self) -> list[str]:
        """Get recovery suggestions based on error context."""
        suggestions = []
        
        if self.is_recoverable():
            suggestions.append("Try using a different serializer (e.g., pickle instead of JSON)")
        
        if self.serializer_type == "json" and self.original_error:
            if "not JSON serializable" in str(self.original_error):
                suggestions.extend([
                    "Ensure all objects are JSON-serializable",
                    "Use pickle serializer for complex Python objects",
                    "Implement custom JSON encoder for complex types"
                ])
        
        if self.serializer_type == "pickle" and self.original_error:
            if "can't pickle" in str(self.original_error):
                suggestions.extend([
                    "Ensure objects don't contain unpicklable elements (lambdas, local classes)",
                    "Try msgpack serializer for better compatibility",
                    "Convert complex objects to serializable format before caching"
                ])
        
        if not suggestions:
            suggestions.append("Check that the value is serializable with the chosen format")
        
        return suggestions