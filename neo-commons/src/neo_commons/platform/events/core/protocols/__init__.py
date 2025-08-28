"""Platform Events Core Protocols

Protocol contracts for the events platform infrastructure.
Each protocol defines a single responsibility interface for dependency injection.
"""

from .event_dispatcher import EventDispatcher
from .delivery_service import DeliveryService
from .event_repository import EventRepository
from .notification_service import NotificationService
from .webhook_repository import WebhookRepository
from .message_queue import MessageQueue

__all__ = [
    "EventDispatcher",
    "DeliveryService",
    "EventRepository",
    "NotificationService",
    "WebhookRepository",
    "MessageQueue",
]