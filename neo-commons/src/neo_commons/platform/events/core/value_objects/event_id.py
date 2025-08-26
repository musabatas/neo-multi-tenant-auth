"""Event ID value object for platform events infrastructure.

Moved from core/value_objects/identifiers.py following maximum separation architecture.
Pure platform infrastructure - used by all business features.
"""

from dataclasses import dataclass
from uuid import UUID

from .....utils import generate_uuid_v7


@dataclass(frozen=True)
class EventId:
    """Event identifier value object with UUIDv7 support."""
    value: UUID
    
    def __post_init__(self):
        if not isinstance(self.value, UUID):
            try:
                object.__setattr__(self, 'value', UUID(self.value))
            except (ValueError, TypeError):
                raise ValueError(f"EventId must be a valid UUID, got: {self.value}")
    
    @classmethod
    def generate(cls) -> 'EventId':
        """Generate a new EventId using UUIDv7 for time-ordering."""
        return cls(generate_uuid_v7())
    
    def __str__(self) -> str:
        """String representation."""
        return str(self.value)
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return f"EventId(value={self.value!r})"