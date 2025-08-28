"""
Public events router.

ONLY handles public/unauthenticated event-related endpoints.
Provides limited read-only access for integration and monitoring.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse

from ..dependencies import (
    verify_public_api_key,  # Optional API key verification
)

# Create public router with proper tags for OpenAPI organization
public_events_router = APIRouter(
    prefix="/public/events",
    tags=["Events"],  # Following CLAUDE.md OpenAPI tag naming standards
)


@public_events_router.get(
    "/health",
    summary="Public health check",
    description="Basic health status of the event system (no authentication required)"
)
async def get_public_health() -> JSONResponse:
    """Public health check endpoint."""
    try:
        # Basic health check without sensitive information
        health_data = {
            "status": "healthy",
            "service": "neo-events",
            "version": "1.0.0",
            "timestamp": "2024-01-15T15:00:00Z"
        }
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=health_data
        )
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy", 
                "service": "neo-events",
                "timestamp": "2024-01-15T15:00:00Z"
            }
        )




@public_events_router.get(
    "/webhook/verify",
    summary="Webhook signature verification helper",
    description="Helper endpoint for webhook signature verification"
)
async def webhook_signature_helper(
    payload: str = Query(..., description="Webhook payload"),
    signature: str = Query(..., description="Received signature"),
    secret: str = Query(..., description="Webhook secret")
) -> JSONResponse:
    """Helper endpoint for webhook signature verification."""
    try:
        # Import webhook utilities
        from ....infrastructure.adapters.http_webhook_adapter import HttpWebhookAdapter
        
        # Verify signature
        is_valid = HttpWebhookAdapter.verify_signature(
            payload=payload.encode(),
            signature=signature,
            secret=secret
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "signature_valid": is_valid,
                "message": "Signature verified" if is_valid else "Signature invalid"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Signature verification failed: {str(e)}"
        )


@public_events_router.get(
    "/docs/integration",
    summary="Integration documentation",
    description="Integration guide and examples for developers"
)
async def get_integration_docs() -> JSONResponse:
    """Integration documentation for developers."""
    docs = {
        "webhook_integration": {
            "signature_verification": {
                "algorithm": "HMAC-SHA256",
                "header": "X-Neo-Signature",
                "format": "sha256={signature}"
            },
            "retry_policy": {
                "attempts": 3,
                "backoff": "exponential",
                "timeout_seconds": 30
            }
        },
        "event_types": {
            "user": ["user.created", "user.updated", "user.deleted"],
            "organization": ["organization.created", "organization.updated"],
            "tenant": ["tenant.created", "tenant.activated", "tenant.suspended"]
        },
        "payload_structure": {
            "event_id": "string",
            "event_type": "string",
            "tenant_id": "string",
            "timestamp": "ISO8601",
            "payload": "object",
            "metadata": "object"
        },
        "rate_limits": {
            "webhook_delivery": "1000 requests/minute per tenant",
            "api_calls": "100 requests/minute per API key"
        }
    }
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=docs
    )


