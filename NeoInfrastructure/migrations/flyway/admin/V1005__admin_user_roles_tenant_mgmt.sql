-- V1005: Admin User Roles and Tenant Management
-- Creates user role assignments and tenant management tables
-- Applied to: Admin database only

-- ============================================================================
-- PLATFORM USER ROLES (User-to-role assignments at platform level)
-- ============================================================================

CREATE TABLE admin.platform_user_roles (
    user_id UUID NOT NULL REFERENCES admin.platform_users ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES admin.platform_roles ON DELETE CASCADE,
    granted_by UUID REFERENCES admin.platform_users,
    granted_reason TEXT,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    PRIMARY KEY (user_id, role_id)
);

-- Indexes for platform_user_roles
CREATE INDEX idx_platform_user_roles_user ON admin.platform_user_roles(user_id);
CREATE INDEX idx_platform_user_roles_role ON admin.platform_user_roles(role_id);
CREATE INDEX idx_platform_user_roles_granted_by ON admin.platform_user_roles(granted_by);
CREATE INDEX idx_platform_user_roles_active ON admin.platform_user_roles(is_active);
CREATE INDEX idx_platform_user_roles_expires ON admin.platform_user_roles(expires_at);

-- ============================================================================
-- PLATFORM USER PERMISSIONS (Direct permission grants to users)
-- ============================================================================

CREATE TABLE admin.platform_user_permissions (
    user_id UUID NOT NULL REFERENCES admin.platform_users ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES admin.platform_permissions ON DELETE CASCADE,
    is_granted BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    granted_by UUID REFERENCES admin.platform_users,
    granted_reason TEXT,
    revoked_by UUID REFERENCES admin.platform_users,
    revoked_reason TEXT,
    PRIMARY KEY (user_id, permission_id)
);

-- Indexes for platform_user_permissions
CREATE INDEX idx_platform_user_permissions_user ON admin.platform_user_permissions(user_id);
CREATE INDEX idx_platform_user_permissions_permission ON admin.platform_user_permissions(permission_id);
CREATE INDEX idx_platform_user_permissions_granted ON admin.platform_user_permissions(is_granted);
CREATE INDEX idx_platform_user_permissions_active ON admin.platform_user_permissions(is_active);

-- =========================================================================
-- TENANT USER ROLES (User-to-role assignments at tenant level)
-- =========================================================================

CREATE TABLE admin.tenant_user_roles (
    tenant_id UUID NOT NULL REFERENCES admin.tenants ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES admin.platform_users ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES admin.platform_roles ON DELETE CASCADE,
    granted_by UUID REFERENCES admin.platform_users,
    granted_reason TEXT,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    PRIMARY KEY (tenant_id, user_id, role_id)
);

-- Indexes for tenant_user_roles
CREATE INDEX idx_tenant_user_roles_tenant ON admin.tenant_user_roles(tenant_id);
CREATE INDEX idx_tenant_user_roles_user ON admin.tenant_user_roles(user_id);
CREATE INDEX idx_tenant_user_roles_role ON admin.tenant_user_roles(role_id);
CREATE INDEX idx_tenant_user_roles_granted_by ON admin.tenant_user_roles(granted_by);
CREATE INDEX idx_tenant_user_roles_active ON admin.tenant_user_roles(is_active);
CREATE INDEX idx_tenant_user_roles_expires ON admin.tenant_user_roles(expires_at);

-- =========================================================================
-- TENANT USER PERMISSIONS (Direct permission grants to users within a tenant)
-- =========================================================================

CREATE TABLE admin.tenant_user_permissions (
    tenant_id UUID NOT NULL REFERENCES admin.tenants ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES admin.platform_users ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES admin.platform_permissions ON DELETE CASCADE,
    is_granted BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    granted_by UUID REFERENCES admin.platform_users,
    granted_reason TEXT,
    revoked_by UUID REFERENCES admin.platform_users,
    revoked_reason TEXT,
    PRIMARY KEY (tenant_id, user_id, permission_id)
);

