"""
Common model patterns for the NeoMultiTenant platform.

This module provides base Pydantic models, mixins, and response patterns
used across all services in the platform.
"""

from .base import (
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
    APIResponse,
    HealthStatus,
    ServiceHealth,
    HealthCheckResponse,
)

from .pagination import (
    PaginationHelper,
    FilterBuilder,
    ListQueryBuilder,
)

from .protocols import (
    BaseModelProtocol,
    APIResponseProtocol,
    PaginationProtocol,
    PaginatedResponseProtocol,
    FilterableModelProtocol
)

__all__ = [
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
    "APIResponse",
    "HealthStatus",
    "ServiceHealth",
    "HealthCheckResponse",
    # Pagination utilities
    "PaginationHelper",
    "FilterBuilder", 
    "ListQueryBuilder",
    
    # Protocol interfaces
    "BaseModelProtocol",
    "APIResponseProtocol",
    "PaginationProtocol",
    "PaginatedResponseProtocol",
    "FilterableModelProtocol"
]