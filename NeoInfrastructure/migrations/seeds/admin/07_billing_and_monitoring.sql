-- ============================================================================
-- BILLING AND MONITORING SEED DATA
-- Creates realistic invoice, payment, monitoring, and rate limiting data
-- ============================================================================

-- ============================================================================
-- TENANT SUBSCRIPTIONS: Create active subscriptions for tenants
-- ============================================================================

-- First create tenant subscriptions
WITH tenant_plan_data AS (
    SELECT 
        t.id as tenant_id,
        t.slug as tenant_slug,
        sp.id as plan_id,
        sp.code as plan_code,
        sp.price_monthly_cents,
        sp.price_yearly_cents
    FROM admin.tenants t
    CROSS JOIN admin.subscription_plans sp
    WHERE sp.code IN ('professional', 'starter', 'enterprise', 'free')
)
INSERT INTO admin.tenant_subscriptions (
    tenant_id, plan_id, external_subscription_id, status, billing_cycle,
    current_period_start, current_period_end, trial_start, trial_end,
    auto_renew, price_cents, currency, created_at
)
SELECT 
    tpd.tenant_id,
    tpd.plan_id,
    sub.external_subscription_id,
    sub.status::admin.subscription_status,
    sub.billing_cycle::admin.billing_cycle,
    sub.current_period_start::date,
    sub.current_period_end::date,
    sub.trial_start::date,
    sub.trial_end::date,
    sub.auto_renew,
    sub.price_cents,
    sub.currency,
    sub.created_at::timestamptz
FROM tenant_plan_data tpd
JOIN (
    VALUES 
        -- TechCorp subscriptions
        ('techcorp-prod', 'professional', 'stripe_sub_1234567', 'active', 'monthly', NOW() - INTERVAL '3 months', NOW() + INTERVAL '1 month', NOW() - INTERVAL '6 months', NOW() - INTERVAL '3 months', true, 9900, 'USD', 'stripe', NOW() - INTERVAL '6 months'),
        ('techcorp-staging', 'starter', 'stripe_sub_2345678', 'active', 'monthly', NOW() - INTERVAL '2 months', NOW() + INTERVAL '1 month', NOW() - INTERVAL '4 months', NOW() - INTERVAL '2 months', true, 2900, 'USD', 'stripe', NOW() - INTERVAL '4 months'),
        
        -- StartupFlex subscription  
        ('startupflex-main', 'starter', 'stripe_sub_3456789', 'active', 'yearly', NOW() - INTERVAL '11 months', NOW() + INTERVAL '1 month', NOW() - INTERVAL '12 months', NOW() - INTERVAL '11 months', true, 31000, 'USD', 'stripe', NOW() - INTERVAL '12 months'),
        
        -- AI Innovate subscriptions
        ('ai-innovate-prod', 'professional', 'ai_sub_001', 'active', 'monthly', NOW() - INTERVAL '3 months', NOW() + INTERVAL '1 month', NOW() - INTERVAL '6 months', NOW() - INTERVAL '3 months', true, 10500, 'EUR', 'invoice', NOW() - INTERVAL '6 months'),
        ('ai-innovate-research', 'professional', 'ai_sub_002', 'active', 'monthly', NOW() - INTERVAL '2 months', NOW() + INTERVAL '1 month', NOW() - INTERVAL '4 months', NOW() - INTERVAL '2 months', true, 10500, 'EUR', 'invoice', NOW() - INTERVAL '4 months'),
        
        -- Enterprise Solutions subscriptions
        ('enterprise-us-prod', 'enterprise', 'ent_sub_001', 'active', 'yearly', NOW() - INTERVAL '12 months', NOW(), NOW() - INTERVAL '18 months', NOW() - INTERVAL '12 months', true, 319000, 'USD', 'invoice', NOW() - INTERVAL '18 months'),
        ('enterprise-eu-prod', 'enterprise', 'ent_sub_002', 'active', 'yearly', NOW() - INTERVAL '18 months', NOW() - INTERVAL '6 months', NOW() - INTERVAL '24 months', NOW() - INTERVAL '18 months', true, 319000, 'EUR', 'invoice', NOW() - INTERVAL '24 months'),
        
        -- Global Corp subscriptions (custom pricing)
        ('globalcorp-eu-prod', 'enterprise', 'gc_sub_001', 'active', 'yearly', NOW() - INTERVAL '3 years', NOW() - INTERVAL '2 years', NULL, NULL, true, 1500000, 'EUR', 'contract', NOW() - INTERVAL '3 years'),
        ('globalcorp-us-prod', 'enterprise', 'gc_sub_002', 'active', 'yearly', NOW() - INTERVAL '3 years', NOW() - INTERVAL '2 years', NULL, NULL, true, 1200000, 'USD', 'contract', NOW() - INTERVAL '3 years')
) AS sub(tenant_slug, plan_code, external_subscription_id, status, billing_cycle, current_period_start, current_period_end, trial_start, trial_end, auto_renew, price_cents, currency, subscription_source, created_at) 
ON tpd.tenant_slug = sub.tenant_slug AND tpd.plan_code = sub.plan_code
ON CONFLICT (tenant_id, plan_id) DO NOTHING;

