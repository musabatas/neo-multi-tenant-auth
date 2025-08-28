"""Action entity for platform actions infrastructure.

Extracted from platform/events/core/entities/event_action.py following maximum separation architecture.
This module contains ONLY the Action entity with single responsibility.

Moved to platform/actions as it's action-focused, not event-focused.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

from .....core.value_objects import UserId
from .....utils import utc_now, ensure_utc
from ..value_objects import (
    ActionId,
    ActionStatus, 
    HandlerType,
    ActionPriority,
    ExecutionMode,
    ActionCondition
)


@dataclass
class Action:
    """Action domain entity.
    
    Represents a configurable action that can be triggered by events or executed independently.
    Supports flexible conditions, multiple handler types, and execution modes.
    
    Following maximum separation architecture - this file contains ONLY Action entity.
    ActionCondition and ActionExecution are separate entities in their own files.
    """
    
    # Identification and naming
    id: ActionId = field(default_factory=ActionId.generate)
    name: str = ""
    description: Optional[str] = None
    
    # Action configuration
    handler_type: HandlerType = HandlerType.WEBHOOK
    configuration: Dict[str, Any] = field(default_factory=dict)
    
    # Trigger conditions (optional - actions can be executed independently)
    event_types: List[str] = field(default_factory=list)  # Event types to trigger on
    conditions: List[ActionCondition] = field(default_factory=list)  # ActionCondition value objects
    context_filters: Dict[str, Any] = field(default_factory=dict)  # Context-based filters
    
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
    tags: Dict[str, str] = field(default_factory=dict)
    created_by_user_id: Optional[UserId] = None
    tenant_id: Optional[str] = None  # For multi-tenant filtering
    
    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    last_triggered_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        # Validate required fields
        if not self.name or not self.name.strip():
            raise ValueError("Action name cannot be empty")
        
        # Validate configuration based on handler type
        self._validate_configuration()
        
        # Ensure timestamps are timezone-aware
        self.created_at = ensure_utc(self.created_at)
        self.updated_at = ensure_utc(self.updated_at)
    
    def _validate_configuration(self) -> None:
        """Validate configuration based on handler type."""
        if self.handler_type == HandlerType.WEBHOOK:
            if not self.configuration.get("url"):
                raise ValueError("Webhook handler requires 'url' in configuration")
        
        elif self.handler_type == HandlerType.EMAIL:
            if not self.configuration.get("to"):
                raise ValueError("Email handler requires 'to' address in configuration")
            if not self.configuration.get("template"):
                raise ValueError("Email handler requires 'template' in configuration")
        
        elif self.handler_type == HandlerType.FUNCTION:
            if not self.configuration.get("module"):
                raise ValueError("Function handler requires 'module' in configuration")
            if not self.configuration.get("function"):
                raise ValueError("Function handler requires 'function' name in configuration")
        
        elif self.handler_type == HandlerType.WORKFLOW:
            if not self.configuration.get("steps"):
                raise ValueError("Workflow handler requires 'steps' in configuration")
    
    def matches_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Check if this action should be triggered for the given event.
        
        Args:
            event_type: The event type that occurred
            event_data: Full event data including metadata
            
        Returns:
            True if action should be triggered, False otherwise
        """
        # Check if action is enabled and active
        if not self.is_enabled or self.status != ActionStatus.ACTIVE:
            return False
        
        # If no event types configured, action doesn't respond to events
        if not self.event_types:
            return False
        
        # Check event type match (supports wildcards)
        if not self._matches_event_type(event_type):
            return False
        
        # Check context filters
        if not self._matches_context_filters(event_data):
            return False
        
        # Check additional conditions (ActionCondition objects evaluated separately)
        if not self._matches_conditions(event_data):
            return False
        
        return True
    
    def _matches_event_type(self, event_type: str) -> bool:
        """Check if event type matches any of the configured types."""
        for configured_type in self.event_types:
            if configured_type == "*":  # Wildcard - matches all
                return True
            elif configured_type.endswith(".*"):  # Category wildcard
                category = configured_type[:-2]
                if event_type.startswith(category + "."):
                    return True
            elif configured_type == event_type:  # Exact match
                return True
        
        return False
    
    def _matches_context_filters(self, event_data: Dict[str, Any]) -> bool:
        """Check if event matches context filters."""
        if not self.context_filters:
            return True
        
        for filter_key, filter_value in self.context_filters.items():
            event_value = event_data.get(filter_key)
            
            if isinstance(filter_value, list):
                if event_value not in filter_value:
                    return False
            elif event_value != filter_value:
                return False
        
        return True
    
    def _matches_conditions(self, event_data: Dict[str, Any]) -> bool:
        """Check if event matches all additional conditions.
        
        Note: conditions list contains ActionCondition value objects with evaluate() method.
        ActionCondition is a separate value object following maximum separation architecture.
        """
        for condition in self.conditions:
            if not condition.evaluate(event_data):
                return False
        
        return True
    
    def update_last_triggered(self) -> None:
        """Update last triggered timestamp.
        
        Note: Statistics (trigger_count, success_count, failure_count) are calculated
        from the action_executions table rather than stored on the action entity.
        """
        self.last_triggered_at = utc_now()
        self.updated_at = utc_now()
    
    def pause(self) -> None:
        """Pause the action (sets status to PAUSED)."""
        if self.status == ActionStatus.ACTIVE:
            self.status = ActionStatus.PAUSED
            self.updated_at = utc_now()
    
    def resume(self) -> None:
        """Resume the action (sets status to ACTIVE)."""
        if self.status == ActionStatus.PAUSED:
            self.status = ActionStatus.ACTIVE
            self.updated_at = utc_now()
    
    def disable(self) -> None:
        """Disable the action."""
        self.is_enabled = False
        self.updated_at = utc_now()
    
    def enable(self) -> None:
        """Enable the action."""
        self.is_enabled = True
        self.updated_at = utc_now()
    
    def archive(self) -> None:
        """Archive the action (sets status to ARCHIVED and disables)."""
        self.status = ActionStatus.ARCHIVED
        self.is_enabled = False
        self.updated_at = utc_now()
    
    def update_configuration(self, new_config: Dict[str, Any]) -> None:
        """Update action configuration.
        
        Args:
            new_config: New configuration dictionary
        """
        old_handler_type = self.handler_type
        
        # Update configuration
        self.configuration.update(new_config)
        
        # If handler type changed, revalidate
        if self.handler_type != old_handler_type:
            self._validate_configuration()
        
        self.updated_at = utc_now()
    
    def add_condition(self, condition: ActionCondition) -> None:
        """Add a new condition to the action.
        
        Args:
            condition: ActionCondition value object to add
        """
        self.conditions.append(condition)
        self.updated_at = utc_now()
    
    def remove_condition(self, field: str, operator: str) -> bool:
        """Remove a condition from the action.
        
        Args:
            field: Field name of condition to remove
            operator: Operator of condition to remove
            
        Returns:
            True if condition was found and removed, False otherwise
        """
        for i, condition in enumerate(self.conditions):
            if condition.field == field and condition.operator == operator:
                self.conditions.pop(i)
                self.updated_at = utc_now()
                return True
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary for serialization."""
        return {
            "id": str(self.id.value),
            "name": self.name,
            "description": self.description,
            "handler_type": self.handler_type.value,
            "configuration": self.configuration,
            "event_types": self.event_types,
            "conditions": [condition.to_dict() for condition in self.conditions],
            "context_filters": self.context_filters,
            "execution_mode": self.execution_mode.value,
            "priority": self.priority.value,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "retry_delay_seconds": self.retry_delay_seconds,
            "status": self.status.value,
            "is_enabled": self.is_enabled,
            "tags": self.tags,
            "created_by_user_id": str(self.created_by_user_id.value) if self.created_by_user_id else None,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_triggered_at": self.last_triggered_at.isoformat() if self.last_triggered_at else None
        }