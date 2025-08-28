"""Action failed domain event for platform actions infrastructure.

This module defines the ActionFailed domain event that represents when
an action execution has failed in the platform infrastructure.

Following maximum separation architecture - this file contains ONLY ActionFailed.
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
class ActionFailed:
    """Platform domain event representing when an action execution has failed.
    
    This is a platform infrastructure event that tracks when the action platform
    fails to execute an action, including error details and retry information.
    
    Event type: 'platform.action_failed'
    Aggregate: The action execution record
    """
    
    # Event identification
    id: UUID = field(default_factory=generate_uuid_v7)
    event_type: str = field(default="platform.action_failed")
    occurred_at: datetime = field(default_factory=utc_now)
    
    # Action failure information
    action_id: ActionId = field(default=None)
    execution_id: ActionExecutionId = field(default=None)
    action_name: str = field(default="")  # Human-readable action name
    handler_type: str = field(default="")  # Type of handler (webhook, email, sms, etc.)
    execution_mode: str = field(default="async")  # How it was executed (sync, async, queued)
    failure_reason: str = field(default="")  # High-level reason for failure
    
    # Error details
    error_message: Optional[str] = field(default=None)
    error_code: Optional[str] = field(default=None)
    execution_time_ms: Optional[int] = field(default=None)
    failure_category: str = field(default="execution_error")  # execution_error, configuration_error, timeout, etc.
    
    # Retry information
    retry_count: int = field(default=0)
    max_retries: int = field(default=3)
    will_retry: bool = field(default=False)
    
    # Context information
    original_event_id: Optional[str] = field(default=None)  # Generic event ID reference
    original_event_type: Optional[str] = field(default=None)
    context_data: Optional[Dict[str, Any]] = field(default=None)
    correlation_id: Optional[UUID] = field(default=None)
    triggered_by_user_id: Optional[UserId] = field(default=None)
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        if self.correlation_id is None:
            self.correlation_id = generate_uuid_v7()
        
        if self.context_data is None:
            self.context_data = {}
        
        # Truncate error message to prevent large event data
        if self.error_message and len(self.error_message) > 2000:
            self.error_message = self.error_message[:2000] + "... (truncated)"
    
    @classmethod
    def create_for_execution(cls,
                           action_id: ActionId,
                           execution_id: ActionExecutionId,
                           action_name: str,
                           handler_type: str,
                           failure_reason: str,
                           execution_mode: str = "async",
                           original_event_id: Optional[str] = None,
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
            
        Returns:
            ActionFailed event instance
        """
        return cls(
            action_id=action_id,
            execution_id=execution_id,
            action_name=action_name,
            handler_type=handler_type,
            execution_mode=execution_mode,
            failure_reason=failure_reason,
            error_message=error_message,
            error_code=error_code,
            execution_time_ms=execution_time_ms,
            retry_count=retry_count,
            max_retries=max_retries,
            will_retry=will_retry,
            failure_category=failure_category,
            context_data=context_data or {},
            original_event_id=original_event_id,
            original_event_type=original_event_type,
            correlation_id=correlation_id or generate_uuid_v7(),
            triggered_by_user_id=triggered_by_user_id
        )
    
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
    
    def get_duration_seconds(self) -> Optional[float]:
        """Get execution duration before failure in seconds."""
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
            "failure_reason": self.failure_reason,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "execution_time_ms": self.execution_time_ms,
            "failure_category": self.failure_category,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "will_retry": self.will_retry,
            "original_event_id": self.original_event_id,
            "original_event_type": self.original_event_type,
            "context_data": self.context_data,
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
            "triggered_by_user_id": str(self.triggered_by_user_id.value) if self.triggered_by_user_id else None,
        }