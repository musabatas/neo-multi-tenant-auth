"""
Base models for API requests and responses.
"""
import os
from typing import Optional, Any, Dict, List, TypeVar, Generic
from datetime import datetime, timezone
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator
from enum import Enum


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
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
    """Mixin for models with timestamps."""
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
    """Mixin for models with audit fields."""
    created_by: Optional[UUID] = Field(None, description="User who created the record")
    updated_by: Optional[UUID] = Field(None, description="User who last updated the record")


class StatusEnum(str, Enum):
    """Common status values."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class SortOrder(str, Enum):
    """Sort order for queries."""
    ASC = "asc"
    DESC = "desc"


T = TypeVar('T')


class PaginationParams(BaseSchema):
    """Pagination parameters for list endpoints."""
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


class PaginatedResponse(BaseSchema, Generic[T]):
    """Paginated response wrapper."""
    items: List[T] = Field(description="List of items")
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    total_pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Has next page")
    has_previous: bool = Field(description="Has previous page")
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int
    ) -> "PaginatedResponse[T]":
        """Create a paginated response."""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )


class APIResponse(BaseSchema, Generic[T]):
    """Standard API response wrapper."""
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
        meta: Optional[Dict[str, Any]] = None,
        include_auto_meta: bool = True
    ) -> "APIResponse[T]":
        """Create a success response."""
        final_meta = meta or {}
        
        # Add automatic metadata collection if enabled
        if include_auto_meta:
            auto_meta = cls._collect_request_metadata()
            if auto_meta:
                final_meta.update(auto_meta)
        
        return cls(
            success=True,
            data=data,
            message=message,
            meta=final_meta if final_meta else None
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
    
    @classmethod
    def _collect_request_metadata(cls) -> Dict[str, Any]:
        """Collect metadata using request context or fallback to basic info."""
        try:
            # Try to get metadata from request context middleware
            from neo_commons.middleware.request_context import RequestContext
            return RequestContext.get_metadata()
        except ImportError:
            # Fallback to basic environment metadata
            return {
                "timestamp": utc_now().isoformat(),
                "environment": os.getenv("ENVIRONMENT", "development")
            }
        except Exception:
            # Never fail the response due to metadata collection issues
            return {}


class HealthStatus(str, Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceHealth(BaseSchema):
    """Service health information."""
    name: str = Field(description="Service name")
    status: HealthStatus = Field(description="Service status")
    latency_ms: Optional[float] = Field(None, description="Response latency in milliseconds")
    error: Optional[str] = Field(None, description="Error message if unhealthy")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class HealthCheckResponse(BaseSchema):
    """Health check response."""
    status: HealthStatus = Field(description="Overall health status")
    version: str = Field(description="Application version", default="1.0.0")
    environment: str = Field(description="Environment name", default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    timestamp: datetime = Field(default_factory=utc_now, description="Check timestamp")
    services: Dict[str, ServiceHealth] = Field(description="Individual service health")
    
    @property
    def is_healthy(self) -> bool:
        """Check if all services are healthy."""
        return self.status == HealthStatus.HEALTHY