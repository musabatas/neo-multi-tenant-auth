"""
Permission Registry Implementation

Protocol-compliant permission registry implementing central permission management with:
- Platform and tenant permission definitions 
- Permission validation and security flagging
- Group-based permission assignment patterns
- Dynamic endpoint permission discovery
- Integration with permission checking protocols
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..protocols import PermissionRegistryProtocol


@dataclass
class PermissionDefinition:
    """
    Structured permission definition with security metadata.
    
    Provides standardized permission representation with security controls,
    validation requirements, and organizational metadata.
    """
    code: str
    resource: str
    action: str
    description: str
    is_dangerous: bool = False
    requires_mfa: bool = False
    requires_approval: bool = False
    scope: str = "platform"  # platform, tenant, user
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage or API responses."""
        return {
            'code': self.code,
            'resource': self.resource,
            'action': self.action,
            'description': self.description,
            'is_dangerous': self.is_dangerous,
            'requires_mfa': self.requires_mfa,
            'requires_approval': self.requires_approval,
            'scope': self.scope
        }


# Platform-level permissions (system-wide operations) extracted from source
PLATFORM_PERMISSIONS = [
    # Platform Administration
    PermissionDefinition(
        code='platform:admin',
        resource='platform',
        action='admin',
        description='Full platform administration access',
        is_dangerous=True,
        requires_mfa=True,
        requires_approval=False,
        scope='platform'
    ),
    PermissionDefinition(
        code='platform:read',
        resource='platform',
        action='read',
        description='View platform configuration and settings',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='platform'
    ),
    PermissionDefinition(
        code='platform:write',
        resource='platform',
        action='write',
        description='Modify platform configuration and settings',
        is_dangerous=True,
        requires_mfa=True,
        requires_approval=False,
        scope='platform'
    ),
    
    # User Management
    PermissionDefinition(
        code='users:read',
        resource='users',
        action='read',
        description='View platform users',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='platform'
    ),
    PermissionDefinition(
        code='users:write',
        resource='users',
        action='write',
        description='Create and modify platform users',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='platform'
    ),
    PermissionDefinition(
        code='users:delete',
        resource='users',
        action='delete',
        description='Delete platform users',
        is_dangerous=True,
        requires_mfa=True,
        requires_approval=False,
        scope='platform'
    ),
    
    # Role Management
    PermissionDefinition(
        code='roles:read',
        resource='roles',
        action='read',
        description='View platform roles and permissions',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='platform'
    ),
    PermissionDefinition(
        code='roles:write',
        resource='roles',
        action='write',
        description='Create and modify platform roles',
        is_dangerous=True,
        requires_mfa=True,
        requires_approval=False,
        scope='platform'
    ),
    PermissionDefinition(
        code='roles:delete',
        resource='roles',
        action='delete',
        description='Delete platform roles',
        is_dangerous=True,
        requires_mfa=True,
        requires_approval=False,
        scope='platform'
    ),
    PermissionDefinition(
        code='roles:assign',
        resource='roles',
        action='assign',
        description='Assign roles to users',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='platform'
    ),
    
    # Tenant Management
    PermissionDefinition(
        code='tenants:read',
        resource='tenants',
        action='read',
        description='View tenant information',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='platform'
    ),
    PermissionDefinition(
        code='tenants:write',
        resource='tenants',
        action='write',
        description='Create and modify tenants',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='platform'
    ),
    PermissionDefinition(
        code='tenants:delete',
        resource='tenants',
        action='delete',
        description='Delete tenants',
        is_dangerous=True,
        requires_mfa=True,
        requires_approval=True,
        scope='platform'
    ),
    PermissionDefinition(
        code='tenants:access',
        resource='tenants',
        action='access',
        description='Access tenant context',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='platform'
    ),
    
    # Organization Management
    PermissionDefinition(
        code='organizations:read',
        resource='organizations',
        action='read',
        description='View organization information',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='platform'
    ),
    PermissionDefinition(
        code='organizations:write',
        resource='organizations',
        action='write',
        description='Create and modify organizations',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='platform'
    ),
    PermissionDefinition(
        code='organizations:delete',
        resource='organizations',
        action='delete',
        description='Delete organizations',
        is_dangerous=True,
        requires_mfa=True,
        requires_approval=True,
        scope='platform'
    ),
    
    # Billing and Subscriptions
    PermissionDefinition(
        code='billing:read',
        resource='billing',
        action='read',
        description='View billing information',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='platform'
    ),
    PermissionDefinition(
        code='billing:write',
        resource='billing',
        action='write',
        description='Modify billing information',
        is_dangerous=True,
        requires_mfa=True,
        requires_approval=False,
        scope='platform'
    ),
    PermissionDefinition(
        code='subscriptions:read',
        resource='subscriptions',
        action='read',
        description='View subscription plans',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='platform'
    ),
    PermissionDefinition(
        code='subscriptions:write',
        resource='subscriptions',
        action='write',
        description='Manage subscription plans',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='platform'
    ),
    
    # Reference Data (for guest authentication)
    PermissionDefinition(
        code='reference_data:read',
        resource='reference_data',
        action='read',
        description='Access public reference data (currencies, countries, etc.)',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='platform'
    ),
    
    # Audit and Monitoring
    PermissionDefinition(
        code='audit:read',
        resource='audit',
        action='read',
        description='View audit logs',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='platform'
    ),
    PermissionDefinition(
        code='audit:write',
        resource='audit',
        action='write',
        description='Modify audit settings',
        is_dangerous=True,
        requires_mfa=True,
        requires_approval=False,
        scope='platform'
    ),
    PermissionDefinition(
        code='monitoring:read',
        resource='monitoring',
        action='read',
        description='View system monitoring data',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='platform'
    ),
    
    # Security Operations
    PermissionDefinition(
        code='security:read',
        resource='security',
        action='read',
        description='View security settings',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='platform'
    ),
    PermissionDefinition(
        code='security:write',
        resource='security',
        action='write',
        description='Modify security settings',
        is_dangerous=True,
        requires_mfa=True,
        requires_approval=True,
        scope='platform'
    ),
    
    # Database Operations
    PermissionDefinition(
        code='database:read',
        resource='database',
        action='read',
        description='View database connections',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='platform'
    ),
    PermissionDefinition(
        code='database:write',
        resource='database',
        action='write',
        description='Manage database connections',
        is_dangerous=True,
        requires_mfa=True,
        requires_approval=False,
        scope='platform'
    ),
    PermissionDefinition(
        code='database:execute',
        resource='database',
        action='execute',
        description='Execute database operations',
        is_dangerous=True,
        requires_mfa=True,
        requires_approval=True,
        scope='platform'
    )
]

