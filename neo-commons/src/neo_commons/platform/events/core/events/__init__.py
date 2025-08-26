"""Platform Events Domain Events

Domain events that represent platform infrastructure occurrences.
Each event represents a single platform operation with single responsibility.

Maximum separation architecture - each file contains exactly one domain event class.
Pure platform infrastructure events - represent platform operations, not business logic.
"""

# Platform infrastructure domain events
from .event_dispatched import EventDispatched
from .action_executed import ActionExecuted
from .webhook_delivered import WebhookDelivered
from .action_failed import ActionFailed
from .delivery_failed import DeliveryFailed

__all__ = [
    "EventDispatched",
    "ActionExecuted", 
    "WebhookDelivered",
    "ActionFailed",
    "DeliveryFailed",
]