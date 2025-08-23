"""Permissions feature for neo-commons.

Feature-First architecture for permission and role management:
- entities/: Permission domain objects, roles, and protocols
- services/: Permission business logic and orchestration
- repositories/: Permission data access and role management
"""

# Core permission entities and protocols
from .entities import (
    Permission, PermissionCode, Role, RoleCode,
    PermissionChecker, PermissionRepository, RoleRepository, 
    UserRoleManager, PermissionCache
)

# Permission service orchestration  
from .services import PermissionService

# Concrete repository implementations
from .repositories import AsyncPGPermissionRepository, AsyncPGRoleRepository

__all__ = [
    # Entities
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
    
    # Services
    "PermissionService",
    
    # Repository Implementations
    "AsyncPGPermissionRepository",
    "AsyncPGRoleRepository",
]