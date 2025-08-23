-- V003: Admin Identity and Access Management
-- Creates core IAM tables for platform administration
-- Applied to: Admin database only

-- ============================================================================
-- USERS (Global platform administrators and users)
-- ============================================================================

CREATE TABLE admin.users (
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
    manager_id UUID REFERENCES admin.users(id) ON DELETE SET NULL,
    
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
CREATE INDEX idx_admin_users_email ON admin.users(email);
CREATE INDEX idx_admin_users_username ON admin.users(username);
CREATE INDEX idx_admin_users_external_id ON admin.users(external_user_id);
CREATE INDEX idx_admin_users_status ON admin.users(status);
CREATE INDEX idx_admin_users_manager ON admin.users(manager_id);
CREATE INDEX idx_admin_users_tags ON admin.users USING GIN(tags);
CREATE INDEX idx_admin_users_deleted ON admin.users(deleted_at);

-- ============================================================================
-- PERMISSIONS (System-wide permissions)
-- ============================================================================

CREATE TABLE admin.permissions (
    -- Core Identity (identical)
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    
    -- Resource and Action (identical)
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    
    -- Scope (unified enum)
    scope_level platform_common.permission_scope DEFAULT 'platform',
    
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
CREATE INDEX idx_admin_permissions_code ON admin.permissions(code);
CREATE INDEX idx_admin_permissions_resource ON admin.permissions(resource);
CREATE INDEX idx_admin_permissions_action ON admin.permissions(action);
CREATE INDEX idx_admin_permissions_scope ON admin.permissions(scope_level);
CREATE INDEX idx_admin_permissions_dangerous ON admin.permissions(is_dangerous);

-- ============================================================================
-- ROLES (System-wide roles)
-- ============================================================================

CREATE TABLE admin.roles (
    -- Core Identity (identical)
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    
    -- Display (unified)
    display_name VARCHAR(200),
    
    -- Role Classification (unified enum)
    role_level platform_common.role_level NOT NULL DEFAULT 'platform',
    
    -- Behavioral Flags (unified)
    is_system BOOLEAN DEFAULT false,
    is_default BOOLEAN DEFAULT false,
    requires_approval BOOLEAN DEFAULT false,
    
    -- Scoping (unified approach)
    scope_type VARCHAR(20) DEFAULT 'global',
    
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
    CONSTRAINT valid_scope_type CHECK (scope_type IN ('global', 'team', 'tenant')),
    CONSTRAINT valid_priority CHECK (priority > 0),
    CONSTRAINT valid_auto_expire CHECK (auto_expire_days IS NULL OR auto_expire_days > 0)
);

COMMENT ON COLUMN admin.roles.populated_permissions IS 'Permissions populated from role_permissions table';

-- Indexes for roles (unified structure)
CREATE INDEX idx_admin_roles_code ON admin.roles(code);
CREATE INDEX idx_admin_roles_level ON admin.roles(role_level);
CREATE INDEX idx_admin_roles_system ON admin.roles(is_system);
CREATE INDEX idx_admin_roles_default ON admin.roles(is_default);
CREATE INDEX idx_admin_roles_scope_type ON admin.roles(scope_type);

-- ============================================================================
-- ROLE PERMISSIONS (Many-to-many relationship)
-- ============================================================================

CREATE TABLE admin.role_permissions (
    -- Core Relationship (identical)
    role_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    
    -- Audit (identical)
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    granted_by UUID,
    granted_reason TEXT,
    
    -- Constraints
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES admin.roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES admin.permissions(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES admin.users(id) ON DELETE SET NULL
);

-- Indexes for role_permissions (unified structure)
CREATE INDEX idx_admin_role_permissions_role ON admin.role_permissions(role_id);
CREATE INDEX idx_admin_role_permissions_permission ON admin.role_permissions(permission_id);
CREATE INDEX idx_admin_role_permissions_granted_by ON admin.role_permissions(granted_by);

-- ============================================================================
-- TEAMS (Added for unified structure)
-- ============================================================================

CREATE TABLE admin.teams (
    -- Core Identity
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    
    -- Hierarchy
    parent_team_id UUID,
    team_path TEXT,
    team_type platform_common.team_types DEFAULT 'working_group',
    
    -- Configuration
    max_members INTEGER,
    is_private BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    
    -- Ownership
    owner_id UUID,
    
    -- Customization
    settings JSONB DEFAULT '{}',
    custom_fields JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    
    -- Lifecycle
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    FOREIGN KEY (parent_team_id) REFERENCES admin.teams(id) ON DELETE SET NULL,
    FOREIGN KEY (owner_id) REFERENCES admin.users(id) ON DELETE SET NULL,
    CONSTRAINT valid_admin_slug_length CHECK (length(slug) >= 2 AND length(slug) <= 60)
);

-- Indexes for teams
CREATE INDEX idx_admin_teams_slug ON admin.teams(slug);
CREATE INDEX idx_admin_teams_parent ON admin.teams(parent_team_id);
CREATE INDEX idx_admin_teams_owner ON admin.teams(owner_id);
CREATE INDEX idx_admin_teams_type ON admin.teams(team_type);
CREATE INDEX idx_admin_teams_active ON admin.teams(is_active);

-- ============================================================================
-- TEAM MEMBERS (Added for unified structure)
-- ============================================================================

CREATE TABLE admin.team_members (
    -- Core Relationship
    team_id UUID NOT NULL,
    user_id UUID NOT NULL,
    
    -- Role and Status
    role VARCHAR(50) DEFAULT 'member',
    status VARCHAR(20) DEFAULT 'active',
    
    -- Invitation Tracking
    invited_by UUID,
    invited_at TIMESTAMPTZ DEFAULT NOW(),
    joined_at TIMESTAMPTZ,
    left_at TIMESTAMPTZ,
    
    -- Preferences
    receive_notifications BOOLEAN DEFAULT true,
    member_config JSONB DEFAULT '{}',
    
    -- Constraints
    PRIMARY KEY (team_id, user_id),
    FOREIGN KEY (team_id) REFERENCES admin.teams(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES admin.users(id) ON DELETE CASCADE,
    FOREIGN KEY (invited_by) REFERENCES admin.users(id) ON DELETE SET NULL
);

-- Indexes for team_members
CREATE INDEX idx_admin_team_members_team ON admin.team_members(team_id);
CREATE INDEX idx_admin_team_members_user ON admin.team_members(user_id);
CREATE INDEX idx_admin_team_members_status ON admin.team_members(status);

-- ============================================================================
-- USER ROLES (Unified Structure with Flexible Scoping)
-- ============================================================================

CREATE TABLE admin.user_roles (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    
    -- Core Relationship (unified)
    user_id UUID NOT NULL,
    role_id INTEGER NOT NULL,
    
    -- Scoping (flexible - can be NULL for global assignments)
    scope_type VARCHAR(20) DEFAULT 'global',
    scope_id UUID,
    
    -- Grant Information (unified)
    granted_by UUID,
    granted_reason TEXT,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Expiration and Status (unified)
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    
    -- Constraints
    -- Use a unique constraint instead of PRIMARY KEY with COALESCE
    CONSTRAINT user_roles_unique_assignment UNIQUE (user_id, role_id, scope_id),
    FOREIGN KEY (user_id) REFERENCES admin.users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES admin.roles(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES admin.users(id) ON DELETE SET NULL,
    
    CONSTRAINT valid_admin_scope_type CHECK (scope_type IN ('global', 'team', 'tenant')),
    CONSTRAINT valid_admin_scope_combination CHECK (
        (scope_type = 'global' AND scope_id IS NULL) OR
        (scope_type != 'global' AND scope_id IS NOT NULL)
    )
);

-- Indexes for user_roles
CREATE INDEX idx_admin_user_roles_user ON admin.user_roles(user_id);
CREATE INDEX idx_admin_user_roles_role ON admin.user_roles(role_id);
CREATE INDEX idx_admin_user_roles_scope ON admin.user_roles(scope_type, scope_id);
CREATE INDEX idx_admin_user_roles_granted_by ON admin.user_roles(granted_by);
CREATE INDEX idx_admin_user_roles_active ON admin.user_roles(is_active);
CREATE INDEX idx_admin_user_roles_expires ON admin.user_roles(expires_at);

-- ============================================================================
-- USER PERMISSIONS (Unified Structure with Flexible Scoping)
-- ============================================================================

CREATE TABLE admin.user_permissions (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    
    -- Core Relationship (unified)
    user_id UUID NOT NULL,
    permission_id INTEGER NOT NULL,
    
    -- Permission State (unified)
    is_granted BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    
    -- Scoping (flexible)
    scope_type VARCHAR(20) DEFAULT 'global',
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
    CONSTRAINT user_permissions_unique_assignment UNIQUE (user_id, permission_id, scope_id),
    FOREIGN KEY (user_id) REFERENCES admin.users(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES admin.permissions(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES admin.users(id) ON DELETE SET NULL,
    FOREIGN KEY (revoked_by) REFERENCES admin.users(id) ON DELETE SET NULL,
    
    CONSTRAINT valid_admin_permission_scope_type CHECK (scope_type IN ('global', 'team', 'tenant')),
    CONSTRAINT valid_admin_permission_scope_combination CHECK (
        (scope_type = 'global' AND scope_id IS NULL) OR
        (scope_type != 'global' AND scope_id IS NOT NULL)
    )
);

-- Indexes for user_permissions
CREATE INDEX idx_admin_user_permissions_user ON admin.user_permissions(user_id);
CREATE INDEX idx_admin_user_permissions_permission ON admin.user_permissions(permission_id);
CREATE INDEX idx_admin_user_permissions_scope ON admin.user_permissions(scope_type, scope_id);
CREATE INDEX idx_admin_user_permissions_granted ON admin.user_permissions(is_granted);
CREATE INDEX idx_admin_user_permissions_active ON admin.user_permissions(is_active);

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================

CREATE TRIGGER update_admin_users_updated_at
    BEFORE UPDATE ON admin.users
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_admin_permissions_updated_at
    BEFORE UPDATE ON admin.permissions
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_admin_roles_updated_at
    BEFORE UPDATE ON admin.roles
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_admin_teams_updated_at
    BEFORE UPDATE ON admin.teams
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE admin.users IS 'Global platform administrators and cross-tenant users (unified structure)';
COMMENT ON TABLE admin.permissions IS 'System-wide permissions that can be granted to roles (unified structure)';
COMMENT ON TABLE admin.roles IS 'Platform-level roles with associated permissions (unified structure)';
COMMENT ON TABLE admin.role_permissions IS 'Many-to-many mapping of roles to permissions (unified structure)';
COMMENT ON TABLE admin.teams IS 'Team organization structure for admin users (unified structure)';
COMMENT ON TABLE admin.team_members IS 'Team membership tracking for admin users (unified structure)';
COMMENT ON TABLE admin.user_roles IS 'User role assignments with flexible scoping (unified structure)';
COMMENT ON TABLE admin.user_permissions IS 'Direct permission grants to users with flexible scoping (unified structure)';

-- Log migration completion
SELECT 'V003: Admin identity and access management tables created' as migration_status;