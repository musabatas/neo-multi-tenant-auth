-- NeoMultiTenant - Seed Data: Organizations and Tenants
-- This seed file populates realistic organizations and tenants
-- Run with: ./deploy.sh --seed

-- ============================================================================
-- ADDITIONAL USERS: Create organization contacts and tenant admins
-- ============================================================================

-- First, let's create additional users to serve as organization contacts and tenant admins
INSERT INTO admin.users (
    email, username, first_name, last_name, display_name, status,
    external_auth_provider, external_user_id, job_title, company,
    timezone, locale, default_role_level, is_system_user, is_onboarding_completed,
    profile_completion_percentage, last_login_at, last_activity_at,
    metadata
) VALUES 
-- Organization Contacts
(
    'ceo@techcorp.com',
    'john_doe_ceo',
    'John',
    'Doe',
    'John Doe (CEO)',
    'active',
    'keycloak',
    'org_contact_001',
    'Chief Executive Officer',
    'TechCorp Solutions',
    'America/New_York',
    'en-US',
    'tenant',
    false,
    true,
    100,
    NOW() - INTERVAL '2 hours',
    NOW() - INTERVAL '1 hour',
    '{"organization_role": "primary_contact", "department": "executive"}'::jsonb
),
(
    'admin@startupflex.io',
    'sarah_admin',
    'Sarah',
    'Johnson',
    'Sarah Johnson (Admin)',
    'active',
    'keycloak',
    'org_contact_002',
    'Operations Manager',
    'StartupFlex',
    'America/Los_Angeles',
    'en-US',
    'tenant',
    false,
    true,
    95,
    NOW() - INTERVAL '6 hours',
    NOW() - INTERVAL '3 hours',
    '{"organization_role": "admin", "department": "operations"}'::jsonb
),
(
    'founder@aiinnovate.eu',
    'marie_founder',
    'Marie',
    'Dubois',
    'Marie Dubois (Founder)',
    'active',
    'keycloak',
    'org_contact_003',
    'Founder & CTO',
    'AI Innovate Labs',
    'Europe/Paris',
    'fr-FR',
    'tenant',
    false,
    true,
    100,
    NOW() - INTERVAL '4 hours',
    NOW() - INTERVAL '2 hours',
    '{"organization_role": "founder", "department": "engineering"}'::jsonb
),
(
    'cto@enterprisesol.com',
    'david_cto',
    'David',
    'Smith',
    'David Smith (CTO)',
    'active',
    'keycloak',
    'org_contact_004',
    'Chief Technology Officer',
    'Enterprise Solutions Inc',
    'America/Chicago',
    'en-US',
    'tenant',
    false,
    true,
    100,
    NOW() - INTERVAL '1 day',
    NOW() - INTERVAL '8 hours',
    '{"organization_role": "technical_lead", "department": "engineering"}'::jsonb
),
(
    'director@globalcorp.com',
    'anna_director',
    'Anna',
    'Mueller',
    'Anna Mueller (Director)',
    'active',
    'keycloak',
    'org_contact_005',
    'IT Director',
    'Global Corp International',
    'Europe/Berlin',
    'de-DE',
    'tenant',
    false,
    true,
    100,
    NOW() - INTERVAL '12 hours',
    NOW() - INTERVAL '4 hours',
    '{"organization_role": "it_director", "department": "technology"}'::jsonb
),
-- Additional Tenant Users
(
    'manager@techcorp.com',
    'lisa_manager',
    'Lisa',
    'Chen',
    'Lisa Chen (Manager)',
    'active',
    'keycloak',
    'tenant_user_001',
    'Project Manager',
    'TechCorp Solutions',
    'America/New_York',
    'en-US',
    'member',
    false,
    true,
    90,
    NOW() - INTERVAL '3 hours',
    NOW() - INTERVAL '1 hour',
    '{"tenant_role": "manager", "department": "projects"}'::jsonb
),
(
    'dev@startupflex.io',
    'alex_dev',
    'Alex',
    'Rodriguez',
    'Alex Rodriguez (Dev)',
    'active',
    'keycloak',
    'tenant_user_002',
    'Senior Developer',
    'StartupFlex',
    'America/Los_Angeles',
    'en-US',
    'member',
    false,
    true,
    85,
    NOW() - INTERVAL '5 hours',
    NOW() - INTERVAL '2 hours',
    '{"tenant_role": "developer", "department": "engineering"}'::jsonb
)
ON CONFLICT (email) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    job_title = EXCLUDED.job_title,
    company = EXCLUDED.company,
    last_activity_at = EXCLUDED.last_activity_at,
    updated_at = NOW();

