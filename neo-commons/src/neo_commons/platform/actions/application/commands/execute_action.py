"""Execute action command."""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime

from ...domain.entities.action import Action, ActionStatus
from ...domain.entities.action_execution import ActionExecution
from ...domain.value_objects.execution_id import ExecutionId
from ....events.domain.entities.domain_event import DomainEvent
from ..protocols.action_execution_repository import ActionExecutionRepositoryProtocol
from ..protocols.action_executor import ActionExecutorProtocol, ExecutionContext
from ....utils import generate_uuid_v7


@dataclass
class ExecuteActionRequest:
    """Request to execute an action."""
    
    action: Action
    event: DomainEvent
    execution_context: Optional[Dict[str, Any]] = None
    input_data: Optional[Dict[str, Any]] = None
    parent_execution_id: Optional[ExecutionId] = None
    attempt_number: int = 1
    worker_id: Optional[str] = None


class ExecuteActionCommand:
    """Command to execute an action."""
    
    def __init__(
        self,
        action_executor: ActionExecutorProtocol,
        execution_repository: ActionExecutionRepositoryProtocol
    ):
        self.action_executor = action_executor
        self.execution_repository = execution_repository
    
    async def execute(self, request: ExecuteActionRequest, schema: str) -> ActionExecution:
        """
        Execute an action for a given event.
        
        Args:
            request: Action execution request
            schema: Database schema name (admin, tenant_xxx, etc.)
            
        Returns:
            Action execution entity with results
            
        Raises:
            ActionExecutionError: If execution fails
        """
        # Create execution record
        execution = ActionExecution(
            id=ExecutionId(generate_uuid_v7()),
            event_id=request.event.id,
            action_id=request.action.id,
            execution_context=request.execution_context or {},
            input_data=request.input_data or request.event.event_data,
            output_data={},
            status=ActionStatus.PENDING,
            queued_at=datetime.now(),
            started_at=None,
            completed_at=None,
            execution_duration_ms=None,
            attempt_number=request.attempt_number,
            is_retry=request.parent_execution_id is not None,
            parent_execution_id=request.parent_execution_id,
            error_message=None,
            error_details=None,
            error_stack_trace=None,
            queue_message_id=None,
            worker_id=request.worker_id,
            memory_usage_mb=None,
            cpu_time_ms=None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Save initial execution record
        execution = await self.execution_repository.save(execution, schema)
        
        # Create execution context
        context = ExecutionContext(
            schema=schema,
            event=request.event,
            tenant_id=getattr(request.event, 'tenant_id', None),
            organization_id=getattr(request.event, 'organization_id', None),
            user_id=getattr(request.event, 'user_id', None),
            correlation_id=getattr(request.event, 'correlation_id', None)
        )
        
        try:
            # Mark as started
            await self.execution_repository.mark_as_started(
                execution.id, 
                request.worker_id or "unknown",
                schema
            )
            
            # Execute the action
            start_time = datetime.now()
            result = await self.action_executor.execute(
                request.action,
                execution.input_data,
                context
            )
            end_time = datetime.now()
            
            # Calculate execution duration
            execution_duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            if result.success:
                # Mark as completed
                await self.execution_repository.mark_as_completed(
                    execution.id,
                    result.output_data,
                    execution_duration_ms,
                    schema
                )
                execution.status = ActionStatus.COMPLETED
                execution.output_data = result.output_data
                execution.completed_at = end_time
                execution.execution_duration_ms = execution_duration_ms
            else:
                # Mark as failed
                await self.execution_repository.mark_as_failed(
                    execution.id,
                    result.error_message or "Execution failed",
                    result.error_details or {},
                    result.error_stack_trace,
                    execution_duration_ms,
                    schema
                )
                execution.status = ActionStatus.FAILED
                execution.error_message = result.error_message
                execution.error_details = result.error_details
                execution.error_stack_trace = result.error_stack_trace
                execution.completed_at = end_time
                execution.execution_duration_ms = execution_duration_ms
            
        except Exception as e:
            # Handle unexpected errors
            await self.execution_repository.mark_as_failed(
                execution.id,
                str(e),
                {"error_type": type(e).__name__},
                None,
                None,
                schema
            )
            execution.status = ActionStatus.FAILED
            execution.error_message = str(e)
            execution.error_details = {"error_type": type(e).__name__}
            execution.completed_at = datetime.now()
        
        return execution