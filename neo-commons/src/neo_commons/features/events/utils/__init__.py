"""Events utilities module."""

from .validation import WebhookValidationRules
from .error_handling import handle_webhook_error
from .queries import (
    # Webhook endpoints queries
    WEBHOOK_ENDPOINT_INSERT,
    WEBHOOK_ENDPOINT_UPDATE,
    WEBHOOK_ENDPOINT_GET_BY_ID,
    WEBHOOK_ENDPOINT_LIST_ACTIVE,
    WEBHOOK_ENDPOINT_DELETE,
    
    # Domain events queries
    DOMAIN_EVENT_INSERT,
    DOMAIN_EVENT_GET_BY_ID,
    DOMAIN_EVENT_GET_UNPROCESSED,
    DOMAIN_EVENT_MARK_PROCESSED,
    
    # Webhook deliveries queries
    WEBHOOK_DELIVERY_INSERT,
    WEBHOOK_DELIVERY_UPDATE,
    WEBHOOK_DELIVERY_GET_PENDING_RETRIES,
)

__all__ = [
    "WebhookValidationRules",
    "handle_webhook_error",
    # Webhook endpoints queries
    "WEBHOOK_ENDPOINT_INSERT",
    "WEBHOOK_ENDPOINT_UPDATE", 
    "WEBHOOK_ENDPOINT_GET_BY_ID",
    "WEBHOOK_ENDPOINT_LIST_ACTIVE",
    "WEBHOOK_ENDPOINT_DELETE",
    # Domain events queries
    "DOMAIN_EVENT_INSERT",
    "DOMAIN_EVENT_GET_BY_ID",
    "DOMAIN_EVENT_GET_UNPROCESSED",
    "DOMAIN_EVENT_MARK_PROCESSED",
    # Webhook deliveries queries
    "WEBHOOK_DELIVERY_INSERT",
    "WEBHOOK_DELIVERY_UPDATE",
    "WEBHOOK_DELIVERY_GET_PENDING_RETRIES",
]