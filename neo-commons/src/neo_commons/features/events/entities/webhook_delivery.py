"""Webhook delivery entities for neo-commons events feature.

This module defines the WebhookDelivery and WebhookDeliveryAttempt entities
that track webhook delivery attempts, responses, and retry logic.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
from enum import Enum
from uuid import UUID

from ....core.value_objects import WebhookDeliveryId, WebhookEndpointId, EventId


class DeliveryStatus(Enum):
    """Webhook delivery status enumeration.
    
    Values match the database constraint in webhook_deliveries table.
    Complex states like circuit breaker and exhausted are handled through
    additional fields rather than separate enum values.
    """
    PENDING = "pending"
    SUCCESS = "success" 
    FAILED = "failed"
    TIMEOUT = "timeout"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


@dataclass
class WebhookDeliveryAttempt:
    """Individual webhook delivery attempt with full request/response details."""
    
    # Attempt identification
    attempt_number: int
    delivery_status: DeliveryStatus
    
    # Request details
    request_url: str
    request_method: str
    request_headers: Dict[str, str] = field(default_factory=dict)
    request_body: Optional[str] = None
    request_signature: Optional[str] = None  # HMAC signature sent
    
    # Response details
    response_status_code: Optional[int] = None
    response_headers: Optional[Dict[str, Any]] = None
    response_body: Optional[str] = None
    response_time_ms: Optional[int] = None
    
    # Error handling
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    # Timestamps
    attempted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Post-init validation and normalization."""
        # Validate attempt_number
        if self.attempt_number < 1:
            raise ValueError("attempt_number must be >= 1")
        
        # Validate HTTP method
        valid_methods = ["POST", "PUT", "PATCH"]
        if self.request_method not in valid_methods:
            raise ValueError(f"request_method must be one of {valid_methods}")
        
        # Validate request_url
        if not self.request_url or not self.request_url.startswith(('http://', 'https://')):
            raise ValueError("request_url must be a valid HTTP/HTTPS URL")
        
        # Ensure timestamps are timezone-aware
        if self.attempted_at.tzinfo is None:
            self.attempted_at = self.attempted_at.replace(tzinfo=timezone.utc)
        
        if self.completed_at and self.completed_at.tzinfo is None:
            self.completed_at = self.completed_at.replace(tzinfo=timezone.utc)
    
    def mark_completed(self) -> None:
        """Mark the attempt as completed."""
        if self.completed_at is None:
            self.completed_at = datetime.now(timezone.utc)
    
    def is_successful(self) -> bool:
        """Check if the delivery attempt was successful."""
        return self.delivery_status == DeliveryStatus.SUCCESS
    
    def is_failed(self) -> bool:
        """Check if the delivery attempt failed."""
        return self.delivery_status in [
            DeliveryStatus.FAILED, 
            DeliveryStatus.TIMEOUT, 
            DeliveryStatus.CANCELLED,
            DeliveryStatus.CIRCUIT_BREAKER_OPEN,
            DeliveryStatus.EXHAUSTED
        ]
    
    def is_retryable(self) -> bool:
        """Check if the delivery attempt can be retried."""
        return self.delivery_status in [
            DeliveryStatus.FAILED, 
            DeliveryStatus.TIMEOUT, 
            DeliveryStatus.RETRYING
        ]
        # Note: CIRCUIT_BREAKER_OPEN is not retryable - circuit breaker will retry when half-open
    
    def get_duration_ms(self) -> Optional[int]:
        """Get the attempt duration in milliseconds."""
        if self.completed_at and self.attempted_at:
            delta = self.completed_at - self.attempted_at
            return int(delta.total_seconds() * 1000)
        return self.response_time_ms


