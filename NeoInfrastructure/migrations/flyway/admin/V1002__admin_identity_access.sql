-- V003: Admin Identity and Access Management
-- Creates core IAM tables for platform administration
-- Applied to: Admin database only

-- ============================================================================
-- PLATFORM USERS (Global platform administrators and users)
-- ============================================================================

CREATE TABLE admin.platform_users (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    email VARCHAR(320) NOT NULL UNIQUE 
        CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    username VARCHAR(39) NOT NULL UNIQUE,
    external_id VARCHAR(255) UNIQUE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    display_name VARCHAR(150),
    avatar_url VARCHAR(2048),
    phone VARCHAR(20),
    timezone VARCHAR(50) NOT NULL DEFAULT 'UTC',
    locale VARCHAR(10) NOT NULL DEFAULT 'en-US',
    external_auth_provider admin.auth_provider NOT NULL,
    external_user_id VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_superadmin BOOLEAN NOT NULL DEFAULT false,
    last_login_at TIMESTAMPTZ,
    provider_metadata JSONB NOT NULL DEFAULT '{}',
    is_onboarding_completed BOOLEAN NOT NULL DEFAULT false,
    profile_completion_percentage SMALLINT NOT NULL DEFAULT 0 
        CONSTRAINT profile_completion_range CHECK (profile_completion_percentage >= 0 AND profile_completion_percentage <= 100),
    notification_preferences JSONB NOT NULL DEFAULT '{}',
    ui_preferences JSONB NOT NULL DEFAULT '{}',
    job_title VARCHAR(150),
    departments VARCHAR(255)[],
    company VARCHAR(255),
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Indexes for platform_users
CREATE INDEX idx_platform_users_email ON admin.platform_users(email);
CREATE INDEX idx_platform_users_username ON admin.platform_users(username);
CREATE INDEX idx_platform_users_external_id ON admin.platform_users(external_id);
CREATE INDEX idx_platform_users_active ON admin.platform_users(is_active);
CREATE INDEX idx_platform_users_provider ON admin.platform_users(external_auth_provider);
CREATE INDEX idx_platform_users_deleted ON admin.platform_users(deleted_at);

-- ============================================================================
-- PLATFORM PERMISSIONS (System-wide permissions)
-- ============================================================================

CREATE TABLE admin.platform_permissions (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    scope_level admin.permission_scope_level DEFAULT 'platform',
    is_dangerous BOOLEAN NOT NULL DEFAULT false,
    requires_mfa BOOLEAN NOT NULL DEFAULT false,
    requires_approval BOOLEAN NOT NULL DEFAULT false,
    permissions_config JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Indexes for platform_permissions
CREATE INDEX idx_platform_permissions_code ON admin.platform_permissions(code);
CREATE INDEX idx_platform_permissions_resource ON admin.platform_permissions(resource);
CREATE INDEX idx_platform_permissions_action ON admin.platform_permissions(action);
CREATE INDEX idx_platform_permissions_scope ON admin.platform_permissions(scope_level);
CREATE INDEX idx_platform_permissions_dangerous ON admin.platform_permissions(is_dangerous);

-- ============================================================================
-- PLATFORM ROLES (System-wide roles)
-- ============================================================================

CREATE TABLE admin.platform_roles (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    display_name VARCHAR(200),
    description TEXT,
    role_level admin.platform_role_level NOT NULL DEFAULT 'platform',
    priority INTEGER NOT NULL DEFAULT 100,
    is_system BOOLEAN NOT NULL DEFAULT false,
    is_default BOOLEAN NOT NULL DEFAULT false,
    max_assignees INTEGER,
    tenant_scoped BOOLEAN NOT NULL DEFAULT false,
    requires_approval BOOLEAN NOT NULL DEFAULT false,
    role_config JSONB DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Indexes for platform_roles
CREATE INDEX idx_platform_roles_code ON admin.platform_roles(code);
CREATE INDEX idx_platform_roles_level ON admin.platform_roles(role_level);
CREATE INDEX idx_platform_roles_system ON admin.platform_roles(is_system);
CREATE INDEX idx_platform_roles_default ON admin.platform_roles(is_default);

-- ============================================================================
-- ROLE PERMISSIONS (Many-to-many relationship)
-- ============================================================================

CREATE TABLE admin.role_permissions (
    role_id INTEGER NOT NULL REFERENCES admin.platform_roles ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES admin.platform_permissions ON DELETE CASCADE,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (role_id, permission_id)
);

-- Indexes for role_permissions
CREATE INDEX idx_role_permissions_role ON admin.role_permissions(role_id);
CREATE INDEX idx_role_permissions_permission ON admin.role_permissions(permission_id);

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================

CREATE TRIGGER update_platform_users_updated_at
    BEFORE UPDATE ON admin.platform_users
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_platform_permissions_updated_at
    BEFORE UPDATE ON admin.platform_permissions
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_platform_roles_updated_at
    BEFORE UPDATE ON admin.platform_roles
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE admin.platform_users IS 'Global platform administrators and cross-tenant users';
COMMENT ON TABLE admin.platform_permissions IS 'System-wide permissions that can be granted to roles';
COMMENT ON TABLE admin.platform_roles IS 'Platform-level roles with associated permissions';
COMMENT ON TABLE admin.role_permissions IS 'Many-to-many mapping of roles to permissions';

-- Log migration completion
SELECT 'V003: Admin identity and access management tables created' as migration_status;