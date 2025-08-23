-- NeoMultiTenant - Seed Data: Roles and Permissions
-- This seed file populates comprehensive starter roles and permissions
-- Run with: ./deploy.sh --seed

-- ============================================================================
-- COMPREHENSIVE PERMISSIONS: Define all system permissions
-- ============================================================================

-- Clear existing permissions and roles (for development only)
TRUNCATE admin.role_permissions CASCADE;
DELETE FROM admin.permissions WHERE id NOT IN (
    SELECT id FROM admin.permissions LIMIT 0
);

-- Insert comprehensive permissions based on database design
INSERT INTO admin.permissions (code, description, resource, action, scope_level) VALUES
-- ============================================================================
-- PLATFORM-LEVEL PERMISSIONS (Global scope)
-- ============================================================================

-- Platform Administration
('platform.admin.read', 'Read platform administration data', 'platform', 'read', 'platform'),
('platform.admin.write', 'Modify platform administration data', 'platform', 'write', 'platform'),
('platform.admin.delete', 'Delete platform administration data', 'platform', 'delete', 'platform'),

-- User Management  
('platform.users.read', 'View platform users', 'users', 'read', 'platform'),
('platform.users.write', 'Manage platform users', 'users', 'write', 'platform'),
('platform.users.delete', 'Delete platform users', 'users', 'delete', 'platform'),
('platform.users.impersonate', 'Impersonate other users for support', 'users', 'impersonate', 'platform'),

-- Role & Permission Management
('platform.roles.read', 'View platform roles', 'roles', 'read', 'platform'),
('platform.roles.write', 'Manage platform roles', 'roles', 'write', 'platform'),
('platform.roles.delete', 'Delete platform roles', 'roles', 'delete', 'platform'),
('platform.permissions.read', 'View platform permissions', 'permissions', 'read', 'platform'),
('platform.permissions.write', 'Manage platform permissions', 'permissions', 'write', 'platform'),

-- Organization Management
('platform.organizations.read', 'View organizations', 'organizations', 'read', 'platform'),
('platform.organizations.write', 'Manage organizations', 'organizations', 'write', 'platform'),
('platform.organizations.delete', 'Delete organizations', 'organizations', 'delete', 'platform'),

-- Tenant Management
('platform.tenants.read', 'View tenant information', 'tenants', 'read', 'platform'),
('platform.tenants.write', 'Manage tenants', 'tenants', 'write', 'platform'),
('platform.tenants.delete', 'Delete tenants', 'tenants', 'delete', 'platform'),
('platform.tenants.suspend', 'Suspend tenant operations', 'tenants', 'suspend', 'platform'),

-- Regional Infrastructure
('platform.regions.read', 'View regional information', 'regions', 'read', 'platform'),
('platform.regions.write', 'Manage regional settings', 'regions', 'write', 'platform'),
('platform.regions.delete', 'Delete regions', 'regions', 'delete', 'platform'),

-- Database Management
('platform.databases.read', 'View database connections', 'databases', 'read', 'platform'),
('platform.databases.write', 'Manage database connections', 'databases', 'write', 'platform'),
('platform.databases.execute', 'Execute database operations', 'databases', 'execute', 'platform'),
('platform.databases.health_check', 'Perform database health checks', 'databases', 'health_check', 'platform'),

-- Migration Management
('platform.migrations.read', 'View migration status', 'migrations', 'read', 'platform'),
('platform.migrations.write', 'Execute migrations', 'migrations', 'write', 'platform'),
('platform.migrations.rollback', 'Rollback migrations', 'migrations', 'rollback', 'platform'),

-- Billing & Subscriptions
('platform.billing.read', 'View billing information', 'billing', 'read', 'platform'),
('platform.billing.write', 'Manage billing and subscriptions', 'billing', 'write', 'platform'),
('platform.billing.process', 'Process payments and invoices', 'billing', 'process', 'platform'),

