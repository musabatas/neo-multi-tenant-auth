"""Webhook delivered domain event for platform events infrastructure.

This module defines the WebhookDelivered domain event that represents when
a webhook has been successfully delivered by the platform infrastructure.

Following maximum separation architecture - this file contains ONLY WebhookDelivered.
Pure platform infrastructure event - represents platform operation, not business logic.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from uuid import UUID

from ..entities.domain_event import DomainEvent
from ..value_objects import EventType, EventId, WebhookDeliveryId, WebhookEndpointId
from .....core.value_objects import UserId
from .....utils import generate_uuid_v7


@dataclass
class WebhookDelivered(DomainEvent):
    """Platform domain event representing when a webhook has been successfully delivered.
    
    This is a platform infrastructure event that tracks when the event platform
    successfully delivers a webhook to an external endpoint.
    
    Event type: 'platform.webhook_delivered'
    Aggregate: The webhook delivery record
    """
    
    # Webhook delivery information (must use field() since parent has default fields)
    webhook_endpoint_id: WebhookEndpointId = field(default=None)
    delivery_url: str = field(default="")  # URL where webhook was delivered
    delivery_method: str = field(default="POST")  # HTTP method used (POST, PUT, etc.)
    
    def __init__(self,
                 delivery_id: WebhookDeliveryId,
                 webhook_endpoint_id: WebhookEndpointId,
                 delivery_url: str,
                 delivery_method: str = "POST",
                 original_event_id: Optional[EventId] = None,
                 original_event_type: Optional[str] = None,
                 http_status_code: Optional[int] = None,
                 response_time_ms: Optional[int] = None,
                 attempt_number: int = 1,
                 retry_count: int = 0,
                 signature_sent: bool = False,
                 response_body: Optional[str] = None,
                 correlation_id: Optional[UUID] = None,
                 triggered_by_user_id: Optional[UserId] = None,
                 **kwargs):
        """Initialize WebhookDelivered domain event.
        
        Args:
            delivery_id: ID of the webhook delivery record
            webhook_endpoint_id: ID of the webhook endpoint configuration
            delivery_url: URL where the webhook was delivered
            delivery_method: HTTP method used for delivery
            original_event_id: ID of the original event that triggered this webhook
            original_event_type: Type of the original event
            http_status_code: HTTP response status code from the webhook endpoint
            response_time_ms: Time taken for webhook delivery in milliseconds
            attempt_number: Which attempt this was (for retries)
            retry_count: Number of retries that occurred
            signature_sent: Whether HMAC signature was sent with the webhook
            response_body: Response body from webhook endpoint (truncated if too long)
            correlation_id: Correlation ID for event tracing
            triggered_by_user_id: User who triggered the original event
            **kwargs: Additional DomainEvent fields
        """
        # Set platform event data
        event_data = {
            "delivery_id": str(delivery_id.value),
            "webhook_endpoint_id": str(webhook_endpoint_id.value),
            "delivery_url": delivery_url,
            "delivery_method": delivery_method,
            "attempt_number": attempt_number,
            "retry_count": retry_count,
            "signature_sent": signature_sent,
        }
        
        # Add optional context data
        if original_event_id:
            event_data["original_event_id"] = str(original_event_id.value)
        if original_event_type:
            event_data["original_event_type"] = original_event_type
        if http_status_code is not None:
            event_data["http_status_code"] = http_status_code
        if response_time_ms is not None:
            event_data["response_time_ms"] = response_time_ms
        if response_body:
            # Truncate response body to prevent large event data
            max_response_length = 1000
            truncated_response = response_body[:max_response_length]
            if len(response_body) > max_response_length:
                truncated_response += "... (truncated)"
            event_data["response_body"] = truncated_response
        
        # Store additional fields
        self.webhook_endpoint_id = webhook_endpoint_id
        self.delivery_url = delivery_url
        self.delivery_method = delivery_method
        
        # Initialize base domain event
        super().__init__(
            event_type=EventType("platform.webhook_delivered"),
            aggregate_id=delivery_id.value,  # Use delivery ID as aggregate
            aggregate_type="webhook_delivery",
            event_data=event_data,
            correlation_id=correlation_id,
            triggered_by_user_id=triggered_by_user_id,
            **kwargs
        )
    
    @property
    def delivery_id(self) -> WebhookDeliveryId:
        """Get the delivery ID from event data."""
        return WebhookDeliveryId(UUID(self.event_data["delivery_id"]))
    
    @property
    def http_status_code(self) -> Optional[int]:
        """Get HTTP response status code."""
        return self.event_data.get("http_status_code")
    
    @property
    def response_time_ms(self) -> Optional[int]:
        """Get response time in milliseconds."""
        return self.event_data.get("response_time_ms")
    
    @property
    def attempt_number(self) -> int:
        """Get the attempt number for this delivery."""
        return self.event_data.get("attempt_number", 1)
    
    @property
    def retry_count(self) -> int:
        """Get the number of retries performed."""
        return self.event_data.get("retry_count", 0)
    
    @property
    def signature_sent(self) -> bool:
        """Check if HMAC signature was sent with the webhook."""
        return self.event_data.get("signature_sent", False)
    
    @property
    def response_body(self) -> Optional[str]:
        """Get the response body (may be truncated)."""
        return self.event_data.get("response_body")
    
    @property
    def original_event_id(self) -> Optional[EventId]:
        """Get the original event ID that triggered this webhook."""
        event_id_str = self.event_data.get("original_event_id")
        return EventId(UUID(event_id_str)) if event_id_str else None
    
    @property
    def original_event_type(self) -> Optional[str]:
        """Get the original event type that triggered this webhook."""
        return self.event_data.get("original_event_type")
    
    def is_successful(self) -> bool:
        """Check if the webhook delivery was successful (2xx status code)."""
        status = self.http_status_code
        return status is not None and 200 <= status < 300
    
    def is_client_error(self) -> bool:
        """Check if the webhook delivery resulted in a client error (4xx status code)."""
        status = self.http_status_code
        return status is not None and 400 <= status < 500
    
    def is_server_error(self) -> bool:
        """Check if the webhook delivery resulted in a server error (5xx status code)."""
        status = self.http_status_code
        return status is not None and 500 <= status < 600
    
    def was_retried(self) -> bool:
        """Check if this delivery required retries."""
        return self.retry_count > 0
    
    @classmethod
    def create_for_delivery(cls,
                          delivery_id: WebhookDeliveryId,
                          webhook_endpoint_id: WebhookEndpointId,
                          delivery_url: str,
                          delivery_method: str = "POST",
                          original_event_id: Optional[EventId] = None,
                          original_event_type: Optional[str] = None,
                          http_status_code: Optional[int] = None,
                          response_time_ms: Optional[int] = None,
                          attempt_number: int = 1,
                          retry_count: int = 0,
                          signature_sent: bool = False,
                          response_body: Optional[str] = None,
                          correlation_id: Optional[UUID] = None,
                          triggered_by_user_id: Optional[UserId] = None) -> 'WebhookDelivered':
        """Factory method to create WebhookDelivered for a specific delivery.
        
        This factory ensures consistent creation of WebhookDelivered events
        with proper UUIDv7 compliance and platform metadata.
        """
        return cls(
            delivery_id=delivery_id,
            webhook_endpoint_id=webhook_endpoint_id,
            delivery_url=delivery_url,
            delivery_method=delivery_method,
            original_event_id=original_event_id,
            original_event_type=original_event_type,
            http_status_code=http_status_code,
            response_time_ms=response_time_ms,
            attempt_number=attempt_number,
            retry_count=retry_count,
            signature_sent=signature_sent,
            response_body=response_body,
            correlation_id=correlation_id or generate_uuid_v7(),
            triggered_by_user_id=triggered_by_user_id
        )