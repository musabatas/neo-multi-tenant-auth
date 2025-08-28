"""Event validation failure exception for platform events infrastructure.

This exception represents failures during event validation in the platform event system.
It inherits from core ValidationError for DRY compliance.
"""

from typing import Any, Dict, Optional

from .....core.exceptions import ValidationError
from ..value_objects import EventId


class EventValidationFailed(ValidationError):
    """Raised when platform event validation fails.
    
    This exception represents failures in event validation processes,
    including schema validation, payload validation, and condition validation.
    """
    
    def __init__(
        self,
        message: str,
        event_id: Optional[EventId] = None,
        event_type: Optional[str] = None,
        field_name: Optional[str] = None,
        validation_type: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize event validation failure exception.
        
        Args:
            message: Human-readable error message
            event_id: ID of the event that failed validation
            event_type: Type of the event that failed
            field_name: Name of the field that failed validation
            validation_type: Type of validation that failed (schema, payload, condition)
            error_code: Specific error code for the failure
            details: Additional details about the validation failure
        """
        # Build enhanced details
        enhanced_details = details or {}
        if event_id:
            enhanced_details["event_id"] = str(event_id)
        if event_type:
            enhanced_details["event_type"] = event_type
        if field_name:
            enhanced_details["field_name"] = field_name
        if validation_type:
            enhanced_details["validation_type"] = validation_type
            
        super().__init__(
            message=message,
            error_code=error_code or "EVENT_VALIDATION_FAILED",
            details=enhanced_details
        )
        
        # Store platform-specific fields
        self.event_id = event_id
        self.event_type = event_type
        self.field_name = field_name
        self.validation_type = validation_type