-- Subscription Plans
('platform.plans.read', 'View subscription plans', 'plans', 'read', 'platform'),
('platform.plans.write', 'Manage subscription plans', 'plans', 'write', 'platform'),
('platform.plans.delete', 'Delete subscription plans', 'plans', 'delete', 'platform'),

-- Payment Management
('platform.payments.read', 'View payment transactions', 'payments', 'read', 'platform'),
('platform.payments.write', 'Manage payment methods', 'payments', 'write', 'platform'),
('platform.payments.refund', 'Process refunds', 'payments', 'refund', 'platform'),

-- System Monitoring
('platform.monitoring.read', 'View system monitoring data', 'monitoring', 'read', 'platform'),
('platform.monitoring.write', 'Manage monitoring settings', 'monitoring', 'write', 'platform'),
('platform.alerts.read', 'View system alerts', 'alerts', 'read', 'platform'),
('platform.alerts.write', 'Manage system alerts', 'alerts', 'write', 'platform'),
('platform.alerts.acknowledge', 'Acknowledge system alerts', 'alerts', 'acknowledge', 'platform'),

-- API Rate Limiting
('platform.rate_limits.read', 'View API rate limits', 'rate_limits', 'read', 'platform'),
('platform.rate_limits.write', 'Manage API rate limits', 'rate_limits', 'write', 'platform'),

-- Audit & Logging
('platform.audit.read', 'View audit logs', 'audit', 'read', 'platform'),
('platform.audit.write', 'Manage audit settings', 'audit', 'write', 'platform'),
('platform.logs.read', 'View system logs', 'logs', 'read', 'platform'),

-- Support & Maintenance
('platform.support.read', 'View support tickets', 'support', 'read', 'platform'),
('platform.support.write', 'Manage support tickets', 'support', 'write', 'platform'),
('platform.maintenance.read', 'View maintenance status', 'maintenance', 'read', 'platform'),
('platform.maintenance.write', 'Manage maintenance windows', 'maintenance', 'write', 'platform'),

-- ============================================================================
-- TENANT-LEVEL PERMISSIONS (Tenant scope)
-- ============================================================================

-- Tenant Administration
('tenant.admin.read', 'Read tenant administration data', 'tenant', 'read', 'tenant'),
('tenant.admin.write', 'Modify tenant administration data', 'tenant', 'write', 'tenant'),

-- User Management within Tenant
('tenant.users.read', 'View tenant users', 'users', 'read', 'tenant'),
('tenant.users.write', 'Manage tenant users', 'users', 'write', 'tenant'),
('tenant.users.delete', 'Delete tenant users', 'users', 'delete', 'tenant'),
('tenant.users.invite', 'Invite new users to tenant', 'users', 'invite', 'tenant'),

-- Role & Permission Management within Tenant
('tenant.roles.read', 'View tenant roles', 'roles', 'read', 'tenant'),
('tenant.roles.write', 'Manage tenant roles', 'roles', 'write', 'tenant'),
('tenant.permissions.read', 'View tenant permissions', 'permissions', 'read', 'tenant'),

-- Team Management
('tenant.teams.read', 'View teams', 'teams', 'read', 'tenant'),
('tenant.teams.write', 'Manage teams', 'teams', 'write', 'tenant'),
('tenant.teams.delete', 'Delete teams', 'teams', 'delete', 'tenant'),
('tenant.teams.join', 'Join teams', 'teams', 'join', 'tenant'),
('tenant.teams.leave', 'Leave teams', 'teams', 'leave', 'tenant'),

-- Settings & Configuration
('tenant.settings.read', 'View tenant settings', 'settings', 'read', 'tenant'),
('tenant.settings.write', 'Manage tenant settings', 'settings', 'write', 'tenant'),

-- Billing & Usage within Tenant
('tenant.billing.read', 'View tenant billing information', 'billing', 'read', 'tenant'),
('tenant.billing.write', 'Manage tenant billing', 'billing', 'write', 'tenant'),
('tenant.quotas.read', 'View tenant quotas', 'quotas', 'read', 'tenant'),
('tenant.usage.read', 'View tenant usage metrics', 'usage', 'read', 'tenant'),

