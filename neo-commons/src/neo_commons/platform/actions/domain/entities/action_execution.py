"""Action Execution entity for tracking action execution history."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import UUID

from ..value_objects.execution_id import ExecutionId
from ..value_objects.action_id import ActionId
from ....events.domain.value_objects.event_id import EventId
from .action import ActionStatus
from ....utils import generate_uuid_v7


@dataclass
class ActionExecution:
    """
    Action Execution entity for tracking action execution history.
    
    Represents a single execution of an action in response to an event.
    Maps to the admin.action_executions and tenant_template.action_executions database tables.
    """
    
    # Core Identity (immutable after creation)
    id: ExecutionId
    event_id: EventId
    action_id: ActionId
    
    # Execution Context (immutable after creation)
    execution_context: Dict[str, Any] = field(default_factory=dict)
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    
    # Execution Status (mutable for tracking progress)
    status: ActionStatus = ActionStatus.PENDING
    
    # Timing Information (mutable for tracking progress)
    queued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_duration_ms: Optional[int] = None
    
    # Retry Handling (mutable for retry logic)
    attempt_number: int = 1
    is_retry: bool = False
    parent_execution_id: Optional[ExecutionId] = None
    
    # Error Handling (mutable for error tracking)
    error_message: Optional[str] = None
    error_details: Dict[str, Any] = field(default_factory=dict)
    error_stack_trace: Optional[str] = None
    
    # Queue Integration (mutable for queue tracking)
    queue_message_id: Optional[str] = None
    worker_id: Optional[str] = None
    
    # Performance Metrics (mutable for monitoring)
    memory_usage_mb: Optional[int] = None
    cpu_time_ms: Optional[int] = None
    
    # Audit Fields (auto-updated)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def create(
        cls,
        event_id: EventId,
        action_id: ActionId,
        input_data: Dict[str, Any],
        execution_context: Optional[Dict[str, Any]] = None,
        queue_message_id: Optional[str] = None,
        worker_id: Optional[str] = None
    ) -> 'ActionExecution':
        """
        Create a new ActionExecution for an event-action pair.
        
        Args:
            event_id: ID of the event that triggered this execution
            action_id: ID of the action being executed
            input_data: Input data for the action execution
            execution_context: Additional context for execution
            queue_message_id: Queue message ID if queued
            worker_id: ID of the worker processing this execution
            
        Returns:
            New ActionExecution instance
        """
        return cls(
            id=ExecutionId.generate(),
            event_id=event_id,
            action_id=action_id,
            input_data=input_data.copy() if input_data else {},
            execution_context=execution_context.copy() if execution_context else {},
            queue_message_id=queue_message_id,
            worker_id=worker_id
        )
    
    @classmethod
    def create_retry(
        cls,
        parent_execution: 'ActionExecution',
        attempt_number: int,
        worker_id: Optional[str] = None
    ) -> 'ActionExecution':
        """
        Create a retry execution from a failed execution.
        
        Args:
            parent_execution: The failed execution to retry
            attempt_number: The retry attempt number
            worker_id: ID of the worker processing this retry
            
        Returns:
            New ActionExecution instance for retry
        """
        return cls(
            id=ExecutionId.generate(),
            event_id=parent_execution.event_id,
            action_id=parent_execution.action_id,
            input_data=parent_execution.input_data.copy(),
            execution_context=parent_execution.execution_context.copy(),
            attempt_number=attempt_number,
            is_retry=True,
            parent_execution_id=parent_execution.id,
            worker_id=worker_id
        )
    
    def start_execution(self) -> None:
        """Mark execution as started."""
        if self.status != ActionStatus.PENDING:
            raise ValueError(f"Cannot start execution in status: {self.status}")
        
        self.status = ActionStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def complete_execution(self, output_data: Optional[Dict[str, Any]] = None) -> None:
        """Mark execution as completed successfully."""
        if self.status != ActionStatus.RUNNING:
            raise ValueError(f"Cannot complete execution not in running status: {self.status}")
        
        now = datetime.now(timezone.utc)
        self.status = ActionStatus.COMPLETED
        self.completed_at = now
        self.updated_at = now
        
        if output_data:
            self.output_data = output_data.copy()
        
        # Calculate execution duration
        if self.started_at:
            delta = now - self.started_at
            self.execution_duration_ms = int(delta.total_seconds() * 1000)
    
    def fail_execution(
        self, 
        error_message: str, 
        error_details: Optional[Dict[str, Any]] = None,
        error_stack_trace: Optional[str] = None
    ) -> None:
        """Mark execution as failed."""
        if self.status not in [ActionStatus.RUNNING, ActionStatus.PENDING]:
            raise ValueError(f"Cannot fail execution in status: {self.status}")
        
        now = datetime.now(timezone.utc)
        self.status = ActionStatus.FAILED
        self.completed_at = now
        self.updated_at = now
        self.error_message = error_message
        self.error_details = error_details.copy() if error_details else {}
        self.error_stack_trace = error_stack_trace
        
        # Calculate execution duration even for failures
        if self.started_at:
            delta = now - self.started_at
            self.execution_duration_ms = int(delta.total_seconds() * 1000)
    
    def timeout_execution(self) -> None:
        """Mark execution as timed out."""
        if self.status != ActionStatus.RUNNING:
            raise ValueError(f"Cannot timeout execution not in running status: {self.status}")
        
        now = datetime.now(timezone.utc)
        self.status = ActionStatus.TIMEOUT
        self.completed_at = now
        self.updated_at = now
        self.error_message = "Action execution timed out"
        
        # Calculate execution duration for timeout
        if self.started_at:
            delta = now - self.started_at
            self.execution_duration_ms = int(delta.total_seconds() * 1000)
    
    def cancel_execution(self) -> None:
        """Cancel execution."""
        if self.status in [ActionStatus.COMPLETED, ActionStatus.FAILED, ActionStatus.CANCELLED]:
            raise ValueError(f"Cannot cancel execution in status: {self.status}")
        
        now = datetime.now(timezone.utc)
        self.status = ActionStatus.CANCELLED
        self.updated_at = now
        
        # Set completed_at for cancelled executions
        if self.status == ActionStatus.RUNNING:
            self.completed_at = now
            if self.started_at:
                delta = now - self.started_at
                self.execution_duration_ms = int(delta.total_seconds() * 1000)
    
    def set_retry_status(self) -> None:
        """Mark execution as being retried."""
        if self.status != ActionStatus.FAILED:
            raise ValueError(f"Cannot retry execution not in failed status: {self.status}")
        
        self.status = ActionStatus.RETRYING
        self.updated_at = datetime.now(timezone.utc)
    
    def update_performance_metrics(self, memory_usage_mb: Optional[int] = None, cpu_time_ms: Optional[int] = None) -> None:
        """Update performance metrics."""
        if memory_usage_mb is not None:
            self.memory_usage_mb = memory_usage_mb
        if cpu_time_ms is not None:
            self.cpu_time_ms = cpu_time_ms
        self.updated_at = datetime.now(timezone.utc)
    
    def can_be_retried(self, retry_policy: Dict[str, Any]) -> bool:
        """Check if execution can be retried based on retry policy."""
        max_retries = retry_policy.get("max_retries", 3)
        return (
            self.status == ActionStatus.FAILED and 
            self.attempt_number <= max_retries
        )
    
    def get_total_duration_ms(self) -> Optional[int]:
        """Get total duration from queued to completed."""
        if self.completed_at:
            delta = self.completed_at - self.queued_at
            return int(delta.total_seconds() * 1000)
        return None
    
    def get_queue_wait_time_ms(self) -> Optional[int]:
        """Get time spent waiting in queue."""
        if self.started_at:
            delta = self.started_at - self.queued_at
            return int(delta.total_seconds() * 1000)
        return None
    
    def is_completed(self) -> bool:
        """Check if execution is in a final state."""
        return self.status in [
            ActionStatus.COMPLETED, 
            ActionStatus.FAILED, 
            ActionStatus.CANCELLED, 
            ActionStatus.TIMEOUT,
            ActionStatus.SKIPPED
        ]
    
    def is_successful(self) -> bool:
        """Check if execution completed successfully."""
        return self.status == ActionStatus.COMPLETED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert action execution to dictionary representation."""
        return {
            'id': str(self.id.value),
            'event_id': str(self.event_id.value),
            'action_id': str(self.action_id.value),
            'execution_context': self.execution_context,
            'input_data': self.input_data,
            'output_data': self.output_data,
            'status': self.status.value,
            'queued_at': self.queued_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'execution_duration_ms': self.execution_duration_ms,
            'total_duration_ms': self.get_total_duration_ms(),
            'queue_wait_time_ms': self.get_queue_wait_time_ms(),
            'attempt_number': self.attempt_number,
            'is_retry': self.is_retry,
            'parent_execution_id': str(self.parent_execution_id.value) if self.parent_execution_id else None,
            'error_message': self.error_message,
            'error_details': self.error_details,
            'error_stack_trace': self.error_stack_trace,
            'queue_message_id': self.queue_message_id,
            'worker_id': self.worker_id,
            'memory_usage_mb': self.memory_usage_mb,
            'cpu_time_ms': self.cpu_time_ms,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
    
    def __post_init__(self):
        """Validate action execution after initialization."""
        # Validate attempt number
        if self.attempt_number <= 0:
            raise ValueError(f"attempt_number must be positive: {self.attempt_number}")
        
        # Validate execution duration
        if self.execution_duration_ms is not None and self.execution_duration_ms < 0:
            raise ValueError(f"execution_duration_ms cannot be negative: {self.execution_duration_ms}")
        
        # Validate timing consistency
        if self.started_at and self.started_at < self.queued_at:
            raise ValueError("started_at cannot be before queued_at")
        
        if self.completed_at and self.started_at and self.completed_at < self.started_at:
            raise ValueError("completed_at cannot be before started_at")
    
    def __str__(self) -> str:
        return f"ActionExecution(id={self.id}, action_id={self.action_id}, status={self.status.value})"
    
    def __repr__(self) -> str:
        return (f"ActionExecution(id={self.id!r}, event_id={self.event_id!r}, "
                f"action_id={self.action_id!r}, status={self.status}, attempt={self.attempt_number})")