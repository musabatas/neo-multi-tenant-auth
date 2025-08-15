"""
Base models for API requests and responses.

This module provides common Pydantic model patterns for the NeoMultiTenant platform,
including base schemas, mixins, pagination, and API response wrappers.
"""
from typing import Optional, Any, Dict, List, TypeVar, Generic
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

from neo_commons.utils.datetime import utc_now


class BaseSchema(BaseModel):
    """Base schema with common configuration for all platform models."""
    
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        validate_assignment=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }
    )


class TimestampMixin(BaseSchema):
    """Mixin for models with creation and update timestamps."""
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class UUIDMixin(BaseSchema):
    """Mixin for models with UUID primary key."""
    id: UUID = Field(description="Unique identifier")


class SoftDeleteMixin(BaseSchema):
    """Mixin for models with soft delete using deleted_at timestamp."""
    deleted_at: Optional[datetime] = Field(None, description="Deletion timestamp")
    
    @property
    def is_deleted(self) -> bool:
        """Check if the record is soft deleted."""
        return self.deleted_at is not None


class AuditMixin(TimestampMixin):
    """Mixin for models with full audit trail."""
    created_by: Optional[UUID] = Field(None, description="User who created the record")
    updated_by: Optional[UUID] = Field(None, description="User who last updated the record")


class StatusEnum(str, Enum):
    """Common status values used across the platform."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class SortOrder(str, Enum):
    """Sort order options for queries."""
    ASC = "asc"
    DESC = "desc"


T = TypeVar('T')


class PaginationParams(BaseSchema):
    """Standard pagination parameters for list endpoints."""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: SortOrder = Field(SortOrder.ASC, description="Sort order")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Get limit for database query."""
        return self.page_size


class PaginationMetadata(BaseSchema):
    """Metadata for paginated responses."""
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of items per page")
    total_pages: int = Field(description="Total number of pages")
    total_items: int = Field(description="Total number of items")
    has_next: bool = Field(description="Whether there is a next page")
    has_previous: bool = Field(description="Whether there is a previous page")


class PaginatedResponse(BaseSchema, Generic[T]):
    """Generic paginated response wrapper."""
    items: List[T] = Field(description="List of items for current page")
    pagination: PaginationMetadata = Field(description="Pagination metadata")
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int
    ) -> "PaginatedResponse[T]":
        """Create a paginated response with metadata."""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        
        pagination = PaginationMetadata(
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            total_items=total,
            has_next=page < total_pages,
            has_previous=page > 1
        )
        
        return cls(items=items, pagination=pagination)


class APIResponse(BaseSchema, Generic[T]):
    """Standard API response wrapper for all platform services."""
    success: bool = Field(description="Operation success flag")
    data: Optional[T] = Field(None, description="Response data")
    message: Optional[str] = Field(None, description="Response message")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="Error details")
    meta: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @classmethod
    def success_response(
        cls,
        data: Optional[T] = None,
        message: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> "APIResponse[T]":
        """Create a success response."""
        return cls(
            success=True,
            data=data,
            message=message,
            meta=meta
        )
    
    @classmethod
    def error_response(
        cls,
        message: str,
        errors: Optional[List[Dict[str, Any]]] = None,
        data: Optional[T] = None
    ) -> "APIResponse[T]":
        """Create an error response."""
        return cls(
            success=False,
            data=data,
            message=message,
            errors=errors
        )


class HealthStatus(str, Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceHealth(BaseSchema):
    """Individual service health information."""
    name: str = Field(description="Service name")
    status: HealthStatus = Field(description="Service status")
    latency_ms: Optional[float] = Field(None, description="Response latency in milliseconds")
    error: Optional[str] = Field(None, description="Error message if unhealthy")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class HealthCheckResponse(BaseSchema):
    """Comprehensive health check response."""
    status: HealthStatus = Field(description="Overall health status")
    version: str = Field(description="Application version")
    environment: str = Field(description="Environment name")
    timestamp: datetime = Field(default_factory=utc_now, description="Check timestamp")
    services: Dict[str, ServiceHealth] = Field(description="Individual service health")
    
    @property
    def is_healthy(self) -> bool:
        """Check if all services are healthy."""
        return self.status == HealthStatus.HEALTHY