"""File management core protocols.

Domain contracts for file management operations following maximum separation architecture.
Each protocol represents an abstraction interface for external dependencies.

Following maximum separation architecture - one file = one purpose.
"""

from .file_repository import FileRepository
from .storage_provider import StorageProviderProtocol  
from .virus_scanner import VirusScanner
from .thumbnail_generator import ThumbnailGenerator
from .upload_coordinator import UploadCoordinator

__all__ = [
    "FileRepository",
    "StorageProviderProtocol", 
    "VirusScanner",
    "ThumbnailGenerator",
    "UploadCoordinator",
]