-- Analytics & Reporting
('tenant.analytics.read', 'View tenant analytics', 'analytics', 'read', 'tenant'),
('tenant.reports.read', 'View tenant reports', 'reports', 'read', 'tenant'),
('tenant.reports.export', 'Export tenant reports', 'reports', 'export', 'tenant'),

-- API & Integration Management
('tenant.api.read', 'View API configurations', 'api', 'read', 'tenant'),
('tenant.api.write', 'Manage API configurations', 'api', 'write', 'tenant'),
('tenant.webhooks.read', 'View webhook configurations', 'webhooks', 'read', 'tenant'),
('tenant.webhooks.write', 'Manage webhook configurations', 'webhooks', 'write', 'tenant'),

-- Contacts & Communication
('tenant.contacts.read', 'View tenant contacts', 'contacts', 'read', 'tenant'),
('tenant.contacts.write', 'Manage tenant contacts', 'contacts', 'write', 'tenant'),

-- Profile & Personal Data
('tenant.profile.read', 'View own profile', 'profile', 'read', 'tenant'),
('tenant.profile.write', 'Manage own profile', 'profile', 'write', 'tenant')

ON CONFLICT (code) DO UPDATE SET
    description = EXCLUDED.description,
    resource = EXCLUDED.resource,
    action = EXCLUDED.action,
    scope_level = EXCLUDED.scope_level,
    updated_at = NOW();

-- ============================================================================
-- PLATFORM ROLES: Define comprehensive role hierarchy
-- ============================================================================

-- Clear existing roles (for development only)
DELETE FROM admin.roles WHERE is_system = false;

-- Insert/Update comprehensive starter roles
INSERT INTO admin.roles (
    code, name, display_name, description, role_level, priority, 
    is_system, is_default, scope_type, requires_approval
) VALUES 
-- System-level roles (highest privilege)
(
    'super_admin',
    'Super Administrator',
    'Super Admin',
    'Full system access with all permissions. Can manage infrastructure, platform settings, and all tenants.',
    'system',
    1000,
    true,
    false,
    'global',
    false
),
(
    'system_architect',
    'System Architect',
    'System Architect',
    'Infrastructure and architecture management. Can configure regions, databases, and system settings.',
    'system',
    950,
    true,
    false,
    'global',
    true
),

-- Platform-level roles (platform management)
(
    'platform_admin',
    'Platform Administrator',
    'Platform Admin',
    'Platform-wide administration. Can manage organizations, tenants, and platform users.',
    'platform',
    900,
    true,
    false,
    'global',
    false
),
(
    'platform_operator',
    'Platform Operator',
    'Platform Operator',
    'Day-to-day platform operations. Can view and manage tenant issues, monitor health, and handle support.',
    'platform',
    850,
    false,
    false,
    'global',
    false
),
(
    'platform_developer',
    'Platform Developer',
    'Platform Developer',
    'Development and integration access. Can manage APIs, webhooks, and platform integrations.',
    'platform',
    800,
    false,
    false,
    'global',
    false
),
(
    'platform_billing_admin',
    'Platform Billing Administrator',
    'Billing Admin',
    'Billing and payment management across all tenants.',
    'platform',
    780,
    false,
    false,
    'global',
    false
),
(
    'platform_support',
    'Platform Support',
    'Support Staff',
    'Customer support access. Can view tenant information and assist with issues.',
    'platform',
    750,
    false,
    false,
    'global',
    false
),
(
    'platform_auditor',
    'Platform Auditor',
    'Auditor',
    'Read-only access for compliance and auditing. Can view all logs and audit trails.',
    'platform',
    700,
    false,
    false,
    'global',
    false
),
(
    'platform_viewer',
    'Platform Viewer',
    'Viewer',
    'Read-only access to platform information. Cannot make any changes.',
    'platform',
    600,
    false,
    true,
    'global',
    false
),

