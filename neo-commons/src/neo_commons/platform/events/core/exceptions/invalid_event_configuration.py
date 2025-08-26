"""Invalid event configuration exception for platform events infrastructure.

This exception represents configuration validation failures in the platform event system.
It inherits from core ValidationError for DRY compliance.
"""

from typing import Any, Dict, Optional

from .....core.exceptions import ValidationError
from ..value_objects import ActionId, EventId


class InvalidEventConfiguration(ValidationError):
    """Raised when platform event configuration is invalid.
    
    This exception represents failures in platform event configuration validation,
    including invalid action configurations, webhook settings, and condition validation.
    """
    
    def __init__(
        self,
        message: str,
        configuration_type: Optional[str] = None,
        action_id: Optional[ActionId] = None,
        event_id: Optional[EventId] = None,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        validation_rule: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize invalid event configuration exception.
        
        Args:
            message: Human-readable error message
            configuration_type: Type of configuration that's invalid (action, webhook, condition, etc.)
            action_id: ID of the action with invalid configuration
            event_id: ID of the event with invalid configuration
            field_name: Name of the field that failed validation
            field_value: Value that failed validation
            validation_rule: Description of the validation rule that failed
            error_code: Specific error code for the failure
            details: Additional details about the failure
        """
        # Build enhanced details
        enhanced_details = details or {}
        if configuration_type:
            enhanced_details["configuration_type"] = configuration_type
        if action_id:
            enhanced_details["action_id"] = str(action_id)
        if event_id:
            enhanced_details["event_id"] = str(event_id)
        if field_name:
            enhanced_details["field_name"] = field_name
        if field_value is not None:
            # Convert to string and truncate if necessary
            field_value_str = str(field_value)
            enhanced_details["field_value"] = field_value_str[:500] + "..." if len(field_value_str) > 500 else field_value_str
        if validation_rule:
            enhanced_details["validation_rule"] = validation_rule
            
        super().__init__(
            message=message,
            error_code=error_code or "INVALID_EVENT_CONFIGURATION",
            details=enhanced_details
        )
        
        # Store platform-specific fields
        self.configuration_type = configuration_type
        self.action_id = action_id
        self.event_id = event_id
        self.field_name = field_name
        self.field_value = field_value
        self.validation_rule = validation_rule