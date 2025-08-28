"""Platform events application handlers.

Handlers respond to platform domain events.
Following event-driven architecture patterns.

Each handler file has single responsibility:
- event_dispatched_handler.py: ONLY dispatch event handling  
- webhook_delivered_handler.py: ONLY delivery event handling

Note: Action-related handlers moved to platform/actions module:
- action_executed_handler.py: Moved to platform/actions
- action_failed_handler.py: Moved to platform/actions
"""

# Import handlers as they are created
from .event_dispatched_handler import EventDispatchedHandler, EventDispatchedHandlerResult
# from .action_executed_handler import ActionExecutedHandler, ActionExecutedHandlerResult  # Moved to platform/actions
from .webhook_delivered_handler import WebhookDeliveredHandler, WebhookDeliveredHandlerResult
# from .action_failed_handler import ActionFailedHandler, ActionFailedHandlerResult  # Moved to platform/actions

__all__ = [
    "EventDispatchedHandler",
    "EventDispatchedHandlerResult",
    # Action handlers moved to platform/actions module
    "WebhookDeliveredHandler", 
    "WebhookDeliveredHandlerResult",
]