-- Tenant-level roles (tenant-specific)
(
    'tenant_owner',
    'Tenant Owner',
    'Owner',
    'Full control over tenant. Can manage all tenant settings, users, and data.',
    'tenant',
    500,
    true,
    false,
    'tenant',
    false
),
(
    'tenant_admin',
    'Tenant Administrator',
    'Admin',
    'Tenant administration. Can manage users, roles, and most settings within the tenant.',
    'tenant',
    450,
    true,
    false,
    'tenant',
    false
),
(
    'tenant_billing_manager',
    'Tenant Billing Manager',
    'Billing Manager',
    'Tenant billing and subscription management.',
    'tenant',
    420,
    false,
    false,
    'tenant',
    false
),
(
    'tenant_manager',
    'Tenant Manager',
    'Manager',
    'Team and resource management. Can manage teams, projects, and workflows.',
    'tenant',
    400,
    false,
    false,
    'tenant',
    false
),
(
    'tenant_developer',
    'Tenant Developer',
    'Developer',
    'Development access within tenant. Can manage APIs, integrations, and custom fields.',
    'tenant',
    350,
    false,
    false,
    'tenant',
    false
),
(
    'tenant_analyst',
    'Tenant Analyst',
    'Analyst',
    'Analytics and reporting access. Can view reports, export data, and create dashboards.',
    'tenant',
    300,
    false,
    false,
    'tenant',
    false
),
(
    'tenant_user',
    'Tenant User',
    'User',
    'Standard user access. Can use tenant features and manage own profile.',
    'tenant',
    200,
    true,
    true,
    'tenant',
    false
),
(
    'tenant_guest',
    'Tenant Guest',
    'Guest',
    'Limited guest access. Read-only access to specific resources.',
    'tenant',
    100,
    false,
    false,
    'tenant',
    false
)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    priority = EXCLUDED.priority,
    updated_at = NOW();

-- ============================================================================
-- ROLE PERMISSIONS: Assign comprehensive permissions to roles
-- ============================================================================

-- Helper function to assign permissions to roles using direct INSERT/SELECT
CREATE OR REPLACE FUNCTION admin.assign_permissions_to_role(
    p_role_code VARCHAR,
    p_permissions TEXT[]
) RETURNS void AS $$
BEGIN
    -- Clear existing permissions for this role
    DELETE FROM admin.role_permissions 
    WHERE role_id = (SELECT id FROM admin.roles WHERE code = p_role_code);
    
    -- Assign permissions using INSERT/SELECT
    INSERT INTO admin.role_permissions (role_id, permission_id)
    SELECT 
        r.id as role_id,
        p.id as permission_id
    FROM admin.roles r
    CROSS JOIN admin.permissions p
    WHERE r.code = p_role_code 
        AND p.code = ANY(p_permissions)
    ON CONFLICT (role_id, permission_id) DO NOTHING;
    
    -- Log assignment
    RAISE NOTICE 'Assigned % permissions to role %', 
        array_length(p_permissions, 1), p_role_code;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- ASSIGN PERMISSIONS TO ROLES
-- ============================================================================

