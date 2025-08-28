"""Action validator for platform actions infrastructure.

This module handles ONLY action validation operations following maximum separation architecture.
Single responsibility: Validate actions for business rules, configuration integrity, and platform constraints.

Pure application layer - no infrastructure concerns.
Contains business validation logic that goes beyond basic entity validation.
"""

import re
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
from uuid import UUID

from ...core.entities import Action
from ...core.value_objects import (
    ActionId, ActionStatus, HandlerType, ActionPriority, 
    ExecutionMode, ActionCondition
)
from ...core.exceptions import ActionExecutionFailed
from neo_commons.core.value_objects import UserId
from neo_commons.utils import utc_now


@dataclass
class ActionValidationResult:
    """Result of action validation operation.
    
    Contains comprehensive validation feedback including all validation
    errors, warnings, and recommendations for action improvement.
    """
    is_valid: bool
    errors: List[str] = None
    warnings: List[str] = None
    recommendations: List[str] = None
    validation_summary: Optional[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.recommendations is None:
            self.recommendations = []


class ActionValidator:
    """Action validator for comprehensive action validation.
    
    Single responsibility: Validate actions against business rules,
    configuration constraints, and platform requirements. Provides detailed
    validation feedback for action creation and handler configuration.
    
    Following enterprise validation pattern with comprehensive rule checking.
    Pure application logic - delegates infrastructure concerns to protocols.
    """
    
    # Action name validation patterns
    VALID_ACTION_NAME_PATTERN = r'^[a-zA-Z0-9][a-zA-Z0-9\s\-_\.]*[a-zA-Z0-9]$'
    
    # Maximum sizes for validation
    MAX_ACTION_NAME_LENGTH = 255
    MAX_DESCRIPTION_LENGTH = 2000
    MAX_EVENT_TYPES_COUNT = 50
    MAX_CONDITIONS_COUNT = 20
    MAX_CONFIGURATION_SIZE_BYTES = 64 * 1024  # 64KB
    MAX_TAGS_SIZE_BYTES = 8 * 1024  # 8KB
    MAX_NESTED_DEPTH = 5
    
    # Valid event type patterns  
    VALID_EVENT_TYPE_PATTERN = r'^[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*$'
    
    # Timeout constraints (seconds)
    MIN_TIMEOUT_SECONDS = 1
    MAX_TIMEOUT_SECONDS = 3600  # 1 hour
    RECOMMENDED_MAX_TIMEOUT = 300  # 5 minutes
    
    # Retry constraints
    MAX_RETRY_COUNT = 10
    MAX_RETRY_DELAY = 300  # 5 minutes
    RECOMMENDED_MAX_RETRIES = 5
    
    # Reserved tag names
    RESERVED_TAG_NAMES = {
        'system', 'platform', 'internal', 'admin', 
        'tenant', 'created_by', 'created_at', 'updated_at'
    }
    
    # Common event categories for validation
    COMMON_EVENT_CATEGORIES = {
        'user', 'organization', 'team', 'project', 'order', 'payment',
        'subscription', 'notification', 'audit', 'system', 'security'
    }
    
    def __init__(self):
        """Initialize action validator with validation rules."""
        pass
    
    def validate_action(self, action: Action) -> ActionValidationResult:
        """Validate an action comprehensively.
        
        Performs complete action validation including:
        1. Basic field validation
        2. Action configuration validation
        3. Event type matching validation
        4. Condition validation
        5. Handler-specific validation
        6. Performance validation
        
        Args:
            action: Action to validate
            
        Returns:
            ActionValidationResult with comprehensive validation feedback
        """
        result = ActionValidationResult(is_valid=True)
        
        try:
            # 1. Basic field validation
            self._validate_basic_fields(action, result)
            
            # 2. Action configuration validation
            self._validate_action_configuration(action, result)
            
            # 3. Event type matching validation
            self._validate_event_types(action, result)
            
            # 4. Condition validation
            self._validate_conditions(action, result)
            
            # 5. Handler-specific validation
            self._validate_handler_configuration(action, result)
            
            # 6. Performance validation
            self._validate_performance_constraints(action, result)
            
            # Final validation status
            result.is_valid = len(result.errors) == 0
            
            # Generate summary
            result.validation_summary = self._generate_validation_summary(result)
            
            return result
            
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Action validation failed with exception: {str(e)}")
            result.validation_summary = "Action validation failed due to unexpected error"
            return result
    
    def validate_action_name(self, name: str) -> ActionValidationResult:
        """Validate action name format only.
        
        Convenience method for validating action name without
        requiring a full action. Useful for API validation.
        
        Args:
            name: Action name to validate
            
        Returns:
            ActionValidationResult with name validation feedback
        """
        result = ActionValidationResult(is_valid=True)
        
        if not name:
            result.errors.append("Action name cannot be empty")
            result.is_valid = False
            return result
        
        # Length validation
        if len(name) > self.MAX_ACTION_NAME_LENGTH:
            result.errors.append(f"Action name exceeds maximum length of {self.MAX_ACTION_NAME_LENGTH}")
            result.is_valid = False
        
        # Pattern validation
        if not re.match(self.VALID_ACTION_NAME_PATTERN, name):
            result.errors.append("Action name must start and end with alphanumeric characters and contain only letters, numbers, spaces, hyphens, underscores, and dots")
            result.is_valid = False
        
        # Business recommendations
        if len(name) < 3:
            result.recommendations.append("Action name should be at least 3 characters long for clarity")
        
        if name.upper() == name:
            result.recommendations.append("Consider using mixed case for better readability")
        
        return result
    
    def validate_handler_configuration(self, handler_type: HandlerType, configuration: Dict[str, Any]) -> ActionValidationResult:
        """Validate handler configuration only.
        
        Convenience method for validating handler configuration without
        requiring a full action. Useful for API validation.
        
        Args:
            handler_type: Type of handler
            configuration: Handler configuration to validate
            
        Returns:
            ActionValidationResult with configuration validation feedback
        """
        result = ActionValidationResult(is_valid=True)
        
        if configuration is None:
            configuration = {}
        
        # Validate based on handler type
        if handler_type == HandlerType.WEBHOOK:
            self._validate_webhook_configuration(configuration, result)
        elif handler_type == HandlerType.EMAIL:
            self._validate_email_configuration(configuration, result)
        elif handler_type == HandlerType.FUNCTION:
            self._validate_function_configuration(configuration, result)
        elif handler_type == HandlerType.WORKFLOW:
            self._validate_workflow_configuration(configuration, result)
        elif handler_type == HandlerType.SMS:
            self._validate_sms_configuration(configuration, result)
        elif handler_type == HandlerType.SLACK:
            self._validate_slack_configuration(configuration, result)
        elif handler_type == HandlerType.TEAMS:
            self._validate_teams_configuration(configuration, result)
        elif handler_type == HandlerType.CUSTOM:
            self._validate_custom_configuration(configuration, result)
        
        # Common configuration validation
        self._validate_configuration_structure(configuration, result, "handler_configuration")
        
        result.is_valid = len(result.errors) == 0
        return result
    
    def _validate_basic_fields(self, action: Action, result: ActionValidationResult) -> None:
        """Validate basic required fields of the action."""
        # Action ID validation
        if not action.id or not action.id.value:
            result.errors.append("Action ID is required")
        
        # Name validation
        name_validation = self.validate_action_name(action.name)
        result.errors.extend(name_validation.errors)
        result.warnings.extend(name_validation.warnings)
        result.recommendations.extend(name_validation.recommendations)
        
        # Description validation
        if action.description and len(action.description) > self.MAX_DESCRIPTION_LENGTH:
            result.errors.append(f"Action description exceeds maximum length of {self.MAX_DESCRIPTION_LENGTH}")
        
        # Status validation
        if not isinstance(action.status, ActionStatus):
            result.errors.append("Action status must be a valid ActionStatus")
        
        # Handler type validation
        if not isinstance(action.handler_type, HandlerType):
            result.errors.append("Handler type must be a valid HandlerType")
        
        # Priority validation
        if not isinstance(action.priority, ActionPriority):
            result.errors.append("Action priority must be a valid ActionPriority")
        
        # Execution mode validation
        if not isinstance(action.execution_mode, ExecutionMode):
            result.errors.append("Execution mode must be a valid ExecutionMode")
        
        # User validation
        if action.created_by_user_id and not action.created_by_user_id.value:
            result.errors.append("Created by user ID cannot be empty if provided")
        
        # Timestamp validation
        self._validate_timestamps(action, result)
    
    def _validate_action_configuration(self, action: Action, result: ActionValidationResult) -> None:
        """Validate action configuration and settings."""
        # Timeout validation
        if action.timeout_seconds < self.MIN_TIMEOUT_SECONDS:
            result.errors.append(f"Timeout must be at least {self.MIN_TIMEOUT_SECONDS} second(s)")
        elif action.timeout_seconds > self.MAX_TIMEOUT_SECONDS:
            result.errors.append(f"Timeout cannot exceed {self.MAX_TIMEOUT_SECONDS} seconds")
        elif action.timeout_seconds > self.RECOMMENDED_MAX_TIMEOUT:
            result.warnings.append(f"Timeout of {action.timeout_seconds}s is quite long. Consider using shorter timeouts for better responsiveness")
        
        # Retry validation
        if action.max_retries > self.MAX_RETRY_COUNT:
            result.errors.append(f"Max retries cannot exceed {self.MAX_RETRY_COUNT}")
        elif action.max_retries > self.RECOMMENDED_MAX_RETRIES:
            result.warnings.append(f"High retry count ({action.max_retries}) may cause delays. Consider using exponential backoff")
        
        # Retry delay validation
        if action.retry_delay_seconds > self.MAX_RETRY_DELAY:
            result.errors.append(f"Retry delay cannot exceed {self.MAX_RETRY_DELAY} seconds")
        
        # Tags validation
        if action.tags:
            self._validate_tags(action.tags, result)
        
        # Context filters validation
        if action.context_filters:
            self._validate_context_filters(action.context_filters, result)
    
    def _validate_event_types(self, action: Action, result: ActionValidationResult) -> None:
        """Validate event types configuration."""
        if not action.event_types:
            result.warnings.append("No event types specified - action can only be executed manually")
            return
        
        if len(action.event_types) > self.MAX_EVENT_TYPES_COUNT:
            result.errors.append(f"Too many event types ({len(action.event_types)}). Maximum allowed: {self.MAX_EVENT_TYPES_COUNT}")
        
        for event_type in action.event_types:
            if not event_type or not event_type.strip():
                result.errors.append("Event type cannot be empty")
                continue
            
            # Allow wildcards
            if event_type == "*" or event_type.endswith(".*"):
                result.warnings.append(f"Wildcard event type '{event_type}' will match many events. Consider being more specific")
                continue
            
            # Validate event type format
            if not re.match(self.VALID_EVENT_TYPE_PATTERN, event_type):
                result.errors.append(f"Invalid event type format: '{event_type}'. Expected format: 'category.action'")
                continue
            
            # Extract category for recommendations
            category = event_type.split('.')[0]
            if category not in self.COMMON_EVENT_CATEGORIES:
                result.recommendations.append(f"Consider using a standard event category. Common categories: {', '.join(sorted(self.COMMON_EVENT_CATEGORIES))}")
    
    def _validate_conditions(self, action: Action, result: ActionValidationResult) -> None:
        """Validate action conditions."""
        if len(action.conditions) > self.MAX_CONDITIONS_COUNT:
            result.errors.append(f"Too many conditions ({len(action.conditions)}). Maximum allowed: {self.MAX_CONDITIONS_COUNT}")
        
        for i, condition in enumerate(action.conditions):
            if not isinstance(condition, ActionCondition):
                result.errors.append(f"Condition {i+1} must be a valid ActionCondition")
                continue
            
            # Validate condition fields
            if not condition.field:
                result.errors.append(f"Condition {i+1}: field cannot be empty")
            
            if not condition.operator:
                result.errors.append(f"Condition {i+1}: operator cannot be empty")
            
            # Check for potentially expensive conditions
            if condition.field.count('.') > 3:
                result.warnings.append(f"Condition {i+1}: deeply nested field '{condition.field}' may impact performance")
            
            # Check for overly broad conditions
            if condition.operator == "exists" and not condition.field.startswith(('data.', 'metadata.', 'context.')):
                result.warnings.append(f"Condition {i+1}: existence check on top-level field may match too many events")
    
    def _validate_handler_configuration(self, action: Action, result: ActionValidationResult) -> None:
        """Validate handler-specific configuration."""
        config_validation = self.validate_handler_configuration(action.handler_type, action.configuration)
        result.errors.extend(config_validation.errors)
        result.warnings.extend(config_validation.warnings)
        result.recommendations.extend(config_validation.recommendations)
    
    def _validate_performance_constraints(self, action: Action, result: ActionValidationResult) -> None:
        """Validate performance-related constraints."""
        # Check configuration size
        config_size = self._calculate_data_size(action.configuration)
        if config_size > self.MAX_CONFIGURATION_SIZE_BYTES:
            result.errors.append(f"Configuration size ({config_size} bytes) exceeds maximum ({self.MAX_CONFIGURATION_SIZE_BYTES} bytes)")
        elif config_size > self.MAX_CONFIGURATION_SIZE_BYTES // 2:
            result.warnings.append(f"Large configuration ({config_size} bytes) may impact performance")
        
        # Check tags size
        tags_size = self._calculate_data_size(action.tags)
        if tags_size > self.MAX_TAGS_SIZE_BYTES:
            result.errors.append(f"Tags size ({tags_size} bytes) exceeds maximum ({self.MAX_TAGS_SIZE_BYTES} bytes)")
        
        # Check nesting depth
        config_depth = self._get_max_depth(action.configuration)
        if config_depth > self.MAX_NESTED_DEPTH:
            result.errors.append(f"Configuration nesting depth ({config_depth}) exceeds maximum ({self.MAX_NESTED_DEPTH})")
        
        # Performance recommendations based on handler type and configuration
        if action.handler_type == HandlerType.WEBHOOK:
            if action.execution_mode == ExecutionMode.SYNC:
                result.warnings.append("Synchronous webhook execution may cause delays. Consider using async mode")
        
        if action.handler_type == HandlerType.EMAIL and action.priority == ActionPriority.HIGH:
            result.recommendations.append("High priority email actions may cause delivery delays during peak times")
    
    def _validate_webhook_configuration(self, config: Dict[str, Any], result: ActionValidationResult) -> None:
        """Validate webhook handler configuration."""
        if not config.get("url"):
            result.errors.append("Webhook handler requires 'url' in configuration")
            return
        
        url = config["url"]
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            result.errors.append("Webhook URL must be a valid HTTP/HTTPS URL")
        
        # Security recommendations
        if url.startswith("http://"):
            result.warnings.append("HTTP URLs are not secure. Consider using HTTPS")
        
        # Method validation
        method = config.get("method", "POST")
        if method not in ["GET", "POST", "PUT", "PATCH"]:
            result.errors.append(f"Invalid HTTP method: {method}")
        
        # Headers validation
        headers = config.get("headers", {})
        if not isinstance(headers, dict):
            result.errors.append("Headers must be a dictionary")
        else:
            for key, value in headers.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    result.errors.append("Header keys and values must be strings")
        
        # Timeout validation (if specified in config)
        if "timeout" in config:
            timeout = config["timeout"]
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                result.errors.append("Webhook timeout must be a positive number")
    
    def _validate_email_configuration(self, config: Dict[str, Any], result: ActionValidationResult) -> None:
        """Validate email handler configuration."""
        if not config.get("to"):
            result.errors.append("Email handler requires 'to' address in configuration")
        
        if not config.get("template"):
            result.errors.append("Email handler requires 'template' in configuration")
        
        # Email validation
        to_email = config.get("to")
        if to_email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', str(to_email)):
            result.errors.append("Invalid email address format")
        
        # Optional fields validation
        if "cc" in config:
            cc_emails = config["cc"]
            if isinstance(cc_emails, list):
                for email in cc_emails:
                    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', str(email)):
                        result.errors.append(f"Invalid CC email address: {email}")
    
    def _validate_function_configuration(self, config: Dict[str, Any], result: ActionValidationResult) -> None:
        """Validate function handler configuration."""
        if not config.get("module"):
            result.errors.append("Function handler requires 'module' in configuration")
        
        if not config.get("function"):
            result.errors.append("Function handler requires 'function' name in configuration")
        
        # Module name validation
        module = config.get("module")
        if module and not re.match(r'^[a-zA-Z_][a-zA-Z0-9_.]*$', str(module)):
            result.errors.append("Invalid module name format")
        
        # Function name validation
        function = config.get("function")
        if function and not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', str(function)):
            result.errors.append("Invalid function name format")
    
    def _validate_workflow_configuration(self, config: Dict[str, Any], result: ActionValidationResult) -> None:
        """Validate workflow handler configuration."""
        if not config.get("steps"):
            result.errors.append("Workflow handler requires 'steps' in configuration")
            return
        
        steps = config["steps"]
        if not isinstance(steps, list) or len(steps) == 0:
            result.errors.append("Workflow steps must be a non-empty list")
            return
        
        if len(steps) > 20:
            result.warnings.append(f"Workflow has many steps ({len(steps)}). Consider breaking into smaller workflows")
        
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                result.errors.append(f"Workflow step {i+1} must be a dictionary")
                continue
            
            if not step.get("type"):
                result.errors.append(f"Workflow step {i+1} requires 'type' field")
            
            if not step.get("name"):
                result.errors.append(f"Workflow step {i+1} requires 'name' field")
    
    def _validate_sms_configuration(self, config: Dict[str, Any], result: ActionValidationResult) -> None:
        """Validate SMS handler configuration."""
        if not config.get("to"):
            result.errors.append("SMS handler requires 'to' phone number in configuration")
        
        if not config.get("message"):
            result.errors.append("SMS handler requires 'message' template in configuration")
        
        # Phone number validation (basic)
        phone = config.get("to")
        if phone and not re.match(r'^\+?[1-9]\d{1,14}$', str(phone)):
            result.warnings.append("Phone number format may be invalid. Use E.164 format (+1234567890)")
    
    def _validate_slack_configuration(self, config: Dict[str, Any], result: ActionValidationResult) -> None:
        """Validate Slack handler configuration."""
        if not config.get("webhook_url") and not config.get("channel"):
            result.errors.append("Slack handler requires either 'webhook_url' or 'channel' in configuration")
        
        # Webhook URL validation
        webhook_url = config.get("webhook_url")
        if webhook_url and not webhook_url.startswith("https://hooks.slack.com/"):
            result.warnings.append("Slack webhook URL should use the official Slack webhook format")
    
    def _validate_teams_configuration(self, config: Dict[str, Any], result: ActionValidationResult) -> None:
        """Validate Microsoft Teams handler configuration."""
        if not config.get("webhook_url"):
            result.errors.append("Teams handler requires 'webhook_url' in configuration")
        
        # Teams webhook URL validation
        webhook_url = config.get("webhook_url")
        if webhook_url and "office.com" not in webhook_url:
            result.warnings.append("Teams webhook URL should use the official Microsoft Teams webhook format")
    
    def _validate_custom_configuration(self, config: Dict[str, Any], result: ActionValidationResult) -> None:
        """Validate custom handler configuration."""
        if not config.get("handler_class"):
            result.errors.append("Custom handler requires 'handler_class' in configuration")
        
        # Handler class validation
        handler_class = config.get("handler_class")
        if handler_class and not re.match(r'^[a-zA-Z_][a-zA-Z0-9_.]*$', str(handler_class)):
            result.errors.append("Invalid handler class name format")
    
    def _validate_timestamps(self, action: Action, result: ActionValidationResult) -> None:
        """Validate action timestamps."""
        now = utc_now()
        
        # Created at validation
        if not action.created_at:
            result.errors.append("Created at timestamp is required")
        
        # Updated at validation
        if not action.updated_at:
            result.errors.append("Updated at timestamp is required")
        else:
            # Check timestamp order
            if action.created_at and action.updated_at < action.created_at:
                result.errors.append("Updated at must be after or equal to created at")
        
        # Last triggered validation
        if action.last_triggered_at:
            if action.created_at and action.last_triggered_at < action.created_at:
                result.errors.append("Last triggered at cannot be before created at")
    
    def _validate_tags(self, tags: Dict[str, str], result: ActionValidationResult) -> None:
        """Validate action tags."""
        if not isinstance(tags, dict):
            result.errors.append("Tags must be a dictionary")
            return
        
        for key, value in tags.items():
            if not isinstance(key, str) or not isinstance(value, str):
                result.errors.append("Tag keys and values must be strings")
                continue
            
            if key.lower() in self.RESERVED_TAG_NAMES:
                result.errors.append(f"Tag name '{key}' is reserved")
            
            if len(key) > 50:
                result.errors.append(f"Tag key '{key}' is too long (max 50 characters)")
            
            if len(value) > 255:
                result.errors.append(f"Tag value for '{key}' is too long (max 255 characters)")
    
    def _validate_context_filters(self, filters: Dict[str, Any], result: ActionValidationResult) -> None:
        """Validate context filters."""
        if not isinstance(filters, dict):
            result.errors.append("Context filters must be a dictionary")
            return
        
        for key, value in filters.items():
            if not key:
                result.errors.append("Context filter key cannot be empty")
            
            # Check for potentially expensive filters
            if key.count('.') > 2:
                result.warnings.append(f"Deeply nested context filter '{key}' may impact performance")
    
    def _validate_configuration_structure(self, config: Dict[str, Any], result: ActionValidationResult, field_name: str) -> None:
        """Validate configuration structure for JSON compatibility."""
        if not isinstance(config, dict):
            return
        
        try:
            # Test JSON serialization
            json.dumps(config, default=str)
        except (TypeError, ValueError) as e:
            result.errors.append(f"{field_name} is not JSON serializable: {str(e)}")
        
        # Check for circular references
        if self._has_circular_reference(config):
            result.errors.append(f"{field_name} contains circular references")
    
    def _calculate_data_size(self, data: Any) -> int:
        """Calculate approximate size of data in bytes."""
        try:
            return len(json.dumps(data, default=str, separators=(',', ':')).encode('utf-8'))
        except:
            return 0
    
    def _get_max_depth(self, obj: Any, current_depth: int = 0) -> int:
        """Get maximum nesting depth of an object."""
        if current_depth > self.MAX_NESTED_DEPTH:
            return current_depth
        
        if isinstance(obj, dict):
            if not obj:
                return current_depth
            return max(self._get_max_depth(v, current_depth + 1) for v in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return current_depth
            return max(self._get_max_depth(item, current_depth + 1) for item in obj)
        else:
            return current_depth
    
    def _has_circular_reference(self, obj: Any, seen: Optional[Set] = None) -> bool:
        """Check for circular references in nested data structures."""
        if seen is None:
            seen = set()
        
        obj_id = id(obj)
        if obj_id in seen:
            return True
        
        if isinstance(obj, (dict, list)):
            seen.add(obj_id)
            try:
                if isinstance(obj, dict):
                    for value in obj.values():
                        if self._has_circular_reference(value, seen):
                            return True
                elif isinstance(obj, list):
                    for item in obj:
                        if self._has_circular_reference(item, seen):
                            return True
            finally:
                seen.remove(obj_id)
        
        return False
    
    def _generate_validation_summary(self, result: ActionValidationResult) -> str:
        """Generate a human-readable validation summary."""
        if result.is_valid:
            summary_parts = ["Action is valid"]
            
            if result.warnings:
                summary_parts.append(f"with {len(result.warnings)} warning(s)")
            
            if result.recommendations:
                summary_parts.append(f"and {len(result.recommendations)} recommendation(s)")
            
            return " ".join(summary_parts) + "."
        else:
            return f"Action validation failed with {len(result.errors)} error(s)."