"""
Common exceptions module for NeoMultiTenant services.
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
    ExternalServiceError,
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
    "ExternalServiceError",
    # Domain
    "TenantError",
    "TenantProvisioningError",
    "QuotaExceededError",
    "MigrationError",
    "ConfigurationError",
    # Service
    "DatabaseError",
    "CacheError",
    "ServiceUnavailableError",
]