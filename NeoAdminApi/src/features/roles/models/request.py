"""
Request models for roles API endpoints.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from .domain import PlatformRoleLevel


class RoleCreateRequest(BaseModel):
    """Request model for creating a new role."""
    
    code: str = Field(..., min_length=1, max_length=100, pattern="^[a-z0-9_-]+$")
    name: str = Field(..., min_length=1, max_length=150)
    display_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    role_level: PlatformRoleLevel = PlatformRoleLevel.PLATFORM
    priority: int = Field(100, ge=0, le=1000)
    max_assignees: Optional[int] = Field(None, ge=1)
    tenant_scoped: bool = False
    requires_approval: bool = False
    role_config: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('code')
    @classmethod
    def validate_code(cls, v):
        if not v.islower() or ' ' in v:
            raise ValueError("Role code must be lowercase without spaces")
        return v


class RoleUpdateRequest(BaseModel):
    """Request model for updating a role."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    display_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    priority: Optional[int] = Field(None, ge=0, le=1000)
    max_assignees: Optional[int] = Field(None, ge=1)
    requires_approval: Optional[bool] = None
    role_config: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class RoleAssignmentRequest(BaseModel):
    """Request model for assigning a role to a user."""
    
    user_id: UUID = Field(..., description="User to assign role to")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for assignment")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration date")
    tenant_id: Optional[UUID] = Field(None, description="Tenant context for assignment")


class BulkRoleAssignmentRequest(BaseModel):
    """Request model for bulk role assignments."""
    
    user_ids: List[UUID] = Field(..., min_length=1, max_length=100)
    role_ids: List[int] = Field(..., min_length=1, max_length=20)
    reason: Optional[str] = Field(None, max_length=500)
    expires_at: Optional[datetime] = None
    tenant_id: Optional[UUID] = None


class RolePermissionUpdateRequest(BaseModel):
    """Request model for updating role permissions."""
    
    permission_ids: List[int] = Field(..., description="List of permission IDs to assign")
    replace: bool = Field(False, description="Replace all existing permissions or add to them")


class RoleSearchFilter(BaseModel):
    """Filter parameters for role search."""
    
    code: Optional[str] = None
    name: Optional[str] = None
    role_level: Optional[PlatformRoleLevel] = None
    is_system: Optional[bool] = None
    is_default: Optional[bool] = None
    tenant_scoped: Optional[bool] = None
    min_priority: Optional[int] = Field(None, ge=0)
    max_priority: Optional[int] = Field(None, le=1000)