-- Indexes for tenant_user_permissions
CREATE INDEX idx_tenant_user_permissions_tenant ON admin.tenant_user_permissions(tenant_id);
CREATE INDEX idx_tenant_user_permissions_user ON admin.tenant_user_permissions(user_id);
CREATE INDEX idx_tenant_user_permissions_permission ON admin.tenant_user_permissions(permission_id);
CREATE INDEX idx_tenant_user_permissions_granted ON admin.tenant_user_permissions(is_granted);
CREATE INDEX idx_tenant_user_permissions_active ON admin.tenant_user_permissions(is_active);

-- ============================================================================
-- TENANT QUOTAS (Resource quotas and usage tracking per tenant)
-- ============================================================================

CREATE TABLE admin.tenant_quotas (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    tenant_id UUID NOT NULL UNIQUE REFERENCES admin.tenants ON DELETE CASCADE,
    storage_quota_gb NUMERIC(10,2) DEFAULT 1.0,
    storage_used_gb NUMERIC(10,2) DEFAULT 0.0,
    files_quota INTEGER DEFAULT 10000,
    files_used INTEGER DEFAULT 0,
    backup_retention_days INTEGER DEFAULT 30,
    users_quota INTEGER DEFAULT 5,
    users_active INTEGER DEFAULT 0,
    admin_users_quota INTEGER DEFAULT 2,
    guest_users_quota INTEGER DEFAULT 10,
    api_calls_monthly BIGINT DEFAULT 10000,
    api_calls_current_month BIGINT DEFAULT 0,
    api_rate_limit_per_minute INTEGER DEFAULT 100,
    bandwidth_quota_gb NUMERIC(8,2) DEFAULT 10.0,
    bandwidth_used_gb NUMERIC(8,2) DEFAULT 0.0,
    integrations_quota INTEGER DEFAULT 3,
    integrations_active INTEGER DEFAULT 0,
    workflows_quota INTEGER DEFAULT 10,
    webhooks_quota INTEGER DEFAULT 5,
    custom_fields_quota INTEGER DEFAULT 50,
    database_connections_quota INTEGER DEFAULT 10,
    database_size_quota_gb NUMERIC(8,2) DEFAULT 1.0,
    quota_period_start DATE DEFAULT CURRENT_DATE,
    quota_period_end DATE DEFAULT (CURRENT_DATE + INTERVAL '1 month'),
    last_reset_at TIMESTAMPTZ DEFAULT NOW(),
    storage_overage_allowed BOOLEAN DEFAULT false,
    bandwidth_overage_allowed BOOLEAN DEFAULT false,
    warning_threshold_percentage SMALLINT DEFAULT 80 
        CONSTRAINT valid_threshold CHECK (warning_threshold_percentage >= 0 AND warning_threshold_percentage <= 100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT valid_quotas CHECK (
        (storage_quota_gb >= 0 OR storage_quota_gb = -1) AND
        (files_quota >= 0 OR files_quota = -1) AND
        (users_quota >= 0 OR users_quota = -1) AND
        (api_calls_monthly >= 0 OR api_calls_monthly = -1) AND
        (bandwidth_quota_gb >= 0 OR bandwidth_quota_gb = -1)
    )
);

-- Indexes for tenant_quotas
CREATE INDEX idx_tenant_quotas_tenant ON admin.tenant_quotas(tenant_id);
CREATE INDEX idx_tenant_quotas_period ON admin.tenant_quotas(quota_period_start, quota_period_end);
CREATE INDEX idx_tenant_quotas_storage_usage ON admin.tenant_quotas(storage_used_gb);
CREATE INDEX idx_tenant_quotas_api_usage ON admin.tenant_quotas(api_calls_current_month);

-- ============================================================================
-- TENANT SETTINGS (Configuration settings per tenant)
-- ============================================================================

CREATE TABLE admin.tenant_settings (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    tenant_id UUID NOT NULL REFERENCES admin.tenants ON DELETE CASCADE,
    setting_key VARCHAR(100) NOT NULL,
    setting_value JSONB NOT NULL,
    setting_type VARCHAR(30) DEFAULT 'json' 
        CONSTRAINT valid_setting_type CHECK (setting_type IN ('string', 'number', 'boolean', 'json', 'encrypted')),
    category VARCHAR(50) NOT NULL,
    subcategory VARCHAR(50),
    is_public BOOLEAN DEFAULT false,
    is_readonly BOOLEAN DEFAULT false,
    requires_admin BOOLEAN DEFAULT true,
    description TEXT,
    validation_schema JSONB,
    updated_by UUID REFERENCES admin.platform_users,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, setting_key)
);

