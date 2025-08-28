"""Platform Events Core Exceptions

Domain exceptions for the events platform infrastructure.
Each exception represents a specific error condition with single responsibility.
"""

from .event_dispatch_failed import EventDispatchFailed
from .webhook_delivery_failed import WebhookDeliveryFailed
from .invalid_event_configuration import InvalidEventConfiguration
from .event_validation_failed import EventValidationFailed
from .event_handler_failed import EventHandlerFailed

__all__ = [
    "EventDispatchFailed",
    "WebhookDeliveryFailed",
    "InvalidEventConfiguration",
    "EventValidationFailed",
    "EventHandlerFailed",
]