"""Aggregate reference value object for linking events to entities."""

from dataclasses import dataclass
from uuid import UUID
from typing import Union


@dataclass(frozen=True)
class AggregateReference:
    """Reference to the aggregate that triggered an event."""
    aggregate_id: UUID
    aggregate_type: str
    
    def __post_init__(self):
        # Validate aggregate_id is UUID
        if not isinstance(self.aggregate_id, UUID):
            try:
                object.__setattr__(self, 'aggregate_id', UUID(str(self.aggregate_id)))
            except (ValueError, TypeError):
                raise ValueError(f"aggregate_id must be a valid UUID, got: {self.aggregate_id}")
        
        # Validate aggregate_type is non-empty string
        if not isinstance(self.aggregate_type, str) or not self.aggregate_type.strip():
            raise ValueError("aggregate_type must be a non-empty string")
        
        # Normalize aggregate_type to lowercase
        object.__setattr__(self, 'aggregate_type', self.aggregate_type.strip().lower())
    
    @classmethod
    def create(cls, aggregate_id: Union[str, UUID], aggregate_type: str) -> 'AggregateReference':
        """Create aggregate reference with validation."""
        return cls(
            aggregate_id=UUID(str(aggregate_id)) if not isinstance(aggregate_id, UUID) else aggregate_id,
            aggregate_type=aggregate_type
        )
    
    def __str__(self) -> str:
        return f"{self.aggregate_type}:{self.aggregate_id}"
    
    def __repr__(self) -> str:
        return f"AggregateReference(aggregate_id={self.aggregate_id!r}, aggregate_type={self.aggregate_type!r})"