"""Create action command for platform actions infrastructure.

This module handles ONLY action creation operations following maximum separation architecture.
Single responsibility: Create and configure new actions in the platform system.

Pure application layer - no infrastructure concerns.
Uses protocols for dependency injection and clean architecture compliance.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime

from ...core.protocols import ActionRepository
from ...core.entities import Action
from ...core.value_objects import ActionId, ActionStatus, HandlerType, ActionPriority, ExecutionMode, ActionCondition
from ...core.exceptions import ActionExecutionFailed
from neo_commons.core.value_objects import UserId
from neo_commons.utils import utc_now, generate_uuid_v7


@dataclass
class CreateActionData:
    """Data required to create an action.
    
    Contains all the configuration needed to create a new action.
    Separates data from business logic following CQRS patterns.
    """
    name: str
    description: Optional[str] = None
    
    # Action configuration
    handler_type: HandlerType = HandlerType.WEBHOOK
    configuration: Dict[str, Any] = None
    
    # Trigger conditions
    event_types: List[str] = None
    conditions: List[ActionCondition] = None
    context_filters: Dict[str, Any] = None
    
    # Execution settings
    execution_mode: ExecutionMode = ExecutionMode.ASYNC
    priority: ActionPriority = ActionPriority.NORMAL
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: int = 5
    
    # Status and lifecycle
    status: ActionStatus = ActionStatus.ACTIVE
    is_enabled: bool = True
    
    # Metadata and tracking
    tags: Dict[str, str] = None
    created_by_user_id: Optional[UserId] = None
    tenant_id: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.configuration is None:
            self.configuration = {}
        if self.event_types is None:
            self.event_types = []
        if self.conditions is None:
            self.conditions = []
        if self.context_filters is None:
            self.context_filters = {}
        if self.tags is None:
            self.tags = {}


@dataclass
class CreateActionResult:
    """Result of action creation operation.
    
    Contains comprehensive creation results for monitoring and tracking.
    Provides structured feedback about the creation process.
    """
    action_id: ActionId
    created_successfully: bool
    action: Optional[Action] = None
    validation_warnings: List[str] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.validation_warnings is None:
            self.validation_warnings = []


class CreateActionCommand:
    """Command to create a new action configuration.
    
    Single responsibility: Create and persist a new action with proper
    validation, configuration setup, and metadata management. Ensures all
    required fields are set and configuration is valid for the handler type.
    
    Following enterprise command pattern with protocol-based dependencies.
    Pure application logic - delegates infrastructure concerns to protocols.
    """
    
    def __init__(self, action_repository: ActionRepository):
        """Initialize create action command with required dependencies.
        
        Args:
            action_repository: Protocol for action persistence operations
        """
        self._action_repository = action_repository
    
    async def execute(self, data: CreateActionData) -> CreateActionResult:
        """Execute action creation command.
        
        Orchestrates the complete action creation process:
        1. Validate action configuration data
        2. Create Action entity with proper defaults
        3. Validate handler-specific configuration
        4. Persist action to repository
        5. Return comprehensive creation results
        
        Args:
            data: Action creation configuration data
            
        Returns:
            CreateActionResult with comprehensive creation information
            
        Raises:
            ActionExecutionFailed: If action creation fails
        """
        try:
            # 1. Validate required data
            validation_warnings = await self._validate_action_data(data)
            
            # 2. Create Action entity
            action = Action(
                id=ActionId.generate(),
                name=data.name,
                description=data.description,
                handler_type=data.handler_type,
                configuration=data.configuration,
                event_types=data.event_types,
                conditions=data.conditions,
                context_filters=data.context_filters,
                execution_mode=data.execution_mode,
                priority=data.priority,
                timeout_seconds=data.timeout_seconds,
                max_retries=data.max_retries,
                retry_delay_seconds=data.retry_delay_seconds,
                status=data.status,
                is_enabled=data.is_enabled,
                tags=data.tags,
                created_by_user_id=data.created_by_user_id,
                tenant_id=data.tenant_id,
                created_at=utc_now(),
                updated_at=utc_now()
            )
            
            # 3. Persist action to repository
            persisted_action = await self._action_repository.save_action(action)
            
            return CreateActionResult(
                action_id=persisted_action.id,
                created_successfully=True,
                action=persisted_action,
                validation_warnings=validation_warnings
            )
            
        except Exception as e:
            # Wrap in domain exception if needed
            if not isinstance(e, ActionExecutionFailed):
                raise ActionExecutionFailed(
                    f"Failed to create action '{data.name}': {str(e)}",
                    original_error=e
                ) from e
            
            return CreateActionResult(
                action_id=ActionId.generate(),  # Generate temp ID for error tracking
                created_successfully=False,
                validation_warnings=[],
                error_message=str(e)
            )
    
    async def execute_webhook_action(
        self,
        name: str,
        webhook_url: str,
        event_types: List[str],
        secret: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        created_by_user_id: Optional[UserId] = None,
        tenant_id: Optional[str] = None
    ) -> CreateActionResult:
        """Convenience method to create a webhook action.
        
        Creates a webhook action with standard configuration and validation.
        Commonly used pattern for webhook action creation.
        
        Args:
            name: Action name
            webhook_url: Webhook endpoint URL
            event_types: List of event types to subscribe to
            secret: Optional webhook secret for HMAC validation
            headers: Optional custom headers for webhook requests
            created_by_user_id: User who created this action
            tenant_id: Optional tenant context for multi-tenant filtering
            
        Returns:
            CreateActionResult with creation information
            
        Raises:
            ActionExecutionFailed: If webhook action creation fails
        """
        # Build webhook configuration
        configuration = {
            "url": webhook_url,
            "method": "POST",
            "timeout_seconds": 30,
            "verify_ssl": True
        }
        
        if secret:
            configuration["secret"] = secret
        
        if headers:
            configuration["headers"] = headers
        
        # Create action data
        data = CreateActionData(
            name=name,
            description=f"Webhook action for {webhook_url}",
            handler_type=HandlerType.WEBHOOK,
            configuration=configuration,
            event_types=event_types,
            created_by_user_id=created_by_user_id,
            tenant_id=tenant_id
        )
        
        return await self.execute(data)
    
    async def execute_email_action(
        self,
        name: str,
        email_to: str,
        email_template: str,
        event_types: List[str],
        email_subject: Optional[str] = None,
        email_from: Optional[str] = None,
        created_by_user_id: Optional[UserId] = None,
        tenant_id: Optional[str] = None
    ) -> CreateActionResult:
        """Convenience method to create an email notification action.
        
        Creates an email action with standard configuration and validation.
        Commonly used pattern for email notification action creation.
        
        Args:
            name: Action name
            email_to: Recipient email address
            email_template: Email template identifier
            event_types: List of event types to subscribe to
            email_subject: Optional custom email subject template
            email_from: Optional custom sender email address
            created_by_user_id: User who created this action
            tenant_id: Optional tenant context for multi-tenant filtering
            
        Returns:
            CreateActionResult with creation information
            
        Raises:
            ActionExecutionFailed: If email action creation fails
        """
        # Build email configuration
        configuration = {
            "to": email_to,
            "template": email_template
        }
        
        if email_subject:
            configuration["subject"] = email_subject
        
        if email_from:
            configuration["from"] = email_from
        
        # Create action data
        data = CreateActionData(
            name=name,
            description=f"Email notification action for {email_to}",
            handler_type=HandlerType.EMAIL,
            configuration=configuration,
            event_types=event_types,
            created_by_user_id=created_by_user_id,
            tenant_id=tenant_id
        )
        
        return await self.execute(data)
    
    async def _validate_action_data(self, data: CreateActionData) -> List[str]:
        """Validate action creation data.
        
        Performs comprehensive validation of action data to ensure it meets
        requirements for successful creation and execution.
        
        Args:
            data: Action creation data to validate
            
        Returns:
            List of validation warnings (non-blocking issues)
            
        Raises:
            ActionExecutionFailed: If validation fails with blocking issues
        """
        warnings = []
        
        # Validate required fields
        if not data.name or not data.name.strip():
            raise ActionExecutionFailed("Action name is required and cannot be empty")
        
        # Event types are optional for actions (can be executed independently)
        
        # Validate event types format if provided
        if data.event_types:
            for event_type in data.event_types:
                if not event_type or '.' not in event_type:
                    raise ActionExecutionFailed(f"Invalid event type format: {event_type}")
        
        # Validate handler configuration
        await self._validate_handler_configuration(data.handler_type, data.configuration)
        
        # Check for potential issues (warnings)
        if data.timeout_seconds > 300:  # 5 minutes
            warnings.append(f"Timeout of {data.timeout_seconds} seconds is very long")
        
        if data.max_retries > 10:
            warnings.append(f"Max retries of {data.max_retries} is very high")
        
        if data.event_types and len(data.event_types) > 50:
            warnings.append(f"Large number of event types ({len(data.event_types)}) may impact performance")
        
        return warnings
    
    async def _validate_handler_configuration(
        self,
        handler_type: HandlerType,
        configuration: Dict[str, Any]
    ) -> None:
        """Validate handler-specific configuration.
        
        Ensures the configuration contains all required fields for the
        specified handler type and validates field values.
        
        Args:
            handler_type: Type of handler to validate configuration for
            configuration: Configuration dictionary to validate
            
        Raises:
            ActionExecutionFailed: If configuration is invalid
        """
        if handler_type == HandlerType.WEBHOOK:
            if not configuration.get("url"):
                raise ActionExecutionFailed("Webhook handler requires 'url' in configuration")
            
            url = configuration["url"]
            if not url.startswith(("http://", "https://")):
                raise ActionExecutionFailed("Webhook URL must start with http:// or https://")
        
        elif handler_type == HandlerType.EMAIL:
            if not configuration.get("to"):
                raise ActionExecutionFailed("Email handler requires 'to' address in configuration")
            
            if not configuration.get("template"):
                raise ActionExecutionFailed("Email handler requires 'template' in configuration")
        
        elif handler_type == HandlerType.FUNCTION:
            if not configuration.get("module"):
                raise ActionExecutionFailed("Function handler requires 'module' in configuration")
            
            if not configuration.get("function"):
                raise ActionExecutionFailed("Function handler requires 'function' name in configuration")
        
        elif handler_type == HandlerType.WORKFLOW:
            if not configuration.get("steps"):
                raise ActionExecutionFailed("Workflow handler requires 'steps' in configuration")
            
            steps = configuration.get("steps", [])
            if not isinstance(steps, list) or len(steps) == 0:
                raise ActionExecutionFailed("Workflow handler requires at least one step")