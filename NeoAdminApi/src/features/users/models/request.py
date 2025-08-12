"""
Platform Users request models.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from .domain import AuthProvider, PlatformRoleLevel, PermissionScopeLevel


class PlatformUserCreate(BaseModel):
    """Request model for creating a platform user."""
    
    email: str = Field(..., max_length=320, description="User email address")
    username: str = Field(..., max_length=39, description="Unique username")
    external_id: Optional[str] = Field(None, max_length=255, description="External system ID")
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    display_name: Optional[str] = Field(None, max_length=150, description="Display name")
    avatar_url: Optional[str] = Field(None, max_length=2048, description="Avatar image URL")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    timezone: str = Field(default="UTC", max_length=50, description="User timezone")
    locale: str = Field(default="en-US", max_length=10, description="User locale")
    external_auth_provider: AuthProvider = Field(..., description="Authentication provider")
    external_user_id: str = Field(..., max_length=255, description="External provider user ID")
    is_active: bool = Field(default=True, description="Whether user is active")
    is_superadmin: bool = Field(default=False, description="Whether user has superadmin privileges")
    provider_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Provider-specific metadata")
    notification_preferences: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Notification settings")
    ui_preferences: Optional[Dict[str, Any]] = Field(default_factory=dict, description="UI preferences")
    job_title: Optional[str] = Field(None, max_length=150, description="Job title")
    departments: Optional[List[str]] = Field(None, description="Department memberships")
    company: Optional[str] = Field(None, max_length=255, description="Company name")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        import re
        pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid email format')
        return v.lower()
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        import re
        if not re.match(r'^[a-zA-Z0-9._-]+$', v):
            raise ValueError('Username can only contain letters, numbers, dots, underscores, and hyphens')
        return v.lower()


class PlatformUserUpdate(BaseModel):
    """Request model for updating a platform user."""
    
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    display_name: Optional[str] = Field(None, max_length=150, description="Display name")
    avatar_url: Optional[str] = Field(None, max_length=2048, description="Avatar image URL")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    timezone: Optional[str] = Field(None, max_length=50, description="User timezone")
    locale: Optional[str] = Field(None, max_length=10, description="User locale")
    is_active: Optional[bool] = Field(None, description="Whether user is active")
    notification_preferences: Optional[Dict[str, Any]] = Field(None, description="Notification settings")
    ui_preferences: Optional[Dict[str, Any]] = Field(None, description="UI preferences")
    job_title: Optional[str] = Field(None, max_length=150, description="Job title")
    departments: Optional[List[str]] = Field(None, description="Department memberships")
    company: Optional[str] = Field(None, max_length=255, description="Company name")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class PlatformUserFilter(BaseModel):
    """Filter model for listing platform users."""
    
    search: Optional[str] = Field(None, min_length=1, max_length=100, description="Search in email, username, name")
    email: Optional[str] = Field(None, description="Filter by email")
    username: Optional[str] = Field(None, description="Filter by username")
    external_auth_provider: Optional[AuthProvider] = Field(None, description="Filter by auth provider")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    is_superadmin: Optional[bool] = Field(None, description="Filter by superadmin status")
    company: Optional[str] = Field(None, description="Filter by company")
    department: Optional[str] = Field(None, description="Filter by department")
    job_title: Optional[str] = Field(None, description="Filter by job title")
    has_role: Optional[str] = Field(None, description="Filter by role code")
    has_permission: Optional[str] = Field(None, description="Filter by permission code")
    tenant_access: Optional[UUID] = Field(None, description="Filter by tenant access")
    created_after: Optional[datetime] = Field(None, description="Filter by creation date (after)")
    created_before: Optional[datetime] = Field(None, description="Filter by creation date (before)")
    last_login_after: Optional[datetime] = Field(None, description="Filter by last login (after)")
    last_login_before: Optional[datetime] = Field(None, description="Filter by last login (before)")


class RoleAssignmentRequest(BaseModel):
    """Request model for assigning roles to users."""
    
    role_codes: List[str] = Field(..., min_length=1, description="Role codes to assign")
    tenant_id: Optional[UUID] = Field(None, description="Tenant scope for role assignment")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for assignment")
    expires_at: Optional[datetime] = Field(None, description="Role assignment expiration")


class PermissionGrantRequest(BaseModel):
    """Request model for granting permissions to users."""
    
    permission_codes: List[str] = Field(..., min_length=1, description="Permission codes to grant")
    tenant_id: Optional[UUID] = Field(None, description="Tenant scope for permission grant")
    is_granted: bool = Field(default=True, description="Grant or revoke permission")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for grant/revocation")
    expires_at: Optional[datetime] = Field(None, description="Permission grant expiration")


class UserStatusUpdate(BaseModel):
    """Request model for updating user status."""
    
    is_active: bool = Field(..., description="New active status")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for status change")


class UserPreferencesUpdate(BaseModel):
    """Request model for updating user preferences."""
    
    timezone: Optional[str] = Field(None, max_length=50, description="User timezone")
    locale: Optional[str] = Field(None, max_length=10, description="User locale")
    notification_preferences: Optional[Dict[str, Any]] = Field(None, description="Notification settings")
    ui_preferences: Optional[Dict[str, Any]] = Field(None, description="UI preferences")


class BulkUserOperation(BaseModel):
    """Request model for bulk operations on users."""
    
    user_ids: List[UUID] = Field(..., min_length=1, max_length=100, description="User IDs to operate on")
    operation: str = Field(..., description="Operation to perform (activate, deactivate, delete)")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for bulk operation")
    
    @field_validator('operation')
    @classmethod
    def validate_operation(cls, v: str) -> str:
        """Validate operation type."""
        allowed_operations = ['activate', 'deactivate', 'delete', 'restore']
        if v not in allowed_operations:
            raise ValueError(f'Operation must be one of: {", ".join(allowed_operations)}')
        return v


class UserSearchRequest(BaseModel):
    """Advanced search request for users."""
    
    query: str = Field(..., min_length=1, max_length=200, description="Search query")
    fields: Optional[List[str]] = Field(None, description="Fields to search in")
    filters: Optional[PlatformUserFilter] = Field(None, description="Additional filters")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: Optional[str] = Field("asc", description="Sort order (asc/desc)")
    
    @field_validator('fields')
    @classmethod
    def validate_fields(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate search fields."""
        if v is None:
            return v
        
        allowed_fields = ['email', 'username', 'first_name', 'last_name', 'display_name', 'company', 'job_title']
        invalid_fields = [f for f in v if f not in allowed_fields]
        if invalid_fields:
            raise ValueError(f'Invalid search fields: {", ".join(invalid_fields)}')
        return v
    
    @field_validator('sort_order')
    @classmethod
    def validate_sort_order(cls, v: str) -> str:
        """Validate sort order."""
        if v not in ['asc', 'desc']:
            raise ValueError('Sort order must be "asc" or "desc"')
        return v
