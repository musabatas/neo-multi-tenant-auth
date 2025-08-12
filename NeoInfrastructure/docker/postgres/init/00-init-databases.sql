-- NeoInfrastructure Shared Database Initialization
-- Creates only GLOBAL databases that serve all regions
-- This script runs automatically during PostgreSQL container startup

-- Create neofast_admin database (Global - deployed to US region but serves all regions)
CREATE DATABASE neofast_admin
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    TEMPLATE = template0;

-- Grant all privileges to postgres user
GRANT ALL PRIVILEGES ON DATABASE neofast_admin TO postgres;

-- Add database comments for documentation
COMMENT ON DATABASE neofast_admin IS 'NeoMultiTenant - Global Platform Administration Database';


-- Log successful database creation
\echo 'NeoInfrastructure shared databases created successfully';