"""Action execution failure exception for platform actions infrastructure.

This exception represents failures during action execution in the platform action system.
It inherits from core EventHandlingError for DRY compliance.
"""

from typing import Any, Dict, Optional

from .....core.exceptions import EventHandlingError
from ..value_objects import ActionId


class ActionExecutionFailed(EventHandlingError):
    """Raised when platform action execution fails.
    
    This exception represents failures in the platform action execution process,
    including handler failures, timeout errors, and configuration issues.
    """
    
    def __init__(
        self,
        message: str,
        action_id: Optional[ActionId] = None,
        event_id: Optional[str] = None,
        action_name: Optional[str] = None,
        handler_type: Optional[str] = None,
        execution_mode: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        """Initialize action execution failure exception.
        
        Args:
            message: Human-readable error message
            action_id: ID of the action that failed to execute
            event_id: ID of the event that triggered the action (optional)
            action_name: Name of the action that failed
            handler_type: Type of handler that failed (webhook, email, sms, etc.)
            execution_mode: Mode of execution (sync, async, queued)
            error_code: Specific error code for the failure
            details: Additional details about the failure
            original_error: Original exception that caused this failure
        """
        # Build enhanced details
        enhanced_details = details or {}
        if action_id:
            enhanced_details["action_id"] = str(action_id)
        if event_id:
            enhanced_details["event_id"] = event_id
        if action_name:
            enhanced_details["action_name"] = action_name
        if handler_type:
            enhanced_details["handler_type"] = handler_type
        if execution_mode:
            enhanced_details["execution_mode"] = execution_mode
        if original_error:
            enhanced_details["original_error"] = str(original_error)
            enhanced_details["original_error_type"] = type(original_error).__name__
            
        super().__init__(
            message=message,
            error_code=error_code or "ACTION_EXECUTION_FAILED",
            details=enhanced_details
        )
        
        # Store platform-specific fields
        self.action_id = action_id
        self.event_id = event_id
        self.action_name = action_name
        self.handler_type = handler_type
        self.execution_mode = execution_mode
        self.original_error = original_error