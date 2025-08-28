"""
Webhook delivery response model.

ONLY handles webhook delivery data API response formatting.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class WebhookDeliveryResponse(BaseModel):
    """Response model for webhook delivery data."""
    
    id: str = Field(
        ...,
        description="Webhook delivery ID",
        example="wdel_123456789"
    )
    
    webhook_endpoint_id: str = Field(
        ...,
        description="Webhook endpoint ID",
        example="wh_123456789"
    )
    
    event_id: str = Field(
        ...,
        description="Event ID",
        example="evt_123456789"
    )
    
    tenant_id: str = Field(
        ...,
        description="Tenant identifier",
        example="tenant_123"
    )
    
    webhook_url: str = Field(
        ...,
        description="Webhook endpoint URL",
        example="https://api.example.com/webhooks/events"
    )
    
    status: str = Field(
        ...,
        description="Delivery status",
        example="delivered"
    )
    
    http_status_code: Optional[int] = Field(
        None,
        description="HTTP response status code",
        example=200
    )
    
    request_headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Request headers sent"
    )
    
    request_payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Request payload sent"
    )
    
    response_headers: Optional[Dict[str, str]] = Field(
        None,
        description="Response headers received"
    )
    
    response_body: Optional[str] = Field(
        None,
        description="Response body received"
    )
    
    delivery_attempt: int = Field(
        ...,
        description="Delivery attempt number",
        example=1
    )
    
    max_attempts: int = Field(
        ...,
        description="Maximum delivery attempts",
        example=3
    )
    
    created_at: datetime = Field(
        ...,
        description="Delivery creation timestamp"
    )
    
    delivered_at: Optional[datetime] = Field(
        None,
        description="Successful delivery timestamp"
    )
    
    failed_at: Optional[datetime] = Field(
        None,
        description="Failure timestamp"
    )
    
    next_retry_at: Optional[datetime] = Field(
        None,
        description="Next retry timestamp"
    )
    
    duration_ms: Optional[float] = Field(
        None,
        description="Delivery duration in milliseconds",
        example=125.5
    )
    
    error_message: Optional[str] = Field(
        None,
        description="Error message if failed"
    )
    
    correlation_id: Optional[str] = Field(
        None,
        description="Correlation ID for tracing",
        example="trace_123"
    )
    
    signature: Optional[str] = Field(
        None,
        description="HMAC signature sent",
        example="sha256=a1b2c3d4..."
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "id": "wdel_123456789",
                "webhook_endpoint_id": "wh_123456789",
                "event_id": "evt_123456789",
                "tenant_id": "tenant_123",
                "webhook_url": "https://api.example.com/webhooks/events",
                "status": "delivered",
                "http_status_code": 200,
                "request_headers": {
                    "Content-Type": "application/json",
                    "User-Agent": "NeoMultiTenant-Webhooks/1.0",
                    "X-Neo-Signature": "sha256=a1b2c3d4..."
                },
                "request_payload": {
                    "event_id": "evt_123456789",
                    "event_type": "user.created",
                    "payload": {"user_id": "usr_123"},
                    "timestamp": "2024-01-15T10:30:00Z"
                },
                "response_headers": {
                    "Content-Type": "application/json",
                    "Server": "nginx/1.20.0"
                },
                "response_body": '{"success": true, "processed": true}',
                "delivery_attempt": 1,
                "max_attempts": 3,
                "created_at": "2024-01-15T10:30:01Z",
                "delivered_at": "2024-01-15T10:30:02Z",
                "failed_at": None,
                "next_retry_at": None,
                "duration_ms": 125.5,
                "error_message": None,
                "correlation_id": "trace_abc123",
                "signature": "sha256=a1b2c3d4..."
            }
        }