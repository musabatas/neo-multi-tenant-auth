-- NeoMultiTenant - Seed Data: Tenant Management (Subscriptions, Quotas, Settings)
-- This seed file populates tenant subscriptions, quotas, settings, and contacts
-- Run with: ./deploy.sh --seed

-- ============================================================================
-- TENANT SUBSCRIPTIONS: Link tenants to subscription plans
-- ============================================================================

-- Create realistic subscription assignments based on organization tiers
WITH tenant_data AS (
    SELECT 
        t.id as tenant_id,
        t.name as tenant_name,
        t.slug as tenant_slug,
        o.company_size as org_size,
        o.name as org_name
    FROM admin.tenants t
    JOIN admin.organizations o ON t.organization_id = o.id
),
plan_data AS (
    SELECT id as plan_id, code FROM admin.subscription_plans
),
admin_user AS (
    SELECT id as admin_id FROM admin.users WHERE email = 'admin@neomultitenant.com' LIMIT 1
)
INSERT INTO admin.tenant_subscriptions (
    tenant_id, plan_id, status, billing_cycle, currency,
    price_cents, discount_percentage, trial_start, trial_end,
    current_period_start, current_period_end, next_billing_date,
    auto_renew, custom_pricing, metadata,
    subscribed_at, activated_at
)
SELECT 
    td.tenant_id,
    pd.plan_id,
    'active'::admin.subscription_status,
    sub.billing_cycle::admin.billing_cycle,
    'USD',
    sub.price_cents,
    sub.discount_percentage,
    sub.trial_start::date,
    sub.trial_end::date,
    sub.current_period_start::date,
    sub.current_period_end::date,
    sub.next_billing_date::date,
    sub.auto_renew,
    sub.custom_pricing,
    sub.metadata::jsonb,
    sub.subscribed_at::timestamptz,
    sub.activated_at::timestamptz
