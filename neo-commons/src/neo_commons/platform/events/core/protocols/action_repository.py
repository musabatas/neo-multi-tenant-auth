"""Action repository protocol for platform events infrastructure.

This module defines the ActionRepository protocol contract following maximum separation architecture.
Single responsibility: Action configuration storage, execution tracking, and management coordination.

Extracted to platform/events following enterprise clean architecture patterns.
Pure platform infrastructure protocol - used by all business features.
"""

from abc import abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from .....core.value_objects import UserId
from ..value_objects import ActionId, EventId
from ..entities.event_action import EventAction
from ..entities.action_execution import ActionExecution


@runtime_checkable
class ActionRepository(Protocol):
    """Action repository protocol for event action persistence and execution tracking.
    
    This protocol defines the contract for action storage operations following
    maximum separation architecture. Single responsibility: coordinate action
    persistence lifecycle, execution tracking, and configuration management.
    
    Pure platform infrastructure protocol - implementations handle:
    - Action configuration persistence and retrieval
    - Action execution tracking and logging
    - Action performance monitoring and analytics
    - Action lifecycle management and archiving
    - Action security and access control
    - Performance optimization for high-volume action execution
    """

    # ===========================================
    # Action Configuration Operations
    # ===========================================
    
    @abstractmethod
    async def save_action(
        self,
        action: EventAction,
        transaction_context: Optional[Dict[str, Any]] = None
    ) -> EventAction:
        """Persist an event action configuration to the repository.
        
        Handles atomic action persistence with proper configuration validation
        and metadata management. Ensures action immutability after persistence.
        
        Args:
            action: Event action configuration to persist
            transaction_context: Optional transaction context for atomic operations
            
        Returns:
            Persisted event action with updated persistence metadata
            
        Raises:
            ActionPersistenceError: If action cannot be persisted
            DuplicateActionError: If action with same ID already exists
            InvalidActionError: If action configuration is invalid or incomplete
        """
        ...
    
    @abstractmethod
    async def get_action_by_id(
        self,
        action_id: ActionId,
        include_metadata: bool = True
    ) -> Optional[EventAction]:
        """Retrieve a specific action by its unique identifier.
        
        Efficient single action retrieval with optional metadata inclusion
        for performance optimization when metadata is not needed.
        
        Args:
            action_id: Unique identifier of the action to retrieve
            include_metadata: Whether to include action metadata in response
            
        Returns:
            Event action if found, None otherwise
            
        Raises:
            ActionRetrievalError: If retrieval operation fails
            InvalidActionIdError: If action ID format is invalid
        """
        ...
    
    @abstractmethod
    async def update_action(
        self,
        action_id: ActionId,
        updates: Dict[str, Any],
        transaction_context: Optional[Dict[str, Any]] = None
    ) -> EventAction:
        """Update an existing action configuration.
        
        Handles atomic action updates with proper validation
        and version management for configuration changes.
        
        Args:
            action_id: Unique identifier of the action to update
            updates: Dictionary of field updates to apply
            transaction_context: Optional transaction context for atomic operations
            
        Returns:
            Updated event action with new configuration
            
        Raises:
            ActionNotFoundError: If action doesn't exist
            InvalidActionUpdateError: If updates are invalid
            ActionUpdateError: If update operation fails
        """
        ...
    
    @abstractmethod
    async def delete_action(
        self,
        action_id: ActionId,
        soft_delete: bool = True,
        transaction_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Delete an action configuration from the repository.
        
        Handles action deletion with soft delete support and
        related execution cleanup considerations.
        
        Args:
            action_id: Unique identifier of the action to delete
            soft_delete: Whether to soft delete (mark inactive) or hard delete
            transaction_context: Optional transaction context for atomic operations
            
        Returns:
            True if deletion was successful, False if action wasn't found
            
        Raises:
            ActionDeletionError: If deletion operation fails
            ActionInUseError: If action has active executions (hard delete only)
        """
        ...

    # ===========================================
    # Action Query Operations
    # ===========================================
    
    @abstractmethod
    async def get_actions_by_event_type(
        self,
        event_type: str,
        active_only: bool = True,
        include_conditions: bool = True
    ) -> List[EventAction]:
        """Retrieve actions that should execute for a specific event type.
        
        Efficient event-triggered action lookup with condition evaluation
        support for dynamic action selection.
        
        Args:
            event_type: Event type to find matching actions for
            active_only: Whether to include only active actions
            include_conditions: Whether to evaluate action conditions
            
        Returns:
            List of event actions that match the event type
            
        Raises:
            ActionRetrievalError: If retrieval operation fails
            InvalidEventTypeError: If event type format is invalid
        """
        ...
    
    @abstractmethod
    async def search_actions(
        self,
        filters: Dict[str, Any],
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Advanced action search with flexible filtering and pagination.
        
        Comprehensive search capabilities with multiple filter types,
        custom sorting, and performance-optimized pagination.
        
        Args:
            filters: Search filters (name, handler_type, status, tags, etc.)
            sort_by: Field to sort by (created_at, name, priority, etc.)
            sort_order: Sort direction (asc, desc)
            limit: Maximum number of actions to return
            offset: Number of actions to skip for pagination
            
        Returns:
            Dict with search results:
            - actions: List of matching event actions
            - total_count: Total number of matching actions
            - has_more: Whether more results are available
            - next_offset: Offset for next page
            
        Raises:
            ActionSearchError: If search operation fails
            InvalidFilterError: If search filters are invalid
            InvalidSortError: If sort parameters are invalid
        """
        ...
    
    @abstractmethod
    async def get_actions_by_user(
        self,
        user_id: UserId,
        include_inactive: bool = False,
        limit: Optional[int] = None
    ) -> List[EventAction]:
        """Retrieve actions created by a specific user.
        
        User-specific action lookup for management interfaces
        and user permission validation.
        
        Args:
            user_id: ID of the user who created the actions
            include_inactive: Whether to include inactive actions
            limit: Maximum number of actions to return
            
        Returns:
            List of event actions created by the user
            
        Raises:
            ActionRetrievalError: If retrieval operation fails
            InvalidUserIdError: If user ID format is invalid
        """
        ...

    # ===========================================
    # Action Execution Tracking Operations
    # ===========================================
    
    @abstractmethod
    async def save_execution(
        self,
        execution: ActionExecution,
        transaction_context: Optional[Dict[str, Any]] = None
    ) -> ActionExecution:
        """Persist an action execution record to the repository.
        
        Handles atomic execution tracking with proper performance
        metrics and error handling for monitoring and debugging.
        
        Args:
            execution: Action execution record to persist
            transaction_context: Optional transaction context for atomic operations
            
        Returns:
            Persisted action execution with updated tracking metadata
            
        Raises:
            ExecutionPersistenceError: If execution record cannot be persisted
            InvalidExecutionError: If execution data is invalid or incomplete
        """
        ...
    
    @abstractmethod
    async def get_execution_by_id(
        self,
        execution_id: ActionId,
        include_result_data: bool = False
    ) -> Optional[ActionExecution]:
        """Retrieve a specific execution by its unique identifier.
        
        Efficient single execution retrieval with optional result data
        inclusion for performance optimization in monitoring systems.
        
        Args:
            execution_id: Unique identifier of the execution to retrieve
            include_result_data: Whether to include execution result data
            
        Returns:
            Action execution if found, None otherwise
            
        Raises:
            ExecutionRetrievalError: If retrieval operation fails
            InvalidExecutionIdError: If execution ID format is invalid
        """
        ...
    
    @abstractmethod
    async def get_executions_by_action(
        self,
        action_id: ActionId,
        status_filter: Optional[str] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Retrieve executions for a specific action with filtering.
        
        Comprehensive execution history retrieval with status and
        time-based filtering for monitoring and debugging.
        
        Args:
            action_id: ID of the action to get executions for
            status_filter: Optional filter by execution status
            from_time: Earliest execution time (inclusive)
            to_time: Latest execution time (inclusive)
            limit: Maximum number of executions to return
            offset: Number of executions to skip for pagination
            
        Returns:
            Dict with execution results:
            - executions: List of action executions
            - total_count: Total number of matching executions
            - has_more: Whether more results are available
            - next_offset: Offset for next page
            
        Raises:
            ExecutionRetrievalError: If retrieval operation fails
            InvalidActionIdError: If action ID format is invalid
        """
        ...
    
    @abstractmethod
    async def get_failed_executions(
        self,
        limit: int = 100,
        action_ids: Optional[List[ActionId]] = None,
        max_age_hours: Optional[int] = None,
        retry_eligible_only: bool = False
    ) -> List[ActionExecution]:
        """Retrieve failed executions for retry processing.
        
        Efficient failed execution lookup with retry eligibility
        filtering for automated retry systems.
        
        Args:
            limit: Maximum number of executions to return
            action_ids: Optional filter by specific action IDs
            max_age_hours: Maximum age of failures to consider (hours)
            retry_eligible_only: Whether to include only retry-eligible executions
            
        Returns:
            List of failed action executions ordered by failure time
            
        Raises:
            ExecutionRetrievalError: If retrieval operation fails
        """
        ...
    
    @abstractmethod
    async def update_execution_status(
        self,
        execution_id: ActionId,
        status: str,
        result_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        completed_at: Optional[datetime] = None
    ) -> ActionExecution:
        """Update the status and result of an action execution.
        
        Handles atomic execution status updates with proper
        completion tracking and error handling.
        
        Args:
            execution_id: Unique identifier of the execution to update
            status: New execution status
            result_data: Optional execution result data
            error_message: Optional error message if execution failed
            completed_at: Optional completion timestamp
            
        Returns:
            Updated action execution with new status
            
        Raises:
            ExecutionNotFoundError: If execution doesn't exist
            InvalidExecutionStatusError: If status transition is invalid
            ExecutionUpdateError: If update operation fails
        """
        ...

    # ===========================================
    # Action Statistics Operations
    # ===========================================
    
    @abstractmethod
    async def get_action_statistics(
        self,
        action_id: Optional[ActionId] = None,
        handler_type: Optional[str] = None,
        time_range_hours: int = 24,
        include_performance_metrics: bool = True
    ) -> Dict[str, Any]:
        """Get comprehensive action statistics for monitoring and analysis.
        
        Provides detailed statistics for system monitoring, performance
        analysis, and operational decision making.
        
        Args:
            action_id: Optional filter by specific action ID
            handler_type: Optional filter by handler type
            time_range_hours: Time range for statistics calculation
            include_performance_metrics: Whether to include detailed performance data
            
        Returns:
            Dict with comprehensive action statistics:
            - total_actions: Total number of configured actions
            - active_actions: Number of active actions
            - total_executions: Total execution attempts
            - successful_executions: Successful execution count
            - failed_executions: Failed execution count
            - success_rate: Overall success percentage
            - average_execution_time_ms: Average execution duration
            - p95_execution_time_ms: 95th percentile execution time
            - retry_rate: Percentage of executions that required retry
            - error_distribution: Error types and frequencies
            - handler_performance: Per-handler performance metrics
            
        Raises:
            ActionStatisticsError: If statistics calculation fails
        """
        ...
    
    @abstractmethod
    async def get_execution_analytics(
        self,
        action_id: Optional[ActionId] = None,
        event_type: Optional[str] = None,
        time_range_hours: int = 24,
        group_by: str = "hour"
    ) -> Dict[str, Any]:
        """Get detailed execution analytics for performance monitoring.
        
        Advanced analytics for capacity planning, performance optimization,
        and trend analysis with flexible time-based grouping.
        
        Args:
            action_id: Optional filter by specific action ID
            event_type: Optional filter by event type
            time_range_hours: Time range for analytics calculation
            group_by: Time grouping (hour, day, week)
            
        Returns:
            Dict with detailed execution analytics:
            - execution_trends: Time-series execution data
            - performance_trends: Performance metrics over time
            - error_trends: Error rate trends
            - capacity_utilization: Resource usage patterns
            - peak_execution_times: High-volume periods
            - bottleneck_analysis: Performance bottleneck identification
            
        Raises:
            AnalyticsError: If analytics calculation fails
        """
        ...

    # ===========================================
    # Action Maintenance Operations
    # ===========================================
    
    @abstractmethod
    async def cleanup_old_executions(
        self,
        retention_days: int = 90,
        keep_failed_days: int = 180,
        batch_size: int = 1000,
        preserve_analytics: bool = True
    ) -> int:
        """Clean up old execution records for database performance maintenance.
        
        Removes old execution records while preserving important failure
        information and aggregate analytics for analysis.
        
        Args:
            retention_days: Days to retain successful execution records
            keep_failed_days: Days to retain failed execution records
            batch_size: Number of records to delete per batch
            preserve_analytics: Whether to preserve aggregate analytics
            
        Returns:
            Number of execution records cleaned up
            
        Raises:
            ExecutionCleanupError: If cleanup operation fails
        """
        ...
    
    @abstractmethod
    async def archive_inactive_actions(
        self,
        inactive_days: int = 365,
        batch_size: int = 100,
        preserve_executions: bool = True,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Archive actions that haven't been used for extended periods.
        
        Intelligent archival with execution history preservation
        and batch processing for minimal performance impact.
        
        Args:
            inactive_days: Archive actions unused for this many days
            batch_size: Number of actions to archive per batch
            preserve_executions: Whether to keep execution history
            dry_run: Whether to simulate archival without actual changes
            
        Returns:
            Dict with archival results:
            - actions_archived: Number of actions archived
            - executions_preserved: Number of execution records preserved
            - processing_time_ms: Total processing time
            - storage_freed_mb: Estimated storage space freed
            
        Raises:
            ActionArchivalError: If archival operation fails
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