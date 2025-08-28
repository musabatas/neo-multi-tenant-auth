"""Action status value object for platform events infrastructure.

Extracted from features/events/entities/event_action.py following maximum separation architecture.
Pure platform infrastructure - used by all business features.
"""

from enum import Enum


class ActionStatus(Enum):
    """Event action status enumeration.
    
    Represents the current status of an event action:
    - ACTIVE: Action is enabled and will be triggered by matching events
    - INACTIVE: Action is disabled and will not be triggered  
    - PAUSED: Action is temporarily paused but can be resumed
    - ARCHIVED: Action is archived and cannot be activated again
    """
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    ARCHIVED = "archived"
    
    def __str__(self) -> str:
        """String representation."""
        return self.value
    
    @property
    def is_executable(self) -> bool:
        """Check if action can be executed in this status."""
        return self in (ActionStatus.ACTIVE,)
    
    @property 
    def is_modifiable(self) -> bool:
        """Check if action can be modified in this status."""
        return self in (ActionStatus.ACTIVE, ActionStatus.INACTIVE, ActionStatus.PAUSED)