-- ============================================================================
-- INVOICES: Generate realistic invoices for tenant subscriptions
-- ============================================================================

-- Create invoices for active subscriptions
WITH subscription_data AS (
    SELECT 
        ts.id as subscription_id,
        ts.tenant_id,
        t.slug as tenant_slug,
        ts.price_cents,
        ts.billing_cycle,
        ts.current_period_start,
        ts.current_period_end,
        ts.currency
    FROM admin.tenant_subscriptions ts
    JOIN admin.tenants t ON ts.tenant_id = t.id
    WHERE ts.status = 'active'
)
INSERT INTO admin.invoices (
    tenant_id, subscription_id, invoice_number, status, invoice_type,
    currency, subtotal_cents, tax_cents, discount_cents, total_cents,
    period_start, period_end, due_at, issued_at, paid_at,
    payment_method, external_invoice_id, customer_notes, tax_rate
)
SELECT 
    sd.tenant_id,
    sd.subscription_id,
    inv.invoice_number,
    inv.status::admin.invoice_status,
    inv.invoice_type,
    sd.currency,
    inv.subtotal_cents,
    inv.tax_cents,
    inv.discount_cents,
    inv.total_cents,
    inv.period_start::date,
    inv.period_end::date,
    inv.due_at::timestamptz,
    inv.issued_at::timestamptz,
    inv.paid_at::timestamptz,
    inv.payment_method,
    inv.external_invoice_id,
    inv.customer_notes,
    inv.tax_rate
