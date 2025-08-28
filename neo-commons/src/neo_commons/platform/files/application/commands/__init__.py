"""File management commands.

Write operations for file management following maximum separation architecture.
Each command handles exactly one write operation with comprehensive validation.

Following maximum separation architecture - one file = one purpose.
"""

from .upload_file import UploadFileCommand, UploadFileData, UploadFileResult
from .upload_file_chunk import UploadFileChunkCommand, UploadFileChunkData, UploadFileChunkResult
from .complete_upload import CompleteUploadCommand, CompleteUploadData, CompleteUploadResult
from .delete_file import DeleteFileCommand, DeleteFileData, DeleteFileResult
from .move_file import MoveFileCommand, MoveFileData, MoveFileResult
from .copy_file import CopyFileCommand, CopyFileData, CopyFileResult
from .update_metadata import UpdateMetadataCommand, UpdateMetadataData, UpdateMetadataResult
from .create_folder import CreateFolderCommand, CreateFolderData, CreateFolderResult
from .set_file_permissions import SetFilePermissionsCommand, SetFilePermissionsData, SetFilePermissionsResult

__all__ = [
    # Upload Operations
    "UploadFileCommand",
    "UploadFileData", 
    "UploadFileResult",
    "UploadFileChunkCommand",
    "UploadFileChunkData",
    "UploadFileChunkResult", 
    "CompleteUploadCommand",
    "CompleteUploadData",
    "CompleteUploadResult",
    
    # File Operations
    "DeleteFileCommand",
    "DeleteFileData",
    "DeleteFileResult",
    "MoveFileCommand", 
    "MoveFileData",
    "MoveFileResult",
    "CopyFileCommand",
    "CopyFileData", 
    "CopyFileResult",
    "UpdateMetadataCommand",
    "UpdateMetadataData",
    "UpdateMetadataResult",
    
    # Folder Operations
    "CreateFolderCommand",
    "CreateFolderData",
    "CreateFolderResult",
    
    # Permission Operations
    "SetFilePermissionsCommand",
    "SetFilePermissionsData", 
    "SetFilePermissionsResult",
]