-- ============================================================================
-- ORGANIZATIONS: Create diverse organizations
-- ============================================================================

-- Insert organizations with different characteristics
WITH contact_users AS (
    SELECT id, email FROM admin.users 
    WHERE email IN ('ceo@techcorp.com', 'admin@startupflex.io', 'founder@aiinnovate.eu', 
                    'cto@enterprisesol.com', 'director@globalcorp.com')
)
INSERT INTO admin.organizations (
    name, legal_name, slug, website_url, industry, business_type, company_size,
    country_code, city, state_province, tax_id,
    primary_contact_id, is_active, verified_at
)
SELECT 
    org.name,
    org.legal_name,
    org.slug,
    org.website_url,
    org.industry,
    org.business_type,
    org.company_size,
    org.country_code,
    org.city,
    org.state_province,
    org.tax_id,
    cu.id,
    org.is_active,
    org.verified_at::timestamptz
FROM contact_users cu
JOIN (
    VALUES 
        -- Tech Startup
        ('TechCorp Solutions', 'TechCorp Solutions LLC', 'techcorp-solutions', 'https://www.techcorp.com', 'Technology', 'corporation', 'medium', 'US', 'San Francisco', 'California', 'US-123456789', 'ceo@techcorp.com', true, NOW() - INTERVAL '6 months'),
        
        -- Small Startup
        ('StartupFlex', 'StartupFlex Inc.', 'startupflex', 'https://startupflex.io', 'SaaS', 'corporation', 'small', 'US', 'Austin', 'Texas', 'US-987654321', 'admin@startupflex.io', true, NOW() - INTERVAL '3 months'),
        
        -- EU AI Company
        ('AI Innovate Labs', 'AI Innovate Labs SAS', 'ai-innovate-labs', 'https://aiinnovate.eu', 'Artificial Intelligence', 'corporation', 'medium', 'FR', 'Paris', 'Île-de-France', 'FR-789123456', 'founder@aiinnovate.eu', true, NOW() - INTERVAL '8 months'),
        
        -- Large Enterprise
        ('Enterprise Solutions Inc', 'Enterprise Solutions Incorporated', 'enterprise-solutions', 'https://www.enterprisesol.com', 'Enterprise Software', 'corporation', 'large', 'US', 'New York', 'New York', 'US-456789123', 'cto@enterprisesol.com', true, NOW() - INTERVAL '2 years'),
        
        -- Global Corporation
        ('Global Corp International', 'Global Corp International AG', 'global-corp-intl', 'https://www.globalcorp.com', 'Manufacturing', 'corporation', 'enterprise', 'DE', 'Munich', 'Bavaria', 'DE-321654987', 'director@globalcorp.com', true, NOW() - INTERVAL '3 years')
) AS org(name, legal_name, slug, website_url, industry, business_type, company_size, country_code, city, state_province, tax_id, contact_email, is_active, verified_at)
ON cu.email = org.contact_email
ON CONFLICT (slug) DO UPDATE SET
    name = EXCLUDED.name,
    legal_name = EXCLUDED.legal_name,
    website_url = EXCLUDED.website_url,
    industry = EXCLUDED.industry,
    updated_at = NOW();

-- ============================================================================
-- TENANTS: Create multiple tenants per organization
-- ============================================================================

-- Insert tenants for each organization
WITH org_data AS (
    SELECT 
        o.id as org_id, 
        o.slug as org_slug, 
        o.name as org_name,
        o.company_size as org_size
    FROM admin.organizations o
    WHERE o.slug IN ('techcorp-solutions', 'startupflex', 'ai-innovate-labs', 'enterprise-solutions', 'global-corp-intl')
),
region_data AS (
    SELECT id as region_id, code as region_code FROM admin.regions
    WHERE code IN ('us-east-1', 'eu-west-1')
),
db_connections AS (
    SELECT 
        dc.id as connection_id, 
        dc.connection_name, 
        r.code as region_code,
        dc.connection_type
    FROM admin.database_connections dc
    JOIN admin.regions r ON dc.region_id = r.id
    WHERE dc.connection_type = 'primary' 
      AND dc.connection_name LIKE '%shared%'
)
INSERT INTO admin.tenants (
    organization_id, slug, name, description, schema_name, database_name,
    deployment_type, environment, region_id, database_connection_id,
    external_auth_provider, external_auth_realm, external_user_id, external_auth_metadata,
    status, features_enabled, feature_overrides, provisioned_at, activated_at,
    last_activity_at, metadata
)
SELECT 
    od.org_id,
    t.slug,
    t.name,
    t.description,
    t.schema_name,
    dbc.connection_name,
    t.deployment_type::admin.deployment_type,
    t.environment::admin.environment_type,
    rd.region_id,
    dbc.connection_id,
    'keycloak',
    t.auth_realm,
    t.external_user_id,
    t.auth_metadata::jsonb,
    t.status::admin.tenant_status,
    t.features_enabled::jsonb,
    t.feature_overrides::jsonb,
    t.provisioned_at::timestamptz,
    t.activated_at::timestamptz,
    t.last_activity_at::timestamptz,
    t.metadata::jsonb
