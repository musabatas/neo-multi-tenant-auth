"""Action execution service for platform actions infrastructure.

Pure application service for orchestrating action execution with lifecycle management,
retry logic, error handling, and performance tracking. Follows maximum separation architecture.

Single responsibility: Coordinate action execution workflow across handlers,
repositories, and external services. Pure orchestration - no business logic.

Extracted from EventDispatcherService following enterprise patterns used by Amazon, Google, and Netflix.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Protocol, runtime_checkable
from datetime import datetime, timezone
from uuid import UUID

# Platform actions core imports (clean boundaries)
from ...core.entities import Action, ActionExecution
from ....events.core.entities import DomainEvent
from ...core.value_objects import ActionId, ExecutionMode, HandlerType, ActionStatus, ActionPriority
from ....events.core.value_objects import EventId
from ...core.exceptions import ActionExecutionFailed
from ....events.core.exceptions import InvalidEventConfiguration
from .....core.value_objects import UserId

# Platform protocols for dependency injection
from ...core.protocols import ActionExecutor, ActionRepository

logger = logging.getLogger(__name__)


@runtime_checkable
class ActionExecutionService(Protocol):
    """Action execution service protocol for platform actions orchestration.
    
    Pure application service that coordinates action execution workflow across 
    action handlers, repositories, and external services. Maintains single responsibility
    for action execution orchestration without business logic or infrastructure concerns.
    """
    
    async def execute_action(
        self,
        action: Action,
        event: DomainEvent,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> ActionExecution:
        """Execute single action with complete lifecycle management.
        
        Args:
            action: Action to execute
            event: Domain event that triggered the action
            execution_context: Additional context for execution
            
        Returns:
            ActionExecution tracking record
            
        Raises:
            ActionExecutionFailed: If action execution fails
        """
        ...
    
    async def execute_actions_for_event(
        self,
        event: DomainEvent,
        actions: List[Action],
        execution_context: Optional[Dict[str, Any]] = None
    ) -> List[ActionExecution]:
        """Execute multiple actions for an event with mode-based orchestration.
        
        Args:
            event: Domain event that triggered the actions
            actions: List of actions to execute
            execution_context: Additional context for execution
            
        Returns:
            List of action execution records
            
        Raises:
            ActionExecutionFailed: If batch execution fails
        """
        ...
    
    async def retry_failed_execution(
        self,
        execution_id: ActionId,
        retry_reason: Optional[str] = None
    ) -> ActionExecution:
        """Retry failed action execution with intelligent backoff.
        
        Args:
            execution_id: ID of failed execution to retry
            retry_reason: Optional reason for retry
            
        Returns:
            New execution record for retry attempt
            
        Raises:
            ActionExecutionFailed: If retry setup fails
        """
        ...


class DefaultActionExecutionService:
    """Default implementation of action execution service.
    
    Orchestrates action execution through handler pattern and repository
    composition. Maintains single responsibility for execution coordination.
    """
    
    def __init__(
        self,
        action_repository: Optional[ActionRepository] = None,
        handlers_registry: Optional[Dict[str, Any]] = None,
        default_timeout_seconds: int = 300,  # 5 minutes
        max_concurrent_actions: int = 10,
        max_retries: int = 3,
        retry_backoff_seconds: int = 5,
        enable_parallel_execution: bool = True
    ):
        """Initialize with injected dependencies.
        
        Args:
            action_repository: Action repository for persistence
            handlers_registry: Registry of action handlers by type
            default_timeout_seconds: Default timeout for action execution
            max_concurrent_actions: Maximum concurrent action executions
            max_retries: Maximum retry attempts for failed actions
            retry_backoff_seconds: Base backoff time between retries
            enable_parallel_execution: Enable parallel execution mode
        """
        self._action_repository = action_repository
        self._handlers_registry = handlers_registry or {}
        
        # Configuration
        self._default_timeout = default_timeout_seconds
        self._max_concurrent = max_concurrent_actions
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff_seconds
        self._enable_parallel = enable_parallel_execution
    
    async def execute_action(
        self,
        action: Action,
        event: DomainEvent,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> ActionExecution:
        """Execute single action with complete lifecycle management."""
        try:
            logger.info(f"Executing action {action.id.value} ({action.name}) for event {event.id.value}")
            
            # Create execution tracking record
            execution = ActionExecution.create_new(
                action_id=action.id,
                event_id=event.id,
                event_type=event.event_type.value,
                event_data=event.event_data,
                execution_context=execution_context or {}
            )
            
            # Persist execution record (if repository available)
            if self._action_repository:
                await self._action_repository.save_execution(execution)
            
            # Start execution
            execution.start_execution()
            
            try:
                # Get handler for action type
                handler = self._get_handler_for_action(action)
                if not handler:
                    raise ActionExecutionFailed(f"No handler available for action type: {action.handler_type.value}")
                
                # Execute action through handler with timeout
                result = await asyncio.wait_for(
                    handler.execute(action, event, execution_context),
                    timeout=self._default_timeout
                )
                
                # Mark as successful
                execution.complete_success(result or {})
                logger.info(f"Action {action.id.value} completed successfully")
                
            except asyncio.TimeoutError:
                execution.complete_timeout()
                logger.error(f"Action {action.id.value} timed out after {self._default_timeout}s")
                
            except Exception as e:
                execution.complete_failure(str(e))
                logger.error(f"Action {action.id.value} failed: {e}")
            
            # Update execution record in repository
            if self._action_repository:
                await self._action_repository.update_execution(execution)
            
            return execution
            
        except Exception as e:
            logger.error(f"Failed to execute action {action.id.value}: {e}")
            raise ActionExecutionFailed(f"Action execution failed: {e}")
    
    async def execute_actions_for_event(
        self,
        event: DomainEvent,
        actions: List[Action],
        execution_context: Optional[Dict[str, Any]] = None
    ) -> List[ActionExecution]:
        """Execute multiple actions for an event with mode-based orchestration."""
        if not actions:
            logger.debug(f"No actions to execute for event {event.id.value}")
            return []
        
        logger.info(f"Executing {len(actions)} actions for event {event.id.value}")
        
        try:
            # Sort actions by priority (higher priority first)
            sorted_actions = sorted(actions, key=lambda a: a.priority.value, reverse=True)
            
            # Group actions by execution mode
            sync_actions = [a for a in sorted_actions if a.execution_mode == ExecutionMode.SYNC]
            async_actions = [a for a in sorted_actions if a.execution_mode == ExecutionMode.ASYNC]
            queued_actions = [a for a in sorted_actions if a.execution_mode == ExecutionMode.QUEUED]
            
            executions = []
            
            # Execute synchronous actions sequentially (blocking)
            if sync_actions:
                logger.debug(f"Executing {len(sync_actions)} synchronous actions")
                for action in sync_actions:
                    execution = await self.execute_action(action, event, execution_context)
                    executions.append(execution)
                    
                    # Stop if sync action fails and is critical
                    if execution.is_failed() and action.priority == ActionPriority.CRITICAL:
                        logger.error(f"Critical synchronous action {action.id.value} failed, stopping execution")
                        break
            
            # Execute asynchronous actions concurrently (non-blocking)
            if async_actions and self._enable_parallel:
                logger.debug(f"Executing {len(async_actions)} asynchronous actions")
                async_executions = await self._execute_actions_parallel(
                    async_actions, 
                    event, 
                    execution_context
                )
                executions.extend(async_executions)
            elif async_actions:
                # Sequential fallback if parallel disabled
                for action in async_actions:
                    execution = await self.execute_action(action, event, execution_context)
                    executions.append(execution)
            
            # Handle queued actions (future enhancement - schedule for background processing)
            if queued_actions:
                logger.debug(f"Scheduling {len(queued_actions)} queued actions for background processing")
                queued_executions = await self._schedule_queued_actions(
                    queued_actions, 
                    event, 
                    execution_context
                )
                executions.extend(queued_executions)
            
            logger.info(f"Completed action execution for event {event.id.value}: {len(executions)} executions")
            return executions
            
        except Exception as e:
            logger.error(f"Failed to execute actions for event {event.id.value}: {e}")
            raise ActionExecutionFailed(f"Batch action execution failed: {e}")
    
    async def retry_failed_execution(
        self,
        execution_id: ActionId,
        retry_reason: Optional[str] = None
    ) -> ActionExecution:
        """Retry failed action execution with intelligent backoff."""
        try:
            if not self._action_repository:
                raise ActionExecutionFailed("Action repository not available for retry operations")
            
            # Get original execution
            original_execution = await self._action_repository.get_execution(execution_id)
            if not original_execution:
                raise ActionExecutionFailed(f"Execution {execution_id.value} not found")
            
            if not original_execution.is_failed():
                raise ActionExecutionFailed(f"Execution {execution_id.value} is not in failed state")
            
            if not original_execution.can_retry(self._max_retries):
                raise ActionExecutionFailed(f"Execution {execution_id.value} exceeded maximum retry limit")
            
            # Get the original action
            action = await self._action_repository.get_action(original_execution.action_id)
            if not action:
                raise ActionExecutionFailed(f"Action {original_execution.action_id.value} not found")
            
            logger.info(f"Retrying failed execution {execution_id.value} (attempt #{original_execution.retry_count + 1})")
            
            # Apply exponential backoff delay
            backoff_delay = self._retry_backoff * (2 ** original_execution.retry_count)
            await asyncio.sleep(backoff_delay)
            
            # Create new execution for retry
            retry_execution = ActionExecution.create_new(
                action_id=action.id,
                event_id=original_execution.event_id,
                event_type=original_execution.event_type,
                event_data=original_execution.event_data,
                execution_context={
                    **original_execution.execution_context,
                    "retry_of": str(execution_id.value),
                    "retry_reason": retry_reason or "Automatic retry",
                    "retry_attempt": original_execution.retry_count + 1
                }
            )
            retry_execution.retry_count = original_execution.retry_count + 1
            
            # Execute the retry
            handler = self._get_handler_for_action(action)
            if not handler:
                retry_execution.complete_failure(f"No handler available for action type: {action.handler_type.value}")
            else:
                retry_execution.start_execution()
                
                try:
                    # Recreate event for retry (simplified)
                    mock_event = type('MockEvent', (), {
                        'id': original_execution.event_id,
                        'event_type': type('EventType', (), {'value': original_execution.event_type})(),
                        'event_data': original_execution.event_data
                    })()
                    
                    result = await asyncio.wait_for(
                        handler.execute(action, mock_event, retry_execution.execution_context),
                        timeout=self._default_timeout
                    )
                    
                    retry_execution.complete_success(result or {})
                    logger.info(f"Retry execution {retry_execution.id.value} completed successfully")
                    
                except asyncio.TimeoutError:
                    retry_execution.complete_timeout()
                    logger.error(f"Retry execution {retry_execution.id.value} timed out")
                    
                except Exception as e:
                    retry_execution.complete_failure(str(e))
                    logger.error(f"Retry execution {retry_execution.id.value} failed: {e}")
            
            # Save retry execution
            await self._action_repository.save_execution(retry_execution)
            
            return retry_execution
            
        except Exception as e:
            logger.error(f"Failed to retry execution {execution_id.value}: {e}")
            raise ActionExecutionFailed(f"Retry execution failed: {e}")
    
    async def _execute_actions_parallel(
        self,
        actions: List[Action],
        event: DomainEvent,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> List[ActionExecution]:
        """Execute actions in parallel with controlled concurrency."""
        semaphore = asyncio.Semaphore(self._max_concurrent)
        
        async def execute_with_semaphore(action: Action) -> ActionExecution:
            async with semaphore:
                return await self.execute_action(action, event, execution_context)
        
        # Create tasks for parallel execution
        tasks = [execute_with_semaphore(action) for action in actions]
        
        # Wait for all executions to complete
        executions = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log them
        valid_executions = []
        for i, result in enumerate(executions):
            if isinstance(result, Exception):
                logger.error(f"Parallel action execution failed for action {actions[i].id.value}: {result}")
                # Create failed execution record
                failed_execution = ActionExecution.create_new(
                    action_id=actions[i].id,
                    event_id=event.id,
                    event_type=event.event_type.value,
                    event_data=event.event_data,
                    execution_context=execution_context or {}
                )
                failed_execution.complete_failure(str(result))
                valid_executions.append(failed_execution)
            else:
                valid_executions.append(result)
        
        return valid_executions
    
    async def _schedule_queued_actions(
        self,
        actions: List[Action],
        event: DomainEvent,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> List[ActionExecution]:
        """Schedule queued actions for background processing."""
        # For now, create pending execution records
        # In a full implementation, this would integrate with a task queue (Redis, Celery, etc.)
        executions = []
        
        for action in actions:
            execution = ActionExecution.create_new(
                action_id=action.id,
                event_id=event.id,
                event_type=event.event_type.value,
                event_data=event.event_data,
                execution_context={
                    **(execution_context or {}),
                    "queued_at": datetime.now(timezone.utc).isoformat(),
                    "execution_mode": "queued"
                }
            )
            # Keep as pending for queue processing
            executions.append(execution)
            
            # Save pending execution if repository available
            if self._action_repository:
                await self._action_repository.save_execution(execution)
            
            logger.debug(f"Queued action {action.id.value} for background processing")
        
        return executions
    
    def _get_handler_for_action(self, action: Action) -> Optional[Any]:
        """Get appropriate handler for action type."""
        handler_type = action.handler_type.value
        return self._handlers_registry.get(handler_type)
    
    async def get_execution_statistics(
        self,
        action_id: Optional[ActionId] = None,
        event_type: Optional[str] = None,
        time_range_hours: int = 24
    ) -> Dict[str, Any]:
        """Get execution statistics for monitoring."""
        if not self._action_repository:
            return {"error": "Action repository not available"}
        
        try:
            # This would query the repository for statistics
            # For now, return basic structure
            return {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "timeout_executions": 0,
                "average_duration_ms": 0.0,
                "success_rate": 0.0,
                "time_range_hours": time_range_hours,
                "query_filters": {
                    "action_id": str(action_id.value) if action_id else None,
                    "event_type": event_type
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get execution statistics: {e}")
            return {"error": f"Statistics retrieval failed: {e}"}
    
    async def cleanup_completed_executions(
        self,
        retention_days: int = 30,
        batch_size: int = 1000
    ) -> int:
        """Clean up old completed executions."""
        if not self._action_repository:
            logger.warning("Action repository not available for cleanup")
            return 0
        
        try:
            # Calculate cutoff date
            cutoff_date = datetime.now(timezone.utc) - timezone.timedelta(days=retention_days)
            
            logger.info(f"Starting cleanup of executions older than {retention_days} days")
            
            # This would call repository cleanup method
            # For now, return 0
            cleaned_count = 0
            
            logger.info(f"Cleanup completed: {cleaned_count} execution records removed")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup executions: {e}")
            return 0


# Factory function for creating service instances
def create_action_execution_service(
    action_repository: Optional[ActionRepository] = None,
    handlers_registry: Optional[Dict[str, Any]] = None,
    **config_options
) -> ActionExecutionService:
    """Create action execution service with dependency injection.
    
    Args:
        action_repository: Action repository implementation
        handlers_registry: Registry of action handlers by type
        **config_options: Configuration options (timeout, concurrency, retries, etc.)
        
    Returns:
        Configured action execution service instance
    """
    return DefaultActionExecutionService(
        action_repository=action_repository,
        handlers_registry=handlers_registry,
        **config_options
    )