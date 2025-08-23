-- NeoMultiTenant - Seed Data: Subscription Plans and Quotas
-- This seed file populates subscription plans and their quota configurations
-- Run with: ./deploy.sh --seed

-- ============================================================================
-- SUBSCRIPTION PLANS: Create comprehensive plan hierarchy
-- ============================================================================

INSERT INTO admin.subscription_plans (
    code, name, description, plan_tier, trial_days,
    price_monthly_cents, price_yearly_cents, setup_fee_cents, currency,
    features, feature_limits, is_active, is_public, sort_order
) VALUES 
-- Free Tier
(
    'free',
    'Free Starter',
    'Perfect for individuals and small projects getting started',
    'free',
    0,
    0,
    0,
    0,
    'USD',
    '{"integrations": 1, "webhooks": 2, "custom_fields": 10, "support": "community", "analytics": "basic"}',
    '{"max_users": 2, "max_storage_gb": 0.5, "max_api_calls_monthly": 1000, "max_databases": 1, "data_retention_days": 30}',
    true,
    true,
    100
),

-- Starter Plan
(
    'starter',
    'Starter Plan',
    'Great for small teams and growing businesses',
    'starter',
    14,
    2900,
    29000,
    0,
    'USD',
    '{"integrations": 5, "webhooks": 10, "custom_fields": 50, "support": "email", "analytics": "basic", "api_access": true}',
    '{"max_users": 10, "max_storage_gb": 10, "max_api_calls_monthly": 25000, "max_databases": 5, "sla": "99%", "support_response": "48h"}',
    true,
    true,
    200
),

-- Professional Plan
(
    'professional',
    'Professional Plan',
    'Advanced features for established businesses',
    'professional',
    14,
    9900,
    99000,
    0,
    'USD',
    '{"integrations": 25, "webhooks": 50, "custom_fields": 200, "support": "priority", "analytics": "advanced", "api_access": "full", "white_label": "partial"}',
    '{"max_users": 50, "max_storage_gb": 100, "max_api_calls_monthly": 250000, "max_databases": 25, "sla": "99.5%", "support_response": "12h"}',
    true,
    true,
    300
),

-- Enterprise Plan
(
    'enterprise',
    'Enterprise Plan',
    'Comprehensive solution for large organizations',
    'enterprise',
    30,
    29900,
    299000,
    50000,
    'USD',
    '{"integrations": "unlimited", "webhooks": "unlimited", "custom_fields": "unlimited", "support": "dedicated", "analytics": "enterprise", "api_access": "unlimited", "white_label": "full", "sso": true, "audit_logs": true}',
    '{"max_users": 500, "max_storage_gb": 1000, "max_api_calls_monthly": 2500000, "max_databases": 100, "sla": "99.9%", "support_response": "4h"}',
    true,
    true,
    400
),

-- Custom Enterprise Plan
(
    'custom',
    'Custom Enterprise',
    'Tailored solutions for unique enterprise requirements',
    'enterprise',
    30,
    0,
    0,
    0,
    'USD',
    '{"everything": "custom", "dedicated_infrastructure": true, "custom_integrations": true, "professional_services": true, "sso": true, "audit_logs": true}',
    '{"max_users": 10000, "max_storage_gb": 10000, "max_api_calls_monthly": 25000000, "max_databases": 1000, "sla": "custom", "support": "24/7"}',
    true,
    false,
    500
)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    price_monthly_cents = EXCLUDED.price_monthly_cents,
    price_yearly_cents = EXCLUDED.price_yearly_cents,
    features = EXCLUDED.features,
    feature_limits = EXCLUDED.feature_limits,
    updated_at = NOW();

-- ============================================================================
-- PLAN QUOTAS: Define detailed quotas for each plan
-- ============================================================================

-- Insert detailed quotas for each plan
WITH plan_ids AS (
    SELECT id, code FROM admin.subscription_plans 
    WHERE code IN ('free', 'starter', 'professional', 'enterprise', 'custom')
)
INSERT INTO admin.plan_quotas (
    plan_id, quota_type, quota_value, is_unlimited, allows_overage, 
    overage_price_per_unit_cents, overage_free_tier
)
SELECT 
    p.id,
    q.quota_type,
    q.quota_value,
    q.is_unlimited,
    q.allows_overage,
    q.overage_price_per_unit_cents,
    q.overage_free_tier