FROM subscription_data sd
JOIN (
    VALUES 
        -- TechCorp invoices (Professional plan)
        ('techcorp-prod', 'INV-TECH-2024-001', 'paid', 'subscription', 9900, 891, 990, 9801, NOW() - INTERVAL '2 months', NOW() - INTERVAL '1 month', NOW() - INTERVAL '1 month' + INTERVAL '15 days', NOW() - INTERVAL '2 months', NOW() - INTERVAL '1 month' + INTERVAL '3 days', 'credit_card', 'stripe_in_1234567', 'Monthly subscription payment', 0.09),
        ('techcorp-prod', 'INV-TECH-2024-002', 'paid', 'subscription', 9900, 891, 0, 10791, NOW() - INTERVAL '1 month', NOW(), NOW() + INTERVAL '15 days', NOW() - INTERVAL '1 month', NOW() - INTERVAL '2 days', 'credit_card', 'stripe_in_2345678', 'Monthly subscription payment', 0.09),
        ('techcorp-staging', 'INV-TECH-STG-2024-001', 'paid', 'subscription', 2900, 261, 0, 3161, NOW() - INTERVAL '1 month', NOW(), NOW() + INTERVAL '15 days', NOW() - INTERVAL '1 month', NOW() - INTERVAL '5 days', 'credit_card', 'stripe_in_3456789', 'Staging environment subscription', 0.09),
        
        -- StartupFlex invoices (Starter plan - annual billing)
        ('startupflex-main', 'INV-SF-2024-001', 'paid', 'subscription', 31000, 2790, 4650, 29140, NOW() - INTERVAL '11 months', NOW() + INTERVAL '1 month', NOW() + INTERVAL '1 month' + INTERVAL '15 days', NOW() - INTERVAL '11 months', NOW() - INTERVAL '10 months' + INTERVAL '5 days', 'credit_card', 'stripe_in_4567890', 'Annual subscription with 15% discount', 0.09),
        
        -- AI Innovate invoices (Professional plan - EUR)
        ('ai-innovate-prod', 'INV-AI-2024-001', 'paid', 'subscription', 10500, 2100, 2100, 10500, NOW() - INTERVAL '2 months', NOW() - INTERVAL '1 month', NOW() - INTERVAL '1 month' + INTERVAL '30 days', NOW() - INTERVAL '2 months', NOW() - INTERVAL '1 month' + INTERVAL '7 days', 'invoice', 'ai_inv_001', 'Monthly subscription - EU customer', 0.20),
        ('ai-innovate-prod', 'INV-AI-2024-002', 'paid', 'subscription', 10500, 2100, 525, 12075, NOW() - INTERVAL '1 month', NOW(), NOW() + INTERVAL '30 days', NOW() - INTERVAL '1 month', NOW() - INTERVAL '15 days', 'invoice', 'ai_inv_002', 'Monthly subscription - EU customer', 0.20),
        ('ai-innovate-research', 'INV-AI-RES-2024-001', 'paid', 'subscription', 10500, 2100, 525, 12075, NOW() - INTERVAL '1 month', NOW(), NOW() + INTERVAL '30 days', NOW() - INTERVAL '1 month', NOW() - INTERVAL '12 days', 'invoice', 'ai_res_001', 'Research environment subscription', 0.20),
        
        -- Enterprise Solutions invoices (Enterprise plan)
        ('enterprise-us-prod', 'INV-ENT-US-2024-001', 'paid', 'subscription', 319000, 28710, 79750, 267960, NOW() - INTERVAL '11 months', NOW() + INTERVAL '1 month', NOW() + INTERVAL '1 month' + INTERVAL '30 days', NOW() - INTERVAL '11 months', NOW() - INTERVAL '10 months' + INTERVAL '15 days', 'invoice', 'ent_us_001', 'Annual contract with 25% discount', 0.09),
        ('enterprise-eu-prod', 'INV-ENT-EU-2024-001', 'paid', 'subscription', 319000, 63800, 79750, 303050, NOW() - INTERVAL '17 months', NOW() - INTERVAL '5 months', NOW() - INTERVAL '5 months' + INTERVAL '30 days', NOW() - INTERVAL '17 months', NOW() - INTERVAL '16 months' + INTERVAL '20 days', 'invoice', 'ent_eu_001', 'Annual contract with EU compliance', 0.20),
        
        -- Global Corp invoices (Custom plan)
        ('globalcorp-eu-prod', 'INV-GC-EU-2024-001', 'paid', 'subscription', 1500000, 300000, 0, 1800000, NOW() - INTERVAL '2 years 11 months', NOW() - INTERVAL '1 year 11 months', NOW() - INTERVAL '1 year 11 months' + INTERVAL '30 days', NOW() - INTERVAL '2 years 11 months', NOW() - INTERVAL '2 years 10 months' + INTERVAL '10 days', 'invoice', 'gc_eu_001', 'Custom enterprise plan - EU operations', 0.20),
        ('globalcorp-us-prod', 'INV-GC-US-2024-001', 'paid', 'subscription', 1200000, 108000, 0, 1308000, NOW() - INTERVAL '2 years 11 months', NOW() - INTERVAL '1 year 11 months', NOW() - INTERVAL '1 year 11 months' + INTERVAL '30 days', NOW() - INTERVAL '2 years 11 months', NOW() - INTERVAL '2 years 10 months' + INTERVAL '15 days', 'invoice', 'gc_us_001', 'Custom enterprise plan - US operations', 0.09)
) AS inv(tenant_slug, invoice_number, status, invoice_type, subtotal_cents, tax_cents, discount_cents, total_cents, period_start, period_end, due_at, issued_at, paid_at, payment_method, external_invoice_id, customer_notes, tax_rate) ON sd.tenant_slug = inv.tenant_slug
ON CONFLICT (invoice_number) DO UPDATE SET
    status = EXCLUDED.status,
    paid_at = EXCLUDED.paid_at;

-- ============================================================================
-- INVOICE LINE ITEMS: Detailed billing line items
-- ============================================================================

