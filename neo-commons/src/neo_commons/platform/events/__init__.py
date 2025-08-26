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
    EventAction,
    ActionExecution,
    WebhookEndpoint,
    WebhookDelivery,
    
    # Value Objects
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
    DeliveryStatus,
    
    # Protocols
    EventDispatcher,
    ActionExecutor,
    DeliveryService,
    EventRepository,
    ActionRepository,
    
    # Platform Domain Events
    EventDispatched,
    ActionExecuted,
    WebhookDelivered,
    ActionFailed,
    DeliveryFailed,
    
    # Platform Exceptions
    EventDispatchFailed,
    ActionExecutionFailed,
    WebhookDeliveryFailed,
    InvalidEventConfiguration,
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