"""File management core events.

Domain events for file management operations following maximum separation architecture.
Each event represents a significant business event that should be trackable and auditable.

Following maximum separation architecture - one file = one purpose.
"""

from .file_uploaded import FileUploaded
from .file_deleted import FileDeleted
from .file_moved import FileMoved
from .upload_failed import UploadFailed
from .virus_scan_completed import VirusScanCompleted

__all__ = [
    "FileUploaded",
    "FileDeleted", 
    "FileMoved",
    "UploadFailed",
    "VirusScanCompleted",
]