WITH invoice_data AS (
    SELECT 
        i.id as invoice_id,
        i.invoice_number,
        i.subtotal_cents,
        t.slug as tenant_slug
    FROM admin.invoices i
    JOIN admin.tenants t ON i.tenant_id = t.id
)
INSERT INTO admin.invoice_line_items (
    invoice_id, description, quantity, unit_price_cents, total_cents,
    item_type, tax_amount_cents, period_start, period_end, metadata
)
SELECT 
    id.invoice_id,
    li.description,
    li.quantity,
    li.unit_price_cents,
    li.total_cents,
    li.item_type::admin.line_item_type,
    li.tax_amount_cents,
    li.period_start::date,
    li.period_end::date,
    li.metadata::jsonb
FROM invoice_data id
JOIN (
    VALUES 
        -- TechCorp line items
        ('INV-TECH-2024-001', 'Professional Plan - Monthly Subscription', 1, 9900, 9900, 'subscription', 891, NOW() - INTERVAL '2 months', NOW() - INTERVAL '1 month', '{"plan_code": "professional", "billing_cycle": "monthly"}'),
        ('INV-TECH-2024-001', 'Additional Storage (5GB)', 5, 200, 1000, 'addon', 90, NOW() - INTERVAL '2 months', NOW() - INTERVAL '1 month', '{"usage_type": "storage", "unit": "GB"}'),
        ('INV-TECH-2024-002', 'Professional Plan - Monthly Subscription', 1, 9900, 9900, 'subscription', 891, NOW() - INTERVAL '1 month', NOW(), '{"plan_code": "professional", "billing_cycle": "monthly"}'),
        ('INV-TECH-2024-002', 'Additional API Calls (50K)', 1, 2500, 2500, 'usage', 225, NOW() - INTERVAL '1 month', NOW(), '{"usage_type": "api_calls", "unit": "50K_calls"}'),
        ('INV-TECH-STG-2024-001', 'Starter Plan - Monthly Subscription (Staging)', 1, 2900, 2900, 'subscription', 261, NOW() - INTERVAL '1 month', NOW(), '{"plan_code": "starter", "environment": "staging"}'),
        
        -- StartupFlex line items
        ('INV-SF-2024-001', 'Starter Plan - Annual Subscription (15% Discount)', 12, 2900, 34800, 'subscription', 2790, NOW() - INTERVAL '11 months', NOW() + INTERVAL '1 month', '{"plan_code": "starter", "billing_cycle": "annual", "startup_discount": true}'),
        
        -- AI Innovate line items
        ('INV-AI-2024-001', 'Professional Plan - Annual Subscription (20% Discount)', 12, 10500, 105000, 'subscription', 16800, NOW() - INTERVAL '2 months', NOW() + INTERVAL '10 months', '{"plan_code": "professional", "billing_cycle": "annual", "eu_customer": true}'),
        ('INV-AI-2024-001', 'GPU Compute Hours (100hrs)', 100, 250, 25000, 'usage', 4000, NOW() - INTERVAL '2 months', NOW() - INTERVAL '1 month', '{"usage_type": "gpu_compute", "unit": "hours"}'),
        ('INV-AI-2024-002', 'Professional Plan - Monthly Subscription', 1, 10500, 10500, 'subscription', 2100, NOW() - INTERVAL '1 month', NOW(), '{"plan_code": "professional", "billing_cycle": "monthly"}'),
        ('INV-AI-2024-002', 'Additional Storage (20GB)', 20, 150, 3000, 'addon', 600, NOW() - INTERVAL '1 month', NOW(), '{"usage_type": "storage", "unit": "GB"}'),
        ('INV-AI-RES-2024-001', 'Professional Plan - Research Discount', 1, 10500, 10500, 'subscription', 2100, NOW() - INTERVAL '1 month', NOW(), '{"plan_code": "professional", "research_discount": true}'),
        
        -- Enterprise Solutions line items
        ('INV-ENT-US-2024-001', 'Enterprise Plan - Annual Contract (25% Discount)', 12, 29900, 319000, 'subscription', 22425, NOW() - INTERVAL '11 months', NOW() + INTERVAL '1 month', '{"plan_code": "enterprise", "enterprise_discount": 25}'),
        ('INV-ENT-US-2024-001', 'Dedicated Support Package', 12, 5000, 60000, 'support', 4500, NOW() - INTERVAL '11 months', NOW() + INTERVAL '1 month', '{"support_level": "dedicated", "sla": "99.9%"}'),
        ('INV-ENT-US-2024-001', 'Additional Integrations (10)', 10, 2500, 25000, 'addon', 2250, NOW() - INTERVAL '11 months', NOW() + INTERVAL '1 month', '{"usage_type": "integrations", "unit": "integration"}'),
        ('INV-ENT-EU-2024-001', 'Enterprise Plan - Annual Contract (25% Discount)', 12, 29900, 319000, 'subscription', 47840, NOW() - INTERVAL '17 months', NOW() - INTERVAL '5 months', '{"plan_code": "enterprise", "enterprise_discount": 25, "eu_compliance": true}'),
        ('INV-ENT-EU-2024-001', 'GDPR Compliance Premium', 12, 7500, 90000, 'compliance', 14400, NOW() - INTERVAL '17 months', NOW() - INTERVAL '5 months', '{"compliance_type": "gdpr", "data_residency": "eu"}'),
        ('INV-ENT-EU-2024-001', 'Dedicated Support Package (EU)', 12, 6000, 72000, 'support', 11520, NOW() - INTERVAL '17 months', NOW() - INTERVAL '5 months', '{"support_level": "dedicated", "region": "eu"}'),
        
        -- Global Corp line items
        ('INV-GC-EU-2024-001', 'Custom Enterprise Plan - EU Operations', 12, 100000, 1200000, 'subscription', 240000, NOW() - INTERVAL '2 years 11 months', NOW() - INTERVAL '1 year 11 months', '{"plan_code": "custom", "custom_contract": true}'),
        ('INV-GC-EU-2024-001', 'Dedicated Infrastructure Package', 12, 20000, 240000, 'infrastructure', 48000, NOW() - INTERVAL '2 years 11 months', NOW() - INTERVAL '1 year 11 months', '{"infrastructure_type": "dedicated", "region": "eu"}'),
        ('INV-GC-EU-2024-001', 'Premium Support & SLA', 12, 15000, 180000, 'support', 36000, NOW() - INTERVAL '2 years 11 months', NOW() - INTERVAL '1 year 11 months', '{"support_level": "premium", "sla": "99.99%"}'),
        ('INV-GC-US-2024-001', 'Custom Enterprise Plan - US Operations', 12, 80000, 960000, 'subscription', 86400, NOW() - INTERVAL '2 years 11 months', NOW() - INTERVAL '1 year 11 months', '{"plan_code": "custom", "custom_contract": true, "region": "us"}'),
        ('INV-GC-US-2024-001', 'Dedicated Infrastructure Package', 12, 15000, 180000, 'infrastructure', 16200, NOW() - INTERVAL '2 years 11 months', NOW() - INTERVAL '1 year 11 months', '{"infrastructure_type": "dedicated", "region": "us"}'),
        ('INV-GC-US-2024-001', 'Premium Support & SLA', 12, 10000, 120000, 'support', 10800, NOW() - INTERVAL '2 years 11 months', NOW() - INTERVAL '1 year 11 months', '{"support_level": "premium", "sla": "99.95%"}')
) AS li(invoice_number, description, quantity, unit_price_cents, total_cents, item_type, tax_amount_cents, period_start, period_end, metadata) ON id.invoice_number = li.invoice_number;

