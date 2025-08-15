"""
Authorization domain protocols.

Protocol interfaces defining contracts for repository and service layers.
"""

from .repository_protocols import (
    PermissionRepositoryProtocol,
    RoleRepositoryProtocol,
    AccessControlRepositoryProtocol,
    SessionRepositoryProtocol
)
from .service_protocols import (
    PermissionServiceProtocol,
    RoleServiceProtocol,
    AccessControlServiceProtocol,
    TokenValidationServiceProtocol
)
from .cache_protocols import (
    AuthCacheProtocol,
    PermissionCacheProtocol
)

__all__ = [
    # Repository protocols
    "PermissionRepositoryProtocol",
    "RoleRepositoryProtocol",
    "AccessControlRepositoryProtocol",
    "SessionRepositoryProtocol",
    
    # Service protocols
    "PermissionServiceProtocol",
    "RoleServiceProtocol", 
    "AccessControlServiceProtocol",
    "TokenValidationServiceProtocol",
    
    # Cache protocols
    "AuthCacheProtocol",
    "PermissionCacheProtocol"
]