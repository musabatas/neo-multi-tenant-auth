-- NeoMultiTenant - Seed Data: Roles and Permissions
-- This seed file populates comprehensive starter roles and permissions
-- Run with: ./deploy.sh --seed

-- ============================================================================
-- PLATFORM ROLES: Define comprehensive role hierarchy
-- ============================================================================

-- Clear existing roles (for development only)
TRUNCATE admin.role_permissions CASCADE;
DELETE FROM admin.platform_roles WHERE is_system = false;

-- Insert/Update comprehensive starter roles
INSERT INTO admin.platform_roles (
    code, name, display_name, description, role_level, priority, 
    is_system, is_default, tenant_scoped, requires_approval
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
    false,
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
    false,
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
    false,
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
    false,
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
    false,
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
    false,
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
    false,
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
    false,
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
    true,
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
    true,
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
    true,
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
    true,
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
    true,
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
    true,
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
    true,
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

-- Helper function to assign permissions to roles
CREATE OR REPLACE FUNCTION admin.assign_permissions_to_role(
    p_role_code VARCHAR,
    p_permissions TEXT[]
) RETURNS void AS $$
DECLARE
    v_role_id INTEGER;
    v_permission_id INTEGER;
    v_permission TEXT;
BEGIN
    -- Get role ID
    SELECT id INTO v_role_id FROM admin.platform_roles WHERE code = p_role_code;
    
    IF v_role_id IS NULL THEN
        RAISE NOTICE 'Role % not found', p_role_code;
        RETURN;
    END IF;
    
    -- Clear existing permissions for this role
    DELETE FROM admin.role_permissions WHERE role_id = v_role_id;
    
    -- Assign each permission
    FOREACH v_permission IN ARRAY p_permissions
    LOOP
        SELECT id INTO v_permission_id 
        FROM admin.platform_permissions 
        WHERE code = v_permission;
        
        IF v_permission_id IS NOT NULL THEN
            INSERT INTO admin.role_permissions (role_id, permission_id)
            VALUES (v_role_id, v_permission_id)
            ON CONFLICT (role_id, permission_id) DO NOTHING;
        ELSE
            RAISE NOTICE 'Permission % not found', v_permission;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- ASSIGN PERMISSIONS TO ROLES
-- ============================================================================

-- Super Admin: All platform permissions
SELECT admin.assign_permissions_to_role('super_admin', ARRAY[
    'platform:admin',
    'platform:read',
    'users:read',
    'users:write',
    'users:delete',
    'roles:read',
    'roles:write',
    'permissions:read',
    'organizations:read',
    'organizations:write',
    'organizations:delete',
    'tenants:read',
    'tenants:write',
    'tenants:delete',
    'regions:read',
    'regions:write',
    'databases:read',
    'databases:write',
    'databases:health_check',
    'database:read',
    'database:write',
    'database:execute',
    'audit:read',
    'audit:write',
    'monitoring:read',
    'monitoring:write',
    'billing:read',
    'billing:write',
    'auth:logout',
    'auth:reset_password'
]);

-- System Architect: Infrastructure and system configuration
SELECT admin.assign_permissions_to_role('system_architect', ARRAY[
    'regions:read',
    'regions:write',
    'databases:read',
    'databases:write',
    'databases:health_check',
    'database:read',
    'database:write',
    'database:execute',
    'monitoring:read',
    'monitoring:write',
    'audit:read'
]);

-- Platform Admin: Platform management without infrastructure
SELECT admin.assign_permissions_to_role('platform_admin', ARRAY[
    'users:read',
    'users:write',
    'users:delete',
    'roles:read',
    'roles:write',
    'permissions:read',
    'organizations:read',
    'organizations:write',
    'organizations:delete',
    'tenants:read',
    'tenants:write',
    'tenants:delete',
    'audit:read',
    'monitoring:read',
    'billing:read',
    'billing:write'
]);

-- Platform Operator: Day-to-day operations
SELECT admin.assign_permissions_to_role('platform_operator', ARRAY[
    'users:read',
    'users:write',
    'roles:read',
    'permissions:read',
    'organizations:read',
    'organizations:write',
    'tenants:read',
    'tenants:write',
    'audit:read',
    'monitoring:read'
]);

-- Platform Developer: Development and integration focus
SELECT admin.assign_permissions_to_role('platform_developer', ARRAY[
    'databases:read',
    'databases:health_check',
    'monitoring:read',
    'audit:read'
]);

-- Platform Support: Customer support access
SELECT admin.assign_permissions_to_role('platform_support', ARRAY[
    'users:read',
    'organizations:read',
    'tenants:read',
    'audit:read',
    'monitoring:read'
]);

-- Platform Auditor: Compliance and audit access
SELECT admin.assign_permissions_to_role('platform_auditor', ARRAY[
    'audit:read',
    'audit:write',
    'users:read',
    'roles:read',
    'permissions:read',
    'organizations:read',
    'tenants:read',
    'monitoring:read'
]);

-- Platform Viewer: Read-only access
SELECT admin.assign_permissions_to_role('platform_viewer', ARRAY[
    'users:read',
    'roles:read',
    'permissions:read',
    'organizations:read',
    'tenants:read',
    'monitoring:read'
]);

-- Tenant Owner: Full tenant control
SELECT admin.assign_permissions_to_role('tenant_owner', ARRAY[
    'tenant.users.read',
    'tenant.users.write',
    'tenant.users.delete',
    'tenant.roles.read',
    'tenant.roles.write',
    'tenant.teams.read',
    'tenant.teams.write',
    'tenant.billing.read',
    'tenant.analytics.read'
]);

-- Tenant Admin: Tenant administration
SELECT admin.assign_permissions_to_role('tenant_admin', ARRAY[
    'tenant.users.read',
    'tenant.users.write',
    'tenant.roles.read',
    'tenant.roles.write',
    'tenant.teams.read',
    'tenant.teams.write',
    'tenant.analytics.read'
]);

-- Tenant Manager: Team and project management
SELECT admin.assign_permissions_to_role('tenant_manager', ARRAY[
    'tenant.users.read',
    'tenant.teams.read',
    'tenant.teams.write',
    'tenant.analytics.read'
]);

-- Tenant Developer: Development within tenant
SELECT admin.assign_permissions_to_role('tenant_developer', ARRAY[
    'tenant.api.read',
    'tenant.api.write',
    'tenant.analytics.read'
]);

-- Tenant Analyst: Analytics and reporting
SELECT admin.assign_permissions_to_role('tenant_analyst', ARRAY[
    'tenant.analytics.read',
    'tenant.reports.read'
]);

-- Tenant User: Standard user access
SELECT admin.assign_permissions_to_role('tenant_user', ARRAY[
    'tenant.profile.read',
    'tenant.teams.read',
    'tenant.analytics.read'
]);

-- Tenant Guest: Minimal read access
SELECT admin.assign_permissions_to_role('tenant_guest', ARRAY[
    'tenant.profile.read'
]);

-- ============================================================================
-- CREATE DEFAULT ADMIN USER (if not exists)
-- ============================================================================

-- Create a default platform admin user for initial access
INSERT INTO admin.platform_users (
    email,
    username,
    external_id,
    first_name,
    last_name,
    display_name,
    is_active,
    is_superadmin,
    external_auth_provider,
    external_user_id,
    metadata
) VALUES (
    'admin@neomultitenant.com',
    'admin',
    'keycloak_admin_user_id',
    'Platform',
    'Administrator',
    'Platform Admin',
    true,
    true,
    'keycloak',
    'keycloak_admin_user_id',
    '{"initial_user": true, "created_by": "seed_script"}'::jsonb
) ON CONFLICT (email) DO UPDATE SET
    is_active = true,
    is_superadmin = true,
    updated_at = NOW();

-- Assign super_admin role to the default admin user
WITH admin_user AS (
    SELECT id FROM admin.platform_users WHERE email = 'admin@neomultitenant.com'
),
super_role AS (
    SELECT id FROM admin.platform_roles WHERE code = 'super_admin'
)
INSERT INTO admin.platform_user_roles (user_id, role_id, granted_reason, is_active)
SELECT 
    admin_user.id,
    super_role.id,
    'Initial seed - default admin user',
    true
FROM admin_user, super_role
ON CONFLICT (user_id, role_id) DO UPDATE SET
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
FROM admin.platform_roles
ORDER BY priority DESC;

-- Show permission counts per role
SELECT 
    r.code as role_code,
    r.name as role_name,
    r.role_level,
    COUNT(rp.permission_id) as permission_count
FROM admin.platform_roles r
LEFT JOIN admin.role_permissions rp ON r.id = rp.role_id
GROUP BY r.id, r.code, r.name, r.role_level
ORDER BY r.priority DESC;

-- Clean up helper function
DROP FUNCTION IF EXISTS admin.assign_permissions_to_role(VARCHAR, TEXT[]);

-- Log seed completion
SELECT 'Roles and permissions seed completed successfully' as seed_status;