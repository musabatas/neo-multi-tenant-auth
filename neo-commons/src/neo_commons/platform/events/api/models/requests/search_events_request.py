"""
Search events request model.

ONLY handles event search API request validation and transformation.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator

from neo_commons.core.value_objects import TenantId


class SearchEventsRequest(BaseModel):
    """Request model for searching events."""
    
    tenant_id: str = Field(
        ...,
        description="Tenant identifier",
        example="tenant_123"
    )
    
    event_types: Optional[List[str]] = Field(
        None,
        description="Filter by event types",
        example=["user.created", "user.updated"]
    )
    
    event_status: Optional[str] = Field(
        None,
        description="Filter by event status",
        example="completed"
    )
    
    start_date: Optional[datetime] = Field(
        None,
        description="Filter events after this date",
        example="2024-01-01T00:00:00Z"
    )
    
    end_date: Optional[datetime] = Field(
        None,
        description="Filter events before this date", 
        example="2024-12-31T23:59:59Z"
    )
    
    user_id: Optional[str] = Field(
        None,
        description="Filter by user who triggered events",
        example="usr_123456789"
    )
    
    correlation_id: Optional[str] = Field(
        None,
        description="Filter by correlation ID",
        example="trace_123"
    )
    
    payload_filters: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Filter by payload content",
        example={"user.email": "john@example.com"}
    )
    
    sort_by: str = Field(
        default="created_at",
        description="Field to sort results by",
        example="created_at"
    )
    
    sort_order: str = Field(
        default="desc",
        description="Sort order",
        example="desc"
    )
    
    page: int = Field(
        default=1,
        description="Page number for pagination",
        ge=1,
        example=1
    )
    
    page_size: int = Field(
        default=20,
        description="Number of results per page",
        ge=1,
        le=100,
        example=20
    )
    
    include_archived: bool = Field(
        default=False,
        description="Include archived events in results"
    )
    
    @validator('event_types')
    def validate_event_types(cls, v):
        """Validate event types format."""
        if v:
            for event_type in v:
                if not event_type or '.' not in event_type:
                    raise ValueError("Event types must be in format 'domain.action'")
            return list(set(v))  # Remove duplicates
        return v
    
    @validator('event_status')
    def validate_event_status(cls, v):
        """Validate event status."""
        if v:
            valid_statuses = ["pending", "processing", "completed", "failed", "archived"]
            if v not in valid_statuses:
                raise ValueError(f"Event status must be one of: {valid_statuses}")
        return v
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Validate date range."""
        if v and values.get('start_date') and v <= values['start_date']:
            raise ValueError("End date must be after start date")
        return v
    
    @validator('sort_by')
    def validate_sort_by(cls, v):
        """Validate sort field."""
        valid_fields = ["created_at", "updated_at", "event_type", "status"]
        if v not in valid_fields:
            raise ValueError(f"Sort field must be one of: {valid_fields}")
        return v
    
    @validator('sort_order')
    def validate_sort_order(cls, v):
        """Validate sort order."""
        valid_orders = ["asc", "desc"]
        if v not in valid_orders:
            raise ValueError(f"Sort order must be one of: {valid_orders}")
        return v
    
    def to_domain(self) -> Dict[str, Any]:
        """Convert to domain representation."""
        return {
            "tenant_id": TenantId(self.tenant_id),
            "event_types": self.event_types,
            "event_status": self.event_status,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "user_id": self.user_id,
            "correlation_id": self.correlation_id,
            "payload_filters": self.payload_filters or {},
            "sort_by": self.sort_by,
            "sort_order": self.sort_order,
            "page": self.page,
            "page_size": self.page_size,
            "include_archived": self.include_archived,
        }
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "tenant_id": "tenant_123",
                "event_types": ["user.created", "user.updated"],
                "event_status": "completed",
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-12-31T23:59:59Z",
                "user_id": "usr_123456789",
                "correlation_id": "trace_123",
                "payload_filters": {
                    "user.email": "john@example.com"
                },
                "sort_by": "created_at",
                "sort_order": "desc",
                "page": 1,
                "page_size": 20,
                "include_archived": False
            }
        }