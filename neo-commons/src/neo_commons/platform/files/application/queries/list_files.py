"""List files query.

ONLY file listing - handles directory file enumeration
with pagination, filtering, and sorting capabilities.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from ...core.protocols.file_repository import FileRepository
from ...core.value_objects.file_path import FilePath


class SortBy(Enum):
    """File sorting options."""
    NAME = "name"
    SIZE = "size"  
    CREATED_DATE = "created_date"
    MODIFIED_DATE = "modified_date"
    FILE_TYPE = "file_type"


class SortOrder(Enum):
    """Sort order options."""
    ASC = "asc"
    DESC = "desc"


@dataclass
class ListFilesData:
    """Data required to list files."""
    
    # Request context
    user_id: str
    tenant_id: str
    
    # Directory specification
    folder_path: str = "/"
    include_subfolders: bool = False
    
    # Pagination
    page: int = 1
    page_size: int = 50
    
    # Filtering
    file_types: Optional[List[str]] = None  # MIME type prefixes: ["image/", "application/pdf"]
    name_pattern: Optional[str] = None      # Search pattern for filename
    size_min_bytes: Optional[int] = None
    size_max_bytes: Optional[int] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    
    # Sorting
    sort_by: SortBy = SortBy.NAME
    sort_order: SortOrder = SortOrder.ASC
    
    # Options
    include_deleted: bool = False
    include_metadata: bool = True
    include_permissions: bool = False
    
    # Optional context
    request_id: Optional[str] = None


@dataclass
class FileListItem:
    """Individual file in listing."""
    
    file_id: str
    filename: str
    file_path: str
    file_size_bytes: int
    file_size_formatted: str
    content_type: str
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: str
    is_deleted: bool
    
    # Optional metadata
    description: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    permissions: Optional[List[str]] = None


@dataclass
class PaginationInfo:
    """Pagination information."""
    
    current_page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool


@dataclass 
class ListFilesResult:
    """Result of file listing query."""
    
    success: bool
    files: List[FileListItem] = None
    pagination: Optional[PaginationInfo] = None
    folder_path: str = ""
    total_size_bytes: int = 0
    query_duration_ms: int = 0
    
    # Error information
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class ListFilesQuery:
    """Query to list files in directory.
    
    Handles file listing including:
    - Directory traversal with permission checking
    - Advanced filtering and search capabilities
    - Efficient pagination with metadata
    - Multiple sorting options
    - Performance optimization for large directories
    - Error handling with proper codes
    """
    
    def __init__(self, file_repository: FileRepository):
        """Initialize list files query.
        
        Args:
            file_repository: Repository for file metadata
        """
        self._file_repository = file_repository
    
    async def execute(self, data: ListFilesData) -> ListFilesResult:
        """Execute file listing operation.
        
        Args:
            data: File listing data and options
            
        Returns:
            Result containing paginated file list
        """
        start_time = datetime.utcnow()
        
        try:
            # Validate folder path
            folder_path = FilePath(data.folder_path)
            
            # Check permissions to access folder
            if not await self._can_access_folder(folder_path, data.user_id, data.tenant_id):
                return ListFilesResult(
                    success=False,
                    folder_path=data.folder_path,
                    error_code="PermissionDenied",
                    error_message="User lacks permission to access this folder"
                )
            
            # Build filter criteria
            filter_criteria = {
                "tenant_id": data.tenant_id,
                "folder_path": data.folder_path,
                "include_subfolders": data.include_subfolders,
                "include_deleted": data.include_deleted,
                "file_types": data.file_types,
                "name_pattern": data.name_pattern,
                "size_min_bytes": data.size_min_bytes,
                "size_max_bytes": data.size_max_bytes,
                "created_after": data.created_after,
                "created_before": data.created_before
            }
            
            # Get total count for pagination
            total_count = await self._file_repository.count_files(filter_criteria)
            
            # Calculate pagination
            total_pages = (total_count + data.page_size - 1) // data.page_size
            offset = (data.page - 1) * data.page_size
            
            pagination = PaginationInfo(
                current_page=data.page,
                page_size=data.page_size,
                total_items=total_count,
                total_pages=total_pages,
                has_next=data.page < total_pages,
                has_previous=data.page > 1
            )
            
            # Get paginated files
            files_metadata = await self._file_repository.list_files(
                filter_criteria=filter_criteria,
                sort_by=data.sort_by.value,
                sort_order=data.sort_order.value,
                offset=offset,
                limit=data.page_size
            )
            
            # Convert to list items
            file_items = []
            total_size = 0
            
            for file_meta in files_metadata:
                # Check individual file permissions
                if not await self._can_view_file(file_meta, data.user_id):
                    continue
                
                file_item = FileListItem(
                    file_id=str(file_meta.id.value),
                    filename=file_meta.filename,
                    file_path=str(file_meta.file_path.value),
                    file_size_bytes=file_meta.file_size.bytes,
                    file_size_formatted=str(file_meta.file_size),
                    content_type=file_meta.content_type.value,
                    created_at=file_meta.created_at,
                    updated_at=file_meta.updated_at,
                    created_by=file_meta.created_by,
                    is_deleted=file_meta.is_deleted
                )
                
                # Add optional metadata
                if data.include_metadata:
                    file_item.description = file_meta.description
                    file_item.tags = file_meta.tags
                
                if data.include_permissions:
                    file_item.permissions = await self._get_file_permissions(file_meta.id)
                
                file_items.append(file_item)
                total_size += file_meta.file_size.bytes
            
            # Calculate duration
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return ListFilesResult(
                success=True,
                files=file_items,
                pagination=pagination,
                folder_path=data.folder_path,
                total_size_bytes=total_size,
                query_duration_ms=duration_ms
            )
                
        except Exception as e:
            # Calculate duration for error case
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return ListFilesResult(
                success=False,
                folder_path=data.folder_path,
                query_duration_ms=duration_ms,
                error_code="ListingFailed",
                error_message=f"Failed to list files: {str(e)}"
            )
    
    async def _can_access_folder(self, folder_path: FilePath, user_id: str, tenant_id: str) -> bool:
        """Check if user can access folder."""
        # Basic permission check - all users can access their tenant's root
        # TODO: Implement folder-level permissions
        return True
    
    async def _can_view_file(self, file_metadata, user_id: str) -> bool:
        """Check if user can view file in listing."""
        # Basic permission check - owner can always view
        if file_metadata.created_by == user_id:
            return True
        
        # TODO: Implement full RBAC permission checking
        return False
    
    async def _get_file_permissions(self, file_id) -> List[str]:
        """Get user's permissions on file."""
        try:
            # TODO: Implement permission retrieval
            return []
        except Exception:
            return []


# Factory function for dependency injection
def create_list_files_query(file_repository: FileRepository) -> ListFilesQuery:
    """Create list files query."""
    return ListFilesQuery(file_repository)