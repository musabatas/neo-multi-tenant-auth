"""Event type value object for platform events infrastructure.

Moved from core/value_objects/identifiers.py following maximum separation architecture.
Pure platform infrastructure - used by all business features.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class EventType:
    """Event type value object (e.g., 'organization.created').
    
    Represents the type of domain event with category.action format validation.
    """
    value: str
    
    def __post_init__(self):
        if not isinstance(self.value, str):
            raise ValueError("EventType must be a string")
        
        if not self.value or not self.value.strip():
            raise ValueError("EventType cannot be empty")
            
        # Event type format: category.action (e.g., organization.created)
        if '.' not in self.value or self.value.count('.') != 1:
            raise ValueError("EventType must be in format 'category.action'")
        
        # Clean and validate format
        clean_value = self.value.strip().lower()
        if not re.match(r'^[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*$', clean_value):
            raise ValueError("EventType must contain only lowercase letters, numbers, and underscores")
        
        object.__setattr__(self, 'value', clean_value)
    
    @property
    def category(self) -> str:
        """Get event category (part before the dot)."""
        return self.value.split('.')[0]
    
    @property  
    def action(self) -> str:
        """Get event action (part after the dot)."""
        return self.value.split('.')[1]
    
    def __str__(self) -> str:
        """String representation."""
        return self.value
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return f"EventType(value='{self.value}')"