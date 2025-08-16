"""
Response models for roles API endpoints.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

from .domain import PlatformRole, PlatformPermission, UserRoleAssignment, PlatformRoleLevel, PermissionScopeLevel


class RoleResponse(BaseModel):
    """Response model for a single role."""
    
    id: int
    code: str
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    role_level: PlatformRoleLevel
    priority: int
    is_system: bool
    is_default: bool
    max_assignees: Optional[int] = None
    tenant_scoped: bool
    requires_approval: bool
    role_config: Dict[str, Any]
    metadata: Dict[str, Any]
    permission_count: Optional[int] = None
    user_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_domain(cls, role: PlatformRole) -> "RoleResponse":
        return cls(
            id=role.id,
            code=role.code,
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            role_level=role.role_level,
            priority=role.priority,
            is_system=role.is_system,
            is_default=role.is_default,
            max_assignees=role.max_assignees,
            tenant_scoped=role.tenant_scoped,
            requires_approval=role.requires_approval,
            role_config=role.role_config,
            metadata=role.metadata,
            permission_count=role.permission_count,
            user_count=role.user_count,
            created_at=role.created_at,
            updated_at=role.updated_at
        )


class RoleDetailResponse(RoleResponse):
    """Detailed response model including permissions."""
    
    permissions: List["PermissionResponse"] = Field(default_factory=list)


class PermissionResponse(BaseModel):
    """Response model for a permission."""
    
    id: int
    code: str
    description: Optional[str] = None
    resource: str
    action: str
    scope_level: PermissionScopeLevel
    is_dangerous: bool
    requires_mfa: bool
    requires_approval: bool
    permissions_config: Dict[str, Any]
    
    @classmethod
    def from_domain(cls, permission: PlatformPermission) -> "PermissionResponse":
        return cls(
            id=permission.id,
            code=permission.code,
            description=permission.description,
            resource=permission.resource,
            action=permission.action,
            scope_level=permission.scope_level,
            is_dangerous=permission.is_dangerous,
            requires_mfa=permission.requires_mfa,
            requires_approval=permission.requires_approval,
            permissions_config=permission.permissions_config
        )


class RoleAssignmentResponse(BaseModel):
    """Response model for role assignment."""
    
    user_id: UUID
    role_id: int
    role_code: str
    role_name: str
    granted_by: Optional[UUID] = None
    granted_by_name: Optional[str] = None
    granted_reason: Optional[str] = None
    granted_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool
    tenant_id: Optional[UUID] = None
    
    @classmethod
    def from_domain(
        cls,
        assignment: UserRoleAssignment,
        role_code: str,
        role_name: str,
        granted_by_name: Optional[str] = None,
        tenant_id: Optional[UUID] = None
    ) -> "RoleAssignmentResponse":
        return cls(
            user_id=assignment.user_id,
            role_id=assignment.role_id,
            role_code=role_code,
            role_name=role_name,
            granted_by=assignment.granted_by,
            granted_by_name=granted_by_name,
            granted_reason=assignment.granted_reason,
            granted_at=assignment.granted_at,
            expires_at=assignment.expires_at,
            is_active=assignment.is_active,
            tenant_id=tenant_id
        )


class BulkRoleOperationResponse(BaseModel):
    """Response for bulk role operations."""
    
    operation: str
    total_requested: int
    successful: int
    failed: int
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    successful_items: List[Dict[str, Any]] = Field(default_factory=list)
    failed_items: List[Dict[str, Any]] = Field(default_factory=list)