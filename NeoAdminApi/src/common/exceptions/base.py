"""
Base exception classes for NeoAdminApi.

MIGRATED TO NEO-COMMONS: Now using neo-commons exception hierarchy with NeoAdminApi-specific extensions.
Import compatibility maintained - all existing imports continue to work.
"""
from typing import Optional, Any, Dict, List

# NEO-COMMONS IMPORT: Use neo-commons exceptions as base
from neo_commons.exceptions.base import (
    NeoCommonsException,
    ValidationError as NeoCommonsValidationError,
    NotFoundError as NeoCommonsNotFoundError,
    ConflictError as NeoCommonsConflictError,
    UnauthorizedError as NeoCommonsUnauthorizedError,
    ForbiddenError as NeoCommonsForbiddenError,
    BadRequestError as NeoCommonsBadRequestError,
    RateLimitError as NeoCommonsRateLimitError,
    ExternalServiceError as NeoCommonsExternalServiceError
)


class NeoAdminException(NeoCommonsException):
    """
    NeoAdminApi base exception extending neo-commons.
    
    Maintains backward compatibility while leveraging neo-commons infrastructure.
    """
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize with NeoAdminApi-specific context."""
        super().__init__(message, code, status_code, details)
        
        # Add NeoAdminApi-specific context to details
        if "service" not in self.details:
            self.details["service"] = "NeoAdminApi"
        if "api_version" not in self.details:
            self.details["api_version"] = "v1"


# BACKWARD COMPATIBILITY: All exception classes maintain exact same interface
class ValidationError(NeoCommonsValidationError):
    """Raised when validation fails. Uses neo-commons implementation."""
    pass


class NotFoundError(NeoCommonsNotFoundError):
    """Raised when a resource is not found. Uses neo-commons implementation."""
    pass


class ConflictError(NeoCommonsConflictError):
    """Raised when there's a conflict with existing data. Uses neo-commons implementation."""
    pass


class UnauthorizedError(NeoCommonsUnauthorizedError):
    """Raised when authentication is required but not provided. Uses neo-commons implementation."""
    pass


class ForbiddenError(NeoCommonsForbiddenError):
    """Raised when user doesn't have permission. Uses neo-commons implementation."""
    pass


class BadRequestError(NeoCommonsBadRequestError):
    """Raised when request is malformed or invalid. Uses neo-commons implementation."""
    pass


class RateLimitError(NeoCommonsRateLimitError):
    """Raised when rate limit is exceeded. Uses neo-commons implementation."""
    pass


class ExternalServiceError(NeoCommonsExternalServiceError):
    """Raised when an external service call fails. Uses neo-commons implementation."""
    pass






