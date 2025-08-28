"""Get file metadata query.

ONLY metadata retrieval - handles file information lookup
with permission validation and comprehensive details.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from ...core.protocols.file_repository import FileRepository
from ...core.value_objects.file_id import FileId
from ...core.exceptions.file_not_found import FileNotFound
from ...core.exceptions.permission_denied import PermissionDenied


@dataclass
class GetFileMetadataData:
    """Data required to get file metadata."""
    
    # File identification
    file_id: str
    
    # Request context
    user_id: str
    tenant_id: str
    
    # Query options
    include_versions: bool = False
    include_permissions: bool = False
    include_shares: bool = False
    include_statistics: bool = False
    
    # Optional context
    request_id: Optional[str] = None


@dataclass 
class FileMetadataInfo:
    """File metadata information."""
    
    file_id: str
    filename: str
    original_filename: str
    file_path: str
    file_size_bytes: int
    file_size_formatted: str
    content_type: str
    storage_provider: str
    storage_key: str
    checksum: str
    checksum_type: str
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime]
    accessed_at: Optional[datetime]
    
    # User information
    created_by: str
    updated_by: Optional[str]
    
    # Organization
    tenant_id: str
    organization_id: Optional[str]
    team_id: Optional[str]
    
    # Status
    is_deleted: bool
    virus_scan_status: str
    upload_session_id: Optional[str]
    
    # Content
    description: Optional[str]
    tags: Dict[str, str]
    
    # Optional extended information
    versions: Optional[list] = None
    permissions: Optional[list] = None
    shares: Optional[list] = None
    statistics: Optional[dict] = None


@dataclass 
class GetFileMetadataResult:
    """Result of file metadata query."""
    
    success: bool
    file_metadata: Optional[FileMetadataInfo] = None
    query_duration_ms: int = 0
    
    # Error information
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class GetFileMetadataQuery:
    """Query to get file metadata.
    
    Handles file metadata retrieval including:
    - File existence validation
    - Permission checking for read access
    - Comprehensive metadata collection
    - Optional extended information (versions, permissions)
    - Performance tracking
    - Error handling with proper codes
    """
    
    def __init__(self, file_repository: FileRepository):
        """Initialize get file metadata query.
        
        Args:
            file_repository: Repository for file metadata
        """
        self._file_repository = file_repository
    
    async def execute(self, data: GetFileMetadataData) -> GetFileMetadataResult:
        """Execute file metadata retrieval.
        
        Args:
            data: Metadata query data and options
            
        Returns:
            Result containing file metadata or error
            
        Raises:
            FileNotFound: If file doesn't exist
            PermissionDenied: If user lacks read permission
        """
        start_time = datetime.utcnow()
        
        try:
            # Validate and get file
            file_id = FileId.from_string(data.file_id)
            file_metadata = await self._file_repository.get_file(file_id)
            
            if not file_metadata:
                return GetFileMetadataResult(
                    success=False,
                    error_code="FileNotFound",
                    error_message=f"File with ID {data.file_id} not found"
                )
            
            # Check if file is deleted (unless user has special permissions)
            if file_metadata.is_deleted:
                # TODO: Check if user has permission to see deleted files
                return GetFileMetadataResult(
                    success=False,
                    error_code="FileDeleted",
                    error_message="File has been deleted"
                )
            
            # Validate tenant isolation
            if file_metadata.tenant_id != data.tenant_id:
                return GetFileMetadataResult(
                    success=False,
                    error_code="PermissionDenied",
                    error_message="File belongs to different tenant"
                )
            
            # Check read permissions
            if not await self._can_read_file(file_metadata, data.user_id):
                return GetFileMetadataResult(
                    success=False,
                    error_code="PermissionDenied",
                    error_message="User lacks permission to access this file"
                )
            
            # Build basic metadata info
            metadata_info = FileMetadataInfo(
                file_id=str(file_metadata.id.value),
                filename=file_metadata.filename,
                original_filename=file_metadata.original_filename,
                file_path=str(file_metadata.file_path.value),
                file_size_bytes=file_metadata.file_size.bytes,
                file_size_formatted=str(file_metadata.file_size),
                content_type=file_metadata.content_type.value,
                storage_provider=str(file_metadata.storage_provider.value),
                storage_key=file_metadata.storage_key.value,
                checksum=file_metadata.checksum.value,
                checksum_type=file_metadata.checksum.algorithm,
                created_at=file_metadata.created_at,
                updated_at=file_metadata.updated_at,
                accessed_at=file_metadata.accessed_at,
                created_by=file_metadata.created_by,
                updated_by=file_metadata.updated_by,
                tenant_id=file_metadata.tenant_id,
                organization_id=file_metadata.organization_id,
                team_id=file_metadata.team_id,
                is_deleted=file_metadata.is_deleted,
                virus_scan_status=file_metadata.virus_scan_status,
                upload_session_id=str(file_metadata.upload_session_id.value) if file_metadata.upload_session_id else None,
                description=file_metadata.description,
                tags=file_metadata.tags
            )
            
            # Add optional extended information
            if data.include_versions:
                metadata_info.versions = await self._get_file_versions(file_id)
            
            if data.include_permissions:
                metadata_info.permissions = await self._get_file_permissions(file_id)
            
            if data.include_shares:
                metadata_info.shares = await self._get_file_shares(file_id)
            
            if data.include_statistics:
                metadata_info.statistics = await self._get_file_statistics(file_id)
            
            # Update last accessed time (optional - might be performance impact)
            # await self._update_last_accessed(file_metadata, data.user_id)
            
            # Calculate duration
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return GetFileMetadataResult(
                success=True,
                file_metadata=metadata_info,
                query_duration_ms=duration_ms
            )
                
        except Exception as e:
            # Calculate duration for error case
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return GetFileMetadataResult(
                success=False,
                query_duration_ms=duration_ms,
                error_code="QueryFailed",
                error_message=f"Unexpected error during metadata query: {str(e)}"
            )
    
    async def _can_read_file(self, file_metadata, user_id: str) -> bool:
        """Check if user can read file metadata."""
        # Basic permission check - owner can always read
        if file_metadata.created_by == user_id:
            return True
        
        # TODO: Implement full RBAC permission checking
        # This would check:
        # - User roles and permissions
        # - Team membership and file sharing
        # - File-specific permissions
        # - Organization-level policies
        
        return False
    
    async def _get_file_versions(self, file_id: FileId) -> list:
        """Get file version history."""
        try:
            versions = await self._file_repository.get_file_versions(file_id)
            return [
                {
                    "version_number": version.version_number,
                    "file_size": version.file_size.bytes,
                    "checksum": version.checksum.value,
                    "created_at": version.created_at.isoformat(),
                    "created_by": version.created_by,
                    "change_comment": version.change_comment
                }
                for version in versions
            ]
        except Exception:
            return []
    
    async def _get_file_permissions(self, file_id: FileId) -> list:
        """Get file permissions."""
        try:
            # TODO: Implement permission retrieval
            return []
        except Exception:
            return []
    
    async def _get_file_shares(self, file_id: FileId) -> list:
        """Get file sharing information."""
        try:
            # TODO: Implement share retrieval
            return []
        except Exception:
            return []
    
    async def _get_file_statistics(self, file_id: FileId) -> dict:
        """Get file usage statistics."""
        try:
            # TODO: Implement statistics retrieval
            return {
                "download_count": 0,
                "view_count": 0,
                "share_count": 0,
                "last_download": None,
                "last_view": None
            }
        except Exception:
            return {}


# Factory function for dependency injection
def create_get_file_metadata_query(file_repository: FileRepository) -> GetFileMetadataQuery:
    """Create get file metadata query."""
    return GetFileMetadataQuery(file_repository)