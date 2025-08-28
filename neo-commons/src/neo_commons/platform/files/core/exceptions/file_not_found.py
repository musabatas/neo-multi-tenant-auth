"""File not found exception for file management platform infrastructure.

ONLY file not found - represents when a requested file cannot be located
in the storage system or database.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Any, Dict, Optional

from .....core.exceptions import ResourceNotFoundError
from ..value_objects import FileId, FilePath


class FileNotFound(ResourceNotFoundError):
    """Raised when a requested file cannot be found.
    
    This exception represents failures when attempting to locate files
    in either the storage system or database metadata.
    """
    
    def __init__(
        self,
        message: str,
        file_id: Optional[FileId] = None,
        file_path: Optional[FilePath] = None,
        storage_key: Optional[str] = None,
        tenant_id: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize file not found exception.
        
        Args:
            message: Human-readable error message
            file_id: ID of the file that was not found
            file_path: Path of the file that was not found
            storage_key: Storage key that was not found
            tenant_id: Tenant context for multi-tenant isolation
            error_code: Specific error code for the failure
            details: Additional details about the failure
        """
        # Build enhanced details
        enhanced_details = details or {}
        if file_id:
            enhanced_details["file_id"] = str(file_id)
        if file_path:
            enhanced_details["file_path"] = str(file_path)
        if storage_key:
            enhanced_details["storage_key"] = storage_key
        if tenant_id:
            enhanced_details["tenant_id"] = tenant_id
            
        super().__init__(
            message=message,
            error_code=error_code or "FILE_NOT_FOUND",
            details=enhanced_details
        )
        
        # Store file-specific fields
        self.file_id = file_id
        self.file_path = file_path
        self.storage_key = storage_key
        self.tenant_id = tenant_id