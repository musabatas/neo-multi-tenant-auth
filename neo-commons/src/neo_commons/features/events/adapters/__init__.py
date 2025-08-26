"""Event feature adapters.

Contains adapters for external services like HTTP webhook delivery.
"""

from .http_webhook_adapter import HttpWebhookAdapter

__all__ = [
    "HttpWebhookAdapter",
]