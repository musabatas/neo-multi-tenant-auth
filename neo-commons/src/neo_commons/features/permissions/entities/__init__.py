"""Permission entities package.

Domain entities and protocols for permission and role management.
"""

from .permission import Permission, PermissionCode
from .role import Role, RoleCode
from .protocols import (
    PermissionChecker,
    PermissionRepository,
    RoleRepository,
    UserRoleManager,
    PermissionCache
)

__all__ = [
    # Domain entities
    "Permission",
    "PermissionCode",
    "Role", 
    "RoleCode",
    
    # Protocols
    "PermissionChecker",
    "PermissionRepository",
    "RoleRepository", 
    "UserRoleManager",
    "PermissionCache",
]