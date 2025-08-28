"""
Search events response model.

ONLY handles event search results API response formatting.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from .event_response import EventResponse


class SearchEventsPaginationResponse(BaseModel):
    """Pagination information for search results."""
    
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    total_items: int = Field(..., description="Total number of items")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_previous: bool = Field(..., description="Whether there are previous pages")


class SearchEventsFiltersResponse(BaseModel):
    """Applied filters for the search."""
    
    event_types: Optional[List[str]] = Field(None, description="Filtered event types")
    event_status: Optional[str] = Field(None, description="Filtered event status")
    start_date: Optional[datetime] = Field(None, description="Start date filter")
    end_date: Optional[datetime] = Field(None, description="End date filter")
    user_id: Optional[str] = Field(None, description="User ID filter")
    correlation_id: Optional[str] = Field(None, description="Correlation ID filter")
    payload_filters: Dict[str, Any] = Field(default_factory=dict, description="Payload filters")
    include_archived: bool = Field(default=False, description="Include archived events")


class SearchEventsStatsResponse(BaseModel):
    """Search statistics."""
    
    total_events: int = Field(..., description="Total events found")
    events_by_status: Dict[str, int] = Field(default_factory=dict, description="Events grouped by status")
    events_by_type: Dict[str, int] = Field(default_factory=dict, description="Events grouped by type")
    date_range_days: int = Field(..., description="Date range span in days")
    search_duration_ms: float = Field(..., description="Search execution time in milliseconds")


class SearchEventsResponse(BaseModel):
    """Response model for event search results."""
    
    events: List[EventResponse] = Field(
        ...,
        description="List of events matching the search criteria"
    )
    
    pagination: SearchEventsPaginationResponse = Field(
        ...,
        description="Pagination information"
    )
    
    filters: SearchEventsFiltersResponse = Field(
        ...,
        description="Applied filters"
    )
    
    stats: SearchEventsStatsResponse = Field(
        ...,
        description="Search statistics"
    )
    
    sort_by: str = Field(
        ...,
        description="Field used for sorting",
        example="created_at"
    )
    
    sort_order: str = Field(
        ...,
        description="Sort order",
        example="desc"
    )
    
    search_id: str = Field(
        ...,
        description="Unique identifier for this search",
        example="search_123456789"
    )
    
    tenant_id: str = Field(
        ...,
        description="Tenant identifier",
        example="tenant_123"
    )
    
    searched_at: datetime = Field(
        ...,
        description="When the search was performed"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "events": [
                    {
                        "id": "evt_123456789",
                        "event_type": "user.created",
                        "payload": {"user_id": "usr_123", "email": "john@example.com"},
                        "tenant_id": "tenant_123",
                        "user_id": "usr_987",
                        "correlation_id": "trace_abc",
                        "status": "completed",
                        "execution_mode": "async",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:05Z",
                        "scheduled_at": None,
                        "processed_at": "2024-01-15T10:30:05Z",
                        "metadata": {"source": "admin_api"},
                        "actions": [],
                        "retry_count": 0,
                        "error_message": None
                    }
                ],
                "pagination": {
                    "page": 1,
                    "page_size": 20,
                    "total_pages": 5,
                    "total_items": 95,
                    "has_next": True,
                    "has_previous": False
                },
                "filters": {
                    "event_types": ["user.created", "user.updated"],
                    "event_status": "completed",
                    "start_date": "2024-01-01T00:00:00Z",
                    "end_date": "2024-01-31T23:59:59Z",
                    "user_id": None,
                    "correlation_id": None,
                    "payload_filters": {},
                    "include_archived": False
                },
                "stats": {
                    "total_events": 95,
                    "events_by_status": {
                        "completed": 85,
                        "failed": 8,
                        "processing": 2
                    },
                    "events_by_type": {
                        "user.created": 50,
                        "user.updated": 45
                    },
                    "date_range_days": 31,
                    "search_duration_ms": 125.5
                },
                "sort_by": "created_at",
                "sort_order": "desc",
                "search_id": "search_123456789",
                "tenant_id": "tenant_123",
                "searched_at": "2024-01-15T15:45:00Z"
            }
        }