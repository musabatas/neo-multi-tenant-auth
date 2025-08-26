"""Action execution entity for platform events infrastructure.

This module defines the ActionExecution entity that represents a single execution
of an event action with tracking, results, and performance metrics.

Extracted from features/events to platform/events following enterprise
clean architecture patterns for maximum separation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime

from .....core.value_objects import UserId
from .....utils import generate_uuid_v7, utc_now, ensure_utc
from ..value_objects import ActionId, EventId


@dataclass
class ActionExecution:
    """Action execution domain entity.
    
    Represents a single execution of an event action with complete lifecycle tracking,
    results, error handling, and performance metrics.
    
    Maps to action_executions table in both admin and tenant schemas.
    Pure platform infrastructure - used by all business features.
    """
    
    # Execution identification (UUIDv7 for time-ordering)
    id: ActionId = field(default_factory=lambda: ActionId(generate_uuid_v7()))
    action_id: ActionId = field(default_factory=lambda: ActionId(generate_uuid_v7()))
    event_id: Optional[EventId] = None  # Reference to the triggering event
    
    # Event context (matches database schema)
    event_type: str = ""
    event_data: Dict[str, Any] = field(default_factory=dict)
    
    # Execution lifecycle tracking (matches database status field)
    status: str = "pending"  # pending, running, success, failed, timeout
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    
    # Results and error handling (matches database schema)
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    
    # Execution context and metadata (matches database schema)
    execution_context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        # Ensure created_at is timezone-aware using our timezone utility
        self.created_at = ensure_utc(self.created_at)
        
        # Validate status values (matches database check constraint)
        valid_statuses = {"pending", "running", "success", "failed", "timeout"}
        if self.status not in valid_statuses:
            raise ValueError(f"Invalid status: {self.status}. Must be one of {valid_statuses}")
        
        # Validate retry_count
        if self.retry_count < 0:
            raise ValueError("Retry count cannot be negative")
    
    def start_execution(self) -> None:
        """Mark execution as started with timestamp."""
        if self.status != "pending":
            raise ValueError(f"Cannot start execution with status: {self.status}")
        
        self.status = "running"
        self.started_at = utc_now()
    
    def complete_success(self, result: Dict[str, Any]) -> None:
        """Mark execution as successfully completed with result.
        
        Args:
            result: Execution result data to store
        """
        if self.status != "running":
            raise ValueError(f"Cannot complete execution with status: {self.status}")
        
        self.status = "success"
        self.completed_at = utc_now()
        self.result = result
        
        # Calculate duration if started
        if self.started_at:
            duration = self.completed_at - self.started_at
            self.duration_ms = int(duration.total_seconds() * 1000)
    
    def complete_failure(self, error_message: str) -> None:
        """Mark execution as failed with error message.
        
        Args:
            error_message: Error description for debugging
        """
        if self.status not in {"running", "pending"}:
            raise ValueError(f"Cannot fail execution with status: {self.status}")
        
        self.status = "failed"
        self.completed_at = utc_now()
        self.error_message = error_message
        
        # Calculate duration if started
        if self.started_at:
            duration = self.completed_at - self.started_at
            self.duration_ms = int(duration.total_seconds() * 1000)
    
    def complete_timeout(self) -> None:
        """Mark execution as timed out."""
        if self.status != "running":
            raise ValueError(f"Cannot timeout execution with status: {self.status}")
        
        self.status = "timeout"
        self.completed_at = utc_now()
        self.error_message = "Execution timed out"
        
        # Calculate duration if started
        if self.started_at:
            duration = self.completed_at - self.started_at
            self.duration_ms = int(duration.total_seconds() * 1000)
    
    def increment_retry_count(self) -> None:
        """Increment retry count for failed executions."""
        if self.status not in {"failed", "timeout"}:
            raise ValueError(f"Cannot retry execution with status: {self.status}")
        
        self.retry_count += 1
        # Reset to pending for retry
        self.status = "pending"
        self.started_at = None
        self.completed_at = None
        self.duration_ms = None
        self.result = None
        # Keep error_message for history
    
    def is_completed(self) -> bool:
        """Check if execution has completed (success, failed, or timeout)."""
        return self.status in {"success", "failed", "timeout"}
    
    def is_successful(self) -> bool:
        """Check if execution completed successfully."""
        return self.status == "success"
    
    def is_failed(self) -> bool:
        """Check if execution failed or timed out."""
        return self.status in {"failed", "timeout"}
    
    def is_running(self) -> bool:
        """Check if execution is currently running."""
        return self.status == "running"
    
    def is_pending(self) -> bool:
        """Check if execution is pending start."""
        return self.status == "pending"
    
    def get_duration_seconds(self) -> Optional[float]:
        """Get execution duration in seconds."""
        if self.duration_ms is not None:
            return self.duration_ms / 1000.0
        return None
    
    def can_retry(self, max_retries: int = 3) -> bool:
        """Check if execution can be retried.
        
        Args:
            max_retries: Maximum number of retry attempts allowed
            
        Returns:
            True if execution can be retried, False otherwise
        """
        return self.is_failed() and self.retry_count < max_retries
    
    @classmethod
    def create_new(cls, action_id: ActionId, event_id: Optional[EventId] = None, 
                   event_type: str = "", event_data: Optional[Dict[str, Any]] = None,
                   **kwargs) -> "ActionExecution":
        """Create a new action execution with UUIDv7 compliance.
        
        This factory method ensures all new executions use UUIDv7 for better
        database performance and time-ordering.
        
        Args:
            action_id: ID of the action being executed
            event_id: ID of the triggering event (optional)
            event_type: Type of the triggering event
            event_data: Data from the triggering event
            **kwargs: Additional fields (execution_context, etc.)
        """
        return cls(
            action_id=action_id,
            event_id=event_id,
            event_type=event_type,
            event_data=event_data or {},
            **kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert execution to dictionary for serialization (matches database schema)."""
        return {
            "id": str(self.id.value),
            "action_id": str(self.action_id.value),
            "event_id": str(self.event_id.value) if self.event_id else None,
            "event_type": self.event_type,
            "event_data": self.event_data,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "result": self.result,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "execution_context": self.execution_context,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionExecution":
        """Create ActionExecution from dictionary (database row).
        
        Args:
            data: Dictionary with execution data (typically from database)
            
        Returns:
            ActionExecution instance
        """
        from uuid import UUID
        
        # Convert string IDs back to value objects (UUIDs should be UUIDv7 from database)
        execution_id = ActionId(UUID(data["id"]))
        action_id = ActionId(UUID(data["action_id"]))
        event_id = EventId(UUID(data["event_id"])) if data.get("event_id") else None
        
        # Parse datetime fields
        started_at = datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
        completed_at = datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        created_at = datetime.fromisoformat(data["created_at"])
        
        return cls(
            id=execution_id,
            action_id=action_id,
            event_id=event_id,
            event_type=data.get("event_type", ""),
            event_data=data.get("event_data", {}),
            status=data.get("status", "pending"),
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=data.get("duration_ms"),
            result=data.get("result"),
            error_message=data.get("error_message"),
            retry_count=data.get("retry_count", 0),
            execution_context=data.get("execution_context", {}),
            created_at=created_at,
        )