"""
Base exception classes for the NeoAdminApi.

Service wrapper that imports from neo-commons and provides the service-specific
base exception class name for backward compatibility.
"""

# Import all exceptions from neo-commons
from neo_commons.exceptions.base import (
    NeoException,
    ValidationError as BaseValidationError,
    NotFoundError as BaseNotFoundError,
    ConflictError as BaseConflictError,
    UnauthorizedError as BaseUnauthorizedError,
    ForbiddenError as BaseForbiddenError,
    BadRequestError as BaseBadRequestError,
    RateLimitError as BaseRateLimitError,
    ExternalServiceError as BaseExternalServiceError,
)


# Service-specific base exception class for backward compatibility
class NeoAdminException(NeoException):
    """Base exception for all NeoAdminApi exceptions."""
    pass


# Re-export all specific exceptions inheriting from NeoAdminException for consistency
class ValidationError(BaseValidationError, NeoAdminException):
    """Raised when validation fails."""
    pass


class NotFoundError(BaseNotFoundError, NeoAdminException):
    """Raised when a resource is not found."""
    pass


class ConflictError(BaseConflictError, NeoAdminException):
    """Raised when there's a conflict with existing data."""
    pass


class UnauthorizedError(BaseUnauthorizedError, NeoAdminException):
    """Raised when authentication is required but not provided."""
    pass


class ForbiddenError(BaseForbiddenError, NeoAdminException):
    """Raised when user doesn't have permission."""
    pass


class BadRequestError(BaseBadRequestError, NeoAdminException):
    """Raised when request is malformed or invalid."""
    pass


class RateLimitError(BaseRateLimitError, NeoAdminException):
    """Raised when rate limit is exceeded."""
    pass


class ExternalServiceError(BaseExternalServiceError, NeoAdminException):
    """Raised when an external service call fails."""
    pass