-- Indexes for tenant_settings
CREATE INDEX idx_tenant_settings_tenant ON admin.tenant_settings(tenant_id);
CREATE INDEX idx_tenant_settings_key ON admin.tenant_settings(setting_key);
CREATE INDEX idx_tenant_settings_category ON admin.tenant_settings(category);
CREATE INDEX idx_tenant_settings_public ON admin.tenant_settings(is_public);

-- ============================================================================
-- TENANT ACCESS GRANTS (External access permissions for tenants)
-- ============================================================================

CREATE TABLE admin.tenant_access_grants (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    tenant_id UUID NOT NULL REFERENCES admin.tenants ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES admin.platform_users,
    access_level VARCHAR(50) NOT NULL 
        CONSTRAINT valid_access_level CHECK (access_level IN ('read', 'write', 'admin', 'owner')),
    access_scope TEXT[],
    granted_by UUID REFERENCES admin.platform_users,
    granted_reason TEXT,
    grant_type VARCHAR(30) DEFAULT 'manual' 
        CONSTRAINT valid_grant_type CHECK (grant_type IN ('manual', 'auto', 'inherited', 'sso')),
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    last_accessed_at TIMESTAMPTZ,
    access_count INTEGER DEFAULT 0,
    ip_restrictions INET[],
    time_restrictions JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,
    UNIQUE(tenant_id, user_id)
);

-- Indexes for tenant_access_grants
CREATE INDEX idx_tenant_access_grants_tenant ON admin.tenant_access_grants(tenant_id);
CREATE INDEX idx_tenant_access_grants_user ON admin.tenant_access_grants(user_id);
CREATE INDEX idx_tenant_access_grants_level ON admin.tenant_access_grants(access_level);
CREATE INDEX idx_tenant_access_grants_active ON admin.tenant_access_grants(is_active);
CREATE INDEX idx_tenant_access_grants_expires ON admin.tenant_access_grants(expires_at);

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================

CREATE TRIGGER update_tenant_quotas_updated_at
    BEFORE UPDATE ON admin.tenant_quotas
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_tenant_settings_updated_at
    BEFORE UPDATE ON admin.tenant_settings
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_tenant_access_grants_updated_at
    BEFORE UPDATE ON admin.tenant_access_grants
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE admin.platform_user_roles IS 'Platform-level role assignments for users (not tenant-scoped)';
COMMENT ON TABLE admin.platform_user_permissions IS 'Direct permission grants to users at platform level (not tenant-scoped)';
COMMENT ON TABLE admin.tenant_user_roles IS 'Tenant-level role assignments for users within a specific tenant';
COMMENT ON TABLE admin.tenant_user_permissions IS 'Direct permission grants to users scoped to a specific tenant';
COMMENT ON TABLE admin.tenant_quotas IS 'Resource quotas and usage tracking for each tenant';
COMMENT ON TABLE admin.tenant_settings IS 'Configuration settings and preferences per tenant';
COMMENT ON TABLE admin.tenant_access_grants IS 'External access permissions and restrictions for tenant access';

