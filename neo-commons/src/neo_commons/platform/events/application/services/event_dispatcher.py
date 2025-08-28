"""Event dispatcher service for platform events infrastructure.

Pure application service for orchestrating event dispatching and webhook delivery
across the platform. Follows maximum separation architecture.

Single responsibility: Coordinate event processing workflow focused on
event dispatching and webhook delivery. Action execution moved to platform/actions.

Note: This is a cleaned version focusing only on events and webhooks.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Protocol, runtime_checkable
from datetime import datetime, timezone
from uuid import UUID

# Platform events core imports (clean boundaries)
from ...core.entities import DomainEvent, WebhookEndpoint, WebhookDelivery
from ...core.value_objects import (
    EventId, WebhookEndpointId, WebhookDeliveryId, DeliveryStatus
)
from ...core.exceptions import (
    EventDispatchFailed, WebhookDeliveryFailed,
    InvalidEventConfiguration
)

# Platform protocols for dependency injection
from ...core.protocols import (
    EventDispatcher, DeliveryService, EventRepository
)

logger = logging.getLogger(__name__)


@runtime_checkable
class EventDispatcherService(Protocol):
    """Event dispatcher service protocol for platform events orchestration.
    
    Pure application service that coordinates event processing workflow
    focused on event dispatching and webhook delivery only.
    
    Note: Action execution functionality has been moved to platform/actions module.
    """
    
    async def dispatch_event(self, event: DomainEvent) -> List[WebhookDelivery]:
        """Dispatch single event through webhook delivery pipeline.
        
        Args:
            event: Domain event to process
            
        Returns:
            List of webhook deliveries created
            
        Raises:
            EventDispatchFailed: If event dispatching fails
        """
        ...
    
    async def dispatch_events_batch(
        self, 
        events: List[DomainEvent],
        batch_size: Optional[int] = None,
        max_concurrent: Optional[int] = None
    ) -> List[WebhookDelivery]:
        """Dispatch multiple events in batches for efficiency.
        
        Args:
            events: List of events to dispatch
            batch_size: Number of events per batch
            max_concurrent: Maximum concurrent processing
            
        Returns:
            List of all webhook deliveries created
            
        Raises:
            EventDispatchFailed: If batch processing fails
        """
        ...
    
    async def process_unprocessed_events(
        self,
        limit: Optional[int] = None,
        use_streaming: bool = False
    ) -> int:
        """Process unprocessed events from repository.
        
        Args:
            limit: Maximum number of events to process
            use_streaming: Use streaming for memory efficiency
            
        Returns:
            Number of events processed
            
        Raises:
            EventDispatchFailed: If processing fails
        """
        ...


class DefaultEventDispatcherService:
    """Default implementation of event dispatcher service.
    
    Orchestrates event processing through repository pattern and webhook
    delivery services. Focused solely on event dispatching and webhook delivery.
    
    Note: Action execution functionality has been moved to platform/actions module.
    """
    
    def __init__(
        self,
        event_repository: EventRepository,
        delivery_service: Optional[DeliveryService] = None,
        default_batch_size: int = 100,
        max_concurrent_events: int = 10
    ):
        """Initialize event dispatcher service.
        
        Args:
            event_repository: Event repository implementation
            delivery_service: Optional webhook delivery service
            default_batch_size: Default batch size for processing
            max_concurrent_events: Maximum concurrent event processing
        """
        self._event_repository = event_repository
        self._delivery_service = delivery_service
        
        # Processing configuration
        self._default_batch_size = default_batch_size
        self._max_concurrent = max_concurrent_events
        
        logger.info(f"Event dispatcher initialized with batch_size={default_batch_size}, max_concurrent={max_concurrent_events}")
    
    async def dispatch_event(self, event: DomainEvent) -> List[WebhookDelivery]:
        """Dispatch single event through webhook delivery pipeline."""
        try:
            logger.info(f"Dispatching event {event.id.value} of type {event.event_type.value}")
            
            # Store event in repository
            await self._event_repository.save_event(event)
            logger.debug(f"Event {event.id.value} saved to repository")
            
            # Deliver webhooks (if enabled and available)
            webhook_deliveries = []
            if self._delivery_service:
                try:
                    webhook_deliveries = await self._delivery_service.deliver_webhooks_for_event(event)
                    logger.debug(f"Created {len(webhook_deliveries)} webhook deliveries for event {event.id.value}")
                except Exception as e:
                    logger.error(f"Webhook delivery failed for event {event.id.value}: {e}")
                    # Continue processing even if webhook delivery fails
            
            # Mark event as processed
            await self._event_repository.mark_event_processed(event.id)
            
            logger.info(f"Successfully dispatched event {event.id.value}")
            return webhook_deliveries
            
        except Exception as e:
            logger.error(f"Failed to dispatch event {event.id.value}: {e}")
            raise EventDispatchFailed(f"Event dispatch failed: {e}")
    
    async def dispatch_events_batch(
        self, 
        events: List[DomainEvent],
        batch_size: Optional[int] = None,
        max_concurrent: Optional[int] = None
    ) -> List[WebhookDelivery]:
        """Dispatch multiple events in batches for efficiency."""
        if not events:
            logger.debug("No events to dispatch in batch")
            return []
        
        batch_size = batch_size or self._default_batch_size
        max_concurrent = max_concurrent or self._max_concurrent
        
        logger.info(f"Starting batch dispatch of {len(events)} events (batch_size={batch_size}, max_concurrent={max_concurrent})")
        
        all_deliveries = []
        
        try:
            # Process events in batches
            for i in range(0, len(events), batch_size):
                batch = events[i:i + batch_size]
                batch_number = (i // batch_size) + 1
                
                logger.debug(f"Processing batch {batch_number} with {len(batch)} events")
                batch_deliveries = await self._process_event_batch(batch, batch_number, max_concurrent)
                all_deliveries.extend(batch_deliveries)
            
            logger.info(f"Batch dispatch completed. Total webhook deliveries created: {len(all_deliveries)}")
            return all_deliveries
            
        except Exception as e:
            logger.error(f"Batch event dispatch failed: {e}")
            raise EventDispatchFailed(f"Batch dispatch failed: {e}")
    
    async def process_unprocessed_events(
        self,
        limit: Optional[int] = None,
        use_streaming: bool = False
    ) -> int:
        """Process unprocessed events from repository."""
        try:
            limit = limit or 1000
            logger.info(f"Processing unprocessed events (limit={limit}, streaming={use_streaming})")
            
            if use_streaming:
                return await self._process_unprocessed_events_streaming(limit)
            else:
                return await self._process_unprocessed_events_batch(limit)
                
        except Exception as e:
            logger.error(f"Unprocessed events processing failed: {e}")
            raise EventDispatchFailed(f"Unprocessed events processing failed: {e}")
    
    async def _process_event_batch(
        self,
        events: List[DomainEvent],
        batch_number: int,
        max_concurrent: int
    ) -> List[WebhookDelivery]:
        """Process a batch of events with concurrency control."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def dispatch_with_semaphore(event: DomainEvent) -> List[WebhookDelivery]:
            async with semaphore:
                return await self._dispatch_single_event(event)
        
        # Create tasks for all events in batch
        tasks = [dispatch_with_semaphore(event) for event in events]
        
        # Execute with concurrency control
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect successful deliveries and log failures
        all_deliveries = []
        failed_count = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_count += 1
                logger.error(f"Event {events[i].id.value} failed in batch {batch_number}: {result}")
            else:
                all_deliveries.extend(result)
        
        logger.info(f"Batch {batch_number} completed: {len(events) - failed_count}/{len(events)} succeeded")
        return all_deliveries
    
    async def _dispatch_single_event(self, event: DomainEvent) -> List[WebhookDelivery]:
        """Dispatch single event with error handling."""
        try:
            return await self.dispatch_event(event)
        except Exception as e:
            logger.error(f"Single event dispatch failed for {event.id.value}: {e}")
            return []
    
    async def _process_unprocessed_events_batch(self, limit: int) -> int:
        """Process unprocessed events using batch mode."""
        try:
            # Get unprocessed events from repository
            unprocessed_events = await self._event_repository.get_unprocessed_events(limit=limit)
            
            if not unprocessed_events:
                logger.debug("No unprocessed events found")
                return 0
            
            logger.info(f"Found {len(unprocessed_events)} unprocessed events")
            
            # Process them in batches
            await self.dispatch_events_batch(unprocessed_events)
            
            return len(unprocessed_events)
            
        except Exception as e:
            logger.error(f"Batch processing of unprocessed events failed: {e}")
            raise
    
    async def _process_unprocessed_events_streaming(self, limit: int) -> int:
        """Process unprocessed events using streaming mode for memory efficiency."""
        try:
            total_processed = 0
            batch_size = min(self._default_batch_size, limit)
            
            while total_processed < limit:
                # Get next batch
                remaining = limit - total_processed
                current_batch_size = min(batch_size, remaining)
                
                events = await self._event_repository.get_unprocessed_events(
                    limit=current_batch_size,
                    skip=total_processed
                )
                
                if not events:
                    break  # No more events
                
                # Process batch
                await self.dispatch_events_batch(events)
                total_processed += len(events)
                
                logger.debug(f"Streaming progress: {total_processed}/{limit} events processed")
            
            logger.info(f"Streaming processing completed: {total_processed} events processed")
            return total_processed
            
        except Exception as e:
            logger.error(f"Streaming processing failed: {e}")
            raise


def create_event_dispatcher_service(
    event_repository: EventRepository,
    delivery_service: Optional[DeliveryService] = None,
    **config_options
) -> DefaultEventDispatcherService:
    """Create event dispatcher service with dependency injection.
    
    Args:
        event_repository: Event repository implementation
        delivery_service: Optional delivery service
        **config_options: Configuration options (batch_size, max_concurrent, etc.)
        
    Returns:
        Configured event dispatcher service
    """
    return DefaultEventDispatcherService(
        event_repository=event_repository,
        delivery_service=delivery_service,
        **config_options
    )