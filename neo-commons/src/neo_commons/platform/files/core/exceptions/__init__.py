"""File management core exceptions.

Domain-specific exceptions for file management operations following maximum separation architecture.
Each exception represents a specific error condition that can occur during file operations.

Following maximum separation architecture - one file = one purpose.
"""

from .file_not_found import FileNotFound
from .storage_quota_exceeded import StorageQuotaExceeded
from .invalid_file_type import InvalidFileType
from .upload_failed import UploadFailed
from .permission_denied import PermissionDenied
from .virus_detected import VirusDetected

__all__ = [
    "FileNotFound",
    "StorageQuotaExceeded", 
    "InvalidFileType",
    "UploadFailed",
    "PermissionDenied",
    "VirusDetected",
]