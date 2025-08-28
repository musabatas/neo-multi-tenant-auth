"""Upload session identifier value object.

ONLY upload session identifier - represents unique upload session ID using 
UUIDv7 for time-ordered performance benefits in database indexes.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from typing import Union
from uuid import UUID

from .....utils import generate_uuid_v7


@dataclass(frozen=True)
class UploadSessionId:
    """Upload session identifier value object.
    
    Represents a unique upload session identifier using UUIDv7 for better
    database performance through time-ordered indexing. Used for tracking
    multi-part uploads, chunked uploads, and resumable upload operations.
    
    Immutable and hashable for use as dictionary keys and in sets.
    """
    
    value: UUID
    
    def __post_init__(self):
        """Validate upload session ID format."""
        if not isinstance(self.value, UUID):
            raise ValueError(f"UploadSessionId must be a UUID, got {type(self.value).__name__}")
    
    @classmethod
    def generate(cls) -> 'UploadSessionId':
        """Generate a new time-ordered upload session ID using UUIDv7."""
        return cls(UUID(generate_uuid_v7()))
    
    @classmethod 
    def from_string(cls, value: str) -> 'UploadSessionId':
        """Create UploadSessionId from string representation."""
        try:
            uuid_value = UUID(value)
            return cls(uuid_value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid upload session ID format: {value}") from e
    
    @classmethod
    def from_uuid(cls, value: UUID) -> 'UploadSessionId':
        """Create UploadSessionId from UUID object."""
        return cls(value)
    
    def to_string(self) -> str:
        """Get string representation of upload session ID."""
        return str(self.value)
    
    def __str__(self) -> str:
        """String representation for logging and display."""
        return self.to_string()
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"UploadSessionId('{self.value}')"