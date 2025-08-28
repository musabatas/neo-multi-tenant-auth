"""Invalid action configuration exception.

ONLY handles invalid action configuration exceptions following maximum separation architecture.
Single responsibility: Signal action configuration validation failures.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from .....core.exceptions import NeoCommonsError
from .....core.shared import RequestContext
from .....utils import utc_now


class InvalidActionConfiguration(NeoCommonsError):
    """
    Exception raised when action configuration is invalid.
    
    Indicates that action configuration does not meet requirements
    or contains invalid values that prevent action execution.
    """
    
    def __init__(
        self,
        message: str,
        action_id: Optional[str] = None,
        configuration_errors: Optional[Dict[str, str]] = None,
        handler_type: Optional[str] = None,
        context: Optional[RequestContext] = None,
        **kwargs
    ):
        """
        Initialize invalid action configuration exception.
        
        Args:
            message: Human-readable error message
            action_id: ID of the action with invalid configuration
            configuration_errors: Dictionary of field-specific errors
            handler_type: Type of handler that failed validation
            context: Request context when error occurred
            **kwargs: Additional context information
        """
        
        # Build enhanced error details
        enhanced_details = {
            "error_type": "invalid_action_configuration",
            "timestamp": utc_now().isoformat(),
            "configuration_errors": configuration_errors or {},
            **kwargs
        }
        
        if action_id:
            enhanced_details["action_id"] = action_id
            
        if handler_type:
            enhanced_details["handler_type"] = handler_type
            
        if context:
            enhanced_details["request_id"] = getattr(context, "request_id", None)
            enhanced_details["user_id"] = getattr(context, "user_id", None)
            enhanced_details["tenant_id"] = getattr(context, "tenant_id", None)
        
        super().__init__(
            message=message,
            error_code="INVALID_ACTION_CONFIGURATION",
            details=enhanced_details,
            context=context
        )
        
        # Store specific attributes
        self.action_id = action_id
        self.configuration_errors = configuration_errors or {}
        self.handler_type = handler_type
    
    @classmethod
    def for_missing_required_field(
        cls, 
        field_name: str, 
        handler_type: str, 
        action_id: Optional[str] = None
    ) -> "InvalidActionConfiguration":
        """
        Create exception for missing required configuration field.
        
        Args:
            field_name: Name of the missing field
            handler_type: Handler type requiring the field
            action_id: Action ID with missing field
            
        Returns:
            InvalidActionConfiguration instance
        """
        return cls(
            message=f"Required configuration field '{field_name}' is missing for {handler_type} handler",
            action_id=action_id,
            handler_type=handler_type,
            configuration_errors={field_name: "Field is required"}
        )
    
    @classmethod
    def for_invalid_field_value(
        cls,
        field_name: str,
        field_value: Any,
        expected_format: str,
        handler_type: str,
        action_id: Optional[str] = None
    ) -> "InvalidActionConfiguration":
        """
        Create exception for invalid field value.
        
        Args:
            field_name: Name of the invalid field
            field_value: The invalid value
            expected_format: Expected format description
            handler_type: Handler type with invalid field
            action_id: Action ID with invalid field
            
        Returns:
            InvalidActionConfiguration instance
        """
        return cls(
            message=f"Invalid value for '{field_name}' in {handler_type} handler: expected {expected_format}",
            action_id=action_id,
            handler_type=handler_type,
            configuration_errors={field_name: f"Expected {expected_format}, got {type(field_value).__name__}"},
            invalid_value=str(field_value)
        )
    
    @classmethod
    def for_unsupported_handler_type(
        cls,
        handler_type: str,
        supported_types: list,
        action_id: Optional[str] = None
    ) -> "InvalidActionConfiguration":
        """
        Create exception for unsupported handler type.
        
        Args:
            handler_type: The unsupported handler type
            supported_types: List of supported handler types
            action_id: Action ID with unsupported handler
            
        Returns:
            InvalidActionConfiguration instance
        """
        return cls(
            message=f"Unsupported handler type '{handler_type}'. Supported types: {', '.join(supported_types)}",
            action_id=action_id,
            handler_type=handler_type,
            supported_types=supported_types
        )