"""
Authorization domain entities.

Core business entities for the authorization system.
"""

from .permission import Permission, PermissionScope, PermissionGroup
from .role import Role, RoleLevel, RoleAssignment
from .access_control import AccessControlEntry, AccessLevel
from .session import Session, SessionContext, SessionStatus, UserType

__all__ = [
    # Permission entities
    "Permission",
    "PermissionScope",
    "PermissionGroup",
    
    # Role entities
    "Role",
    "RoleLevel", 
    "RoleAssignment",
    
    # Access control entities
    "AccessControlEntry",
    "AccessLevel",
    
    # Session entities
    "Session",
    "SessionContext",
    "SessionStatus",
    "UserType"
]