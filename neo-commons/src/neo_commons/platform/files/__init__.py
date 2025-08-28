"""File management platform module.

Enterprise-grade file management feature for neo-commons following maximum 
separation architecture patterns.

Provides:
- Multi-storage support (local, S3)
- Chunked/resumable uploads
- Fine-grained permissions
- Virus scanning integration
- Thumbnail generation
- Storage quota management
"""

# Only import implemented components
from .core.entities import *
from .core.value_objects import *
# from .core.events import *  # TODO: Implement events
from .core.exceptions import *  
from .core.protocols import *

__all__ = [
    # Entities
    "FileMetadata",
    "UploadSession", 
    "FileVersion",
    "FilePermission",
    
    # Value Objects
    "FileId",
    "FilePath",
    "FileSize",
    "MimeType",
    "StorageProvider",
    "UploadSessionId",
    "Checksum",
    "StorageKey",
    
    # Events (TODO)
    # "FileUploaded",
    # "FileDeleted",
    # "FileMoved",
    # "UploadFailed",
    # "VirusScanCompleted",
    
    # Exceptions
    "FileNotFound",
    "StorageQuotaExceeded",
    "InvalidFileType",
    "UploadFailed",
    "PermissionDenied",
    "VirusDetected",
    
    # Protocols
    "FileRepository",
    "StorageProviderProtocol",
    "VirusScanner",
    "ThumbnailGenerator",
    "UploadCoordinator",
]