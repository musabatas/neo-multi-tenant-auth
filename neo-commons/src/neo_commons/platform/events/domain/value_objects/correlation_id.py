"""Correlation ID value object for event tracking."""

from dataclasses import dataclass
from uuid import UUID
from typing import Optional
from ....utils import generate_uuid_v7


@dataclass(frozen=True)
class CorrelationId:
    """Correlation ID to group related events together."""
    value: UUID
    
    def __post_init__(self):
        if not isinstance(self.value, UUID):
            try:
                object.__setattr__(self, 'value', UUID(str(self.value)))
            except (ValueError, TypeError):
                raise ValueError(f"CorrelationId must be a valid UUID, got: {self.value}")
    
    @classmethod
    def generate(cls) -> 'CorrelationId':
        """Generate a new CorrelationId using UUIDv7."""
        return cls(generate_uuid_v7())
    
    @classmethod
    def from_optional(cls, value: Optional[str]) -> Optional['CorrelationId']:
        """Create from optional string value."""
        if value is None:
            return None
        return cls(UUID(value))
    
    def __str__(self) -> str:
        return str(self.value)
    
    def __repr__(self) -> str:
        return f"CorrelationId(value={self.value!r})"