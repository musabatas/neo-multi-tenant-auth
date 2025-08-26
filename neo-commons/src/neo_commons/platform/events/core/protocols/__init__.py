"""Platform Events Core Protocols

Protocol contracts for the events platform infrastructure.
Each protocol defines a single responsibility interface for dependency injection.
"""

from .event_dispatcher import EventDispatcher
from .action_executor import ActionExecutor
from .delivery_service import DeliveryService
from .event_repository import EventRepository
from .action_repository import ActionRepository

__all__ = [
    "EventDispatcher",
    "ActionExecutor",
    "DeliveryService",
    "EventRepository",
    "ActionRepository",
]