-- Super Admin: All platform permissions
SELECT admin.assign_permissions_to_role('super_admin', ARRAY[
    'platform.admin.read', 'platform.admin.write', 'platform.admin.delete',
    'platform.users.read', 'platform.users.write', 'platform.users.delete', 'platform.users.impersonate',
    'platform.roles.read', 'platform.roles.write', 'platform.roles.delete',
    'platform.permissions.read', 'platform.permissions.write',
    'platform.organizations.read', 'platform.organizations.write', 'platform.organizations.delete',
    'platform.tenants.read', 'platform.tenants.write', 'platform.tenants.delete', 'platform.tenants.suspend',
    'platform.regions.read', 'platform.regions.write', 'platform.regions.delete',
    'platform.databases.read', 'platform.databases.write', 'platform.databases.execute', 'platform.databases.health_check',
    'platform.migrations.read', 'platform.migrations.write', 'platform.migrations.rollback',
    'platform.billing.read', 'platform.billing.write', 'platform.billing.process',
    'platform.plans.read', 'platform.plans.write', 'platform.plans.delete',
    'platform.payments.read', 'platform.payments.write', 'platform.payments.refund',
    'platform.monitoring.read', 'platform.monitoring.write',
    'platform.alerts.read', 'platform.alerts.write', 'platform.alerts.acknowledge',
    'platform.rate_limits.read', 'platform.rate_limits.write',
    'platform.audit.read', 'platform.audit.write',
    'platform.logs.read',
    'platform.support.read', 'platform.support.write',
    'platform.maintenance.read', 'platform.maintenance.write'
]);

-- System Architect: Infrastructure and system configuration
SELECT admin.assign_permissions_to_role('system_architect', ARRAY[
    'platform.regions.read', 'platform.regions.write', 'platform.regions.delete',
    'platform.databases.read', 'platform.databases.write', 'platform.databases.execute', 'platform.databases.health_check',
    'platform.migrations.read', 'platform.migrations.write', 'platform.migrations.rollback',
    'platform.monitoring.read', 'platform.monitoring.write',
    'platform.alerts.read', 'platform.alerts.write', 'platform.alerts.acknowledge',
    'platform.audit.read',
    'platform.logs.read',
    'platform.maintenance.read', 'platform.maintenance.write'
]);

-- Platform Admin: Platform management without infrastructure
SELECT admin.assign_permissions_to_role('platform_admin', ARRAY[
    'platform.admin.read', 'platform.admin.write',
    'platform.users.read', 'platform.users.write', 'platform.users.delete',
    'platform.roles.read', 'platform.roles.write',
    'platform.permissions.read',
    'platform.organizations.read', 'platform.organizations.write', 'platform.organizations.delete',
    'platform.tenants.read', 'platform.tenants.write', 'platform.tenants.delete', 'platform.tenants.suspend',
    'platform.billing.read', 'platform.billing.write',
    'platform.plans.read', 'platform.plans.write',
    'platform.payments.read', 'platform.payments.write',
    'platform.monitoring.read',
    'platform.alerts.read', 'platform.alerts.acknowledge',
    'platform.audit.read',
    'platform.support.read', 'platform.support.write'
]);

-- Platform Operator: Day-to-day operations
SELECT admin.assign_permissions_to_role('platform_operator', ARRAY[
    'platform.users.read', 'platform.users.write',
    'platform.roles.read',
    'platform.permissions.read',
    'platform.organizations.read', 'platform.organizations.write',
    'platform.tenants.read', 'platform.tenants.write',
    'platform.monitoring.read',
    'platform.alerts.read', 'platform.alerts.acknowledge',
    'platform.audit.read',
    'platform.support.read', 'platform.support.write'
]);

-- Platform Developer: Development and integration focus
SELECT admin.assign_permissions_to_role('platform_developer', ARRAY[
    'platform.databases.read', 'platform.databases.health_check',
    'platform.migrations.read',
    'platform.monitoring.read',
    'platform.alerts.read',
    'platform.rate_limits.read', 'platform.rate_limits.write',
    'platform.audit.read',
    'platform.logs.read'
]);

-- Platform Billing Admin: Billing and payment management
SELECT admin.assign_permissions_to_role('platform_billing_admin', ARRAY[
    'platform.billing.read', 'platform.billing.write', 'platform.billing.process',
    'platform.plans.read', 'platform.plans.write', 'platform.plans.delete',
    'platform.payments.read', 'platform.payments.write', 'platform.payments.refund',
    'platform.organizations.read',
    'platform.tenants.read',
    'platform.audit.read'
]);

