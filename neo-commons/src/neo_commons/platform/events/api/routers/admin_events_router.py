"""
Admin events router.

ONLY handles platform administrator event management endpoints.
Provides administrative control over the entire event system.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from ..models.requests import (
    DispatchEventRequest,
    RegisterWebhookRequest,
    ConfigureHandlerRequest,
    ArchiveEventRequest,
    SearchEventsRequest,
)
from ..models.responses import (
    EventResponse,
    WebhookDeliveryResponse,
    DeliveryStatsResponse,
    SearchEventsResponse,
)
from ..dependencies import (
    get_event_service,
    get_webhook_service,
    get_current_admin_user,
)

# Create admin router with proper tags for OpenAPI organization
admin_events_router = APIRouter(
    prefix="/admin/events",
    tags=["Events"],  # Following CLAUDE.md OpenAPI tag naming standards
    dependencies=[Depends(get_current_admin_user)],  # Admin authentication required
)


@admin_events_router.post(
    "/dispatch",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dispatch event for any tenant",
    description="Dispatch events on behalf of any tenant (admin privilege)"
)
async def dispatch_event(
    request: DispatchEventRequest,
    event_service=Depends(get_event_service)
) -> EventResponse:
    """Admin-only event dispatch with cross-tenant capability."""
    try:
        # Admin can dispatch events for any tenant
        event = await event_service.dispatch_event(request.to_domain())
        return EventResponse.from_domain(event)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dispatch event: {str(e)}"
        )


@admin_events_router.get(
    "/search",
    response_model=SearchEventsResponse,
    summary="Search events across all tenants",
    description="Search and filter events across the entire platform"
)
async def search_events_cross_tenant(
    event_types: Optional[List[str]] = Query(None, description="Filter by event types"),
    event_status: Optional[str] = Query(None, description="Filter by status"),
    tenant_id: Optional[str] = Query(None, description="Filter by specific tenant"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    event_service=Depends(get_event_service)
) -> SearchEventsResponse:
    """Cross-tenant event search for platform administrators."""
    try:
        # Build search request with admin privileges
        search_request = SearchEventsRequest(
            tenant_id=tenant_id or "admin_search",  # Special tenant for admin searches
            event_types=event_types,
            event_status=event_status,
            page=page,
            page_size=page_size
        )
        
        results = await event_service.search_events_admin(search_request.to_domain())
        return SearchEventsResponse.from_domain(results)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search events: {str(e)}"
        )




@admin_events_router.post(
    "/events/{event_id}/archive",
    response_model=EventResponse,
    summary="Archive event",
    description="Archive events from any tenant"
)
async def archive_event(
    event_id: str,
    request: ArchiveEventRequest,
    event_service=Depends(get_event_service)
) -> EventResponse:
    """Archive events with admin privileges."""
    try:
        # Override event_id from path parameter
        request.event_id = event_id
        event = await event_service.archive_event(request.to_domain())
        return EventResponse.from_domain(event)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive event: {str(e)}"
        )