-- ============================================================================
-- PAYMENT TRANSACTIONS: Payment processing records
-- ============================================================================

WITH invoice_data AS (
    SELECT 
        i.id as invoice_id,
        i.invoice_number,
        i.total_cents,
        i.tenant_id
    FROM admin.invoices i
)
INSERT INTO admin.payment_transactions (
    tenant_id, invoice_id, transaction_id, external_reference, transaction_type,
    amount_cents, currency, payment_method_type, status, processor,
    processor_fee_cents, net_amount_cents, processed_at
)
SELECT 
    id.tenant_id,
    id.invoice_id,
    pt.transaction_id,
    pt.external_reference,
    pt.transaction_type,
    pt.amount_cents,
    pt.currency,
    pt.payment_method_type,
    pt.status,
    pt.processor,
    pt.processor_fee_cents,
    pt.net_amount_cents,
    pt.processed_at::timestamptz
FROM invoice_data id
JOIN (
    VALUES 
        -- TechCorp payment transactions
        ('INV-TECH-2024-001', 'txn_stripe_001', 'pi_1234567890', 'payment', 9801, 'USD', 'credit_card', 'succeeded', 'stripe', 314, 9487, NOW() - INTERVAL '1 month' + INTERVAL '3 days'),
        ('INV-TECH-2024-002', 'txn_stripe_002', 'pi_2345678901', 'payment', 10791, 'USD', 'credit_card', 'succeeded', 'stripe', 344, 10447, NOW() - INTERVAL '2 days'),
        ('INV-TECH-STG-2024-001', 'txn_stripe_003', 'pi_3456789012', 'payment', 3161, 'USD', 'credit_card', 'succeeded', 'stripe', 122, 3039, NOW() - INTERVAL '5 days'),
        
        -- StartupFlex payment transactions
        ('INV-SF-2024-001', 'txn_stripe_004', 'pi_4567890123', 'payment', 29140, 'USD', 'credit_card', 'succeeded', 'stripe', 875, 28265, NOW() - INTERVAL '10 months' + INTERVAL '5 days'),
        
        -- AI Innovate payment transactions (EUR)
        ('INV-AI-2024-001', 'txn_bank_001', 'sepa_1234567', 'payment', 10500, 'EUR', 'sepa_debit', 'succeeded', 'stripe', 0, 10500, NOW() - INTERVAL '1 month' + INTERVAL '7 days'),
        ('INV-AI-2024-002', 'txn_bank_002', 'sepa_2345678', 'payment', 12075, 'EUR', 'sepa_debit', 'succeeded', 'stripe', 0, 12075, NOW() - INTERVAL '15 days'),
        ('INV-AI-RES-2024-001', 'txn_bank_003', 'sepa_3456789', 'payment', 12075, 'EUR', 'sepa_debit', 'succeeded', 'stripe', 0, 12075, NOW() - INTERVAL '12 days'),
        
        -- Enterprise Solutions payment transactions
        ('INV-ENT-US-2024-001', 'txn_ach_001', 'ach_1234567', 'payment', 267960, 'USD', 'ach', 'succeeded', 'stripe', 1256, 266704, NOW() - INTERVAL '10 months' + INTERVAL '15 days'),
        ('INV-ENT-EU-2024-001', 'txn_wire_001', 'wire_1234567', 'payment', 303050, 'EUR', 'wire_transfer', 'succeeded', 'bank', 2500, 300550, NOW() - INTERVAL '16 months' + INTERVAL '20 days'),
        
        -- Global Corp payment transactions
        ('INV-GC-EU-2024-001', 'txn_wire_002', 'wire_2345678', 'payment', 1800000, 'EUR', 'wire_transfer', 'succeeded', 'bank', 4500, 1795500, NOW() - INTERVAL '2 years 10 months' + INTERVAL '10 days'),
        ('INV-GC-US-2024-001', 'txn_wire_003', 'wire_3456789', 'payment', 1308000, 'USD', 'wire_transfer', 'succeeded', 'bank', 3500, 1304500, NOW() - INTERVAL '2 years 10 months' + INTERVAL '15 days')
) AS pt(invoice_number, transaction_id, external_reference, transaction_type, amount_cents, currency, payment_method_type, status, processor, processor_fee_cents, net_amount_cents, processed_at) ON id.invoice_number = pt.invoice_number
ON CONFLICT (transaction_id) DO UPDATE SET
    status = EXCLUDED.status,
    processed_at = EXCLUDED.processed_at;

