"""
Deliver webhook request model.

ONLY handles manual webhook delivery API request validation and transformation.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, HttpUrl, validator

from neo_commons.platform.events.core.value_objects.webhook_endpoint_id import WebhookEndpointId
from neo_commons.platform.events.core.value_objects.event_id import EventId
from neo_commons.core.value_objects import TenantId


class DeliverWebhookRequest(BaseModel):
    """Request model for manual webhook delivery."""
    
    webhook_endpoint_id: str = Field(
        ...,
        description="ID of the webhook endpoint to deliver to",
        example="wh_123456789"
    )
    
    event_id: str = Field(
        ...,
        description="ID of the event to deliver",
        example="evt_123456789"
    )
    
    tenant_id: str = Field(
        ...,
        description="Tenant identifier",
        example="tenant_123"
    )
    
    override_url: Optional[HttpUrl] = Field(
        None,
        description="Override URL for this specific delivery",
        example="https://api.example.com/webhooks/test"
    )
    
    override_headers: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Additional headers for this delivery"
    )
    
    force_delivery: bool = Field(
        default=False,
        description="Force delivery even if conditions are not met"
    )
    
    test_mode: bool = Field(
        default=False,
        description="Run in test mode (no actual delivery)"
    )
    
    correlation_id: Optional[str] = Field(
        None,
        description="Correlation ID for tracking this delivery",
        example="trace_123"
    )
    
    @validator('webhook_endpoint_id')
    def validate_webhook_endpoint_id(cls, v):
        """Validate webhook endpoint ID format."""
        if not v.strip():
            raise ValueError("Webhook endpoint ID cannot be empty")
        return v.strip()
    
    @validator('event_id')
    def validate_event_id(cls, v):
        """Validate event ID format."""
        if not v.strip():
            raise ValueError("Event ID cannot be empty")
        return v.strip()
    
    @validator('override_url')
    def validate_override_url(cls, v):
        """Validate override URL if provided."""
        if v and not str(v).startswith(('http://', 'https://')):
            raise ValueError("Override URL must use HTTP or HTTPS")
        return v
    
    def to_domain(self) -> Dict[str, Any]:
        """Convert to domain representation."""
        return {
            "webhook_endpoint_id": WebhookEndpointId(self.webhook_endpoint_id),
            "event_id": EventId(self.event_id),
            "tenant_id": TenantId(self.tenant_id),
            "override_url": str(self.override_url) if self.override_url else None,
            "override_headers": self.override_headers or {},
            "force_delivery": self.force_delivery,
            "test_mode": self.test_mode,
            "correlation_id": self.correlation_id,
        }
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "webhook_endpoint_id": "wh_123456789",
                "event_id": "evt_987654321",
                "tenant_id": "tenant_123",
                "override_url": "https://api.example.com/webhooks/test",
                "override_headers": {
                    "X-Test-Mode": "true",
                    "X-Delivery-ID": "manual_001"
                },
                "force_delivery": False,
                "test_mode": True,
                "correlation_id": "manual_delivery_trace_123"
            }
        }