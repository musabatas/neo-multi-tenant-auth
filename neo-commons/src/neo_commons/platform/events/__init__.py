"""
Platform Events Infrastructure

Pure platform infrastructure providing event dispatching, action execution, 
and delivery services to all business features.

Following enterprise patterns for 
maximum separation and single responsibility.
"""

# Import everything from core to provide unified API
from .core import (
    # Entities
    DomainEvent,
    WebhookEndpoint,
    WebhookDelivery,
    
    # Value Objects
    EventId,
    EventType,
    WebhookEndpointId,
    WebhookDeliveryId,
    DeliveryStatus,
    
    # Protocols
    EventDispatcher,
    DeliveryService,
    EventRepository,
    NotificationService,
    WebhookRepository,
    MessageQueue,
    
    # Platform Domain Events
    EventDispatched,
    WebhookDelivered,
    DeliveryFailed,
    
    # Platform Exceptions
    EventDispatchFailed,
    WebhookDeliveryFailed,
    InvalidEventConfiguration,
    EventValidationFailed,
    EventHandlerFailed,
)

# Note: Application layer imports disabled until action dependencies are resolved
# from .application import (
#     # Commands (write operations) - temporarily commented out due to action dependencies
#     # DispatchEventCommand,
#     # DispatchEventData, 
#     # DispatchEventResult,
#     # ...
# )

# Note: Action-related commands, queries, and validators have been moved to platform/actions module

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
    
    # Note: Application layer exports temporarily disabled until action dependencies are resolved
    # These will be re-enabled once the action functionality is properly separated
    
    # Application Commands, Queries, Validators, and Services will be available after cleanup is complete
    
    # Note: Action-related exports have been moved to platform/actions module
]