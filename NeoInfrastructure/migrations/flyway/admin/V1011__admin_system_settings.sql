-- V1011: Admin System Settings
-- Creates flexible system settings table for configuration management
-- Applied to: Admin database only

-- ============================================================================
-- CREATE ENUM TYPE FIRST
-- ============================================================================

-- Create setting_type enum in platform_common if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'setting_type' AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'platform_common')) THEN
        CREATE TYPE platform_common.setting_type AS ENUM (
            'string',
            'number', 
            'boolean',
            'json',
            'array',
            'email',
            'url',
            'password',
            'text',
            'select',
            'multiselect'
        );
    END IF;
END$$;

-- ============================================================================
-- SYSTEM SETTINGS (Flexible configuration management)
-- ============================================================================

CREATE TABLE admin.system_settings (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    tenant_id UUID, -- NULL for platform-wide settings, UUID for tenant-specific
    setting_key VARCHAR(100) NOT NULL,
    setting_value JSONB,
    setting_type platform_common.setting_type NOT NULL DEFAULT 'string',
    category VARCHAR(50) DEFAULT 'general',
    description TEXT,
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for system_settings
CREATE INDEX idx_admin_system_settings_tenant_id ON admin.system_settings(tenant_id);
CREATE INDEX idx_admin_system_settings_category ON admin.system_settings(category);
CREATE INDEX idx_admin_system_settings_type ON admin.system_settings(setting_type);
CREATE INDEX idx_admin_system_settings_public ON admin.system_settings(is_public);
CREATE INDEX idx_admin_system_settings_value ON admin.system_settings USING GIN(setting_value);

-- Unique constraints handled via partial indexes
CREATE UNIQUE INDEX idx_admin_system_settings_platform_unique 
    ON admin.system_settings(setting_key) WHERE tenant_id IS NULL;
CREATE UNIQUE INDEX idx_admin_system_settings_tenant_unique 
    ON admin.system_settings(tenant_id, setting_key) WHERE tenant_id IS NOT NULL;

-- Add check constraints
ALTER TABLE admin.system_settings ADD CONSTRAINT valid_setting_key 
    CHECK (setting_key ~ '^[a-z][a-z0-9_.]*$' AND length(setting_key) >= 2);

-- Add foreign key constraint for tenant_id
ALTER TABLE admin.system_settings ADD CONSTRAINT fk_system_settings_tenant_id 
    FOREIGN KEY (tenant_id) REFERENCES admin.tenants(id) ON DELETE CASCADE;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

CREATE TRIGGER update_admin_system_settings_updated_at
    BEFORE UPDATE ON admin.system_settings
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE admin.system_settings IS 'System configuration settings - platform-wide (tenant_id=NULL) and tenant-specific';
COMMENT ON COLUMN admin.system_settings.tenant_id IS 'NULL for platform-wide settings, tenant UUID for tenant-specific overrides';
COMMENT ON COLUMN admin.system_settings.setting_key IS 'Unique identifier for the setting (snake_case, can use dots for hierarchy)';
COMMENT ON COLUMN admin.system_settings.setting_value IS 'The setting value stored as JSONB for flexibility';
COMMENT ON COLUMN admin.system_settings.setting_type IS 'Basic data type of the setting';
COMMENT ON COLUMN admin.system_settings.category IS 'Category for grouping related settings';
COMMENT ON COLUMN admin.system_settings.description IS 'Human-readable description of what this setting does';
COMMENT ON COLUMN admin.system_settings.is_public IS 'Whether the setting can be accessed by non-admin users';

-- ============================================================================
-- DEFAULT SYSTEM SETTINGS
-- ============================================================================

-- Insert platform-wide default admin system settings (tenant_id = NULL)
INSERT INTO admin.system_settings (
    tenant_id, setting_key, setting_value, setting_type, category, description, is_public
) VALUES 
-- Basic platform settings
(NULL, 'platform.name', '"NeoMultiTenant Platform"', 'string', 'platform', 'Display name for the platform', true),
(NULL, 'platform.url', '"https://localhost:8000"', 'string', 'platform', 'Base URL for the platform', false),
(NULL, 'support.email', '"support@neomultitenant.com"', 'string', 'platform', 'Support email address', true),

-- Authentication defaults
(NULL, 'auth.session_timeout_minutes', '480', 'number', 'auth', 'Default session timeout in minutes', false),
(NULL, 'auth.password_min_length', '8', 'number', 'auth', 'Default minimum password length', false),

-- API settings defaults
(NULL, 'api.rate_limit_default', '1000', 'number', 'api', 'Default rate limit per minute', false),

-- Feature flags defaults
(NULL, 'features.user_registration', 'true', 'boolean', 'features', 'Enable user registration by default', false),
(NULL, 'features.analytics', 'true', 'boolean', 'features', 'Enable analytics by default', false)

ON CONFLICT (setting_key) WHERE tenant_id IS NULL DO NOTHING;

-- ============================================================================
-- TENANT SETTINGS MANAGEMENT FUNCTIONS
-- ============================================================================

-- Function to create default settings for a tenant (admin-managed)
CREATE OR REPLACE FUNCTION admin.create_tenant_settings(p_tenant_id UUID)
RETURNS void AS $$
BEGIN
    INSERT INTO admin.system_settings (
        tenant_id, setting_key, setting_value, setting_type, category, description, is_public
    ) 
    SELECT 
        p_tenant_id,
        setting_key,
        setting_value,
        setting_type, 
        category,
        description,
        is_public
    FROM admin.system_settings 
    WHERE tenant_id IS NULL
    ON CONFLICT (tenant_id, setting_key) WHERE tenant_id IS NOT NULL DO NOTHING;
    
    RAISE NOTICE 'Created tenant-specific settings for tenant % based on platform defaults', p_tenant_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get effective setting value (tenant-specific overrides platform default)
CREATE OR REPLACE FUNCTION admin.get_setting(p_tenant_id UUID, p_setting_key VARCHAR)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    -- First try tenant-specific setting
    SELECT setting_value INTO result
    FROM admin.system_settings 
    WHERE tenant_id = p_tenant_id AND setting_key = p_setting_key;
    
    -- If not found, fall back to platform default
    IF result IS NULL THEN
        SELECT setting_value INTO result
        FROM admin.system_settings 
        WHERE tenant_id IS NULL AND setting_key = p_setting_key;
    END IF;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION admin.create_tenant_settings(UUID) IS 'Creates tenant-specific settings based on platform defaults';
COMMENT ON FUNCTION admin.get_setting(UUID, VARCHAR) IS 'Gets effective setting value with tenant override fallback to platform default';

-- Log migration completion
SELECT 'V1011: Admin system settings table created' as migration_status;
