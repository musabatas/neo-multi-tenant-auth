"""Domain protocols for neo-commons.

This module defines protocols for domain-level contracts and interfaces.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class TenantContextProtocol(Protocol):
    """Protocol for tenant context objects."""
    
    tenant_id: str
    schema_name: str
    region: str
    is_admin_request: bool
    metadata: Dict[str, Any]


@runtime_checkable
class UserIdentityProtocol(Protocol):
    """Protocol for user identity objects."""
    
    platform_id: str
    external_id: str
    email: str
    username: Optional[str]
    tenant_id: Optional[str]
    permissions: set[str]
    roles: set[str]


@runtime_checkable
class PermissionCheckerProtocol(Protocol):
    """Protocol for permission checking."""
    
    async def check_permission(
        self,
        user_id: str,
        permission: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if user has specific permission."""
        ...
    
    async def check_multiple_permissions(
        self,
        user_id: str,
        permissions: List[str],
        require_all: bool = True,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check multiple permissions."""
        ...
    
    async def get_user_permissions(
        self,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> set[str]:
        """Get all permissions for user."""
        ...


@runtime_checkable
class UserResolverProtocol(Protocol):
    """Protocol for user identity resolution."""
    
    async def resolve_user(
        self, 
        identifier: str, 
        tenant_id: Optional[str] = None
    ) -> Optional[UserIdentityProtocol]:
        """Resolve user identity from identifier."""
        ...
    
    async def create_or_update_user(
        self, 
        external_user: Dict[str, Any], 
        tenant_id: str
    ) -> UserIdentityProtocol:
        """Create or update user from external provider."""
        ...


@runtime_checkable
class SchemaResolverProtocol(Protocol):
    """Protocol for database schema resolution."""
    
    async def resolve_schema(self, tenant_id: Optional[str] = None) -> str:
        """Resolve database schema name for tenant."""
        ...
    
    def validate_schema_name(self, schema_name: str) -> str:
        """Validate and return safe schema name."""
        ...