FROM tenant_data td
CROSS JOIN admin_user au
JOIN (
    VALUES 
        -- TechCorp subscriptions
        ('techcorp-prod', 'professional', 'monthly', 9900, 10.0, NULL, NULL, NOW() - INTERVAL '6 months', NOW() + INTERVAL '1 month' - INTERVAL '6 months', NOW() + INTERVAL '1 month', true, false, '{"sales_rep": "john.sales@company.com", "contract_term": 12}', NOW() - INTERVAL '6 months', NOW() - INTERVAL '6 months'),
        ('techcorp-staging', 'starter', 'monthly', 2900, 0.0, NULL, NULL, NOW() - INTERVAL '5 months', NOW() + INTERVAL '1 month' - INTERVAL '5 months', NOW() + INTERVAL '1 month', true, false, '{"environment": "staging", "auto_downgrade": true}', NOW() - INTERVAL '5 months', NOW() - INTERVAL '5 months'),
        
        -- StartupFlex subscriptions
        ('startupflex-main', 'starter', 'annual', 29000, 15.0, NOW() - INTERVAL '3 months', NOW() - INTERVAL '2 months 15 days', NOW() - INTERVAL '3 months', NOW() + INTERVAL '9 months', NOW() + INTERVAL '9 months', true, false, '{"startup_discount": true, "referral_code": "STARTUP2024"}', NOW() - INTERVAL '3 months', NOW() - INTERVAL '2 months 15 days'),
        
        -- AI Innovate subscriptions
        ('ai-innovate-prod', 'professional', 'annual', 99000, 20.0, NULL, NULL, NOW() - INTERVAL '8 months', NOW() + INTERVAL '4 months', NOW() + INTERVAL '4 months', true, false, '{"eu_customer": true, "currency_preference": "EUR", "vat_number": "FR123456789"}', NOW() - INTERVAL '8 months', NOW() - INTERVAL '8 months'),
        ('ai-innovate-research', 'professional', 'monthly', 9900, 5.0, NULL, NULL, NOW() - INTERVAL '6 months', NOW() + INTERVAL '1 month' - INTERVAL '6 months', NOW() + INTERVAL '1 month', true, false, '{"research_discount": true, "academic_rate": false}', NOW() - INTERVAL '6 months', NOW() - INTERVAL '6 months'),
        
        -- Enterprise Solutions subscriptions
        ('enterprise-us-prod', 'enterprise', 'annual', 299000, 25.0, NULL, NULL, NOW() - INTERVAL '2 years', NOW() + INTERVAL '10 months', NOW() + INTERVAL '10 months', true, true, '{"enterprise_contract": true, "dedicated_support": true, "sla": "99.9%"}', NOW() - INTERVAL '2 years', NOW() - INTERVAL '2 years'),
        ('enterprise-eu-prod', 'enterprise', 'annual', 299000, 25.0, NULL, NULL, NOW() - INTERVAL '18 months', NOW() + INTERVAL '6 months', NOW() + INTERVAL '6 months', true, true, '{"enterprise_contract": true, "gdpr_premium": true, "data_residency": "eu"}', NOW() - INTERVAL '18 months', NOW() - INTERVAL '18 months'),
        
        -- Global Corp subscriptions - Custom plans
        ('globalcorp-eu-prod', 'custom', 'annual', 1500000, 0.0, NULL, NULL, NOW() - INTERVAL '3 years', NOW() + INTERVAL '9 months', NOW() + INTERVAL '9 months', true, true, '{"custom_contract": true, "dedicated_infrastructure": true, "multi_region": true, "manufacturing_features": true}', NOW() - INTERVAL '3 years', NOW() - INTERVAL '3 years'),
        ('globalcorp-us-prod', 'custom', 'annual', 1200000, 0.0, NULL, NULL, NOW() - INTERVAL '3 years', NOW() + INTERVAL '9 months', NOW() + INTERVAL '9 months', true, true, '{"custom_contract": true, "manufacturing_features": true, "compliance_package": "us"}', NOW() - INTERVAL '3 years', NOW() - INTERVAL '3 years')
) AS sub(tenant_slug, plan_code, billing_cycle, price_cents, discount_percentage, trial_start, trial_end, current_period_start, current_period_end, next_billing_date, auto_renew, custom_pricing, metadata, subscribed_at, activated_at) ON td.tenant_slug = sub.tenant_slug
JOIN plan_data pd ON pd.code = sub.plan_code
ON CONFLICT (tenant_id, plan_id) DO NOTHING;

-- ============================================================================
-- TENANT QUOTAS: Set resource quotas and track usage
-- ============================================================================

-- Create quota records for each tenant based on their subscription plan
WITH tenant_subscriptions AS (
    SELECT 
        ts.tenant_id,
        t.slug as tenant_slug,
        sp.code as plan_code,
        (sp.feature_limits->>'max_users')::integer as max_users,
        (sp.feature_limits->>'max_storage_gb')::numeric as max_storage_gb,
        (sp.feature_limits->>'max_api_calls_monthly')::bigint as max_api_calls_monthly
    FROM admin.tenant_subscriptions ts
    JOIN admin.tenants t ON ts.tenant_id = t.id
    JOIN admin.subscription_plans sp ON ts.plan_id = sp.id
)
INSERT INTO admin.tenant_quotas (
    tenant_id, storage_quota_gb, storage_used_gb, files_quota, files_used,
    backup_retention_days, users_quota, users_active, admin_users_quota, guest_users_quota,
    api_calls_monthly, api_calls_current_month, api_rate_limit_per_minute,
    bandwidth_quota_gb, bandwidth_used_gb, integrations_quota, integrations_active,
    workflows_quota, webhooks_quota, custom_fields_quota,
    database_size_quota_gb, quota_period_start, quota_period_end, last_reset_at
)
SELECT 
    ts.tenant_id,
    ts.max_storage_gb,
    q.storage_used,
    q.files_quota,
    q.files_used,
    q.backup_retention_days,
    ts.max_users,
    q.users_active,
    q.admin_users_quota,
    q.guest_users_quota,
    ts.max_api_calls_monthly,
    q.api_calls_current,
    q.api_rate_limit,
    q.bandwidth_quota_gb,
    q.bandwidth_used_gb,
    q.integrations_quota,
    q.integrations_active,
    q.workflows_quota,
    q.webhooks_quota,
    q.custom_fields_quota,
    q.database_size_quota_gb,
    DATE_TRUNC('month', NOW()),
    DATE_TRUNC('month', NOW()) + INTERVAL '1 month' - INTERVAL '1 day',
    NOW()
