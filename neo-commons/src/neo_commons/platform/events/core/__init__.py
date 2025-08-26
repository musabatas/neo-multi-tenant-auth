"""Platform Events Core Infrastructure

Core domain entities, value objects, and protocols
for the events platform infrastructure.

Follows Clean Core architecture with only essential domain concepts
and no business logic or external dependencies.
"""

# Core domain entities
from .entities import (
    DomainEvent,
    EventAction,
    ActionExecution,
    WebhookEndpoint,
    WebhookDelivery
)

# Core value objects
from .value_objects import (
    EventId,
    ActionId,
    ActionStatus,
    HandlerType,
    ActionPriority,
    ExecutionMode,
    EventType,
    ActionCondition,
    WebhookEndpointId,
    WebhookDeliveryId,
    DeliveryStatus
)

# Platform protocols
from .protocols import (
    EventDispatcher,
    ActionExecutor,
    DeliveryService,
    EventRepository,
    ActionRepository
)

# Platform domain events
from .events import (
    EventDispatched,
    ActionExecuted,
    WebhookDelivered,
    ActionFailed,
    DeliveryFailed
)

# Platform exceptions
from .exceptions import (
    EventDispatchFailed,
    ActionExecutionFailed,
    WebhookDeliveryFailed,
    InvalidEventConfiguration
)

__all__ = [
    # Entities
    "DomainEvent",
    "EventAction", 
    "ActionExecution",
    "WebhookEndpoint",
    "WebhookDelivery",
    
    # Value Objects
    "EventId",
    "ActionId",
    "ActionStatus",
    "HandlerType",
    "ActionPriority",
    "ExecutionMode",
    "EventType",
    "ActionCondition",
    "WebhookEndpointId",
    "WebhookDeliveryId",
    "DeliveryStatus",
    
    # Protocols
    "EventDispatcher",
    "ActionExecutor",
    "DeliveryService",
    "EventRepository",
    "ActionRepository",
    
    # Platform Domain Events
    "EventDispatched",
    "ActionExecuted",
    "WebhookDelivered", 
    "ActionFailed",
    "DeliveryFailed",
    
    # Platform Exceptions
    "EventDispatchFailed",
    "ActionExecutionFailed",
    "WebhookDeliveryFailed",
    "InvalidEventConfiguration",
]