@dataclass
class WebhookDelivery:
    """Webhook delivery entity tracking delivery attempts and overall status.
    
    Represents a complete webhook delivery process including all retry attempts.
    Matches the webhook_deliveries table structure in both admin and tenant schemas.
    """
    
    # Identification
    id: WebhookDeliveryId
    webhook_endpoint_id: WebhookEndpointId
    webhook_event_id: EventId
    
    # Current delivery state
    current_attempt: int = 1
    overall_status: DeliveryStatus = DeliveryStatus.PENDING
    
    # Retry configuration (copied from webhook endpoint at creation time)
    max_attempts: int = 3
    base_backoff_seconds: int = 5
    backoff_multiplier: float = 2.0
    
    # Retry tracking
    next_retry_at: Optional[datetime] = None
    max_attempts_reached: bool = False
    
    # Attempt history
    attempts: List[WebhookDeliveryAttempt] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Post-init validation and normalization."""
        # Validate max_attempts
        if not (1 <= self.max_attempts <= 10):
            raise ValueError("max_attempts must be between 1 and 10")
        
        # Validate backoff configuration
        if not (1 <= self.base_backoff_seconds <= 3600):
            raise ValueError("base_backoff_seconds must be between 1 and 3600")
        
        if not (1.0 <= self.backoff_multiplier <= 5.0):
            raise ValueError("backoff_multiplier must be between 1.0 and 5.0")
        
        # Validate current_attempt
        if self.current_attempt < 1:
            raise ValueError("current_attempt must be >= 1")
        
        # Ensure timestamps are timezone-aware
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)
        
        if self.next_retry_at and self.next_retry_at.tzinfo is None:
            self.next_retry_at = self.next_retry_at.replace(tzinfo=timezone.utc)
    
    def add_attempt(self, attempt: WebhookDeliveryAttempt) -> None:
        """Add a delivery attempt to the history."""
        # Validate attempt number matches current attempt
        if attempt.attempt_number != self.current_attempt:
            raise ValueError(
                f"Attempt number {attempt.attempt_number} doesn't match current attempt {self.current_attempt}"
            )
        
        self.attempts.append(attempt)
        
        # Update overall status based on attempt result
        if attempt.is_successful():
            self.overall_status = DeliveryStatus.SUCCESS
            self.next_retry_at = None
        elif attempt.is_failed():
            if self.can_retry():
                self.overall_status = DeliveryStatus.RETRYING
                self.schedule_next_retry()
            else:
                self.overall_status = DeliveryStatus.FAILED
                self.max_attempts_reached = True
                self.next_retry_at = None
        
        # Mark attempt as completed
        attempt.mark_completed()
    
    def can_retry(self) -> bool:
        """Check if more retry attempts are allowed."""
        return self.current_attempt < self.max_attempts and not self.max_attempts_reached
    
    def get_next_retry_delay_seconds(self) -> int:
        """Calculate the delay for the next retry attempt."""
        if not self.can_retry():
            return 0
        
        # Exponential backoff: delay = base_delay * (multiplier ^ (attempt - 1))
        delay = self.base_backoff_seconds * (self.backoff_multiplier ** (self.current_attempt - 1))
        return min(int(delay), 3600)  # Cap at 1 hour
    
    def schedule_next_retry(self) -> None:
        """Schedule the next retry attempt."""
        if not self.can_retry():
            return
        
        delay_seconds = self.get_next_retry_delay_seconds()
        self.next_retry_at = datetime.now(timezone.utc).replace(
            second=0, microsecond=0
        ) + timedelta(seconds=delay_seconds)
        
        self.current_attempt += 1
    
    def cancel(self, reason: str = "Cancelled by user") -> None:
        """Cancel the webhook delivery."""
        self.overall_status = DeliveryStatus.CANCELLED
        self.next_retry_at = None
        self.max_attempts_reached = True
        
        # Add cancellation attempt if no attempts yet
        if not self.attempts:
            cancel_attempt = WebhookDeliveryAttempt(
                attempt_number=self.current_attempt,
                delivery_status=DeliveryStatus.CANCELLED,
                request_url="",  # Will be filled when actually attempting
                request_method="POST",
                error_message=reason,
                error_code="CANCELLED"
            )
            self.attempts.append(cancel_attempt)
    
    def is_ready_for_retry(self) -> bool:
        """Check if the delivery is ready for retry."""
        if not self.can_retry():
            return False
        
        if not self.next_retry_at:
            return False
        
        return datetime.now(timezone.utc) >= self.next_retry_at
    
    def get_latest_attempt(self) -> Optional[WebhookDeliveryAttempt]:
        """Get the most recent delivery attempt."""
        return self.attempts[-1] if self.attempts else None
    
    def get_successful_attempt(self) -> Optional[WebhookDeliveryAttempt]:
        """Get the first successful delivery attempt."""
        for attempt in self.attempts:
            if attempt.is_successful():
                return attempt
        return None
    
    def get_total_duration_ms(self) -> int:
        """Get total time spent on all delivery attempts."""
        if not self.attempts:
            return 0
        
        total_ms = 0
        for attempt in self.attempts:
            duration = attempt.get_duration_ms()
            if duration:
                total_ms += duration
        
        return total_ms
    
    def get_success_rate(self) -> float:
        """Get the success rate of delivery attempts (0.0 to 1.0)."""
        if not self.attempts:
            return 0.0
        
        successful_attempts = sum(1 for attempt in self.attempts if attempt.is_successful())
        return successful_attempts / len(self.attempts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert webhook delivery to dictionary representation."""
        return {
            "id": str(self.id.value),
            "webhook_endpoint_id": str(self.webhook_endpoint_id.value),
            "webhook_event_id": str(self.webhook_event_id.value),
            "current_attempt": self.current_attempt,
            "overall_status": self.overall_status.value,
            "max_attempts": self.max_attempts,
            "base_backoff_seconds": self.base_backoff_seconds,
            "backoff_multiplier": self.backoff_multiplier,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
            "max_attempts_reached": self.max_attempts_reached,
            "attempts": [
                {
                    "attempt_number": attempt.attempt_number,
                    "delivery_status": attempt.delivery_status.value,
                    "request_url": attempt.request_url,
                    "request_method": attempt.request_method,
                    "request_headers": attempt.request_headers,
                    "request_body": attempt.request_body,
                    "request_signature": attempt.request_signature,
                    "response_status_code": attempt.response_status_code,
                    "response_headers": attempt.response_headers,
                    "response_body": attempt.response_body,
                    "response_time_ms": attempt.response_time_ms,
                    "error_message": attempt.error_message,
                    "error_code": attempt.error_code,
                    "attempted_at": attempt.attempted_at.isoformat(),
                    "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else None,
                }
                for attempt in self.attempts
            ],
            "created_at": self.created_at.isoformat(),
        }