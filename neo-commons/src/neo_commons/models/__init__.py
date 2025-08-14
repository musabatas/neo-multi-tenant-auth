"""
Neo Commons Models Package

This package contains reusable Pydantic models for FastAPI applications
in the NeoMultiTenant platform.

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
    "CursorPaginatedResponse"
]