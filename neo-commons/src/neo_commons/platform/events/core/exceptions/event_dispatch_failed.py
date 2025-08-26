"""Event dispatch failure exception for platform events infrastructure.

This exception represents failures during event dispatching in the platform event system.
It inherits from core EventPublishingError for DRY compliance.
"""

from typing import Any, Dict, Optional

from .....core.exceptions import EventPublishingError
from ..value_objects import EventId


class EventDispatchFailed(EventPublishingError):
    """Raised when platform event dispatch fails.
    
    This exception represents failures in the platform event dispatching process,
    including dispatcher unavailability, routing failures, and validation errors.
    """
    
    def __init__(
        self,
        message: str,
        event_id: Optional[EventId] = None,
        event_type: Optional[str] = None,
        dispatcher: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize event dispatch failure exception.
        
        Args:
            message: Human-readable error message
            event_id: ID of the event that failed to dispatch
            event_type: Type of the event that failed
            dispatcher: Name of the dispatcher that failed
            error_code: Specific error code for the failure
            details: Additional details about the failure
        """
        # Build enhanced details
        enhanced_details = details or {}
        if event_id:
            enhanced_details["event_id"] = str(event_id)
        if event_type:
            enhanced_details["event_type"] = event_type
        if dispatcher:
            enhanced_details["dispatcher"] = dispatcher
            
        super().__init__(
            message=message,
            error_code=error_code or "EVENT_DISPATCH_FAILED",
            details=enhanced_details
        )
        
        # Store platform-specific fields
        self.event_id = event_id
        self.event_type = event_type
        self.dispatcher = dispatcher