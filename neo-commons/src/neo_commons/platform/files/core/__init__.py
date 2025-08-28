"""File management core domain layer.

Clean core containing only essential value objects, exceptions,
and shared contracts. No business logic or external dependencies.

Following maximum separation architecture - one file = one purpose.
"""

from .entities import *
from .value_objects import *
# from .events import *  # TODO: Implement events
from .exceptions import *  
from .protocols import *

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
    
    # Events (TODO: Implement later)
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