# Tenant-level permissions (tenant-scoped operations) extracted from source
TENANT_PERMISSIONS = [
    # Tenant Administration
    PermissionDefinition(
        code='tenant:admin',
        resource='tenant',
        action='admin',
        description='Full tenant administration access',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='tenant'
    ),
    PermissionDefinition(
        code='tenant:read',
        resource='tenant',
        action='read',
        description='View tenant settings',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='tenant'
    ),
    PermissionDefinition(
        code='tenant:write',
        resource='tenant',
        action='write',
        description='Modify tenant settings',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='tenant'
    ),
    
    # Tenant User Management
    PermissionDefinition(
        code='tenant.users:read',
        resource='tenant.users',
        action='read',
        description='View tenant users',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='tenant'
    ),
    PermissionDefinition(
        code='tenant.users:write',
        resource='tenant.users',
        action='write',
        description='Manage tenant users',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='tenant'
    ),
    PermissionDefinition(
        code='tenant.users:delete',
        resource='tenant.users',
        action='delete',
        description='Delete tenant users',
        is_dangerous=True,
        requires_mfa=False,
        requires_approval=False,
        scope='tenant'
    ),
    
    # Tenant Role Management
    PermissionDefinition(
        code='tenant.roles:read',
        resource='tenant.roles',
        action='read',
        description='View tenant roles',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='tenant'
    ),
    PermissionDefinition(
        code='tenant.roles:write',
        resource='tenant.roles',
        action='write',
        description='Manage tenant roles',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='tenant'
    ),
    PermissionDefinition(
        code='tenant.roles:assign',
        resource='tenant.roles',
        action='assign',
        description='Assign tenant roles to users',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='tenant'
    ),
    
    # Tenant Teams
    PermissionDefinition(
        code='tenant.teams:read',
        resource='tenant.teams',
        action='read',
        description='View tenant teams',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='tenant'
    ),
    PermissionDefinition(
        code='tenant.teams:write',
        resource='tenant.teams',
        action='write',
        description='Manage tenant teams',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='tenant'
    ),
    
    # Tenant Data
    PermissionDefinition(
        code='tenant.data:read',
        resource='tenant.data',
        action='read',
        description='View tenant data',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='tenant'
    ),
    PermissionDefinition(
        code='tenant.data:write',
        resource='tenant.data',
        action='write',
        description='Modify tenant data',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='tenant'
    ),
    PermissionDefinition(
        code='tenant.data:delete',
        resource='tenant.data',
        action='delete',
        description='Delete tenant data',
        is_dangerous=True,
        requires_mfa=False,
        requires_approval=False,
        scope='tenant'
    ),
    PermissionDefinition(
        code='tenant.data:export',
        resource='tenant.data',
        action='export',
        description='Export tenant data',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='tenant'
    ),
    PermissionDefinition(
        code='tenant.data:import',
        resource='tenant.data',
        action='import',
        description='Import tenant data',
        is_dangerous=True,
        requires_mfa=False,
        requires_approval=False,
        scope='tenant'
    ),
    
    # Tenant Settings
    PermissionDefinition(
        code='tenant.settings:read',
        resource='tenant.settings',
        action='read',
        description='View tenant configuration',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='tenant'
    ),
    PermissionDefinition(
        code='tenant.settings:write',
        resource='tenant.settings',
        action='write',
        description='Modify tenant configuration',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='tenant'
    ),
    
    # Tenant Audit
    PermissionDefinition(
        code='tenant.audit:read',
        resource='tenant.audit',
        action='read',
        description='View tenant audit logs',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='tenant'
    ),
    
    # Tenant Billing
    PermissionDefinition(
        code='tenant.billing:read',
        resource='tenant.billing',
        action='read',
        description='View tenant billing information',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='tenant'
    ),
    PermissionDefinition(
        code='tenant.billing:write',
        resource='tenant.billing',
        action='write',
        description='Manage tenant billing',
        is_dangerous=False,
        requires_mfa=False,
        requires_approval=False,
        scope='tenant'
    )
]

