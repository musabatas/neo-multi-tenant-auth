"""
Event service dependencies.

ONLY handles dependency injection for event-related services.
Action-related dependencies have been moved to platform/actions module.
Monitoring dependencies will be implemented at neo-commons level.
"""

from typing import Annotated
from fastapi import Depends

# Import platform container for service resolution
from neo_commons.platform.container import get_container
from ...application.services.event_dispatcher import EventDispatcherService
from ...application.services.webhook_delivery import WebhookDeliveryService


async def get_event_service() -> EventDispatcherService:
    """
    Get event service instance from container.
    
    Provides access to event dispatching and management operations.
    """
    container = get_container()
    return await container.get(EventDispatcherService)


async def get_webhook_service() -> WebhookDeliveryService:
    """
    Get webhook service instance from container.
    
    Provides access to webhook registration and delivery operations.
    """
    container = get_container()
    return await container.get(WebhookDeliveryService)


# Type aliases for dependency injection
EventServiceDep = Annotated[EventDispatcherService, Depends(get_event_service)]
WebhookServiceDep = Annotated[WebhookDeliveryService, Depends(get_webhook_service)]