FROM tenant_subscriptions ts
JOIN (
    VALUES 
        -- TechCorp quotas (Professional plan usage)
        ('techcorp-prod', 8.5, 50000, 45000, 365, 25, 3, 15, 18500, 80, 25.5, 20, 15, 8, 35, 150, 10, 5.2),
        ('techcorp-staging', 2.1, 10000, 8500, 90, 8, 2, 5, 2200, 120, 4.2, 3, 8, 2, 5, 50, 3, 1.8),
        
        -- StartupFlex quotas (Starter plan usage)
        ('startupflex-main', 3.2, 15000, 12000, 365, 6, 1, 8, 8500, 100, 8.1, 4, 6, 3, 5, 25, 5, 2.1),
        
        -- AI Innovate quotas (Professional plan usage)
        ('ai-innovate-prod', 45.8, 75000, 62000, 365, 28, 4, 20, 125000, 60, 52.3, 18, 22, 12, 25, 180, 15, 18.7),
        ('ai-innovate-research', 22.1, 30000, 28500, 180, 15, 2, 10, 45000, 80, 18.9, 12, 18, 8, 15, 120, 8, 8.2),
        
        -- Enterprise Solutions quotas (Enterprise plan usage)
        ('enterprise-us-prod', 285.6, 150000, 145000, 2555, 180, 8, 75, 850000, 40, 312.8, 85, 95, 45, 75, 450, 35, 156.2),
        ('enterprise-eu-prod', 198.7, 120000, 115000, 2555, 125, 6, 50, 680000, 40, 245.1, 65, 78, 38, 68, 380, 28, 98.5),
        
        -- Global Corp quotas (Custom plan usage)
        ('globalcorp-eu-prod', 1250.8, 500000, 485000, 3650, 450, 12, 200, 1850000, 20, 1156.7, 280, 350, 150, 185, 850, 85, 542.3),
        ('globalcorp-us-prod', 1088.5, 450000, 440000, 3650, 380, 10, 180, 1650000, 20, 1001.2, 245, 320, 135, 168, 750, 78, 456.8)
) AS q(tenant_slug, storage_used, files_quota, files_used, backup_retention_days, users_active, admin_users_quota, guest_users_quota, api_calls_current, api_rate_limit, bandwidth_quota_gb, bandwidth_used_gb, integrations_quota, integrations_active, workflows_quota, webhooks_quota, custom_fields_quota, database_size_quota_gb) ON ts.tenant_slug = q.tenant_slug
ON CONFLICT (tenant_id) DO UPDATE SET
    storage_used_gb = EXCLUDED.storage_used_gb,
    files_used = EXCLUDED.files_used,
    users_active = EXCLUDED.users_active,
    api_calls_current_month = EXCLUDED.api_calls_current_month,
    bandwidth_used_gb = EXCLUDED.bandwidth_used_gb,
    integrations_active = EXCLUDED.integrations_active,
    last_reset_at = EXCLUDED.last_reset_at,
    updated_at = NOW();

-- ============================================================================
-- TENANT SETTINGS: Configure tenant-specific settings
-- ============================================================================

