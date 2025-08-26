"""Event dispatcher protocol for platform events infrastructure.

This module defines the EventDispatcher protocol contract following maximum separation architecture.
Single responsibility: Event dispatching coordination and orchestration.

Extracted to platform/events following enterprise clean architecture patterns.
Pure platform infrastructure protocol - used by all business features.
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from uuid import UUID

from .....core.value_objects import UserId
from ..value_objects import EventId, WebhookEndpointId
from ..entities.domain_event import DomainEvent
from ..entities.webhook_endpoint import WebhookEndpoint
from ..entities.webhook_delivery import WebhookDelivery


@runtime_checkable
class EventDispatcher(Protocol):
    """Event dispatcher protocol for orchestrating event processing and delivery.
    
    This protocol defines the contract for event dispatching operations following
    maximum separation architecture. Single responsibility: coordinate event processing
    and webhook delivery orchestration across the platform.
    
    Pure platform infrastructure protocol - implementations handle:
    - Event processing coordination
    - Webhook delivery orchestration
    - Subscription management
    - Delivery retry coordination
    - Performance optimization
    """

    # ===========================================
    # Core Event Dispatching Operations
    # ===========================================
    
    @abstractmethod
    async def dispatch_event(self, event: DomainEvent) -> List[WebhookDelivery]:
        """Dispatch a single event to all relevant webhook endpoints.
        
        This is the core dispatching method that:
        - Finds matching webhook subscriptions
        - Creates deliveries for each subscription
        - Coordinates delivery attempts
        - Returns delivery tracking information
        
        Args:
            event: Domain event to dispatch
            
        Returns:
            List of webhook deliveries created for this event
            
        Raises:
            EventDispatchError: If dispatching fails
        """
        ...
    
    @abstractmethod
    async def dispatch_unprocessed_events(
        self, 
        limit: Optional[int] = None,
        batch_size: Optional[int] = None,
        max_concurrent_batches: Optional[int] = None
    ) -> int:
        """Process unprocessed events for webhook delivery with configurable batching.
        
        Coordinates batch processing of events that haven't been processed yet.
        Supports parallel processing and optimized database operations.
        
        Args:
            limit: Maximum number of events to process (uses configuration if None)
            batch_size: Number of events per batch (uses configuration if None)
            max_concurrent_batches: Maximum concurrent batches (uses configuration if None)
            
        Returns:
            Count of successfully processed events
            
        Raises:
            EventDispatchError: If batch processing fails
        """
        ...
    
    @abstractmethod
    async def dispatch_events_parallel(
        self,
        events: List[DomainEvent],
        max_concurrent_events: Optional[int] = None,
        timeout_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """High-performance parallel event dispatching for real-time scenarios.
        
        Coordinates parallel processing of multiple events with controlled concurrency
        and comprehensive performance metrics.
        
        Args:
            events: List of events to dispatch
            max_concurrent_events: Maximum concurrent events (uses configuration if None)
            timeout_seconds: Timeout for entire operation (uses configuration if None)
            
        Returns:
            Dict with processing statistics:
            - total_events: Total events processed
            - successful_events: Successfully processed events
            - failed_events: Failed events
            - total_deliveries: Total deliveries created
            - processing_time_ms: Total processing time
            - events_per_second: Processing throughput
            
        Raises:
            EventDispatchError: If parallel processing fails
            TimeoutError: If processing exceeds timeout
        """
        ...

    # ===========================================
    # Event Publishing Operations
    # ===========================================
    
    @abstractmethod
    async def publish_event(self, event: DomainEvent) -> bool:
        """Publish a domain event to the platform.
        
        Saves the event to persistent storage and makes it available for dispatching.
        This is typically the entry point for new events into the system.
        
        Args:
            event: Domain event to publish
            
        Returns:
            True if event was successfully published, False otherwise
            
        Raises:
            EventPublishError: If publishing fails
        """
        ...
    
    @abstractmethod
    async def publish_batch_events(self, events: List[DomainEvent]) -> int:
        """Publish multiple domain events as a batch.
        
        Optimized batch publishing for high-throughput scenarios.
        
        Args:
            events: List of domain events to publish
            
        Returns:
            Count of successfully published events
            
        Raises:
            EventPublishError: If batch publishing fails
        """
        ...
    
    @abstractmethod
    async def create_and_publish_event(
        self,
        event_type: str,
        aggregate_id: UUID,
        aggregate_type: str,
        event_data: Dict[str, Any],
        triggered_by_user_id: Optional[UserId] = None,
        context_id: Optional[UUID] = None,
        correlation_id: Optional[UUID] = None,
        causation_id: Optional[UUID] = None
    ) -> DomainEvent:
        """Create and publish a domain event in one atomic operation.
        
        Factory method that creates a properly configured domain event and publishes it.
        Ensures all required fields are set and UUIDv7 compliance is maintained.
        
        Args:
            event_type: Type of the event (e.g., "organization.created")
            aggregate_id: ID of the entity that triggered the event (should be UUIDv7)
            aggregate_type: Type of entity (organization, user, etc.)
            event_data: Main event payload
            triggered_by_user_id: User who triggered this event
            context_id: Generic context (organization_id, team_id, etc.)
            correlation_id: For tracking related events
            causation_id: The event that caused this event
            
        Returns:
            The created and published domain event
            
        Raises:
            EventCreationError: If event creation fails
            EventPublishError: If publishing fails
        """
        ...

    # ===========================================
    # Subscription Management Operations
    # ===========================================
    
    @abstractmethod
    async def get_subscribed_endpoints(
        self, 
        event_type: str, 
        context_id: Optional[UUID] = None
    ) -> List[WebhookEndpoint]:
        """Get webhook endpoints subscribed to a specific event type.
        
        Finds all active webhook endpoints that have subscriptions matching
        the given event type and context filters.
        
        Args:
            event_type: Event type to find subscriptions for
            context_id: Optional context filter (organization, team, etc.)
            
        Returns:
            List of webhook endpoints subscribed to the event type
            
        Raises:
            EventDispatchError: If subscription lookup fails
        """
        ...
    
    @abstractmethod
    async def subscribe_endpoint(
        self, 
        endpoint_id: WebhookEndpointId, 
        event_type: str, 
        event_filters: Optional[Dict[str, Any]] = None,
        context_id: Optional[UUID] = None
    ) -> bool:
        """Subscribe a webhook endpoint to an event type.
        
        Creates a new subscription that will cause events of the specified type
        to be delivered to the given endpoint.
        
        Args:
            endpoint_id: ID of the webhook endpoint to subscribe
            event_type: Event type to subscribe to
            event_filters: Optional filters to apply to event data
            context_id: Optional context filter (organization, team, etc.)
            
        Returns:
            True if subscription was created successfully, False otherwise
            
        Raises:
            SubscriptionError: If subscription creation fails
        """
        ...
    
    @abstractmethod
    async def unsubscribe_endpoint(
        self, 
        endpoint_id: WebhookEndpointId, 
        event_type: str
    ) -> bool:
        """Unsubscribe a webhook endpoint from an event type.
        
        Deactivates subscriptions for the given endpoint and event type.
        Uses soft delete to maintain audit trail.
        
        Args:
            endpoint_id: ID of the webhook endpoint to unsubscribe
            event_type: Event type to unsubscribe from
            
        Returns:
            True if unsubscription was successful, False otherwise
            
        Raises:
            SubscriptionError: If unsubscription fails
        """
        ...
    
    @abstractmethod
    async def get_endpoint_subscriptions(self, endpoint_id: WebhookEndpointId) -> List[str]:
        """Get all event types that an endpoint is subscribed to.
        
        Returns the list of event types that will trigger webhook deliveries
        to the specified endpoint.
        
        Args:
            endpoint_id: ID of the webhook endpoint
            
        Returns:
            List of event type strings the endpoint is subscribed to
            
        Raises:
            EventDispatchError: If subscription lookup fails
        """
        ...

    # ===========================================
    # Delivery Management Operations
    # ===========================================
    
    @abstractmethod
    async def retry_failed_deliveries(self, limit: int = 100) -> int:
        """Retry failed webhook deliveries.
        
        Finds deliveries that have failed but are eligible for retry and
        attempts to deliver them again. Implements backoff strategies.
        
        Args:
            limit: Maximum number of deliveries to retry
            
        Returns:
            Count of delivery retry attempts made
            
        Raises:
            DeliveryRetryError: If retry processing fails
        """
        ...
    
    @abstractmethod
    async def cancel_delivery(
        self, 
        delivery_id: WebhookEndpointId, 
        reason: str = "Cancelled"
    ) -> bool:
        """Cancel a webhook delivery.
        
        Marks a delivery as cancelled to prevent further retry attempts.
        
        Args:
            delivery_id: ID of the delivery to cancel
            reason: Reason for cancellation
            
        Returns:
            True if delivery was cancelled successfully, False otherwise
            
        Raises:
            DeliveryError: If cancellation fails
        """
        ...
    
    @abstractmethod
    async def verify_endpoint(self, endpoint: WebhookEndpoint) -> bool:
        """Verify that a webhook endpoint is reachable and valid.
        
        Performs a test delivery to verify the endpoint can receive webhooks
        and responds appropriately.
        
        Args:
            endpoint: Webhook endpoint to verify
            
        Returns:
            True if endpoint verification succeeded, False otherwise
            
        Raises:
            EndpointVerificationError: If verification fails
        """
        ...

    # ===========================================
    # Performance and Monitoring Operations
    # ===========================================
    
    @abstractmethod
    async def dispatch_events_streaming(
        self,
        event_stream_size_limit: int = 10000,
        batch_size: int = 100,
        max_concurrent_batches: int = 5,
        memory_threshold_mb: int = 500
    ) -> Dict[str, Any]:
        """Process events using streaming for memory efficiency.
        
        Handles very large volumes of events without loading all into memory
        simultaneously. Includes adaptive batch sizing based on memory usage.
        
        Args:
            event_stream_size_limit: Maximum events to process in this stream
            batch_size: Initial batch size (adjusted based on memory)
            max_concurrent_batches: Maximum concurrent batches
            memory_threshold_mb: Memory threshold to trigger adaptive sizing
            
        Returns:
            Dict with comprehensive streaming processing statistics
            
        Raises:
            StreamingProcessingError: If streaming processing fails
        """
        ...
    
    @abstractmethod
    async def get_processing_status(self) -> Dict[str, Any]:
        """Get current event processing status and metrics.
        
        Returns comprehensive status information about event processing
        including queue sizes, performance metrics, and system health.
        
        Returns:
            Dict with processing status information:
            - unprocessed_events: Count of events waiting for processing
            - processing_events: Count of events currently being processed
            - failed_events: Count of events that failed processing
            - performance_metrics: Processing throughput and latency
            - system_health: Memory usage and resource status
            
        Raises:
            StatusError: If status retrieval fails
        """
        ...