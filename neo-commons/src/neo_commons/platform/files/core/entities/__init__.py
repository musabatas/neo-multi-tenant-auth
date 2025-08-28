"""File management entities.

Domain entities representing core business objects in the file management system.
Each entity is responsible for its own business logic and state management.

Following maximum separation architecture - one entity per file.
"""

from .file_metadata import FileMetadata
from .upload_session import UploadSession
from .file_version import FileVersion
from .file_permission import FilePermission

__all__ = [
    "FileMetadata",
    "UploadSession", 
    "FileVersion",
    "FilePermission",
]