FROM org_data od
CROSS JOIN (
    VALUES 
        -- TechCorp Tenants (US-based)
        ('techcorp-solutions', 'techcorp-prod', 'TechCorp Production', 'Production environment for TechCorp main application', 'tenant_techcorp_prod', 'techcorp-prod-realm', 'techcorp_prod_001', '{"realm_id": "techcorp-prod", "client_id": "techcorp-app"}', 'schema', 'production', 'us-east-1', 'active', '{"analytics": true, "integrations": true, "api_access": true, "white_label": true}', '{}', NOW() - INTERVAL '6 months', NOW() - INTERVAL '6 months', NOW() - INTERVAL '2 hours', '{"primary_app": true, "tier": "production"}'),
        ('techcorp-solutions', 'techcorp-staging', 'TechCorp Staging', 'Staging environment for testing and development', 'tenant_techcorp_staging', 'techcorp-staging-realm', 'techcorp_staging_001', '{"realm_id": "techcorp-staging", "client_id": "techcorp-staging-app"}', 'schema', 'staging', 'us-east-1', 'active', '{"analytics": true, "integrations": true, "api_access": true}', '{"rate_limiting": {"enabled": true, "requests_per_minute": 100}}', NOW() - INTERVAL '5 months', NOW() - INTERVAL '5 months', NOW() - INTERVAL '4 hours', '{"environment": "staging", "auto_cleanup": true}'),
        
        -- StartupFlex Tenants (US-based) 
        ('startupflex', 'startupflex-main', 'StartupFlex Main', 'Primary application for StartupFlex SaaS platform', 'tenant_startupflex_main', 'startupflex-main-realm', 'startupflex_main_001', '{"realm_id": "startupflex-main", "client_id": "startupflex-app"}', 'schema', 'production', 'us-east-1', 'active', '{"analytics": true, "integrations": false, "api_access": true}', '{}', NOW() - INTERVAL '3 months', NOW() - INTERVAL '3 months', NOW() - INTERVAL '1 hour', '{"startup_tier": true, "support_level": "standard"}'),
        
        -- AI Innovate Tenants (EU-based for GDPR compliance)
        ('ai-innovate-labs', 'ai-innovate-prod', 'AI Innovate Production', 'Production AI/ML platform for European customers', 'tenant_ai_innovate_prod', 'ai-innovate-prod-realm', 'ai_innovate_prod_001', '{"realm_id": "ai-innovate-prod", "client_id": "ai-platform"}', 'schema', 'production', 'eu-west-1', 'active', '{"analytics": true, "integrations": true, "api_access": true, "ml_features": true}', '{"data_residency": {"enabled": true, "region": "eu"}}', NOW() - INTERVAL '8 months', NOW() - INTERVAL '8 months', NOW() - INTERVAL '3 hours', '{"gdpr_compliant": true, "ml_workloads": true}'),
        ('ai-innovate-labs', 'ai-innovate-research', 'AI Research Lab', 'Research and development environment', 'tenant_ai_research', 'ai-research-realm', 'ai_research_001', '{"realm_id": "ai-research", "client_id": "research-tools"}', 'schema', 'development', 'eu-west-1', 'active', '{"analytics": true, "integrations": true, "experimental_features": true}', '{}', NOW() - INTERVAL '6 months', NOW() - INTERVAL '6 months', NOW() - INTERVAL '5 hours', '{"research_environment": true, "experimental": true}'),
        
        -- Enterprise Solutions Tenants (Multi-region)
        ('enterprise-solutions', 'enterprise-us-prod', 'Enterprise US Production', 'Primary US production environment', 'tenant_enterprise_us_prod', 'enterprise-us-prod-realm', 'enterprise_us_prod_001', '{"realm_id": "enterprise-us-prod", "client_id": "enterprise-platform"}', 'schema', 'production', 'us-east-1', 'active', '{"analytics": true, "integrations": true, "api_access": true, "enterprise_features": true, "sso": true}', '{}', NOW() - INTERVAL '2 years', NOW() - INTERVAL '2 years', NOW() - INTERVAL '1 hour', '{"enterprise_tier": true, "primary_region": "us"}'),
        ('enterprise-solutions', 'enterprise-eu-prod', 'Enterprise EU Production', 'European production environment for GDPR compliance', 'tenant_enterprise_eu_prod', 'enterprise-eu-prod-realm', 'enterprise_eu_prod_001', '{"realm_id": "enterprise-eu-prod", "client_id": "enterprise-platform-eu"}', 'schema', 'production', 'eu-west-1', 'active', '{"analytics": true, "integrations": true, "api_access": true, "enterprise_features": true, "sso": true, "gdpr_features": true}', '{"data_residency": {"enabled": true, "region": "eu"}}', NOW() - INTERVAL '18 months', NOW() - INTERVAL '18 months', NOW() - INTERVAL '30 minutes', '{"enterprise_tier": true, "gdpr_compliant": true, "region": "eu"}'),
        
        -- Global Corp Tenants (Multi-region, Multi-environment)
        ('global-corp-intl', 'globalcorp-eu-prod', 'Global Corp EU Production', 'European production system for Global Corp', 'tenant_globalcorp_eu_prod', 'globalcorp-eu-prod-realm', 'globalcorp_eu_prod_001', '{"realm_id": "globalcorp-eu-prod", "client_id": "globalcorp-platform"}', 'schema', 'production', 'eu-west-1', 'active', '{"analytics": true, "integrations": true, "api_access": true, "enterprise_features": true, "sso": true, "audit_logs": true}', '{"data_residency": {"enabled": true, "region": "eu"}, "compliance": {"iso27001": true, "gdpr": true}}', NOW() - INTERVAL '3 years', NOW() - INTERVAL '3 years', NOW() - INTERVAL '15 minutes', '{"global_tier": true, "manufacturing_features": true}'),
        ('global-corp-intl', 'globalcorp-us-prod', 'Global Corp US Production', 'US production system for Global Corp', 'tenant_globalcorp_us_prod', 'globalcorp-us-prod-realm', 'globalcorp_us_prod_001', '{"realm_id": "globalcorp-us-prod", "client_id": "globalcorp-platform-us"}', 'schema', 'production', 'us-east-1', 'active', '{"analytics": true, "integrations": true, "api_access": true, "enterprise_features": true, "sso": true, "audit_logs": true}', '{"compliance": {"soc2": true, "iso27001": true}}', NOW() - INTERVAL '3 years', NOW() - INTERVAL '3 years', NOW() - INTERVAL '45 minutes', '{"global_tier": true, "manufacturing_features": true, "region": "us"}')
) AS t(org_slug, slug, name, description, schema_name, auth_realm, external_user_id, auth_metadata, deployment_type, environment, region_code, status, features_enabled, feature_overrides, provisioned_at, activated_at, last_activity_at, metadata)
JOIN region_data rd ON rd.region_code = t.region_code  
JOIN db_connections dbc ON dbc.region_code = t.region_code
WHERE od.org_slug = t.org_slug
ON CONFLICT (slug) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    features_enabled = EXCLUDED.features_enabled,
    last_activity_at = EXCLUDED.last_activity_at,
    updated_at = NOW();

