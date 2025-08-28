"""Event handler failure exception for platform events infrastructure.

This exception represents failures during event handler processing in the platform event system.
It inherits from core EventProcessingError for DRY compliance.
"""

from typing import Any, Dict, Optional

from .....core.exceptions import EventHandlingError
from ..value_objects import EventId


class EventHandlerFailed(EventHandlingError):
    """Raised when platform event handler processing fails.
    
    This exception represents failures in event handler operations,
    including handler execution errors, processing failures, and state update issues.
    """
    
    def __init__(
        self,
        message: str,
        event_id: Optional[EventId] = None,
        handler_name: Optional[str] = None,
        action_id: Optional[str] = None,
        handler_type: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize event handler failure exception.
        
        Args:
            message: Human-readable error message
            event_id: ID of the event being handled
            handler_name: Name of the handler that failed
            action_id: ID of the action being processed (if applicable, matches database action_id field)
            handler_type: Type of handler that failed
            error_code: Specific error code for the failure
            details: Additional details about the handler failure
        """
        # Build enhanced details
        enhanced_details = details or {}
        if event_id:
            enhanced_details["event_id"] = str(event_id)
        if handler_name:
            enhanced_details["handler_name"] = handler_name
        if action_id:
            enhanced_details["action_id"] = action_id
        if handler_type:
            enhanced_details["handler_type"] = handler_type
            
        super().__init__(
            message=message,
            error_code=error_code or "EVENT_HANDLER_FAILED",
            details=enhanced_details
        )
        
        # Store platform-specific fields
        self.event_id = event_id
        self.handler_name = handler_name
        self.action_id = action_id
        self.handler_type = handler_type