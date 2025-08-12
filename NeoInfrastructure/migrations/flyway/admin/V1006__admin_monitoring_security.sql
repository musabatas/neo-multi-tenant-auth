-- V007: Admin Monitoring and Security
-- Creates system monitoring, alerts, and security tables
-- Applied to: Admin database only

-- Ensure pgcrypto extension exists (required for uuid_generate_v7)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================================
-- SYSTEM ALERTS (Platform-wide monitoring and alerting)
-- ============================================================================

CREATE TABLE admin.system_alerts (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    alert_name VARCHAR(100) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    severity admin.risk_level NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    source_id VARCHAR(255),
    region_id UUID REFERENCES admin.regions,
    tenant_id UUID REFERENCES admin.tenants,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    resolution_steps TEXT,
    status VARCHAR(30) DEFAULT 'open' 
        CONSTRAINT valid_alert_status CHECK (status IN ('open', 'acknowledged', 'investigating', 'resolved', 'closed')),
    acknowledged_by UUID REFERENCES admin.platform_users,
    acknowledged_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES admin.platform_users,
    resolved_at TIMESTAMPTZ,
    first_occurrence_at TIMESTAMPTZ DEFAULT NOW(),
    last_occurrence_at TIMESTAMPTZ DEFAULT NOW(),
    occurrence_count INTEGER DEFAULT 1,
    escalation_level INTEGER DEFAULT 1 
        CONSTRAINT valid_escalation_level CHECK (escalation_level >= 1 AND escalation_level <= 5),
    escalated_at TIMESTAMPTZ,
    escalated_to UUID REFERENCES admin.platform_users,
    notifications_sent INTEGER DEFAULT 0,
    last_notification_sent_at TIMESTAMPTZ,
    suppress_notifications_until TIMESTAMPTZ,
    affected_systems TEXT[],
    impact_description TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for system_alerts
CREATE INDEX idx_system_alerts_name ON admin.system_alerts(alert_name);
CREATE INDEX idx_system_alerts_type ON admin.system_alerts(alert_type);
CREATE INDEX idx_system_alerts_severity ON admin.system_alerts(severity);
CREATE INDEX idx_system_alerts_status ON admin.system_alerts(status);
CREATE INDEX idx_system_alerts_region ON admin.system_alerts(region_id);
CREATE INDEX idx_system_alerts_tenant ON admin.system_alerts(tenant_id);
CREATE INDEX idx_system_alerts_source ON admin.system_alerts(source_type, source_id);
CREATE INDEX idx_system_alerts_escalation ON admin.system_alerts(escalation_level);
CREATE INDEX idx_system_alerts_occurrence ON admin.system_alerts(last_occurrence_at);

-- ============================================================================
-- API RATE LIMITS (Rate limiting configuration and enforcement)
-- ============================================================================

CREATE TABLE admin.api_rate_limits (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    limit_name VARCHAR(100) NOT NULL UNIQUE,
    limit_type VARCHAR(30) NOT NULL 
        CONSTRAINT valid_limit_type CHECK (limit_type IN ('user', 'tenant', 'ip', 'api_key', 'global')),
    requests_per_window INTEGER NOT NULL,
    window_size_seconds INTEGER NOT NULL,
    burst_allowance INTEGER DEFAULT 0,
    applies_to_users BOOLEAN DEFAULT false,
    applies_to_tenants UUID[],
    applies_to_endpoints TEXT[],
    is_active BOOLEAN DEFAULT true,
    enforce_strict BOOLEAN DEFAULT true,
    block_duration_seconds INTEGER DEFAULT 300,
    send_alert BOOLEAN DEFAULT true,
    alert_threshold_percentage SMALLINT DEFAULT 90 
        CONSTRAINT valid_alert_threshold CHECK (alert_threshold_percentage >= 0 AND alert_threshold_percentage <= 100),
    description TEXT,
    created_by UUID REFERENCES admin.platform_users,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT positive_limits CHECK (
        requests_per_window > 0 AND 
        window_size_seconds > 0 AND 
        burst_allowance >= 0 AND 
        block_duration_seconds >= 0
    )
);

-- Indexes for api_rate_limits
CREATE INDEX idx_api_rate_limits_name ON admin.api_rate_limits(limit_name);
CREATE INDEX idx_api_rate_limits_type ON admin.api_rate_limits(limit_type);
CREATE INDEX idx_api_rate_limits_active ON admin.api_rate_limits(is_active);
CREATE INDEX idx_api_rate_limits_tenants ON admin.api_rate_limits USING GIN(applies_to_tenants);
CREATE INDEX idx_api_rate_limits_endpoints ON admin.api_rate_limits USING GIN(applies_to_endpoints);

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================

CREATE TRIGGER update_system_alerts_updated_at
    BEFORE UPDATE ON admin.system_alerts
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_api_rate_limits_updated_at
    BEFORE UPDATE ON admin.api_rate_limits
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE admin.system_alerts IS 'Platform-wide system monitoring, alerts, and incident management';
COMMENT ON TABLE admin.api_rate_limits IS 'API rate limiting configuration and enforcement rules';



-- Insert default subscription plans
INSERT INTO admin.subscription_plans (code, name, description, price_monthly_cents, price_yearly_cents, plan_tier, features) VALUES
('free', 'Free Plan', 'Basic features for getting started', 0, 0, 'free', '{"users": 5, "storage_gb": 1, "api_calls": 1000}'),
('starter', 'Starter Plan', 'Perfect for small teams', 2900, 31000, 'starter', '{"users": 25, "storage_gb": 10, "api_calls": 10000}'),
('professional', 'Professional Plan', 'Advanced features for growing businesses', 9900, 105000, 'professional', '{"users": 100, "storage_gb": 100, "api_calls": 100000}'),
('enterprise', 'Enterprise Plan', 'Full-featured plan for large organizations', 29900, 319000, 'enterprise', '{"users": -1, "storage_gb": 1000, "api_calls": 1000000}');

-- Insert default API rate limits
INSERT INTO admin.api_rate_limits (limit_name, limit_type, requests_per_window, window_size_seconds, description) VALUES
('global_default', 'global', 1000, 60, 'Default global rate limit - 1000 requests per minute'),
('tenant_default', 'tenant', 100, 60, 'Default tenant rate limit - 100 requests per minute'),
('user_default', 'user', 60, 60, 'Default user rate limit - 60 requests per minute'),
('api_key_default', 'api_key', 500, 60, 'Default API key rate limit - 500 requests per minute');

-- Insert default platform permissions
INSERT INTO admin.platform_permissions (code, description, resource, action, scope_level) VALUES
('platform.admin.read', 'Read platform administration data', 'platform', 'read', 'platform'),
('platform.admin.write', 'Modify platform administration data', 'platform', 'write', 'platform'),
('platform.users.read', 'View platform users', 'users', 'read', 'platform'),
('platform.users.write', 'Manage platform users', 'users', 'write', 'platform'),
('platform.tenants.read', 'View tenant information', 'tenants', 'read', 'platform'),
('platform.tenants.write', 'Manage tenants', 'tenants', 'write', 'platform'),
('platform.billing.read', 'View billing information', 'billing', 'read', 'platform'),
('platform.billing.write', 'Manage billing and subscriptions', 'billing', 'write', 'platform'),
('tenant.admin.read', 'Read tenant administration data', 'tenant', 'read', 'tenant'),
('tenant.admin.write', 'Modify tenant administration data', 'tenant', 'write', 'tenant'),
('tenant.users.read', 'View tenant users', 'users', 'read', 'tenant'),
('tenant.users.write', 'Manage tenant users', 'users', 'write', 'tenant');

-- Insert default platform roles
INSERT INTO admin.platform_roles (code, name, description, role_level, is_system) VALUES
('super_admin', 'Super Administrator', 'Full platform access with all permissions', 'system', true),
('platform_admin', 'Platform Administrator', 'Platform administration access', 'platform', true),
('tenant_admin', 'Tenant Administrator', 'Tenant-level administration access', 'tenant', true),
('tenant_user', 'Tenant User', 'Basic tenant user access', 'tenant', true);

-- Grant permissions to roles
INSERT INTO admin.role_permissions (role_id, permission_id) 
SELECT r.id, p.id 
FROM admin.platform_roles r 
CROSS JOIN admin.platform_permissions p 
WHERE r.code = 'super_admin';

INSERT INTO admin.role_permissions (role_id, permission_id) 
SELECT r.id, p.id 
FROM admin.platform_roles r 
CROSS JOIN admin.platform_permissions p 
WHERE r.code = 'platform_admin' AND p.code LIKE 'platform.%';

INSERT INTO admin.role_permissions (role_id, permission_id) 
SELECT r.id, p.id 
FROM admin.platform_roles r 
CROSS JOIN admin.platform_permissions p 
WHERE r.code = 'tenant_admin' AND p.code LIKE 'tenant.%';

INSERT INTO admin.role_permissions (role_id, permission_id) 
SELECT r.id, p.id 
FROM admin.platform_roles r 
CROSS JOIN admin.platform_permissions p 
WHERE r.code = 'tenant_user' AND p.code IN ('tenant.admin.read', 'tenant.users.read');

-- Log migration completion
SELECT 'V007: Admin monitoring, security, and default data created' as migration_status;