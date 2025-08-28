"""
Webhook logs response model.

ONLY handles webhook logs data API response formatting.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from .webhook_delivery_response import WebhookDeliveryResponse


class WebhookLogsPaginationResponse(BaseModel):
    """Pagination information for webhook logs."""
    
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    total_items: int = Field(..., description="Total number of items")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_previous: bool = Field(..., description="Whether there are previous pages")


class WebhookLogsStatsResponse(BaseModel):
    """Webhook logs statistics."""
    
    total_deliveries: int = Field(..., description="Total deliveries in logs")
    successful_deliveries: int = Field(..., description="Successful deliveries")
    failed_deliveries: int = Field(..., description="Failed deliveries")
    pending_deliveries: int = Field(..., description="Pending deliveries")
    success_rate: float = Field(..., description="Success rate as percentage")
    average_response_time_ms: float = Field(..., description="Average response time in ms")
    unique_endpoints: int = Field(..., description="Number of unique endpoints")


class WebhookLogsResponse(BaseModel):
    """Response model for webhook logs data."""
    
    tenant_id: str = Field(
        ...,
        description="Tenant identifier",
        example="tenant_123"
    )
    
    webhook_endpoint_id: Optional[str] = Field(
        None,
        description="Specific webhook endpoint ID if filtered",
        example="wh_123456789"
    )
    
    deliveries: List[WebhookDeliveryResponse] = Field(
        ...,
        description="List of webhook deliveries"
    )
    
    pagination: WebhookLogsPaginationResponse = Field(
        ...,
        description="Pagination information"
    )
    
    stats: WebhookLogsStatsResponse = Field(
        ...,
        description="Webhook delivery statistics"
    )
    
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Applied filters"
    )
    
    period_start: Optional[datetime] = Field(
        None,
        description="Log period start"
    )
    
    period_end: Optional[datetime] = Field(
        None,
        description="Log period end"
    )
    
    sort_by: str = Field(
        default="created_at",
        description="Field used for sorting"
    )
    
    sort_order: str = Field(
        default="desc", 
        description="Sort order"
    )
    
    retrieved_at: datetime = Field(
        ...,
        description="When logs were retrieved"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "tenant_id": "tenant_123",
                "webhook_endpoint_id": "wh_123456789",
                "deliveries": [
                    {
                        "id": "wdel_123456789",
                        "webhook_endpoint_id": "wh_123456789",
                        "event_id": "evt_123456789",
                        "tenant_id": "tenant_123",
                        "webhook_url": "https://api.example.com/webhooks/events",
                        "status": "delivered",
                        "http_status_code": 200,
                        "request_headers": {"Content-Type": "application/json"},
                        "request_payload": {"event_type": "user.created"},
                        "response_headers": {"Content-Type": "application/json"},
                        "response_body": '{"success": true}',
                        "delivery_attempt": 1,
                        "max_attempts": 3,
                        "created_at": "2024-01-15T10:30:01Z",
                        "delivered_at": "2024-01-15T10:30:02Z",
                        "failed_at": None,
                        "next_retry_at": None,
                        "duration_ms": 125.5,
                        "error_message": None,
                        "correlation_id": "trace_123",
                        "signature": "sha256=a1b2c3d4..."
                    }
                ],
                "pagination": {
                    "page": 1,
                    "page_size": 20,
                    "total_pages": 3,
                    "total_items": 55,
                    "has_next": True,
                    "has_previous": False
                },
                "stats": {
                    "total_deliveries": 55,
                    "successful_deliveries": 50,
                    "failed_deliveries": 3,
                    "pending_deliveries": 2,
                    "success_rate": 90.9,
                    "average_response_time_ms": 125.5,
                    "unique_endpoints": 5
                },
                "filters": {
                    "status": "delivered",
                    "date_range": "last_7_days"
                },
                "period_start": "2024-01-08T00:00:00Z",
                "period_end": "2024-01-15T23:59:59Z",
                "sort_by": "created_at",
                "sort_order": "desc",
                "retrieved_at": "2024-01-15T15:00:00Z"
            }
        }