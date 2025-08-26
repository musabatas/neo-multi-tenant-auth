"""Delivery failed domain event for platform events infrastructure.

This module defines the DeliveryFailed domain event that represents when
a delivery attempt has failed in the platform infrastructure.

Following maximum separation architecture - this file contains ONLY DeliveryFailed.
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
class DeliveryFailed(DomainEvent):
    """Platform domain event representing when a delivery attempt has failed.
    
    This is a platform infrastructure event that tracks when the event platform
    fails to deliver a webhook, email, SMS, or other notification, including 
    error details and retry information.
    
    Event type: 'platform.delivery_failed'
    Aggregate: The delivery record (webhook_delivery, email_delivery, etc.)
    """
    
    # Delivery failure information (must use field() since parent has default fields)
    delivery_type: str = field(default="")  # Type of delivery (webhook, email, sms, etc.)
    delivery_target: str = field(default="")  # URL, email address, phone number, etc.
    failure_reason: str = field(default="")  # High-level reason for failure
    
    def __init__(self,
                 delivery_id: UUID,
                 delivery_type: str,
                 delivery_target: str,
                 failure_reason: str,
                 original_event_id: Optional[EventId] = None,
                 original_event_type: Optional[str] = None,
                 error_message: Optional[str] = None,
                 error_code: Optional[str] = None,
                 http_status_code: Optional[int] = None,
                 response_time_ms: Optional[int] = None,
                 attempt_number: int = 1,
                 retry_count: int = 0,
                 max_retries: int = 3,
                 will_retry: bool = False,
                 failure_category: str = "delivery_error",
                 endpoint_id: Optional[UUID] = None,
                 request_data: Optional[Dict[str, Any]] = None,
                 response_data: Optional[Dict[str, Any]] = None,
                 correlation_id: Optional[UUID] = None,
                 triggered_by_user_id: Optional[UserId] = None,
                 **kwargs):
        """Initialize DeliveryFailed domain event.
        
        Args:
            delivery_id: ID of the delivery attempt
            delivery_type: Type of delivery (webhook, email, sms, slack, etc.)
            delivery_target: Target for delivery (URL, email, phone, etc.)
            failure_reason: High-level reason for the failure
            original_event_id: ID of the original event that triggered this delivery
            original_event_type: Type of the original event
            error_message: Detailed error message from the failure
            error_code: Specific error code (if available)
            http_status_code: HTTP status code (for webhook deliveries)
            response_time_ms: Time taken before failure in milliseconds
            attempt_number: Which attempt this was (for retries)
            retry_count: Current number of retries attempted
            max_retries: Maximum number of retries allowed
            will_retry: Whether this delivery will be retried
            failure_category: Category of failure (delivery_error, timeout, auth_error, etc.)
            endpoint_id: ID of the endpoint configuration (webhook_endpoint_id, etc.)
            request_data: Data about the request that failed
            response_data: Response data from the failed delivery attempt
            correlation_id: Correlation ID for event tracing
            triggered_by_user_id: User who triggered the original event
            **kwargs: Additional DomainEvent fields
        """
        # Set platform event data
        event_data = {
            "delivery_id": str(delivery_id),
            "delivery_type": delivery_type,
            "delivery_target": delivery_target,
            "failure_reason": failure_reason,
            "attempt_number": attempt_number,
            "retry_count": retry_count,
            "max_retries": max_retries,
            "will_retry": will_retry,
            "failure_category": failure_category,
        }
        
        # Add optional context data
        if original_event_id:
            event_data["original_event_id"] = str(original_event_id.value)
        if original_event_type:
            event_data["original_event_type"] = original_event_type
        if error_message:
            # Truncate error message to prevent large event data
            max_error_length = 2000
            truncated_error = error_message[:max_error_length]
            if len(error_message) > max_error_length:
                truncated_error += "... (truncated)"
            event_data["error_message"] = truncated_error
        if error_code:
            event_data["error_code"] = error_code
        if http_status_code is not None:
            event_data["http_status_code"] = http_status_code
        if response_time_ms is not None:
            event_data["response_time_ms"] = response_time_ms
        if endpoint_id:
            event_data["endpoint_id"] = str(endpoint_id)
        if request_data:
            event_data["request_data"] = request_data
        if response_data:
            event_data["response_data"] = response_data
        
        # Store additional fields
        self.delivery_type = delivery_type
        self.delivery_target = delivery_target
        self.failure_reason = failure_reason
        
        # Initialize base domain event
        super().__init__(
            event_type=EventType("platform.delivery_failed"),
            aggregate_id=delivery_id,  # Use delivery ID as aggregate
            aggregate_type=f"{delivery_type}_delivery",
            event_data=event_data,
            correlation_id=correlation_id,
            triggered_by_user_id=triggered_by_user_id,
            **kwargs
        )
    
    @property
    def delivery_id(self) -> UUID:
        """Get the delivery ID from event data."""
        return UUID(self.event_data["delivery_id"])
    
    @property
    def error_message(self) -> Optional[str]:
        """Get the detailed error message."""
        return self.event_data.get("error_message")
    
    @property
    def error_code(self) -> Optional[str]:
        """Get the specific error code."""
        return self.event_data.get("error_code")
    
    @property
    def http_status_code(self) -> Optional[int]:
        """Get HTTP status code (for webhook deliveries)."""
        return self.event_data.get("http_status_code")
    
    @property
    def response_time_ms(self) -> Optional[int]:
        """Get response time before failure in milliseconds."""
        return self.event_data.get("response_time_ms")
    
    @property
    def attempt_number(self) -> int:
        """Get the attempt number for this delivery."""
        return self.event_data.get("attempt_number", 1)
    
    @property
    def retry_count(self) -> int:
        """Get the current number of retries attempted."""
        return self.event_data.get("retry_count", 0)
    
    @property
    def max_retries(self) -> int:
        """Get the maximum number of retries allowed."""
        return self.event_data.get("max_retries", 3)
    
    @property
    def will_retry(self) -> bool:
        """Check if this delivery will be retried."""
        return self.event_data.get("will_retry", False)
    
    @property
    def failure_category(self) -> str:
        """Get the category of failure."""
        return self.event_data.get("failure_category", "delivery_error")
    
    @property
    def endpoint_id(self) -> Optional[UUID]:
        """Get the endpoint ID (if applicable)."""
        endpoint_id_str = self.event_data.get("endpoint_id")
        return UUID(endpoint_id_str) if endpoint_id_str else None
    
    @property
    def request_data(self) -> Optional[Dict[str, Any]]:
        """Get request data from the failed delivery attempt."""
        return self.event_data.get("request_data")
    
    @property
    def response_data(self) -> Optional[Dict[str, Any]]:
        """Get response data from the failed delivery attempt."""
        return self.event_data.get("response_data")
    
    @property
    def original_event_id(self) -> Optional[EventId]:
        """Get the original event ID that triggered this delivery."""
        event_id_str = self.event_data.get("original_event_id")
        return EventId(UUID(event_id_str)) if event_id_str else None
    
    @property
    def original_event_type(self) -> Optional[str]:
        """Get the original event type that triggered this delivery."""
        return self.event_data.get("original_event_type")
    
    def is_webhook_delivery(self) -> bool:
        """Check if this was a webhook delivery failure."""
        return self.delivery_type == "webhook"
    
    def is_email_delivery(self) -> bool:
        """Check if this was an email delivery failure."""
        return self.delivery_type == "email"
    
    def is_sms_delivery(self) -> bool:
        """Check if this was an SMS delivery failure."""
        return self.delivery_type == "sms"
    
    def is_retryable_failure(self) -> bool:
        """Check if this failure is retryable."""
        return self.will_retry and self.retry_count < self.max_retries
    
    def is_final_failure(self) -> bool:
        """Check if this is the final failure (no more retries)."""
        return not self.will_retry or self.retry_count >= self.max_retries
    
    def is_authentication_error(self) -> bool:
        """Check if this was an authentication error."""
        return self.failure_category == "auth_error"
    
    def is_timeout_error(self) -> bool:
        """Check if this was a timeout error."""
        return self.failure_category == "timeout"
    
    def is_client_error(self) -> bool:
        """Check if this was a client error (4xx for webhooks)."""
        status = self.http_status_code
        return status is not None and 400 <= status < 500
    
    def is_server_error(self) -> bool:
        """Check if this was a server error (5xx for webhooks)."""
        status = self.http_status_code
        return status is not None and 500 <= status < 600
    
    @classmethod
    def create_for_webhook(cls,
                         delivery_id: WebhookDeliveryId,
                         delivery_target: str,
                         failure_reason: str,
                         original_event_id: Optional[EventId] = None,
                         original_event_type: Optional[str] = None,
                         error_message: Optional[str] = None,
                         error_code: Optional[str] = None,
                         http_status_code: Optional[int] = None,
                         response_time_ms: Optional[int] = None,
                         attempt_number: int = 1,
                         retry_count: int = 0,
                         max_retries: int = 3,
                         will_retry: bool = False,
                         failure_category: str = "delivery_error",
                         endpoint_id: Optional[WebhookEndpointId] = None,
                         request_data: Optional[Dict[str, Any]] = None,
                         response_data: Optional[Dict[str, Any]] = None,
                         correlation_id: Optional[UUID] = None,
                         triggered_by_user_id: Optional[UserId] = None) -> 'DeliveryFailed':
        """Factory method to create DeliveryFailed for a webhook delivery failure.
        
        This factory ensures consistent creation of DeliveryFailed events
        for webhook deliveries with proper UUIDv7 compliance and platform metadata.
        """
        return cls(
            delivery_id=delivery_id.value,
            delivery_type="webhook",
            delivery_target=delivery_target,
            failure_reason=failure_reason,
            original_event_id=original_event_id,
            original_event_type=original_event_type,
            error_message=error_message,
            error_code=error_code,
            http_status_code=http_status_code,
            response_time_ms=response_time_ms,
            attempt_number=attempt_number,
            retry_count=retry_count,
            max_retries=max_retries,
            will_retry=will_retry,
            failure_category=failure_category,
            endpoint_id=endpoint_id.value if endpoint_id else None,
            request_data=request_data,
            response_data=response_data,
            correlation_id=correlation_id or generate_uuid_v7(),
            triggered_by_user_id=triggered_by_user_id
        )
    
    @classmethod
    def create_for_email(cls,
                        delivery_id: UUID,
                        email_address: str,
                        failure_reason: str,
                        original_event_id: Optional[EventId] = None,
                        original_event_type: Optional[str] = None,
                        error_message: Optional[str] = None,
                        error_code: Optional[str] = None,
                        attempt_number: int = 1,
                        retry_count: int = 0,
                        max_retries: int = 3,
                        will_retry: bool = False,
                        failure_category: str = "delivery_error",
                        correlation_id: Optional[UUID] = None,
                        triggered_by_user_id: Optional[UserId] = None) -> 'DeliveryFailed':
        """Factory method to create DeliveryFailed for an email delivery failure."""
        return cls(
            delivery_id=delivery_id,
            delivery_type="email",
            delivery_target=email_address,
            failure_reason=failure_reason,
            original_event_id=original_event_id,
            original_event_type=original_event_type,
            error_message=error_message,
            error_code=error_code,
            attempt_number=attempt_number,
            retry_count=retry_count,
            max_retries=max_retries,
            will_retry=will_retry,
            failure_category=failure_category,
            correlation_id=correlation_id or generate_uuid_v7(),
            triggered_by_user_id=triggered_by_user_id
        )