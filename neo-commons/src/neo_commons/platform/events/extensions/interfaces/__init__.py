"""
Extension interface exports.

ONLY handles extension point interfaces and contracts.
"""

from .event_extension import EventExtension
from .webhook_extension import WebhookExtension
from .notification_extension import NotificationExtension

__all__ = [
    "EventExtension",
    "WebhookExtension",
    "NotificationExtension",
]