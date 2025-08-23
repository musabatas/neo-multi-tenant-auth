"""
Common models and patterns for NeoAdminApi.

Service wrapper that re-exports neo-commons models with any NeoAdminApi-specific extensions.
"""

# Import all models from neo-commons
from neo_commons.models import (
    BaseSchema,
    TimestampMixin,
    UUIDMixin,
    SoftDeleteMixin,
    AuditMixin,
    StatusEnum,
    SortOrder,
    PaginationParams,
    PaginationMetadata,
    PaginatedResponse,
    HealthStatus,
    ServiceHealth,
    HealthCheckResponse,
    # Pagination utilities
    PaginationHelper,
    FilterBuilder,
    ListQueryBuilder,
)

# Import NeoAdminApi-specific extensions
from .base import APIResponse

__all__ = [
    # Base models from neo-commons
    "BaseSchema",
    "TimestampMixin",
    "UUIDMixin",
    "SoftDeleteMixin",
    "AuditMixin",
    "StatusEnum",
    "SortOrder",
    "PaginationParams",
    "PaginationMetadata",
    "PaginatedResponse",
    "HealthStatus",
    "ServiceHealth",
    "HealthCheckResponse",
    # Pagination utilities from neo-commons
    "PaginationHelper",
    "FilterBuilder",
    "ListQueryBuilder",
    # NeoAdminApi-specific extensions
    "APIResponse",
]