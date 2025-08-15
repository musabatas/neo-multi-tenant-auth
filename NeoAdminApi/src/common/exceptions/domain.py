"""
Domain-specific exceptions for business logic errors.

MIGRATED TO NEO-COMMONS: Now using neo-commons domain exceptions.
Import compatibility maintained - all existing imports continue to work.
"""

# NEO-COMMONS IMPORT: Use neo-commons domain exceptions directly
from neo_commons.exceptions.domain import (
    TenantError,
    TenantProvisioningError,
    QuotaExceededError,
    MigrationError,
    ConfigurationError,
)

# Re-export for backward compatibility
__all__ = [
    "TenantError",
    "TenantProvisioningError", 
    "QuotaExceededError",
    "MigrationError",
    "ConfigurationError",
]