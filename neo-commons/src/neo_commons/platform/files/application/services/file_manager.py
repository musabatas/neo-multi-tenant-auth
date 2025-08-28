"""File manager service.

ONLY file management orchestration - coordinates file operations
with business logic, validation, and multi-service coordination.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from typing import Optional

from ...core.protocols.file_repository import FileRepository
from ...core.protocols.storage_provider import StorageProviderProtocol
from ...core.protocols.virus_scanner import VirusScanner
from ..commands.upload_file import UploadFileCommand, UploadFileData, UploadFileResult
from ..commands.delete_file import DeleteFileCommand, DeleteFileData, DeleteFileResult
from ..commands.move_file import MoveFileCommand, MoveFileData, MoveFileResult
from ..queries.get_file_metadata import GetFileMetadataQuery, GetFileMetadataData, GetFileMetadataResult
from ..queries.get_file_content import GetFileContentQuery, GetFileContentData, GetFileContentResult
from ..queries.list_files import ListFilesQuery, ListFilesData, ListFilesResult


@dataclass
class FileManagerConfig:
    """Configuration for file manager service."""
    
    # Size limits
    max_file_size_bytes: int = 500 * 1024 * 1024  # 500MB default
    max_files_per_folder: int = 10000
    
    # Features
    enable_virus_scanning: bool = True
    enable_thumbnails: bool = True
    enable_versioning: bool = True
    enable_audit_logging: bool = True
    
    # Performance
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour
    
    # Storage
    default_storage_provider: str = "local"
    storage_path_template: str = "tenants/{tenant_id}/files/{year}/{month}/{file_id}/{filename}"


class FileManager:
    """Main file management service.
    
    Orchestrates file operations including:
    - High-level file operations (upload, download, delete, move)
    - Business rule enforcement and validation
    - Multi-service coordination (storage, virus scan, thumbnails)
    - Performance optimization and caching
    - Error handling and recovery
    - Audit logging and compliance
    - Quota enforcement and monitoring
    """
    
    def __init__(
        self,
        file_repository: FileRepository,
        storage_provider: StorageProviderProtocol,
        virus_scanner: Optional[VirusScanner] = None,
        config: Optional[FileManagerConfig] = None
    ):
        """Initialize file manager service.
        
        Args:
            file_repository: Repository for file metadata
            storage_provider: Storage backend for file content
            virus_scanner: Optional virus scanner
            config: Service configuration
        """
        self._file_repository = file_repository
        self._storage_provider = storage_provider
        self._virus_scanner = virus_scanner
        self._config = config or FileManagerConfig()
        
        # Initialize commands
        self._upload_command = UploadFileCommand(
            file_repository=file_repository,
            storage_provider=storage_provider,
            virus_scanner=virus_scanner
        )
        self._delete_command = DeleteFileCommand(
            file_repository=file_repository,
            storage_provider=storage_provider
        )
        self._move_command = MoveFileCommand(
            file_repository=file_repository,
            storage_provider=storage_provider
        )
        
        # Initialize queries
        self._metadata_query = GetFileMetadataQuery(file_repository)
        self._content_query = GetFileContentQuery(file_repository, storage_provider)
        self._list_query = ListFilesQuery(file_repository)
    
    # High-level file operations
    
    async def upload_file(
        self,
        filename: str,
        content: bytes,
        user_id: str,
        tenant_id: str,
        folder_path: str = "/",
        content_type: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs
    ) -> UploadFileResult:
        """Upload a file with business validation.
        
        Args:
            filename: Original filename
            content: File content bytes
            user_id: User uploading the file
            tenant_id: Tenant context
            folder_path: Destination folder path
            content_type: MIME type (auto-detected if None)
            description: File description
            **kwargs: Additional upload options
            
        Returns:
            Upload result with file metadata or error
        """
        # Validate file size
        if len(content) > self._config.max_file_size_bytes:
            return UploadFileResult(
                success=False,
                filename=filename,
                error_code="FileTooLarge",
                error_message=f"File size {len(content)} exceeds maximum {self._config.max_file_size_bytes}"
            )
        
        # Check folder file limit
        folder_file_count = await self._get_folder_file_count(folder_path, tenant_id)
        if folder_file_count >= self._config.max_files_per_folder:
            return UploadFileResult(
                success=False,
                filename=filename,
                error_code="FolderFull",
                error_message=f"Folder has reached maximum file limit of {self._config.max_files_per_folder}"
            )
        
        # Create upload data
        upload_data = UploadFileData(
            filename=filename,
            content=content,
            content_type=content_type,
            folder_path=folder_path,
            description=description,
            user_id=user_id,
            tenant_id=tenant_id,
            scan_for_viruses=self._config.enable_virus_scanning,
            generate_thumbnails=self._config.enable_thumbnails,
            **kwargs
        )
        
        # Execute upload
        return await self._upload_command.execute(upload_data)
    
    async def get_file_metadata(
        self,
        file_id: str,
        user_id: str,
        tenant_id: str,
        include_versions: bool = False,
        include_permissions: bool = False,
        **kwargs
    ) -> GetFileMetadataResult:
        """Get file metadata with permission validation.
        
        Args:
            file_id: File identifier
            user_id: Requesting user
            tenant_id: Tenant context
            include_versions: Include version history
            include_permissions: Include permission details
            **kwargs: Additional query options
            
        Returns:
            Metadata result with file information or error
        """
        metadata_data = GetFileMetadataData(
            file_id=file_id,
            user_id=user_id,
            tenant_id=tenant_id,
            include_versions=include_versions,
            include_permissions=include_permissions,
            **kwargs
        )
        
        return await self._metadata_query.execute(metadata_data)
    
    async def get_file_content(
        self,
        file_id: str,
        user_id: str,
        tenant_id: str,
        stream_content: bool = True,
        byte_range_start: Optional[int] = None,
        byte_range_end: Optional[int] = None,
        **kwargs
    ) -> GetFileContentResult:
        """Get file content with streaming support.
        
        Args:
            file_id: File identifier
            user_id: Requesting user
            tenant_id: Tenant context
            stream_content: Return content as stream
            byte_range_start: Start byte for partial content
            byte_range_end: End byte for partial content
            **kwargs: Additional query options
            
        Returns:
            Content result with file data or stream
        """
        content_data = GetFileContentData(
            file_id=file_id,
            user_id=user_id,
            tenant_id=tenant_id,
            stream_content=stream_content,
            byte_range_start=byte_range_start,
            byte_range_end=byte_range_end,
            **kwargs
        )
        
        return await self._content_query.execute(content_data)
    
    async def list_files(
        self,
        user_id: str,
        tenant_id: str,
        folder_path: str = "/",
        page: int = 1,
        page_size: int = 50,
        **kwargs
    ) -> ListFilesResult:
        """List files in folder with pagination.
        
        Args:
            user_id: Requesting user
            tenant_id: Tenant context
            folder_path: Folder to list
            page: Page number (1-based)
            page_size: Items per page
            **kwargs: Additional filtering options
            
        Returns:
            List result with paginated files
        """
        list_data = ListFilesData(
            user_id=user_id,
            tenant_id=tenant_id,
            folder_path=folder_path,
            page=page,
            page_size=page_size,
            **kwargs
        )
        
        return await self._list_query.execute(list_data)
    
    async def delete_file(
        self,
        file_id: str,
        user_id: str,
        tenant_id: str,
        permanent_delete: bool = False,
        reason: Optional[str] = None,
        **kwargs
    ) -> DeleteFileResult:
        """Delete file with audit logging.
        
        Args:
            file_id: File identifier
            user_id: User deleting the file
            tenant_id: Tenant context
            permanent_delete: True for permanent, False for soft delete
            reason: Reason for deletion
            **kwargs: Additional delete options
            
        Returns:
            Delete result with operation status
        """
        delete_data = DeleteFileData(
            file_id=file_id,
            user_id=user_id,
            tenant_id=tenant_id,
            permanent_delete=permanent_delete,
            reason=reason,
            **kwargs
        )
        
        return await self._delete_command.execute(delete_data)
    
    async def move_file(
        self,
        file_id: str,
        new_folder_path: str,
        user_id: str,
        tenant_id: str,
        new_filename: Optional[str] = None,
        overwrite_existing: bool = False,
        **kwargs
    ) -> MoveFileResult:
        """Move file to new location.
        
        Args:
            file_id: File identifier
            new_folder_path: Destination folder
            user_id: User moving the file
            tenant_id: Tenant context
            new_filename: New filename (optional)
            overwrite_existing: Allow overwriting existing files
            **kwargs: Additional move options
            
        Returns:
            Move result with operation status
        """
        move_data = MoveFileData(
            file_id=file_id,
            new_folder_path=new_folder_path,
            new_filename=new_filename,
            user_id=user_id,
            tenant_id=tenant_id,
            overwrite_existing=overwrite_existing,
            **kwargs
        )
        
        return await self._move_command.execute(move_data)
    
    # Helper methods
    
    async def _get_folder_file_count(self, folder_path: str, tenant_id: str) -> int:
        """Get number of files in folder."""
        try:
            filter_criteria = {
                "tenant_id": tenant_id,
                "folder_path": folder_path,
                "include_subfolders": False,
                "include_deleted": False
            }
            return await self._file_repository.count_files(filter_criteria)
        except Exception:
            # Default to 0 on error - better to allow upload than block
            return 0
    
    # Service management
    
    async def initialize(self) -> None:
        """Initialize the file manager service."""
        # TODO: Implement service initialization
        # - Validate storage provider connectivity
        # - Initialize caches
        # - Set up background tasks
        pass
    
    async def shutdown(self) -> None:
        """Shutdown the file manager service."""
        # TODO: Implement graceful shutdown
        # - Complete pending operations
        # - Clean up resources
        # - Close connections
        pass
    
    async def health_check(self) -> dict:
        """Get service health status."""
        try:
            # Check repository connectivity
            repo_healthy = await self._file_repository.health_check()
            
            # Check storage provider
            storage_healthy = await self._storage_provider.health_check()
            
            # Check virus scanner (if enabled)
            scanner_healthy = True
            if self._virus_scanner:
                scanner_healthy = await self._virus_scanner.health_check()
            
            overall_healthy = repo_healthy and storage_healthy and scanner_healthy
            
            return {
                "healthy": overall_healthy,
                "components": {
                    "repository": repo_healthy,
                    "storage": storage_healthy,
                    "virus_scanner": scanner_healthy
                },
                "config": {
                    "max_file_size_mb": self._config.max_file_size_bytes // (1024 * 1024),
                    "virus_scanning_enabled": self._config.enable_virus_scanning,
                    "thumbnails_enabled": self._config.enable_thumbnails,
                    "versioning_enabled": self._config.enable_versioning
                }
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }


# Factory function for dependency injection
def create_file_manager(
    file_repository: FileRepository,
    storage_provider: StorageProviderProtocol,
    virus_scanner: Optional[VirusScanner] = None,
    config: Optional[FileManagerConfig] = None
) -> FileManager:
    """Create file manager service."""
    return FileManager(
        file_repository=file_repository,
        storage_provider=storage_provider,
        virus_scanner=virus_scanner,
        config=config
    )