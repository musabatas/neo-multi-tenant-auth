"""Action execution ID value object for platform actions infrastructure.

Pure platform infrastructure - used by all business features.
"""

from dataclasses import dataclass
from uuid import UUID

from .....utils import generate_uuid_v7


@dataclass(frozen=True)
class ActionExecutionId:
    """Action execution identifier value object with UUIDv7 support."""
    value: UUID
    
    def __post_init__(self):
        if not isinstance(self.value, UUID):
            try:
                object.__setattr__(self, 'value', UUID(self.value))
            except (ValueError, TypeError):
                raise ValueError(f"ActionExecutionId must be a valid UUID, got: {self.value}")
    
    @classmethod
    def generate(cls) -> 'ActionExecutionId':
        """Generate a new ActionExecutionId using UUIDv7 for time-ordering."""
        return cls(generate_uuid_v7())
    
    def __str__(self) -> str:
        """String representation."""
        return str(self.value)
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return f"ActionExecutionId(value={self.value!r})"