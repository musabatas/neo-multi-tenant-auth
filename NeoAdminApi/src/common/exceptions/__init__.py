"""
Common exceptions module.
Re-exports all exceptions for backward compatibility.
"""

# Base and HTTP exceptions
from .base import (
    NeoAdminException,
    ValidationError,
    NotFoundError,
    ConflictError,
    UnauthorizedError,
    ForbiddenError,
    BadRequestError,
    RateLimitError,
)

# Domain-specific exceptions
from .domain import (
    TenantError,
    TenantProvisioningError,
    QuotaExceededError,
    MigrationError,
    ConfigurationError,
)

# Service and infrastructure exceptions
from .service import (
    DatabaseError,
    CacheError,
    ExternalServiceError,
    ServiceUnavailableError,
)

__all__ = [
    # Base
    "NeoAdminException",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "UnauthorizedError",
    "ForbiddenError",
    "BadRequestError",
    "RateLimitError",
    # Domain
    "TenantError",
    "TenantProvisioningError",
    "QuotaExceededError",
    "MigrationError",
    "ConfigurationError",
    # Service
    "DatabaseError",
    "CacheError",
    "ExternalServiceError",
    "ServiceUnavailableError",
]