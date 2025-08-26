"""
This module defines the EventAction entity and related enums for dynamic event handling.
Enables flexible, configurable actions that can be triggered by domain events.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from ....core.value_objects import ActionId, UserId, EventType


class ActionStatus(Enum):
    """Event action status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    ARCHIVED = "archived"


class HandlerType(Enum):
    """Action handler type enumeration."""
    WEBHOOK = "webhook"
    EMAIL = "email"
    FUNCTION = "function"
    WORKFLOW = "workflow"
    SMS = "sms"
    SLACK = "slack"
    TEAMS = "teams"
    CUSTOM = "custom"


class ActionPriority(Enum):
    """Action execution priority enumeration."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class ExecutionMode(Enum):
    """Action execution mode enumeration."""
    SYNC = "sync"      # Execute synchronously (blocks event processing)
    ASYNC = "async"    # Execute asynchronously (non-blocking)
    QUEUED = "queued"  # Queue for later execution


class ActionCondition:
    """Represents a condition that must be met for action execution."""
    
    def __init__(self, field: str, operator: str, value: Any):
        """Initialize action condition.
        
        Args:
            field: Event field to check (e.g., 'event_type', 'context_id', 'data.user_id')
            operator: Comparison operator ('equals', 'contains', 'gt', 'lt', 'in', 'not_in')
            value: Value to compare against
        """
        self.field = field
        self.operator = operator
        self.value = value
    
    def evaluate(self, event_data: Dict[str, Any]) -> bool:
        """Evaluate condition against event data.
        
        Args:
            event_data: Event data to evaluate against
            
        Returns:
            True if condition is met, False otherwise
        """
        # Get field value from event data (supports nested fields)
        field_value = self._get_field_value(event_data, self.field)
        
        if self.operator == "equals":
            return field_value == self.value
        elif self.operator == "contains":
            return str(self.value) in str(field_value) if field_value else False
        elif self.operator == "gt":
            return field_value > self.value if field_value is not None else False
        elif self.operator == "lt":
            return field_value < self.value if field_value is not None else False
        elif self.operator == "in":
            return field_value in self.value if isinstance(self.value, (list, tuple)) else False
        elif self.operator == "not_in":
            return field_value not in self.value if isinstance(self.value, (list, tuple)) else True
        elif self.operator == "exists":
            return field_value is not None
        elif self.operator == "not_exists":
            return field_value is None
        else:
            raise ValueError(f"Unknown operator: {self.operator}")
    
    def _get_field_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get nested field value from data using dot notation.
        
        Args:
            data: Data dictionary
            field_path: Field path with dot notation (e.g., 'data.user.id')
            
        Returns:
            Field value or None if not found
        """
        parts = field_path.split('.')
        current = data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert condition to dictionary."""
        return {
            "field": self.field,
            "operator": self.operator,
            "value": self.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionCondition":
        """Create condition from dictionary."""
        return cls(
            field=data["field"],
            operator=data["operator"],
            value=data["value"]
        )


@dataclass
class EventAction:
    """Event action domain entity.
    
    Represents a configurable action that can be triggered by domain events.
    Supports flexible conditions, multiple handler types, and execution modes.
    """
    
    # Identification and naming
    id: ActionId
    name: str
    description: Optional[str] = None
    
    # Action configuration
    handler_type: HandlerType = HandlerType.WEBHOOK
    configuration: Dict[str, Any] = field(default_factory=dict)
    
    # Trigger conditions
    event_types: List[str] = field(default_factory=list)  # Event types to trigger on
    conditions: List[ActionCondition] = field(default_factory=list)  # Additional conditions
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
    created_by_user_id: UserId = None
    tenant_id: Optional[str] = None  # For multi-tenant filtering
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_triggered_at: Optional[datetime] = None
    
    # Statistics
    trigger_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        # Validate required fields
        if not self.name or not self.name.strip():
            raise ValueError("Action name cannot be empty")
        
        if not self.event_types:
            raise ValueError("At least one event type must be specified")
        
        # Validate event types format
        for event_type in self.event_types:
            if not event_type or '.' not in event_type:
                raise ValueError(f"Invalid event type format: {event_type}")
        
        # Validate configuration based on handler type
        self._validate_configuration()
        
        # Ensure timestamps are timezone-aware
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)
        
        if self.updated_at.tzinfo is None:
            self.updated_at = self.updated_at.replace(tzinfo=timezone.utc)
    
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
        
        # Check event type match (supports wildcards)
        if not self._matches_event_type(event_type):
            return False
        
        # Check context filters
        if not self._matches_context_filters(event_data):
            return False
        
        # Check additional conditions
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
        """Check if event matches all additional conditions."""
        for condition in self.conditions:
            if not condition.evaluate(event_data):
                return False
        
        return True
    
    def update_trigger_stats(self, success: bool) -> None:
        """Update trigger statistics.
        
        Args:
            success: Whether the action execution was successful
        """
        self.trigger_count += 1
        self.last_triggered_at = datetime.now(timezone.utc)
        
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        
        self.updated_at = datetime.now(timezone.utc)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.trigger_count == 0:
            return 0.0
        return (self.success_count / self.trigger_count) * 100
    
    def pause(self) -> None:
        """Pause the action (sets status to PAUSED)."""
        if self.status == ActionStatus.ACTIVE:
            self.status = ActionStatus.PAUSED
            self.updated_at = datetime.now(timezone.utc)
    
    def resume(self) -> None:
        """Resume the action (sets status to ACTIVE)."""
        if self.status == ActionStatus.PAUSED:
            self.status = ActionStatus.ACTIVE
            self.updated_at = datetime.now(timezone.utc)
    
    def disable(self) -> None:
        """Disable the action."""
        self.is_enabled = False
        self.updated_at = datetime.now(timezone.utc)
    
    def enable(self) -> None:
        """Enable the action."""
        self.is_enabled = True
        self.updated_at = datetime.now(timezone.utc)
    
    def archive(self) -> None:
        """Archive the action (sets status to ARCHIVED and disables)."""
        self.status = ActionStatus.ARCHIVED
        self.is_enabled = False
        self.updated_at = datetime.now(timezone.utc)
    
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
        
        self.updated_at = datetime.now(timezone.utc)
    
    def add_condition(self, condition: ActionCondition) -> None:
        """Add a new condition to the action.
        
        Args:
            condition: Condition to add
        """
        self.conditions.append(condition)
        self.updated_at = datetime.now(timezone.utc)
    
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
                self.updated_at = datetime.now(timezone.utc)
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
            "last_triggered_at": self.last_triggered_at.isoformat() if self.last_triggered_at else None,
            "trigger_count": self.trigger_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate
        }


@dataclass
class ActionExecution:
    """Represents a single execution of an event action."""
    
    id: ActionId  # Using ActionExecutionId would be better, but ActionId works for now
    action_id: ActionId
    event_id: Optional[str] = None  # EventId from the triggering event
    
    # Execution context
    event_type: str = ""
    event_data: Dict[str, Any] = field(default_factory=dict)
    
    # Execution details
    status: str = "pending"  # pending, running, success, failed, timeout
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    
    # Results and error handling
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    
    # Metadata
    execution_context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def start_execution(self) -> None:
        """Mark execution as started."""
        self.status = "running"
        self.started_at = datetime.now(timezone.utc)
    
    def complete_success(self, result: Dict[str, Any]) -> None:
        """Mark execution as successfully completed."""
        self.status = "success"
        self.completed_at = datetime.now(timezone.utc)
        self.result = result
        
        if self.started_at:
            duration = self.completed_at - self.started_at
            self.duration_ms = int(duration.total_seconds() * 1000)
    
    def complete_failure(self, error_message: str) -> None:
        """Mark execution as failed."""
        self.status = "failed"
        self.completed_at = datetime.now(timezone.utc)
        self.error_message = error_message
        
        if self.started_at:
            duration = self.completed_at - self.started_at
            self.duration_ms = int(duration.total_seconds() * 1000)
    
    def complete_timeout(self) -> None:
        """Mark execution as timed out."""
        self.status = "timeout"
        self.completed_at = datetime.now(timezone.utc)
        self.error_message = "Execution timed out"
        
        if self.started_at:
            duration = self.completed_at - self.started_at
            self.duration_ms = int(duration.total_seconds() * 1000)