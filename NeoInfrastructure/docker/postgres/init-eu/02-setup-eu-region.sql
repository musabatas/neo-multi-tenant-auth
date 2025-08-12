-- EU West Region Specific Configuration
-- This script runs after database creation for EU region setup
-- GDPR Compliance and region-specific configurations

-- Log EU region setup
\echo 'Setting up EU West region specific configuration'
\echo 'Region: eu-west-1'
\echo 'GDPR Compliant: true'
\echo 'Connection Type: primary'

-- GDPR Compliance configurations
-- Set default timezone for EU region
-- SET timezone = 'Europe/Dublin';

-- Future: Add EU/GDPR-specific database configurations here
-- - Enhanced audit trails
-- - Data anonymization functions
-- - Consent tracking tables
-- - Data export utilities

-- Update pg_cron settings for EU databases
ALTER SYSTEM SET cron.database_name = 'neofast_admin_eu';

\echo 'EU West region configuration completed';