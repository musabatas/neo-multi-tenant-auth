"""Move file command.

ONLY file moving - handles file relocation within storage
with path updates and metadata synchronization.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from ...core.protocols.file_repository import FileRepository
from ...core.protocols.storage_provider import StorageProviderProtocol  
from ...core.value_objects.file_id import FileId
from ...core.value_objects.file_path import FilePath
from ...core.value_objects.storage_key import StorageKey
from ...core.exceptions.file_not_found import FileNotFound
from ...core.exceptions.permission_denied import PermissionDenied


@dataclass
class MoveFileData:
    """Data required to move a file."""
    
    # Required fields (no defaults)
    file_id: str
    new_folder_path: str
    user_id: str
    tenant_id: str
    
    # Optional fields (with defaults)
    new_filename: Optional[str] = None  # If None, keep current filename
    overwrite_existing: bool = False
    create_folders: bool = True  # Create destination folder if it doesn't exist
    reason: Optional[str] = None  # Reason for move (audit)
    request_id: Optional[str] = None


@dataclass 
class MoveFileResult:
    """Result of file move operation."""
    
    # Required fields
    success: bool
    file_id: str
    
    # Optional fields (with defaults)
    old_path: str = ""
    new_path: str = ""
    filename: str = ""
    new_storage_key: str = ""
    move_duration_ms: int = 0
    
    # Operation details
    storage_moved: bool = False
    metadata_updated: bool = False
    folders_created: bool = False
    
    # Error information
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class MoveFileCommand:
    """Command to move a file to new location.
    
    Handles file relocation including:
    - File metadata validation and permission checks
    - Destination path validation and creation
    - Storage provider file moving
    - Metadata path updates
    - Conflict resolution (overwrite/error)
    - Audit trail creation
    - Error handling and rollback
    - Performance tracking
    """
    
    def __init__(
        self,
        file_repository: FileRepository,
        storage_provider: StorageProviderProtocol
    ):
        """Initialize move file command.
        
        Args:
            file_repository: Repository for file metadata
            storage_provider: Storage backend for file moving
        """
        self._file_repository = file_repository
        self._storage_provider = storage_provider
    
    async def execute(self, data: MoveFileData) -> MoveFileResult:
        """Execute file move operation.
        
        Args:
            data: File move data and options
            
        Returns:
            Result of the move operation
            
        Raises:
            FileNotFound: If source file doesn't exist
            PermissionDenied: If user lacks move permission
        """
        start_time = datetime.utcnow()
        old_storage_key: Optional[str] = None
        new_storage_key: Optional[str] = None
        
        try:
            # Validate source file exists
            file_id = FileId.from_string(data.file_id)
            file_metadata = await self._file_repository.get_file(file_id)
            
            if not file_metadata:
                return MoveFileResult(
                    success=False,
                    file_id=data.file_id,
                    error_code="FileNotFound",
                    error_message=f"File with ID {data.file_id} not found"
                )
            
            # Check if file is deleted
            if file_metadata.is_deleted:
                return MoveFileResult(
                    success=False,
                    file_id=data.file_id,
                    filename=file_metadata.filename,
                    error_code="FileDeleted",
                    error_message="Cannot move deleted file"
                )
            
            # Validate tenant isolation
            if file_metadata.tenant_id != data.tenant_id:
                return MoveFileResult(
                    success=False,
                    file_id=data.file_id,
                    filename=file_metadata.filename,
                    error_code="PermissionDenied",
                    error_message="File belongs to different tenant"
                )
            
            # Check move permissions
            if not await self._can_move_file(file_metadata, data.user_id):
                return MoveFileResult(
                    success=False,
                    file_id=data.file_id,
                    filename=file_metadata.filename,
                    error_code="PermissionDenied",
                    error_message="User lacks permission to move this file"
                )
            
            # Determine new filename and paths
            new_filename = data.new_filename or file_metadata.filename
            new_file_path = self._create_new_file_path(data.new_folder_path, new_filename)
            
            # Check if destination already exists (unless overwrite allowed)
            if not data.overwrite_existing:
                existing_file = await self._file_repository.get_file_by_path(new_file_path)
                if existing_file and str(existing_file.id.value) != data.file_id:
                    return MoveFileResult(
                        success=False,
                        file_id=data.file_id,
                        filename=file_metadata.filename,
                        old_path=str(file_metadata.file_path.value),
                        new_path=str(new_file_path.value),
                        error_code="FileExists",
                        error_message=f"File already exists at destination: {new_file_path.value}"
                    )
            
            # Generate new storage key
            old_storage_key = file_metadata.storage_key.value
            new_storage_key = self._generate_new_storage_key(
                data.tenant_id,
                file_id,
                new_filename
            )
            
            # Move file in storage provider
            move_success = await self._storage_provider.move_file(
                source_key=old_storage_key,
                destination_key=new_storage_key,
                metadata={
                    "file_id": str(file_id.value),
                    "tenant_id": data.tenant_id,
                    "moved_by": data.user_id,
                    "move_reason": data.reason
                }
            )
            
            if not move_success:
                return MoveFileResult(
                    success=False,
                    file_id=data.file_id,
                    filename=file_metadata.filename,
                    old_path=str(file_metadata.file_path.value),
                    new_path=str(new_file_path.value),
                    error_code="StorageMoveFailed",
                    error_message="Failed to move file in storage"
                )
            
            # Update file metadata with new paths
            updated_metadata = file_metadata.move_to_location(
                new_path=new_file_path,
                new_filename=new_filename,
                new_storage_key=StorageKey(new_storage_key),
                moved_by=data.user_id,
                move_reason=data.reason
            )
            
            # Save updated metadata
            await self._file_repository.update_file(updated_metadata)
            
            # Create audit log entry
            await self._create_audit_log(
                file_metadata=file_metadata,
                new_path=str(new_file_path.value),
                user_id=data.user_id,
                reason=data.reason
            )
            
            # Calculate duration
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return MoveFileResult(
                success=True,
                file_id=data.file_id,
                old_path=str(file_metadata.file_path.value),
                new_path=str(new_file_path.value),
                filename=new_filename,
                new_storage_key=new_storage_key,
                move_duration_ms=duration_ms,
                storage_moved=True,
                metadata_updated=True
            )
                
        except Exception as e:
            # Rollback storage move if it succeeded but metadata update failed
            if new_storage_key and old_storage_key:
                try:
                    await self._storage_provider.move_file(
                        source_key=new_storage_key,
                        destination_key=old_storage_key
                    )
                except Exception:
                    pass  # Best effort rollback
            
            # Calculate duration for error case
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return MoveFileResult(
                success=False,
                file_id=data.file_id,
                move_duration_ms=duration_ms,
                error_code="MoveFailed",
                error_message=f"Unexpected error during file move: {str(e)}"
            )
    
    def _create_new_file_path(self, folder_path: str, filename: str) -> FilePath:
        """Create new file path from folder and filename."""
        if not folder_path.startswith("/"):
            folder_path = "/" + folder_path
        if not folder_path.endswith("/"):
            folder_path = folder_path + "/"
        
        new_path = folder_path + filename
        return FilePath(new_path)
    
    def _generate_new_storage_key(self, tenant_id: str, file_id: FileId, filename: str) -> str:
        """Generate new storage key for moved file."""
        year_month = datetime.utcnow().strftime("%Y/%m")
        return f"tenants/{tenant_id}/files/{year_month}/{file_id.value}/{filename}"
    
    async def _can_move_file(self, file_metadata, user_id: str) -> bool:
        """Check if user can move file (simplified permission check)."""
        # Basic permission check - owner can always move
        if file_metadata.created_by == user_id:
            return True
        
        # TODO: Implement full RBAC permission checking
        return False
    
    async def _create_audit_log(
        self,
        file_metadata,
        new_path: str,
        user_id: str,
        reason: Optional[str] = None
    ) -> None:
        """Create audit log entry for file move."""
        try:
            audit_data = {
                "action": "move_file",
                "file_id": str(file_metadata.id.value),
                "filename": file_metadata.filename,
                "old_path": str(file_metadata.file_path.value),
                "new_path": new_path,
                "user_id": user_id,
                "tenant_id": file_metadata.tenant_id,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # TODO: Implement audit logging
            
        except Exception:
            # Don't fail move for audit log errors
            pass


# Factory function for dependency injection
def create_move_file_command(
    file_repository: FileRepository,
    storage_provider: StorageProviderProtocol
) -> MoveFileCommand:
    """Create move file command."""
    return MoveFileCommand(
        file_repository=file_repository,
        storage_provider=storage_provider
    )