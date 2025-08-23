-- V001: Platform Common Schema
-- Creates shared functions, types, and utilities used across all databases
-- Applied to: Admin database (but shared functions will be used everywhere)

-- Enable required extensions in public schema explicitly
-- This ensures pgcrypto functions are accessible from all schemas
CREATE EXTENSION IF NOT EXISTS pgcrypto SCHEMA public;

-- Now create platform_common schema
CREATE SCHEMA IF NOT EXISTS platform_common;

-- ============================================================================
-- ENUM TYPES (Platform Common)
-- ============================================================================

-- Auth provider types (used across platform)
CREATE TYPE platform_common.auth_provider AS ENUM (
    'keycloak', 'auth0', 'authentik', 'authelia', 'azure', 'google', 'custom'
);

-- Unified role levels (merge platform and user role levels)
CREATE TYPE platform_common.role_level AS ENUM (
    'system',     -- System-wide (super admin)
    'platform',   -- Platform-wide (platform admin)
    'tenant',     -- Tenant-wide (tenant admin)
    'owner',      -- Tenant owner
    'admin',      -- Tenant administrator
    'manager',    -- Team manager
    'member',     -- Standard member
    'viewer',     -- Read-only access
    'guest'       -- Limited guest access
);

-- Unified user status
CREATE TYPE platform_common.user_status AS ENUM (
    'active', 'inactive', 'pending', 'suspended', 'archived'
);

-- Unified permission scope levels  
CREATE TYPE platform_common.permission_scope AS ENUM (
    'platform', 'tenant', 'team', 'user'
);

-- Team types
CREATE TYPE platform_common.team_types AS ENUM (
    'department', 'project', 'working_group', 'committee', 'other'
);

-- Risk levels
CREATE TYPE platform_common.risk_levels AS ENUM (
    'low', 'medium', 'high', 'critical'
);

-- ============================================================================
-- SHARED FUNCTIONS
-- ============================================================================

-- UUID v7 generation function (time-ordered UUIDs)
CREATE OR REPLACE FUNCTION platform_common.uuid_generate_v7() RETURNS uuid
    LANGUAGE plpgsql
AS $$
DECLARE
    unix_ts_ms bytea;
    uuid_bytes bytea;
BEGIN
    -- Get current timestamp in milliseconds
    unix_ts_ms = substring(int8send(floor(extract(epoch from clock_timestamp()) * 1000)::bigint) from 3);
    
    -- Generate random bytes (pgcrypto should be in public schema)
    uuid_bytes = unix_ts_ms || gen_random_bytes(10);
    
    -- Set version (7) and variant bits
    uuid_bytes = set_byte(uuid_bytes, 6, (b'0111' || get_byte(uuid_bytes, 6)::bit(4))::bit(8)::int);
    uuid_bytes = set_byte(uuid_bytes, 8, (b'10' || get_byte(uuid_bytes, 8)::bit(6))::bit(8)::int);
    
    RETURN encode(uuid_bytes, 'hex')::uuid;
END;
$$;

-- Updated_at trigger function
CREATE OR REPLACE FUNCTION platform_common.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- Grant usage permissions
GRANT USAGE ON SCHEMA platform_common TO PUBLIC;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA platform_common TO PUBLIC;

-- Set default privileges for future functions
ALTER DEFAULT PRIVILEGES IN SCHEMA platform_common GRANT EXECUTE ON FUNCTIONS TO PUBLIC;

-- Log migration completion
SELECT 'V001: Platform common schema and shared functions created' as migration_status;