# Permission groups for easier assignment (matching source)
PERMISSION_GROUPS = {
    'platform_admin': [
        'platform:admin',
        'users:*',
        'roles:*',
        'tenants:*',
        'organizations:*',
        'billing:*',
        'subscriptions:*',
        'audit:*',
        'monitoring:*',
        'security:*',
        'database:*'
    ],
    'platform_operator': [
        'platform:read',
        'users:read',
        'roles:read',
        'tenants:read',
        'organizations:read',
        'audit:read',
        'monitoring:read'
    ],
    'tenant_admin': [
        'tenant:admin',
        'tenant.users:*',
        'tenant.roles:*',
        'tenant.teams:*',
        'tenant.data:*',
        'tenant.settings:*',
        'tenant.audit:*',
        'tenant.billing:*'
    ],
    'tenant_user': [
        'tenant:read',
        'tenant.data:read',
        'tenant.settings:read'
    ]
}


class PermissionRegistry(PermissionRegistryProtocol):
    """
    Protocol-compliant permission registry implementation.
    
    Provides centralized permission management with validation, grouping,
    and dynamic discovery capabilities for permission-based security.
    
    Features:
    - Platform and tenant permission registration
    - Permission validation with security flags
    - Group-based permission expansion
    - Dynamic endpoint permission discovery
    - Wildcard permission matching
    """
    
    def __init__(self):
        """Initialize permission registry with platform and tenant permissions."""
        self._permissions: Dict[str, PermissionDefinition] = {}
        self._groups: Dict[str, List[str]] = PERMISSION_GROUPS.copy()
        
        # Register platform and tenant permissions
        self._register_permissions(PLATFORM_PERMISSIONS)
        self._register_permissions(TENANT_PERMISSIONS)
        
        print(f"Permission registry initialized with {len(self._permissions)} permissions")
    
    def _register_permissions(self, permissions: List[PermissionDefinition]) -> None:
        """Register a list of permission definitions."""
        for perm in permissions:
            self._permissions[perm.code] = perm
    
    async def validate_permission(self, permission_code: str) -> bool:
        """
        Validate if a permission code exists in the registry.
        
        Args:
            permission_code: Permission code to validate
            
        Returns:
            True if permission exists, False otherwise
        """
        return permission_code in self._permissions
    
    async def get_permission(self, permission_code: str) -> Optional[PermissionDefinition]:
        """
        Get permission definition by code.
        
        Args:
            permission_code: Permission code to lookup
            
        Returns:
            Permission definition if found, None otherwise
        """
        return self._permissions.get(permission_code)
    
    async def get_permissions_by_scope(self, scope: str) -> List[PermissionDefinition]:
        """
        Get all permissions for a specific scope.
        
        Args:
            scope: Permission scope ('platform', 'tenant', 'user')
            
        Returns:
            List of permission definitions for the scope
        """
        return [perm for perm in self._permissions.values() if perm.scope == scope]
    
    async def get_dangerous_permissions(self) -> List[PermissionDefinition]:
        """
        Get all permissions marked as dangerous.
        
        Returns:
            List of dangerous permission definitions
        """
        return [perm for perm in self._permissions.values() if perm.is_dangerous]
    
    async def get_mfa_required_permissions(self) -> List[PermissionDefinition]:
        """
        Get all permissions requiring MFA.
        
        Returns:
            List of permission definitions requiring MFA
        """
        return [perm for perm in self._permissions.values() if perm.requires_mfa]
    
    async def get_approval_required_permissions(self) -> List[PermissionDefinition]:
        """
        Get all permissions requiring approval.
        
        Returns:
            List of permission definitions requiring approval
        """
        return [perm for perm in self._permissions.values() if perm.requires_approval]
    
    async def expand_permission_group(self, group_name: str) -> List[str]:
        """
        Expand a permission group to individual permission codes.
        
        Supports wildcard expansion (e.g., 'users:*' expands to all user permissions).
        
        Args:
            group_name: Name of permission group
            
        Returns:
            List of expanded permission codes
        """
        if group_name not in self._groups:
            print(f"Warning: Permission group '{group_name}' not found")
            return []
        
        expanded_permissions = []
        for perm_pattern in self._groups[group_name]:
            if perm_pattern.endswith(':*'):
                # Wildcard expansion (matching source logic)
                resource_prefix = perm_pattern[:-2]  # Remove ':*'
                matching_perms = [
                    code for code in self._permissions.keys()
                    if code.startswith(f"{resource_prefix}:")
                ]
                expanded_permissions.extend(matching_perms)
            else:
                expanded_permissions.append(perm_pattern)
        
        return list(set(expanded_permissions))  # Remove duplicates
    
    async def check_permission_security(self, permission_code: str) -> Dict[str, Any]:
        """
        Check security requirements for a permission.
        
        Args:
            permission_code: Permission code to check
            
        Returns:
            Dictionary with security requirements
        """
        perm = await self.get_permission(permission_code)
        if not perm:
            return {"valid": False, "error": "Permission not found"}
        
        return {
            "valid": True,
            "permission": perm.code,
            "is_dangerous": perm.is_dangerous,
            "requires_mfa": perm.requires_mfa,
            "requires_approval": perm.requires_approval,
            "scope": perm.scope,
            "description": perm.description
        }
    
    async def list_all_permissions(self) -> List[PermissionDefinition]:
        """
        Get all registered permissions.
        
        Returns:
            List of all permission definitions
        """
        return list(self._permissions.values())
    
    async def list_permission_codes(self) -> List[str]:
        """
        Get all registered permission codes.
        
        Returns:
            List of all permission codes
        """
        return list(self._permissions.keys())
    
    async def get_resource_permissions(self, resource: str) -> List[PermissionDefinition]:
        """
        Get all permissions for a specific resource.
        
        Args:
            resource: Resource name (e.g., 'users', 'tenants')
            
        Returns:
            List of permission definitions for the resource
        """
        return [perm for perm in self._permissions.values() if perm.resource == resource]
    
    async def register_dynamic_permission(self, permission: PermissionDefinition) -> bool:
        """
        Register a dynamic permission at runtime.
        
        Args:
            permission: Permission definition to register
            
        Returns:
            True if registration successful, False if already exists
        """
        if permission.code in self._permissions:
            print(f"Warning: Permission '{permission.code}' already exists")
            return False
        
        self._permissions[permission.code] = permission
        print(f"Registered dynamic permission: {permission.code}")
        return True
    
    async def get_permissions_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics of the permission registry.
        
        Returns:
            Dictionary with registry statistics
        """
        total_perms = len(self._permissions)
        dangerous_count = len([p for p in self._permissions.values() if p.is_dangerous])
        mfa_count = len([p for p in self._permissions.values() if p.requires_mfa])
        approval_count = len([p for p in self._permissions.values() if p.requires_approval])
        
        scope_counts = {}
        for perm in self._permissions.values():
            scope_counts[perm.scope] = scope_counts.get(perm.scope, 0) + 1
        
        return {
            "total_permissions": total_perms,
            "dangerous_permissions": dangerous_count,
            "mfa_required_permissions": mfa_count,
            "approval_required_permissions": approval_count,
            "permissions_by_scope": scope_counts,
            "permission_groups": len(self._groups)
        }


# Global registry instance
_permission_registry = None

def get_permission_registry() -> PermissionRegistry:
    """
    Get the global permission registry instance.
    
    Returns:
        Global PermissionRegistry instance
    """
    global _permission_registry
    if _permission_registry is None:
        _permission_registry = PermissionRegistry()
    return _permission_registry