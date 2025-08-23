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
-- North America
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
    'us-west-2',
    'US West (Oregon)',
    'United States West',
    'US',
    'North America',
    'Oregon',
    'America/Los_Angeles',
    true,
    false,
    ARRAY['SOC2', 'ISO27001', 'HIPAA'],
    true,
    true,
    'Docker',
    'us-west-2',
    'neo-postgres-us-east:5432',
    '172.19.0.0/16'
),
(
    'ca-central-1',
    'Canada Central (Toronto)',
    'Canada Central',
    'CA',
    'North America',
    'Toronto',
    'America/Toronto',
    true,
    false,
    ARRAY['SOC2', 'ISO27001', 'PIPEDA'],
    true,
    true,
    'Docker',
    'ca-central-1',
    'neo-postgres-us-east:5432',
    '172.19.0.0/16'
),
-- Europe
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
),
(
    'eu-central-1',
    'EU Central (Frankfurt)',
    'European Union Central',
    'DE',
    'Europe',
    'Frankfurt',
    'Europe/Berlin',
    true,
    true,
    ARRAY['GDPR', 'SOC2', 'ISO27001', 'BSI'],
    true,
    true,
    'Docker',
    'eu-central-1',
    'neo-postgres-eu-west:5432',
    '172.19.0.0/16'
),
(
    'eu-north-1',
    'EU North (Stockholm)',
    'European Union North',
    'SE',
    'Europe',
    'Stockholm',
    'Europe/Stockholm',
    true,
    true,
    ARRAY['GDPR', 'SOC2', 'ISO27001'],
    true,
    true,
    'Docker',
    'eu-north-1',
    'neo-postgres-eu-west:5432',
    '172.19.0.0/16'
),
-- Asia Pacific
(
    'ap-southeast-1',
    'Asia Pacific (Singapore)',
    'Asia Pacific Southeast',
    'SG',
    'Asia',
    'Singapore',
    'Asia/Singapore',
    true,
    false,
    ARRAY['SOC2', 'ISO27001', 'PDPA'],
    true,
    true,
    'Docker',
    'ap-southeast-1',
    'neo-postgres-us-east:5432',
    '172.19.0.0/16'
),
(
    'ap-northeast-1',
    'Asia Pacific (Tokyo)',
    'Asia Pacific Northeast',
    'JP',
    'Asia',
    'Tokyo',
    'Asia/Tokyo',
    true,
    false,
    ARRAY['SOC2', 'ISO27001', 'APPI'],
    true,
    true,
    'Docker',
    'ap-northeast-1',
    'neo-postgres-us-east:5432',
    '172.19.0.0/16'
),
(
    'ap-south-1',
    'Asia Pacific (Mumbai)',
    'Asia Pacific South',
    'IN',
    'Asia',
    'Mumbai',
    'Asia/Kolkata',
    true,
    false,
    ARRAY['SOC2', 'ISO27001', 'DPDP'],
    true,
    true,
    'Docker',
    'ap-south-1',
    'neo-postgres-us-east:5432',
    '172.19.0.0/16'
),
-- Australia
(
    'ap-southeast-2',
    'Asia Pacific (Sydney)',
    'Australia Southeast',
    'AU',
    'Oceania',
    'Sydney',
    'Australia/Sydney',
    true,
    false,
    ARRAY['SOC2', 'ISO27001', 'Privacy Act'],
    true,
    true,
    'Docker',
    'ap-southeast-2',
    'neo-postgres-us-east:5432',
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
    SELECT id, code FROM admin.regions 
    WHERE code IN ('us-east-1', 'us-west-2', 'ca-central-1', 'eu-west-1', 'eu-central-1', 'eu-north-1', 'ap-southeast-1', 'ap-northeast-1', 'ap-south-1', 'ap-southeast-2')
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
    country_code,
    continent,
    gdpr_region,
    compliance_certifications,
    is_active,
    accepts_new_tenants
FROM admin.regions 
ORDER BY continent, code;

-- Show database connections
SELECT 
    r.code as region_code,
    r.continent,
    dc.connection_name,
    dc.connection_type,
    dc.host,
    dc.port,
    dc.database_name,
    dc.is_active,
    dc.is_healthy
FROM admin.database_connections dc
JOIN admin.regions r ON dc.region_id = r.id
ORDER BY r.continent, r.code, dc.connection_type, dc.connection_name;

-- Regional summary
SELECT 
    continent,
    COUNT(*) as region_count,
    COUNT(CASE WHEN gdpr_region THEN 1 END) as gdpr_regions,
    COUNT(CASE WHEN accepts_new_tenants THEN 1 END) as accepting_tenants
FROM admin.regions
GROUP BY continent
ORDER BY continent;