-- ============================================================================
-- SYSTEM ALERTS: Platform monitoring and alerting
-- ============================================================================

WITH alert_data AS (
    SELECT 
        t.id as tenant_id,
        t.slug as tenant_slug,
        t.region_id
    FROM admin.tenants t
),
alert_users AS (
    SELECT 
        u.id as user_id,
        u.email
    FROM admin.users u 
    WHERE u.email IN ('hans.security@globalcorp.com', 'michael.devops@enterprisesol.com', 
                      'jennifer.architect@enterprisesol.com', 'manager@techcorp.com')
)
INSERT INTO admin.system_alerts (
    alert_name, alert_type, severity, source_type, source_id, title, description,
    region_id, tenant_id, status, acknowledged_by, resolved_by,
    first_occurrence_at, escalated_at, resolved_at, metadata
)
SELECT 
    sa.alert_name,
    sa.alert_type,
    sa.severity::admin.risk_level,
    sa.source_type,
    sa.source_id,
    sa.title,
    sa.description,
    ad.region_id,
    ad.tenant_id,
    sa.status,
    au_ack.user_id,
    au_res.user_id,
    sa.first_occurrence_at::timestamptz,
    sa.escalated_at::timestamptz,
    sa.resolved_at::timestamptz,
    sa.metadata::jsonb
