"""
Common exceptions module.

MIGRATED TO NEO-COMMONS: Now using neo-commons exception hierarchy.
Import compatibility maintained - all existing imports continue to work.
"""

# NEO-COMMONS IMPORT: Use neo-commons exceptions as base
from neo_commons.exceptions import (
    # Base and HTTP exceptions
    NeoCommonsException as NeoAdminException,  # Alias for backward compatibility
    ValidationError,
    NotFoundError,
    ConflictError,
    UnauthorizedError,
    ForbiddenError,
    BadRequestError,
    RateLimitError,
    ExternalServiceError,
    # Domain-specific exceptions
    TenantError,
    TenantProvisioningError,
    QuotaExceededError,
    MigrationError,
    ConfigurationError,
    # Service and infrastructure exceptions
    DatabaseError,
    CacheError,
    ServiceUnavailableError,
    # Aliases for authentication/authorization
    AuthenticationError,
    AuthorizationError,
)

# BACKWARD COMPATIBILITY: Re-export legacy local exceptions if they have specific extensions
# Import remaining local exceptions only if they have NeoAdminApi-specific functionality
try:
    from .domain import *  # Import any remaining domain-specific extensions
except ImportError:
    pass  # No additional domain exceptions

try:
    from .service import *  # Import any remaining service-specific extensions
except ImportError:
    pass  # No additional service exceptions

__all__ = [
    # Base exceptions from neo-commons
    "NeoAdminException",
    "ValidationError",
    "NotFoundError", 
    "ConflictError",
    "UnauthorizedError",
    "ForbiddenError",
    "BadRequestError",
    "RateLimitError",
    "ExternalServiceError",
    # Domain exceptions from neo-commons
    "TenantError",
    "TenantProvisioningError",
    "QuotaExceededError",
    "MigrationError",
    "ConfigurationError",
    # Service exceptions from neo-commons
    "DatabaseError",
    "CacheError",
    "ServiceUnavailableError",
    # Aliases for convenience
    "AuthenticationError",
    "AuthorizationError",
]