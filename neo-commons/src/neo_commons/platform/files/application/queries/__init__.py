"""File management queries.

Read operations for file management following maximum separation architecture.
Each query handles exactly one read operation with comprehensive validation.

Following maximum separation architecture - one file = one purpose.
"""

from .get_file_metadata import GetFileMetadataQuery, GetFileMetadataData, GetFileMetadataResult
from .get_file_content import GetFileContentQuery, GetFileContentData, GetFileContentResult
from .list_files import ListFilesQuery, ListFilesData, ListFilesResult
from .search_files import SearchFilesQuery, SearchFilesData, SearchFilesResult
from .get_upload_url import GetUploadUrlQuery, GetUploadUrlData, GetUploadUrlResult
from .get_upload_progress import GetUploadProgressQuery, GetUploadProgressData, GetUploadProgressResult
from .get_file_versions import GetFileVersionsQuery, GetFileVersionsData, GetFileVersionsResult
from .check_file_permissions import CheckFilePermissionsQuery, CheckFilePermissionsData, CheckFilePermissionsResult

__all__ = [
    # File Information Queries
    "GetFileMetadataQuery",
    "GetFileMetadataData",
    "GetFileMetadataResult",
    "GetFileContentQuery",
    "GetFileContentData", 
    "GetFileContentResult",
    
    # File Listing and Search
    "ListFilesQuery",
    "ListFilesData",
    "ListFilesResult",
    "SearchFilesQuery",
    "SearchFilesData",
    "SearchFilesResult",
    
    # Upload Queries
    "GetUploadUrlQuery",
    "GetUploadUrlData",
    "GetUploadUrlResult",
    "GetUploadProgressQuery",
    "GetUploadProgressData",
    "GetUploadProgressResult",
    
    # Version and Permission Queries
    "GetFileVersionsQuery",
    "GetFileVersionsData",
    "GetFileVersionsResult",
    "CheckFilePermissionsQuery",
    "CheckFilePermissionsData",
    "CheckFilePermissionsResult",
]