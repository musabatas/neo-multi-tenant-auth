-- V002: Admin Schema and Types
-- Creates admin schema with all enum types for platform administration
-- Applied to: Admin database only

-- Create admin schema
CREATE SCHEMA IF NOT EXISTS admin;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================================
-- ADMIN ENUM TYPES
-- ============================================================================

-- Auth provider types (admin-specific, can differ from platform_common)
CREATE TYPE admin.auth_provider AS ENUM (
    'keycloak', 'auth0', 'authelia', 'authentik', 'azure', 'google', 'custom'
);

-- Platform role levels (system-wide roles)
CREATE TYPE admin.platform_role_level AS ENUM (
    'system', 'platform', 'tenant'
);

-- Permission scope levels (where permissions can be applied)
CREATE TYPE admin.permission_scope_level AS ENUM (
    'platform', 'tenant', 'user'
);

-- Contact types for tenant management
CREATE TYPE admin.contact_type AS ENUM (
    'owner', 'admin', 'billing', 'technical', 'legal', 'emergency'
);

-- Tenant lifecycle status
CREATE TYPE admin.tenant_status AS ENUM (
    'pending', 'provisioning', 'active', 'suspended', 'migrating', 'archived', 'deleted'
);

-- Deployment strategy types
CREATE TYPE admin.deployment_type AS ENUM (
    'schema', 'database', 'dedicated'
);

-- Environment types
CREATE TYPE admin.environment_type AS ENUM (
    'development', 'staging', 'production'
);

-- Subscription plan tiers
CREATE TYPE admin.plan_tier AS ENUM (
    'free', 'starter', 'professional', 'enterprise', 'custom'
);

-- Billing cycles
CREATE TYPE admin.billing_cycle AS ENUM (
    'monthly', 'yearly'
);

-- Subscription statuses
CREATE TYPE admin.subscription_status AS ENUM (
    'trial', 'active', 'past_due', 'canceled', 'expired'
);

-- Invoice statuses
CREATE TYPE admin.invoice_status AS ENUM (
    'draft', 'open', 'paid', 'void', 'uncollectible'
);

-- Line item types for billing
CREATE TYPE admin.line_item_type AS ENUM (
    'subscription', 'usage', 'addon', 'discount', 'tax'
);

-- Database connection types
CREATE TYPE admin.connection_type AS ENUM (
    'primary', 'replica', 'analytics', 'backup'
);

-- Health status for monitoring
CREATE TYPE admin.health_status AS ENUM (
    'healthy', 'degraded', 'unhealthy'
);

-- Actor types for audit trails
CREATE TYPE admin.actor_type AS ENUM (
    'user', 'system', 'api', 'service'
);

-- Risk levels for security and monitoring
CREATE TYPE admin.risk_level AS ENUM (
    'low', 'medium', 'high', 'critical'
);

-- Data retention policies
CREATE TYPE admin.retention_policy AS ENUM (
    'standard', 'extended', 'permanent', 'immediate_delete'
);

-- Grant usage permissions
GRANT USAGE ON SCHEMA admin TO PUBLIC;

-- Log migration completion
SELECT 'V002: Admin schema and enum types created' as migration_status;