-- ============================================================================
-- VERIFICATION: Show organizations and tenants
-- ============================================================================

-- Show organizations with contact info
SELECT 
    o.name,
    o.slug,
    o.industry,
    o.company_size,
    o.is_active,
    u.display_name as primary_contact,
    o.city || ', ' || o.state_province as location
FROM admin.organizations o
JOIN admin.users u ON o.primary_contact_id = u.id
ORDER BY o.company_size DESC, o.name;

-- Show tenants with organization info
SELECT 
    o.name as organization,
    t.name as tenant,
    t.slug,
    t.environment,
    r.name as region,
    t.status,
    t.provisioned_at::date as provisioned_date,
    t.last_activity_at::date as last_active
FROM admin.tenants t
JOIN admin.organizations o ON t.organization_id = o.id
JOIN admin.regions r ON t.region_id = r.id
ORDER BY o.name, t.environment, t.name;

-- Summary statistics
SELECT 
    'Organizations' as entity_type,
    COUNT(*) as total_count,
    COUNT(CASE WHEN is_active = true THEN 1 END) as active_count
FROM admin.organizations
UNION ALL
SELECT 
    'Tenants' as entity_type,
    COUNT(*) as total_count,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_count
FROM admin.tenants;

-- Log completion
SELECT 'Organizations and tenants seeded successfully' as seed_status;
