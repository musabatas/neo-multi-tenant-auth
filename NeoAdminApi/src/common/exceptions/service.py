"""
Service and infrastructure-related exceptions.
"""
from typing import Optional

from .base import NeoAdminException


class DatabaseError(NeoAdminException):
    """Raised when database operation fails."""
    
    def __init__(
        self,
        message: str = "Database operation failed",
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, status_code=500, **kwargs)
        if operation:
            self.details["operation"] = operation


class CacheError(NeoAdminException):
    """Raised when cache operation fails."""
    
    def __init__(
        self,
        message: str = "Cache operation failed",
        operation: Optional[str] = None,
        key: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, status_code=500, **kwargs)
        if operation:
            self.details["operation"] = operation
        if key:
            self.details["key"] = key


class ExternalServiceError(NeoAdminException):
    """Raised when external service call fails."""
    
    def __init__(
        self,
        message: str = "External service error",
        service: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, status_code=502, **kwargs)
        if service:
            self.details["service"] = service


class ServiceUnavailableError(NeoAdminException):
    """Raised when a service is temporarily unavailable."""
    
    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        service: Optional[str] = None,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, status_code=503, **kwargs)
        if service:
            self.details["service"] = service
        if retry_after:
            self.details["retry_after"] = retry_after