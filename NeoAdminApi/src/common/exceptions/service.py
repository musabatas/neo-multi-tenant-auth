"""
Service and infrastructure-related exceptions.

MIGRATED TO NEO-COMMONS: Now using neo-commons service exceptions.
Import compatibility maintained - all existing imports continue to work.
"""

# NEO-COMMONS IMPORT: Use neo-commons service exceptions directly
from neo_commons.exceptions.service import (
    DatabaseError,
    CacheError,
    ServiceUnavailableError,
)

# Import ExternalServiceError from base module since it's in the base module in neo-commons
from neo_commons.exceptions.base import ExternalServiceError

# Re-export for backward compatibility
__all__ = [
    "DatabaseError",
    "CacheError",
    "ExternalServiceError",
    "ServiceUnavailableError",
]