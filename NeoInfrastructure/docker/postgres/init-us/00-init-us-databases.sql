-- US East Region Database Initialization
-- Creates US-specific databases for regional data
-- This script runs automatically during PostgreSQL container startup

-- Create neofast_shared_us database
CREATE DATABASE neofast_shared_us
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    TEMPLATE = template0;

-- Create neofast_analytics_us database
CREATE DATABASE neofast_analytics_us
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    TEMPLATE = template0;

-- Grant all privileges to postgres user
GRANT ALL PRIVILEGES ON DATABASE neofast_shared_us TO postgres;
GRANT ALL PRIVILEGES ON DATABASE neofast_analytics_us TO postgres;

-- Add database comments for documentation
COMMENT ON DATABASE neofast_shared_us IS 'NeoMultiTenant - Shared Tenant Data (US Region)';
COMMENT ON DATABASE neofast_analytics_us IS 'NeoMultiTenant - Analytics Data (US Region)';

-- Log successful database creation
\echo 'NeoInfrastructure US East regional databases created successfully';