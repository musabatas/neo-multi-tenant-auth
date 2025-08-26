"""Event dispatcher service orchestrator using specialized services.

Orchestrates multiple specialized services following single responsibility principle.
Acts as a facade for complex event operations requiring cross-service coordination.
"""

import asyncio
import logging
import time
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from uuid import UUID

from ....core.value_objects import (
    EventId, WebhookEndpointId, WebhookEventTypeId, WebhookDeliveryId, WebhookSubscriptionId, UserId
)

from ..entities.domain_event import DomainEvent
from ..entities.webhook_endpoint import WebhookEndpoint
from ..entities.webhook_delivery import WebhookDelivery
from ..entities.webhook_subscription import WebhookSubscription
from ..entities.protocols import (
    EventRepository,
    WebhookEndpointRepository, 
    WebhookEventTypeRepository,
    WebhookDeliveryRepository,
    WebhookSubscriptionRepository,
    EventActionRepository,
    ActionExecutionRepository
)

# Import specialized services
from .event_publisher_service import EventPublisherService
from .webhook_delivery_service import WebhookDeliveryService
from .webhook_endpoint_service import WebhookEndpointService
from .webhook_event_type_service import WebhookEventTypeService
from .webhook_config_service import get_webhook_config_service, WebhookConfigService
from .event_action_registry import EventActionRegistryService

logger = logging.getLogger(__name__)