-- Create comprehensive settings for each tenant
WITH tenant_data AS (
    SELECT 
        t.id as tenant_id,
        t.slug as tenant_slug,
        t.name as tenant_name
    FROM admin.tenants t
),
admin_user AS (
    SELECT id as admin_id FROM admin.users WHERE email = 'admin@neomultitenant.com' LIMIT 1
)
INSERT INTO admin.tenant_settings (
    tenant_id, setting_key, setting_value, setting_type, category,
    is_public, is_readonly, requires_admin, description, updated_by
)
SELECT 
    td.tenant_id,
    s.setting_key,
    s.setting_value::jsonb,
    s.setting_type,
    s.category,
    s.is_public,
    s.is_readonly,
    s.requires_admin,
    s.description,
    au.admin_id
FROM tenant_data td
CROSS JOIN admin_user au
JOIN (
    VALUES 
        -- General settings for all tenants
        ('default_timezone', '"America/New_York"', 'string', 'general', true, false, false, 'Default timezone for the tenant'),
        ('default_locale', '"en-US"', 'string', 'general', true, false, false, 'Default locale for the tenant'),
        ('date_format', '"MM/DD/YYYY"', 'string', 'general', true, false, false, 'Default date format'),
        ('currency', '"USD"', 'string', 'billing', true, false, false, 'Default currency for billing'),
        ('theme', '"light"', 'string', 'ui', true, false, false, 'Default UI theme'),
        ('session_timeout', '480', 'number', 'security', false, false, true, 'Session timeout in minutes'),
        ('mfa_required', 'false', 'boolean', 'security', false, false, true, 'Whether MFA is required for all users'),
        ('password_policy', '{"min_length": 8, "require_special": true, "require_numbers": true}', 'json', 'security', false, false, true, 'Password complexity requirements'),
        ('api_rate_limit', '1000', 'number', 'api', false, false, true, 'API rate limit per minute'),
        ('webhook_timeout', '30', 'number', 'integration', false, false, false, 'Webhook timeout in seconds'),
        ('backup_enabled', 'true', 'boolean', 'system', false, false, true, 'Whether automatic backups are enabled'),
        ('backup_frequency', '"daily"', 'string', 'system', false, false, true, 'Backup frequency'),
        ('maintenance_window', '"02:00-04:00"', 'string', 'system', false, false, false, 'Preferred maintenance window'),
        ('notification_email', '"notifications@example.com"', 'string', 'notification', false, false, false, 'Email for system notifications'),
        ('analytics_enabled', 'true', 'boolean', 'feature', true, false, false, 'Whether analytics tracking is enabled'),
        ('custom_branding', '{"logo_url": "", "primary_color": "#007bff", "secondary_color": "#6c757d"}', 'json', 'ui', true, false, false, 'Custom branding configuration')
) AS s(setting_key, setting_value, setting_type, category, is_public, is_readonly, requires_admin, description) ON td.tenant_slug IN ('techcorp-prod', 'techcorp-staging', 'startupflex-main', 'ai-innovate-prod', 'ai-innovate-research', 'enterprise-us-prod', 'enterprise-eu-prod', 'globalcorp-eu-prod', 'globalcorp-us-prod')

UNION ALL

-- Specific settings per tenant type
SELECT 
    td.tenant_id,
    s.setting_key,
    s.setting_value::jsonb,
    s.setting_type,
    s.category,
    s.is_public,
    s.is_readonly,
    s.requires_admin,
    s.description,
    au.admin_id