-- ==========================================================================
-- CONSTRAINT ENFORCEMENT TRIGGERS (ensure correct scoping)
-- ==========================================================================

-- Enforce that only platform/system roles are used in platform_user_roles
CREATE OR REPLACE FUNCTION admin.tf_enforce_platform_user_roles()
RETURNS TRIGGER AS $$
DECLARE
    v_role_level admin.platform_role_level;
BEGIN
    SELECT role_level INTO v_role_level FROM admin.platform_roles WHERE id = NEW.role_id;
    IF v_role_level IS NULL THEN
        RAISE EXCEPTION 'Role % does not exist', NEW.role_id;
    END IF;
    IF v_role_level NOT IN ('system', 'platform') THEN
        RAISE EXCEPTION 'Role % has level %, which is not allowed for platform_user_roles', NEW.role_id, v_role_level;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_enforce_platform_user_roles
    BEFORE INSERT OR UPDATE ON admin.platform_user_roles
    FOR EACH ROW
    EXECUTE FUNCTION admin.tf_enforce_platform_user_roles();

-- Enforce that only tenant-level roles are used in tenant_user_roles
CREATE OR REPLACE FUNCTION admin.tf_enforce_tenant_user_roles()
RETURNS TRIGGER AS $$
DECLARE
    v_role_level admin.platform_role_level;
BEGIN
    SELECT role_level INTO v_role_level FROM admin.platform_roles WHERE id = NEW.role_id;
    IF v_role_level IS NULL THEN
        RAISE EXCEPTION 'Role % does not exist', NEW.role_id;
    END IF;
    IF v_role_level <> 'tenant' THEN
        RAISE EXCEPTION 'Role % has level %, which is not allowed for tenant_user_roles', NEW.role_id, v_role_level;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_enforce_tenant_user_roles
    BEFORE INSERT OR UPDATE ON admin.tenant_user_roles
    FOR EACH ROW
    EXECUTE FUNCTION admin.tf_enforce_tenant_user_roles();

-- Enforce permission scope for platform_user_permissions
CREATE OR REPLACE FUNCTION admin.tf_enforce_platform_user_permissions()
RETURNS TRIGGER AS $$
DECLARE
    v_scope admin.permission_scope_level;
BEGIN
    SELECT scope_level INTO v_scope FROM admin.platform_permissions WHERE id = NEW.permission_id;
    IF v_scope IS NULL THEN
        RAISE EXCEPTION 'Permission % does not exist', NEW.permission_id;
    END IF;
    IF v_scope <> 'platform' THEN
        RAISE EXCEPTION 'Permission % has scope %, which is not allowed for platform_user_permissions', NEW.permission_id, v_scope;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_enforce_platform_user_permissions
    BEFORE INSERT OR UPDATE ON admin.platform_user_permissions
    FOR EACH ROW
    EXECUTE FUNCTION admin.tf_enforce_platform_user_permissions();

-- Enforce permission scope for tenant_user_permissions
CREATE OR REPLACE FUNCTION admin.tf_enforce_tenant_user_permissions()
RETURNS TRIGGER AS $$
DECLARE
    v_scope admin.permission_scope_level;
BEGIN
    SELECT scope_level INTO v_scope FROM admin.platform_permissions WHERE id = NEW.permission_id;
    IF v_scope IS NULL THEN
        RAISE EXCEPTION 'Permission % does not exist', NEW.permission_id;
    END IF;
    IF v_scope <> 'tenant' THEN
        RAISE EXCEPTION 'Permission % has scope %, which is not allowed for tenant_user_permissions', NEW.permission_id, v_scope;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_enforce_tenant_user_permissions
    BEFORE INSERT OR UPDATE ON admin.tenant_user_permissions
    FOR EACH ROW
    EXECUTE FUNCTION admin.tf_enforce_tenant_user_permissions();

-- Log migration completion
SELECT 'V1005: Admin user roles and tenant management tables created' as migration_status;