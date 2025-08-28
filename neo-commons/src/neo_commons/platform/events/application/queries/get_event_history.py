"""Get event history query for platform events infrastructure.

This module handles ONLY event history retrieval operations following maximum separation architecture.
Single responsibility: Retrieve chronological sequences of domain events with filtering and pagination.

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
class GetEventHistoryData:
    """Data required to retrieve event history.
    
    Contains all the parameters needed for event history retrieval operations.
    Separates data from business logic following CQRS patterns.
    """
    # Filtering options
    aggregate_id: Optional[str] = None
    aggregate_type: Optional[str] = None
    event_types: Optional[List[str]] = None
    correlation_id: Optional[str] = None
    user_id: Optional[UserId] = None
    
    # Time range filtering
    from_time: Optional[datetime] = None
    to_time: Optional[datetime] = None
    
    # Pagination and ordering
    limit: int = 100
    offset: int = 0
    sort_order: str = "desc"  # desc (newest first) or asc (oldest first)
    
    # Additional options
    include_metadata: bool = True
    include_processing_status: bool = False
    include_causation_chain: bool = False


@dataclass
class GetEventHistoryResult:
    """Result of event history retrieval operation.
    
    Contains comprehensive event history data for monitoring and analysis.
    Provides structured feedback about the retrieved event sequence.
    """
    events: List[DomainEvent]
    total_count: int
    returned_count: int
    has_more: bool
    next_offset: Optional[int] = None
    
    # Time range information
    earliest_event_time: Optional[datetime] = None
    latest_event_time: Optional[datetime] = None
    
    # Performance metrics
    retrieval_time_ms: Optional[int] = None
    
    # Filter summary
    filters_applied: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class GetEventHistoryQuery:
    """Query to retrieve chronological sequences of domain events with comprehensive filtering.
    
    Single responsibility: Orchestrate the retrieval of domain event history including
    time-based filtering, aggregate filtering, event type filtering, pagination,
    and performance-optimized sequential access patterns.
    
    Following enterprise query pattern with protocol-based dependencies.
    Pure application logic - delegates infrastructure concerns to protocols.
    """
    
    def __init__(
        self,
        event_repository: EventRepository
    ):
        """Initialize get event history query with required dependencies.
        
        Args:
            event_repository: Protocol for event data access operations
        """
        self._event_repository = event_repository
    
    async def execute(self, data: GetEventHistoryData) -> GetEventHistoryResult:
        """Execute event history retrieval query.
        
        Orchestrates the complete event history retrieval process:
        1. Validate and prepare search filters
        2. Determine optimal retrieval strategy based on filters
        3. Retrieve events from repository using appropriate method
        4. Calculate pagination and metadata information
        5. Gather performance metrics
        6. Return comprehensive history data
        
        Args:
            data: Event history retrieval configuration data
            
        Returns:
            GetEventHistoryResult with comprehensive event history information
        """
        start_time = utc_now()
        
        try:
            # 1. Validate and prepare search filters
            filters = await self._prepare_search_filters(data)
            
            # 2. Choose optimal retrieval strategy
            events = await self._retrieve_events_by_strategy(data, filters)
            
            # 3. Calculate pagination information
            total_count = len(events)  # In real implementation, this would be a separate count query
            returned_count = len(events)
            has_more = returned_count == data.limit
            next_offset = data.offset + returned_count if has_more else None
            
            # 4. Calculate time range information
            earliest_event_time = None
            latest_event_time = None
            if events:
                event_times = [event.occurred_at for event in events]
                earliest_event_time = min(event_times)
                latest_event_time = max(event_times)
            
            # 5. Calculate retrieval metrics
            end_time = utc_now()
            retrieval_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return GetEventHistoryResult(
                events=events,
                total_count=total_count,
                returned_count=returned_count,
                has_more=has_more,
                next_offset=next_offset,
                earliest_event_time=earliest_event_time,
                latest_event_time=latest_event_time,
                retrieval_time_ms=retrieval_time_ms,
                filters_applied=filters
            )
            
        except Exception as e:
            # Calculate retrieval time for failed operations
            end_time = utc_now()
            retrieval_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return GetEventHistoryResult(
                events=[],
                total_count=0,
                returned_count=0,
                has_more=False,
                retrieval_time_ms=retrieval_time_ms,
                filters_applied=await self._prepare_search_filters(data) if data else {},
                error_message=f"Failed to retrieve event history: {str(e)}"
            )
    
    async def execute_for_aggregate(
        self,
        aggregate_id: str,
        aggregate_type: str,
        limit: int = 100,
        from_version: Optional[int] = None,
        to_version: Optional[int] = None
    ) -> GetEventHistoryResult:
        """Execute event history retrieval for a specific aggregate.
        
        Convenience method for aggregate-specific event history retrieval.
        Optimized for event sourcing patterns and aggregate reconstruction.
        
        Args:
            aggregate_id: ID of the aggregate entity
            aggregate_type: Type of the aggregate entity
            limit: Maximum number of events to return
            from_version: Minimum aggregate version (inclusive)
            to_version: Maximum aggregate version (inclusive)
            
        Returns:
            GetEventHistoryResult with aggregate event history
        """
        start_time = utc_now()
        
        try:
            events = await self._event_repository.get_events_by_aggregate(
                aggregate_id=aggregate_id,
                aggregate_type=aggregate_type,
                from_version=from_version,
                to_version=to_version,
                limit=limit
            )
            
            # Calculate metrics
            end_time = utc_now()
            retrieval_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Calculate time range
            earliest_event_time = None
            latest_event_time = None
            if events:
                event_times = [event.occurred_at for event in events]
                earliest_event_time = min(event_times)
                latest_event_time = max(event_times)
            
            return GetEventHistoryResult(
                events=events,
                total_count=len(events),
                returned_count=len(events),
                has_more=len(events) == limit,
                earliest_event_time=earliest_event_time,
                latest_event_time=latest_event_time,
                retrieval_time_ms=retrieval_time_ms,
                filters_applied={
                    "aggregate_id": aggregate_id,
                    "aggregate_type": aggregate_type,
                    "from_version": from_version,
                    "to_version": to_version
                }
            )
            
        except Exception as e:
            end_time = utc_now()
            retrieval_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return GetEventHistoryResult(
                events=[],
                total_count=0,
                returned_count=0,
                has_more=False,
                retrieval_time_ms=retrieval_time_ms,
                error_message=f"Failed to retrieve aggregate history: {str(e)}"
            )
    
    async def execute_by_event_type(
        self,
        event_type: str,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> GetEventHistoryResult:
        """Execute event history retrieval filtered by event type.
        
        Convenience method for event type specific history retrieval.
        Useful for analyzing patterns in specific event types.
        
        Args:
            event_type: Type of events to retrieve
            from_time: Earliest event time (inclusive)
            to_time: Latest event time (inclusive)
            limit: Maximum number of events to return
            offset: Number of events to skip for pagination
            
        Returns:
            GetEventHistoryResult with event type history
        """
        start_time = utc_now()
        
        try:
            events = await self._event_repository.get_events_by_type(
                event_type=event_type,
                from_time=from_time,
                to_time=to_time,
                limit=limit,
                offset=offset
            )
            
            # Calculate metrics
            end_time = utc_now()
            retrieval_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Calculate time range
            earliest_event_time = None
            latest_event_time = None
            if events:
                event_times = [event.occurred_at for event in events]
                earliest_event_time = min(event_times)
                latest_event_time = max(event_times)
            
            return GetEventHistoryResult(
                events=events,
                total_count=len(events),  # In real implementation, would need separate count query
                returned_count=len(events),
                has_more=len(events) == limit,
                next_offset=offset + len(events) if len(events) == limit else None,
                earliest_event_time=earliest_event_time,
                latest_event_time=latest_event_time,
                retrieval_time_ms=retrieval_time_ms,
                filters_applied={
                    "event_type": event_type,
                    "from_time": from_time.isoformat() if from_time else None,
                    "to_time": to_time.isoformat() if to_time else None
                }
            )
            
        except Exception as e:
            end_time = utc_now()
            retrieval_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return GetEventHistoryResult(
                events=[],
                total_count=0,
                returned_count=0,
                has_more=False,
                retrieval_time_ms=retrieval_time_ms,
                error_message=f"Failed to retrieve event type history: {str(e)}"
            )
    
    async def execute_by_correlation(
        self,
        correlation_id: str,
        include_causation_chain: bool = False,
        limit: int = 100
    ) -> GetEventHistoryResult:
        """Execute event history retrieval for correlated events.
        
        Convenience method for correlation-based event history retrieval.
        Supports distributed system event correlation and causation tracking.
        
        Args:
            correlation_id: Correlation ID linking related events
            include_causation_chain: Whether to include full causation chain
            limit: Maximum number of events to return
            
        Returns:
            GetEventHistoryResult with correlated event history
        """
        start_time = utc_now()
        
        try:
            events = await self._event_repository.get_events_by_correlation_id(
                correlation_id=correlation_id,
                include_causation_chain=include_causation_chain,
                limit=limit
            )
            
            # Calculate metrics
            end_time = utc_now()
            retrieval_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Calculate time range
            earliest_event_time = None
            latest_event_time = None
            if events:
                event_times = [event.occurred_at for event in events]
                earliest_event_time = min(event_times)
                latest_event_time = max(event_times)
            
            return GetEventHistoryResult(
                events=events,
                total_count=len(events),
                returned_count=len(events),
                has_more=len(events) == limit,
                earliest_event_time=earliest_event_time,
                latest_event_time=latest_event_time,
                retrieval_time_ms=retrieval_time_ms,
                filters_applied={
                    "correlation_id": correlation_id,
                    "include_causation_chain": include_causation_chain
                }
            )
            
        except Exception as e:
            end_time = utc_now()
            retrieval_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return GetEventHistoryResult(
                events=[],
                total_count=0,
                returned_count=0,
                has_more=False,
                retrieval_time_ms=retrieval_time_ms,
                error_message=f"Failed to retrieve correlated history: {str(e)}"
            )
    
    async def _prepare_search_filters(self, data: GetEventHistoryData) -> Dict[str, Any]:
        """Prepare search filters from query data.
        
        Converts query data into search filters compatible with the
        repository search interface.
        
        Args:
            data: Event history query data
            
        Returns:
            Dictionary with search filters
        """
        filters = {}
        
        if data.aggregate_id:
            filters["aggregate_id"] = data.aggregate_id
        
        if data.aggregate_type:
            filters["aggregate_type"] = data.aggregate_type
        
        if data.event_types:
            filters["event_types"] = data.event_types
        
        if data.correlation_id:
            filters["correlation_id"] = data.correlation_id
        
        if data.user_id:
            filters["user_id"] = str(data.user_id.value) if hasattr(data.user_id, 'value') else str(data.user_id)
        
        if data.from_time:
            filters["from_time"] = data.from_time
        
        if data.to_time:
            filters["to_time"] = data.to_time
        
        return filters
    
    async def _retrieve_events_by_strategy(
        self,
        data: GetEventHistoryData,
        filters: Dict[str, Any]
    ) -> List[DomainEvent]:
        """Retrieve events using optimal strategy based on filters.
        
        Chooses the most efficient retrieval method based on the
        provided filters and query parameters.
        
        Args:
            data: Event history query data
            filters: Prepared search filters
            
        Returns:
            List of domain events
        """
        # Strategy 1: Aggregate-specific retrieval (most efficient)
        if data.aggregate_id and data.aggregate_type:
            return await self._event_repository.get_events_by_aggregate(
                aggregate_id=data.aggregate_id,
                aggregate_type=data.aggregate_type,
                limit=data.limit
            )
        
        # Strategy 2: Event type retrieval with time filtering
        if data.event_types and len(data.event_types) == 1:
            return await self._event_repository.get_events_by_type(
                event_type=data.event_types[0],
                from_time=data.from_time,
                to_time=data.to_time,
                limit=data.limit,
                offset=data.offset
            )
        
        # Strategy 3: Correlation-based retrieval
        if data.correlation_id:
            return await self._event_repository.get_events_by_correlation_id(
                correlation_id=data.correlation_id,
                include_causation_chain=data.include_causation_chain,
                limit=data.limit
            )
        
        # Strategy 4: General search (fallback)
        search_result = await self._event_repository.search_events(
            filters=filters,
            sort_by="occurred_at",
            sort_order=data.sort_order,
            limit=data.limit,
            offset=data.offset
        )
        
        return search_result.get("events", [])