FROM alert_data ad
LEFT JOIN alert_users au_ack ON au_ack.email = sa.acknowledged_email
LEFT JOIN alert_users au_res ON au_res.email = sa.resolved_email
JOIN (
    VALUES 
        -- Security alerts
        ('techcorp-prod', 'security_failed_login', 'security', 'high', 'auth_system', 'auth_001', 'Multiple Failed Login Attempts', 'Detected 15 failed login attempts from IP 192.168.1.100 in 5 minutes', 'investigating', 'hans.security@globalcorp.com', NULL, NOW() - INTERVAL '2 hours', NOW() - INTERVAL '1 hour', NULL, '{"ip_address": "192.168.1.100", "attempt_count": 15, "user_agent": "Mozilla/5.0"}'),
        ('enterprise-us-prod', 'security_suspicious_api', 'security', 'medium', 'api_gateway', 'api_001', 'Suspicious API Activity', 'Unusual API usage pattern detected for user michael.devops@enterprisesol.com', 'acknowledged', 'michael.devops@enterprisesol.com', NULL, NOW() - INTERVAL '6 hours', NULL, NULL, '{"user_id": "user_12345", "unusual_endpoints": ["/admin/users", "/admin/billing"]}'),
        
        -- Infrastructure alerts
        ('globalcorp-eu-prod', 'infrastructure_disk_space', 'infrastructure', 'medium', 'database_monitoring', 'db_001', 'Database Disk Usage High', 'Database disk usage at 85%, recommend cleanup or expansion', 'resolved', 'hans.security@globalcorp.com', 'hans.security@globalcorp.com', NOW() - INTERVAL '12 hours', NULL, NOW() - INTERVAL '6 hours', '{"disk_usage": "85%", "available_space": "2.5GB", "database": "globalcorp_manufacturing"}'),
        ('globalcorp-us-prod', 'infrastructure_memory', 'infrastructure', 'high', 'database_monitoring', 'db_002', 'High Memory Usage', 'Database memory usage at 95%, performance impact detected', 'investigating', 'michael.devops@enterprisesol.com', NULL, NOW() - INTERVAL '8 hours', NOW() - INTERVAL '7 hours', NULL, '{"memory_usage": "95%", "affected_queries": ["SELECT * FROM large_table"], "database": "globalcorp_us"}'),
        
        -- Performance alerts 
        ('techcorp-prod', 'performance_response_time', 'performance', 'medium', 'application_monitoring', 'app_001', 'API Response Time Degraded', 'Average API response time increased to 2.5s (normal: 0.5s)', 'resolved', 'manager@techcorp.com', 'manager@techcorp.com', NOW() - INTERVAL '3 days', NULL, NOW() - INTERVAL '2 days', '{"avg_response_time": "2.5s", "normal_response_time": "0.5s", "affected_endpoints": ["/api/v1/users"]}'),
        ('enterprise-eu-prod', 'performance_queue_backup', 'performance', 'high', 'queue_system', 'queue_001', 'Job Queue Backup', 'Background job queue has 500+ pending jobs, processing severely delayed', 'investigating', 'jennifer.architect@enterprisesol.com', NULL, NOW() - INTERVAL '1 hour', NOW() - INTERVAL '30 minutes', NULL, '{"pending_jobs": 547, "avg_wait_time": "45 minutes", "queue_type": "background_processing"}'),
        
        -- Billing alerts 
        ('techcorp-prod', 'billing_usage_threshold', 'billing', 'low', 'usage_monitoring', 'usage_001', 'API Usage Approaching Limit', 'Current API usage at 85% of monthly quota (21,250/25,000)', 'resolved', NULL, 'manager@techcorp.com', NOW() - INTERVAL '3 days', NULL, NOW() - INTERVAL '2 days', '{"current_usage": 21250, "monthly_quota": 25000, "percentage": 85}'),
        ('enterprise-eu-prod', 'billing_payment_received', 'billing', 'low', 'billing_system', 'bill_001', 'Invoice Payment Received', 'Annual subscription payment of €303,050 processed successfully', 'resolved', NULL, NULL, NOW() - INTERVAL '15 days', NULL, NOW() - INTERVAL '15 days', '{"invoice_number": "INV-ENT-EU-2024-001", "amount_cents": 303050, "currency": "EUR"}')
) AS sa(tenant_slug, alert_name, alert_type, severity, source_type, source_id, title, description, status, acknowledged_email, resolved_email, first_occurrence_at, escalated_at, resolved_at, metadata) ON ad.tenant_slug = sa.tenant_slug
ON CONFLICT (alert_name, tenant_id) DO UPDATE SET
    status = EXCLUDED.status,
    resolved_by = EXCLUDED.resolved_by,
    resolved_at = EXCLUDED.resolved_at;

