-- V001: Tenant Template Schema
-- Creates the complete tenant template schema for regional databases
-- Applied to: Regional shared databases (both US and EU)
-- Placeholders: ${region}, ${gdpr}

-- Ensure platform_common schema exists and is accessible
-- (This should be replicated/accessible in regional databases)

-- ============================================================================
-- TENANT TEMPLATE SCHEMA
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS tenant_template;

-- Grant usage permissions
GRANT USAGE ON SCHEMA tenant_template TO PUBLIC;

-- ============================================================================
-- TENANT USERS (Users within a specific tenant)
-- ============================================================================

CREATE TABLE tenant_template.users (
    -- Core Identity (identical in both schemas)
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    email VARCHAR(320) NOT NULL UNIQUE 
        CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    username VARCHAR(39) UNIQUE,
    
    -- External Auth (unified fields)
    external_user_id VARCHAR(255) NOT NULL,
    external_auth_provider platform_common.auth_provider NOT NULL DEFAULT 'keycloak',
    external_auth_metadata JSONB DEFAULT '{}',
    
    -- Profile Information (identical)
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    display_name VARCHAR(150),
    avatar_url VARCHAR(2048),
    phone VARCHAR(20),
    job_title VARCHAR(150),
    
    -- Localization (identical)
    timezone VARCHAR(50) DEFAULT 'UTC',
    locale VARCHAR(10) DEFAULT 'en-US',
    
    -- Status (unified - replaces both status and is_active)
    status platform_common.user_status DEFAULT 'active',
    
    -- Organizational (conditional fields managed by configuration)
    departments VARCHAR(255)[],
    company VARCHAR(255),                    -- Used in admin schema for platform context
    manager_id UUID REFERENCES tenant_template.users(id) ON DELETE SET NULL,
    
    -- Role and Access (managed by scope context)
    default_role_level platform_common.role_level DEFAULT 'member',
    is_system_user BOOLEAN DEFAULT false,   -- Replaces is_superadmin, broader usage
    
    -- Onboarding and Profile
    is_onboarding_completed BOOLEAN DEFAULT false,
    profile_completion_percentage SMALLINT DEFAULT 0 
        CONSTRAINT profile_completion_range CHECK (profile_completion_percentage >= 0 AND profile_completion_percentage <= 100),
    
    -- Preferences (identical)
    notification_preferences JSONB DEFAULT '{}',
    ui_preferences JSONB DEFAULT '{}',
    feature_flags JSONB DEFAULT '{}',       -- Added to admin schema
    
    -- Tags and Custom Fields (unified)
    tags VARCHAR(50)[],                     -- Added to admin schema
    custom_fields JSONB DEFAULT '{}',       -- Added to admin schema
    metadata JSONB DEFAULT '{}',
    
    -- Activity Tracking (identical)
    invited_at TIMESTAMPTZ,                 -- Added to admin schema
    activated_at TIMESTAMPTZ,               -- Added to admin schema
    last_activity_at TIMESTAMPTZ,
    last_login_at TIMESTAMPTZ,
    
    -- Audit Fields (identical)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    
    -- Constraints (unified)
    CONSTRAINT unique_external_user UNIQUE (external_user_id, external_auth_provider)
);

-- Indexes for users (unified structure)
CREATE INDEX idx_tenant_users_email ON tenant_template.users(email);
CREATE INDEX idx_tenant_users_username ON tenant_template.users(username);
CREATE INDEX idx_tenant_users_external_id ON tenant_template.users(external_user_id);
CREATE INDEX idx_tenant_users_status ON tenant_template.users(status);
CREATE INDEX idx_tenant_users_manager ON tenant_template.users(manager_id);
CREATE INDEX idx_tenant_users_tags ON tenant_template.users USING GIN(tags);
CREATE INDEX idx_tenant_users_deleted ON tenant_template.users(deleted_at);

-- ============================================================================
-- TENANT PERMISSIONS (Tenant-level permissions)
-- ============================================================================

