"""Action ID value object for platform events infrastructure.

Moved from core/value_objects/identifiers.py following maximum separation architecture.
Pure platform infrastructure - used by all business features.
"""

from dataclasses import dataclass
from uuid import UUID

from .....utils import generate_uuid_v7


@dataclass(frozen=True)
class ActionId:
    """Event action identifier value object with UUIDv7 support."""
    value: UUID
    
    def __post_init__(self):
        if not isinstance(self.value, UUID):
            try:
                object.__setattr__(self, 'value', UUID(self.value))
            except (ValueError, TypeError):
                raise ValueError(f"ActionId must be a valid UUID, got: {self.value}")
    
    @classmethod
    def generate(cls) -> 'ActionId':
        """Generate a new ActionId using UUIDv7 for time-ordering."""
        return cls(generate_uuid_v7())
    
    def __str__(self) -> str:
        """String representation."""
        return str(self.value)
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return f"ActionId(value={self.value!r})"