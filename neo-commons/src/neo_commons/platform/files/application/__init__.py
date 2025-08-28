"""File management application layer.

Application layer containing use cases, commands, queries, and business orchestration.
This layer coordinates between the core domain and infrastructure layers.

Following maximum separation architecture - one file = one purpose.
"""

from .commands import *
from .queries import *
from .services import *
from .validators import *
from .handlers import *

__all__ = [
    # Commands (Write Operations)
    "UploadFileCommand",
    "UploadFileChunkCommand", 
    "CompleteUploadCommand",
    "DeleteFileCommand",
    "MoveFileCommand",
    "CopyFileCommand",
    "UpdateMetadataCommand",
    "CreateFolderCommand",
    "SetFilePermissionsCommand",
    
    # Queries (Read Operations)
    "GetFileMetadataQuery",
    "GetFileContentQuery",
    "ListFilesQuery",
    "SearchFilesQuery",
    "GetUploadUrlQuery",
    "GetUploadProgressQuery",
    "GetFileVersionsQuery",
    "CheckFilePermissionsQuery",
    
    # Services
    "FileManager",
    "UploadCoordinatorService",
    "StorageManager",
    "PermissionManager",
    "CleanupService",
    "QuotaManager",
    "VirusScanService",
    
    # Validators
    "FileTypeValidator",
    "FileSizeValidator",
    "FilePathValidator",
    "QuotaValidator",
    "PermissionValidator",
    "UploadValidator",
    
    # Event Handlers
    "FileUploadedHandler",
    "FileDeletedHandler",
    "VirusScanHandler",
    "QuotaExceededHandler",
    "ThumbnailHandler",
]