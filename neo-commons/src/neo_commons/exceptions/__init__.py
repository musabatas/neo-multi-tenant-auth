"""
Common exceptions module for NeoMultiTenant services.
Re-exports all exceptions for backward compatibility.
"""

# Base and HTTP exceptions
from .base import (
    NeoCommonsException,
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

# Aliases for common patterns
AuthenticationError = UnauthorizedError
AuthorizationError = ForbiddenError

__all__ = [
    # Base
    "NeoCommonsException",
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
    # Aliases
    "AuthenticationError",
    "AuthorizationError",
]