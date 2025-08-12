-- Keycloak Schema Setup
-- Creates the keycloak schema in neofast_admin database
-- This script runs after database creation

-- Connect to neofast_admin database and create keycloak schema
\c neofast_admin;

-- Create keycloak schema
CREATE SCHEMA IF NOT EXISTS keycloak;

-- Grant all privileges on keycloak schema to postgres user
GRANT ALL ON SCHEMA keycloak TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA keycloak TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA keycloak TO postgres;

-- Set default privileges for future objects in keycloak schema
ALTER DEFAULT PRIVILEGES IN SCHEMA keycloak GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA keycloak GRANT ALL ON SEQUENCES TO postgres;

-- Log successful schema creation
\echo 'Keycloak schema created successfully in neofast_admin database';