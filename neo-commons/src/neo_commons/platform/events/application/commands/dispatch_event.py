"""Dispatch event command for platform events infrastructure.

This module handles ONLY event dispatching operations following maximum separation architecture.
Single responsibility: Coordinate the dispatching of domain events to webhook endpoints.

Pure application layer - no infrastructure concerns.
Uses protocols for dependency injection and clean architecture compliance.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime
from uuid import UUID

from ...core.protocols import EventDispatcher, EventRepository
from ...core.entities import DomainEvent, WebhookDelivery
from ...core.value_objects import EventId
from ...core.exceptions import EventDispatchFailed
from neo_commons.core.value_objects import UserId
from neo_commons.utils import utc_now, generate_uuid_v7


@dataclass
class DispatchEventData:
    """Data required to dispatch an event.
    
    Contains only the essential data needed for event dispatching operations.
    Separates data from business logic following CQRS patterns.
    """
    event_id: EventId
    force_dispatch: bool = False
    retry_failed_deliveries: bool = False
    max_concurrent_deliveries: Optional[int] = None
    timeout_seconds: Optional[float] = None


@dataclass 
class DispatchEventResult:
    """Result of event dispatch operation.
    
    Contains comprehensive dispatch results for monitoring and tracking.
    Provides structured feedback about the dispatch process.
    """
    event_id: EventId
    dispatched_successfully: bool
    webhook_deliveries_created: List[WebhookDelivery]
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    processing_time_ms: float
    error_message: Optional[str] = None


class DispatchEventCommand:
    """Command to dispatch a domain event to webhook endpoints.
    
    Single responsibility: Orchestrate the dispatching of a domain event
    to all relevant webhook subscribers. Handles event retrieval, subscription
    matching, delivery coordination, and result aggregation.
    
    Following enterprise command pattern with protocol-based dependencies.
    Pure application logic - delegates infrastructure concerns to protocols.
    """
    
    def __init__(
        self,
        event_dispatcher: EventDispatcher,
        event_repository: EventRepository
    ):
        """Initialize dispatch event command with required dependencies.
        
        Args:
            event_dispatcher: Protocol for dispatching events to webhooks
            event_repository: Protocol for event data access operations
        """
        self._event_dispatcher = event_dispatcher
        self._event_repository = event_repository
    
    async def execute(self, data: DispatchEventData) -> DispatchEventResult:
        """Execute event dispatch command.
        
        Orchestrates the complete event dispatching process:
        1. Retrieve event from repository
        2. Validate event is ready for dispatch  
        3. Dispatch to webhook endpoints
        4. Track delivery results
        5. Update event processing status
        6. Return comprehensive results
        
        Args:
            data: Event dispatch configuration data
            
        Returns:
            DispatchEventResult with comprehensive dispatch information
            
        Raises:
            EventDispatchFailed: If event dispatching fails
        """
        start_time = utc_now()
        
        try:
            # 1. Retrieve event from repository
            event = await self._event_repository.get_event_by_id(data.event_id)
            if not event:
                raise EventDispatchFailed(
                    f"Event with ID {data.event_id.value} not found",
                    event_id=data.event_id
                )
            
            # 2. Validate event is eligible for dispatch
            if not data.force_dispatch:
                await self._validate_event_for_dispatch(event)
            
            # 3. Dispatch event to webhook endpoints
            webhook_deliveries = await self._event_dispatcher.dispatch_event(event)
            
            # 4. Calculate processing metrics
            end_time = utc_now()
            processing_time_ms = (end_time - start_time).total_seconds() * 1000
            
            # 5. Aggregate delivery results
            total_deliveries = len(webhook_deliveries)
            successful_deliveries = len([d for d in webhook_deliveries if d.is_successful()])
            failed_deliveries = total_deliveries - successful_deliveries
            
            # 6. Update event processing status
            await self._update_event_dispatch_status(
                event_id=data.event_id,
                dispatched_successfully=failed_deliveries == 0,
                total_deliveries=total_deliveries
            )
            
            # 7. Handle retry of failed deliveries if requested
            if data.retry_failed_deliveries and failed_deliveries > 0:
                await self._retry_failed_deliveries(webhook_deliveries)
            
            return DispatchEventResult(
                event_id=data.event_id,
                dispatched_successfully=failed_deliveries == 0,
                webhook_deliveries_created=webhook_deliveries,
                total_deliveries=total_deliveries,
                successful_deliveries=successful_deliveries,
                failed_deliveries=failed_deliveries,
                processing_time_ms=processing_time_ms
            )
            
        except Exception as e:
            # Calculate processing time for failed operations
            end_time = utc_now()
            processing_time_ms = (end_time - start_time).total_seconds() * 1000
            
            # Update event with failure status
            await self._update_event_dispatch_status(
                event_id=data.event_id,
                dispatched_successfully=False,
                error_message=str(e)
            )
            
            # Wrap in domain exception
            if not isinstance(e, EventDispatchFailed):
                raise EventDispatchFailed(
                    f"Failed to dispatch event {data.event_id.value}: {str(e)}",
                    event_id=data.event_id,
                    original_error=e
                ) from e
            
            raise
    
    async def execute_by_event(self, event: DomainEvent) -> DispatchEventResult:
        """Execute event dispatch directly with event entity.
        
        Convenience method for dispatching when you already have the event entity.
        Delegates to main execute method for consistency.
        
        Args:
            event: Domain event to dispatch
            
        Returns:
            DispatchEventResult with dispatch information
            
        Raises:
            EventDispatchFailed: If event dispatching fails
        """
        data = DispatchEventData(event_id=event.id)
        return await self.execute(data)
    
    async def execute_batch(self, event_ids: List[EventId]) -> List[DispatchEventResult]:
        """Execute batch event dispatching for multiple events.
        
        Dispatches multiple events efficiently while maintaining individual
        result tracking. Uses parallel processing for performance.
        
        Args:
            event_ids: List of event IDs to dispatch
            
        Returns:
            List of dispatch results for each event
            
        Raises:
            EventDispatchFailed: If batch dispatching fails
        """
        import asyncio
        
        # Create dispatch tasks for parallel execution
        dispatch_tasks = [
            self.execute(DispatchEventData(event_id=event_id))
            for event_id in event_ids
        ]
        
        # Execute all dispatches in parallel
        results = await asyncio.gather(*dispatch_tasks, return_exceptions=True)
        
        # Convert exceptions to failed results
        dispatch_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                dispatch_results.append(
                    DispatchEventResult(
                        event_id=event_ids[i],
                        dispatched_successfully=False,
                        webhook_deliveries_created=[],
                        total_deliveries=0,
                        successful_deliveries=0,
                        failed_deliveries=0,
                        processing_time_ms=0,
                        error_message=str(result)
                    )
                )
            else:
                dispatch_results.append(result)
        
        return dispatch_results
    
    async def _validate_event_for_dispatch(self, event: DomainEvent) -> None:
        """Validate that event is eligible for dispatching.
        
        Checks event state and requirements to ensure it can be dispatched.
        Prevents double dispatching and validates event integrity.
        
        Args:
            event: Domain event to validate
            
        Raises:
            EventDispatchFailed: If event is not eligible for dispatch
        """
        # Check if event has already been successfully dispatched
        if hasattr(event, 'dispatched_at') and event.dispatched_at:
            raise EventDispatchFailed(
                f"Event {event.id.value} has already been dispatched at {event.dispatched_at}",
                event_id=event.id
            )
        
        # Validate required event data
        if not event.event_type or not event.event_type.value:
            raise EventDispatchFailed(
                f"Event {event.id.value} has invalid event_type",
                event_id=event.id
            )
        
        if not event.aggregate_id:
            raise EventDispatchFailed(
                f"Event {event.id.value} has invalid aggregate_id",
                event_id=event.id
            )
    
    async def _update_event_dispatch_status(
        self,
        event_id: EventId,
        dispatched_successfully: bool,
        total_deliveries: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Update event with dispatch status information.
        
        Updates the event record with dispatch results for tracking and audit purposes.
        
        Args:
            event_id: ID of the event to update
            dispatched_successfully: Whether dispatch was successful
            total_deliveries: Total number of deliveries created
            error_message: Error message if dispatch failed
        """
        try:
            update_data = {
                'dispatched_at': utc_now() if dispatched_successfully else None,
                'dispatch_error': error_message,
                'total_webhook_deliveries': total_deliveries
            }
            
            await self._event_repository.update_processing_status(event_id, update_data)
        except Exception:
            # Don't fail the entire dispatch if status update fails
            # This is tracked separately for monitoring
            pass
    
    async def _retry_failed_deliveries(self, webhook_deliveries: List[WebhookDelivery]) -> None:
        """Retry failed webhook deliveries.
        
        Attempts to retry deliveries that failed during the initial dispatch.
        Uses exponential backoff and retry limits.
        
        Args:
            webhook_deliveries: List of webhook deliveries to check for failures
        """
        failed_deliveries = [d for d in webhook_deliveries if not d.is_successful()]
        
        if failed_deliveries:
            try:
                # Retry failed deliveries using the dispatcher's retry mechanism
                await self._event_dispatcher.retry_failed_deliveries(len(failed_deliveries))
            except Exception:
                # Don't fail the entire dispatch if retry fails
                # This will be handled by background retry processes
                pass