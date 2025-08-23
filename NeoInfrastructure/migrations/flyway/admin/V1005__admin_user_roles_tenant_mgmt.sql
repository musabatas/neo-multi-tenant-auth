-- V1005: Admin User Roles and Tenant Management
-- Creates user role assignments and tenant management tables
-- Applied to: Admin database only

-- ============================================================================
-- USER ROLES AND PERMISSIONS - MOVED TO V1002 FOR UNIFIED STRUCTURE
-- ============================================================================
-- 
-- NOTE: The unified user_roles and user_permissions tables are now created in V1002
-- to match the structure used in tenant schemas. This enables:
-- 1. Dynamic, reusable code across admin and tenant schemas
-- 2. Flexible scoping (global, tenant, team) in a single table
-- 3. Consistent permission checking logic
--
-- The unified tables support:
-- - Global assignments: scope_type='global', scope_id=NULL
-- - Tenant assignments: scope_type='tenant', scope_id=tenant_uuid  
-- - Team assignments: scope_type='team', scope_id=team_uuid

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
    updated_by UUID REFERENCES admin.users,
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
    user_id UUID NOT NULL REFERENCES admin.users,
    access_level VARCHAR(50) NOT NULL 
        CONSTRAINT valid_access_level CHECK (access_level IN ('read', 'write', 'admin', 'owner')),
    access_scope TEXT[],
    granted_by UUID REFERENCES admin.users,
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

-- Comments for old tables removed - these tables are now unified in V1002
-- admin.user_roles and admin.user_permissions now handle all scoping via scope_type/scope_id
COMMENT ON TABLE admin.tenant_quotas IS 'Resource quotas and usage tracking for each tenant';
COMMENT ON TABLE admin.tenant_settings IS 'Configuration settings and preferences per tenant';
COMMENT ON TABLE admin.tenant_access_grants IS 'External access permissions and restrictions for tenant access';

-- ==========================================================================
-- CONSTRAINT ENFORCEMENT TRIGGERS - REMOVED
-- ==========================================================================
-- 
-- Previous validation triggers for role and permission scoping have been removed
-- because we now use a unified table structure with scope_type and scope_id columns.
-- 
-- The unified admin.user_roles and admin.user_permissions tables (created in V1002)
-- use CHECK constraints and application-level validation instead of triggers.
-- 
-- This provides better performance and simpler maintenance while still ensuring
-- data integrity through the flexible scoping mechanism.
-- 
-- For reference, the old separate tables that these triggers validated:
-- - admin.platform_user_roles (now part of admin.user_roles with scope_type='global')
-- - admin.tenant_user_roles (now part of admin.user_roles with scope_type='tenant')
-- - admin.platform_user_permissions (now part of admin.user_permissions with scope_type='global')
-- - admin.tenant_user_permissions (now part of admin.user_permissions with scope_type='tenant')

-- Log migration completion
SELECT 'V1005: Admin user roles and tenant management tables created' as migration_status;