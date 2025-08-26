"""Event repository protocol for platform events infrastructure.

This module defines the EventRepository protocol contract following maximum separation architecture.
Single responsibility: Event storage, retrieval, and persistence coordination.

Extracted to platform/events following enterprise clean architecture patterns.
Pure platform infrastructure protocol - used by all business features.
"""

from abc import abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from .....core.value_objects import UserId
from ..value_objects import EventId
from ..entities.domain_event import DomainEvent


@runtime_checkable
class EventRepository(Protocol):
    """Event repository protocol for domain event persistence and retrieval operations.
    
    This protocol defines the contract for event storage operations following
    maximum separation architecture. Single responsibility: coordinate event
    persistence lifecycle, retrieval patterns, and storage optimization.
    
    Pure platform infrastructure protocol - implementations handle:
    - Event persistence and retrieval
    - Event stream management and ordering
    - Query optimization and indexing
    - Event filtering and search capabilities
    - Archive and retention management
    - Performance optimization for high-volume event streams
    """

    # ===========================================
    # Core Persistence Operations
    # ===========================================
    
    @abstractmethod
    async def save_event(
        self,
        event: DomainEvent,
        transaction_context: Optional[Dict[str, Any]] = None
    ) -> DomainEvent:
        """Persist a domain event to the event store.
        
        Handles atomic event persistence with proper event ordering
        and metadata management. Ensures event immutability after persistence.
        
        Args:
            event: Domain event to persist
            transaction_context: Optional transaction context for atomic operations
            
        Returns:
            Persisted domain event with updated persistence metadata
            
        Raises:
            EventPersistenceError: If event cannot be persisted
            DuplicateEventError: If event with same ID already exists
            InvalidEventError: If event data is invalid or incomplete
        """
        ...
    
    @abstractmethod
    async def save_events_batch(
        self,
        events: List[DomainEvent],
        preserve_order: bool = True,
        transaction_context: Optional[Dict[str, Any]] = None
    ) -> List[DomainEvent]:
        """Persist multiple domain events atomically.
        
        Batch persistence for high-performance event streaming with
        guaranteed ordering and atomic transaction support.
        
        Args:
            events: List of domain events to persist
            preserve_order: Whether to maintain event ordering
            transaction_context: Optional transaction context for atomic operations
            
        Returns:
            List of persisted domain events with updated metadata
            
        Raises:
            EventBatchPersistenceError: If batch operation fails
            InvalidEventBatchError: If any event in batch is invalid
            TransactionError: If transaction fails during batch operation
        """
        ...
    
    @abstractmethod
    async def get_event_by_id(
        self,
        event_id: EventId,
        include_metadata: bool = True
    ) -> Optional[DomainEvent]:
        """Retrieve a specific event by its unique identifier.
        
        Efficient single event retrieval with optional metadata inclusion
        for performance optimization when metadata is not needed.
        
        Args:
            event_id: Unique identifier of the event to retrieve
            include_metadata: Whether to include event metadata in response
            
        Returns:
            Domain event if found, None otherwise
            
        Raises:
            EventRetrievalError: If retrieval operation fails
            InvalidEventIdError: If event ID format is invalid
        """
        ...

    # ===========================================
    # Event Stream Operations
    # ===========================================
    
    @abstractmethod
    async def get_events_by_aggregate(
        self,
        aggregate_id: str,
        aggregate_type: str,
        from_version: Optional[int] = None,
        to_version: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[DomainEvent]:
        """Retrieve events for a specific aggregate with version filtering.
        
        Optimized for event sourcing patterns with efficient aggregate
        reconstruction and version-based filtering capabilities.
        
        Args:
            aggregate_id: ID of the aggregate entity
            aggregate_type: Type of the aggregate entity
            from_version: Minimum aggregate version (inclusive)
            to_version: Maximum aggregate version (inclusive)
            limit: Maximum number of events to return
            
        Returns:
            List of domain events ordered by aggregate version
            
        Raises:
            EventRetrievalError: If retrieval operation fails
            InvalidAggregateError: If aggregate information is invalid
        """
        ...
    
    @abstractmethod
    async def get_events_by_type(
        self,
        event_type: str,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[DomainEvent]:
        """Retrieve events filtered by type and time range.
        
        Efficient event type querying with time-based filtering
        and pagination support for large result sets.
        
        Args:
            event_type: Type of events to retrieve
            from_time: Earliest event time (inclusive)
            to_time: Latest event time (inclusive)
            limit: Maximum number of events to return
            offset: Number of events to skip for pagination
            
        Returns:
            List of domain events ordered by occurrence time
            
        Raises:
            EventRetrievalError: If retrieval operation fails
            InvalidEventTypeError: If event type is invalid
            InvalidTimeRangeError: If time range is invalid
        """
        ...
    
    @abstractmethod
    async def get_events_by_correlation_id(
        self,
        correlation_id: str,
        include_causation_chain: bool = False,
        limit: Optional[int] = None
    ) -> List[DomainEvent]:
        """Retrieve events linked by correlation ID for distributed tracing.
        
        Supports distributed system event correlation with optional
        causation chain reconstruction for complex event flows.
        
        Args:
            correlation_id: Correlation ID linking related events
            include_causation_chain: Whether to include full causation chain
            limit: Maximum number of events to return
            
        Returns:
            List of correlated domain events ordered by occurrence time
            
        Raises:
            EventRetrievalError: If retrieval operation fails
            InvalidCorrelationIdError: If correlation ID format is invalid
        """
        ...

    # ===========================================
    # Event Query Operations
    # ===========================================
    
    @abstractmethod
    async def get_unprocessed_events(
        self,
        limit: Optional[int] = None,
        event_types: Optional[List[str]] = None,
        max_age_hours: Optional[int] = None
    ) -> List[DomainEvent]:
        """Retrieve events that haven't been processed by handlers.
        
        Efficient retrieval of pending events for processing systems
        with type filtering and age-based filtering capabilities.
        
        Args:
            limit: Maximum number of events to return
            event_types: Optional filter by specific event types
            max_age_hours: Maximum age of events to consider (hours)
            
        Returns:
            List of unprocessed domain events ordered by occurrence time
            
        Raises:
            EventRetrievalError: If retrieval operation fails
        """
        ...
    
    @abstractmethod
    async def search_events(
        self,
        filters: Dict[str, Any],
        sort_by: str = "occurred_at",
        sort_order: str = "desc",
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Advanced event search with flexible filtering and pagination.
        
        Comprehensive search capabilities with multiple filter types,
        custom sorting, and performance-optimized pagination.
        
        Args:
            filters: Search filters (event_type, aggregate_type, user_id, etc.)
            sort_by: Field to sort by (occurred_at, aggregate_version, etc.)
            sort_order: Sort direction (asc, desc)
            limit: Maximum number of events to return
            offset: Number of events to skip for pagination
            
        Returns:
            Dict with search results:
            - events: List of matching domain events
            - total_count: Total number of matching events
            - has_more: Whether more results are available
            - next_offset: Offset for next page
            
        Raises:
            EventSearchError: If search operation fails
            InvalidFilterError: If search filters are invalid
            InvalidSortError: If sort parameters are invalid
        """
        ...

    # ===========================================
    # Event Statistics Operations
    # ===========================================
    
    @abstractmethod
    async def get_event_statistics(
        self,
        aggregate_type: Optional[str] = None,
        event_type: Optional[str] = None,
        time_range_hours: int = 24,
        include_processing_stats: bool = True
    ) -> Dict[str, Any]:
        """Get comprehensive event statistics for monitoring and analysis.
        
        Provides detailed statistics for system monitoring, performance
        analysis, and operational decision making.
        
        Args:
            aggregate_type: Optional filter by aggregate type
            event_type: Optional filter by event type
            time_range_hours: Time range for statistics calculation
            include_processing_stats: Whether to include processing metrics
            
        Returns:
            Dict with comprehensive event statistics:
            - total_events: Total event count
            - events_per_hour: Event rate breakdown
            - event_type_distribution: Event types and counts
            - aggregate_type_distribution: Aggregate types and counts
            - processing_lag: Average processing delay
            - unprocessed_count: Events waiting for processing
            - error_rate: Event processing error percentage
            
        Raises:
            EventStatisticsError: If statistics calculation fails
        """
        ...
    
    @abstractmethod
    async def get_aggregate_statistics(
        self,
        aggregate_id: str,
        aggregate_type: str,
        include_version_history: bool = False
    ) -> Dict[str, Any]:
        """Get statistics for a specific aggregate entity.
        
        Detailed aggregate analysis including event counts, version
        information, and optional version history for debugging.
        
        Args:
            aggregate_id: ID of the aggregate entity
            aggregate_type: Type of the aggregate entity
            include_version_history: Whether to include version progression
            
        Returns:
            Dict with aggregate statistics:
            - total_events: Total events for this aggregate
            - current_version: Current aggregate version
            - first_event_at: Timestamp of first event
            - last_event_at: Timestamp of latest event
            - event_type_counts: Event types and their frequencies
            - version_history: Optional version progression details
            
        Raises:
            EventStatisticsError: If statistics calculation fails
            InvalidAggregateError: If aggregate information is invalid
        """
        ...

    # ===========================================
    # Event Maintenance Operations
    # ===========================================
    
    @abstractmethod
    async def mark_events_processed(
        self,
        event_ids: List[EventId],
        processor_name: str,
        processing_metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Mark events as processed by a specific processor.
        
        Tracks event processing completion with processor identification
        and optional metadata for audit and debugging purposes.
        
        Args:
            event_ids: List of event IDs that were processed
            processor_name: Name/identifier of the processing component
            processing_metadata: Optional metadata about processing
            
        Returns:
            Number of events successfully marked as processed
            
        Raises:
            EventProcessingError: If processing update fails
            InvalidEventIdError: If any event ID is invalid
        """
        ...
    
    @abstractmethod
    async def archive_old_events(
        self,
        older_than_days: int = 365,
        batch_size: int = 1000,
        preserve_aggregates: bool = True,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Archive old events for long-term storage and database performance.
        
        Intelligent archival with aggregate preservation options and
        batch processing for minimal performance impact.
        
        Args:
            older_than_days: Archive events older than this many days
            batch_size: Number of events to archive per batch
            preserve_aggregates: Whether to keep complete aggregate event streams
            dry_run: Whether to simulate archival without actual changes
            
        Returns:
            Dict with archival results:
            - events_archived: Number of events archived
            - aggregates_preserved: Number of aggregate streams preserved
            - processing_time_ms: Total processing time
            - storage_freed_mb: Estimated storage space freed
            
        Raises:
            EventArchivalError: If archival operation fails
            InvalidArchivalParametersError: If parameters are invalid
        """
        ...
    
    @abstractmethod
    async def cleanup_processed_events(
        self,
        retention_days: int = 90,
        keep_unprocessed: bool = True,
        batch_size: int = 1000
    ) -> int:
        """Clean up processed events for database maintenance.
        
        Removes old processed events while preserving unprocessed events
        and maintaining system performance during cleanup.
        
        Args:
            retention_days: Days to retain processed events
            keep_unprocessed: Whether to preserve unprocessed events
            batch_size: Number of events to delete per batch
            
        Returns:
            Number of events cleaned up
            
        Raises:
            EventCleanupError: If cleanup operation fails
        """
        ...

    # ===========================================
    # Health and Diagnostics Operations
    # ===========================================
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform repository health check for monitoring systems.
        
        Comprehensive health assessment including connection status,
        performance metrics, and operational indicators.
        
        Returns:
            Dict with health information:
            - is_healthy: Overall health status
            - connection_status: Database connection health
            - recent_operation_success_rate: Success rate for recent operations
            - average_response_time_ms: Average operation response time
            - pending_operations: Number of operations in queue
            - last_successful_operation: Timestamp of last successful operation
            - storage_usage: Current storage utilization metrics
            
        Raises:
            HealthCheckError: If health check cannot be performed
        """
        ...
    
    @abstractmethod
    async def get_repository_metrics(
        self,
        time_range_hours: int = 1,
        include_performance_details: bool = False
    ) -> Dict[str, Any]:
        """Get detailed repository performance metrics.
        
        Performance analysis for optimization and capacity planning
        with optional detailed breakdown for troubleshooting.
        
        Args:
            time_range_hours: Time range for metrics calculation
            include_performance_details: Whether to include detailed metrics
            
        Returns:
            Dict with repository metrics:
            - operations_per_second: Repository operation rate
            - average_query_time_ms: Average query execution time
            - cache_hit_rate: Query cache effectiveness
            - connection_pool_usage: Database connection utilization
            - error_rate: Operation failure percentage
            - storage_growth_rate: Data growth trends
            
        Raises:
            MetricsError: If metrics calculation fails
        """
        ...