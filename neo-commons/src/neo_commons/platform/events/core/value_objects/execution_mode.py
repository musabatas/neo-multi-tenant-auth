"""Execution mode value object for platform events infrastructure.

Extracted from features/events/entities/event_action.py following maximum separation architecture.
Pure platform infrastructure - used by all business features.
"""

from enum import Enum


class ExecutionMode(Enum):
    """Action execution mode enumeration.
    
    Represents how an action should be executed:
    - SYNC: Execute synchronously (blocks event processing)
    - ASYNC: Execute asynchronously (non-blocking)
    - QUEUED: Queue for later execution
    """
    
    SYNC = "sync"      # Execute synchronously (blocks event processing)
    ASYNC = "async"    # Execute asynchronously (non-blocking)
    QUEUED = "queued"  # Queue for later execution
    
    def __str__(self) -> str:
        """String representation."""
        return self.value
    
    @property
    def is_blocking(self) -> bool:
        """Check if this execution mode blocks the calling process."""
        return self == ExecutionMode.SYNC
    
    @property
    def is_deferred(self) -> bool:
        """Check if this execution mode defers execution."""
        return self in (ExecutionMode.ASYNC, ExecutionMode.QUEUED)
    
    @property
    def requires_queue(self) -> bool:
        """Check if this execution mode requires a message queue."""
        return self == ExecutionMode.QUEUED