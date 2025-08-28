"""Platform Events Core Infrastructure

Core domain entities, value objects, and protocols
for the events platform infrastructure.

Follows Clean Core architecture with only essential domain concepts
and no business logic or external dependencies.
"""

# Core domain entities
from .entities import (
    DomainEvent,
    WebhookEndpoint,
    WebhookDelivery
)

# Core value objects
from .value_objects import (
    EventId,
    EventType,
    WebhookEndpointId,
    WebhookDeliveryId,
    DeliveryStatus
)

# Platform protocols
from .protocols import (
    EventDispatcher,
    DeliveryService,
    EventRepository,
    NotificationService,
    WebhookRepository,
    MessageQueue
)

# Platform domain events
from .events import (
    EventDispatched,
    WebhookDelivered,
    DeliveryFailed
)

# Platform exceptions
from .exceptions import (
    EventDispatchFailed,
    WebhookDeliveryFailed,
    InvalidEventConfiguration,
    EventValidationFailed,
    EventHandlerFailed
)

__all__ = [
    # Entities
    "DomainEvent",
    "WebhookEndpoint",
    "WebhookDelivery",
    
    # Value Objects
    "EventId",
    "EventType",
    "WebhookEndpointId",
    "WebhookDeliveryId",
    "DeliveryStatus",
    
    # Protocols
    "EventDispatcher",
    "DeliveryService",
    "EventRepository",
    "NotificationService",
    "WebhookRepository",
    "MessageQueue",
    
    # Platform Domain Events
    "EventDispatched",
    "WebhookDelivered", 
    "DeliveryFailed",
    
    # Platform Exceptions
    "EventDispatchFailed",
    "WebhookDeliveryFailed",
    "InvalidEventConfiguration",
    "EventValidationFailed",
    "EventHandlerFailed",
]