FROM tenant_data td
CROSS JOIN admin_user au
JOIN (
    VALUES 
        -- EU-specific settings
        ('ai-innovate-prod', 'gdpr_compliant', 'true', 'boolean', 'compliance', false, false, true, 'GDPR compliance enabled'),
        ('ai-innovate-research', 'gdpr_compliant', 'true', 'boolean', 'compliance', false, false, true, 'GDPR compliance enabled'),
        ('enterprise-eu-prod', 'gdpr_compliant', 'true', 'boolean', 'compliance', false, false, true, 'GDPR compliance enabled'),
        ('globalcorp-eu-prod', 'gdpr_compliant', 'true', 'boolean', 'compliance', false, false, true, 'GDPR compliance enabled'),
        ('ai-innovate-prod', 'data_residency', '"eu-west-1"', 'string', 'compliance', false, false, true, 'Required data residency region'),
        ('enterprise-eu-prod', 'data_residency', '"eu-west-1"', 'string', 'compliance', false, false, true, 'Required data residency region'),
        ('globalcorp-eu-prod', 'data_residency', '"eu-west-1"', 'string', 'compliance', false, false, true, 'Required data residency region'),
        
        -- Enterprise-specific settings
        ('enterprise-us-prod', 'sso_enabled', 'true', 'boolean', 'security', false, false, false, 'Single Sign-On enabled'),
        ('enterprise-eu-prod', 'sso_enabled', 'true', 'boolean', 'security', false, false, false, 'Single Sign-On enabled'),
        ('globalcorp-eu-prod', 'sso_enabled', 'true', 'boolean', 'security', false, false, false, 'Single Sign-On enabled'),
        ('globalcorp-us-prod', 'sso_enabled', 'true', 'boolean', 'security', false, false, false, 'Single Sign-On enabled'),
        ('enterprise-us-prod', 'audit_logs_retention', '2555', 'number', 'compliance', false, false, true, 'Audit log retention in days'),
        ('enterprise-eu-prod', 'audit_logs_retention', '2555', 'number', 'compliance', false, false, true, 'Audit log retention in days'),
        ('globalcorp-eu-prod', 'audit_logs_retention', '3650', 'number', 'compliance', false, false, true, 'Audit log retention in days'),
        ('globalcorp-us-prod', 'audit_logs_retention', '3650', 'number', 'compliance', false, false, true, 'Audit log retention in days'),
        
        -- Development/Staging specific settings
        ('techcorp-staging', 'auto_cleanup', 'true', 'boolean', 'system', false, false, false, 'Auto cleanup old data'),
        ('techcorp-staging', 'debug_mode', 'true', 'boolean', 'development', false, false, false, 'Enable debug logging')
) AS s(tenant_slug, setting_key, setting_value, setting_type, category, is_public, is_readonly, requires_admin, description) ON td.tenant_slug = s.tenant_slug
ON CONFLICT (tenant_id, setting_key) DO UPDATE SET
    setting_value = EXCLUDED.setting_value,
    updated_by = EXCLUDED.updated_by,
    updated_at = NOW();

-- ============================================================================
-- TENANT CONTACTS: Additional contacts beyond primary contact
-- ============================================================================

-- Add technical and billing contacts for each tenant
WITH tenant_data AS (
    SELECT 
        t.id as tenant_id,
        t.slug as tenant_slug,
        t.name as tenant_name
    FROM admin.tenants t
),
contact_users AS (
    SELECT 
        id as user_id, 
        email,
        first_name || ' ' || last_name as full_name
    FROM admin.users 
    WHERE email IN ('manager@techcorp.com', 'dev@startupflex.io', 'founder@aiinnovate.eu', 
                    'cto@enterprisesol.com', 'director@globalcorp.com')
)
INSERT INTO admin.tenant_contacts (
    tenant_id, user_id, contact_type, contact_info, is_primary,
    receive_notifications
)
SELECT 
    td.tenant_id,
    cu.user_id,
    c.contact_type::admin.contact_type,
    c.contact_info::jsonb,
    c.is_primary,
    c.receive_notifications
