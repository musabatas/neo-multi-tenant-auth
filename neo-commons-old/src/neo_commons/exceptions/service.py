"""
Service and infrastructure-related exceptions.

This module provides exceptions for service-level operations like
database access, caching, and service availability.
"""
from typing import Optional

from .base import NeoException


class DatabaseError(NeoException):
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


class CacheError(NeoException):
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


class ServiceUnavailableError(NeoException):
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