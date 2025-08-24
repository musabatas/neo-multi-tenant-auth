"""Base exceptions for neo-commons.

This module defines the base exception hierarchy for the neo-commons library.
All exceptions inherit from NeoCommonsError and include error codes, details,
and HTTP status code mappings for API responses.
"""

from typing import Any, Dict, Optional


class NeoCommonsError(Exception):
    """Base exception for all neo-commons errors.
    
    All exceptions in the neo-commons library inherit from this base class
    and include structured error information for better debugging and API responses.
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        *args,
        **kwargs
    ):
        super().__init__(message, *args, **kwargs)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}


def get_http_status_code(exception: Exception) -> int:
    """Get HTTP status code for exception using configurable mapping.
    
    Args:
        exception: The exception instance
        
    Returns:
        HTTP status code
    """
    from .http_mapping import get_http_status_code as get_configurable_status_code
    return get_configurable_status_code(exception)


def create_error_response(exception: NeoCommonsError) -> Dict[str, Any]:
    """Create standardized error response from exception.
    
    Args:
        exception: The neo-commons exception
        
    Returns:
        Error response dictionary
    """
    return {
        "error": {
            "code": exception.error_code,
            "message": exception.message,
            "details": exception.details,
            "type": exception.__class__.__name__,
        }
    }