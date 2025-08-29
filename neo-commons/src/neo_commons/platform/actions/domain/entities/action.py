"""Core Action entity for action execution."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from uuid import UUID
from enum import Enum

from ..value_objects.action_id import ActionId
from ..value_objects.action_type import ActionType
from ....utils import generate_uuid_v7


class ActionStatus(Enum):
    """Action processing status matching platform_common.action_status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"
    PAUSED = "paused"
    BLOCKED = "blocked"


@dataclass
class Action:
    """
    Core Action entity for action execution.
    
    Represents an action definition that can be executed in response to events.
    Maps to the admin.actions and tenant_template.actions database tables.
    """
    
    # Core Identity (immutable after creation)
    id: ActionId
    name: str
    action_type: ActionType
    
    # Action Configuration (immutable after creation)
    handler_class: str
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Trigger Configuration (mutable for configuration updates)
    event_patterns: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    # Execution Settings (mutable for operational tuning)
    is_active: bool = True
    priority: str = "normal"  # Using EventPriority values: low, normal, high, very_high, critical
    timeout_seconds: int = 300
    retry_policy: Dict[str, Any] = field(default_factory=lambda: {
        "max_retries": 3, 
        "backoff_type": "exponential", 
        "initial_delay_ms": 1000
    })
    
    # Resource Limits (mutable for operational tuning)
    max_concurrent_executions: int = 1
    rate_limit_per_minute: Optional[int] = None
    
    # Monitoring and Health (mutable for health tracking)
    is_healthy: bool = True
    last_health_check_at: Optional[datetime] = None
    health_check_error: Optional[str] = None
    
    # Statistics (mutable for metrics tracking)
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    avg_execution_time_ms: int = 0
    
    # Metadata (mutable for operational management)
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    owner_team: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Audit Fields (immutable after creation, auto-updated)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None
    
    @classmethod
    def create(
        cls,
        name: str,
        action_type: str,
        handler_class: str,
        event_patterns: List[str],
        config: Optional[Dict[str, Any]] = None,
        conditions: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        is_active: bool = True,
        priority: str = "normal",
        timeout_seconds: int = 300,
        retry_policy: Optional[Dict[str, Any]] = None,
        max_concurrent_executions: int = 1,
        rate_limit_per_minute: Optional[int] = None,
        tags: Optional[List[str]] = None,
        owner_team: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'Action':
        """
        Create a new Action with proper validation.
        
        Args:
            name: Unique action name (e.g., 'send_welcome_email')
            action_type: Action type enum value (e.g., 'email')
            handler_class: Python class path for action handler
            event_patterns: List of event patterns this action responds to
            config: Action-specific configuration
            conditions: Additional trigger conditions
            description: Action description
            is_active: Whether action is active
            priority: Action priority (low, normal, high, very_high, critical)
            timeout_seconds: Action execution timeout
            retry_policy: Retry configuration
            max_concurrent_executions: Maximum concurrent executions
            rate_limit_per_minute: Rate limiting configuration
            tags: Action tags for organization
            owner_team: Team responsible for this action
            metadata: Additional metadata
            
        Returns:
            New Action instance
        """
        return cls(
            id=ActionId(generate_uuid_v7()),
            name=name,
            action_type=ActionType(action_type),
            handler_class=handler_class,
            config=config.copy() if config else {},
            event_patterns=event_patterns.copy() if event_patterns else [],
            conditions=conditions.copy() if conditions else {},
            description=description,
            is_active=is_active,
            priority=priority,
            timeout_seconds=timeout_seconds,
            retry_policy=retry_policy.copy() if retry_policy else {
                "max_retries": 3, 
                "backoff_type": "exponential", 
                "initial_delay_ms": 1000
            },
            max_concurrent_executions=max_concurrent_executions,
            rate_limit_per_minute=rate_limit_per_minute,
            tags=tags.copy() if tags else [],
            owner_team=owner_team,
            metadata=metadata.copy() if metadata else {}
        )
    
    def update_health_status(self, is_healthy: bool, error_message: Optional[str] = None) -> None:
        """Update action health status."""
        self.is_healthy = is_healthy
        self.health_check_error = error_message
        self.last_health_check_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def update_statistics(self, execution_time_ms: int, success: bool) -> None:
        """Update action execution statistics."""
        self.total_executions += 1
        
        if success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1
        
        # Update rolling average execution time
        if self.total_executions == 1:
            self.avg_execution_time_ms = execution_time_ms
        else:
            # Simple moving average
            current_avg = self.avg_execution_time_ms
            self.avg_execution_time_ms = int(
                (current_avg * (self.total_executions - 1) + execution_time_ms) / self.total_executions
            )
        
        self.updated_at = datetime.now(timezone.utc)
    
    def deactivate(self) -> None:
        """Deactivate the action."""
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)
    
    def activate(self) -> None:
        """Activate the action."""
        self.is_active = True
        self.updated_at = datetime.now(timezone.utc)
    
    def can_execute(self) -> bool:
        """Check if action can be executed."""
        return self.is_active and self.is_healthy
    
    def matches_event_pattern(self, event_type: str) -> bool:
        """Check if event type matches any of the action's patterns."""
        import fnmatch
        for pattern in self.event_patterns:
            if fnmatch.fnmatch(event_type, pattern):
                return True
        return False
    
    def get_success_rate(self) -> float:
        """Get action success rate as percentage."""
        if self.total_executions == 0:
            return 0.0
        return (self.successful_executions / self.total_executions) * 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary representation."""
        return {
            'id': str(self.id.value),
            'name': self.name,
            'action_type': self.action_type.value,
            'handler_class': self.handler_class,
            'config': self.config,
            'event_patterns': self.event_patterns,
            'conditions': self.conditions,
            'is_active': self.is_active,
            'priority': self.priority,
            'timeout_seconds': self.timeout_seconds,
            'retry_policy': self.retry_policy,
            'max_concurrent_executions': self.max_concurrent_executions,
            'rate_limit_per_minute': self.rate_limit_per_minute,
            'is_healthy': self.is_healthy,
            'last_health_check_at': self.last_health_check_at.isoformat() if self.last_health_check_at else None,
            'health_check_error': self.health_check_error,
            'total_executions': self.total_executions,
            'successful_executions': self.successful_executions,
            'failed_executions': self.failed_executions,
            'avg_execution_time_ms': self.avg_execution_time_ms,
            'success_rate': self.get_success_rate(),
            'description': self.description,
            'tags': self.tags,
            'owner_team': self.owner_team,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
        }
    
    def __post_init__(self):
        """Validate action after initialization."""
        # Validate timeout
        if self.timeout_seconds <= 0:
            raise ValueError(f"timeout_seconds must be positive: {self.timeout_seconds}")
        
        # Validate concurrent executions
        if self.max_concurrent_executions <= 0:
            raise ValueError(f"max_concurrent_executions must be positive: {self.max_concurrent_executions}")
        
        # Validate rate limit
        if self.rate_limit_per_minute is not None and self.rate_limit_per_minute <= 0:
            raise ValueError(f"rate_limit_per_minute must be positive: {self.rate_limit_per_minute}")
        
        # Validate statistics
        if self.total_executions < 0:
            raise ValueError(f"total_executions cannot be negative: {self.total_executions}")
        if self.successful_executions < 0:
            raise ValueError(f"successful_executions cannot be negative: {self.successful_executions}")
        if self.failed_executions < 0:
            raise ValueError(f"failed_executions cannot be negative: {self.failed_executions}")
        if (self.successful_executions + self.failed_executions) > self.total_executions:
            raise ValueError("successful + failed executions cannot exceed total executions")
        
        # Validate event patterns
        if not self.event_patterns:
            raise ValueError("Action must have at least one event pattern")
    
    def __str__(self) -> str:
        return f"Action(id={self.id}, name={self.name}, type={self.action_type.value})"
    
    def __repr__(self) -> str:
        return (f"Action(id={self.id!r}, name={self.name!r}, action_type={self.action_type!r}, "
                f"is_active={self.is_active}, is_healthy={self.is_healthy})")