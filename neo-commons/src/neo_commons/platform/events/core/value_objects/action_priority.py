"""Action priority value object for platform events infrastructure.

Extracted from features/events/entities/event_action.py following maximum separation architecture.
Pure platform infrastructure - used by all business features.
"""

from enum import Enum


class ActionPriority(Enum):
    """Action execution priority enumeration.
    
    Represents the priority level for action execution:
    - LOW: Low priority, execute when resources are available
    - NORMAL: Normal priority, standard execution order
    - HIGH: High priority, prioritized execution
    - CRITICAL: Critical priority, immediate execution
    """
    
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
    
    def __str__(self) -> str:
        """String representation."""
        return self.value
    
    @property
    def numeric_value(self) -> int:
        """Get numeric representation for priority ordering."""
        priority_map = {
            ActionPriority.LOW: 1,
            ActionPriority.NORMAL: 2,
            ActionPriority.HIGH: 3,
            ActionPriority.CRITICAL: 4
        }
        return priority_map[self]
    
    @property
    def is_urgent(self) -> bool:
        """Check if this priority level requires urgent processing."""
        return self in (ActionPriority.HIGH, ActionPriority.CRITICAL)