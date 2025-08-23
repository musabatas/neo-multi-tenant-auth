"""
Exception handling for the NeoMultiTenant platform.

This module provides a consistent exception hierarchy for all services
in the platform, enabling standardized error handling and response formats.
"""

from .base import (
    NeoException,
    ValidationError,
    NotFoundError,
    ConflictError,
    UnauthorizedError,
    ForbiddenError,
    BadRequestError,
    RateLimitError,
    ExternalServiceError,
)

from .domain import (
    TenantError,
    TenantProvisioningError,
    QuotaExceededError,
    MigrationError,
    ConfigurationError,
)

from .service import (
    DatabaseError,
    CacheError,
    ServiceUnavailableError,
)

from .protocols import (
    ExceptionProtocol,
    DomainExceptionProtocol,
    ServiceExceptionProtocol,
    ExceptionHandlerProtocol,
    ValidationExceptionProtocol,
    ErrorReporterProtocol
)

__all__ = [
    # Base exceptions
    "NeoException",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "UnauthorizedError",
    "ForbiddenError",
    "BadRequestError",
    "RateLimitError",
    "ExternalServiceError",
    # Domain exceptions
    "TenantError",
    "TenantProvisioningError",
    "QuotaExceededError",
    "MigrationError",
    "ConfigurationError",
    # Service exceptions
    "DatabaseError",
    "CacheError",
    "ServiceUnavailableError",
    
    # Protocol interfaces
    "ExceptionProtocol",
    "DomainExceptionProtocol",
    "ServiceExceptionProtocol",
    "ExceptionHandlerProtocol",
    "ValidationExceptionProtocol",
    "ErrorReporterProtocol"
]