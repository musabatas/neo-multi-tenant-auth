"""Deserialization error exception.

ONLY deserialization errors - exception for cache value deserialization failures
with detailed error context and data recovery suggestions.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Any, Optional, Dict


class DeserializationError(Exception):
    """Cache deserialization error.
    
    Raised when cached bytes cannot be deserialized back to Python objects.
    Provides detailed error context and recovery suggestions.
    """
    
    def __init__(
        self,
        message: str,
        data: Optional[bytes] = None,
        serializer_type: Optional[str] = None,
        original_error: Optional[Exception] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize deserialization error.
        
        Args:
            message: Error description
            data: Serialized data that failed to deserialize (if safe to include)
            serializer_type: Type of serializer that failed
            original_error: Original underlying exception
            metadata: Additional error context
        """
        super().__init__(message)
        self.data = data
        self.serializer_type = serializer_type
        self.original_error = original_error
        self.metadata = metadata or {}
    
    def get_error_code(self) -> str:
        """Get structured error code."""
        return "CACHE_DESERIALIZATION_ERROR"
    
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
        
        if self.data is not None:
            try:
                details["data_size"] = len(self.data)
                details["data_preview"] = repr(self.data[:50])  # First 50 bytes for debugging
            except Exception:
                details["data_size"] = "unknown"
                details["data_preview"] = "unavailable"
        
        return details
    
    def is_data_corrupted(self) -> bool:
        """Check if data appears corrupted based on error patterns."""
        if self.original_error:
            error_msg = str(self.original_error).lower()
            corruption_indicators = [
                "invalid", "corrupt", "truncated", "malformed",
                "unexpected end", "bad data", "format error"
            ]
            return any(indicator in error_msg for indicator in corruption_indicators)
        return False
    
    def is_version_mismatch(self) -> bool:
        """Check if error might be due to serializer version mismatch."""
        if self.original_error:
            error_msg = str(self.original_error).lower()
            version_indicators = [
                "protocol", "version", "unsupported", "format",
                "incompatible", "unknown opcode"
            ]
            return any(indicator in error_msg for indicator in version_indicators)
        return False
    
    def get_recovery_suggestions(self) -> list[str]:
        """Get recovery suggestions based on error context."""
        suggestions = []
        
        if self.is_data_corrupted():
            suggestions.extend([
                "Data may be corrupted - consider cache invalidation",
                "Check cache storage integrity",
                "Verify network transmission if using distributed cache"
            ])
        
        if self.is_version_mismatch():
            suggestions.extend([
                "Serializer version mismatch detected",
                "Update serializer to compatible version",
                "Consider cache migration if format changed",
                "Check serializer configuration compatibility"
            ])
        
        if self.serializer_type == "json" and self.original_error:
            if "json" in str(self.original_error).lower():
                suggestions.extend([
                    "Invalid JSON format detected",
                    "Check for character encoding issues",
                    "Verify JSON structure integrity"
                ])
        
        if self.serializer_type == "pickle" and self.original_error:
            if "pickle" in str(self.original_error).lower():
                suggestions.extend([
                    "Pickle format error - check protocol version",
                    "Ensure all required modules are available",
                    "Verify pickle data integrity"
                ])
        
        if self.serializer_type == "msgpack" and self.original_error:
            if "msgpack" in str(self.original_error).lower():
                suggestions.extend([
                    "MessagePack format error detected",
                    "Check msgpack library version compatibility",
                    "Verify binary data integrity"
                ])
        
        if not suggestions:
            suggestions.extend([
                "Check serialized data format and integrity",
                "Verify serializer configuration matches original",
                "Consider trying fallback serializer if available"
            ])
        
        return suggestions
    
    def should_retry_with_fallback(self) -> bool:
        """Check if error suggests trying with fallback serializer."""
        # Don't retry if data is clearly corrupted
        if self.is_data_corrupted():
            return False
        
        # Retry for version mismatches or format issues
        if self.is_version_mismatch():
            return True
        
        # Retry for format-specific errors that might work with different serializer
        if self.original_error:
            error_msg = str(self.original_error).lower()
            fallback_indicators = [
                "unsupported", "unknown format", "invalid format",
                "not recognized", "cannot decode"
            ]
            return any(indicator in error_msg for indicator in fallback_indicators)
        
        return False