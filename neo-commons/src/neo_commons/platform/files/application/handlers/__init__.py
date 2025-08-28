"""File management event handlers.

Event handlers for file management operations following maximum separation architecture.
Each handler processes exactly one event type with specific business logic.

Following maximum separation architecture - one file = one purpose.
"""

from .file_uploaded_handler import FileUploadedHandler
from .file_deleted_handler import FileDeletedHandler
from .virus_scan_handler import VirusScanHandler
from .quota_exceeded_handler import QuotaExceededHandler
from .thumbnail_handler import ThumbnailHandler

__all__ = [
    # Event Handlers
    "FileUploadedHandler",
    "FileDeletedHandler", 
    "VirusScanHandler",
    "QuotaExceededHandler",
    "ThumbnailHandler",
]