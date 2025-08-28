"""
Tenant events router.

ONLY handles tenant-specific event management endpoints.
Provides event operations within tenant scope.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from ..models.requests import (
    DispatchEventRequest,
    RegisterWebhookRequest,
    DeliverWebhookRequest,
    SearchEventsRequest,
)
from ..models.responses import (
    EventResponse,
    WebhookDeliveryResponse,
    EventHistoryResponse,
    DeliveryStatsResponse,
    WebhookLogsResponse,
    SearchEventsResponse,
)
from ..dependencies import (
    get_event_service,
    get_webhook_service,
    get_current_user,
    get_tenant_context,
)

# Create tenant router with proper tags for OpenAPI organization
tenant_events_router = APIRouter(
    prefix="/tenant/events", 
    tags=["Events"],  # Following CLAUDE.md OpenAPI tag naming standards
    dependencies=[Depends(get_current_user), Depends(get_tenant_context)],  # Tenant authentication & context
)


@tenant_events_router.post(
    "/dispatch",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dispatch event in tenant scope",
    description="Dispatch events within the current tenant context"
)
async def dispatch_event(
    request: DispatchEventRequest,
    tenant_context=Depends(get_tenant_context),
    event_service=Depends(get_event_service)
) -> EventResponse:
    """Tenant-scoped event dispatch."""
    try:
        # Ensure tenant_id matches current tenant context
        request.tenant_id = tenant_context.tenant_id.value
        event = await event_service.dispatch_event(request.to_domain())
        return EventResponse.from_domain(event)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dispatch event: {str(e)}"
        )


@tenant_events_router.post(
    "/webhooks/register",
    response_model=WebhookDeliveryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register webhook endpoint",
    description="Register webhook endpoints for tenant events"
)
async def register_webhook(
    request: RegisterWebhookRequest,
    tenant_context=Depends(get_tenant_context),
    webhook_service=Depends(get_webhook_service)
) -> WebhookDeliveryResponse:
    """Register tenant webhook endpoints."""
    try:
        # Ensure tenant_id matches current tenant context
        request.tenant_id = tenant_context.tenant_id.value
        webhook = await webhook_service.register_webhook(request.to_domain())
        return WebhookDeliveryResponse.from_domain(webhook)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register webhook: {str(e)}"
        )


@tenant_events_router.post(
    "/webhooks/{webhook_id}/deliver",
    response_model=WebhookDeliveryResponse,
    summary="Trigger manual webhook delivery",
    description="Manually trigger webhook delivery for testing"
)
async def deliver_webhook(
    webhook_id: str,
    request: DeliverWebhookRequest,
    tenant_context=Depends(get_tenant_context),
    webhook_service=Depends(get_webhook_service)
) -> WebhookDeliveryResponse:
    """Manual webhook delivery for tenant testing."""
    try:
        # Ensure tenant_id and webhook_id match current context
        request.tenant_id = tenant_context.tenant_id.value
        request.webhook_endpoint_id = webhook_id
        
        delivery = await webhook_service.deliver_webhook(request.to_domain())
        return WebhookDeliveryResponse.from_domain(delivery)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deliver webhook: {str(e)}"
        )


@tenant_events_router.get(
    "/search",
    response_model=SearchEventsResponse,
    summary="Search tenant events",
    description="Search and filter events within tenant scope"
)
async def search_tenant_events(
    event_types: Optional[List[str]] = Query(None, description="Filter by event types"),
    event_status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    tenant_context=Depends(get_tenant_context),
    event_service=Depends(get_event_service)
) -> SearchEventsResponse:
    """Tenant-scoped event search."""
    try:
        search_request = SearchEventsRequest(
            tenant_id=tenant_context.tenant_id.value,
            event_types=event_types,
            event_status=event_status,
            page=page,
            page_size=page_size
        )
        
        results = await event_service.search_events(search_request.to_domain())
        return SearchEventsResponse.from_domain(results)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search events: {str(e)}"
        )


@tenant_events_router.get(
    "/{event_id}",
    response_model=EventResponse,
    summary="Get event details",
    description="Get detailed information about a specific event"
)
async def get_event(
    event_id: str,
    tenant_context=Depends(get_tenant_context),
    event_service=Depends(get_event_service)
) -> EventResponse:
    """Get tenant event details."""
    try:
        event = await event_service.get_event(
            event_id,
            tenant_context.tenant_id
        )
        
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        return EventResponse.from_domain(event)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get event: {str(e)}"
        )


@tenant_events_router.get(
    "/{event_id}/history",
    response_model=EventHistoryResponse,
    summary="Get event history",
    description="Get complete history of event changes and actions"
)
async def get_event_history(
    event_id: str,
    tenant_context=Depends(get_tenant_context),
    event_service=Depends(get_event_service)
) -> EventHistoryResponse:
    """Get tenant event history."""
    try:
        history = await event_service.get_event_history(
            event_id,
            tenant_context.tenant_id
        )
        
        return EventHistoryResponse.from_domain(history)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get event history: {str(e)}"
        )



@tenant_events_router.get(
    "/webhooks/logs",
    response_model=WebhookLogsResponse,
    summary="Get webhook delivery logs",
    description="Get webhook delivery logs for tenant"
)
async def get_webhook_logs(
    webhook_id: Optional[str] = Query(None, description="Filter by webhook ID"),
    status: Optional[str] = Query(None, description="Filter by delivery status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    tenant_context=Depends(get_tenant_context),
    webhook_service=Depends(get_webhook_service)
) -> WebhookLogsResponse:
    """Get tenant webhook delivery logs."""
    try:
        logs = await webhook_service.get_webhook_logs(
            tenant_id=tenant_context.tenant_id,
            webhook_id=webhook_id,
            status=status,
            page=page,
            page_size=page_size
        )
        return WebhookLogsResponse.from_domain(logs)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get webhook logs: {str(e)}"
        )