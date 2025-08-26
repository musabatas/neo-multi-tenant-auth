"""Action executed domain event for platform events infrastructure.

This module defines the ActionExecuted domain event that represents when
an action has been successfully executed by the platform infrastructure.

Following maximum separation architecture - this file contains ONLY ActionExecuted.
Pure platform infrastructure event - represents platform operation, not business logic.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from uuid import UUID

from ..entities.domain_event import DomainEvent
from ..value_objects import EventType, EventId, ActionId
from .....core.value_objects import UserId
from .....utils import generate_uuid_v7


@dataclass
class ActionExecuted(DomainEvent):
    """Platform domain event representing when an action has been successfully executed.
    
    This is a platform infrastructure event that tracks when the event platform
    successfully executes an action in response to a domain event.
    
    Event type: 'platform.action_executed'
    Aggregate: The action execution record
    """
    
    # Action execution information (must use field() since parent has default fields)
    action_id: ActionId = field(default=None)
    action_name: str = field(default="")  # Human-readable action name
    handler_type: str = field(default="")  # Type of handler (webhook, email, sms, etc.)
    execution_mode: str = field(default="async")  # How it was executed (sync, async, queued)
    
    def __init__(self,
                 action_id: ActionId,
                 execution_id: ActionId,
                 action_name: str,
                 handler_type: str,
                 execution_mode: str = "async",
                 original_event_id: Optional[EventId] = None,
                 original_event_type: Optional[str] = None,
                 execution_time_ms: Optional[int] = None,
                 success: bool = True,
                 result_data: Optional[Dict[str, Any]] = None,
                 correlation_id: Optional[UUID] = None,
                 triggered_by_user_id: Optional[UserId] = None,
                 **kwargs):
        """Initialize ActionExecuted domain event.
        
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
            correlation_id: Correlation ID for event tracing
            triggered_by_user_id: User who triggered the original event
            **kwargs: Additional DomainEvent fields
        """
        # Set platform event data
        event_data = {
            "action_id": str(action_id.value),
            "execution_id": str(execution_id.value),
            "action_name": action_name,
            "handler_type": handler_type,
            "execution_mode": execution_mode,
            "success": success,
        }
        
        # Add optional context data
        if original_event_id:
            event_data["original_event_id"] = str(original_event_id.value)
        if original_event_type:
            event_data["original_event_type"] = original_event_type
        if execution_time_ms is not None:
            event_data["execution_time_ms"] = execution_time_ms
        if result_data:
            event_data["result_data"] = result_data
        
        # Store additional fields
        self.action_id = action_id
        self.action_name = action_name
        self.handler_type = handler_type
        self.execution_mode = execution_mode
        
        # Initialize base domain event
        super().__init__(
            event_type=EventType("platform.action_executed"),
            aggregate_id=execution_id.value,  # Use execution ID as aggregate
            aggregate_type="action_execution",
            event_data=event_data,
            correlation_id=correlation_id,
            triggered_by_user_id=triggered_by_user_id,
            **kwargs
        )
    
    @property
    def execution_id(self) -> ActionId:
        """Get the execution ID from event data."""
        return ActionId(UUID(self.event_data["execution_id"]))
    
    @property
    def success(self) -> bool:
        """Check if the action execution was successful."""
        return self.event_data.get("success", False)
    
    @property
    def execution_time_ms(self) -> Optional[int]:
        """Get execution time in milliseconds."""
        return self.event_data.get("execution_time_ms")
    
    @property
    def result_data(self) -> Optional[Dict[str, Any]]:
        """Get result data from the action execution."""
        return self.event_data.get("result_data")
    
    @property
    def original_event_id(self) -> Optional[EventId]:
        """Get the original event ID that triggered this action."""
        event_id_str = self.event_data.get("original_event_id")
        return EventId(UUID(event_id_str)) if event_id_str else None
    
    @property
    def original_event_type(self) -> Optional[str]:
        """Get the original event type that triggered this action."""
        return self.event_data.get("original_event_type")
    
    def is_webhook_execution(self) -> bool:
        """Check if this was a webhook action execution."""
        return self.handler_type == "webhook"
    
    def is_email_execution(self) -> bool:
        """Check if this was an email action execution."""
        return self.handler_type == "email"
    
    def is_synchronous_execution(self) -> bool:
        """Check if this was a synchronous execution."""
        return self.execution_mode == "sync"
    
    @classmethod
    def create_for_execution(cls,
                           action_id: ActionId,
                           execution_id: ActionId,
                           action_name: str,
                           handler_type: str,
                           execution_mode: str = "async",
                           original_event_id: Optional[EventId] = None,
                           original_event_type: Optional[str] = None,
                           execution_time_ms: Optional[int] = None,
                           success: bool = True,
                           result_data: Optional[Dict[str, Any]] = None,
                           correlation_id: Optional[UUID] = None,
                           triggered_by_user_id: Optional[UserId] = None) -> 'ActionExecuted':
        """Factory method to create ActionExecuted for a specific execution.
        
        This factory ensures consistent creation of ActionExecuted events
        with proper UUIDv7 compliance and platform metadata.
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
            result_data=result_data,
            correlation_id=correlation_id or generate_uuid_v7(),
            triggered_by_user_id=triggered_by_user_id
        )