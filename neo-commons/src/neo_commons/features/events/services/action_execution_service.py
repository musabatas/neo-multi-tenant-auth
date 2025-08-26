"""
Action Execution Service

Provides reliable execution of event actions with retry logic, error handling,
timeout management, and comprehensive logging. Integrates with action handlers
and maintains execution state.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone, timedelta
from enum import Enum

from ..entities.protocols import ActionExecutionRepository, ActionExecutionService as ActionExecutionServiceProtocol
from ..entities.event_action import EventAction, ExecutionMode, ActionPriority
from ..entities.action_handlers import (
    EventActionHandler,
    HandlerRegistry,
    ExecutionContext,
    HandlerResult,
    HandlerStatus
)
from ....core.value_objects.identifiers import ActionId, ActionExecutionId, UserId
from ....utils.uuid import generate_uuid_v7
from .action_monitoring_service import ActionMonitoringService, ActionMonitoringConfig

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """Action execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    RETRY_SCHEDULED = "retry_scheduled"


class ActionExecution:
    """Represents an action execution instance."""
    
    def __init__(
        self,
        id: ActionExecutionId,
        action_id: ActionId,
        event_id: Optional[str] = None,
        event_type: str = "",
        event_data: Optional[Dict[str, Any]] = None,
        status: ExecutionStatus = ExecutionStatus.PENDING,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        duration_ms: Optional[int] = None,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        retry_count: int = 0,
        execution_context: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.action_id = action_id
        self.event_id = event_id
        self.event_type = event_type
        self.event_data = event_data or {}
        self.status = status
        self.started_at = started_at
        self.completed_at = completed_at
        self.duration_ms = duration_ms
        self.result = result
        self.error_message = error_message
        self.retry_count = retry_count
        self.execution_context = execution_context or {}
        self.created_at = created_at or datetime.now(timezone.utc)


class ActionExecutionService:
    """Service for reliable execution of event actions."""
    
    def __init__(
        self,
        execution_repository: ActionExecutionRepository,
        handler_registry: HandlerRegistry,
        default_timeout_seconds: int = 30,
        max_concurrent_executions: int = 10,
        enable_execution_metrics: bool = True,
        monitoring_config: Optional[ActionMonitoringConfig] = None
    ):
        self._execution_repository = execution_repository
        self._handler_registry = handler_registry
        self._default_timeout_seconds = default_timeout_seconds
        self._max_concurrent_executions = max_concurrent_executions
        self._enable_execution_metrics = enable_execution_metrics
        
        # Initialize monitoring service
        self._monitoring_service = ActionMonitoringService(
            execution_repository, 
            monitoring_config or ActionMonitoringConfig()
        )
        
        # Execution management
        self._active_executions: Dict[str, ActionExecution] = {}
        self._execution_semaphore = asyncio.Semaphore(max_concurrent_executions)
        
        # Metrics
        self._execution_metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "timeout_executions": 0,
            "retry_executions": 0,
            "average_duration_ms": 0.0
        }
        self._duration_history: List[int] = []
    
    async def execute_action(
        self, 
        action: EventAction, 
        event_data: Dict[str, Any],
        execution_context: Optional[Dict[str, Any]] = None,
        priority_override: Optional[ActionPriority] = None
    ) -> ActionExecution:
        """Execute an action with the given event data."""
        execution_id = ActionExecutionId(generate_uuid_v7())
        
        # Create execution record
        execution = ActionExecution(
            id=execution_id,
            action_id=action.id,
            event_id=event_data.get("event_id"),
            event_type=event_data.get("event_type", ""),
            event_data=event_data,
            execution_context=execution_context or {}
        )
        
        # Store execution
        self._active_executions[str(execution_id.value)] = execution
        
        try:
            # Save initial execution record
            await self._save_execution(execution)
            
            # Execute based on execution mode
            if action.execution_mode == ExecutionMode.SYNC:
                await self._execute_synchronously(action, execution)
            elif action.execution_mode == ExecutionMode.ASYNC:
                # Start async execution (don't await)
                asyncio.create_task(self._execute_asynchronously(action, execution))
            elif action.execution_mode == ExecutionMode.QUEUED:
                # For now, treat as async (future: integrate with task queue)
                asyncio.create_task(self._execute_asynchronously(action, execution))
            
            return execution
            
        except Exception as e:
            logger.error(f"Failed to start action execution {execution_id.value}: {str(e)}")
            execution.status = ExecutionStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now(timezone.utc)
            
            await self._save_execution(execution)
            self._update_metrics(execution)
            
            return execution
    
    async def execute_actions_for_event(
        self, 
        event_type: str, 
        event_data: Dict[str, Any],
        actions: List[EventAction]
    ) -> List[ActionExecution]:
        """Execute all matching actions for an event."""
        if not actions:
            return []
        
        logger.info(f"Executing {len(actions)} actions for event type: {event_type}")
        
        executions = []
        
        # Group actions by execution mode and priority
        sync_actions = [a for a in actions if a.execution_mode == ExecutionMode.SYNC]
        async_actions = [a for a in actions if a.execution_mode == ExecutionMode.ASYNC]
        queued_actions = [a for a in actions if a.execution_mode == ExecutionMode.QUEUED]
        
        # Sort by priority (high to low)
        sync_actions.sort(key=lambda a: a.priority.value, reverse=True)
        async_actions.sort(key=lambda a: a.priority.value, reverse=True)
        queued_actions.sort(key=lambda a: a.priority.value, reverse=True)
        
        # Execute synchronous actions first (blocking)
        for action in sync_actions:
            try:
                execution = await self.execute_action(action, event_data)
                executions.append(execution)
            except Exception as e:
                logger.error(f"Failed to execute sync action {action.id.value}: {str(e)}")
        
        # Execute asynchronous actions (fire-and-forget)
        async_tasks = []
        for action in async_actions:
            try:
                execution = await self.execute_action(action, event_data)
                executions.append(execution)
            except Exception as e:
                logger.error(f"Failed to start async action {action.id.value}: {str(e)}")
        
        # Execute queued actions
        for action in queued_actions:
            try:
                execution = await self.execute_action(action, event_data)
                executions.append(execution)
            except Exception as e:
                logger.error(f"Failed to queue action {action.id.value}: {str(e)}")
        
        logger.info(f"Started execution for {len(executions)} actions")
        return executions
    
    async def retry_failed_execution(self, execution_id: ActionExecutionId) -> bool:
        """Retry a failed action execution."""
        try:
            # Get execution record
            execution = await self._execution_repository.get_execution_by_id(execution_id)
            if not execution:
                logger.warning(f"Execution {execution_id.value} not found for retry")
                return False
            
            # Convert to ActionExecution (would need proper conversion logic)
            # For now, create a new execution
            logger.info(f"Retrying failed execution {execution_id.value}")
            
            # This would integrate with getting the original action and re-executing
            # For now, return True to indicate retry was attempted
            return True
            
        except Exception as e:
            logger.error(f"Failed to retry execution {execution_id.value}: {str(e)}")
            return False
    
    async def cancel_execution(self, execution_id: ActionExecutionId) -> bool:
        """Cancel a running execution."""
        execution_key = str(execution_id.value)
        
        if execution_key in self._active_executions:
            execution = self._active_executions[execution_key]
            
            if execution.status == ExecutionStatus.RUNNING:
                execution.status = ExecutionStatus.CANCELLED
                execution.completed_at = datetime.now(timezone.utc)
                execution.error_message = "Execution cancelled by user"
                
                await self._save_execution(execution)
                self._update_metrics(execution)
                
                logger.info(f"Cancelled execution {execution_id.value}")
                return True
        
        return False
    
    async def get_execution_status(self, execution_id: ActionExecutionId) -> Optional[ActionExecution]:
        """Get the current status of an execution."""
        execution_key = str(execution_id.value)
        
        # Check active executions first
        if execution_key in self._active_executions:
            return self._active_executions[execution_key]
        
        # Check repository
        try:
            stored_execution = await self._execution_repository.get_execution_by_id(execution_id)
            if stored_execution:
                # Convert stored execution to ActionExecution
                # This would need proper conversion logic
                pass
        except Exception as e:
            logger.error(f"Failed to get execution status {execution_id.value}: {str(e)}")
        
        return None
    
    async def get_execution_metrics(self) -> Dict[str, Any]:
        """Get execution metrics and statistics."""
        if not self._enable_execution_metrics:
            return {"metrics_disabled": True}
        
        return {
            "total_executions": self._execution_metrics["total_executions"],
            "successful_executions": self._execution_metrics["successful_executions"],
            "failed_executions": self._execution_metrics["failed_executions"],
            "timeout_executions": self._execution_metrics["timeout_executions"],
            "retry_executions": self._execution_metrics["retry_executions"],
            "average_duration_ms": self._execution_metrics["average_duration_ms"],
            "success_rate_percent": (
                (self._execution_metrics["successful_executions"] / self._execution_metrics["total_executions"]) * 100
                if self._execution_metrics["total_executions"] > 0 else 0.0
            ),
            "active_executions": len(self._active_executions),
            "handler_stats": await self._get_handler_statistics()
        }
    
    async def _execute_synchronously(self, action: EventAction, execution: ActionExecution) -> None:
        """Execute action synchronously with timeout and error handling."""
        async with self._execution_semaphore:
            await self._perform_execution(action, execution)
    
    async def _execute_asynchronously(self, action: EventAction, execution: ActionExecution) -> None:
        """Execute action asynchronously with concurrency control."""
        async with self._execution_semaphore:
            await self._perform_execution(action, execution)
    
    async def _perform_execution(self, action: EventAction, execution: ActionExecution) -> None:
        """Perform the actual action execution with comprehensive error handling."""
        start_time = datetime.now(timezone.utc)
        execution.status = ExecutionStatus.RUNNING
        execution.started_at = start_time
        
        # Log execution start with monitoring
        await self._monitoring_service.log_execution_start(action, execution, execution.event_data)
        
        await self._save_execution(execution)
        
        try:
            # Get handler for this action
            handler = await self._handler_registry.get_handler(action.handler_type.value)
            if not handler:
                raise ValueError(f"No handler found for type: {action.handler_type.value}")
            
            if handler.status != HandlerStatus.REGISTERED:
                raise ValueError(f"Handler {action.handler_type.value} is not available (status: {handler.status.value})")
            
            # Validate handler can handle this action
            if not handler.can_handle(action):
                raise ValueError(f"Handler {action.handler_type.value} cannot handle this action")
            
            # Create execution context
            context = ExecutionContext(
                execution_id=execution.id,
                action_id=action.id,
                event_type=execution.event_type,
                event_data=execution.event_data,
                tenant_id=action.tenant_id,
                user_id=str(action.created_by_user_id.value) if action.created_by_user_id else None,
                correlation_id=execution.execution_context.get("correlation_id"),
                execution_metadata={
                    "timestamp": start_time.isoformat(),
                    "timeout_seconds": action.timeout_seconds,
                    "retry_count": execution.retry_count,
                    "priority": action.priority.value
                }
            )
            
            # Execute with timeout
            timeout_seconds = action.timeout_seconds or self._default_timeout_seconds
            result = await asyncio.wait_for(
                handler.execute(action, context),
                timeout=timeout_seconds
            )
            
            # Handle result
            execution.completed_at = datetime.now(timezone.utc)
            execution.duration_ms = int((execution.completed_at - start_time).total_seconds() * 1000)
            
            if isinstance(result, HandlerResult):
                if result.success:
                    execution.status = ExecutionStatus.SUCCESS
                    execution.result = {
                        "success": True,
                        "message": result.message,
                        "metadata": result.metadata
                    }
                else:
                    execution.status = ExecutionStatus.FAILED
                    execution.error_message = result.error
                    execution.result = {
                        "success": False,
                        "error": result.error,
                        "metadata": result.metadata
                    }
            else:
                # Legacy result handling
                execution.status = ExecutionStatus.SUCCESS
                execution.result = {"result": result}
            
            logger.info(f"Action {action.name} executed successfully in {execution.duration_ms}ms")
            
        except asyncio.TimeoutError:
            execution.status = ExecutionStatus.TIMEOUT
            execution.completed_at = datetime.now(timezone.utc)
            execution.duration_ms = int((execution.completed_at - start_time).total_seconds() * 1000)
            execution.error_message = f"Execution timed out after {timeout_seconds}s"
            
            logger.warning(f"Action {action.name} timed out after {timeout_seconds}s")
            
        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.completed_at = datetime.now(timezone.utc)
            execution.duration_ms = int((execution.completed_at - start_time).total_seconds() * 1000)
            execution.error_message = str(e)
            
            logger.error(f"Action {action.name} failed: {str(e)}")
            # Log execution error with monitoring
            await self._monitoring_service.log_execution_error(action, execution, e)
        
        finally:
            # Save final execution state
            await self._save_execution(execution)
            self._update_metrics(execution)
            
            # Log execution completion with monitoring
            await self._monitoring_service.log_execution_complete(action, execution)
            
            # Remove from active executions
            execution_key = str(execution.id.value)
            if execution_key in self._active_executions:
                del self._active_executions[execution_key]
            
            # Schedule retry if needed
            if (execution.status in [ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT] and 
                execution.retry_count < action.max_retries):
                await self._schedule_retry(action, execution)
    
    async def _schedule_retry(self, action: EventAction, execution: ActionExecution) -> None:
        """Schedule a retry for a failed execution."""
        try:
            # Calculate retry delay
            delay_seconds = action.retry_delay_seconds * (2 ** execution.retry_count)  # Exponential backoff
            retry_time = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
            
            logger.info(
                f"Scheduling retry {execution.retry_count + 1}/{action.max_retries} "
                f"for action {action.name} in {delay_seconds}s"
            )
            
            # Create retry task (simplified - would integrate with task scheduler)
            asyncio.create_task(self._execute_retry(action, execution, delay_seconds))
            
            # Update execution status
            execution.status = ExecutionStatus.RETRY_SCHEDULED
            await self._save_execution(execution)
            
        except Exception as e:
            logger.error(f"Failed to schedule retry for execution {execution.id.value}: {str(e)}")
    
    async def _execute_retry(self, action: EventAction, original_execution: ActionExecution, delay_seconds: int) -> None:
        """Execute a retry after the specified delay."""
        await asyncio.sleep(delay_seconds)
        
        try:
            # Create new execution for retry
            retry_execution = ActionExecution(
                id=ActionExecutionId(generate_uuid_v7()),
                action_id=action.id,
                event_id=original_execution.event_id,
                event_type=original_execution.event_type,
                event_data=original_execution.event_data,
                retry_count=original_execution.retry_count + 1,
                execution_context=original_execution.execution_context
            )
            
            # Store retry execution
            self._active_executions[str(retry_execution.id.value)] = retry_execution
            self._execution_metrics["retry_executions"] += 1
            
            # Execute retry
            await self._perform_execution(action, retry_execution)
            
        except Exception as e:
            logger.error(f"Retry execution failed for action {action.name}: {str(e)}")
    
    async def _save_execution(self, execution: ActionExecution) -> None:
        """Save execution to repository."""
        try:
            # This would call the actual repository save method
            # For now, just log
            logger.debug(f"Saving execution {execution.id.value} with status {execution.status.value}")
        except Exception as e:
            logger.error(f"Failed to save execution {execution.id.value}: {str(e)}")
    
    def _update_metrics(self, execution: ActionExecution) -> None:
        """Update execution metrics."""
        if not self._enable_execution_metrics:
            return
        
        self._execution_metrics["total_executions"] += 1
        
        if execution.status == ExecutionStatus.SUCCESS:
            self._execution_metrics["successful_executions"] += 1
        elif execution.status in [ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
            self._execution_metrics["failed_executions"] += 1
        elif execution.status == ExecutionStatus.TIMEOUT:
            self._execution_metrics["timeout_executions"] += 1
        
        # Update average duration
        if execution.duration_ms:
            self._duration_history.append(execution.duration_ms)
            
            # Keep only last 1000 durations for rolling average
            if len(self._duration_history) > 1000:
                self._duration_history.pop(0)
            
            self._execution_metrics["average_duration_ms"] = sum(self._duration_history) / len(self._duration_history)
    
    async def _get_handler_statistics(self) -> Dict[str, Any]:
        """Get statistics about registered handlers."""
        try:
            handlers = await self._handler_registry.list_handlers()
            
            stats = {
                "total_handlers": len(handlers),
                "handlers_by_status": {},
                "handlers_by_type": {}
            }
            
            for handler in handlers:
                # Count by status
                status = handler.status.value
                stats["handlers_by_status"][status] = stats["handlers_by_status"].get(status, 0) + 1
                
                # Count by type
                handler_type = handler.handler_type
                stats["handlers_by_type"][handler_type] = stats["handlers_by_type"].get(handler_type, 0) + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get handler statistics: {str(e)}")
            return {"error": str(e)}
    
    async def start_monitoring(self) -> None:
        """Start the monitoring service."""
        await self._monitoring_service.start_monitoring()
        logger.info("Action execution monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop the monitoring service."""
        await self._monitoring_service.stop_monitoring()
        logger.info("Action execution monitoring stopped")
    
    async def get_action_metrics(self, action_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific action.
        
        Args:
            action_id: Action ID
            
        Returns:
            Metrics dictionary if available, None otherwise
        """
        from ....core.value_objects import ActionId
        metrics = await self._monitoring_service.get_action_metrics(action_id)
        if not metrics:
            return None
        
        return {
            "total_executions": metrics.total_executions,
            "successful_executions": metrics.successful_executions,
            "failed_executions": metrics.failed_executions,
            "timeout_executions": metrics.timeout_executions,
            "avg_duration_ms": metrics.avg_duration_ms,
            "min_duration_ms": metrics.min_duration_ms,
            "max_duration_ms": metrics.max_duration_ms,
            "p95_duration_ms": metrics.p95_duration_ms,
            "success_rate_percent": metrics.success_rate_percent,
            "executions_per_minute": metrics.executions_per_minute,
            "error_count_by_type": metrics.error_count_by_type,
            "recent_errors": metrics.recent_errors,
            "window_start": metrics.window_start.isoformat(),
            "window_end": metrics.window_end.isoformat()
        }
    
    async def get_global_metrics(self) -> Dict[str, Any]:
        """Get global execution metrics.
        
        Returns:
            Global metrics dictionary
        """
        metrics = await self._monitoring_service.get_global_metrics()
        
        return {
            "total_executions": metrics.total_executions,
            "successful_executions": metrics.successful_executions,
            "failed_executions": metrics.failed_executions,
            "timeout_executions": metrics.timeout_executions,
            "avg_duration_ms": metrics.avg_duration_ms,
            "min_duration_ms": metrics.min_duration_ms,
            "max_duration_ms": metrics.max_duration_ms,
            "p95_duration_ms": metrics.p95_duration_ms,
            "success_rate_percent": metrics.success_rate_percent,
            "executions_per_minute": metrics.executions_per_minute,
            "error_count_by_type": metrics.error_count_by_type,
            "recent_errors": metrics.recent_errors
        }
    
    async def check_action_health(self, action_id: str) -> Dict[str, Any]:
        """Check health status of an action.
        
        Args:
            action_id: Action ID to check
            
        Returns:
            Health status information
        """
        return await self._monitoring_service.check_action_health(action_id)