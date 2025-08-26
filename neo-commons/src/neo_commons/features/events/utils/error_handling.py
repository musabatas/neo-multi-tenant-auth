"""Error handling utilities for events feature following neo-commons patterns.

This module provides centralized error handling for webhook-related operations,
consistent with the patterns used in the organizations feature.
"""

import logging
from typing import Any, Optional, Union
from uuid import UUID

from ....core.exceptions import (
    EntityNotFoundError,
    EntityAlreadyExistsError, 
    DatabaseError,
    DomainError
)
from ....core.value_objects import (
    EventId,
    WebhookEndpointId,
    WebhookEventTypeId,
    WebhookDeliveryId
)


logger = logging.getLogger(__name__)


def handle_webhook_error(
    operation: str,
    entity_type: str,
    entity_id: Optional[Union[str, UUID, EventId, WebhookEndpointId, WebhookEventTypeId, WebhookDeliveryId]] = None,
    error: Optional[Exception] = None,
    context: Optional[dict] = None
) -> None:
    """Handle webhook-related errors with consistent logging and exception mapping.
    
    Args:
        operation: The operation being performed (e.g., 'create', 'update', 'delete')
        entity_type: Type of entity (e.g., 'webhook_endpoint', 'domain_event')
        entity_id: ID of the entity involved (optional)
        error: Original exception (optional)
        context: Additional context for logging (optional)
        
    Raises:
        Appropriate neo-commons exception based on the error type
    """
    context = context or {}
    entity_id_str = str(entity_id) if entity_id else "unknown"
    
    # Log the error with full context
    logger.error(
        f"Webhook {operation} failed for {entity_type} {entity_id_str}",
        extra={
            "operation": operation,
            "entity_type": entity_type,
            "entity_id": entity_id_str,
            "error_type": type(error).__name__ if error else "unknown",
            "error_message": str(error) if error else "unknown error",
            "context": context
        },
        exc_info=error
    )
    
    # Re-raise appropriate exception based on error type
    if error:
        if isinstance(error, (EntityNotFoundError, EntityAlreadyExistsError, DatabaseError, DomainError)):
            # Already a neo-commons exception, re-raise as-is
            raise error
        elif "not found" in str(error).lower():
            raise EntityNotFoundError(entity_type, entity_id_str)
        elif "already exists" in str(error).lower() or "duplicate" in str(error).lower():
            raise EntityAlreadyExistsError(entity_type, entity_id_str)
        elif "database" in str(error).lower() or "connection" in str(error).lower():
            raise DatabaseError(f"Database error during {operation} of {entity_type}: {error}")
        else:
            raise DomainError(f"Unexpected error during {operation} of {entity_type}: {error}")
    else:
        raise DomainError(f"Unknown error during {operation} of {entity_type} {entity_id_str}")


def handle_webhook_endpoint_error(
    operation: str,
    endpoint_id: Optional[WebhookEndpointId] = None,
    error: Optional[Exception] = None,
    context: Optional[dict] = None
) -> None:
    """Handle webhook endpoint specific errors."""
    handle_webhook_error(
        operation=operation,
        entity_type="webhook_endpoint",
        entity_id=endpoint_id,
        error=error,
        context=context
    )


def handle_domain_event_error(
    operation: str,
    event_id: Optional[EventId] = None,
    error: Optional[Exception] = None,
    context: Optional[dict] = None
) -> None:
    """Handle domain event specific errors."""
    handle_webhook_error(
        operation=operation,
        entity_type="domain_event",
        event_id=event_id,
        error=error,
        context=context
    )


def handle_webhook_delivery_error(
    operation: str,
    delivery_id: Optional[WebhookDeliveryId] = None,
    error: Optional[Exception] = None,
    context: Optional[dict] = None
) -> None:
    """Handle webhook delivery specific errors."""
    handle_webhook_error(
        operation=operation,
        entity_type="webhook_delivery",
        entity_id=delivery_id,
        error=error,
        context=context
    )


def handle_event_type_error(
    operation: str,
    type_id: Optional[WebhookEventTypeId] = None,
    error: Optional[Exception] = None,
    context: Optional[dict] = None
) -> None:
    """Handle webhook event type specific errors."""
    handle_webhook_error(
        operation=operation,
        entity_type="webhook_event_type",
        entity_id=type_id,
        error=error,
        context=context
    )