FROM tenant_data td
JOIN contact_users cu ON true
JOIN (
    VALUES 
        -- TechCorp contacts
        ('techcorp-prod', 'manager@techcorp.com', 'technical', '{"phone": "+1-555-0123", "role": "Technical Lead", "department": "Engineering"}', false, true),
        ('techcorp-staging', 'manager@techcorp.com', 'technical', '{"phone": "+1-555-0123", "role": "Technical Lead", "department": "Engineering"}', false, true),
        
        -- StartupFlex contacts
        ('startupflex-main', 'dev@startupflex.io', 'technical', '{"phone": "+1-555-0456", "role": "Senior Developer", "department": "Engineering"}', false, true),
        
        -- AI Innovate contacts (founder as technical contact)
        ('ai-innovate-prod', 'founder@aiinnovate.eu', 'technical', '{"phone": "+33-1-23-45-67-89", "role": "Founder & CTO", "department": "Engineering"}', false, true),
        ('ai-innovate-research', 'founder@aiinnovate.eu', 'technical', '{"phone": "+33-1-23-45-67-89", "role": "Founder & CTO", "department": "Research"}', false, true),
        
        -- Enterprise Solutions contacts
        ('enterprise-us-prod', 'cto@enterprisesol.com', 'technical', '{"phone": "+1-555-0789", "role": "Chief Technology Officer", "department": "Technology"}', false, true),
        ('enterprise-eu-prod', 'cto@enterprisesol.com', 'technical', '{"phone": "+1-555-0789", "role": "Chief Technology Officer", "department": "Technology"}', false, true),
        
        -- Global Corp contacts
        ('globalcorp-eu-prod', 'director@globalcorp.com', 'technical', '{"phone": "+49-89-123-45678", "role": "IT Director", "department": "Technology"}', false, true),
        ('globalcorp-us-prod', 'director@globalcorp.com', 'admin', '{"phone": "+49-89-123-45678", "role": "IT Director", "department": "Technology"}', false, true)
) AS c(tenant_slug, contact_email, contact_type, contact_info, is_primary, receive_notifications) ON td.tenant_slug = c.tenant_slug AND cu.email = c.contact_email
ON CONFLICT (tenant_id, user_id, contact_type) DO UPDATE SET
    contact_info = EXCLUDED.contact_info,
    receive_notifications = EXCLUDED.receive_notifications,
    updated_at = NOW();

-- ============================================================================
-- VERIFICATION: Show tenant management data
-- ============================================================================

-- Show tenant subscriptions summary
SELECT 
    t.name as tenant,
    sp.name as plan_name,
    ts.status,
    ts.billing_cycle,
    ts.price_cents / 100.0 as price,
    ts.current_period_end::date as period_end,
    ts.auto_renew
FROM admin.tenant_subscriptions ts
JOIN admin.tenants t ON ts.tenant_id = t.id
JOIN admin.subscription_plans sp ON ts.plan_id = sp.id
ORDER BY t.name;

-- Show tenant quotas summary
SELECT 
    t.name as tenant,
    tq.users_quota,
    tq.users_active,
    tq.storage_quota_gb,
    ROUND(tq.storage_used_gb, 1) as storage_used_gb,
    tq.api_calls_monthly,
    tq.api_calls_current_month,
    ROUND((tq.storage_used_gb / tq.storage_quota_gb * 100), 1) as storage_usage_pct
FROM admin.tenant_quotas tq
JOIN admin.tenants t ON tq.tenant_id = t.id
ORDER BY storage_usage_pct DESC;

-- Show tenant settings count per category
SELECT 
    t.name as tenant,
    ts.category,
    COUNT(*) as settings_count
FROM admin.tenant_settings ts
JOIN admin.tenants t ON ts.tenant_id = t.id
GROUP BY t.name, ts.category
ORDER BY t.name, ts.category;

-- Show tenant contacts summary
SELECT 
    t.name as tenant,
    tc.contact_type,
    u.display_name as contact_name,
    u.email,
    tc.receive_notifications
FROM admin.tenant_contacts tc
JOIN admin.tenants t ON tc.tenant_id = t.id
JOIN admin.users u ON tc.user_id = u.id
ORDER BY t.name, tc.contact_type;

-- Log completion
SELECT 'Tenant management data seeded successfully' as seed_status;