CREATE TABLE tenant_template.permissions (
    -- Core Identity (identical)
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    
    -- Resource and Action (identical)
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    
    -- Scope (unified enum)
    scope_level platform_common.permission_scope DEFAULT 'tenant',
    
    -- Security Flags (unified)
    is_dangerous BOOLEAN DEFAULT false,
    requires_mfa BOOLEAN DEFAULT false,
    requires_approval BOOLEAN DEFAULT false,
    
    -- Configuration (unified field name)
    permission_config JSONB DEFAULT '{}',
    
    -- Audit Fields (identical)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Indexes for permissions (unified structure)
CREATE INDEX idx_tenant_permissions_code ON tenant_template.permissions(code);
CREATE INDEX idx_tenant_permissions_resource ON tenant_template.permissions(resource);
CREATE INDEX idx_tenant_permissions_action ON tenant_template.permissions(action);
CREATE INDEX idx_tenant_permissions_scope ON tenant_template.permissions(scope_level);
CREATE INDEX idx_tenant_permissions_dangerous ON tenant_template.permissions(is_dangerous);

-- ============================================================================
-- TENANT ROLES (Tenant-level roles)
-- ============================================================================

CREATE TABLE tenant_template.roles (
    -- Core Identity (identical)
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    
    -- Display (unified)
    display_name VARCHAR(200),
    
    -- Role Classification (unified enum)
    role_level platform_common.role_level NOT NULL DEFAULT 'member',
    
    -- Behavioral Flags (unified)
    is_system BOOLEAN DEFAULT false,
    is_default BOOLEAN DEFAULT false,
    requires_approval BOOLEAN DEFAULT false,
    
    -- Scoping (unified approach)
    scope_type VARCHAR(20) DEFAULT 'tenant',
    
    -- Limits and Rules (unified)
    priority INTEGER DEFAULT 100,
    max_assignees INTEGER,
    auto_expire_days INTEGER,
    
    -- Configuration (identical)
    role_config JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    
    -- Permissions populated from role_permissions table. Update with trigger.
    populated_permissions JSONB DEFAULT '{}',
    
    -- Audit Fields (identical)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT valid_tenant_scope_type CHECK (scope_type IN ('global', 'team', 'tenant')),
    CONSTRAINT valid_tenant_priority CHECK (priority > 0),
    CONSTRAINT valid_tenant_auto_expire CHECK (auto_expire_days IS NULL OR auto_expire_days > 0)
);

COMMENT ON COLUMN tenant_template.roles.populated_permissions IS 'Permissions populated from role_permissions table';

-- Indexes for roles (unified structure)
CREATE INDEX idx_tenant_roles_code ON tenant_template.roles(code);
CREATE INDEX idx_tenant_roles_level ON tenant_template.roles(role_level);
CREATE INDEX idx_tenant_roles_system ON tenant_template.roles(is_system);
CREATE INDEX idx_tenant_roles_default ON tenant_template.roles(is_default);
CREATE INDEX idx_tenant_roles_scope_type ON tenant_template.roles(scope_type);

-- ============================================================================
-- ROLE PERMISSIONS (Many-to-many relationship)
-- ============================================================================

CREATE TABLE tenant_template.role_permissions (
    -- Core Relationship (identical)
    role_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    
    -- Audit (identical)
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    granted_by UUID,
    granted_reason TEXT,
    
    -- Constraints
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES tenant_template.roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES tenant_template.permissions(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES tenant_template.users(id) ON DELETE SET NULL
);

-- Indexes for role_permissions (unified structure)
CREATE INDEX idx_tenant_role_permissions_role ON tenant_template.role_permissions(role_id);
CREATE INDEX idx_tenant_role_permissions_permission ON tenant_template.role_permissions(permission_id);
CREATE INDEX idx_tenant_role_permissions_granted_by ON tenant_template.role_permissions(granted_by);

-- ============================================================================
-- TEAMS (Team/group management within tenant)
-- ============================================================================

CREATE TABLE tenant_template.teams (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE 
        CONSTRAINT slug_length CHECK (length(slug) >= 2 AND length(slug) <= 60),
    description TEXT,
    parent_team_id UUID REFERENCES tenant_template.teams,
    team_path TEXT,
    team_type platform_common.team_types DEFAULT 'working_group',
    max_members INTEGER,
    is_private BOOLEAN DEFAULT false,
    owner_id UUID REFERENCES tenant_template.users,
    settings JSONB DEFAULT '{}',
    custom_fields JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for teams
CREATE INDEX idx_tenant_teams_slug ON tenant_template.teams(slug);
CREATE INDEX idx_tenant_teams_parent ON tenant_template.teams(parent_team_id);
CREATE INDEX idx_tenant_teams_owner ON tenant_template.teams(owner_id);
CREATE INDEX idx_tenant_teams_type ON tenant_template.teams(team_type);
CREATE INDEX idx_tenant_teams_active ON tenant_template.teams(is_active);

-- ============================================================================
-- USER ROLES (User-to-role assignments within teams)
-- ============================================================================

CREATE TABLE tenant_template.user_roles (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    
    -- Core Relationship (unified)
    user_id UUID NOT NULL,
    role_id INTEGER NOT NULL,
    
    -- Scoping (flexible - can be NULL for global assignments)
    scope_type VARCHAR(20) DEFAULT 'tenant',
    scope_id UUID,
    
    -- Grant Information (unified)
    granted_by UUID,
    granted_reason TEXT,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Expiration and Status (unified)
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    
    -- Constraints
    -- Use a unique constraint for the business key
    CONSTRAINT tenant_user_roles_unique_assignment UNIQUE (user_id, role_id, scope_id),
    FOREIGN KEY (user_id) REFERENCES tenant_template.users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES tenant_template.roles(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES tenant_template.users(id) ON DELETE SET NULL,
    
    CONSTRAINT valid_tenant_user_scope_type CHECK (scope_type IN ('global', 'team', 'tenant')),
    CONSTRAINT valid_tenant_user_scope_combination CHECK (
        (scope_type = 'tenant' AND scope_id IS NULL) OR
        (scope_type != 'tenant' AND scope_id IS NOT NULL)
    )
);

-- Indexes for user_roles (unified structure)
CREATE INDEX idx_tenant_user_roles_user ON tenant_template.user_roles(user_id);
CREATE INDEX idx_tenant_user_roles_role ON tenant_template.user_roles(role_id);
CREATE INDEX idx_tenant_user_roles_scope ON tenant_template.user_roles(scope_type, scope_id);
CREATE INDEX idx_tenant_user_roles_granted_by ON tenant_template.user_roles(granted_by);
CREATE INDEX idx_tenant_user_roles_active ON tenant_template.user_roles(is_active);
CREATE INDEX idx_tenant_user_roles_expires ON tenant_template.user_roles(expires_at);

-- ============================================================================
-- USER PERMISSIONS (Direct permission grants to users)
-- ============================================================================

CREATE TABLE tenant_template.user_permissions (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    
    -- Core Relationship (unified)
    user_id UUID NOT NULL,
    permission_id INTEGER NOT NULL,
    
    -- Permission State (unified)
    is_granted BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    
    -- Scoping (flexible)
    scope_type VARCHAR(20) DEFAULT 'tenant',
    scope_id UUID,
    
    -- Grant Information (unified)
    granted_by UUID,
    granted_reason TEXT,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Revocation Information (unified)
    revoked_by UUID,
    revoked_reason TEXT,
    
    -- Expiration (unified)
    expires_at TIMESTAMPTZ,
    
    -- Constraints
    -- Use a unique constraint for the business key
    CONSTRAINT tenant_user_permissions_unique_assignment UNIQUE (user_id, permission_id, scope_id),
    FOREIGN KEY (user_id) REFERENCES tenant_template.users(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES tenant_template.permissions(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES tenant_template.users(id) ON DELETE SET NULL,
    FOREIGN KEY (revoked_by) REFERENCES tenant_template.users(id) ON DELETE SET NULL,
    
    CONSTRAINT valid_tenant_permission_scope_type CHECK (scope_type IN ('global', 'team', 'tenant')),
    CONSTRAINT valid_tenant_permission_scope_combination CHECK (
        (scope_type = 'tenant' AND scope_id IS NULL) OR
        (scope_type != 'tenant' AND scope_id IS NOT NULL)
    )
);

-- Indexes for user_permissions (unified structure)
CREATE INDEX idx_tenant_user_permissions_user ON tenant_template.user_permissions(user_id);
CREATE INDEX idx_tenant_user_permissions_permission ON tenant_template.user_permissions(permission_id);
CREATE INDEX idx_tenant_user_permissions_scope ON tenant_template.user_permissions(scope_type, scope_id);
CREATE INDEX idx_tenant_user_permissions_granted ON tenant_template.user_permissions(is_granted);
CREATE INDEX idx_tenant_user_permissions_active ON tenant_template.user_permissions(is_active);

-- ============================================================================
-- TEAM MEMBERS (Team membership tracking)
-- ============================================================================

CREATE TABLE tenant_template.team_members (
    team_id UUID NOT NULL REFERENCES tenant_template.teams ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES tenant_template.users ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'member',
    status VARCHAR(20) DEFAULT 'active',
    invited_by UUID REFERENCES tenant_template.users,
    invited_at TIMESTAMPTZ DEFAULT NOW(),
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    left_at TIMESTAMPTZ,
    receive_notifications BOOLEAN DEFAULT true,
    member_config JSONB DEFAULT '{}',
    PRIMARY KEY (team_id, user_id)
);

-- Indexes for team_members
CREATE INDEX idx_tenant_team_members_team ON tenant_template.team_members(team_id);
CREATE INDEX idx_tenant_team_members_user ON tenant_template.team_members(user_id);
CREATE INDEX idx_tenant_team_members_status ON tenant_template.team_members(status);

-- ============================================================================
-- INVITATIONS (User invitations to tenant)
-- ============================================================================

CREATE TABLE tenant_template.invitations (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    email VARCHAR(320) NOT NULL,
    invited_role platform_common.role_level DEFAULT 'member',
    invitation_token VARCHAR(255) NOT NULL UNIQUE,
    invited_by UUID NOT NULL REFERENCES tenant_template.users,
    invited_to_team_id UUID REFERENCES tenant_template.teams,
    invitation_message TEXT,
    status VARCHAR(20) DEFAULT 'pending' 
        CONSTRAINT valid_invitation_status CHECK (status IN ('pending', 'accepted', 'declined', 'expired')),
    accepted_by UUID REFERENCES tenant_template.users,
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '7 days'),
    accepted_at TIMESTAMPTZ,
    declined_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- SETTINGS (Tenant-specific configuration and preferences)
-- ============================================================================

CREATE TABLE tenant_template.settings (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    key VARCHAR(255) NOT NULL UNIQUE,
    value JSONB NOT NULL DEFAULT '{}',
    description TEXT,
    category VARCHAR(100) DEFAULT 'general',
    is_public BOOLEAN DEFAULT false,
    is_required BOOLEAN DEFAULT false,
    validation_schema JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for invitations
CREATE INDEX idx_tenant_invitations_email ON tenant_template.invitations(email);
CREATE INDEX idx_tenant_invitations_token ON tenant_template.invitations(invitation_token);
CREATE INDEX idx_tenant_invitations_status ON tenant_template.invitations(status);
CREATE INDEX idx_tenant_invitations_invited_by ON tenant_template.invitations(invited_by);
CREATE INDEX idx_tenant_invitations_expires ON tenant_template.invitations(expires_at);

-- Indexes for settings
CREATE INDEX idx_tenant_settings_key ON tenant_template.settings(key);
CREATE INDEX idx_tenant_settings_category ON tenant_template.settings(category);
CREATE INDEX idx_tenant_settings_public ON tenant_template.settings(is_public);

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON tenant_template.users
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_permissions_updated_at
    BEFORE UPDATE ON tenant_template.permissions
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_roles_updated_at
    BEFORE UPDATE ON tenant_template.roles
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_teams_updated_at
    BEFORE UPDATE ON tenant_template.teams
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_settings_updated_at
    BEFORE UPDATE ON tenant_template.settings
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON SCHEMA tenant_template IS 'Template schema for tenant-specific data in region: ${region}';
COMMENT ON TABLE tenant_template.users IS 'Users within a specific tenant instance';
COMMENT ON TABLE tenant_template.permissions IS 'Tenant-level permissions and access controls';
COMMENT ON TABLE tenant_template.roles IS 'Tenant-level roles with associated permissions';
COMMENT ON TABLE tenant_template.teams IS 'Team and group management within tenant';
COMMENT ON TABLE tenant_template.user_roles IS 'User role assignments within teams';
COMMENT ON TABLE tenant_template.user_permissions IS 'Direct permission grants to users';
COMMENT ON TABLE tenant_template.team_members IS 'Team membership and participation tracking';
COMMENT ON TABLE tenant_template.settings IS 'Tenant-specific configuration and preferences';
COMMENT ON TABLE tenant_template.invitations IS 'User invitations to join the tenant';

-- ============================================================================
-- DEFAULT DATA FOR TENANT TEMPLATE
-- ============================================================================

-- Insert default tenant permissions
INSERT INTO tenant_template.permissions (code, description, resource, action, scope_level) VALUES
('tenant.read', 'Read tenant data', 'tenant', 'read', 'tenant'),
('tenant.write', 'Modify tenant data', 'tenant', 'write', 'tenant'),
('users.read', 'View users', 'users', 'read', 'tenant'),
('users.write', 'Manage users', 'users', 'write', 'tenant'),
('users.invite', 'Invite new users', 'users', 'invite', 'tenant'),
('teams.read', 'View teams', 'teams', 'read', 'team'),
('teams.write', 'Manage teams', 'teams', 'write', 'team'),
('teams.join', 'Join teams', 'teams', 'join', 'team'),
('settings.read', 'View settings', 'settings', 'read', 'tenant'),
('settings.write', 'Modify settings', 'settings', 'write', 'tenant');

-- Insert default tenant roles
INSERT INTO tenant_template.roles (code, name, description, role_level, is_system, is_default) VALUES
('owner', 'Owner', 'Tenant owner with full access', 'owner', true, false),
('admin', 'Administrator', 'Tenant administrator', 'admin', true, false),
('manager', 'Manager', 'Team manager with limited admin access', 'manager', true, false),
('member', 'Member', 'Standard tenant member', 'member', true, true),
('viewer', 'Viewer', 'Read-only access to tenant', 'viewer', true, false),
('guest', 'Guest', 'Limited guest access', 'guest', true, false);

-- Grant all permissions to owner role
INSERT INTO tenant_template.role_permissions (role_id, permission_id) 
SELECT r.id, p.id 
FROM tenant_template.roles r 
CROSS JOIN tenant_template.permissions p 
WHERE r.code = 'owner';

-- Grant most permissions to admin role
INSERT INTO tenant_template.role_permissions (role_id, permission_id) 
SELECT r.id, p.id 
FROM tenant_template.roles r 
CROSS JOIN tenant_template.permissions p 
WHERE r.code = 'admin' AND p.code != 'settings.write';

-- Grant team permissions to manager role
INSERT INTO tenant_template.role_permissions (role_id, permission_id) 
SELECT r.id, p.id 
FROM tenant_template.roles r 
CROSS JOIN tenant_template.permissions p 
WHERE r.code = 'manager' AND p.code IN ('tenant.read', 'users.read', 'teams.read', 'teams.write');

-- Grant basic permissions to member role
INSERT INTO tenant_template.role_permissions (role_id, permission_id) 
SELECT r.id, p.id 
FROM tenant_template.roles r 
CROSS JOIN tenant_template.permissions p 
WHERE r.code = 'member' AND p.code IN ('tenant.read', 'users.read', 'teams.read', 'teams.join');

-- Grant read-only permissions to viewer role
INSERT INTO tenant_template.role_permissions (role_id, permission_id) 
SELECT r.id, p.id 
FROM tenant_template.roles r 
CROSS JOIN tenant_template.permissions p 
WHERE r.code = 'viewer' AND p.code IN ('tenant.read', 'users.read', 'teams.read');

-- Grant minimal permissions to guest role
INSERT INTO tenant_template.role_permissions (role_id, permission_id) 
SELECT r.id, p.id 
FROM tenant_template.roles r 
CROSS JOIN tenant_template.permissions p 
WHERE r.code = 'guest' AND p.code = 'tenant.read';

-- Log migration completion
SELECT 'V001: Tenant template schema created for region ${region} (GDPR: ${gdpr})' as migration_status;