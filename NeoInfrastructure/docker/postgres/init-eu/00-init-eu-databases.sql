-- EU West Region Database Initialization
-- Creates EU-specific databases for GDPR compliance
-- This script runs automatically during PostgreSQL container startup

-- NOTE: neofast_admin is only deployed to US region (primary)
-- EU region only has regional tenant data and analytics

-- Create neofast_shared_eu database
CREATE DATABASE neofast_shared_eu
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    TEMPLATE = template0;

-- Create neofast_analytics_eu database
CREATE DATABASE neofast_analytics_eu
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    TEMPLATE = template0;

-- Grant all privileges to postgres user
GRANT ALL PRIVILEGES ON DATABASE neofast_shared_eu TO postgres;
GRANT ALL PRIVILEGES ON DATABASE neofast_analytics_eu TO postgres;

-- Add database comments for documentation
COMMENT ON DATABASE neofast_shared_eu IS 'NeoMultiTenant - Shared Tenant Data (EU Region/GDPR)';
COMMENT ON DATABASE neofast_analytics_eu IS 'NeoMultiTenant - Analytics Data (EU Region/GDPR)';

-- Log successful database creation
\echo 'NeoInfrastructure EU West databases created successfully';