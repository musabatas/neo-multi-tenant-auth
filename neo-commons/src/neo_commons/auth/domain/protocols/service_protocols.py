"""
Service protocol interfaces for authorization domain.

Defines contracts for application service layer implementations.
"""
from typing import Protocol, runtime_checkable, List, Optional, Dict, Any
from ..entities.permission import Permission
from ..entities.role import Role, RoleAssignment
from ..entities.access_control import AccessControlEntry
from ..entities.session import Session, SessionContext
from ..value_objects.permission_check import PermissionCheck, PermissionResult
from ..value_objects.user_context import UserContext
from ..value_objects.tenant_context import TenantContext


@runtime_checkable
class PermissionServiceProtocol(Protocol):
    """Protocol for permission business logic operations."""
    
    async def check_permission(
        self,
        user_context: UserContext,
        permission: str,
        tenant_context: Optional[TenantContext] = None
    ) -> PermissionResult:
        """Check if user has a specific permission."""
        ...
    
    async def check_permissions_batch(
        self,
        checks: List[PermissionCheck]
    ) -> List[PermissionResult]:
        """Check multiple permissions in batch."""
        ...
    
    async def has_any_permission(
        self,
        user_context: UserContext,
        permissions: List[str],
        tenant_context: Optional[TenantContext] = None
    ) -> PermissionResult:
        """Check if user has any of the specified permissions."""
        ...
    
    async def has_all_permissions(
        self,
        user_context: UserContext,
        permissions: List[str],
        tenant_context: Optional[TenantContext] = None
    ) -> PermissionResult:
        """Check if user has all of the specified permissions."""
        ...
    
    async def get_user_permissions(
        self,
        user_context: UserContext,
        tenant_context: Optional[TenantContext] = None,
        use_cache: bool = True
    ) -> List[Permission]:
        """Get all permissions for a user."""
        ...
    
    async def get_effective_permissions(
        self,
        user_context: UserContext,
        resource: str,
        tenant_context: Optional[TenantContext] = None
    ) -> List[Permission]:
        """Get effective permissions for a user on a specific resource."""
        ...
    
    async def invalidate_user_permission_cache(self, user_id: str, tenant_id: Optional[str] = None) -> None:
        """Invalidate cached permissions for a user."""
        ...


@runtime_checkable
class RoleServiceProtocol(Protocol):
    """Protocol for role business logic operations."""
    
    async def get_user_roles(
        self,
        user_context: UserContext,
        tenant_context: Optional[TenantContext] = None,
        use_cache: bool = True
    ) -> List[Role]:
        """Get all roles for a user."""
        ...
    
    async def assign_role(
        self,
        user_id: str,
        role_id: str,
        assigned_by: str,
        tenant_id: Optional[str] = None,
        expires_at: Optional[Any] = None
    ) -> RoleAssignment:
        """Assign a role to a user."""
        ...
    
    async def revoke_role(
        self,
        user_id: str,
        role_id: str,
        revoked_by: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Revoke a role from a user."""
        ...
    
    async def get_role_hierarchy(
        self,
        role_id: str,
        tenant_context: Optional[TenantContext] = None
    ) -> List[Role]:
        """Get role hierarchy including parent/child roles."""
        ...
    
    async def can_assign_role(
        self,
        assigner_context: UserContext,
        target_role_id: str,
        target_user_id: str,
        tenant_context: Optional[TenantContext] = None
    ) -> bool:
        """Check if user can assign a specific role."""
        ...
    
    async def get_assignable_roles(
        self,
        assigner_context: UserContext,
        tenant_context: Optional[TenantContext] = None
    ) -> List[Role]:
        """Get roles that user can assign to others."""
        ...
    
    async def invalidate_user_role_cache(self, user_id: str, tenant_id: Optional[str] = None) -> None:
        """Invalidate cached roles for a user."""
        ...


@runtime_checkable
class AccessControlServiceProtocol(Protocol):
    """Protocol for access control business logic operations."""
    
    async def compute_access_control(
        self,
        user_context: UserContext,
        resource: str,
        tenant_context: Optional[TenantContext] = None
    ) -> AccessControlEntry:
        """Compute complete access control for user-resource combination."""
        ...
    
    async def check_resource_access(
        self,
        user_context: UserContext,
        resource: str,
        action: str,
        tenant_context: Optional[TenantContext] = None
    ) -> bool:
        """Check if user can perform action on resource."""
        ...
    
    async def get_user_accessible_resources(
        self,
        user_context: UserContext,
        resource_type: str,
        tenant_context: Optional[TenantContext] = None
    ) -> List[str]:
        """Get resources user has access to."""
        ...
    
    async def validate_access_request(
        self,
        user_context: UserContext,
        resource: str,
        action: str,
        resource_id: Optional[str] = None,
        tenant_context: Optional[TenantContext] = None
    ) -> PermissionResult:
        """Validate complete access request with detailed result."""
        ...
    
    async def bulk_validate_access(
        self,
        user_context: UserContext,
        requests: List[tuple[str, str]],  # (resource, action) pairs
        tenant_context: Optional[TenantContext] = None
    ) -> Dict[str, PermissionResult]:
        """Validate multiple access requests in batch."""
        ...


@runtime_checkable 
class TokenValidationServiceProtocol(Protocol):
    """Protocol for Keycloak token validation operations."""
    
    async def validate_access_token(
        self,
        token: str,
        realm: Optional[str] = None
    ) -> SessionContext:
        """Validate Keycloak access token and extract session context."""
        ...
    
    async def introspect_token(
        self,
        token: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """Introspect token with Keycloak for real-time validation."""
        ...
    
    async def validate_token_claims(
        self,
        token_claims: Dict[str, Any],
        required_scopes: Optional[List[str]] = None,
        required_audience: Optional[str] = None
    ) -> bool:
        """Validate token claims meet requirements."""
        ...
    
    async def extract_user_context(
        self,
        token: str,
        tenant_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserContext:
        """Extract user context from validated token."""
        ...
    
    async def refresh_token_validation(
        self,
        refresh_token: str,
        realm: Optional[str] = None
    ) -> tuple[str, SessionContext]:
        """Validate refresh token and get new access token."""
        ...
    
    async def revoke_token(
        self,
        token: str,
        token_type: str = "access_token",
        realm: Optional[str] = None
    ) -> bool:
        """Revoke token in Keycloak."""
        ...
    
    async def get_realm_public_keys(self, realm: str) -> Dict[str, Any]:
        """Get public keys for JWT validation from realm."""
        ...
    
    async def validate_jwt_signature(
        self,
        token: str,
        realm: str
    ) -> Dict[str, Any]:
        """Validate JWT signature and return claims."""
        ...