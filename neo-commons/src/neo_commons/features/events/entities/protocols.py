"""Protocol interfaces for event-specific operations.

Defines contracts for event repositories and services following 
protocol-based dependency injection patterns used across neo-commons.
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from uuid import UUID

from ....core.value_objects import (
    EventId, 
    WebhookEndpointId, 
    WebhookEventTypeId, 
    WebhookDeliveryId,
    WebhookSubscriptionId,
    UserId,
    ActionId,
    ActionExecutionId
)
from .domain_event import DomainEvent
from .webhook_endpoint import WebhookEndpoint
from .webhook_event_type import WebhookEventType
from .webhook_delivery import WebhookDelivery
from .webhook_subscription import WebhookSubscription


# Repository Protocols following organizations pattern
@runtime_checkable
class EventRepository(Protocol):
    """Protocol for domain event repository operations."""
    
    @abstractmethod
    async def save(self, event: DomainEvent) -> DomainEvent:
        """Save a domain event."""
        ...
    
    @abstractmethod
    async def get_by_id(self, event_id: EventId) -> Optional[DomainEvent]:
        """Get a domain event by ID."""
        ...
    
    @abstractmethod
    async def get_by_aggregate(self, aggregate_type: str, aggregate_id: UUID) -> List[DomainEvent]:
        """Get all events for a specific aggregate."""
        ...
    
    @abstractmethod
    async def get_unprocessed(self, limit: int = 100) -> List[DomainEvent]:
        """Get unprocessed events for webhook delivery."""
        ...
    
    @abstractmethod
    async def get_unprocessed_paginated(self, limit: int = 100, offset: int = 0) -> List[DomainEvent]:
        """Get unprocessed events with pagination for streaming processing."""
        ...
    
    @abstractmethod
    async def get_unprocessed_for_update(
        self, 
        limit: int = 100,
        skip_locked: bool = True,
        select_columns: Optional[List[str]] = None
    ) -> List[DomainEvent]:
        """Get unprocessed events with FOR UPDATE lock for high-concurrency scenarios.
        
        Args:
            limit: Maximum number of events to fetch
            skip_locked: Use SKIP LOCKED to avoid blocking on locked rows
            select_columns: Specific columns to select for performance optimization
            
        Returns:
            List of unprocessed events with database locks
        """
        ...
    
    @abstractmethod
    async def mark_as_processed(self, event_id: EventId) -> bool:
        """Mark an event as processed for webhook delivery."""
        ...
    
    @abstractmethod
    async def mark_multiple_as_processed(self, event_ids: List[EventId]) -> int:
        """Mark multiple events as processed for webhook delivery.
        
        Args:
            event_ids: List of event IDs to mark as processed
            
        Returns:
            Number of events successfully marked as processed
        """
        ...
    
    @abstractmethod
    async def mark_multiple_as_processed_bulk(
        self, 
        event_ids: List[EventId],
        batch_size: int = 100
    ) -> int:
        """Bulk mark multiple events as processed with optimized batch operations.
        
        Args:
            event_ids: List of event IDs to mark as processed
            batch_size: Size of each batch for bulk operations
            
        Returns:
            Number of events successfully marked as processed
        """
        ...
    
    @abstractmethod
    async def get_by_correlation_id(self, correlation_id: UUID) -> List[DomainEvent]:
        """Get events by correlation ID for tracking related events."""
        ...
    
    @abstractmethod
    async def get_by_context(self, context_id: UUID, limit: int = 100) -> List[DomainEvent]:
        """Get events by context ID (organization, team, etc.)."""
        ...
    
    @abstractmethod
    async def count_unprocessed(self) -> int:
        """Count total unprocessed events for streaming processing statistics."""
        ...
    
    @abstractmethod
    async def count_processing(self) -> int:
        """Count events currently being processed for streaming processing statistics."""
        ...


@runtime_checkable
class WebhookEndpointRepository(Protocol):
    """Protocol for webhook endpoint repository operations."""
    
    @abstractmethod
    async def save(self, endpoint: WebhookEndpoint) -> WebhookEndpoint:
        """Save a webhook endpoint."""
        ...
    
    @abstractmethod
    async def get_by_id(self, endpoint_id: WebhookEndpointId) -> Optional[WebhookEndpoint]:
        """Get a webhook endpoint by ID."""
        ...
    
    @abstractmethod
    async def get_by_context(self, context_id: UUID, active_only: bool = True) -> List[WebhookEndpoint]:
        """Get webhook endpoints by context ID."""
        ...
    
    @abstractmethod
    async def get_active_endpoints(self) -> List[WebhookEndpoint]:
        """Get all active webhook endpoints."""
        ...
    
    @abstractmethod
    async def update(self, endpoint: WebhookEndpoint) -> WebhookEndpoint:
        """Update webhook endpoint."""
        ...
    
    @abstractmethod
    async def delete(self, endpoint_id: WebhookEndpointId) -> bool:
        """Delete a webhook endpoint."""
        ...
    
    @abstractmethod
    async def update_last_used(self, endpoint_id: WebhookEndpointId) -> bool:
        """Update the last used timestamp for an endpoint."""
        ...


@runtime_checkable
class WebhookEventTypeRepository(Protocol):
    """Protocol for webhook event type repository operations."""
    
    @abstractmethod
    async def save(self, event_type: WebhookEventType) -> WebhookEventType:
        """Save a webhook event type."""
        ...
    
    @abstractmethod
    async def get_by_id(self, type_id: WebhookEventTypeId) -> Optional[WebhookEventType]:
        """Get a webhook event type by ID."""
        ...
    
    @abstractmethod
    async def get_by_event_type(self, event_type: str) -> Optional[WebhookEventType]:
        """Get a webhook event type by event type string."""
        ...
    
    @abstractmethod
    async def get_by_category(self, category: str, enabled_only: bool = True) -> List[WebhookEventType]:
        """Get webhook event types by category."""
        ...
    
    @abstractmethod
    async def get_enabled_types(self) -> List[WebhookEventType]:
        """Get all enabled webhook event types."""
        ...
    
    @abstractmethod
    async def delete(self, type_id: WebhookEventTypeId) -> bool:
        """Delete a webhook event type."""
        ...


@runtime_checkable
class WebhookDeliveryRepository(Protocol):
    """Protocol for webhook delivery repository operations."""
    
    @abstractmethod
    async def save(self, delivery: WebhookDelivery) -> WebhookDelivery:
        """Save a webhook delivery."""
        ...
    
    @abstractmethod
    async def get_by_id(self, delivery_id: WebhookDeliveryId) -> Optional[WebhookDelivery]:
        """Get a webhook delivery by ID."""
        ...
    
    @abstractmethod
    async def get_pending_retries(self, limit: int = 100) -> List[WebhookDelivery]:
        """Get webhook deliveries that are ready for retry."""
        ...
    
    @abstractmethod
    async def get_by_endpoint(self, endpoint_id: WebhookEndpointId, limit: int = 100) -> List[WebhookDelivery]:
        """Get webhook deliveries for a specific endpoint."""
        ...
    
    @abstractmethod
    async def get_by_event(self, event_id: EventId) -> List[WebhookDelivery]:
        """Get webhook deliveries for a specific event."""
        ...
    
    @abstractmethod
    async def get_delivery_stats(self, endpoint_id: WebhookEndpointId, 
                                days: int = 7) -> Dict[str, Any]:
        """Get delivery statistics for an endpoint."""
        ...


@runtime_checkable
class WebhookSubscriptionRepository(Protocol):
    """Protocol for webhook subscription repository operations."""
    
    @abstractmethod
    async def save(self, subscription: WebhookSubscription) -> WebhookSubscription:
        """Save a webhook subscription."""
        ...
    
    @abstractmethod
    async def get_by_id(self, subscription_id: WebhookSubscriptionId) -> Optional[WebhookSubscription]:
        """Get a webhook subscription by ID."""
        ...
    
    @abstractmethod
    async def get_by_endpoint_id(self, endpoint_id: WebhookEndpointId, 
                                active_only: bool = True) -> List[WebhookSubscription]:
        """Get webhook subscriptions by endpoint ID."""
        ...
    
    @abstractmethod
    async def get_by_event_type(self, event_type: str, 
                               active_only: bool = True) -> List[WebhookSubscription]:
        """Get webhook subscriptions by event type."""
        ...
    
    @abstractmethod
    async def get_by_context(self, context_id: UUID, 
                            active_only: bool = True) -> List[WebhookSubscription]:
        """Get webhook subscriptions by context ID."""
        ...
    
    @abstractmethod
    async def get_active_subscriptions(self) -> List[WebhookSubscription]:
        """Get all active webhook subscriptions."""
        ...
    
    @abstractmethod
    async def get_matching_subscriptions(self, event_type: str, 
                                       context_id: Optional[UUID] = None) -> List[WebhookSubscription]:
        """Get subscriptions that match the given event type and context."""
        ...
    
    @abstractmethod
    async def get_matching_subscriptions_optimized(
        self,
        event_type: str,
        context_id: Optional[UUID] = None,
        select_columns: Optional[List[str]] = None,
        use_index_only: bool = True
    ) -> List[WebhookSubscription]:
        """Get matching subscriptions with database query optimizations.
        
        Args:
            event_type: Event type to match
            context_id: Optional context filter
            select_columns: Specific columns to select for performance
            use_index_only: Prefer index-only scans when possible
            
        Returns:
            List of matching subscriptions optimized for performance
        """
        ...
    
    @abstractmethod
    async def update(self, subscription: WebhookSubscription) -> WebhookSubscription:
        """Update webhook subscription."""
        ...
    
    @abstractmethod
    async def delete(self, subscription_id: WebhookSubscriptionId) -> bool:
        """Delete a webhook subscription."""
        ...
    
    @abstractmethod
    async def update_last_triggered(self, subscription_id: WebhookSubscriptionId) -> bool:
        """Update the last triggered timestamp for a subscription."""
        ...
    
    @abstractmethod
    async def exists(self, subscription_id: WebhookSubscriptionId) -> bool:
        """Check if webhook subscription exists."""
        ...


# Service Protocols following organizations pattern
@runtime_checkable
class EventPublisher(Protocol):
    """Protocol for event publishing operations."""
    
    @abstractmethod
    async def publish(self, event: DomainEvent) -> bool:
        """Publish a domain event."""
        ...
    
    @abstractmethod
    async def publish_batch(self, events: List[DomainEvent]) -> int:
        """Publish multiple domain events. Returns count of successfully published events."""
        ...
    
    @abstractmethod
    async def create_and_publish(self, event_type: str, aggregate_type: str, 
                               aggregate_id: UUID, event_data: Dict[str, Any],
                               triggered_by_user_id: Optional[UserId] = None,
                               context_id: Optional[UUID] = None,
                               correlation_id: Optional[UUID] = None,
                               causation_id: Optional[UUID] = None) -> DomainEvent:
        """Create and publish a domain event in one operation."""
        ...


@runtime_checkable
class WebhookDeliveryService(Protocol):
    """Protocol for webhook delivery operations."""
    
    @abstractmethod
    async def deliver_event(self, event: DomainEvent) -> List[WebhookDelivery]:
        """Deliver an event to all subscribed webhook endpoints."""
        ...
    
    @abstractmethod
    async def deliver_to_endpoint(self, event: DomainEvent, 
                                 endpoint: WebhookEndpoint) -> WebhookDelivery:
        """Deliver an event to a specific webhook endpoint."""
        ...
    
    @abstractmethod
    async def retry_failed_deliveries(self, limit: int = 100) -> int:
        """Retry failed webhook deliveries. Returns count of retry attempts."""
        ...
    
    @abstractmethod
    async def verify_endpoint(self, endpoint: WebhookEndpoint) -> bool:
        """Verify that a webhook endpoint is reachable and valid."""
        ...
    
    @abstractmethod
    async def cancel_delivery(self, delivery_id: WebhookDeliveryId, 
                            reason: str = "Cancelled") -> bool:
        """Cancel a webhook delivery."""
        ...


@runtime_checkable
class EventDispatcher(Protocol):
    """Protocol for event dispatching and orchestration."""
    
    @abstractmethod
    async def dispatch_unprocessed_events(self, limit: int = 100) -> int:
        """Process unprocessed events for webhook delivery. Returns count of processed events."""
        ...
    
    @abstractmethod
    async def dispatch_event(self, event: DomainEvent) -> List[WebhookDelivery]:
        """Dispatch a single event to all relevant webhook endpoints."""
        ...
    
    @abstractmethod
    async def get_subscribed_endpoints(self, event_type: str, 
                                     context_id: Optional[UUID] = None) -> List[WebhookEndpoint]:
        """Get webhook endpoints subscribed to a specific event type."""
        ...
    
    @abstractmethod
    async def subscribe_endpoint(self, endpoint_id: WebhookEndpointId, 
                               event_type: str, event_filters: Optional[Dict[str, Any]] = None) -> bool:
        """Subscribe a webhook endpoint to an event type."""
        ...
    
    @abstractmethod
    async def unsubscribe_endpoint(self, endpoint_id: WebhookEndpointId, 
                                 event_type: str) -> bool:
        """Unsubscribe a webhook endpoint from an event type."""
        ...
    
    @abstractmethod
    async def get_endpoint_subscriptions(self, endpoint_id: WebhookEndpointId) -> List[str]:
        """Get all event types that an endpoint is subscribed to."""
        ...

@runtime_checkable
class EventActionRepository(Protocol):
    """Protocol for event action repository operations."""
    
    @abstractmethod
    async def save(self, action) -> Any:  # EventAction return type
        """Save an event action."""
        ...
    
    @abstractmethod
    async def get_by_id(self, action_id) -> Optional[Any]:  # ActionId param, EventAction return
        """Get action by ID."""
        ...
    
    @abstractmethod
    async def get_actions_for_event(self, event_type: str, 
                                  context_filters: Optional[Dict[str, Any]] = None) -> List[Any]:  # List[EventAction]
        """Get actions that should be triggered for the given event."""
        ...
    
    @abstractmethod
    async def get_active_actions(self) -> List[Any]:  # List[EventAction]
        """Get all active actions."""
        ...
    
    @abstractmethod
    async def get_actions_by_handler_type(self, handler_type: str) -> List[Any]:  # List[EventAction] 
        """Get actions by handler type."""
        ...
    
    @abstractmethod
    async def update(self, action) -> Any:  # EventAction param and return
        """Update an existing action."""
        ...
    
    @abstractmethod
    async def delete(self, action_id) -> bool:  # ActionId param
        """Delete an action."""
        ...
    
    @abstractmethod
    async def get_by_tenant(self, tenant_id: str) -> List[Any]:  # List[EventAction]
        """Get actions for a specific tenant."""
        ...


@runtime_checkable  
class ActionExecutionRepository(Protocol):
    """Protocol for action execution repository operations."""
    
    @abstractmethod
    async def save_execution(self, execution) -> Any:  # ActionExecution param and return
        """Save an action execution record."""
        ...
    
    @abstractmethod
    async def get_execution_by_id(self, execution_id) -> Optional[Any]:  # ActionExecutionId param, ActionExecution return
        """Get execution by ID."""
        ...
    
    @abstractmethod
    async def get_executions_by_action(self, action_id, limit: int = 100) -> List[Any]:  # ActionId param, List[ActionExecution] return
        """Get executions for a specific action."""
        ...
    
    @abstractmethod
    async def get_failed_executions(self, limit: int = 100) -> List[Any]:  # List[ActionExecution]
        """Get failed executions for retry."""
        ...
    
    @abstractmethod
    async def update_execution(self, execution) -> Any:  # ActionExecution param and return
        """Update an execution record."""
        ...
    
    @abstractmethod
    async def get_execution_stats(self, action_id, days: int = 7) -> Dict[str, Any]:  # ActionId param
        """Get execution statistics for an action."""
        ...


@runtime_checkable
class EventActionRegistry(Protocol):
    """Protocol for event action registry operations."""
    
    @abstractmethod
    async def register_action(self, action) -> None:  # EventAction param
        """Register a new event action."""
        ...
    
    @abstractmethod
    async def unregister_action(self, action_id) -> bool:  # ActionId param
        """Unregister an event action."""
        ...
    
    @abstractmethod
    async def get_actions_for_event(self, event_type: str, event_data: Dict[str, Any]) -> List[Any]:  # List[EventAction]
        """Get actions that match the given event."""
        ...
    
    @abstractmethod
    async def reload_actions(self) -> None:
        """Reload actions from storage."""
        ...


@runtime_checkable
class ActionExecutionService(Protocol):
    """Protocol for action execution service operations."""
    
    @abstractmethod
    async def execute_action(self, action, event_data: Dict[str, Any]) -> Any:  # EventAction param, ActionExecution return
        """Execute an action with the given event data."""
        ...
    
    @abstractmethod
    async def execute_actions_for_event(self, event_type: str, event_data: Dict[str, Any]) -> List[Any]:  # List[ActionExecution]
        """Execute all matching actions for an event."""
        ...
    
    @abstractmethod
    async def retry_failed_execution(self, execution_id) -> bool:  # ActionExecutionId param
        """Retry a failed action execution."""
        ...
