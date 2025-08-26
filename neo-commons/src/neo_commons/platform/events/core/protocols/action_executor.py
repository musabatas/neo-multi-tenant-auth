"""Action executor protocol for platform events infrastructure.

This module defines the ActionExecutor protocol contract following maximum separation architecture.
Single responsibility: Action execution coordination and lifecycle management.

Extracted to platform/events following enterprise clean architecture patterns.
Pure platform infrastructure protocol - used by all business features.
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from .....core.value_objects import UserId
from ..value_objects import ActionId, EventId
from ..entities.event_action import EventAction
from ..entities.action_execution import ActionExecution


@runtime_checkable
class ActionExecutor(Protocol):
    """Action executor protocol for coordinating event action execution.
    
    This protocol defines the contract for action execution operations following
    maximum separation architecture. Single responsibility: coordinate action execution
    lifecycle, error handling, retry logic, and performance tracking.
    
    Pure platform infrastructure protocol - implementations handle:
    - Action execution coordination  
    - Lifecycle state management
    - Error handling and recovery
    - Retry logic and backoff strategies
    - Performance metrics and monitoring
    - Concurrency control and throttling
    """

    # ===========================================
    # Core Action Execution Operations
    # ===========================================
    
    @abstractmethod
    async def execute_action(
        self,
        action: EventAction,
        event_data: Dict[str, Any],
        execution_context: Optional[Dict[str, Any]] = None,
        triggered_by_user_id: Optional[UserId] = None,
        correlation_id: Optional[str] = None
    ) -> ActionExecution:
        """Execute a single action with complete lifecycle management.
        
        This is the core execution method that:
        - Creates execution tracking record
        - Coordinates handler execution based on action type
        - Manages execution state transitions
        - Handles errors and timeout scenarios
        - Applies retry logic and backoff strategies
        - Records performance metrics
        
        Args:
            action: Event action to execute
            event_data: Event payload data for action processing
            execution_context: Additional context for execution (tenant_id, etc.)
            triggered_by_user_id: User who triggered the event that caused this action
            correlation_id: For tracking related executions across the system
            
        Returns:
            ActionExecution with complete execution tracking information
            
        Raises:
            ActionExecutionError: If execution setup fails
            ActionTimeoutError: If execution exceeds configured timeout
            ActionHandlerError: If action handler fails
        """
        ...
    
    @abstractmethod
    async def execute_actions_for_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        actions: List[EventAction],
        execution_context: Optional[Dict[str, Any]] = None,
        triggered_by_user_id: Optional[UserId] = None,
        correlation_id: Optional[str] = None
    ) -> List[ActionExecution]:
        """Execute multiple actions for a single event with optimized coordination.
        
        Coordinates execution of multiple actions following their execution modes:
        - Synchronous actions: Execute sequentially by priority
        - Asynchronous actions: Execute concurrently with throttling
        - Queued actions: Schedule for background execution
        
        Args:
            event_type: Type of event that triggered these actions
            event_data: Event payload data
            actions: List of actions to execute (will be sorted by priority)
            execution_context: Additional context for all executions
            triggered_by_user_id: User who triggered the originating event
            correlation_id: For tracking related executions
            
        Returns:
            List of ActionExecution records for all execution attempts
            
        Raises:
            ActionExecutionError: If batch execution coordination fails
        """
        ...
    
    @abstractmethod
    async def execute_actions_parallel(
        self,
        actions: List[EventAction],
        event_data: Dict[str, Any],
        max_concurrent_actions: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """High-performance parallel action execution for real-time scenarios.
        
        Coordinates parallel execution of actions with controlled concurrency
        and comprehensive performance metrics collection.
        
        Args:
            actions: List of actions to execute in parallel
            event_data: Event payload data
            max_concurrent_actions: Maximum concurrent executions (uses config if None)
            timeout_seconds: Timeout for entire parallel operation (uses config if None)
            execution_context: Additional context for executions
            
        Returns:
            Dict with execution results and performance metrics:
            - total_actions: Total actions processed
            - successful_actions: Successfully executed actions
            - failed_actions: Failed action executions
            - executions: List of ActionExecution records
            - total_duration_ms: Total execution time
            - average_duration_ms: Average per-action execution time
            - max_duration_ms: Longest individual execution time
            - actions_per_second: Execution throughput
            
        Raises:
            ActionExecutionError: If parallel execution coordination fails
            ActionTimeoutError: If operation exceeds timeout
        """
        ...

    # ===========================================
    # Execution State Management Operations
    # ===========================================
    
    @abstractmethod
    async def get_execution_status(self, execution_id: ActionId) -> Optional[ActionExecution]:
        """Get current status of an action execution.
        
        Returns current execution state including progress, results, and error information.
        
        Args:
            execution_id: ID of the execution to check
            
        Returns:
            ActionExecution record or None if not found
            
        Raises:
            ActionExecutionError: If status retrieval fails
        """
        ...
    
    @abstractmethod
    async def cancel_execution(
        self, 
        execution_id: ActionId, 
        reason: str = "Cancelled by request"
    ) -> bool:
        """Cancel a running or pending action execution.
        
        Attempts to cancel the execution gracefully and updates the execution record
        with cancellation information.
        
        Args:
            execution_id: ID of the execution to cancel
            reason: Reason for cancellation
            
        Returns:
            True if cancellation was successful, False if execution couldn't be cancelled
            
        Raises:
            ActionExecutionError: If cancellation operation fails
        """
        ...
    
    @abstractmethod
    async def update_execution_progress(
        self,
        execution_id: ActionId,
        progress_data: Dict[str, Any],
        status: Optional[str] = None
    ) -> bool:
        """Update progress information for a long-running execution.
        
        Allows handlers to report progress for long-running operations.
        
        Args:
            execution_id: ID of the execution to update
            progress_data: Progress information (percentage, current step, etc.)
            status: Optional status update (if transitioning states)
            
        Returns:
            True if update was successful, False otherwise
            
        Raises:
            ActionExecutionError: If progress update fails
        """
        ...

    # ===========================================
    # Retry and Error Recovery Operations
    # ===========================================
    
    @abstractmethod
    async def retry_failed_execution(
        self,
        execution_id: ActionId,
        retry_reason: Optional[str] = None,
        override_retry_limit: Optional[bool] = False
    ) -> ActionExecution:
        """Retry a failed action execution with intelligent backoff.
        
        Attempts to re-execute a failed action following the configured retry strategy:
        - Exponential backoff based on action configuration
        - Retry count validation against max_retries limit
        - Error classification for retry eligibility
        
        Args:
            execution_id: ID of the failed execution to retry
            retry_reason: Optional reason for manual retry
            override_retry_limit: Whether to ignore max retry limit (admin only)
            
        Returns:
            New ActionExecution record for the retry attempt
            
        Raises:
            ActionExecutionError: If retry setup fails
            RetryLimitExceededError: If retry limit has been reached
            RetryNotAllowedError: If execution is not eligible for retry
        """
        ...
    
    @abstractmethod
    async def retry_failed_executions_batch(
        self,
        limit: int = 100,
        event_types: Optional[List[str]] = None,
        handler_types: Optional[List[str]] = None,
        max_age_hours: int = 24
    ) -> int:
        """Batch retry of failed executions with intelligent filtering.
        
        Finds and retries eligible failed executions using configurable criteria
        and retry policies. Useful for scheduled batch recovery operations.
        
        Args:
            limit: Maximum number of executions to retry
            event_types: Optional filter by event types
            handler_types: Optional filter by handler types
            max_age_hours: Maximum age of failures to consider for retry
            
        Returns:
            Count of retry attempts initiated
            
        Raises:
            ActionExecutionError: If batch retry operation fails
        """
        ...
    
    @abstractmethod
    async def get_failed_executions(
        self,
        limit: int = 100,
        event_type: Optional[str] = None,
        handler_type: Optional[str] = None,
        retry_eligible_only: bool = True,
        include_timeout: bool = True
    ) -> List[ActionExecution]:
        """Get failed executions eligible for retry or analysis.
        
        Retrieves failed executions with filtering options for operations
        like batch retry, error analysis, and monitoring dashboards.
        
        Args:
            limit: Maximum number of executions to return
            event_type: Optional filter by event type
            handler_type: Optional filter by handler type
            retry_eligible_only: Only return executions eligible for retry
            include_timeout: Whether to include timeout failures
            
        Returns:
            List of failed ActionExecution records
            
        Raises:
            ActionExecutionError: If retrieval fails
        """
        ...

    # ===========================================
    # Performance and Monitoring Operations
    # ===========================================
    
    @abstractmethod
    async def get_execution_statistics(
        self,
        action_id: Optional[ActionId] = None,
        event_type: Optional[str] = None,
        handler_type: Optional[str] = None,
        time_range_hours: int = 24
    ) -> Dict[str, Any]:
        """Get execution statistics for monitoring and performance analysis.
        
        Provides comprehensive statistics for specific actions, event types,
        handler types, or platform-wide metrics.
        
        Args:
            action_id: Optional specific action to analyze
            event_type: Optional event type filter
            handler_type: Optional handler type filter
            time_range_hours: Time range for statistics calculation
            
        Returns:
            Dict with execution statistics:
            - total_executions: Total execution count
            - successful_executions: Success count
            - failed_executions: Failure count
            - timeout_executions: Timeout count
            - retry_executions: Retry count
            - average_duration_ms: Average execution time
            - median_duration_ms: Median execution time
            - p95_duration_ms: 95th percentile execution time
            - success_rate: Success percentage
            - throughput_per_hour: Executions per hour
            - error_distribution: Error type breakdown
            
        Raises:
            ActionExecutionError: If statistics calculation fails
        """
        ...
    
    @abstractmethod
    async def get_active_executions(
        self,
        action_id: Optional[ActionId] = None,
        event_type: Optional[str] = None,
        handler_type: Optional[str] = None
    ) -> List[ActionExecution]:
        """Get currently running action executions.
        
        Returns executions in 'running' or 'pending' state for monitoring
        active operations and detecting stuck executions.
        
        Args:
            action_id: Optional filter by specific action
            event_type: Optional filter by event type
            handler_type: Optional filter by handler type
            
        Returns:
            List of active ActionExecution records
            
        Raises:
            ActionExecutionError: If retrieval fails
        """
        ...
    
    @abstractmethod
    async def cleanup_completed_executions(
        self,
        retention_days: int = 30,
        keep_failures: bool = True,
        batch_size: int = 1000
    ) -> int:
        """Clean up old completed executions for performance maintenance.
        
        Removes old execution records to maintain database performance
        while preserving important failure information for analysis.
        
        Args:
            retention_days: Days to retain execution records
            keep_failures: Whether to preserve failed executions longer
            batch_size: Number of records to delete per batch
            
        Returns:
            Count of execution records cleaned up
            
        Raises:
            ActionExecutionError: If cleanup operation fails
        """
        ...

    # ===========================================
    # Handler Integration Operations
    # ===========================================
    
    @abstractmethod
    async def register_handler(
        self,
        handler_type: str,
        handler_instance: Any,
        priority: int = 100,
        configuration: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Register a new action handler for a specific handler type.
        
        Allows dynamic registration of action handlers for different types
        like webhook, email, function, workflow, etc.
        
        Args:
            handler_type: Type identifier for the handler
            handler_instance: Handler implementation instance
            priority: Handler priority (lower numbers execute first)
            configuration: Optional handler configuration
            
        Returns:
            True if handler was registered successfully
            
        Raises:
            HandlerRegistrationError: If handler registration fails
        """
        ...
    
    @abstractmethod
    async def unregister_handler(
        self,
        handler_type: str,
        handler_instance: Optional[Any] = None
    ) -> bool:
        """Unregister an action handler.
        
        Removes a handler from the registry. If handler_instance is provided,
        only that specific instance is removed.
        
        Args:
            handler_type: Type identifier for the handler
            handler_instance: Optional specific handler instance to remove
            
        Returns:
            True if handler was unregistered successfully
            
        Raises:
            HandlerRegistrationError: If handler unregistration fails
        """
        ...
    
    @abstractmethod
    async def get_available_handlers(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all available action handlers and their configurations.
        
        Returns information about registered handlers for monitoring
        and configuration purposes.
        
        Returns:
            Dict mapping handler types to list of handler information:
            - handler_type -> [{"priority": int, "configuration": dict, ...}]
            
        Raises:
            ActionExecutionError: If handler information retrieval fails
        """
        ...