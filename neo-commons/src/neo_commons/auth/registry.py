"""
Permission registry with predefined platform and tenant permissions.
"""

# Platform-level permissions (system-wide operations)
PLATFORM_PERMISSIONS = [
    # Platform Administration
    {
        'code': 'platform:admin',
        'resource': 'platform',
        'action': 'admin',
        'description': 'Full platform administration access',
        'is_dangerous': True,
        'requires_mfa': True,
        'requires_approval': False
    },
    {
        'code': 'platform:read',
        'resource': 'platform',
        'action': 'read',
        'description': 'View platform configuration and settings',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'platform:write',
        'resource': 'platform',
        'action': 'write',
        'description': 'Modify platform configuration and settings',
        'is_dangerous': True,
        'requires_mfa': True,
        'requires_approval': False
    },
    
    # User Management
    {
        'code': 'users:read',
        'resource': 'users',
        'action': 'read',
        'description': 'View platform users',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'users:write',
        'resource': 'users',
        'action': 'write',
        'description': 'Create and modify platform users',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'users:delete',
        'resource': 'users',
        'action': 'delete',
        'description': 'Delete platform users',
        'is_dangerous': True,
        'requires_mfa': True,
        'requires_approval': False
    },
    
    # Role Management
    {
        'code': 'roles:read',
        'resource': 'roles',
        'action': 'read',
        'description': 'View platform roles and permissions',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'roles:write',
        'resource': 'roles',
        'action': 'write',
        'description': 'Create and modify platform roles',
        'is_dangerous': True,
        'requires_mfa': True,
        'requires_approval': False
    },
    {
        'code': 'roles:delete',
        'resource': 'roles',
        'action': 'delete',
        'description': 'Delete platform roles',
        'is_dangerous': True,
        'requires_mfa': True,
        'requires_approval': False
    },
    {
        'code': 'roles:assign',
        'resource': 'roles',
        'action': 'assign',
        'description': 'Assign roles to users',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    
    # Tenant Management
    {
        'code': 'tenants:read',
        'resource': 'tenants',
        'action': 'read',
        'description': 'View tenant information',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'tenants:write',
        'resource': 'tenants',
        'action': 'write',
        'description': 'Create and modify tenants',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'tenants:delete',
        'resource': 'tenants',
        'action': 'delete',
        'description': 'Delete tenants',
        'is_dangerous': True,
        'requires_mfa': True,
        'requires_approval': True
    },
    {
        'code': 'tenants:access',
        'resource': 'tenants',
        'action': 'access',
        'description': 'Access tenant context',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    
    # Organization Management
    {
        'code': 'organizations:read',
        'resource': 'organizations',
        'action': 'read',
        'description': 'View organization information',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'organizations:write',
        'resource': 'organizations',
        'action': 'write',
        'description': 'Create and modify organizations',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'organizations:delete',
        'resource': 'organizations',
        'action': 'delete',
        'description': 'Delete organizations',
        'is_dangerous': True,
        'requires_mfa': True,
        'requires_approval': True
    },
    
    # Billing and Subscriptions
    {
        'code': 'billing:read',
        'resource': 'billing',
        'action': 'read',
        'description': 'View billing information',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'billing:write',
        'resource': 'billing',
        'action': 'write',
        'description': 'Modify billing information',
        'is_dangerous': True,
        'requires_mfa': True,
        'requires_approval': False
    },
    {
        'code': 'subscriptions:read',
        'resource': 'subscriptions',
        'action': 'read',
        'description': 'View subscription plans',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'subscriptions:write',
        'resource': 'subscriptions',
        'action': 'write',
        'description': 'Manage subscription plans',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    
    # Audit and Monitoring
    {
        'code': 'audit:read',
        'resource': 'audit',
        'action': 'read',
        'description': 'View audit logs',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'audit:write',
        'resource': 'audit',
        'action': 'write',
        'description': 'Modify audit settings',
        'is_dangerous': True,
        'requires_mfa': True,
        'requires_approval': False
    },
    {
        'code': 'monitoring:read',
        'resource': 'monitoring',
        'action': 'read',
        'description': 'View system monitoring data',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    
    # Security Operations
    {
        'code': 'security:read',
        'resource': 'security',
        'action': 'read',
        'description': 'View security settings',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'security:write',
        'resource': 'security',
        'action': 'write',
        'description': 'Modify security settings',
        'is_dangerous': True,
        'requires_mfa': True,
        'requires_approval': True
    },
    
    # Database Operations
    {
        'code': 'database:read',
        'resource': 'database',
        'action': 'read',
        'description': 'View database connections',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'database:write',
        'resource': 'database',
        'action': 'write',
        'description': 'Manage database connections',
        'is_dangerous': True,
        'requires_mfa': True,
        'requires_approval': False
    },
    {
        'code': 'database:execute',
        'resource': 'database',
        'action': 'execute',
        'description': 'Execute database operations',
        'is_dangerous': True,
        'requires_mfa': True,
        'requires_approval': True
    }
]

# Tenant-level permissions (tenant-scoped operations)
TENANT_PERMISSIONS = [
    # Tenant Administration
    {
        'code': 'tenant:admin',
        'resource': 'tenant',
        'action': 'admin',
        'description': 'Full tenant administration access',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'tenant:read',
        'resource': 'tenant',
        'action': 'read',
        'description': 'View tenant settings',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'tenant:write',
        'resource': 'tenant',
        'action': 'write',
        'description': 'Modify tenant settings',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    
    # Tenant User Management
    {
        'code': 'tenant.users:read',
        'resource': 'tenant.users',
        'action': 'read',
        'description': 'View tenant users',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'tenant.users:write',
        'resource': 'tenant.users',
        'action': 'write',
        'description': 'Manage tenant users',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'tenant.users:delete',
        'resource': 'tenant.users',
        'action': 'delete',
        'description': 'Delete tenant users',
        'is_dangerous': True,
        'requires_mfa': False,
        'requires_approval': False
    },
    
    # Tenant Role Management
    {
        'code': 'tenant.roles:read',
        'resource': 'tenant.roles',
        'action': 'read',
        'description': 'View tenant roles',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'tenant.roles:write',
        'resource': 'tenant.roles',
        'action': 'write',
        'description': 'Manage tenant roles',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'tenant.roles:assign',
        'resource': 'tenant.roles',
        'action': 'assign',
        'description': 'Assign tenant roles to users',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    
    # Tenant Teams
    {
        'code': 'tenant.teams:read',
        'resource': 'tenant.teams',
        'action': 'read',
        'description': 'View tenant teams',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'tenant.teams:write',
        'resource': 'tenant.teams',
        'action': 'write',
        'description': 'Manage tenant teams',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    
    # Tenant Data
    {
        'code': 'tenant.data:read',
        'resource': 'tenant.data',
        'action': 'read',
        'description': 'View tenant data',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'tenant.data:write',
        'resource': 'tenant.data',
        'action': 'write',
        'description': 'Modify tenant data',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'tenant.data:delete',
        'resource': 'tenant.data',
        'action': 'delete',
        'description': 'Delete tenant data',
        'is_dangerous': True,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'tenant.data:export',
        'resource': 'tenant.data',
        'action': 'export',
        'description': 'Export tenant data',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'tenant.data:import',
        'resource': 'tenant.data',
        'action': 'import',
        'description': 'Import tenant data',
        'is_dangerous': True,
        'requires_mfa': False,
        'requires_approval': False
    },
    
    # Tenant Settings
    {
        'code': 'tenant.settings:read',
        'resource': 'tenant.settings',
        'action': 'read',
        'description': 'View tenant configuration',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'tenant.settings:write',
        'resource': 'tenant.settings',
        'action': 'write',
        'description': 'Modify tenant configuration',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    
    # Tenant Audit
    {
        'code': 'tenant.audit:read',
        'resource': 'tenant.audit',
        'action': 'read',
        'description': 'View tenant audit logs',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    
    # Tenant Billing
    {
        'code': 'tenant.billing:read',
        'resource': 'tenant.billing',
        'action': 'read',
        'description': 'View tenant billing information',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    },
    {
        'code': 'tenant.billing:write',
        'resource': 'tenant.billing',
        'action': 'write',
        'description': 'Manage tenant billing',
        'is_dangerous': False,
        'requires_mfa': False,
        'requires_approval': False
    }
]

# Permission groups for easier assignment
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