"""Platform Events Core Value Objects

Immutable value objects for the events platform infrastructure.
Each value object represents a domain concept with single responsibility.
Following maximum separation architecture with one value object per file.
"""

# Event-related identifiers moved from core/value_objects/identifiers.py
from .event_id import EventId

# Platform-specific enums
from .event_type import EventType

# Webhook infrastructure
from .webhook_endpoint_id import WebhookEndpointId
from .webhook_delivery_id import WebhookDeliveryId
from .delivery_status import DeliveryStatus

__all__ = [
    # Event identifiers
    "EventId", 
    
    # Platform enums
    "EventType",
    
    # Webhook infrastructure
    "WebhookEndpointId",
    "WebhookDeliveryId",
    "DeliveryStatus",
]