-- Platform Support: Customer support access
SELECT admin.assign_permissions_to_role('platform_support', ARRAY[
    'platform.users.read',
    'platform.organizations.read',
    'platform.tenants.read',
    'platform.billing.read',
    'platform.monitoring.read',
    'platform.alerts.read',
    'platform.audit.read',
    'platform.support.read', 'platform.support.write'
]);

-- Platform Auditor: Compliance and audit access
SELECT admin.assign_permissions_to_role('platform_auditor', ARRAY[
    'platform.users.read',
    'platform.roles.read',
    'platform.permissions.read',
    'platform.organizations.read',
    'platform.tenants.read',
    'platform.billing.read',
    'platform.monitoring.read',
    'platform.alerts.read',
    'platform.audit.read', 'platform.audit.write',
    'platform.logs.read'
]);

-- Platform Viewer: Read-only access
SELECT admin.assign_permissions_to_role('platform_viewer', ARRAY[
    'platform.users.read',
    'platform.roles.read',
    'platform.permissions.read',
    'platform.organizations.read',
    'platform.tenants.read',
    'platform.monitoring.read',
    'platform.alerts.read'
]);

-- Tenant Owner: Full tenant control
SELECT admin.assign_permissions_to_role('tenant_owner', ARRAY[
    'tenant.admin.read', 'tenant.admin.write',
    'tenant.users.read', 'tenant.users.write', 'tenant.users.delete', 'tenant.users.invite',
    'tenant.roles.read', 'tenant.roles.write',
    'tenant.permissions.read',
    'tenant.teams.read', 'tenant.teams.write', 'tenant.teams.delete',
    'tenant.settings.read', 'tenant.settings.write',
    'tenant.billing.read', 'tenant.billing.write',
    'tenant.quotas.read',
    'tenant.usage.read',
    'tenant.analytics.read',
    'tenant.reports.read', 'tenant.reports.export',
    'tenant.api.read', 'tenant.api.write',
    'tenant.webhooks.read', 'tenant.webhooks.write',
    'tenant.contacts.read', 'tenant.contacts.write',
    'tenant.profile.read', 'tenant.profile.write'
]);

-- Tenant Admin: Tenant administration
SELECT admin.assign_permissions_to_role('tenant_admin', ARRAY[
    'tenant.admin.read', 'tenant.admin.write',
    'tenant.users.read', 'tenant.users.write', 'tenant.users.delete', 'tenant.users.invite',
    'tenant.roles.read', 'tenant.roles.write',
    'tenant.permissions.read',
    'tenant.teams.read', 'tenant.teams.write', 'tenant.teams.delete',
    'tenant.settings.read', 'tenant.settings.write',
    'tenant.quotas.read',
    'tenant.usage.read',
    'tenant.analytics.read',
    'tenant.reports.read', 'tenant.reports.export',
    'tenant.api.read', 'tenant.api.write',
    'tenant.webhooks.read', 'tenant.webhooks.write',
    'tenant.contacts.read', 'tenant.contacts.write',
    'tenant.profile.read', 'tenant.profile.write'
]);

-- Tenant Billing Manager: Billing management
SELECT admin.assign_permissions_to_role('tenant_billing_manager', ARRAY[
    'tenant.billing.read', 'tenant.billing.write',
    'tenant.quotas.read',
    'tenant.usage.read',
    'tenant.contacts.read', 'tenant.contacts.write',
    'tenant.profile.read', 'tenant.profile.write'
]);

-- Tenant Manager: Team and project management
SELECT admin.assign_permissions_to_role('tenant_manager', ARRAY[
    'tenant.users.read', 'tenant.users.invite',
    'tenant.teams.read', 'tenant.teams.write', 'tenant.teams.delete',
    'tenant.analytics.read',
    'tenant.reports.read',
    'tenant.profile.read', 'tenant.profile.write'
]);

