"""
Permission Registry Module

Central permission registry and validation system with:
- Platform and tenant permission definitions
- Permission validation and group management
- Dynamic permission discovery from decorated endpoints
- Integration with permission checking services
"""

from .permissions import (
    PermissionRegistry,
    PLATFORM_PERMISSIONS,
    TENANT_PERMISSIONS,
    PERMISSION_GROUPS,
    PermissionDefinition,
    get_permission_registry
)

__all__ = [
    "PermissionRegistry",
    "PLATFORM_PERMISSIONS",
    "TENANT_PERMISSIONS", 
    "PERMISSION_GROUPS",
    "PermissionDefinition",
    "get_permission_registry"
]