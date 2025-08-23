"""Request context entity.

This module defines the RequestContext entity for managing
request-scoped information.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timezone

from ..value_objects.identifiers import UserId, TenantId, OrganizationId, PermissionCode, RoleCode
from ...utils.uuid import generate_uuid_v7


@dataclass
class RequestContext:
    """Request context entity.
    
    Represents the context of a request including user, tenant,
    and permission information.
    """
    
    request_id: str
    user_id: Optional[UserId] = None
    tenant_id: Optional[TenantId] = None
    organization_id: Optional[OrganizationId] = None
    schema_name: str = "admin"
    is_admin_request: bool = True
    region: str = "us-east"
    user_permissions: Set[PermissionCode] = field(default_factory=set)
    user_roles: Set[RoleCode] = field(default_factory=set)
    tenant_features: Dict[str, bool] = field(default_factory=dict)
    request_metadata: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    api_version: str = "v1"
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Post-initialization processing."""
        if not self.correlation_id:
            self.correlation_id = generate_uuid_v7()
    
    @property
    def is_authenticated(self) -> bool:
        """Check if request is authenticated."""
        return self.user_id is not None
    
    @property
    def is_tenant_request(self) -> bool:
        """Check if this is a tenant-scoped request."""
        return self.tenant_id is not None and not self.is_admin_request
    
    @property
    def effective_schema(self) -> str:
        """Get the effective database schema for this request."""
        if self.is_admin_request:
            return "admin"
        elif self.tenant_id:
            return f"tenant_{self.tenant_id.value}"
        return self.schema_name
    
    def has_permission(self, permission: PermissionCode) -> bool:
        """Check if request context has permission."""
        return permission in self.user_permissions
    
    def has_any_permission(self, permissions: List[PermissionCode]) -> bool:
        """Check if request context has any of the specified permissions."""
        return any(perm in self.user_permissions for perm in permissions)
    
    def has_all_permissions(self, permissions: List[PermissionCode]) -> bool:
        """Check if request context has all specified permissions."""
        return all(perm in self.user_permissions for perm in permissions)
    
    def has_role(self, role: RoleCode) -> bool:
        """Check if request context has role."""
        return role in self.user_roles
    
    def has_feature(self, feature: str) -> bool:
        """Check if request context has feature enabled."""
        return self.tenant_features.get(feature, False)
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to request context."""
        self.request_metadata[key] = value