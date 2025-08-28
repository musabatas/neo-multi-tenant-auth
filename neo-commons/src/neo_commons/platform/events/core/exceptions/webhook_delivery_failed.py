"""Webhook delivery failure exception for platform events infrastructure.

This exception represents failures during webhook delivery in the platform event system.
It inherits from core EventHandlingError for DRY compliance.
"""

from typing import Any, Dict, Optional

from .....core.exceptions import EventHandlingError
from ..value_objects import WebhookEndpointId, WebhookDeliveryId, EventId


class WebhookDeliveryFailed(EventHandlingError):
    """Raised when platform webhook delivery fails.
    
    This exception represents failures in the platform webhook delivery process,
    including network errors, HTTP errors, timeout errors, and authentication failures.
    """
    
    def __init__(
        self,
        message: str,
        webhook_endpoint_id: Optional[WebhookEndpointId] = None,
        delivery_id: Optional[WebhookDeliveryId] = None,
        action_id: Optional[str] = None,
        event_id: Optional[EventId] = None,
        endpoint_url: Optional[str] = None,
        http_status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        attempt_count: Optional[int] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize webhook delivery failure exception.
        
        Args:
            message: Human-readable error message
            webhook_endpoint_id: ID of the webhook endpoint that failed
            delivery_id: ID of the delivery attempt
            action_id: ID of the action that triggered the webhook
            event_id: ID of the event that triggered the delivery
            endpoint_url: URL of the webhook endpoint
            http_status_code: HTTP status code from the webhook response
            response_body: Response body from the webhook (truncated if needed)
            attempt_count: Number of delivery attempts made
            error_code: Specific error code for the failure
            details: Additional details about the failure
        """
        # Build enhanced details
        enhanced_details = details or {}
        if webhook_endpoint_id:
            enhanced_details["webhook_endpoint_id"] = str(webhook_endpoint_id)
        if delivery_id:
            enhanced_details["delivery_id"] = str(delivery_id)
        if action_id:
            enhanced_details["action_id"] = action_id
        if event_id:
            enhanced_details["event_id"] = str(event_id)
        if endpoint_url:
            enhanced_details["endpoint_url"] = endpoint_url
        if http_status_code:
            enhanced_details["http_status_code"] = http_status_code
        if response_body:
            # Truncate response body to prevent excessive log sizes
            enhanced_details["response_body"] = response_body[:1000] + "..." if len(response_body) > 1000 else response_body
        if attempt_count:
            enhanced_details["attempt_count"] = attempt_count
            
        super().__init__(
            message=message,
            error_code=error_code or "WEBHOOK_DELIVERY_FAILED",
            details=enhanced_details
        )
        
        # Store platform-specific fields
        self.webhook_endpoint_id = webhook_endpoint_id
        self.delivery_id = delivery_id
        self.action_id = action_id
        self.event_id = event_id
        self.endpoint_url = endpoint_url
        self.http_status_code = http_status_code
        self.response_body = response_body
        self.attempt_count = attempt_count