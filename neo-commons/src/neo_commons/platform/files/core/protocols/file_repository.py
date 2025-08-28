"""File repository protocol.

ONLY file metadata storage contract - defines interface for file metadata
repository implementations with async support.

Following maximum separation architecture - one file = one purpose.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from typing_extensions import Protocol, runtime_checkable

from ..entities.file_metadata import FileMetadata
from ..entities.upload_session import UploadSession
from ..entities.file_version import FileVersion
from ..entities.file_permission import FilePermission
from ..value_objects.file_id import FileId
from ..value_objects.upload_session_id import UploadSessionId
from ..value_objects.file_path import FilePath


@runtime_checkable
class FileRepository(Protocol):
    """File repository protocol.
    
    Defines interface for file metadata storage implementations with support for:
    - File metadata CRUD operations
    - Upload session management
    - File version tracking
    - Permission management
    - Path-based operations
    - Tenant isolation
    - Batch operations for efficiency
    """
    
    # File metadata operations
    async def create_file(self, file_metadata: FileMetadata) -> FileMetadata:
        """Create new file metadata record.
        
        Returns the created file with any generated fields populated.
        Raises error if file with same ID already exists.
        """
        ...
    
    async def get_file_by_id(self, file_id: FileId, tenant_id: str) -> Optional[FileMetadata]:
        """Get file metadata by ID.
        
        Returns None if file doesn't exist or doesn't belong to tenant.
        Enforces tenant isolation.
        """
        ...
    
    async def get_file_by_path(self, file_path: FilePath, tenant_id: str) -> Optional[FileMetadata]:
        """Get file metadata by path.
        
        Returns None if file doesn't exist or doesn't belong to tenant.
        Enforces tenant isolation.
        """
        ...
    
    async def update_file(self, file_metadata: FileMetadata) -> FileMetadata:
        """Update existing file metadata.
        
        Returns updated file metadata.
        Raises error if file doesn't exist.
        """
        ...
    
    async def delete_file(self, file_id: FileId, tenant_id: str) -> bool:
        """Delete file metadata by ID.
        
        Returns True if file existed and was deleted.
        Returns False if file didn't exist.
        Enforces tenant isolation.
        """
        ...
    
    async def list_files(
        self, 
        tenant_id: str,
        folder_path: Optional[FilePath] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[FileMetadata]:
        """List files in tenant/folder.
        
        Returns paginated list of files.
        If folder_path is None, lists all tenant files.
        Enforces tenant isolation.
        """
        ...
    
    async def search_files(
        self,
        tenant_id: str,
        query: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[FileMetadata]:
        """Search files by name/content.
        
        Returns paginated list of matching files.
        Enforces tenant isolation.
        """
        ...
    
    # Upload session operations
    async def create_upload_session(self, session: UploadSession) -> UploadSession:
        """Create new upload session.
        
        Returns the created session with any generated fields populated.
        """
        ...
    
    async def get_upload_session(
        self, 
        session_id: UploadSessionId, 
        tenant_id: str
    ) -> Optional[UploadSession]:
        """Get upload session by ID.
        
        Returns None if session doesn't exist or doesn't belong to tenant.
        Enforces tenant isolation.
        """
        ...
    
    async def update_upload_session(self, session: UploadSession) -> UploadSession:
        """Update existing upload session.
        
        Returns updated session.
        Raises error if session doesn't exist.
        """
        ...
    
    async def complete_upload_session(
        self, 
        session_id: UploadSessionId, 
        tenant_id: str
    ) -> bool:
        """Mark upload session as completed.
        
        Returns True if session was updated successfully.
        Enforces tenant isolation.
        """
        ...
    
    async def delete_upload_session(
        self, 
        session_id: UploadSessionId, 
        tenant_id: str
    ) -> bool:
        """Delete upload session by ID.
        
        Returns True if session existed and was deleted.
        Enforces tenant isolation.
        """
        ...
    
    # File version operations
    async def create_file_version(self, version: FileVersion) -> FileVersion:
        """Create new file version record.
        
        Returns the created version with any generated fields populated.
        """
        ...
    
    async def get_file_versions(
        self, 
        file_id: FileId, 
        tenant_id: str
    ) -> List[FileVersion]:
        """Get all versions of a file.
        
        Returns list ordered by version number (newest first).
        Enforces tenant isolation.
        """
        ...
    
    async def get_file_version(
        self, 
        file_id: FileId, 
        version_number: int, 
        tenant_id: str
    ) -> Optional[FileVersion]:
        """Get specific file version.
        
        Returns None if version doesn't exist.
        Enforces tenant isolation.
        """
        ...
    
    # Permission operations
    async def create_file_permission(self, permission: FilePermission) -> FilePermission:
        """Create new file permission.
        
        Returns the created permission with any generated fields populated.
        """
        ...
    
    async def get_file_permissions(
        self, 
        file_id: FileId, 
        tenant_id: str
    ) -> List[FilePermission]:
        """Get all permissions for a file.
        
        Returns list of permissions.
        Enforces tenant isolation.
        """
        ...
    
    async def check_file_permission(
        self,
        file_id: FileId,
        user_id: str,
        permission: str,
        tenant_id: str
    ) -> bool:
        """Check if user has specific permission on file.
        
        Returns True if user has the permission.
        Enforces tenant isolation.
        """
        ...
    
    async def delete_file_permission(
        self,
        file_id: FileId,
        user_id: str,
        tenant_id: str
    ) -> bool:
        """Delete file permission for user.
        
        Returns True if permission existed and was deleted.
        Enforces tenant isolation.
        """
        ...
    
    # Batch operations
    async def get_files_by_ids(
        self, 
        file_ids: List[FileId], 
        tenant_id: str
    ) -> List[FileMetadata]:
        """Get multiple files by IDs.
        
        Returns list of files (excludes non-existent ones).
        More efficient than individual get calls.
        Enforces tenant isolation.
        """
        ...
    
    async def delete_files(
        self, 
        file_ids: List[FileId], 
        tenant_id: str
    ) -> Dict[FileId, bool]:
        """Delete multiple files by IDs.
        
        Returns dictionary mapping file IDs to deletion status.
        Enforces tenant isolation.
        """
        ...
    
    # Storage statistics
    async def get_storage_usage(self, tenant_id: str) -> Dict[str, Any]:
        """Get storage usage statistics for tenant.
        
        Returns dictionary with metrics like:
        - total_files: Total number of files
        - total_size_bytes: Total storage used in bytes
        - file_types: Breakdown by MIME type
        - largest_files: List of largest files
        """
        ...
    
    async def get_file_count(self, tenant_id: str) -> int:
        """Get total file count for tenant."""
        ...
    
    # Health and monitoring
    async def ping(self) -> bool:
        """Health check - verify repository is responsive.
        
        Returns True if repository is healthy and responsive.
        """
        ...