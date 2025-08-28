"""Action condition value object for platform events infrastructure.

This module defines the ActionCondition value object that represents immutable conditions
for event action execution with evaluation logic.

Moved from entities/ to value_objects/ following the DEVELOPMENT_PLAN.md architecture.
Pure platform infrastructure - used by all business features.
"""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class ActionCondition:
    """Immutable value object representing a condition for event action execution.
    
    Evaluates conditions against event data with support for nested field access 
    and multiple comparison operators. Follows value object pattern with immutability.
    """
    
    field: str
    operator: str  
    value: Any
    
    def __post_init__(self):
        """Post-initialization validation."""
        if not self.field or not self.field.strip():
            raise ValueError("Field cannot be empty")
            
        valid_operators = {
            "equals", "contains", "gt", "lt", "in", "not_in", 
            "exists", "not_exists"
        }
        
        if self.operator not in valid_operators:
            raise ValueError(f"Invalid operator: {self.operator}. Must be one of {valid_operators}")
    
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
            # This should never happen due to __post_init__ validation
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
        """Convert condition to dictionary for serialization."""
        return {
            "field": self.field,
            "operator": self.operator,
            "value": self.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionCondition":
        """Create condition from dictionary.
        
        Args:
            data: Dictionary with field, operator, value keys
            
        Returns:
            ActionCondition instance
        """
        return cls(
            field=data["field"],
            operator=data["operator"],
            value=data["value"]
        )
    
    @classmethod
    def equals(cls, field: str, value: Any) -> "ActionCondition":
        """Create equals condition convenience method."""
        return cls(field=field, operator="equals", value=value)
    
    @classmethod 
    def contains(cls, field: str, value: Any) -> "ActionCondition":
        """Create contains condition convenience method."""
        return cls(field=field, operator="contains", value=value)
    
    @classmethod
    def exists(cls, field: str) -> "ActionCondition":
        """Create exists condition convenience method."""
        return cls(field=field, operator="exists", value=True)
    
    @classmethod
    def not_exists(cls, field: str) -> "ActionCondition":
        """Create not_exists condition convenience method."""
        return cls(field=field, operator="not_exists", value=True)