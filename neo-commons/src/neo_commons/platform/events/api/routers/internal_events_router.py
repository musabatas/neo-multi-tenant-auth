"""
Internal events router.

ONLY handles internal service-to-service event communication.
Provides high-performance endpoints for inter-service event operations.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from ..models.requests import (
    DispatchEventRequest,
    DeliverWebhookRequest,
)
from ..models.responses import (
    EventResponse,
    WebhookDeliveryResponse,
)
from ..dependencies import (
    get_event_service,
    get_webhook_service,
    verify_internal_service_token,
)

# Create internal router with proper tags for OpenAPI organization
internal_events_router = APIRouter(
    prefix="/internal/events",
    tags=["Events"],  # Following CLAUDE.md OpenAPI tag naming standards
    dependencies=[Depends(verify_internal_service_token)],  # Internal service authentication
)


@internal_events_router.post(
    "/dispatch/bulk",
    response_model=List[EventResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk dispatch events",
    description="High-performance bulk event dispatch for internal services"
)
async def bulk_dispatch_events(
    events: List[DispatchEventRequest],
    event_service=Depends(get_event_service)
) -> List[EventResponse]:
    """Bulk event dispatch for internal services."""
    try:
        # Convert to domain objects
        domain_events = [event.to_domain() for event in events]
        
        # Bulk dispatch with performance optimization
        dispatched_events = await event_service.bulk_dispatch_events(domain_events)
        
        return [EventResponse.from_domain(event) for event in dispatched_events]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk dispatch events: {str(e)}"
        )


@internal_events_router.post(
    "/dispatch/async",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Asynchronous event dispatch",
    description="Fire-and-forget event dispatch for high-throughput scenarios"
)
async def async_dispatch_event(
    request: DispatchEventRequest,
    event_service=Depends(get_event_service)
) -> JSONResponse:
    """Asynchronous event dispatch for internal services."""
    try:
        # Queue event for async processing
        event_id = await event_service.queue_event_for_dispatch(request.to_domain())
        
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "message": "Event queued for processing",
                "event_id": event_id,
                "status": "queued"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue event: {str(e)}"
        )


@internal_events_router.post(
    "/webhooks/deliver/retry",
    response_model=WebhookDeliveryResponse,
    summary="Retry webhook delivery",
    description="Internal retry mechanism for failed webhook deliveries"
)
async def retry_webhook_delivery(
    delivery_id: str,
    force_retry: bool = False,
    webhook_service=Depends(get_webhook_service)
) -> WebhookDeliveryResponse:
    """Retry webhook delivery for internal failure handling."""
    try:
        delivery = await webhook_service.retry_webhook_delivery(
            delivery_id,
            force_retry=force_retry
        )
        
        if not delivery:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook delivery not found"
            )
        
        return WebhookDeliveryResponse.from_domain(delivery)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry webhook delivery: {str(e)}"
        )


# Action execution endpoints moved to platform/actions module


@internal_events_router.get(
    "/health/detailed",
    summary="Detailed system health",
    description="Comprehensive health check for internal monitoring"
)
async def get_detailed_health(
    event_service=Depends(get_event_service),
    webhook_service=Depends(get_webhook_service)
) -> JSONResponse:
    """Detailed health check for internal monitoring systems."""
    try:
        health_data = {
            "event_service": await event_service.get_health_status(),
            "webhook_service": await webhook_service.get_health_status(),
            "timestamp": "2024-01-15T15:00:00Z",
            "version": "1.0.0"
        }
        
        # Determine overall health
        all_healthy = all(
            service.get("status") == "healthy" 
            for service in health_data.values()
            if isinstance(service, dict) and "status" in service
        )
        
        health_data["overall_status"] = "healthy" if all_healthy else "degraded"
        
        status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        
        return JSONResponse(
            status_code=status_code,
            content=health_data
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "overall_status": "unhealthy",
                "error": str(e),
                "timestamp": "2024-01-15T15:00:00Z"
            }
        )


@internal_events_router.get(
    "/metrics/performance",
    summary="Performance metrics",
    description="Real-time performance metrics for internal monitoring"
)
async def get_performance_metrics(
    event_service=Depends(get_event_service)
) -> JSONResponse:
    """Performance metrics for internal monitoring."""
    try:
        metrics = await event_service.get_performance_metrics()
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=metrics
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance metrics: {str(e)}"
        )


@internal_events_router.post(
    "/system/maintenance/start",
    summary="Start maintenance mode",
    description="Put event system into maintenance mode"
)
async def start_maintenance_mode(
    reason: str,
    estimated_duration_minutes: Optional[int] = None,
    event_service=Depends(get_event_service)
) -> JSONResponse:
    """Start maintenance mode for the event system."""
    try:
        await event_service.start_maintenance_mode(
            reason=reason,
            estimated_duration_minutes=estimated_duration_minutes
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "maintenance_mode_started",
                "reason": reason,
                "estimated_duration_minutes": estimated_duration_minutes
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start maintenance mode: {str(e)}"
        )


@internal_events_router.post(
    "/system/maintenance/stop",
    summary="Stop maintenance mode",
    description="Exit maintenance mode and resume normal operations"
)
async def stop_maintenance_mode(
    event_service=Depends(get_event_service)
) -> JSONResponse:
    """Stop maintenance mode."""
    try:
        await event_service.stop_maintenance_mode()
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "maintenance_mode_stopped",
                "message": "System resumed normal operations"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop maintenance mode: {str(e)}"
        )