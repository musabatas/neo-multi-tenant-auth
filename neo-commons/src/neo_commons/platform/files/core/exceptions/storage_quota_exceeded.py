"""Storage quota exceeded exception for file management platform infrastructure.

ONLY storage quota exceeded - represents when a file operation would exceed
the configured storage quota limits.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Any, Dict, Optional

from .....core.exceptions import BusinessLogicError
from ..value_objects import FileSize


class StorageQuotaExceeded(BusinessLogicError):
    """Raised when a file operation would exceed storage quota limits.
    
    This exception represents failures when file operations would cause
    storage usage to exceed configured tenant or system limits.
    """
    
    def __init__(
        self,
        message: str,
        current_usage: Optional[FileSize] = None,
        quota_limit: Optional[FileSize] = None,
        requested_size: Optional[FileSize] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        quota_type: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize storage quota exceeded exception.
        
        Args:
            message: Human-readable error message
            current_usage: Current storage usage
            quota_limit: Maximum allowed storage quota
            requested_size: Size of file that would exceed quota
            tenant_id: Tenant context for multi-tenant isolation
            user_id: User attempting the operation
            quota_type: Type of quota (tenant, user, organization)
            error_code: Specific error code for the failure
            details: Additional details about the failure
        """
        # Build enhanced details
        enhanced_details = details or {}
        if current_usage:
            enhanced_details["current_usage"] = str(current_usage)
            enhanced_details["current_usage_bytes"] = current_usage.bytes
        if quota_limit:
            enhanced_details["quota_limit"] = str(quota_limit)
            enhanced_details["quota_limit_bytes"] = quota_limit.bytes
        if requested_size:
            enhanced_details["requested_size"] = str(requested_size)
            enhanced_details["requested_size_bytes"] = requested_size.bytes
        if tenant_id:
            enhanced_details["tenant_id"] = tenant_id
        if user_id:
            enhanced_details["user_id"] = user_id
        if quota_type:
            enhanced_details["quota_type"] = quota_type
            
        super().__init__(
            message=message,
            error_code=error_code or "STORAGE_QUOTA_EXCEEDED",
            details=enhanced_details
        )
        
        # Store quota-specific fields
        self.current_usage = current_usage
        self.quota_limit = quota_limit
        self.requested_size = requested_size
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.quota_type = quota_type