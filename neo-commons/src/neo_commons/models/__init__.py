"""
Neo Commons Models Package

This package contains reusable Pydantic models for FastAPI applications
using the neo-commons library.

Components:
- Base: Common schemas, mixins, and base models
- Pagination: Pagination helpers and responses
"""

from .base import (
    BaseSchema,
    TimestampMixin,
    UUIDMixin,
    SoftDeleteMixin,
    AuditMixin,
    StatusEnum,
    SortOrder,
    PaginationParams as BasePaginationParams,
    PaginatedResponse as BasePaginatedResponse,
    APIResponse,
    HealthStatus,
    ServiceHealth,
    HealthCheckResponse
)

from .pagination import (
    PaginationMetadata,
    PaginatedResponse,
    PaginationParams,
    CursorPaginationParams,
    CursorPaginatedResponse
)

# Aliases for common patterns
BaseModel = BaseSchema

# Create properly ordered mixin classes
class TimestampedModel(TimestampMixin, BaseSchema):
    """BaseSchema with timestamp mixin."""
    pass

class TenantModel(UUIDMixin, TimestampMixin, BaseSchema):
    """BaseSchema with UUID and timestamp mixins."""
    pass

__all__ = [
    # Base schemas and mixins
    "BaseSchema",
    "TimestampMixin", 
    "UUIDMixin",
    "SoftDeleteMixin",
    "AuditMixin",
    
    # Enums
    "StatusEnum",
    "SortOrder",
    "HealthStatus",
    
    # Base pagination (simplified)
    "BasePaginationParams",
    "BasePaginatedResponse",
    
    # API responses
    "APIResponse",
    
    # Health check models
    "ServiceHealth",
    "HealthCheckResponse",
    
    # Enhanced pagination models
    "PaginationMetadata",
    "PaginatedResponse", 
    "PaginationParams",
    "CursorPaginationParams",
    "CursorPaginatedResponse",
    
    # Aliases
    "BaseModel",
    "TimestampedModel",
    "TenantModel"
]