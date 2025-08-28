-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- For UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";       -- For pgcrypto
CREATE EXTENSION IF NOT EXISTS "pg_jsonschema";  -- For jsonschema
CREATE EXTENSION IF NOT EXISTS "pgjwt";          -- For jwt
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements"; -- For pg_stat_statements
CREATE EXTENSION IF NOT EXISTS "btree_gin";      -- For gin indexes
CREATE EXTENSION IF NOT EXISTS "hypopg";         -- For hypothetical indexes

CREATE EXTENSION IF NOT EXISTS "pgstattuple";       -- For pgstattuple functions
CREATE EXTENSION IF NOT EXISTS "index_advisor";      -- For index advisor functions

-- Set timezone
SET timezone = 'UTC';
-- Set search path
ALTER DATABASE postgres SET search_path TO public, extensions;

-- Create extension dependencies
CREATE EXTENSION IF NOT EXISTS "plpgsql" WITH SCHEMA pg_catalog;
CREATE EXTENSION IF NOT EXISTS "pg_cron" WITH SCHEMA pg_catalog;