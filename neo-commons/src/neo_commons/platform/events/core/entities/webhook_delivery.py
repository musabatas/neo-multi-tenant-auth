"""Webhook delivery entity for platform events infrastructure.

This module defines the WebhookDelivery entity that represents a single webhook
delivery attempt with tracking, results, and performance metrics.

Extracted from features/events to platform/events following enterprise
clean architecture patterns for maximum separation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime
from uuid import UUID

from .....utils import generate_uuid_v7, utc_now, ensure_utc
from ..value_objects import EventId, WebhookEndpointId, WebhookDeliveryId, DeliveryStatus


@dataclass
class WebhookDelivery:
    """Webhook delivery domain entity.
    
    Represents a single webhook delivery attempt with complete lifecycle tracking,
    request/response details, error handling, and performance metrics.
    
    Maps to webhook_deliveries table in both admin and tenant schemas.
    Pure platform infrastructure - used by all business features.
    """
    
    # Delivery identification (UUIDv7 for time-ordering)
    id: WebhookDeliveryId = field(default_factory=lambda: WebhookDeliveryId(UUID(generate_uuid_v7())))
    webhook_endpoint_id: WebhookEndpointId = field(default_factory=lambda: WebhookEndpointId(UUID(generate_uuid_v7())))
    webhook_event_id: EventId = field(default_factory=lambda: EventId(UUID(generate_uuid_v7())))
    
    # Delivery attempt tracking
    attempt_number: int = 1
    delivery_status: DeliveryStatus = DeliveryStatus.PENDING
    
    # Request details (matches database schema)
    request_url: str = ""
    request_method: str = "POST"
    request_headers: Dict[str, Any] = field(default_factory=dict)
    request_body: Optional[str] = None
    request_signature: Optional[str] = None  # HMAC signature sent
    
    # Response details (matches database schema)
    response_status_code: Optional[int] = None
    response_headers: Optional[Dict[str, Any]] = None
    response_body: Optional[str] = None
    response_time_ms: Optional[int] = None
    
    # Error handling (matches database schema)
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    # Retry information (matches database schema)
    next_retry_at: Optional[datetime] = None
    max_attempts_reached: bool = False
    
    # Timestamps (matches database schema)
    attempted_at: datetime = field(default_factory=utc_now)
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=utc_now)
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        # Validate attempt number (matches database check constraint)
        if self.attempt_number < 1:
            raise ValueError("Attempt number must be >= 1")
        
        # Validate delivery status
        if not isinstance(self.delivery_status, DeliveryStatus):
            raise ValueError("delivery_status must be a DeliveryStatus enum")
        
        # Validate HTTP method if request_url is provided
        if self.request_url and self.request_method not in {"POST", "PUT", "PATCH"}:
            raise ValueError(f"Invalid HTTP method: {self.request_method}. Must be POST, PUT, or PATCH")
        
        # Validate request URL format if provided
        if self.request_url and not self._is_valid_url(self.request_url):
            raise ValueError(f"Invalid request URL format: {self.request_url}")
        
        # Validate response status code if provided
        if self.response_status_code is not None and not (100 <= self.response_status_code <= 599):
            raise ValueError(f"Invalid HTTP status code: {self.response_status_code}")
        
        # Validate response time if provided
        if self.response_time_ms is not None and self.response_time_ms < 0:
            raise ValueError("Response time cannot be negative")
        
        # Ensure timestamps are timezone-aware
        self.attempted_at = ensure_utc(self.attempted_at)
        self.created_at = ensure_utc(self.created_at)
        
        if self.completed_at:
            self.completed_at = ensure_utc(self.completed_at)
        
        if self.next_retry_at:
            self.next_retry_at = ensure_utc(self.next_retry_at)
    
    def _is_valid_url(self, url: str) -> bool:
        """Basic URL validation."""
        import re
        # Basic URL pattern that requires http/https protocol
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return bool(url_pattern.match(url))
    
    def start_delivery(self, request_url: str, request_headers: Dict[str, Any], 
                      request_body: Optional[str] = None, request_signature: Optional[str] = None) -> None:
        """Mark delivery as started with request details."""
        if self.delivery_status not in {DeliveryStatus.PENDING, DeliveryStatus.RETRYING}:
            raise ValueError(f"Cannot start delivery with status: {self.delivery_status}")
        
        if not self._is_valid_url(request_url):
            raise ValueError(f"Invalid request URL: {request_url}")
        
        self.delivery_status = DeliveryStatus.RETRYING  # In progress
        self.request_url = request_url
        self.request_headers = request_headers
        self.request_body = request_body
        self.request_signature = request_signature
        self.attempted_at = utc_now()
    
    def complete_success(self, response_status_code: int, response_headers: Dict[str, Any], 
                        response_body: Optional[str] = None, response_time_ms: Optional[int] = None) -> None:
        """Mark delivery as successfully completed with response details."""
        if self.delivery_status not in {DeliveryStatus.RETRYING, DeliveryStatus.PENDING}:
            raise ValueError(f"Cannot complete delivery with status: {self.delivery_status}")
        
        self.delivery_status = DeliveryStatus.SUCCESS
        self.completed_at = utc_now()
        self.response_status_code = response_status_code
        self.response_headers = response_headers
        self.response_body = response_body
        self.response_time_ms = response_time_ms
        
        # Clear retry information on success
        self.next_retry_at = None
        self.error_message = None
        self.error_code = None
    
    def complete_failure(self, error_message: str, error_code: Optional[str] = None,
                        response_status_code: Optional[int] = None, response_headers: Optional[Dict[str, Any]] = None,
                        response_body: Optional[str] = None, response_time_ms: Optional[int] = None) -> None:
        """Mark delivery as failed with error details."""
        if self.delivery_status not in {DeliveryStatus.RETRYING, DeliveryStatus.PENDING}:
            raise ValueError(f"Cannot fail delivery with status: {self.delivery_status}")
        
        # Determine failure type based on response
        if response_status_code == 408 or response_status_code == 504:
            self.delivery_status = DeliveryStatus.TIMEOUT
        else:
            self.delivery_status = DeliveryStatus.FAILED
        
        self.completed_at = utc_now()
        self.error_message = error_message
        self.error_code = error_code
        self.response_status_code = response_status_code
        self.response_headers = response_headers
        self.response_body = response_body
        self.response_time_ms = response_time_ms
    
    def complete_timeout(self, error_message: str = "Request timed out") -> None:
        """Mark delivery as timed out."""
        if self.delivery_status not in {DeliveryStatus.RETRYING, DeliveryStatus.PENDING}:
            raise ValueError(f"Cannot timeout delivery with status: {self.delivery_status}")
        
        self.delivery_status = DeliveryStatus.TIMEOUT
        self.completed_at = utc_now()
        self.error_message = error_message
        self.error_code = "TIMEOUT"
    
    def cancel_delivery(self, reason: str = "Delivery cancelled") -> None:
        """Cancel the delivery."""
        if self.delivery_status.is_final:
            raise ValueError(f"Cannot cancel delivery with final status: {self.delivery_status}")
        
        self.delivery_status = DeliveryStatus.CANCELLED
        self.completed_at = utc_now()
        self.error_message = reason
        self.error_code = "CANCELLED"
        self.next_retry_at = None
    
    def schedule_retry(self, next_retry_at: datetime, max_attempts: int) -> None:
        """Schedule the delivery for retry."""
        if not self.delivery_status.is_retryable:
            raise ValueError(f"Cannot retry delivery with status: {self.delivery_status}")
        
        if self.attempt_number >= max_attempts:
            self.max_attempts_reached = True
            self.next_retry_at = None
            # Keep current failure status (FAILED or TIMEOUT)
        else:
            self.delivery_status = DeliveryStatus.RETRYING
            self.next_retry_at = ensure_utc(next_retry_at)
    
    def increment_attempt(self) -> None:
        """Increment the attempt number for retry."""
        if not self.delivery_status.is_retryable and self.delivery_status != DeliveryStatus.PENDING:
            raise ValueError(f"Cannot increment attempts for status: {self.delivery_status}")
        
        self.attempt_number += 1
        self.delivery_status = DeliveryStatus.PENDING
        self.completed_at = None
        self.attempted_at = utc_now()
        
        # Clear previous response data for new attempt
        self.response_status_code = None
        self.response_headers = None
        self.response_body = None
        self.response_time_ms = None
        
        # Keep error information for history
    
    def is_completed(self) -> bool:
        """Check if delivery has completed (success or final failure)."""
        return self.delivery_status.is_final or self.max_attempts_reached
    
    def is_successful(self) -> bool:
        """Check if delivery completed successfully."""
        return self.delivery_status.is_successful
    
    def is_failed(self) -> bool:
        """Check if delivery failed (including timeout)."""
        return self.delivery_status.is_failed
    
    def is_retryable(self) -> bool:
        """Check if delivery can be retried."""
        return self.delivery_status.is_retryable and not self.max_attempts_reached
    
    def is_ready_for_retry(self) -> bool:
        """Check if delivery is ready for retry (past retry time)."""
        if not self.is_retryable() or not self.next_retry_at:
            return False
        return utc_now() >= self.next_retry_at
    
    def get_duration_ms(self) -> Optional[int]:
        """Get delivery duration in milliseconds."""
        if self.completed_at and self.attempted_at:
            duration = self.completed_at - self.attempted_at
            return int(duration.total_seconds() * 1000)
        return self.response_time_ms
    
    def get_duration_seconds(self) -> Optional[float]:
        """Get delivery duration in seconds."""
        duration_ms = self.get_duration_ms()
        if duration_ms is not None:
            return duration_ms / 1000.0
        return None
    
    @classmethod
    def create_new(cls, webhook_endpoint_id: WebhookEndpointId, webhook_event_id: EventId,
                   request_method: str = "POST", **kwargs) -> "WebhookDelivery":
        """Create a new webhook delivery with UUIDv7 compliance.
        
        This factory method ensures all new deliveries use UUIDv7 for better
        database performance and time-ordering.
        
        Args:
            webhook_endpoint_id: ID of the webhook endpoint
            webhook_event_id: ID of the webhook event being delivered
            request_method: HTTP method for the request
            **kwargs: Additional fields (request_url, request_headers, etc.)
        """
        return cls(
            webhook_endpoint_id=webhook_endpoint_id,
            webhook_event_id=webhook_event_id,
            request_method=request_method,
            **kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert delivery to dictionary for serialization (matches database schema)."""
        return {
            "id": str(self.id.value),
            "webhook_endpoint_id": str(self.webhook_endpoint_id.value),
            "webhook_event_id": str(self.webhook_event_id.value),
            "attempt_number": self.attempt_number,
            "delivery_status": self.delivery_status.value,
            "request_url": self.request_url,
            "request_method": self.request_method,
            "request_headers": self.request_headers,
            "request_body": self.request_body,
            "request_signature": self.request_signature,
            "response_status_code": self.response_status_code,
            "response_headers": self.response_headers,
            "response_body": self.response_body,
            "response_time_ms": self.response_time_ms,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
            "max_attempts_reached": self.max_attempts_reached,
            "attempted_at": self.attempted_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WebhookDelivery":
        """Create WebhookDelivery from dictionary representation.
        
        Args:
            data: Dictionary with delivery data (typically from database)
            
        Returns:
            WebhookDelivery instance
        """
        from uuid import UUID
        from datetime import datetime
        
        # Convert string IDs back to value objects (UUIDs should be UUIDv7 from database)
        delivery_id = WebhookDeliveryId(UUID(data["id"]))
        webhook_endpoint_id = WebhookEndpointId(UUID(data["webhook_endpoint_id"]))
        webhook_event_id = EventId(UUID(data["webhook_event_id"]))
        
        # Parse enum
        delivery_status = DeliveryStatus(data["delivery_status"])
        
        # Parse datetime fields
        attempted_at = datetime.fromisoformat(data["attempted_at"])
        completed_at = datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        created_at = datetime.fromisoformat(data["created_at"])
        next_retry_at = datetime.fromisoformat(data["next_retry_at"]) if data.get("next_retry_at") else None
        
        return cls(
            id=delivery_id,
            webhook_endpoint_id=webhook_endpoint_id,
            webhook_event_id=webhook_event_id,
            attempt_number=data.get("attempt_number", 1),
            delivery_status=delivery_status,
            request_url=data.get("request_url", ""),
            request_method=data.get("request_method", "POST"),
            request_headers=data.get("request_headers", {}),
            request_body=data.get("request_body"),
            request_signature=data.get("request_signature"),
            response_status_code=data.get("response_status_code"),
            response_headers=data.get("response_headers"),
            response_body=data.get("response_body"),
            response_time_ms=data.get("response_time_ms"),
            error_message=data.get("error_message"),
            error_code=data.get("error_code"),
            next_retry_at=next_retry_at,
            max_attempts_reached=data.get("max_attempts_reached", False),
            attempted_at=attempted_at,
            completed_at=completed_at,
            created_at=created_at,
        )