-- ============================================================================
-- API RATE LIMITS: Custom rate limiting rules
-- ============================================================================

WITH admin_user AS (
    SELECT id as admin_id FROM admin.users WHERE email = 'admin@neomultitenant.com' LIMIT 1
)
INSERT INTO admin.api_rate_limits (
    limit_name, limit_type, requests_per_window, window_size_seconds,
    burst_allowance, applies_to_users, description, created_by
)
SELECT 
    rl.limit_name,
    rl.limit_type,
    rl.requests_per_window,
    rl.window_size_seconds,
    rl.burst_allowance,
    rl.applies_to_users,
    rl.description,
    au.admin_id
FROM admin_user au
CROSS JOIN (
    VALUES 
        -- Executive/Admin users (higher limits)
        ('cto_enterprise_limit', 'user', 200, 60, 300, true, 'Higher limit for CTO-level access'),
        ('director_global_limit', 'user', 150, 60, 250, true, 'Higher limit for IT Director access'),
        ('manager_techcorp_limit', 'user', 120, 60, 200, true, 'Manager-level API access'),
        
        -- Developer users (moderate limits)
        ('developer_standard_limit', 'user', 100, 60, 150, true, 'Standard developer API access'),
        ('architect_limit', 'user', 150, 60, 200, true, 'Solutions architect access'),
        
        -- Tenant-specific limits
        ('enterprise_tenant_limit', 'tenant', 500, 60, 750, false, 'Higher limits for enterprise tenants'),
        ('startup_tenant_limit', 'tenant', 200, 60, 300, false, 'Moderate limits for startup tenants'),
        
        -- Global limits
        ('premium_global_limit', 'global', 2000, 60, 3000, false, 'Premium tier global rate limit'),
        ('standard_global_limit', 'global', 1000, 60, 1500, false, 'Standard tier global rate limit')
) AS rl(limit_name, limit_type, requests_per_window, window_size_seconds, burst_allowance, applies_to_users, description)
ON CONFLICT (limit_name) DO NOTHING;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Summary of billing data
SELECT 
    'Billing Summary' as report_type,
    COUNT(i.id) as total_invoices,
    SUM(i.total_cents) / 100.0 as total_billed_dollars,
    COUNT(CASE WHEN i.status = 'paid' THEN 1 END) as paid_invoices,
    COUNT(pt.id) as total_transactions
FROM admin.invoices i
LEFT JOIN admin.payment_transactions pt ON i.id = pt.invoice_id;

-- System alerts summary
SELECT 
    sa.severity,
    sa.alert_type,
    COUNT(*) as alert_count,
    COUNT(CASE WHEN sa.status = 'resolved' THEN 1 END) as resolved_count,
    COUNT(CASE WHEN sa.status IN ('open', 'investigating') THEN 1 END) as active_count
FROM admin.system_alerts sa
GROUP BY sa.severity, sa.alert_type
ORDER BY sa.severity, sa.alert_type;

-- Rate limits summary
SELECT 
    arl.limit_type,
    COUNT(*) as limit_count,
    AVG(arl.requests_per_window) as avg_requests_per_window,
    MAX(arl.requests_per_window) as max_requests_per_window
FROM admin.api_rate_limits arl
WHERE arl.is_active = true
GROUP BY arl.limit_type
ORDER BY arl.limit_type;

-- Success message
SELECT 'Billing, transactions, and monitoring data seeded successfully' as seed_status;