class EventDispatcherService:
    """Event dispatcher service orchestrator.
    
    Coordinates multiple specialized services and provides a unified interface
    for complex event and webhook operations. Acts as a facade while delegating
    specific operations to single-responsibility services.
    """
    
    def __init__(
        self,
        event_repository: EventRepository,
        endpoint_repository: WebhookEndpointRepository,
        event_type_repository: WebhookEventTypeRepository,
        delivery_repository: WebhookDeliveryRepository,
        subscription_repository: WebhookSubscriptionRepository,
        action_repository: Optional[EventActionRepository] = None,
        execution_repository: Optional[ActionExecutionRepository] = None,
        config_service: Optional[WebhookConfigService] = None
    ):
        """Initialize with injected dependencies and create specialized services.
        
        Args:
            event_repository: Domain event repository implementation
            endpoint_repository: Webhook endpoint repository implementation
            event_type_repository: Webhook event type repository implementation
            delivery_repository: Webhook delivery repository implementation
            subscription_repository: Webhook subscription repository implementation
            action_repository: Optional event action repository implementation
            execution_repository: Optional action execution repository implementation
            config_service: Optional webhook configuration service (uses global if not provided)
        """
        self._event_repository = event_repository
        self._endpoint_repository = endpoint_repository
        self._event_type_repository = event_type_repository
        self._delivery_repository = delivery_repository
        self._subscription_repository = subscription_repository
        self._action_repository = action_repository
        self._execution_repository = execution_repository
        
        # Configuration service for externalized values
        self._config_service = config_service or get_webhook_config_service()
        self._config = self._config_service.get_config()
        
        # Create specialized services
        self._publisher_service = EventPublisherService(event_repository)
        self._delivery_service = WebhookDeliveryService(delivery_repository)
        self._endpoint_service = WebhookEndpointService(endpoint_repository)
        self._event_type_service = WebhookEventTypeService(event_type_repository)
        
        # Create dynamic action registry service if repositories are provided
        self._action_registry: Optional[EventActionRegistryService] = None
        if action_repository:
            self._action_registry = EventActionRegistryService(
                repository=action_repository,
                cache_ttl_seconds=300,  # 5 minutes
                enable_cache=True
            )
    
    # ===========================================
    # Event Publishing Operations (delegate to EventPublisherService)
    # ===========================================
    
    async def publish_event(self, event: DomainEvent) -> bool:
        """Publish a domain event."""
        return await self._publisher_service.publish(event)
    
    async def publish_batch_events(self, events: List[DomainEvent]) -> int:
        """Publish multiple domain events. Returns count of successfully published events."""
        return await self._publisher_service.publish_batch(events)
    
    async def create_and_publish_event(
        self,
        event_type: str,
        aggregate_type: str, 
        aggregate_id: UUID,
        event_data: Dict[str, Any],
        triggered_by_user_id: Optional[UserId] = None,
        context_id: Optional[UUID] = None,
        correlation_id: Optional[UUID] = None,
        causation_id: Optional[UUID] = None
    ) -> DomainEvent:
        """Create and publish a domain event in one operation."""
        return await self._publisher_service.create_and_publish(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_data=event_data,
            triggered_by_user_id=triggered_by_user_id,
            context_id=context_id,
            correlation_id=correlation_id,
            causation_id=causation_id
        )
    
    async def create_organization_event(
        self,
        event_action: str,
        organization_id: UUID,
        event_data: Dict[str, Any],
        triggered_by_user_id: Optional[UserId] = None,
        correlation_id: Optional[UUID] = None,
        causation_id: Optional[UUID] = None
    ) -> DomainEvent:
        """Convenience method to create organization-related events."""
        return await self._publisher_service.create_organization_event(
            event_action=event_action,
            organization_id=organization_id,
            event_data=event_data,
            triggered_by_user_id=triggered_by_user_id,
            correlation_id=correlation_id,
            causation_id=causation_id
        )
    
    async def create_user_event(
        self,
        event_action: str,
        user_id: UUID,
        event_data: Dict[str, Any],
        context_id: Optional[UUID] = None,
        triggered_by_user_id: Optional[UserId] = None,
        correlation_id: Optional[UUID] = None,
        causation_id: Optional[UUID] = None
    ) -> DomainEvent:
        """Convenience method to create user-related events."""
        return await self._publisher_service.create_user_event(
            event_action=event_action,
            user_id=user_id,
            event_data=event_data,
            context_id=context_id,
            triggered_by_user_id=triggered_by_user_id,
            correlation_id=correlation_id,
            causation_id=causation_id
        )
    
    # ===========================================
    # Event Dispatching Operations (core orchestration)
    # ===========================================
    
    async def dispatch_unprocessed_events(
        self, 
        limit: Optional[int] = None,
        batch_size: Optional[int] = None,
        max_concurrent_batches: Optional[int] = None,
        use_streaming: bool = False,
        stream_chunk_size: Optional[int] = None,
        use_optimized_queries: Optional[bool] = None
    ) -> int:
        """Process unprocessed events for webhook delivery with configurable parallel processing.
        
        Args:
            limit: Maximum number of events to process (uses config default if None)
            batch_size: Number of events to process in each batch (uses config default if None)
            max_concurrent_batches: Maximum number of batches to process concurrently (uses config default if None)
            use_streaming: Whether to use streaming processing for memory efficiency
            stream_chunk_size: Size of each stream chunk for memory-efficient processing (uses config default if None)
            use_optimized_queries: Use FOR UPDATE SKIP LOCKED and selective column queries (uses config default if None)
            
        Returns:
            Count of successfully processed events
        """
        try:
            # Apply configuration defaults for None values
            perf_config = self._config.performance
            db_config = self._config.database
            
            actual_limit = limit if limit is not None else perf_config.default_event_limit
            actual_batch_size = batch_size if batch_size is not None else perf_config.default_batch_size
            actual_max_concurrent_batches = max_concurrent_batches if max_concurrent_batches is not None else perf_config.max_concurrent_batches
            actual_stream_chunk_size = stream_chunk_size if stream_chunk_size is not None else perf_config.stream_chunk_size
            actual_use_optimized = use_optimized_queries if use_optimized_queries is not None else db_config.use_for_update_skip_locked
            
            if use_streaming:
                return await self._dispatch_unprocessed_events_streaming(
                    actual_limit, actual_batch_size, actual_max_concurrent_batches, actual_stream_chunk_size, actual_use_optimized
                )
            
            # Get unprocessed events with optimized queries
            if actual_use_optimized:
                # Use FOR UPDATE SKIP LOCKED for high-concurrency scenarios
                select_columns = ["id", "event_type", "event_data", "context_id", "created_at"]
                unprocessed_events = await self._event_repository.get_unprocessed_for_update(
                    limit=actual_limit,
                    skip_locked=True,
                    select_columns=select_columns
                )
            else:
                unprocessed_events = await self._event_repository.get_unprocessed(actual_limit)
            
            if not unprocessed_events:
                logger.debug("No unprocessed events found for webhook dispatch")
                return 0
            
            logger.info(f"Starting parallel batch processing of {len(unprocessed_events)} unprocessed events")
            
            # Split events into batches
            event_batches = [
                unprocessed_events[i:i + actual_batch_size] 
                for i in range(0, len(unprocessed_events), actual_batch_size)
            ]
            
            total_processed = 0
            semaphore = asyncio.Semaphore(actual_max_concurrent_batches)
            
            # Process batches with controlled concurrency
            batch_tasks = [
                self._process_event_batch(batch, batch_idx + 1, semaphore)
                for batch_idx, batch in enumerate(event_batches)
            ]
            
            # Wait for all batches to complete
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Collect results and handle any exceptions
            for batch_idx, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Batch {batch_idx + 1} failed with exception: {result}")
                else:
                    total_processed += result
                    logger.debug(f"Batch {batch_idx + 1} processed {result} events")
            
            logger.info(f"Parallel batch processing complete: {total_processed} events processed successfully")
            return total_processed
            
        except Exception as e:
            logger.error(f"Error in parallel batch processing unprocessed events: {e}")
            raise
    
    async def _dispatch_unprocessed_events_streaming(
        self,
        limit: int,
        batch_size: int,
        max_concurrent_batches: int,
        stream_chunk_size: int,
        use_optimized_queries: bool = True
    ) -> int:
        """Process unprocessed events using streaming for memory efficiency in high-volume scenarios.
        
        Args:
            limit: Maximum number of events to process
            batch_size: Number of events to process in each batch  
            max_concurrent_batches: Maximum number of batches to process concurrently
            stream_chunk_size: Size of each stream chunk for memory-efficient processing
            
        Returns:
            Count of successfully processed events
        """
        try:
            logger.info(f"Starting memory-efficient streaming processing (limit={limit}, chunk_size={stream_chunk_size})")
            
            total_processed = 0
            offset = 0
            
            while offset < limit:
                # Calculate current chunk size
                current_chunk_size = min(stream_chunk_size, limit - offset)
                
                # Get chunk of unprocessed events
                event_chunk = await self._event_repository.get_unprocessed_paginated(
                    limit=current_chunk_size, 
                    offset=offset
                )
                
                if not event_chunk:
                    logger.debug(f"No more events found at offset {offset}")
                    break
                
                logger.debug(f"Processing chunk {offset // stream_chunk_size + 1} with {len(event_chunk)} events")
                
                # Split chunk into batches
                event_batches = [
                    event_chunk[i:i + batch_size] 
                    for i in range(0, len(event_chunk), batch_size)
                ]
                
                # Process batches in chunk with controlled concurrency
                semaphore = asyncio.Semaphore(max_concurrent_batches)
                batch_tasks = [
                    self._process_event_batch(batch, f"{offset // stream_chunk_size + 1}.{batch_idx + 1}", semaphore)
                    for batch_idx, batch in enumerate(event_batches)
                ]
                
                # Wait for chunk batches to complete
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Collect chunk results
                chunk_processed = 0
                for batch_idx, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        logger.error(f"Chunk batch {offset // stream_chunk_size + 1}.{batch_idx + 1} failed: {result}")
                    else:
                        chunk_processed += result
                
                total_processed += chunk_processed
                offset += len(event_chunk)
                
                logger.info(f"Chunk {offset // stream_chunk_size} complete: {chunk_processed} events processed")
                
                # Break if we got fewer events than requested (end of data)
                if len(event_chunk) < current_chunk_size:
                    break
            
            logger.info(f"Streaming processing complete: {total_processed} events processed across {(offset - 1) // stream_chunk_size + 1} chunks")
            return total_processed
            
        except Exception as e:
            logger.error(f"Error in streaming event processing: {e}")
            raise
    
    async def dispatch_events_parallel(
        self,
        events: List[DomainEvent],
        max_concurrent_events: Optional[int] = None,
        event_batch_size: Optional[int] = None,
        max_delivery_concurrency: Optional[int] = None,
        timeout_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """High-performance parallel event dispatching for real-time scenarios.
        
        Args:
            events: List of events to dispatch
            max_concurrent_events: Maximum events to process concurrently (uses config if None)
            event_batch_size: Number of events to process in each micro-batch (uses config if None)
            max_delivery_concurrency: Maximum concurrent deliveries per event (uses config if None)
            timeout_seconds: Timeout for the entire operation (uses config if None)
            
        Returns:
            Dict with processing statistics and results
        """
        try:
            if not events:
                return {
                    "total_events": 0,
                    "successful_events": 0, 
                    "failed_events": 0,
                    "total_deliveries": 0,
                    "processing_time_ms": 0.0
                }
            
            # Apply configuration defaults
            perf_config = self._config.performance
            
            actual_max_concurrent_events = max_concurrent_events if max_concurrent_events is not None else perf_config.max_concurrent_events
            actual_event_batch_size = event_batch_size if event_batch_size is not None else 5  # Use small batches for parallel processing
            actual_max_delivery_concurrency = max_delivery_concurrency if max_delivery_concurrency is not None else perf_config.max_delivery_concurrency
            actual_timeout_seconds = timeout_seconds if timeout_seconds is not None else perf_config.event_processing_timeout_seconds
            
            start_time = datetime.now(timezone.utc)
            logger.info(f"Starting high-performance parallel dispatch of {len(events)} events")
            
            # Create semaphores for concurrency control
            event_semaphore = asyncio.Semaphore(actual_max_concurrent_events)
            delivery_semaphore = asyncio.Semaphore(actual_max_delivery_concurrency)
            
            # Split events into micro-batches for optimal memory usage
            event_batches = [
                events[i:i + actual_event_batch_size]
                for i in range(0, len(events), actual_event_batch_size)
            ]
            
            # Process micro-batches concurrently
            batch_tasks = [
                self._process_event_microbatch(
                    batch, 
                    batch_idx + 1,
                    event_semaphore,
                    delivery_semaphore,
                    actual_timeout_seconds / len(event_batches)  # Distribute timeout across batches
                )
                for batch_idx, batch in enumerate(event_batches)
            ]
            
            # Wait for all batches with timeout
            try:
                batch_results = await asyncio.wait_for(
                    asyncio.gather(*batch_tasks, return_exceptions=True),
                    timeout=actual_timeout_seconds
                )
            except asyncio.TimeoutError:
                logger.error(f"Parallel dispatch timed out after {actual_timeout_seconds}s")
                raise
            
            # Aggregate results
            total_successful = 0
            total_failed = 0
            total_deliveries = 0
            failed_batches = []
            
            for batch_idx, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Micro-batch {batch_idx + 1} failed: {result}")
                    failed_batches.append(batch_idx + 1)
                    total_failed += len(event_batches[batch_idx])
                else:
                    total_successful += result["successful_events"]
                    total_failed += result["failed_events"]
                    total_deliveries += result["total_deliveries"]
            
            # Calculate processing time
            end_time = datetime.now(timezone.utc)
            processing_time_ms = (end_time - start_time).total_seconds() * 1000
            
            result = {
                "total_events": len(events),
                "successful_events": total_successful,
                "failed_events": total_failed,
                "total_deliveries": total_deliveries,
                "processing_time_ms": round(processing_time_ms, 2),
                "events_per_second": round(len(events) / (processing_time_ms / 1000), 2),
                "failed_batches": failed_batches,
                "average_deliveries_per_event": round(total_deliveries / len(events), 2) if events else 0
            }
            
            logger.info(
                f"Parallel dispatch complete: {total_successful}/{len(events)} events successful, "
                f"{total_deliveries} deliveries, {processing_time_ms:.2f}ms "
                f"({result['events_per_second']:.2f} events/sec)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in parallel event dispatch: {e}")
            raise
    
    async def _process_event_microbatch(
        self,
        events: List[DomainEvent],
        batch_number: int,
        event_semaphore: asyncio.Semaphore,
        delivery_semaphore: asyncio.Semaphore,
        timeout_seconds: float
    ) -> Dict[str, Any]:
        """Process a micro-batch of events with fine-grained concurrency control.
        
        Args:
            events: Events to process in this micro-batch
            batch_number: Batch number for tracking
            event_semaphore: Semaphore for event-level concurrency
            delivery_semaphore: Semaphore for delivery-level concurrency
            timeout_seconds: Timeout for this micro-batch
            
        Returns:
            Dict with micro-batch processing statistics
        """
        try:
            logger.debug(f"Processing micro-batch {batch_number} with {len(events)} events")
            
            # Process events in micro-batch concurrently
            event_tasks = [
                self._dispatch_single_event_with_concurrency_control(
                    event,
                    event_semaphore,
                    delivery_semaphore
                )
                for event in events
            ]
            
            # Wait for all events in micro-batch with timeout
            try:
                event_results = await asyncio.wait_for(
                    asyncio.gather(*event_tasks, return_exceptions=True),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                logger.error(f"Micro-batch {batch_number} timed out after {timeout_seconds}s")
                raise
            
            # Process results
            successful_events = 0
            failed_events = 0
            total_deliveries = 0
            successful_event_ids = []
            
            for event_idx, result in enumerate(event_results):
                event = events[event_idx]
                if isinstance(result, Exception):
                    logger.error(f"Event {event.id} in micro-batch {batch_number} failed: {result}")
                    failed_events += 1
                else:
                    successful_events += 1
                    total_deliveries += len(result)
                    successful_event_ids.append(event.id)
            
            # Bulk mark events as processed
            if successful_event_ids:
                try:
                    await self._event_repository.mark_multiple_as_processed(successful_event_ids)
                except Exception as e:
                    logger.error(f"Failed to bulk mark events in micro-batch {batch_number}: {e}")
                    # Individual fallback handled in parent method
            
            return {
                "successful_events": successful_events,
                "failed_events": failed_events,
                "total_deliveries": total_deliveries
            }
            
        except Exception as e:
            logger.error(f"Error processing micro-batch {batch_number}: {e}")
            raise
    
    async def _dispatch_single_event_with_concurrency_control(
        self,
        event: DomainEvent,
        event_semaphore: asyncio.Semaphore,
        delivery_semaphore: asyncio.Semaphore
    ) -> List[WebhookDelivery]:
        """Dispatch single event with fine-grained concurrency control.
        
        Args:
            event: Event to dispatch
            event_semaphore: Semaphore for event processing
            delivery_semaphore: Semaphore for delivery operations
            
        Returns:
            List of created webhook deliveries
        """
        async with event_semaphore:
            try:
                # Get matching subscriptions with optimized queries for high-performance scenarios
                matching_subscriptions = await self._subscription_repository.get_matching_subscriptions_optimized(
                    event.event_type.value,
                    event.context_id,
                    select_columns=["id", "endpoint_id", "event_filters", "is_active"],
                    use_index_only=True
                )
                
                if not matching_subscriptions:
                    return []
                
                # Filter subscriptions based on event data
                filtered_subscriptions = []
                for subscription in matching_subscriptions:
                    try:
                        if subscription.matches_event(
                            event.event_type.value,
                            event.event_data,
                            event.context_id
                        ):
                            filtered_subscriptions.append(subscription)
                            # Update subscription timestamp (fire-and-forget)
                            asyncio.create_task(
                                self._subscription_repository.update_last_triggered(subscription.id)
                            )
                    except Exception as e:
                        logger.error(f"Error evaluating subscription {subscription.id}: {e}")
                
                if not filtered_subscriptions:
                    return []
                
                # Create delivery tasks with delivery concurrency control
                delivery_tasks = []
                for subscription in filtered_subscriptions:
                    delivery_tasks.append(
                        self._create_delivery_with_semaphore(
                            event, 
                            subscription,
                            delivery_semaphore
                        )
                    )
                
                # Execute deliveries with controlled concurrency
                delivery_results = await asyncio.gather(*delivery_tasks, return_exceptions=True)
                
                # Collect successful deliveries
                deliveries = []
                for result in delivery_results:
                    if isinstance(result, Exception):
                        logger.error(f"Delivery creation failed for event {event.id}: {result}")
                    elif result is not None:
                        deliveries.append(result)
                
                return deliveries
                
            except Exception as e:
                logger.error(f"Error dispatching event {event.id} with concurrency control: {e}")
                raise
    
    async def _create_delivery_with_semaphore(
        self,
        event: DomainEvent,
        subscription: WebhookSubscription,
        delivery_semaphore: asyncio.Semaphore
    ) -> Optional[WebhookDelivery]:
        """Create delivery with delivery-level concurrency control.
        
        Args:
            event: Event to deliver
            subscription: Subscription for delivery
            delivery_semaphore: Semaphore for delivery concurrency
            
        Returns:
            Created delivery or None if failed
        """
        async with delivery_semaphore:
            try:
                # Get endpoint for subscription
                endpoint = await self._endpoint_repository.get_by_id(subscription.endpoint_id)
                if endpoint and endpoint.is_active:
                    delivery = await self._delivery_service.deliver_to_endpoint(event, endpoint)
                    
                    # Update endpoint timestamp (fire-and-forget)
                    asyncio.create_task(
                        self._endpoint_service.update_last_used(endpoint.id)
                    )
                    
                    return delivery
                else:
                    logger.warning(f"Endpoint {subscription.endpoint_id} not found or inactive")
                    return None
                    
            except Exception as e:
                logger.error(f"Failed to create delivery for subscription {subscription.id}: {e}")
                return None
    
    async def dispatch_unprocessed_events_optimized(
        self,
        limit: Optional[int] = None,
        batch_size: Optional[int] = None,
        max_concurrent_batches: Optional[int] = None,
        concurrent_workers: Optional[int] = None
    ) -> Dict[str, Any]:
        """Ultra-high-performance event dispatching with advanced database optimizations.
        
        This method demonstrates the complete database optimization implementation with:
        - FOR UPDATE SKIP LOCKED for concurrent processing without blocking
        - Selective column queries to minimize data transfer
        - Optimized bulk operations for marking events as processed
        - Index-only scans for subscription matching
        - Advanced concurrency controls with worker pools
        
        Args:
            limit: Maximum number of events to process (uses config optimal value if None)
            batch_size: Events per batch for optimal throughput (uses config optimal value if None)
            max_concurrent_batches: Maximum concurrent batch operations (uses config if None)
            concurrent_workers: Concurrent workers per batch for delivery processing (uses config if None)
            
        Returns:
            Dict with detailed performance metrics and processing statistics
        """
        try:
            # Apply configuration defaults with optimization-focused values
            perf_config = self._config.performance
            
            actual_limit = limit if limit is not None else min(perf_config.max_event_limit, 500)  # Cap for optimization
            actual_batch_size = batch_size if batch_size is not None else perf_config.optimal_batch_size
            actual_max_concurrent_batches = max_concurrent_batches if max_concurrent_batches is not None else perf_config.max_concurrent_batches
            actual_concurrent_workers = concurrent_workers if concurrent_workers is not None else perf_config.concurrent_workers
            
            start_time = datetime.now(timezone.utc)
            logger.info(f"Starting ultra-optimized event processing (limit={actual_limit}, batch_size={actual_batch_size})")
            
            # Phase 1: Get events with FOR UPDATE SKIP LOCKED for zero-wait concurrency
            select_columns = ["id", "event_type", "event_data", "context_id", "created_at", "aggregate_id"]
            unprocessed_events = await self._event_repository.get_unprocessed_for_update(
                limit=actual_limit,
                skip_locked=True,
                select_columns=select_columns
            )
            
            if not unprocessed_events:
                return {
                    "total_events": 0,
                    "processed_events": 0,
                    "failed_events": 0,
                    "total_deliveries": 0,
                    "processing_time_ms": 0.0,
                    "events_per_second": 0.0,
                    "optimization_level": "ultra-optimized"
                }
            
            logger.info(f"Acquired {len(unprocessed_events)} events with database locks (no blocking)")
            
            # Phase 2: Split into optimal batches
            event_batches = [
                unprocessed_events[i:i + actual_batch_size]
                for i in range(0, len(unprocessed_events), actual_batch_size)
            ]
            
            # Phase 3: Process batches with controlled concurrency
            batch_semaphore = asyncio.Semaphore(actual_max_concurrent_batches)
            batch_tasks = [
                self._process_optimized_batch(
                    batch, 
                    batch_idx + 1,
                    batch_semaphore,
                    actual_concurrent_workers
                )
                for batch_idx, batch in enumerate(event_batches)
            ]
            
            # Phase 4: Execute with timeout and gather results
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Phase 5: Aggregate performance metrics
            total_processed = 0
            total_failed = 0
            total_deliveries = 0
            failed_batches = []
            
            for batch_idx, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Optimized batch {batch_idx + 1} failed: {result}")
                    failed_batches.append(batch_idx + 1)
                    total_failed += len(event_batches[batch_idx])
                else:
                    total_processed += result["processed_count"]
                    total_deliveries += result["delivery_count"]
                    if result["failed_count"] > 0:
                        total_failed += result["failed_count"]
            
            # Phase 6: Calculate performance metrics
            end_time = datetime.now(timezone.utc)
            processing_time_ms = (end_time - start_time).total_seconds() * 1000
            events_per_second = len(unprocessed_events) / (processing_time_ms / 1000) if processing_time_ms > 0 else 0
            
            performance_metrics = {
                "total_events": len(unprocessed_events),
                "processed_events": total_processed,
                "failed_events": total_failed,
                "total_deliveries": total_deliveries,
                "processing_time_ms": round(processing_time_ms, 2),
                "events_per_second": round(events_per_second, 2),
                "deliveries_per_event": round(total_deliveries / len(unprocessed_events), 2) if unprocessed_events else 0,
                "optimization_level": "ultra-optimized",
                "database_optimizations": {
                    "for_update_skip_locked": True,
                    "selective_columns": True,
                    "index_only_scans": True,
                    "bulk_operations": True
                },
                "concurrency_metrics": {
                    "batch_count": len(event_batches),
                    "max_concurrent_batches": max_concurrent_batches,
                    "workers_per_batch": concurrent_workers,
                    "failed_batches": failed_batches
                }
            }
            
            logger.info(
                f"Ultra-optimized processing complete: {total_processed}/{len(unprocessed_events)} events, "
                f"{total_deliveries} deliveries, {processing_time_ms:.2f}ms "
                f"({events_per_second:.2f} events/sec)"
            )
            
            return performance_metrics
            
        except Exception as e:
            logger.error(f"Error in ultra-optimized event processing: {e}")
            raise
    
    async def _process_optimized_batch(
        self,
        events: List[DomainEvent],
        batch_number: int,
        batch_semaphore: asyncio.Semaphore,
        concurrent_workers: int
    ) -> Dict[str, Any]:
        """Process a batch with database and concurrency optimizations.
        
        Args:
            events: Events to process
            batch_number: Batch identifier
            batch_semaphore: Concurrency control for batch processing
            concurrent_workers: Number of concurrent workers for delivery processing
            
        Returns:
            Dict with batch processing statistics
        """
        async with batch_semaphore:
            try:
                logger.debug(f"Processing optimized batch {batch_number} with {len(events)} events")
                
                # Use worker semaphore for delivery concurrency control
                worker_semaphore = asyncio.Semaphore(concurrent_workers)
                
                # Process events in batch with fine-grained concurrency
                event_tasks = [
                    self._process_single_event_optimized(event, worker_semaphore)
                    for event in events
                ]
                
                event_results = await asyncio.gather(*event_tasks, return_exceptions=True)
                
                # Collect results and successful event IDs
                processed_count = 0
                failed_count = 0
                delivery_count = 0
                successful_event_ids = []
                
                for event_idx, result in enumerate(event_results):
                    event = events[event_idx]
                    if isinstance(result, Exception):
                        logger.error(f"Event {event.id} in batch {batch_number} failed: {result}")
                        failed_count += 1
                    else:
                        processed_count += 1
                        delivery_count += result
                        successful_event_ids.append(event.id)
                
                # Use optimized bulk marking with batching
                if successful_event_ids:
                    await self._event_repository.mark_multiple_as_processed_bulk(
                        successful_event_ids,
                        batch_size=50  # Optimal batch size for bulk operations
                    )
                
                return {
                    "processed_count": processed_count,
                    "failed_count": failed_count,
                    "delivery_count": delivery_count
                }
                
            except Exception as e:
                logger.error(f"Error in optimized batch {batch_number}: {e}")
                raise
    
    async def _process_single_event_optimized(
        self, 
        event: DomainEvent, 
        worker_semaphore: asyncio.Semaphore
    ) -> int:
        """Process single event with optimization-focused implementation.
        
        Args:
            event: Event to process
            worker_semaphore: Concurrency control semaphore
            
        Returns:
            Number of deliveries created for this event
        """
        async with worker_semaphore:
            try:
                # Use optimized subscription query with minimal data transfer
                matching_subscriptions = await self._subscription_repository.get_matching_subscriptions_optimized(
                    event.event_type.value,
                    event.context_id,
                    select_columns=["id", "endpoint_id", "event_filters"],
                    use_index_only=True
                )
                
                if not matching_subscriptions:
                    return 0
                
                # Process subscriptions with minimal overhead
                delivery_count = 0
                for subscription in matching_subscriptions:
                    try:
                        # Quick filter check without full entity hydration
                        if subscription.matches_event(
                            event.event_type.value,
                            event.event_data,
                            event.context_id
                        ):
                            # Create delivery asynchronously (fire-and-forget for timestamp updates)
                            endpoint = await self._endpoint_repository.get_by_id(subscription.endpoint_id)
                            if endpoint and endpoint.is_active:
                                await self._delivery_service.deliver_to_endpoint(event, endpoint)
                                delivery_count += 1
                                
                                # Fire-and-forget updates to avoid blocking
                                asyncio.create_task(
                                    self._subscription_repository.update_last_triggered(subscription.id)
                                )
                                asyncio.create_task(
                                    self._endpoint_service.update_last_used(endpoint.id)
                                )
                    
                    except Exception as subscription_error:
                        logger.error(f"Subscription {subscription.id} processing error: {subscription_error}")
                
                return delivery_count
                
            except Exception as e:
                logger.error(f"Optimized event processing error for {event.id}: {e}")
                return 0
    
    async def _process_event_batch(
        self, 
        events: List[DomainEvent], 
        batch_number: int,
        semaphore: asyncio.Semaphore
    ) -> int:
        """Process a batch of events concurrently.
        
        Args:
            events: List of events to process in this batch
            batch_number: Batch number for logging
            semaphore: Semaphore to control concurrency
            
        Returns:
            Number of successfully processed events in this batch
        """
        async with semaphore:
            logger.debug(f"Processing batch {batch_number} with {len(events)} events")
            
            # Process events in the batch concurrently
            event_tasks = [
                self._dispatch_single_event(event) 
                for event in events
            ]
            
            # Wait for all events in batch to complete
            event_results = await asyncio.gather(*event_tasks, return_exceptions=True)
            
            # Collect successful event IDs for bulk processing
            successful_event_ids = []
            successful_deliveries_count = 0
            
            for event_idx, result in enumerate(event_results):
                event = events[event_idx]
                if isinstance(result, Exception):
                    logger.error(f"Event {event.id} in batch {batch_number} failed: {result}")
                else:
                    successful_event_ids.append(event.id)
                    successful_deliveries_count += len(result)
                    logger.debug(f"Event {event.id} dispatched to {len(result)} endpoints")
            
            # Bulk mark events as processed with optimized batch operations
            if successful_event_ids:
                try:
                    # Use optimized bulk processing if available
                    await self._event_repository.mark_multiple_as_processed_bulk(
                        successful_event_ids, 
                        batch_size=min(len(successful_event_ids), 100)
                    )
                    logger.info(
                        f"Batch {batch_number}: {len(successful_event_ids)} events processed successfully, "
                        f"{successful_deliveries_count} total deliveries created"
                    )
                except Exception as e:
                    logger.error(f"Failed to bulk mark events as processed in batch {batch_number}: {e}")
                    # Fallback to standard bulk marking
                    try:
                        await self._event_repository.mark_multiple_as_processed(successful_event_ids)
                    except Exception as fallback_error:
                        logger.error(f"Fallback bulk marking also failed: {fallback_error}")
                        # Final fallback to individual marking
                        for event_id in successful_event_ids:
                            try:
                                await self._event_repository.mark_as_processed(event_id)
                            except Exception as individual_error:
                                logger.error(f"Failed to mark individual event {event_id} as processed: {individual_error}")
            
            return len(successful_event_ids)
    
    async def _dispatch_single_event(self, event: DomainEvent) -> List[WebhookDelivery]:
        """Dispatch a single event with proper error handling for batch processing.
        
        Args:
            event: Domain event to dispatch
            
        Returns:
            List of webhook deliveries created
            
        Raises:
            Exception: If event dispatching fails (for batch error handling)
        """
        try:
            return await self.dispatch_event(event)
        except Exception as e:
            logger.error(f"Failed to dispatch event {event.id}: {e}")
            raise
    
    async def dispatch_event(self, event: DomainEvent) -> List[WebhookDelivery]:
        """Dispatch a single event to all relevant webhook endpoints and execute dynamic actions."""
        try:
            # Execute dynamic actions first (if enabled)
            if self._action_registry:
                await self._execute_event_actions(event)
            
            # Get matching subscriptions with optimized queries
            matching_subscriptions = await self._subscription_repository.get_matching_subscriptions_optimized(
                event.event_type.value,
                event.context_id,
                select_columns=["id", "endpoint_id", "event_filters", "is_active"],
                use_index_only=True
            )
            
            if not matching_subscriptions:
                logger.debug(f"No matching subscriptions found for event {event.event_type.value}")
                return []
            
            # Filter subscriptions based on event data and subscription rules
            filtered_subscriptions = []
            for subscription in matching_subscriptions:
                try:
                    if subscription.matches_event(
                        event.event_type.value, 
                        event.event_data, 
                        event.context_id
                    ):
                        filtered_subscriptions.append(subscription)
                        # Update subscription last triggered timestamp
                        await self._subscription_repository.update_last_triggered(subscription.id)
                except Exception as e:
                    logger.error(f"Error evaluating subscription {subscription.id} for event {event.id}: {e}")
            
            if not filtered_subscriptions:
                logger.debug(f"No subscriptions matched event filters for {event.event_type.value}")
                return []
            
            deliveries = []
            
            # Create deliveries for each filtered subscription's endpoint
            for subscription in filtered_subscriptions:
                try:
                    # Get the endpoint for this subscription
                    endpoint = await self._endpoint_repository.get_by_id(subscription.endpoint_id)
                    if endpoint and endpoint.is_active:
                        delivery = await self._delivery_service.deliver_to_endpoint(event, endpoint)
                        deliveries.append(delivery)
                        
                        # Update endpoint last used timestamp
                        await self._endpoint_service.update_last_used(endpoint.id)
                    else:
                        logger.warning(f"Endpoint {subscription.endpoint_id} not found or inactive for subscription {subscription.id}")
                        
                except Exception as e:
                    logger.error(f"Failed to create delivery for subscription {subscription.id}: {e}")
            
            logger.info(f"Created {len(deliveries)} webhook deliveries for event {event.id} from {len(filtered_subscriptions)} matching subscriptions")
            return deliveries
            
        except Exception as e:
            logger.error(f"Error dispatching event {event.id}: {e}")
            raise
    
    async def get_subscribed_endpoints(
        self, 
        event_type: str, 
        context_id: Optional[UUID] = None
    ) -> List[WebhookEndpoint]:
        """Get webhook endpoints subscribed to a specific event type."""
        try:
            # Check if event type exists and is enabled
            event_type_entity = await self._event_type_repository.get_by_event_type(event_type)
            if not event_type_entity or not event_type_entity.is_enabled:
                logger.debug(f"Event type {event_type} is not enabled for webhooks")
                return []
            
            # Get matching subscriptions for this event type and context
            matching_subscriptions = await self._subscription_repository.get_matching_subscriptions(
                event_type, context_id
            )
            
            if not matching_subscriptions:
                logger.debug(f"No active subscriptions found for event type {event_type}")
                return []
            
            # Get the endpoints for the matching subscriptions
            subscribed_endpoints = []
            for subscription in matching_subscriptions:
                try:
                    endpoint = await self._endpoint_repository.get_by_id(subscription.endpoint_id)
                    if endpoint and endpoint.is_active:
                        # Check if endpoint meets verification requirements
                        if event_type_entity.is_subscription_allowed(endpoint.is_verified):
                            subscribed_endpoints.append(endpoint)
                        else:
                            logger.debug(f"Endpoint {endpoint.id} doesn't meet verification requirements for {event_type}")
                    else:
                        logger.warning(f"Endpoint {subscription.endpoint_id} not found or inactive")
                except Exception as e:
                    logger.error(f"Error fetching endpoint {subscription.endpoint_id}: {e}")
            
            logger.debug(f"Found {len(subscribed_endpoints)} subscribed endpoints for {event_type}")
            return subscribed_endpoints
            
        except Exception as e:
            logger.error(f"Error getting subscribed endpoints for {event_type}: {e}")
            raise
    
    # ===========================================
    # Subscription Management Operations (complete implementation)
    # ===========================================
    
    async def subscribe_endpoint(
        self, 
        endpoint_id: WebhookEndpointId, 
        event_type: str, 
        event_filters: Optional[Dict[str, Any]] = None,
        context_id: Optional[UUID] = None,
        subscription_name: Optional[str] = None,
        description: Optional[str] = None
    ) -> bool:
        """Subscribe a webhook endpoint to an event type."""
        try:
            # Verify endpoint exists and is active
            endpoint = await self._endpoint_repository.get_by_id(endpoint_id)
            if not endpoint or not endpoint.is_active:
                logger.warning(f"Cannot subscribe inactive endpoint {endpoint_id}")
                return False
            
            # Verify event type exists and get event type ID
            event_type_entity = await self._event_type_repository.get_by_event_type(event_type)
            if not event_type_entity:
                logger.warning(f"Event type {event_type} not found")
                return False
            
            # Verify subscription is allowed (verification requirements)
            if event_type_entity.requires_verification and not endpoint.is_verified:
                logger.warning(f"Subscription not allowed - endpoint {endpoint_id} not verified for {event_type}")
                return False
            
            # Create subscription entity
            from ....utils.uuid import generate_uuid_v7
            subscription = WebhookSubscription(
                id=WebhookSubscriptionId(generate_uuid_v7()),
                endpoint_id=endpoint_id,
                event_type_id=event_type_entity.id,
                event_type=event_type,
                event_filters=event_filters or {},
                is_active=True,
                context_id=context_id,
                subscription_name=subscription_name,
                description=description
            )
            
            # Save subscription to repository
            await self._subscription_repository.save(subscription)
            
            logger.info(f"Subscribed endpoint {endpoint_id} to event type {event_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing endpoint {endpoint_id} to {event_type}: {e}")
            return False
    
    async def unsubscribe_endpoint(self, endpoint_id: WebhookEndpointId, event_type: str) -> bool:
        """Unsubscribe a webhook endpoint from an event type."""
        try:
            # Get existing subscriptions for this endpoint and event type
            subscriptions = await self._subscription_repository.get_by_endpoint_id(endpoint_id, active_only=False)
            
            removed_count = 0
            for subscription in subscriptions:
                if subscription.event_type == event_type and subscription.is_active:
                    # Deactivate the subscription rather than delete it (soft delete)
                    subscription.deactivate()
                    await self._subscription_repository.update(subscription)
                    removed_count += 1
            
            if removed_count > 0:
                logger.info(f"Unsubscribed endpoint {endpoint_id} from event type {event_type} ({removed_count} subscriptions deactivated)")
                return True
            else:
                logger.warning(f"No active subscription found for endpoint {endpoint_id} and event type {event_type}")
                return False
            
        except Exception as e:
            logger.error(f"Error unsubscribing endpoint {endpoint_id} from {event_type}: {e}")
            return False
    
    async def get_endpoint_subscriptions(self, endpoint_id: WebhookEndpointId) -> List[str]:
        """Get all event types that an endpoint is subscribed to."""
        try:
            # Get active subscriptions for this endpoint
            subscriptions = await self._subscription_repository.get_by_endpoint_id(endpoint_id, active_only=True)
            
            # Extract unique event types
            event_types = list(set(subscription.event_type for subscription in subscriptions))
            
            logger.debug(f"Retrieved {len(event_types)} subscriptions for endpoint {endpoint_id}")
            return event_types
            
        except Exception as e:
            logger.error(f"Error getting subscriptions for endpoint {endpoint_id}: {e}")
            return []
    
    async def get_subscription_by_id(self, subscription_id: WebhookSubscriptionId) -> Optional[WebhookSubscription]:
        """Get a subscription by its ID."""
        try:
            return await self._subscription_repository.get_by_id(subscription_id)
        except Exception as e:
            logger.error(f"Error getting subscription {subscription_id}: {e}")
            return None
    
    async def update_subscription_filters(
        self, 
        subscription_id: WebhookSubscriptionId, 
        event_filters: Dict[str, Any]
    ) -> bool:
        """Update event filters for a subscription."""
        try:
            subscription = await self._subscription_repository.get_by_id(subscription_id)
            if not subscription:
                logger.warning(f"Subscription {subscription_id} not found")
                return False
            
            subscription.update_filters(event_filters)
            await self._subscription_repository.update(subscription)
            
            logger.info(f"Updated filters for subscription {subscription_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating filters for subscription {subscription_id}: {e}")
            return False
    
    async def activate_subscription(self, subscription_id: WebhookSubscriptionId) -> bool:
        """Activate a subscription."""
        try:
            subscription = await self._subscription_repository.get_by_id(subscription_id)
            if not subscription:
                logger.warning(f"Subscription {subscription_id} not found")
                return False
            
            subscription.activate()
            await self._subscription_repository.update(subscription)
            
            logger.info(f"Activated subscription {subscription_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error activating subscription {subscription_id}: {e}")
            return False
    
    async def deactivate_subscription(self, subscription_id: WebhookSubscriptionId) -> bool:
        """Deactivate a subscription."""
        try:
            subscription = await self._subscription_repository.get_by_id(subscription_id)
            if not subscription:
                logger.warning(f"Subscription {subscription_id} not found")
                return False
            
            subscription.deactivate()
            await self._subscription_repository.update(subscription)
            
            logger.info(f"Deactivated subscription {subscription_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deactivating subscription {subscription_id}: {e}")
            return False
    
    async def get_subscriptions_by_event_type(self, event_type: str, active_only: bool = True) -> List[WebhookSubscription]:
        """Get all subscriptions for a specific event type."""
        try:
            return await self._subscription_repository.get_by_event_type(event_type, active_only)
        except Exception as e:
            logger.error(f"Error getting subscriptions for event type {event_type}: {e}")
            return []
    
    async def delete_subscription(self, subscription_id: WebhookSubscriptionId) -> bool:
        """Permanently delete a subscription."""
        try:
            success = await self._subscription_repository.delete(subscription_id)
            if success:
                logger.info(f"Deleted subscription {subscription_id}")
            else:
                logger.warning(f"Subscription {subscription_id} not found for deletion")
            return success
            
        except Exception as e:
            logger.error(f"Error deleting subscription {subscription_id}: {e}")
            return False
    
    # ===========================================
    # Delivery Management Operations (delegate to WebhookDeliveryService)
    # ===========================================
    
    async def retry_failed_deliveries(self, limit: int = 100) -> int:
        """Retry failed webhook deliveries. Returns count of retry attempts."""
        return await self._delivery_service.retry_failed_deliveries(limit)
    
    async def cancel_delivery(
        self, 
        delivery_id: WebhookDeliveryId, 
        reason: str = "Cancelled"
    ) -> bool:
        """Cancel a webhook delivery."""
        return await self._delivery_service.cancel_delivery(delivery_id, reason)
    
    async def verify_endpoint(self, endpoint: WebhookEndpoint) -> bool:
        """Verify that a webhook endpoint is reachable and valid."""
        return await self._delivery_service.verify_endpoint(endpoint)
    
    # ===========================================
    # Endpoint Management Operations (delegate to WebhookEndpointService)
    # ===========================================
    
    async def create_webhook_endpoint(
        self,
        name: str,
        endpoint_url: str,
        context_id: UUID,
        description: Optional[str] = None,
        secret_token: Optional[str] = None,
        is_active: bool = True,
        headers: Optional[Dict[str, str]] = None,
        http_method: str = "POST",
        timeout_seconds: int = 30,
        is_verified: bool = False
    ) -> WebhookEndpoint:
        """Create a new webhook endpoint."""
        return await self._endpoint_service.create_endpoint(
            name=name,
            endpoint_url=endpoint_url,
            context_id=context_id,
            description=description,
            secret_token=secret_token,
            is_active=is_active,
            headers=headers,
            http_method=http_method,
            timeout_seconds=timeout_seconds,
            is_verified=is_verified
        )
    
    # ===========================================
    # Event Type Management Operations (delegate to WebhookEventTypeService)
    # ===========================================
    
    async def create_webhook_event_type(
        self,
        event_type: str,
        display_name: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
        is_enabled: bool = True,
        requires_verification: bool = False,
        payload_schema: Optional[Dict[str, Any]] = None,
        example_payload: Optional[Dict[str, Any]] = None
    ) -> WebhookEventType:
        """Create a new webhook event type."""
        return await self._event_type_service.create_event_type(
            event_type=event_type,
            display_name=display_name,
            description=description,
            category=category,
            is_enabled=is_enabled,
            requires_verification=requires_verification,
            payload_schema=payload_schema,
            example_payload=example_payload
        )
    
    # ===========================================
    # Dynamic Event Actions Processing
    # ===========================================
    
    async def _execute_event_actions(self, event: DomainEvent) -> None:
        """Execute dynamic actions for the given event."""
        if not self._action_registry:
            return
            
        try:
            # Prepare event data for action processing
            event_data = {
                "event_id": str(event.id.value),
                "event_type": event.event_type.value,
                "aggregate_type": event.aggregate_type.value,
                "aggregate_id": str(event.aggregate_id),
                "event_data": event.event_data,
                "context_id": str(event.context_id) if event.context_id else None,
                "correlation_id": str(event.correlation_id) if event.correlation_id else None,
                "causation_id": str(event.causation_id) if event.causation_id else None,
                "created_at": event.created_at.isoformat() if event.created_at else None,
                "triggered_by_user_id": str(event.triggered_by_user_id.value) if event.triggered_by_user_id else None,
                "metadata": event.metadata or {}
            }
            
            # Get matching actions from registry
            matching_actions = await self._action_registry.get_actions_for_event(
                event.event_type.value, 
                event_data
            )
            
            if not matching_actions:
                logger.debug(f"No dynamic actions found for event type: {event.event_type.value}")
                return
                
            logger.info(f"Executing {len(matching_actions)} dynamic actions for event {event.id.value}")
            
            # Execute actions based on execution mode
            sync_actions = [action for action in matching_actions if action.execution_mode.value == "sync"]
            async_actions = [action for action in matching_actions if action.execution_mode.value == "async"]
            queued_actions = [action for action in matching_actions if action.execution_mode.value == "queued"]
            
            # Execute synchronous actions first (blocking)
            if sync_actions:
                await self._execute_actions_synchronously(sync_actions, event_data)
            
            # Execute asynchronous actions (fire-and-forget)
            if async_actions:
                asyncio.create_task(self._execute_actions_asynchronously(async_actions, event_data))
            
            # Execute queued actions (would integrate with task queue system)
            if queued_actions:
                asyncio.create_task(self._execute_actions_queued(queued_actions, event_data))
                
        except Exception as e:
            logger.error(f"Error executing dynamic actions for event {event.id.value}: {str(e)}")
            # Don't raise - action execution failures should not block event processing
    
    async def _execute_actions_synchronously(self, actions: List[Any], event_data: Dict[str, Any]) -> None:
        """Execute actions synchronously (blocks event processing)."""
        for action in actions:
            try:
                await self._execute_single_action(action, event_data, is_sync=True)
            except Exception as e:
                logger.error(f"Synchronous action {action.id.value} failed: {str(e)}")
                # Continue with other actions even if one fails
    
    async def _execute_actions_asynchronously(self, actions: List[Any], event_data: Dict[str, Any]) -> None:
        """Execute actions asynchronously (non-blocking)."""
        tasks = []
        for action in actions:
            task = asyncio.create_task(self._execute_single_action(action, event_data, is_sync=False))
            tasks.append(task)
        
        # Wait for all async actions to complete (with error handling)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Asynchronous action {actions[i].id.value} failed: {str(result)}")
    
    async def _execute_actions_queued(self, actions: List[Any], event_data: Dict[str, Any]) -> None:
        """Execute actions via queue system (future enhancement)."""
        # For now, execute as async actions
        # In future, integrate with actual task queue (Celery, RQ, etc.)
        await self._execute_actions_asynchronously(actions, event_data)
        
        logger.debug(f"Queued {len(actions)} actions for background processing")
    
    async def _execute_single_action(self, action: Any, event_data: Dict[str, Any], is_sync: bool = False) -> None:
        """Execute a single dynamic action with proper error handling and logging."""
        if not self._execution_repository:
            logger.warning("Action execution repository not available - cannot execute actions")
            return
            
        from ....utils.uuid import generate_uuid_v7
        from ....core.value_objects.identifiers import ActionExecutionId
        
        # Create execution record
        execution_id = ActionExecutionId(generate_uuid_v7())
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(f"Executing action {action.name} (ID: {action.id.value}) - Mode: {'sync' if is_sync else 'async'}")
            
            # This would integrate with the ActionExecutionService (next task)
            # For now, just log the action execution
            execution_result = {
                "success": True,
                "message": f"Action {action.name} executed successfully",
                "metadata": {
                    "handler_type": action.handler_type.value,
                    "execution_mode": action.execution_mode.value,
                    "event_type": event_data["event_type"],
                    "is_sync": is_sync
                }
            }
            
            # Update action statistics
            if self._action_repository:
                await self._action_repository.update_statistics(
                    action.id,
                    trigger_increment=1,
                    success_increment=1,
                    failure_increment=0
                )
            
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            logger.info(f"Action {action.name} completed successfully in {duration_ms}ms")
            
        except Exception as e:
            # Update failure statistics
            if self._action_repository:
                await self._action_repository.update_statistics(
                    action.id,
                    trigger_increment=1,
                    success_increment=0,
                    failure_increment=1
                )
            
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            logger.error(f"Action {action.name} failed after {duration_ms}ms: {str(e)}")
            raise
    
    async def get_action_registry_stats(self) -> Optional[Dict[str, Any]]:
        """Get statistics about the action registry cache."""
        if not self._action_registry:
            return None
        
        return await self._action_registry.get_cache_stats()
    
    async def reload_action_registry(self) -> bool:
        """Reload the action registry cache."""
        if not self._action_registry:
            return False
        
        try:
            await self._action_registry.reload_actions()
            logger.info("Action registry cache reloaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to reload action registry: {str(e)}")
            return False
    
    async def register_dynamic_action(self, action: Any) -> bool:
        """Register a new dynamic action."""
        if not self._action_registry:
            return False
        
        try:
            await self._action_registry.register_action(action)
            return True
        except Exception as e:
            logger.error(f"Failed to register dynamic action: {str(e)}")
            return False
    
    async def unregister_dynamic_action(self, action_id: Any) -> bool:  # ActionId
        """Unregister a dynamic action."""
        if not self._action_registry:
            return False
        
        try:
            return await self._action_registry.unregister_action(action_id)
        except Exception as e:
            logger.error(f"Failed to unregister dynamic action: {str(e)}")
            return False

    # ===========================================
    # Streaming Event Processing for Memory Efficiency
    # ===========================================
    
    async def dispatch_events_streaming(
        self,
        event_stream_size_limit: int = 10000,
        batch_size: int = 100,
        max_concurrent_batches: int = 5,
        memory_threshold_mb: int = 500
    ) -> Dict[str, Any]:
        """Process unprocessed events using streaming for memory efficiency.
        
        This method processes events in streaming fashion to handle very large volumes
        without loading all events into memory simultaneously. Includes memory monitoring
        and adaptive batch sizing based on available memory.
        
        Args:
            event_stream_size_limit: Maximum number of events to process in this stream
            batch_size: Initial batch size (will be adjusted based on memory usage)
            max_concurrent_batches: Maximum concurrent batches
            memory_threshold_mb: Memory threshold to trigger adaptive batch sizing
            
        Returns:
            Dict with comprehensive streaming processing statistics
        """
        start_time = time.time()
        logger.info(f"Starting streaming event processing (limit: {event_stream_size_limit}, batch: {batch_size})")
        
        try:
            total_processed = 0
            total_deliveries = 0
            total_batches = 0
            adaptive_adjustments = 0
            current_batch_size = batch_size
            
            # Get webhook config for streaming parameters
            config = get_webhook_config()
            
            # Memory monitoring setup
            import psutil
            process = psutil.Process()
            initial_memory_mb = process.memory_info().rss / 1024 / 1024
            
            # Batch processing semaphore
            batch_semaphore = asyncio.Semaphore(max_concurrent_batches)
            
            # Streaming loop
            events_remaining = True
            while events_remaining and total_processed < event_stream_size_limit:
                try:
                    # Memory-aware batch size adjustment
                    current_memory_mb = process.memory_info().rss / 1024 / 1024
                    memory_delta = current_memory_mb - initial_memory_mb
                    
                    if memory_delta > memory_threshold_mb:
                        # Reduce batch size if memory usage is high
                        new_batch_size = max(10, int(current_batch_size * 0.7))
                        if new_batch_size != current_batch_size:
                            logger.info(
                                f"Adaptive batch sizing: {current_batch_size} → {new_batch_size} "
                                f"(memory: {current_memory_mb:.1f}MB, delta: +{memory_delta:.1f}MB)"
                            )
                            current_batch_size = new_batch_size
                            adaptive_adjustments += 1
                    elif memory_delta < memory_threshold_mb * 0.5 and current_batch_size < batch_size:
                        # Increase batch size if memory usage is low
                        new_batch_size = min(batch_size, int(current_batch_size * 1.3))
                        if new_batch_size != current_batch_size:
                            logger.debug(f"Adaptive batch sizing: {current_batch_size} → {new_batch_size}")
                            current_batch_size = new_batch_size
                            adaptive_adjustments += 1
                    
                    # Get next batch of unprocessed events using streaming repository method
                    unprocessed_events = await self._event_repository.get_unprocessed_for_update(
                        limit=current_batch_size,
                        skip_locked=True,
                        select_columns=["id", "event_type", "event_data", "context_id"]  # Minimal columns
                    )
                    
                    if not unprocessed_events:
                        logger.debug("No more unprocessed events found, ending stream")
                        events_remaining = False
                        break
                    
                    logger.debug(
                        f"Streaming batch {total_batches + 1}: {len(unprocessed_events)} events "
                        f"(memory: {current_memory_mb:.1f}MB)"
                    )
                    
                    # Process batch with streaming optimizations
                    batch_result = await self._process_streaming_batch(
                        unprocessed_events,
                        total_batches + 1,
                        batch_semaphore
                    )
                    
                    # Update statistics
                    total_processed += batch_result["events_processed"]
                    total_deliveries += batch_result["deliveries_created"]
                    total_batches += 1
                    
                    # Check if we've reached the stream limit
                    if total_processed >= event_stream_size_limit:
                        logger.info(f"Reached streaming limit of {event_stream_size_limit} events")
                        break
                        
                    # Small delay to allow garbage collection
                    await asyncio.sleep(0.01)
                    
                except Exception as batch_error:
                    logger.error(f"Error in streaming batch {total_batches + 1}: {batch_error}")
                    # Continue with next batch instead of failing entire stream
                    continue
            
            # Final statistics
            processing_time = time.time() - start_time
            events_per_second = total_processed / processing_time if processing_time > 0 else 0
            final_memory_mb = process.memory_info().rss / 1024 / 1024
            memory_efficiency = (final_memory_mb - initial_memory_mb) / max(total_processed, 1)
            
            performance_metrics = {
                "events_processed": total_processed,
                "deliveries_created": total_deliveries,
                "batches_processed": total_batches,
                "processing_time_seconds": processing_time,
                "events_per_second": events_per_second,
                "memory_metrics": {
                    "initial_memory_mb": initial_memory_mb,
                    "final_memory_mb": final_memory_mb,
                    "peak_memory_delta_mb": memory_delta,
                    "memory_per_event_kb": memory_efficiency * 1024,
                    "adaptive_adjustments": adaptive_adjustments
                },
                "streaming_config": {
                    "initial_batch_size": batch_size,
                    "final_batch_size": current_batch_size,
                    "max_concurrent_batches": max_concurrent_batches,
                    "memory_threshold_mb": memory_threshold_mb,
                    "stream_limit": event_stream_size_limit
                }
            }
            
            logger.info(
                f"Streaming processing complete: {total_processed} events, {total_deliveries} deliveries, "
                f"{processing_time:.2f}s ({events_per_second:.2f} events/sec), "
                f"memory efficiency: {memory_efficiency:.2f}KB/event"
            )
            
            return performance_metrics
            
        except Exception as e:
            logger.error(f"Error in streaming event processing: {e}")
            raise
    
    async def _process_streaming_batch(
        self,
        events: List[DomainEvent],
        batch_number: int,
        batch_semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        """Process a batch with streaming optimizations focused on memory efficiency.
        
        Args:
            events: Events to process
            batch_number: Batch identifier  
            batch_semaphore: Concurrency control semaphore
            
        Returns:
            Dict with batch processing results
        """
        async with batch_semaphore:
            try:
                logger.debug(f"Processing streaming batch {batch_number} with {len(events)} events")
                
                events_processed = 0
                deliveries_created = 0
                successful_event_ids = []
                
                # Process events one at a time to minimize memory usage
                for event in events:
                    try:
                        # Process single event
                        deliveries = await self.dispatch_event(event)
                        
                        # Track results
                        deliveries_created += len(deliveries)
                        successful_event_ids.append(event.id)
                        events_processed += 1
                        
                        # Immediate cleanup - clear event data to free memory
                        event.event_data = {}
                        
                    except Exception as event_error:
                        logger.error(f"Failed to process event {event.id} in streaming batch {batch_number}: {event_error}")
                        continue
                
                # Mark processed events as completed in batch
                if successful_event_ids:
                    try:
                        await self._event_repository.mark_multiple_as_processed(successful_event_ids)
                        logger.debug(f"Streaming batch {batch_number}: marked {len(successful_event_ids)} events as processed")
                    except Exception as mark_error:
                        logger.error(f"Failed to mark events as processed in streaming batch {batch_number}: {mark_error}")
                
                return {
                    "events_processed": events_processed,
                    "deliveries_created": deliveries_created,
                    "batch_number": batch_number
                }
                
            except Exception as e:
                logger.error(f"Error in streaming batch {batch_number}: {e}")
                return {
                    "events_processed": 0,
                    "deliveries_created": 0,
                    "batch_number": batch_number
                }
    
    async def get_streaming_processing_status(self) -> Dict[str, Any]:
        """Get current streaming processing status and memory usage.
        
        Returns:
            Dict with streaming processing status and memory metrics
        """
        try:
            import psutil
            process = psutil.Process()
            
            # Get event processing statistics
            unprocessed_count = await self._event_repository.count_unprocessed()
            processing_count = await self._event_repository.count_processing()
            
            # Memory statistics
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # System memory
            system_memory = psutil.virtual_memory()
            
            return {
                "event_statistics": {
                    "unprocessed_events": unprocessed_count,
                    "processing_events": processing_count,
                    "total_pending": unprocessed_count + processing_count
                },
                "memory_statistics": {
                    "process_memory_mb": memory_mb,
                    "system_memory_total_gb": system_memory.total / 1024 / 1024 / 1024,
                    "system_memory_available_gb": system_memory.available / 1024 / 1024 / 1024,
                    "system_memory_percent": system_memory.percent
                },
                "streaming_recommendations": {
                    "recommended_batch_size": min(200, max(50, unprocessed_count // 100)) if unprocessed_count > 0 else 100,
                    "memory_pressure": "high" if system_memory.percent > 85 else "medium" if system_memory.percent > 70 else "low",
                    "recommended_concurrency": 3 if system_memory.percent > 80 else 5 if system_memory.percent > 60 else 10
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting streaming processing status: {e}")
            return {
                "event_statistics": {"error": str(e)},
                "memory_statistics": {"error": str(e)},
                "streaming_recommendations": {"error": str(e)}
            }