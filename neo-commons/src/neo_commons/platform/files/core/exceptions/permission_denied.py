"""Permission denied exception for file management platform infrastructure.

ONLY permission denied - represents when a user lacks sufficient permissions
to perform a file operation.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Any, Dict, Optional, Set

from .....core.exceptions import AuthorizationError
from ..value_objects import FileId, FilePath


class PermissionDenied(AuthorizationError):
    """Raised when a user lacks permission to perform a file operation.
    
    This exception represents failures when users attempt file operations
    without sufficient permissions based on RBAC or file-specific permissions.
    """
    
    def __init__(
        self,
        message: str,
        file_id: Optional[FileId] = None,
        file_path: Optional[FilePath] = None,
        operation: Optional[str] = None,
        required_permissions: Optional[Set[str]] = None,
        user_permissions: Optional[Set[str]] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        team_id: Optional[str] = None,
        permission_type: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize permission denied exception.
        
        Args:
            message: Human-readable error message
            file_id: ID of the file access was denied to
            file_path: Path of the file access was denied to
            operation: Operation that was denied (read, write, delete, share, etc.)
            required_permissions: Set of permissions required for the operation
            user_permissions: Set of permissions the user actually has
            tenant_id: Tenant context for multi-tenant isolation
            user_id: User who was denied access
            team_id: Team context if applicable
            permission_type: Type of permission check (file, folder, system)
            error_code: Specific error code for the failure
            details: Additional details about the failure
        """
        # Build enhanced details
        enhanced_details = details or {}
        if file_id:
            enhanced_details["file_id"] = str(file_id)
        if file_path:
            enhanced_details["file_path"] = str(file_path)
        if operation:
            enhanced_details["operation"] = operation
        if required_permissions:
            enhanced_details["required_permissions"] = sorted(list(required_permissions))
        if user_permissions:
            enhanced_details["user_permissions"] = sorted(list(user_permissions))
        if tenant_id:
            enhanced_details["tenant_id"] = tenant_id
        if user_id:
            enhanced_details["user_id"] = user_id
        if team_id:
            enhanced_details["team_id"] = team_id
        if permission_type:
            enhanced_details["permission_type"] = permission_type
            
        super().__init__(
            message=message,
            error_code=error_code or "PERMISSION_DENIED",
            details=enhanced_details
        )
        
        # Store permission-specific fields
        self.file_id = file_id
        self.file_path = file_path
        self.operation = operation
        self.required_permissions = required_permissions
        self.user_permissions = user_permissions
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.team_id = team_id
        self.permission_type = permission_type