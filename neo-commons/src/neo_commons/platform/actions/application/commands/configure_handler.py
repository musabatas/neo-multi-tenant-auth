"""Configure handler command for platform events infrastructure.

This module handles ONLY handler configuration operations following maximum separation architecture.
Single responsibility: Configure and update action handlers in the platform system.

Pure application layer - no infrastructure concerns.
Uses protocols for dependency injection and clean architecture compliance.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

from ...core.protocols import ActionRepository
from ...core.entities import Action
from ...core.value_objects import ActionId, HandlerType, ActionPriority, ExecutionMode
from ...core.exceptions import InvalidActionConfiguration
from .....core.value_objects import UserId
from .....utils import utc_now


@dataclass
class ConfigureHandlerData:
    """Data required to configure an action handler.
    
    Contains all the configuration needed to update handler settings.
    Separates data from business logic following CQRS patterns.
    """
    action_id: ActionId
    
    # Handler configuration
    handler_type: Optional[HandlerType] = None
    configuration: Dict[str, Any] = field(default_factory=dict)
    
    # Execution settings
    execution_mode: Optional[ExecutionMode] = None
    priority: Optional[ActionPriority] = None
    timeout_seconds: Optional[int] = None
    max_retries: Optional[int] = None
    retry_delay_seconds: Optional[int] = None
    
    # Handler-specific settings
    custom_headers: Dict[str, Any] = field(default_factory=dict)
    authentication: Dict[str, Any] = field(default_factory=dict)
    
    # Context and metadata
    updated_by_user_id: Optional[UserId] = None
    configuration_notes: Optional[str] = None
    
    def __post_init__(self):
        """Validate data after initialization."""
        # Set defaults for mutable fields
        if self.configuration is None:
            self.configuration = {}
        if self.custom_headers is None:
            self.custom_headers = {}
        if self.authentication is None:
            self.authentication = {}


@dataclass
class ConfigureHandlerResult:
    """Result of handler configuration operation.
    
    Contains the updated action and operation metadata.
    Provides clear feedback about the configuration operation.
    """
    action: Action
    action_id: ActionId
    updated_at: datetime
    changes_applied: List[str]
    success: bool = True
    message: str = "Handler configuration updated successfully"


class ConfigureHandlerCommand:
    """Command to configure action handlers.
    
    Handles action handler configuration with proper validation,
    configuration merging, and handler-specific logic.
    
    Single responsibility: ONLY handler configuration logic.
    Uses dependency injection through protocols for clean architecture.
    """
    
    def __init__(self, repository: ActionRepository):
        """Initialize command with required dependencies.
        
        Args:
            repository: Action repository for action persistence
        """
        self._repository = repository
    
    async def execute(self, data: ConfigureHandlerData) -> ConfigureHandlerResult:
        """Execute handler configuration command.
        
        Retrieves the existing action, applies configuration updates,
        validates the new configuration, and persists changes.
        
        Args:
            data: Handler configuration data containing updates
            
        Returns:
            ConfigureHandlerResult with updated action and metadata
            
        Raises:
            InvalidActionConfiguration: If handler configuration is invalid
            ValueError: If action not found or configuration invalid
        """
        try:
            # Get existing action
            existing_action = await self._repository.get_action_by_id(data.action_id)
            if not existing_action:
                raise ValueError(f"Action not found: {data.action_id}")
            
            # Validate configuration data
            self._validate_configuration_data(data, existing_action)
            
            # Apply configuration updates
            updated_action, changes = self._apply_configuration_updates(existing_action, data)
            
            # Validate the updated configuration
            self._validate_updated_configuration(updated_action)
            
            # Update the action in repository
            final_action = await self._repository.update_action(
                data.action_id,
                self._build_update_dict(updated_action),
                transaction_context={"updated_by": data.updated_by_user_id}
            )
            
            # Create result
            result = ConfigureHandlerResult(
                action=final_action,
                action_id=final_action.id,
                updated_at=final_action.updated_at,
                changes_applied=changes,
                success=True,
                message=f"Handler configuration updated for action '{final_action.name}'"
            )
            
            return result
            
        except ValueError as e:
            raise InvalidActionConfiguration(f"Invalid handler configuration: {str(e)}")
        except Exception as e:
            raise InvalidActionConfiguration(f"Failed to configure handler: {str(e)}")
    
    def _validate_configuration_data(self, data: ConfigureHandlerData, existing_action: Action) -> None:
        """Validate handler configuration data.
        
        Performs business logic validation before applying updates.
        
        Args:
            data: Handler configuration data to validate
            existing_action: Current action configuration
            
        Raises:
            ValueError: If validation fails
        """
        # Validate timeout if provided
        if data.timeout_seconds is not None:
            if not (5 <= data.timeout_seconds <= 300):
                raise ValueError(f"Invalid timeout: {data.timeout_seconds}. Must be between 5 and 300 seconds")
        
        # Validate retry configuration if provided
        if data.max_retries is not None:
            if not (0 <= data.max_retries <= 10):
                raise ValueError(f"Invalid max retries: {data.max_retries}. Must be between 0 and 10")
        
        if data.retry_delay_seconds is not None:
            if not (1 <= data.retry_delay_seconds <= 3600):
                raise ValueError(f"Invalid retry delay: {data.retry_delay_seconds}. Must be between 1 and 3600 seconds")
        
        # Validate handler type specific configuration
        handler_type = data.handler_type or existing_action.handler_type
        if handler_type == HandlerType.WEBHOOK:
            self._validate_webhook_configuration(data.configuration, existing_action.configuration)
        elif handler_type == HandlerType.EMAIL:
            self._validate_email_configuration(data.configuration, existing_action.configuration)
        elif handler_type == HandlerType.FUNCTION:
            self._validate_function_configuration(data.configuration, existing_action.configuration)
        elif handler_type == HandlerType.WORKFLOW:
            self._validate_workflow_configuration(data.configuration, existing_action.configuration)
    
    def _validate_webhook_configuration(self, new_config: Dict[str, Any], existing_config: Dict[str, Any]) -> None:
        """Validate webhook-specific configuration."""
        # Merge configurations to get complete picture
        merged_config = {**existing_config, **new_config}
        
        if "url" in new_config:
            url = new_config["url"]
            if not url or not isinstance(url, str):
                raise ValueError("Webhook handler requires valid 'url' in configuration")
            if not (url.startswith("http://") or url.startswith("https://")):
                raise ValueError("Webhook URL must start with http:// or https://")
        
        # Validate optional webhook settings
        if "method" in new_config and new_config["method"] not in {"POST", "PUT", "PATCH"}:
            raise ValueError("Webhook method must be POST, PUT, or PATCH")
    
    def _validate_email_configuration(self, new_config: Dict[str, Any], existing_config: Dict[str, Any]) -> None:
        """Validate email-specific configuration."""
        merged_config = {**existing_config, **new_config}
        
        if "to" in new_config:
            to_addresses = new_config["to"]
            if not to_addresses:
                raise ValueError("Email handler requires 'to' addresses in configuration")
            if isinstance(to_addresses, str):
                to_addresses = [to_addresses]
            for addr in to_addresses:
                if not isinstance(addr, str) or "@" not in addr:
                    raise ValueError(f"Invalid email address: {addr}")
        
        if "template" in new_config:
            if not new_config["template"] or not isinstance(new_config["template"], str):
                raise ValueError("Email handler requires valid 'template' in configuration")
    
    def _validate_function_configuration(self, new_config: Dict[str, Any], existing_config: Dict[str, Any]) -> None:
        """Validate function-specific configuration."""
        merged_config = {**existing_config, **new_config}
        
        if "module" in new_config:
            if not new_config["module"] or not isinstance(new_config["module"], str):
                raise ValueError("Function handler requires valid 'module' in configuration")
        
        if "function" in new_config:
            if not new_config["function"] or not isinstance(new_config["function"], str):
                raise ValueError("Function handler requires valid 'function' name in configuration")
    
    def _validate_workflow_configuration(self, new_config: Dict[str, Any], existing_config: Dict[str, Any]) -> None:
        """Validate workflow-specific configuration."""
        merged_config = {**existing_config, **new_config}
        
        if "steps" in new_config:
            steps = new_config["steps"]
            if not steps or not isinstance(steps, list):
                raise ValueError("Workflow handler requires 'steps' list in configuration")
            for i, step in enumerate(steps):
                if not isinstance(step, dict) or "action" not in step:
                    raise ValueError(f"Workflow step {i} must have 'action' field")
    
    def _apply_configuration_updates(self, action: Action, data: ConfigureHandlerData) -> tuple[Action, List[str]]:
        """Apply configuration updates to the action.
        
        Args:
            action: Current action to update
            data: Configuration data to apply
            
        Returns:
            Tuple of (updated_action, list_of_changes)
        """
        changes = []
        
        # Create updated action (copy existing action and apply changes)
        updated_action = Action(
            id=action.id,
            name=action.name,
            description=action.description,
            handler_type=data.handler_type or action.handler_type,
            configuration={**action.configuration, **data.configuration},
            event_types=action.event_types.copy(),
            conditions=action.conditions.copy(),
            context_filters=action.context_filters.copy(),
            execution_mode=data.execution_mode or action.execution_mode,
            priority=data.priority or action.priority,
            timeout_seconds=data.timeout_seconds or action.timeout_seconds,
            max_retries=data.max_retries or action.max_retries,
            retry_delay_seconds=data.retry_delay_seconds or action.retry_delay_seconds,
            status=action.status,
            is_enabled=action.is_enabled,
            tags=action.tags.copy(),
            created_by_user_id=action.created_by_user_id,
            tenant_id=action.tenant_id,
            created_at=action.created_at,
            updated_at=utc_now(),
            last_triggered_at=action.last_triggered_at
        )
        
        # Track changes
        if data.handler_type and data.handler_type != action.handler_type:
            changes.append(f"handler_type: {action.handler_type.value} → {data.handler_type.value}")
        
        if data.configuration:
            changes.append(f"configuration: updated {len(data.configuration)} settings")
        
        if data.execution_mode and data.execution_mode != action.execution_mode:
            changes.append(f"execution_mode: {action.execution_mode.value} → {data.execution_mode.value}")
        
        if data.priority and data.priority != action.priority:
            changes.append(f"priority: {action.priority.value} → {data.priority.value}")
        
        if data.timeout_seconds and data.timeout_seconds != action.timeout_seconds:
            changes.append(f"timeout_seconds: {action.timeout_seconds} → {data.timeout_seconds}")
        
        if data.max_retries is not None and data.max_retries != action.max_retries:
            changes.append(f"max_retries: {action.max_retries} → {data.max_retries}")
        
        if data.retry_delay_seconds and data.retry_delay_seconds != action.retry_delay_seconds:
            changes.append(f"retry_delay_seconds: {action.retry_delay_seconds} → {data.retry_delay_seconds}")
        
        return updated_action, changes
    
    def _validate_updated_configuration(self, action: Action) -> None:
        """Validate the final updated configuration.
        
        Uses the Action's built-in validation to ensure
        the complete configuration is valid.
        
        Args:
            action: Updated action to validate
            
        Raises:
            ValueError: If configuration is invalid
        """
        # The Action.__post_init__ will validate the configuration
        # This ensures that the complete merged configuration is valid
        pass
    
    def _build_update_dict(self, action: Action) -> Dict[str, Any]:
        """Build update dictionary for repository.
        
        Args:
            action: Updated action entity
            
        Returns:
            Dictionary of updates to apply
        """
        return {
            "handler_type": action.handler_type,
            "configuration": action.configuration,
            "execution_mode": action.execution_mode,
            "priority": action.priority,
            "timeout_seconds": action.timeout_seconds,
            "max_retries": action.max_retries,
            "retry_delay_seconds": action.retry_delay_seconds,
            "updated_at": action.updated_at
        }


def create_configure_handler_command(repository: ActionRepository) -> ConfigureHandlerCommand:
    """Factory function to create ConfigureHandlerCommand instance.
    
    Args:
        repository: Action repository for action persistence
        
    Returns:
        Configured ConfigureHandlerCommand instance
    """
    return ConfigureHandlerCommand(repository=repository)