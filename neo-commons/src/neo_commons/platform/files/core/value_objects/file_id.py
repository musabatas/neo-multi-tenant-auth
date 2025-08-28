"""File identifier value object.

ONLY file identifier - represents unique file ID using UUIDv7 for time-ordered 
performance benefits in database indexes.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from typing import Union
from uuid import UUID

from .....utils import generate_uuid_v7


@dataclass(frozen=True)
class FileId:
    """File identifier value object.
    
    Represents a unique file identifier using UUIDv7 for better database
    performance through time-ordered indexing. Used for all file entities
    including metadata, versions, and permissions.
    
    Immutable and hashable for use as dictionary keys and in sets.
    """
    
    value: UUID
    
    def __post_init__(self):
        """Validate file ID format."""
        if not isinstance(self.value, UUID):
            raise ValueError(f"FileId must be a UUID, got {type(self.value).__name__}")
    
    @classmethod
    def generate(cls) -> 'FileId':
        """Generate a new time-ordered file ID using UUIDv7."""
        return cls(UUID(generate_uuid_v7()))
    
    @classmethod 
    def from_string(cls, value: str) -> 'FileId':
        """Create FileId from string representation."""
        try:
            uuid_value = UUID(value)
            return cls(uuid_value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid file ID format: {value}") from e
    
    @classmethod
    def from_uuid(cls, value: UUID) -> 'FileId':
        """Create FileId from UUID object."""
        return cls(value)
    
    def to_string(self) -> str:
        """Get string representation of file ID."""
        return str(self.value)
    
    def __str__(self) -> str:
        """String representation for logging and display."""
        return self.to_string()
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"FileId('{self.value}')"