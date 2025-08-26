"""Platform Events Core Exceptions

Domain exceptions for the events platform infrastructure.
Each exception represents a specific error condition with single responsibility.
"""

from .event_dispatch_failed import EventDispatchFailed
from .action_execution_failed import ActionExecutionFailed
from .webhook_delivery_failed import WebhookDeliveryFailed
from .invalid_event_configuration import InvalidEventConfiguration

__all__ = [
    "EventDispatchFailed",
    "ActionExecutionFailed",
    "WebhookDeliveryFailed",
    "InvalidEventConfiguration",
]