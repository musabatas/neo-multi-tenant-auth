"""Get event query for platform events infrastructure.

This module handles ONLY event retrieval operations following maximum separation architecture.
Single responsibility: Retrieve domain events with optional metadata and related data.

Pure application layer - no infrastructure concerns.
Uses protocols for dependency injection and clean architecture compliance.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime
from uuid import UUID

from ...core.protocols import EventRepository
from ...core.entities import DomainEvent
from ...core.value_objects import EventId
from ...core.exceptions import EventDispatchFailed
from neo_commons.core.value_objects import UserId
from neo_commons.utils import utc_now


@dataclass
class GetEventData:
    """Data required to retrieve an event.
    
    Contains all the parameters needed for event retrieval operations.
    Separates data from business logic following CQRS patterns.
    """
    event_id: EventId
    include_metadata: bool = True
    include_actions: bool = False
    include_deliveries: bool = False
    include_processing_status: bool = True
    
    
@dataclass
class GetEventResult:
    """Result of event retrieval operation.
    
    Contains comprehensive event data for monitoring and analysis.
    Provides structured feedback about the retrieved event.
    """
    event_id: EventId
    event_found: bool
    event: Optional[DomainEvent] = None
    processing_status: Optional[Dict[str, Any]] = None
    related_actions: Optional[List[Dict[str, Any]]] = None
    delivery_attempts: Optional[List[Dict[str, Any]]] = None
    retrieval_time_ms: Optional[int] = None
    error_message: Optional[str] = None


class GetEventQuery:
    """Query to retrieve a domain event with optional related data.
    
    Single responsibility: Orchestrate the retrieval of a domain event including
    optional metadata, processing status, related actions, and delivery information.
    Provides comprehensive event information for monitoring and debugging purposes.
    
    Following enterprise query pattern with protocol-based dependencies.
    Pure application logic - delegates infrastructure concerns to protocols.
    """
    
    def __init__(
        self,
        event_repository: EventRepository
    ):
        """Initialize get event query with required dependencies.
        
        Args:
            event_repository: Protocol for event data access operations
        """
        self._event_repository = event_repository
    
    async def execute(self, data: GetEventData) -> GetEventResult:
        """Execute event retrieval query.
        
        Orchestrates the complete event retrieval process:
        1. Retrieve event from repository
        2. Validate event exists
        3. Optionally retrieve related actions
        4. Optionally retrieve delivery attempts
        5. Gather processing status information
        6. Return comprehensive event data
        
        Args:
            data: Event retrieval configuration data
            
        Returns:
            GetEventResult with comprehensive event information
        """
        start_time = utc_now()
        
        try:
            # 1. Retrieve event from repository
            event = await self._event_repository.get_event_by_id(
                event_id=data.event_id,
                include_metadata=data.include_metadata
            )
            
            if not event:
                return GetEventResult(
                    event_id=data.event_id,
                    event_found=False,
                    error_message=f"Event with ID {data.event_id.value} not found"
                )
            
            # 2. Initialize result with basic event data
            result_data = {
                "event_id": data.event_id,
                "event_found": True,
                "event": event
            }
            
            # 3. Optionally retrieve processing status
            if data.include_processing_status:
                processing_status = await self._get_processing_status(event)
                result_data["processing_status"] = processing_status
            
            # 4. Optionally retrieve related actions
            if data.include_actions:
                related_actions = await self._get_related_actions(event)
                result_data["related_actions"] = related_actions
            
            # 5. Optionally retrieve delivery attempts
            if data.include_deliveries:
                delivery_attempts = await self._get_delivery_attempts(event)
                result_data["delivery_attempts"] = delivery_attempts
            
            # 6. Calculate retrieval metrics
            end_time = utc_now()
            retrieval_time_ms = int((end_time - start_time).total_seconds() * 1000)
            result_data["retrieval_time_ms"] = retrieval_time_ms
            
            return GetEventResult(**result_data)
            
        except Exception as e:
            # Calculate retrieval time for failed operations
            end_time = utc_now()
            retrieval_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return GetEventResult(
                event_id=data.event_id,
                event_found=False,
                retrieval_time_ms=retrieval_time_ms,
                error_message=f"Failed to retrieve event {data.event_id.value}: {str(e)}"
            )
    
    async def execute_simple(self, event_id: EventId) -> GetEventResult:
        """Execute simple event retrieval without optional data.
        
        Convenience method for basic event retrieval with minimal data.
        Useful for quick event existence checks and basic event data.
        
        Args:
            event_id: ID of the event to retrieve
            
        Returns:
            GetEventResult with basic event information
        """
        data = GetEventData(
            event_id=event_id,
            include_metadata=True,
            include_actions=False,
            include_deliveries=False,
            include_processing_status=False
        )
        return await self.execute(data)
    
    async def execute_with_status(self, event_id: EventId) -> GetEventResult:
        """Execute event retrieval with processing status information.
        
        Convenience method for retrieving event with processing status.
        Useful for monitoring event processing progress and debugging.
        
        Args:
            event_id: ID of the event to retrieve
            
        Returns:
            GetEventResult with event and processing status
        """
        data = GetEventData(
            event_id=event_id,
            include_metadata=True,
            include_actions=False,
            include_deliveries=False,
            include_processing_status=True
        )
        return await self.execute(data)
    
    async def execute_comprehensive(self, event_id: EventId) -> GetEventResult:
        """Execute comprehensive event retrieval with all optional data.
        
        Convenience method for complete event analysis including all
        related actions, deliveries, and processing status.
        
        Args:
            event_id: ID of the event to retrieve
            
        Returns:
            GetEventResult with complete event information
        """
        data = GetEventData(
            event_id=event_id,
            include_metadata=True,
            include_actions=True,
            include_deliveries=True,
            include_processing_status=True
        )
        return await self.execute(data)
    
    async def execute_batch(
        self,
        event_ids: List[EventId],
        include_metadata: bool = True
    ) -> List[GetEventResult]:
        """Execute batch event retrieval for multiple events.
        
        Retrieves multiple events efficiently while maintaining individual
        result tracking. Uses parallel processing for performance.
        
        Args:
            event_ids: List of event IDs to retrieve
            include_metadata: Whether to include event metadata
            
        Returns:
            List of retrieval results for each event
        """
        import asyncio
        
        # Create retrieval tasks for parallel execution
        retrieval_tasks = [
            self.execute(GetEventData(
                event_id=event_id,
                include_metadata=include_metadata,
                include_actions=False,
                include_deliveries=False,
                include_processing_status=False
            ))
            for event_id in event_ids
        ]
        
        # Execute all retrievals in parallel
        results = await asyncio.gather(*retrieval_tasks, return_exceptions=True)
        
        # Convert exceptions to failed results
        retrieval_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                retrieval_results.append(
                    GetEventResult(
                        event_id=event_ids[i],
                        event_found=False,
                        retrieval_time_ms=0,
                        error_message=str(result)
                    )
                )
            else:
                retrieval_results.append(result)
        
        return retrieval_results
    
    async def _get_processing_status(self, event: DomainEvent) -> Dict[str, Any]:
        """Get processing status information for an event.
        
        Retrieves comprehensive processing status including dispatch status,
        action execution status, and delivery status.
        
        Args:
            event: Domain event to get status for
            
        Returns:
            Dictionary with processing status information
        """
        try:
            # This would be implemented based on the actual repository methods
            # For now, return basic status information
            status = {
                "event_id": str(event.id.value),
                "processing_started_at": event.occurred_at,
                "last_updated_at": utc_now(),
                "dispatch_status": "completed" if hasattr(event, 'dispatched_at') and event.dispatched_at else "pending",
                "actions_triggered": 0,  # Would be calculated from actual data
                "deliveries_attempted": 0,  # Would be calculated from actual data
                "current_status": "processed" if hasattr(event, 'processed_at') and event.processed_at else "processing"
            }
            
            return status
        except Exception:
            # Return minimal status on error
            return {
                "event_id": str(event.id.value),
                "status_error": "Could not retrieve processing status"
            }
    
    async def _get_related_actions(self, event: DomainEvent) -> List[Dict[str, Any]]:
        """Get related actions for an event.
        
        Retrieves all actions that were triggered by this event including
        their configuration and execution status.
        
        Args:
            event: Domain event to get actions for
            
        Returns:
            List of action information dictionaries
        """
        try:
            # This would be implemented based on actual action repository
            # For now, return placeholder structure
            actions = []
            
            # In real implementation, this would query the action repository
            # actions = await self._action_repository.get_actions_by_event_type(event.event_type)
            
            return actions
        except Exception:
            return []
    
    async def _get_delivery_attempts(self, event: DomainEvent) -> List[Dict[str, Any]]:
        """Get delivery attempts for an event.
        
        Retrieves all webhook and notification delivery attempts for this event
        including their status, timing, and error information.
        
        Args:
            event: Domain event to get delivery attempts for
            
        Returns:
            List of delivery attempt information
        """
        try:
            # This would be implemented based on actual delivery repository
            # For now, return placeholder structure
            deliveries = []
            
            # In real implementation, this would query the delivery repository
            # deliveries = await self._delivery_repository.get_deliveries_by_event_id(event.id)
            
            return deliveries
        except Exception:
            return []