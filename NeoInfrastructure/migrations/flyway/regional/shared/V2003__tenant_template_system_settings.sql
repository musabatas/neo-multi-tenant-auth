-- V2003: Tenant Template System Settings
-- Creates flexible system settings table for tenant configuration management
-- Applied to: Tenant template database

-- ============================================================================
-- CREATE SCHEMA AND ENUM TYPE FIRST
-- ============================================================================

-- Create platform_common schema if not exists
CREATE SCHEMA IF NOT EXISTS platform_common;

-- Create uuid_generate_v7 function if not exists
CREATE OR REPLACE FUNCTION platform_common.uuid_generate_v7() RETURNS UUID AS $$
BEGIN
    RETURN gen_random_uuid();
END;
$$ LANGUAGE plpgsql;

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

-- Create update trigger function if not exists
CREATE OR REPLACE FUNCTION platform_common.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SYSTEM SETTINGS (Flexible configuration management)
-- ============================================================================

CREATE TABLE tenant_template.system_settings (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value JSONB,
    setting_type platform_common.setting_type NOT NULL DEFAULT 'string',
    category VARCHAR(50) DEFAULT 'general',
    description TEXT,
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for system_settings
CREATE INDEX idx_tenant_system_settings_category ON tenant_template.system_settings(category);
CREATE INDEX idx_tenant_system_settings_type ON tenant_template.system_settings(setting_type);
CREATE INDEX idx_tenant_system_settings_public ON tenant_template.system_settings(is_public);
CREATE INDEX idx_tenant_system_settings_value ON tenant_template.system_settings USING GIN(setting_value);

-- Add check constraints
ALTER TABLE tenant_template.system_settings ADD CONSTRAINT valid_setting_key 
    CHECK (setting_key ~ '^[a-z][a-z0-9_.]*$' AND length(setting_key) >= 2);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

CREATE TRIGGER update_tenant_system_settings_updated_at
    BEFORE UPDATE ON tenant_template.system_settings
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE tenant_template.system_settings IS 'Tenant database-specific system configuration settings';
COMMENT ON COLUMN tenant_template.system_settings.setting_key IS 'Unique identifier for the setting (snake_case, can use dots for hierarchy)';
COMMENT ON COLUMN tenant_template.system_settings.setting_value IS 'The setting value stored as JSONB for flexibility';
COMMENT ON COLUMN tenant_template.system_settings.setting_type IS 'Basic data type of the setting';
COMMENT ON COLUMN tenant_template.system_settings.category IS 'Category for grouping related settings';
COMMENT ON COLUMN tenant_template.system_settings.description IS 'Human-readable description of what this setting does';
COMMENT ON COLUMN tenant_template.system_settings.is_public IS 'Whether the setting can be accessed by non-admin users';

-- ============================================================================
-- DEFAULT TENANT SETTINGS
-- ============================================================================

-- Insert default tenant system settings
INSERT INTO tenant_template.system_settings (
    setting_key, setting_value, setting_type, category, description, is_public
) VALUES 
-- Tenant branding
('tenant.name', '""', 'string', 'branding', 'Display name for this tenant', true),
('tenant.logo_url', '""', 'string', 'branding', 'URL to tenant logo', true),
('tenant.primary_color', '"#007bff"', 'string', 'branding', 'Primary brand color', true),

-- General configuration
('general.timezone', '"UTC"', 'string', 'general', 'Default timezone', true),
('general.locale', '"en-US"', 'string', 'general', 'Default locale', true),
('general.currency', '"USD"', 'string', 'general', 'Default currency', true),

-- User management
('users.max_allowed', '0', 'number', 'users', 'Maximum users (0 = unlimited)', false),
('users.require_email_verification', 'true', 'boolean', 'users', 'Require email verification', false),

-- Features
('features.teams_enabled', 'true', 'boolean', 'features', 'Enable teams functionality', false),
('features.analytics_enabled', 'true', 'boolean', 'features', 'Enable analytics', true)

ON CONFLICT (setting_key) DO NOTHING;

-- Log migration completion
SELECT 'V2003: Tenant template system settings table created' as migration_status;
