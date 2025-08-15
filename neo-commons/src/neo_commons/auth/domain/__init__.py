"""
Authorization domain layer - Core business entities and rules.

This module contains pure business logic for authorization (roles, permissions, access control).
Authentication is handled by Keycloak externally.

Domain entities:
    - Permission: Fine-grained access control
    - Role: Collections of permissions
    - AccessControlEntry: User/role assignments
    - Session: Validated Keycloak session context

Business rules:
    - Permission implication logic
    - Role hierarchy validation
    - Multi-level RBAC (Platform vs Tenant)
    - Access control resolution
"""

from .entities.permission import Permission, PermissionScope, PermissionGroup
from .entities.role import Role, RoleLevel, RoleAssignment
from .entities.access_control import AccessControlEntry, AccessLevel
from .entities.session import Session, SessionContext, SessionStatus

from .value_objects.permission_check import PermissionCheck, PermissionResult
from .value_objects.user_context import UserContext, UserType
from .value_objects.tenant_context import TenantContext

from .protocols.repository_protocols import (
    PermissionRepositoryProtocol,
    RoleRepositoryProtocol, 
    AccessControlRepositoryProtocol,
    SessionRepositoryProtocol
)
from .protocols.service_protocols import (
    PermissionServiceProtocol,
    RoleServiceProtocol,
    AccessControlServiceProtocol,
    TokenValidationServiceProtocol
)
from .protocols.cache_protocols import (
    AuthCacheProtocol,
    PermissionCacheProtocol
)

__all__ = [
    # Entities
    "Permission",
    "PermissionScope", 
    "PermissionGroup",
    "Role",
    "RoleLevel",
    "RoleAssignment",
    "AccessControlEntry",
    "AccessLevel",
    "Session",
    "SessionContext",
    "SessionStatus",
    
    # Value Objects
    "PermissionCheck",
    "PermissionResult",
    "UserContext",
    "UserType",
    "TenantContext",
    
    # Protocols
    "PermissionRepositoryProtocol",
    "RoleRepositoryProtocol",
    "AccessControlRepositoryProtocol", 
    "SessionRepositoryProtocol",
    "PermissionServiceProtocol",
    "RoleServiceProtocol",
    "AccessControlServiceProtocol",
    "TokenValidationServiceProtocol",
    "AuthCacheProtocol",
    "PermissionCacheProtocol"
]