"""
Domain-specific exceptions for business logic errors.

Service wrapper that extends neo-commons domain exceptions with
NeoAdminApi-specific functionality and backward compatibility.
"""
from typing import Optional
from uuid import UUID

# Import neo-commons domain exceptions
from neo_commons.exceptions.domain import (
    TenantError as BaseTenantError,
    TenantProvisioningError as BaseTenantProvisioningError,
    QuotaExceededError as BaseQuotaExceededError,
    MigrationError as BaseMigrationError,
    ConfigurationError as BaseConfigurationError,
)

from .base import NeoAdminException


class TenantError(BaseTenantError, NeoAdminException):
    """NeoAdminApi tenant exception with service-specific functionality."""
    pass


class TenantProvisioningError(BaseTenantProvisioningError, NeoAdminException):
    """NeoAdminApi tenant provisioning exception with service-specific functionality."""
    pass


class QuotaExceededError(BaseQuotaExceededError, NeoAdminException):
    """NeoAdminApi quota exception with service-specific functionality."""
    pass


class MigrationError(BaseMigrationError, NeoAdminException):
    """NeoAdminApi migration exception with service-specific functionality."""
    pass


class ConfigurationError(BaseConfigurationError, NeoAdminException):
    """NeoAdminApi configuration exception with service-specific functionality."""
    pass