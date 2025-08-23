"""
Service and infrastructure-related exceptions.

Service wrapper that extends neo-commons service exceptions with
NeoAdminApi-specific functionality and backward compatibility.
"""
from typing import Optional

# Import neo-commons service exceptions
from neo_commons.exceptions.service import (
    DatabaseError as BaseDatabaseError,
    CacheError as BaseCacheError,
    ServiceUnavailableError as BaseServiceUnavailableError,
)
# Import ExternalServiceError from base exceptions (already exists)
from neo_commons.exceptions import ExternalServiceError

from .base import NeoAdminException


class DatabaseError(BaseDatabaseError, NeoAdminException):
    """NeoAdminApi database exception with service-specific functionality."""
    pass


class CacheError(BaseCacheError, NeoAdminException):
    """NeoAdminApi cache exception with service-specific functionality."""
    pass


class ServiceUnavailableError(BaseServiceUnavailableError, NeoAdminException):
    """NeoAdminApi service unavailable exception with service-specific functionality."""
    pass


# ExternalServiceError is already imported from neo_commons.exceptions and is available
# No need to create a service wrapper as it's already generic enough