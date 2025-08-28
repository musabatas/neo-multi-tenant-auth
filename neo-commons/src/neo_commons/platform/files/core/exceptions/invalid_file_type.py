"""Invalid file type exception for file management platform infrastructure.

ONLY invalid file type - represents when a file type is not allowed
by system or tenant configuration policies.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Any, Dict, Optional, Set

from .....core.exceptions import ValidationError
from ..value_objects import MimeType, FilePath


class InvalidFileType(ValidationError):
    """Raised when a file type is not allowed by system policies.
    
    This exception represents failures when file types don't match
    configured allowed/blocked file type policies.
    """
    
    def __init__(
        self,
        message: str,
        file_path: Optional[FilePath] = None,
        mime_type: Optional[MimeType] = None,
        detected_extension: Optional[str] = None,
        allowed_types: Optional[Set[str]] = None,
        blocked_types: Optional[Set[str]] = None,
        tenant_id: Optional[str] = None,
        policy_name: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize invalid file type exception.
        
        Args:
            message: Human-readable error message
            file_path: Path of the invalid file
            mime_type: Detected MIME type of the file
            detected_extension: File extension that was detected
            allowed_types: Set of allowed file types/extensions
            blocked_types: Set of blocked file types/extensions
            tenant_id: Tenant context for multi-tenant isolation
            policy_name: Name of the policy that was violated
            error_code: Specific error code for the failure
            details: Additional details about the failure
        """
        # Build enhanced details
        enhanced_details = details or {}
        if file_path:
            enhanced_details["file_path"] = str(file_path)
        if mime_type:
            enhanced_details["mime_type"] = str(mime_type)
            enhanced_details["mime_category"] = mime_type.get_category()
        if detected_extension:
            enhanced_details["detected_extension"] = detected_extension
        if allowed_types:
            enhanced_details["allowed_types"] = sorted(list(allowed_types))
        if blocked_types:
            enhanced_details["blocked_types"] = sorted(list(blocked_types))
        if tenant_id:
            enhanced_details["tenant_id"] = tenant_id
        if policy_name:
            enhanced_details["policy_name"] = policy_name
            
        super().__init__(
            message=message,
            error_code=error_code or "INVALID_FILE_TYPE",
            details=enhanced_details
        )
        
        # Store file type-specific fields
        self.file_path = file_path
        self.mime_type = mime_type
        self.detected_extension = detected_extension
        self.allowed_types = allowed_types
        self.blocked_types = blocked_types
        self.tenant_id = tenant_id
        self.policy_name = policy_name