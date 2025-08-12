-- NeoMultiTenant - Seed Data: Regions and Database Connections
-- This seed file populates the initial regions and database connections
-- Run with: ./deploy.sh --seed

-- ============================================================================
-- REGIONS: Insert deployment regions
-- ============================================================================

INSERT INTO admin.regions (
    code, name, display_name, country_code, continent, city, timezone,
    data_residency_compliant, gdpr_region, compliance_certifications,
    is_active, accepts_new_tenants, provider, provider_region,
    primary_endpoint, internal_network
) VALUES 
(
    'us-east-1',
    'US East (Virginia)',
    'United States East',
    'US',
    'North America',
    'Virginia',
    'America/New_York',
    true,
    false,
    ARRAY['SOC2', 'ISO27001', 'HIPAA'],
    true,
    true,
    'Docker',
    'us-east-1',
    'neo-postgres-us-east:5432',
    '172.19.0.0/16'
),
(
    'eu-west-1',
    'EU West (Ireland)',
    'European Union West',
    'IE',
    'Europe',
    'Dublin',
    'Europe/Dublin',
    true,
    true,
    ARRAY['GDPR', 'SOC2', 'ISO27001'],
    true,
    true,
    'Docker',
    'eu-west-1',
    'neo-postgres-eu-west:5432',
    '172.19.0.0/16'
)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    display_name = EXCLUDED.display_name,
    gdpr_region = EXCLUDED.gdpr_region,
    compliance_certifications = EXCLUDED.compliance_certifications,
    updated_at = NOW();

-- ============================================================================
-- DATABASE CONNECTIONS: Insert all database connection info
-- ============================================================================

-- Insert database connections for each region and database
WITH region_ids AS (
    SELECT id, code FROM admin.regions WHERE code IN ('us-east-1', 'eu-west-1')
)
INSERT INTO admin.database_connections (
    region_id, connection_name, connection_type, host, port, database_name,
    ssl_mode, username, encrypted_password, pool_min_size, pool_max_size, pool_timeout_seconds,
    is_active, is_healthy, last_health_check
)
SELECT 
    r.id,
    conn.connection_name,
    conn.connection_type::admin.connection_type,
    conn.host,
    conn.port,
    conn.database_name,
    'disable', -- Development SSL mode
    'postgres',
    'gAAAAABol4ATGxSZIbqI00K0du_r2yesIsV_AUgGyZ5oeuI6jhs-6suJ07tkS8HuzEI0fT366Cllhozg5uGOSFSUQ3hI3kY2GA==', -- Pre-encrypted 'postgres' password
    5,
    20,
    30,
    true,
    true,
    NOW()
FROM region_ids r
CROSS JOIN (
    VALUES 
        -- US East Region databases
        ('us-east-1', 'neofast-admin-primary', 'primary', 'neo-postgres-us-east', 5432, 'neofast_admin'),
        ('us-east-1', 'neofast-shared-us-primary', 'primary', 'neo-postgres-us-east', 5432, 'neofast_shared_us'),
        ('us-east-1', 'neofast-analytics-us', 'analytics', 'neo-postgres-us-east', 5432, 'neofast_analytics_us'),
        
        -- EU West Region databases  
        ('eu-west-1', 'neofast-shared-eu-primary', 'primary', 'neo-postgres-eu-west', 5432, 'neofast_shared_eu'),
        ('eu-west-1', 'neofast-analytics-eu', 'analytics', 'neo-postgres-eu-west', 5432, 'neofast_analytics_eu')
) AS conn(region_code, connection_name, connection_type, host, port, database_name)
WHERE r.code = conn.region_code
ON CONFLICT (connection_name) DO UPDATE SET
    host = EXCLUDED.host,
    port = EXCLUDED.port,
    is_healthy = EXCLUDED.is_healthy,
    last_health_check = EXCLUDED.last_health_check,
    updated_at = NOW();

-- ============================================================================
-- VERIFICATION: Show populated data
-- ============================================================================

-- Show regions
SELECT 
    code,
    name,
    gdpr_region,
    compliance_certifications,
    is_active
FROM admin.regions 
WHERE code IN ('us-east-1', 'eu-west-1')
ORDER BY code;

-- Show database connections
SELECT 
    r.code as region_code,
    dc.connection_name,
    dc.connection_type,
    dc.host,
    dc.port,
    dc.database_name,
    dc.is_active,
    dc.is_healthy
FROM admin.database_connections dc
JOIN admin.regions r ON dc.region_id = r.id
WHERE r.code IN ('us-east-1', 'eu-west-1')
ORDER BY r.code, dc.connection_type, dc.connection_name;