-- Tenant Developer: Development within tenant
SELECT admin.assign_permissions_to_role('tenant_developer', ARRAY[
    'tenant.api.read', 'tenant.api.write',
    'tenant.webhooks.read', 'tenant.webhooks.write',
    'tenant.analytics.read',
    'tenant.reports.read',
    'tenant.teams.read', 'tenant.teams.join', 'tenant.teams.leave',
    'tenant.profile.read', 'tenant.profile.write'
]);

-- Tenant Analyst: Analytics and reporting
SELECT admin.assign_permissions_to_role('tenant_analyst', ARRAY[
    'tenant.analytics.read',
    'tenant.reports.read', 'tenant.reports.export',
    'tenant.usage.read',
    'tenant.profile.read', 'tenant.profile.write'
]);

-- Tenant User: Standard user access
SELECT admin.assign_permissions_to_role('tenant_user', ARRAY[
    'tenant.teams.read', 'tenant.teams.join', 'tenant.teams.leave',
    'tenant.analytics.read',
    'tenant.profile.read', 'tenant.profile.write'
]);

-- Tenant Guest: Minimal read access
SELECT admin.assign_permissions_to_role('tenant_guest', ARRAY[
    'tenant.profile.read'
]);

-- ============================================================================
-- CREATE DEFAULT ADMIN USER (if not exists)
-- ============================================================================

-- Create a default platform admin user for initial access
INSERT INTO admin.users (
    email,
    username,
    first_name,
    last_name,
    display_name,
    status,
    is_system_user,
    external_auth_provider,
    external_user_id,
    metadata
) VALUES (
    'admin@neomultitenant.com',
    'admin',
    'Platform',
    'Administrator',
    'Platform Admin',
    'active',
    true,
    'keycloak',
    'keycloak_admin_user_id',
    '{"initial_user": true, "created_by": "seed_script"}'::jsonb
) ON CONFLICT (email) DO UPDATE SET
    status = 'active',
    is_system_user = true,
    updated_at = NOW();

-- Assign super_admin role to the default admin user
WITH admin_user AS (
    SELECT id FROM admin.users WHERE email = 'admin@neomultitenant.com'
),
super_role AS (
    SELECT id FROM admin.roles WHERE code = 'super_admin'
)
INSERT INTO admin.user_roles (user_id, role_id, granted_reason, is_active, scope_type)
SELECT 
    admin_user.id,
    super_role.id,
    'Initial seed - default admin user',
    true,
    'global'
FROM admin_user, super_role
ON CONFLICT (user_id, role_id, scope_id) DO UPDATE SET
    is_active = true,
    granted_at = NOW();

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Show role hierarchy
SELECT 
    code,
    name,
    role_level,
    priority,
    CASE 
        WHEN is_system THEN 'System'
        WHEN is_default THEN 'Default'
        ELSE 'Custom'
    END as type
FROM admin.roles
ORDER BY priority DESC;

-- Show permission counts per role
SELECT 
    r.code as role_code,
    r.name as role_name,
    r.role_level,
    COUNT(rp.permission_id) as permission_count
FROM admin.roles r
LEFT JOIN admin.role_permissions rp ON r.id = rp.role_id
GROUP BY r.id, r.code, r.name, r.role_level
ORDER BY r.priority DESC;

-- Show permissions by scope level
SELECT 
    scope_level,
    COUNT(*) as permission_count,
    COUNT(DISTINCT resource) as resource_count
FROM admin.permissions
GROUP BY scope_level
ORDER BY scope_level;

-- Show permissions by resource
SELECT 
    resource,
    scope_level,
    COUNT(*) as permission_count,
    array_agg(DISTINCT action ORDER BY action) as available_actions
FROM admin.permissions
GROUP BY resource, scope_level
ORDER BY resource, scope_level;

-- Clean up helper function
DROP FUNCTION IF EXISTS admin.assign_permissions_to_role(VARCHAR, TEXT[]);

-- Log seed completion
SELECT 'Roles and permissions seed completed successfully' as seed_status;