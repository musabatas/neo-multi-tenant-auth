"""Action failed domain event for platform events infrastructure.

This module defines the ActionFailed domain event that represents when
an action execution has failed in the platform infrastructure.

Following maximum separation architecture - this file contains ONLY ActionFailed.
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
class ActionFailed(DomainEvent):
    """Platform domain event representing when an action execution has failed.
    
    This is a platform infrastructure event that tracks when the event platform
    fails to execute an action, including error details and retry information.
    
    Event type: 'platform.action_failed'
    Aggregate: The action execution record
    """
    
    # Action failure information (must use field() since parent has default fields)
    action_id: ActionId = field(default=None)
    action_name: str = field(default="")  # Human-readable action name
    handler_type: str = field(default="")  # Type of handler (webhook, email, sms, etc.)
    failure_reason: str = field(default="")  # High-level reason for failure
    
    def __init__(self,
                 action_id: ActionId,
                 execution_id: ActionId,
                 action_name: str,
                 handler_type: str,
                 failure_reason: str,
                 execution_mode: str = "async",
                 original_event_id: Optional[EventId] = None,
                 original_event_type: Optional[str] = None,
                 error_message: Optional[str] = None,
                 error_code: Optional[str] = None,
                 execution_time_ms: Optional[int] = None,
                 retry_count: int = 0,
                 max_retries: int = 3,
                 will_retry: bool = False,
                 failure_category: str = "execution_error",
                 context_data: Optional[Dict[str, Any]] = None,
                 correlation_id: Optional[UUID] = None,
                 triggered_by_user_id: Optional[UserId] = None,
                 **kwargs):
        """Initialize ActionFailed domain event.
        
        Args:
            action_id: ID of the action configuration
            execution_id: ID of the specific execution instance  
            action_name: Human-readable name of the action
            handler_type: Type of handler that failed to execute the action
            failure_reason: High-level reason for the failure
            execution_mode: Mode of execution (sync, async, queued)
            original_event_id: ID of the original event that triggered this action
            original_event_type: Type of the original event
            error_message: Detailed error message from the failure
            error_code: Specific error code (if available)
            execution_time_ms: Time taken before failure in milliseconds
            retry_count: Current number of retries attempted
            max_retries: Maximum number of retries allowed
            will_retry: Whether this action will be retried
            failure_category: Category of failure (execution_error, configuration_error, timeout, etc.)
            context_data: Additional context data about the failure
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
            "failure_reason": failure_reason,
            "execution_mode": execution_mode,
            "retry_count": retry_count,
            "max_retries": max_retries,
            "will_retry": will_retry,
            "failure_category": failure_category,
        }
        
        # Add optional error details
        if original_event_id:
            event_data["original_event_id"] = str(original_event_id.value)
        if original_event_type:
            event_data["original_event_type"] = original_event_type
        if error_message:
            # Truncate error message to prevent large event data
            max_error_length = 2000
            truncated_error = error_message[:max_error_length]
            if len(error_message) > max_error_length:
                truncated_error += "... (truncated)"
            event_data["error_message"] = truncated_error
        if error_code:
            event_data["error_code"] = error_code
        if execution_time_ms is not None:
            event_data["execution_time_ms"] = execution_time_ms
        if context_data:
            event_data["context_data"] = context_data
        
        # Store additional fields
        self.action_id = action_id
        self.action_name = action_name
        self.handler_type = handler_type
        self.failure_reason = failure_reason
        
        # Initialize base domain event
        super().__init__(
            event_type=EventType("platform.action_failed"),
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
    def execution_mode(self) -> str:
        """Get the execution mode."""
        return self.event_data.get("execution_mode", "async")
    
    @property
    def error_message(self) -> Optional[str]:
        """Get the detailed error message."""
        return self.event_data.get("error_message")
    
    @property
    def error_code(self) -> Optional[str]:
        """Get the specific error code."""
        return self.event_data.get("error_code")
    
    @property
    def execution_time_ms(self) -> Optional[int]:
        """Get execution time before failure in milliseconds."""
        return self.event_data.get("execution_time_ms")
    
    @property
    def retry_count(self) -> int:
        """Get the current number of retries attempted."""
        return self.event_data.get("retry_count", 0)
    
    @property
    def max_retries(self) -> int:
        """Get the maximum number of retries allowed."""
        return self.event_data.get("max_retries", 3)
    
    @property
    def will_retry(self) -> bool:
        """Check if this action will be retried."""
        return self.event_data.get("will_retry", False)
    
    @property
    def failure_category(self) -> str:
        """Get the category of failure."""
        return self.event_data.get("failure_category", "execution_error")
    
    @property
    def context_data(self) -> Optional[Dict[str, Any]]:
        """Get additional context data about the failure."""
        return self.event_data.get("context_data")
    
    @property
    def original_event_id(self) -> Optional[EventId]:
        """Get the original event ID that triggered this action."""
        event_id_str = self.event_data.get("original_event_id")
        return EventId(UUID(event_id_str)) if event_id_str else None
    
    @property
    def original_event_type(self) -> Optional[str]:
        """Get the original event type that triggered this action."""
        return self.event_data.get("original_event_type")
    
    def is_retryable_failure(self) -> bool:
        """Check if this failure is retryable."""
        return self.will_retry and self.retry_count < self.max_retries
    
    def is_final_failure(self) -> bool:
        """Check if this is the final failure (no more retries)."""
        return not self.will_retry or self.retry_count >= self.max_retries
    
    def is_configuration_error(self) -> bool:
        """Check if this was a configuration error."""
        return self.failure_category == "configuration_error"
    
    def is_timeout_error(self) -> bool:
        """Check if this was a timeout error."""
        return self.failure_category == "timeout"
    
    def is_webhook_failure(self) -> bool:
        """Check if this was a webhook action failure."""
        return self.handler_type == "webhook"
    
    def is_email_failure(self) -> bool:
        """Check if this was an email action failure."""
        return self.handler_type == "email"
    
    @classmethod
    def create_for_execution(cls,
                           action_id: ActionId,
                           execution_id: ActionId,
                           action_name: str,
                           handler_type: str,
                           failure_reason: str,
                           execution_mode: str = "async",
                           original_event_id: Optional[EventId] = None,
                           original_event_type: Optional[str] = None,
                           error_message: Optional[str] = None,
                           error_code: Optional[str] = None,
                           execution_time_ms: Optional[int] = None,
                           retry_count: int = 0,
                           max_retries: int = 3,
                           will_retry: bool = False,
                           failure_category: str = "execution_error",
                           context_data: Optional[Dict[str, Any]] = None,
                           correlation_id: Optional[UUID] = None,
                           triggered_by_user_id: Optional[UserId] = None) -> 'ActionFailed':
        """Factory method to create ActionFailed for a specific execution failure.
        
        This factory ensures consistent creation of ActionFailed events
        with proper UUIDv7 compliance and platform metadata.
        """
        return cls(
            action_id=action_id,
            execution_id=execution_id,
            action_name=action_name,
            handler_type=handler_type,
            failure_reason=failure_reason,
            execution_mode=execution_mode,
            original_event_id=original_event_id,
            original_event_type=original_event_type,
            error_message=error_message,
            error_code=error_code,
            execution_time_ms=execution_time_ms,
            retry_count=retry_count,
            max_retries=max_retries,
            will_retry=will_retry,
            failure_category=failure_category,
            context_data=context_data,
            correlation_id=correlation_id or generate_uuid_v7(),
            triggered_by_user_id=triggered_by_user_id
        )