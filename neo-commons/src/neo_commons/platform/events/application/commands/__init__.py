"""Platform events application commands.

Commands handle write operations in the platform events system.
Following CQRS pattern - commands are separated from queries.

Each command file has single responsibility:
- dispatch_event.py: ONLY event dispatching logic
- deliver_webhook.py: ONLY webhook delivery logic
- register_webhook.py: ONLY webhook registration logic
- archive_event.py: ONLY event archival logic

Action-related commands (including configure_handler.py) have been moved to platform/actions module.
"""

# Import commands as they are created
from .dispatch_event import DispatchEventCommand, DispatchEventData, DispatchEventResult
from .deliver_webhook import DeliverWebhookCommand, DeliverWebhookData, DeliverWebhookResult
from .register_webhook import RegisterWebhookCommand, RegisterWebhookData, RegisterWebhookResult
from .archive_event import ArchiveEventCommand, ArchiveEventData, ArchiveEventResult

# Import configure_handler from platform/actions where it belongs
from neo_commons.platform.actions.application.commands.configure_handler import (
    ConfigureHandlerCommand, 
    ConfigureHandlerData, 
    ConfigureHandlerResult
)

__all__ = [
    "DispatchEventCommand",
    "DispatchEventData", 
    "DispatchEventResult",
    "DeliverWebhookCommand",
    "DeliverWebhookData",
    "DeliverWebhookResult",
    "RegisterWebhookCommand",
    "RegisterWebhookData",
    "RegisterWebhookResult",
    "ConfigureHandlerCommand",
    "ConfigureHandlerData",
    "ConfigureHandlerResult",
    "ArchiveEventCommand",
    "ArchiveEventData",
    "ArchiveEventResult",
]