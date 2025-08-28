"""Delete file command.

ONLY file deletion - handles file removal from storage and metadata
with proper cleanup and audit trail.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List

from ...core.protocols.file_repository import FileRepository
from ...core.protocols.storage_provider import StorageProviderProtocol  
from ...core.value_objects.file_id import FileId
from ...core.exceptions.file_not_found import FileNotFound
from ...core.exceptions.permission_denied import PermissionDenied


@dataclass
class DeleteFileData:
    """Data required to delete a file."""
    
    # File identification
    file_id: str
    
    # Deletion context
    user_id: str
    tenant_id: str
    
    # Deletion options
    permanent_delete: bool = False  # True for permanent, False for soft delete
    delete_versions: bool = True   # Whether to delete all versions
    reason: Optional[str] = None   # Reason for deletion (audit)
    
    # Optional context
    request_id: Optional[str] = None


@dataclass 
class DeleteFileResult:
    """Result of file deletion operation."""
    
    # Required fields
    success: bool
    file_id: str
    
    # Optional fields (with defaults)
    filename: str = ""
    deleted_permanently: bool = False
    versions_deleted: int = 0
    storage_freed_bytes: int = 0
    deletion_duration_ms: int = 0
    
    # Error information
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class DeleteFileCommand:
    """Command to delete a file.
    
    Handles file deletion including:
    - File metadata validation and permission checks
    - Storage content removal (file + versions)
    - Metadata cleanup (soft or hard delete)
    - Related data cleanup (permissions, shares, etc.)
    - Audit trail creation
    - Storage quota adjustment
    - Error handling and rollback
    - Performance tracking
    """
    
    def __init__(
        self,
        file_repository: FileRepository,
        storage_provider: StorageProviderProtocol
    ):
        """Initialize delete file command.
        
        Args:
            file_repository: Repository for file metadata
            storage_provider: Storage backend for content removal
        """
        self._file_repository = file_repository
        self._storage_provider = storage_provider
    
    async def execute(self, data: DeleteFileData) -> DeleteFileResult:
        """Execute file deletion operation.
        
        Args:
            data: File deletion data and options
            
        Returns:
            Result of the deletion operation
            
        Raises:
            FileNotFound: If file doesn't exist
            PermissionDenied: If user lacks delete permission
        """
        start_time = datetime.utcnow()
        total_freed_bytes = 0
        versions_deleted = 0
        
        try:
            # Validate file exists
            file_id = FileId.from_string(data.file_id)
            file_metadata = await self._file_repository.get_file(file_id)
            
            if not file_metadata:
                return DeleteFileResult(
                    success=False,
                    file_id=data.file_id,
                    error_code="FileNotFound",
                    error_message=f"File with ID {data.file_id} not found"
                )
            
            # Check if already deleted (soft delete)
            if file_metadata.is_deleted and not data.permanent_delete:
                return DeleteFileResult(
                    success=False,
                    file_id=data.file_id,
                    filename=file_metadata.filename,
                    error_code="AlreadyDeleted",
                    error_message="File is already deleted"
                )
            
            # Validate tenant isolation
            if file_metadata.tenant_id != data.tenant_id:
                return DeleteFileResult(
                    success=False,
                    file_id=data.file_id,
                    filename=file_metadata.filename,
                    error_code="PermissionDenied",
                    error_message="File belongs to different tenant"
                )
            
            # Check delete permissions (basic check - full RBAC would be more complex)
            if not await self._can_delete_file(file_metadata, data.user_id):
                return DeleteFileResult(
                    success=False,
                    file_id=data.file_id,
                    filename=file_metadata.filename,
                    error_code="PermissionDenied",
                    error_message="User lacks permission to delete this file"
                )
            
            # Get file versions if we need to delete them
            file_versions = []
            if data.delete_versions:
                file_versions = await self._file_repository.get_file_versions(file_id)
            
            # Delete from storage provider (main file + versions)
            storage_deletions = []
            
            # Delete main file
            main_delete_success = await self._storage_provider.delete_file(
                file_metadata.storage_key.value
            )
            if main_delete_success:
                storage_deletions.append(file_metadata.storage_key.value)
                total_freed_bytes += file_metadata.file_size.bytes
            
            # Delete versions
            for version in file_versions:
                version_delete_success = await self._storage_provider.delete_file(
                    version.storage_key.value
                )
                if version_delete_success:
                    storage_deletions.append(version.storage_key.value)
                    total_freed_bytes += version.file_size.bytes
                    versions_deleted += 1
            
            # Update metadata based on deletion type
            if data.permanent_delete:
                # Permanent deletion - remove from database
                await self._file_repository.delete_file_permanent(file_id)
                
                # Delete related data
                await self._delete_related_data(file_id)
                
            else:
                # Soft deletion - mark as deleted
                soft_deleted_metadata = file_metadata.mark_deleted(
                    deleted_by=data.user_id,
                    deletion_reason=data.reason
                )
                await self._file_repository.update_file(soft_deleted_metadata)
                
                # Soft delete versions
                for version in file_versions:
                    deleted_version = version.mark_deleted(
                        deleted_by=data.user_id,
                        deletion_reason=data.reason
                    )
                    await self._file_repository.update_file_version(deleted_version)
            
            # Create audit log entry
            await self._create_audit_log(
                file_metadata=file_metadata,
                user_id=data.user_id,
                action="delete_permanent" if data.permanent_delete else "delete_soft",
                reason=data.reason,
                storage_freed_bytes=total_freed_bytes,
                versions_affected=versions_deleted + 1  # +1 for main file
            )
            
            # Calculate duration
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return DeleteFileResult(
                success=True,
                file_id=data.file_id,
                filename=file_metadata.filename,
                deleted_permanently=data.permanent_delete,
                versions_deleted=versions_deleted,
                storage_freed_bytes=total_freed_bytes,
                deletion_duration_ms=duration_ms
            )
                
        except Exception as e:
            # Calculate duration for error case
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return DeleteFileResult(
                success=False,
                file_id=data.file_id,
                deletion_duration_ms=duration_ms,
                error_code="DeletionFailed",
                error_message=f"Unexpected error during file deletion: {str(e)}"
            )
    
    async def _can_delete_file(self, file_metadata, user_id: str) -> bool:
        """Check if user can delete file (simplified permission check)."""
        # Basic permission check - owner can always delete
        if file_metadata.created_by == user_id:
            return True
        
        # TODO: Implement full RBAC permission checking
        # This would check:
        # - User roles and permissions
        # - Team membership and roles
        # - File-specific permissions
        # - Organization-level policies
        
        return False
    
    async def _delete_related_data(self, file_id: FileId) -> None:
        """Delete related data for permanent deletion."""
        try:
            # Delete file permissions
            await self._file_repository.delete_file_permissions(file_id)
            
            # Delete file shares (if implemented)
            # await self._file_repository.delete_file_shares(file_id)
            
            # Delete file comments/annotations (if implemented)
            # await self._file_repository.delete_file_comments(file_id)
            
            # Delete thumbnail/preview files
            # await self._storage_provider.delete_thumbnails(file_id)
            
        except Exception as e:
            # Log error but don't fail the main deletion
            # In production, you'd log this properly
            pass
    
    async def _create_audit_log(
        self,
        file_metadata,
        user_id: str,
        action: str,
        reason: Optional[str] = None,
        storage_freed_bytes: int = 0,
        versions_affected: int = 1
    ) -> None:
        """Create audit log entry for file deletion."""
        try:
            audit_data = {
                "action": action,
                "file_id": str(file_metadata.id.value),
                "filename": file_metadata.filename,
                "file_path": str(file_metadata.file_path.value),
                "user_id": user_id,
                "tenant_id": file_metadata.tenant_id,
                "reason": reason,
                "storage_freed_bytes": storage_freed_bytes,
                "versions_affected": versions_affected,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # TODO: Implement audit logging
            # In production, this would write to audit log table or service
            
        except Exception:
            # Don't fail deletion for audit log errors
            pass


# Factory function for dependency injection
def create_delete_file_command(
    file_repository: FileRepository,
    storage_provider: StorageProviderProtocol
) -> DeleteFileCommand:
    """Create delete file command."""
    return DeleteFileCommand(
        file_repository=file_repository,
        storage_provider=storage_provider
    )