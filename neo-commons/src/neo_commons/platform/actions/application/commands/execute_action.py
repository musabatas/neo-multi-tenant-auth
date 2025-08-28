"""Execute action command for platform actions infrastructure.

This module handles ONLY action execution operations following maximum separation architecture.
Single responsibility: Execute actions with proper lifecycle management and error handling.

Pure application layer - no infrastructure concerns.
Uses protocols for dependency injection and clean architecture compliance.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime
from uuid import UUID

from ...core.protocols import ActionExecutor, ActionRepository
from ...core.entities import Action, ActionExecution
from ...core.value_objects import ActionId
from ...core.exceptions import ActionExecutionFailed
from neo_commons.core.value_objects import UserId
from neo_commons.utils import utc_now, generate_uuid_v7


@dataclass
class ExecuteActionData:
    """Data required to execute an action.
    
    Contains all the information needed to execute an action.
    Separates data from business logic following CQRS patterns.
    """
    action_id: ActionId
    event_data: Dict[str, Any]
    event_type: Optional[str] = None
    execution_context: Optional[Dict[str, Any]] = None
    triggered_by_user_id: Optional[UserId] = None
    correlation_id: Optional[str] = None
    force_execute: bool = False
    timeout_override: Optional[int] = None
    
    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.execution_context is None:
            self.execution_context = {}


@dataclass
class ExecuteActionResult:
    """Result of action execution operation.
    
    Contains comprehensive execution results for monitoring and tracking.
    Provides structured feedback about the execution process.
    """
    action_id: ActionId
    execution_id: ActionId
    executed_successfully: bool
    action_execution: Optional[ActionExecution] = None
    execution_time_ms: Optional[int] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    handler_result: Optional[Dict[str, Any]] = None


class ExecuteActionCommand:
    """Command to execute an action with complete lifecycle management.
    
    Single responsibility: Orchestrate the execution of an action including
    action retrieval, validation, handler execution, state management, error handling,
    and result tracking. Ensures proper execution lifecycle and performance monitoring.
    
    Following enterprise command pattern with protocol-based dependencies.
    Pure application logic - delegates infrastructure concerns to protocols.
    """
    
    def __init__(
        self,
        action_executor: ActionExecutor,
        action_repository: ActionRepository
    ):
        """Initialize execute action command with required dependencies.
        
        Args:
            action_executor: Protocol for executing actions with handlers
            action_repository: Protocol for action persistence operations
        """
        self._action_executor = action_executor
        self._action_repository = action_repository
    
    async def execute(self, data: ExecuteActionData) -> ExecuteActionResult:
        """Execute action execution command.
        
        Orchestrates the complete action execution process:
        1. Retrieve action configuration from repository
        2. Validate action is eligible for execution
        3. Execute action using appropriate handler
        4. Track execution results and performance
        5. Handle errors and retry logic
        6. Return comprehensive execution results
        
        Args:
            data: Action execution configuration data
            
        Returns:
            ExecuteActionResult with comprehensive execution information
            
        Raises:
            ActionExecutionFailed: If action execution setup fails
        """
        start_time = utc_now()
        
        try:
            # 1. Retrieve action configuration
            action = await self._action_repository.get_action_by_id(data.action_id)
            if not action:
                raise ActionExecutionFailed(
                    f"Action with ID {data.action_id.value} not found",
                    action_id=data.action_id
                )
            
            # 2. Validate action is eligible for execution
            if not data.force_execute:
                await self._validate_action_for_execution(action, data)
            
            # 3. Prepare execution context
            execution_context = {
                **data.execution_context,
                "timeout_override": data.timeout_override,
                "execution_mode": action.execution_mode.value,
                "priority": action.priority.value
            }
            
            # 4. Execute action using executor protocol
            action_execution = await self._action_executor.execute_action(
                action=action,
                event_data=data.event_data,
                execution_context=execution_context,
                triggered_by_user_id=data.triggered_by_user_id,
                correlation_id=data.correlation_id
            )
            
            # 5. Calculate execution metrics
            end_time = utc_now()
            execution_time_ms = (end_time - start_time).total_seconds() * 1000
            
            # 6. Update action statistics
            await self._update_action_statistics(
                action_id=data.action_id,
                execution_successful=action_execution.status == "success"
            )
            
            return ExecuteActionResult(
                action_id=data.action_id,
                execution_id=action_execution.id,
                executed_successfully=action_execution.status == "success",
                action_execution=action_execution,
                execution_time_ms=int(execution_time_ms),
                retry_count=action_execution.retry_count,
                handler_result=action_execution.result
            )
            
        except Exception as e:
            # Calculate execution time for failed operations
            end_time = utc_now()
            execution_time_ms = (end_time - start_time).total_seconds() * 1000
            
            # Update action statistics with failure
            await self._update_action_statistics(
                action_id=data.action_id,
                execution_successful=False
            )
            
            # Wrap in domain exception if needed
            if not isinstance(e, ActionExecutionFailed):
                raise ActionExecutionFailed(
                    f"Failed to execute action {data.action_id.value}: {str(e)}",
                    action_id=data.action_id,
                    original_error=e
                ) from e
            
            return ExecuteActionResult(
                action_id=data.action_id,
                execution_id=ActionId.generate(),  # Generate temp ID for error tracking
                executed_successfully=False,
                execution_time_ms=int(execution_time_ms),
                error_message=str(e)
            )
    
    async def execute_by_action(
        self,
        action: Action,
        event_data: Dict[str, Any],
        event_type: Optional[str] = None,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> ExecuteActionResult:
        """Execute action directly with action entity.
        
        Convenience method for executing when you already have the action entity.
        Delegates to main execute method for consistency.
        
        Args:
            action: Action to execute
            event_data: Event payload data for action processing
            event_type: Type of event that triggered this action
            execution_context: Additional context for execution
            
        Returns:
            ExecuteActionResult with execution information
            
        Raises:
            ActionExecutionFailed: If action execution fails
        """
        data = ExecuteActionData(
            action_id=action.id,
            event_data=event_data,
            event_type=event_type,
            execution_context=execution_context or {}
        )
        return await self.execute(data)
    
    async def execute_batch(
        self,
        execution_requests: List[ExecuteActionData]
    ) -> List[ExecuteActionResult]:
        """Execute batch action execution for multiple actions.
        
        Executes multiple actions efficiently while maintaining individual
        result tracking. Uses parallel processing for performance.
        
        Args:
            execution_requests: List of action execution requests
            
        Returns:
            List of execution results for each action
            
        Raises:
            ActionExecutionFailed: If batch execution setup fails
        """
        import asyncio
        
        # Create execution tasks for parallel execution
        execution_tasks = [
            self.execute(request)
            for request in execution_requests
        ]
        
        # Execute all actions in parallel
        results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        
        # Convert exceptions to failed results
        execution_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                execution_results.append(
                    ExecuteActionResult(
                        action_id=execution_requests[i].action_id,
                        execution_id=ActionId.generate(),
                        executed_successfully=False,
                        execution_time_ms=0,
                        error_message=str(result)
                    )
                )
            else:
                execution_results.append(result)
        
        return execution_results
    
    async def execute_with_retry(
        self,
        data: ExecuteActionData,
        max_retry_attempts: Optional[int] = None,
        retry_delay_seconds: Optional[int] = None
    ) -> ExecuteActionResult:
        """Execute action with automatic retry logic.
        
        Attempts to execute the action with automatic retry on failure.
        Uses exponential backoff for retry delays.
        
        Args:
            data: Action execution configuration data
            max_retry_attempts: Override max retry attempts from action config
            retry_delay_seconds: Override retry delay from action config
            
        Returns:
            ExecuteActionResult with final execution information
            
        Raises:
            ActionExecutionFailed: If all retry attempts fail
        """
        import asyncio
        
        # Get action configuration for retry settings
        action = await self._action_repository.get_action_by_id(data.action_id)
        if not action:
            raise ActionExecutionFailed(
                f"Action with ID {data.action_id.value} not found",
                action_id=data.action_id
            )
        
        # Use provided overrides or action defaults
        max_retries = max_retry_attempts or action.max_retries
        base_delay = retry_delay_seconds or action.retry_delay_seconds
        
        last_result = None
        
        for attempt in range(max_retries + 1):  # +1 for initial attempt
            try:
                result = await self.execute(data)
                
                if result.executed_successfully:
                    return result
                
                last_result = result
                
                # If this isn't the last attempt, wait before retrying
                if attempt < max_retries:
                    # Exponential backoff: base_delay * (2 ^ attempt)
                    delay = base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                
            except Exception as e:
                # If this is the last attempt, raise the exception
                if attempt == max_retries:
                    raise
                
                # Otherwise, wait and try again
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
        
        # Return the last result if we exhausted all retries
        if last_result:
            return last_result
        
        # This should never happen, but provide a fallback
        raise ActionExecutionFailed(
            f"Action {data.action_id.value} failed after {max_retries} retry attempts",
            action_id=data.action_id
        )
    
    async def _validate_action_for_execution(
        self,
        action: Action,
        data: ExecuteActionData
    ) -> None:
        """Validate that action is eligible for execution.
        
        Checks action state and configuration to ensure it can be executed.
        Prevents execution of disabled or misconfigured actions.
        
        Args:
            action: Action to validate
            data: Execution data to validate against action
            
        Raises:
            ActionExecutionFailed: If action is not eligible for execution
        """
        # Check if action is enabled and active
        if not action.is_enabled:
            raise ActionExecutionFailed(
                f"Action {action.id.value} is disabled",
                action_id=action.id
            )
        
        if action.status.value != "active":
            raise ActionExecutionFailed(
                f"Action {action.id.value} is not active (status: {action.status.value})",
                action_id=action.id
            )
        
        # Validate handler configuration exists
        if not action.configuration:
            raise ActionExecutionFailed(
                f"Action {action.id.value} has no handler configuration",
                action_id=action.id
            )
        
        # Check event type matching if specified
        if data.event_type and action.event_types:
            event_matches = any(
                self._event_type_matches(data.event_type, configured_type)
                for configured_type in action.event_types
            )
            
            if not event_matches:
                raise ActionExecutionFailed(
                    f"Event type '{data.event_type}' does not match action's configured types: {action.event_types}",
                    action_id=action.id
                )
    
    def _event_type_matches(self, event_type: str, configured_type: str) -> bool:
        """Check if an event type matches a configured type pattern.
        
        Supports wildcard matching for flexible event type configuration.
        
        Args:
            event_type: Actual event type from the event
            configured_type: Configured event type (may include wildcards)
            
        Returns:
            True if event type matches the configured pattern
        """
        if configured_type == "*":  # Wildcard - matches all
            return True
        elif configured_type.endswith(".*"):  # Category wildcard
            category = configured_type[:-2]
            return event_type.startswith(category + ".")
        else:  # Exact match
            return configured_type == event_type
    
    async def _update_action_statistics(
        self,
        action_id: ActionId,
        execution_successful: bool
    ) -> None:
        """Update action execution statistics.
        
        Updates action-level statistics for monitoring and performance tracking.
        Statistics are managed by the database through triggers.
        
        Args:
            action_id: ID of the action to update statistics for
            execution_successful: Whether the execution was successful
        """
        try:
            # Statistics are typically updated by database triggers
            # when action_executions records are created/updated
            # This method is a placeholder for any additional
            # application-level statistics tracking
            pass
        except Exception:
            # Don't fail the entire execution if statistics update fails
            # This is tracked separately for monitoring
            pass