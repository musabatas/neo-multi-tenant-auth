"""Action executed domain event for platform actions infrastructure.

This module defines the ActionExecuted domain event that represents when
an action has been successfully executed by the platform infrastructure.

Following maximum separation architecture - this file contains ONLY ActionExecuted.
Pure platform infrastructure event - represents platform operation, not business logic.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime
from uuid import UUID

from ..value_objects import ActionId, ActionExecutionId
from .....core.value_objects import UserId
from .....utils import generate_uuid_v7, utc_now


@dataclass
class ActionExecuted:
    """Platform domain event representing when an action has been successfully executed.
    
    This is a platform infrastructure event that tracks when the action platform
    successfully executes an action in response to a trigger (event or direct execution).
    
    Event type: 'platform.action_executed'
    Aggregate: The action execution record
    """
    
    # Event identification
    id: UUID = field(default_factory=generate_uuid_v7)
    event_type: str = field(default="platform.action_executed")
    occurred_at: datetime = field(default_factory=utc_now)
    
    # Action execution information
    action_id: ActionId = field(default=None)
    execution_id: ActionExecutionId = field(default=None)
    action_name: str = field(default="")  # Human-readable action name
    handler_type: str = field(default="")  # Type of handler (webhook, email, sms, etc.)
    execution_mode: str = field(default="async")  # How it was executed (sync, async, queued)
    
    # Execution results
    success: bool = field(default=True)
    execution_time_ms: Optional[int] = field(default=None)
    result_data: Optional[Dict[str, Any]] = field(default=None)
    error_message: Optional[str] = field(default=None)
    
    # Context information
    original_event_id: Optional[str] = field(default=None)  # Generic event ID reference
    original_event_type: Optional[str] = field(default=None)
    correlation_id: Optional[UUID] = field(default=None)
    triggered_by_user_id: Optional[UserId] = field(default=None)
    
    def __post_init__(self):
        """Post-initialization validation."""
        if self.correlation_id is None:
            self.correlation_id = generate_uuid_v7()
        
        if self.result_data is None:
            self.result_data = {}
    
    @classmethod
    def create_for_execution(cls,
                           action_id: ActionId,
                           execution_id: ActionExecutionId,
                           action_name: str,
                           handler_type: str,
                           execution_mode: str = "async",
                           original_event_id: Optional[str] = None,
                           original_event_type: Optional[str] = None,
                           execution_time_ms: Optional[int] = None,
                           success: bool = True,
                           result_data: Optional[Dict[str, Any]] = None,
                           error_message: Optional[str] = None,
                           correlation_id: Optional[UUID] = None,
                           triggered_by_user_id: Optional[UserId] = None) -> 'ActionExecuted':
        """Factory method to create ActionExecuted for a specific execution.
        
        This factory ensures consistent creation of ActionExecuted events
        with proper UUIDv7 compliance and platform metadata.
        
        Args:
            action_id: ID of the action configuration
            execution_id: ID of the specific execution instance  
            action_name: Human-readable name of the action
            handler_type: Type of handler that executed the action
            execution_mode: Mode of execution (sync, async, queued)
            original_event_id: ID of the original event that triggered this action
            original_event_type: Type of the original event
            execution_time_ms: Time taken to execute the action in milliseconds
            success: Whether the action executed successfully
            result_data: Any result data from the action execution
            error_message: Error message if execution failed
            correlation_id: Correlation ID for event tracing
            triggered_by_user_id: User who triggered the original event
            
        Returns:
            ActionExecuted event instance
        """
        return cls(
            action_id=action_id,
            execution_id=execution_id,
            action_name=action_name,
            handler_type=handler_type,
            execution_mode=execution_mode,
            original_event_id=original_event_id,
            original_event_type=original_event_type,
            execution_time_ms=execution_time_ms,
            success=success,
            result_data=result_data or {},
            error_message=error_message,
            correlation_id=correlation_id or generate_uuid_v7(),
            triggered_by_user_id=triggered_by_user_id
        )
    
    def is_webhook_execution(self) -> bool:
        """Check if this was a webhook action execution."""
        return self.handler_type == "webhook"
    
    def is_email_execution(self) -> bool:
        """Check if this was an email action execution."""
        return self.handler_type == "email"
    
    def is_synchronous_execution(self) -> bool:
        """Check if this was a synchronous execution."""
        return self.execution_mode == "sync"
    
    def is_successful(self) -> bool:
        """Check if the action execution was successful."""
        return self.success
    
    def get_duration_seconds(self) -> Optional[float]:
        """Get execution duration in seconds."""
        if self.execution_time_ms is not None:
            return self.execution_time_ms / 1000.0
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "id": str(self.id),
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "action_id": str(self.action_id.value) if self.action_id else None,
            "execution_id": str(self.execution_id.value) if self.execution_id else None,
            "action_name": self.action_name,
            "handler_type": self.handler_type,
            "execution_mode": self.execution_mode,
            "success": self.success,
            "execution_time_ms": self.execution_time_ms,
            "result_data": self.result_data,
            "error_message": self.error_message,
            "original_event_id": self.original_event_id,
            "original_event_type": self.original_event_type,
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
            "triggered_by_user_id": str(self.triggered_by_user_id.value) if self.triggered_by_user_id else None,
        }