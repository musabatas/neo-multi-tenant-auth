"""Action ID value object."""

from dataclasses import dataclass
from uuid import UUID
from typing import Union

from .....utils import generate_uuid_v7, is_valid_uuid


@dataclass(frozen=True)
class ActionId:
    """
    Action ID value object.
    
    Represents a unique identifier for an action using UUIDv7.
    Provides validation and ensures immutability.
    """
    
    value: UUID
    
    def __post_init__(self):
        """Validate action ID on creation."""
        if not isinstance(self.value, UUID):
            raise TypeError(f"ActionId value must be UUID, got {type(self.value)}")
        
        if not is_valid_uuid(str(self.value)):
            raise ValueError(f"Invalid UUID format: {self.value}")
    
    @classmethod
    def generate(cls) -> 'ActionId':
        """Generate a new ActionId using UUIDv7."""
        return cls(generate_uuid_v7())
    
    @classmethod
    def from_string(cls, uuid_str: str) -> 'ActionId':
        """Create ActionId from UUID string."""
        try:
            return cls(UUID(uuid_str))
        except ValueError as e:
            raise ValueError(f"Invalid UUID string: {uuid_str}") from e
    
    def __str__(self) -> str:
        """String representation returns UUID string."""
        return str(self.value)
    
    def __hash__(self) -> int:
        """Hash based on UUID value."""
        return hash(self.value)
    
    def __eq__(self, other) -> bool:
        """Equality based on UUID value."""
        if isinstance(other, ActionId):
            return self.value == other.value
        return False