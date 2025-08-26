"""Delivery status enum for platform events infrastructure.

Platform-specific enum following maximum separation architecture.
This enum is pure platform infrastructure - used by all business features.

Extracted to platform/events following enterprise clean architecture patterns.
"""

from enum import Enum


class DeliveryStatus(Enum):
    """Webhook delivery status enumeration.
    
    Values match the database constraint in webhook_deliveries table:
    delivery_status IN ('pending', 'success', 'failed', 'timeout', 'retrying', 'cancelled')
    
    Pure platform infrastructure enum for webhook delivery tracking.
    """
    
    PENDING = "pending"      # Initial state, delivery not yet attempted
    SUCCESS = "success"      # Delivery completed successfully
    FAILED = "failed"        # Delivery failed due to error or bad response
    TIMEOUT = "timeout"      # Delivery timed out
    RETRYING = "retrying"    # Currently retrying delivery
    CANCELLED = "cancelled"  # Delivery was cancelled

    @property
    def is_final(self) -> bool:
        """Check if this status represents a final state (no more attempts)."""
        return self in {DeliveryStatus.SUCCESS, DeliveryStatus.CANCELLED}
    
    @property
    def is_failed(self) -> bool:
        """Check if this status represents a failure state."""
        return self in {DeliveryStatus.FAILED, DeliveryStatus.TIMEOUT}
    
    @property
    def is_retryable(self) -> bool:
        """Check if delivery can be retried from this status."""
        return self in {DeliveryStatus.FAILED, DeliveryStatus.TIMEOUT, DeliveryStatus.RETRYING}
    
    @property
    def is_successful(self) -> bool:
        """Check if this status represents successful delivery."""
        return self == DeliveryStatus.SUCCESS
    
    @classmethod
    def from_http_status(cls, status_code: int) -> "DeliveryStatus":
        """Determine delivery status from HTTP response status code."""
        if 200 <= status_code < 300:
            return cls.SUCCESS
        elif status_code == 408 or status_code == 504:  # Request Timeout or Gateway Timeout
            return cls.TIMEOUT
        else:
            return cls.FAILED