FROM plan_ids p
CROSS JOIN (
    VALUES 
        -- Free Plan Quotas
        ('free', 'max_users', 2, false, false, 0, 0),
        ('free', 'max_storage_gb', 0.5, false, false, 0, 0),
        ('free', 'max_api_calls_monthly', 1000, false, false, 0, 0),
        ('free', 'max_databases', 1, false, false, 0, 0),
        ('free', 'max_integrations', 1, false, false, 0, 0),
        ('free', 'max_webhooks', 2, false, false, 0, 0),
        
        -- Starter Plan Quotas
        ('starter', 'max_users', 10, false, true, 500, 0),
        ('starter', 'max_storage_gb', 10, false, true, 200, 0),
        ('starter', 'max_api_calls_monthly', 25000, false, true, 1, 0),
        ('starter', 'max_databases', 5, false, true, 1000, 0),
        ('starter', 'max_integrations', 5, false, true, 500, 0),
        ('starter', 'max_webhooks', 10, false, true, 100, 0),
        
        -- Professional Plan Quotas
        ('professional', 'max_users', 50, false, true, 300, 0),
        ('professional', 'max_storage_gb', 100, false, true, 150, 0),
        ('professional', 'max_api_calls_monthly', 250000, false, true, 0.5, 0),
        ('professional', 'max_databases', 25, false, true, 800, 0),
        ('professional', 'max_integrations', 25, false, true, 300, 0),
        ('professional', 'max_webhooks', 50, false, true, 50, 0),
        
        -- Enterprise Plan Quotas  
        ('enterprise', 'max_users', 500, false, true, 200, 0),
        ('enterprise', 'max_storage_gb', 1000, false, true, 100, 0),
        ('enterprise', 'max_api_calls_monthly', 2500000, false, true, 0.2, 0),
        ('enterprise', 'max_databases', 100, false, true, 500, 0),
        ('enterprise', 'max_integrations', 100, false, true, 200, 0),
        ('enterprise', 'max_webhooks', 200, false, true, 25, 0),
        
        -- Custom Plan Quotas (high limits)
        ('custom', 'max_users', 10000, false, true, 150, 0),
        ('custom', 'max_storage_gb', 10000, false, true, 50, 0),
        ('custom', 'max_api_calls_monthly', 25000000, false, true, 0.1, 0),
        ('custom', 'max_databases', 1000, false, true, 300, 0),
        ('custom', 'max_integrations', 1000, false, true, 100, 0),
        ('custom', 'max_webhooks', 1000, false, true, 10, 0)
) AS q(plan_code, quota_type, quota_value, is_unlimited, allows_overage, overage_price_per_unit_cents, overage_free_tier)
WHERE p.code = q.plan_code
ON CONFLICT (plan_id, quota_type) DO UPDATE SET
    quota_value = EXCLUDED.quota_value,
    overage_price_per_unit_cents = EXCLUDED.overage_price_per_unit_cents,
    updated_at = NOW();

-- ============================================================================
-- VERIFICATION: Show plans and quotas
-- ============================================================================

-- Show subscription plans
SELECT 
    code,
    name,
    plan_tier,
    price_monthly_cents / 100.0 as monthly_price,
    price_yearly_cents / 100.0 as yearly_price,
    trial_days,
    is_active,
    is_public
FROM admin.subscription_plans
ORDER BY sort_order;

-- Show plan quotas summary
SELECT 
    sp.code,
    sp.name,
    COUNT(pq.id) as quota_count,
    STRING_AGG(pq.quota_type || ':' || pq.quota_value, ', ' ORDER BY pq.quota_type) as quotas
FROM admin.subscription_plans sp
LEFT JOIN admin.plan_quotas pq ON sp.id = pq.plan_id
GROUP BY sp.id, sp.code, sp.name, sp.sort_order
ORDER BY sp.sort_order;

-- Log completion
SELECT 'Subscription plans and quotas seeded successfully' as seed_status;
