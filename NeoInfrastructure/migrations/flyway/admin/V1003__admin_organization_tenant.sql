-- V004: Admin Organization and Tenant Management
-- Creates organization and tenant management tables
-- Applied to: Admin database only

-- ============================================================================
-- ORGANIZATIONS (Companies/entities that can have multiple tenants)
-- ============================================================================

CREATE TABLE admin.organizations (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE 
        CONSTRAINT slug_format CHECK (slug ~* '^[a-z0-9][a-z0-9-]*[a-z0-9]$')
        CONSTRAINT slug_length CHECK (length(slug) >= 2 AND length(slug) <= 100),
    legal_name VARCHAR(255),
    tax_id VARCHAR(50),
    business_type VARCHAR(50),
    industry VARCHAR(100),
    company_size VARCHAR(20),
    website_url VARCHAR(2048),
    primary_contact_id UUID REFERENCES admin.platform_users,
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state_province VARCHAR(100),
    postal_code VARCHAR(20),
    country_code CHAR(2),
    default_timezone VARCHAR(50) DEFAULT 'UTC',
    default_locale VARCHAR(10) DEFAULT 'en-US',
    default_currency CHAR(3) DEFAULT 'USD',
    logo_url VARCHAR(2048),
    brand_colors JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    verified_at TIMESTAMPTZ,
    verification_documents TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Indexes for organizations
CREATE INDEX idx_organizations_slug ON admin.organizations(slug);
CREATE INDEX idx_organizations_name ON admin.organizations(name);
CREATE INDEX idx_organizations_active ON admin.organizations(is_active);
CREATE INDEX idx_organizations_country ON admin.organizations(country_code);
CREATE INDEX idx_organizations_primary_contact ON admin.organizations(primary_contact_id);

-- ============================================================================
-- REGIONS (Geographic deployment regions)
-- ============================================================================

CREATE TABLE admin.regions (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    country_code CHAR(2) NOT NULL,
    continent VARCHAR(20) NOT NULL,
    city VARCHAR(100),
    timezone VARCHAR(50) NOT NULL,
    coordinates VARCHAR(50),
    data_residency_compliant BOOLEAN DEFAULT true,
    gdpr_region BOOLEAN DEFAULT false,
    compliance_certifications TEXT[],
    legal_entity VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    accepts_new_tenants BOOLEAN DEFAULT true,
    capacity_percentage SMALLINT DEFAULT 0 
        CONSTRAINT valid_capacity CHECK (capacity_percentage >= 0 AND capacity_percentage <= 100),
    max_tenants INTEGER,
    current_tenants INTEGER DEFAULT 0,
    priority INTEGER DEFAULT 0,
    provider VARCHAR(50),
    provider_region VARCHAR(50),
    availability_zones TEXT[],
    primary_endpoint VARCHAR(255) NOT NULL,
    backup_endpoints TEXT[],
    internal_network VARCHAR(18),
    cost_per_gb_monthly_cents INTEGER DEFAULT 0,
    cost_per_tenant_monthly_cents INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT valid_tenant_counts CHECK (
        current_tenants >= 0 AND 
        (max_tenants IS NULL OR current_tenants <= max_tenants)
    )
);

-- Indexes for regions
CREATE INDEX idx_regions_code ON admin.regions(code);
CREATE INDEX idx_regions_active ON admin.regions(is_active);
CREATE INDEX idx_regions_accepts_tenants ON admin.regions(accepts_new_tenants);
CREATE INDEX idx_regions_country ON admin.regions(country_code);
CREATE INDEX idx_regions_gdpr ON admin.regions(gdpr_region);

-- ============================================================================
-- DATABASE CONNECTIONS (Regional database connection configs)
-- ============================================================================

CREATE TABLE admin.database_connections (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    region_id UUID NOT NULL REFERENCES admin.regions,
    connection_name VARCHAR(100) NOT NULL UNIQUE,
    connection_type admin.connection_type NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INTEGER DEFAULT 5432,
    database_name VARCHAR(63) NOT NULL,
    ssl_mode VARCHAR(20) DEFAULT 'require',
    username VARCHAR(255) DEFAULT 'postgres' NOT NULL,
    encrypted_password VARCHAR(256),
    pool_min_size INTEGER DEFAULT 5,
    pool_max_size INTEGER DEFAULT 20,
    pool_timeout_seconds INTEGER DEFAULT 30,
    pool_recycle_seconds INTEGER DEFAULT 3600,
    pool_pre_ping BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    is_healthy BOOLEAN DEFAULT true,
    last_health_check TIMESTAMPTZ,
    consecutive_failures INTEGER DEFAULT 0,
    max_consecutive_failures INTEGER DEFAULT 3,
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT valid_pool_config CHECK (
        pool_min_size >= 0 AND 
        pool_max_size >= pool_min_size AND 
        pool_timeout_seconds > 0 AND 
        pool_recycle_seconds > 0
    )
);

-- Indexes for database_connections
CREATE INDEX idx_database_connections_region ON admin.database_connections(region_id);
CREATE INDEX idx_database_connections_type ON admin.database_connections(connection_type);
CREATE INDEX idx_database_connections_active ON admin.database_connections(is_active);
CREATE INDEX idx_database_connections_healthy ON admin.database_connections(is_healthy);

-- ============================================================================
-- TENANTS (Individual tenant instances)
-- ============================================================================

CREATE TABLE admin.tenants (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    organization_id UUID NOT NULL REFERENCES admin.organizations,
    slug VARCHAR(63) NOT NULL UNIQUE 
        CONSTRAINT tenant_slug_format CHECK (slug ~* '^[a-z0-9][a-z0-9-]*[a-z0-9]$')
        CONSTRAINT tenant_slug_length CHECK (length(slug) >= 2 AND length(slug) <= 54),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    schema_name VARCHAR(63) NOT NULL UNIQUE 
        CONSTRAINT schema_name_format CHECK (schema_name ~* '^[a-z][a-z0-9_]*$'),
    database_name VARCHAR(63),
    custom_domain VARCHAR(253) UNIQUE,
    deployment_type admin.deployment_type DEFAULT 'schema',
    environment admin.environment_type DEFAULT 'production',
    region_id UUID REFERENCES admin.regions,
    database_connection_id UUID REFERENCES admin.database_connections,
    external_auth_provider admin.auth_provider NOT NULL,
    external_auth_realm VARCHAR(100) NOT NULL,
    external_user_id VARCHAR(255) NOT NULL,
    external_auth_metadata JSONB DEFAULT '{}',
    allow_impersonations BOOLEAN NOT NULL DEFAULT false,
    status admin.tenant_status DEFAULT 'pending',
    internal_notes TEXT,
    features_enabled JSONB DEFAULT '{}',
    feature_overrides JSONB DEFAULT '{}',
    provisioned_at TIMESTAMPTZ,
    activated_at TIMESTAMPTZ,
    suspended_at TIMESTAMPTZ,
    last_activity_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Indexes for tenants
CREATE INDEX idx_tenants_organization ON admin.tenants(organization_id);
CREATE INDEX idx_tenants_slug ON admin.tenants(slug);
CREATE INDEX idx_tenants_schema_name ON admin.tenants(schema_name);
CREATE INDEX idx_tenants_status ON admin.tenants(status);
CREATE INDEX idx_tenants_region ON admin.tenants(region_id);
CREATE INDEX idx_tenants_environment ON admin.tenants(environment);
CREATE INDEX idx_tenants_auth_provider ON admin.tenants(external_auth_provider);

-- ============================================================================
-- TENANT CONTACTS (Contact information for tenants)
-- ============================================================================

CREATE TABLE admin.tenant_contacts (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    tenant_id UUID NOT NULL REFERENCES admin.tenants ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES admin.platform_users,
    contact_type admin.contact_type NOT NULL,
    contact_info JSONB DEFAULT '{}',
    is_primary BOOLEAN DEFAULT false,
    receive_notifications BOOLEAN DEFAULT true,
    receive_billing_emails BOOLEAN DEFAULT false,
    receive_technical_alerts BOOLEAN DEFAULT false,
    receive_marketing_emails BOOLEAN DEFAULT true,
    emergency_phone VARCHAR(20),
    alternative_email VARCHAR(320),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, user_id, contact_type)
);

-- Indexes for tenant_contacts
CREATE INDEX idx_tenant_contacts_tenant ON admin.tenant_contacts(tenant_id);
CREATE INDEX idx_tenant_contacts_user ON admin.tenant_contacts(user_id);
CREATE INDEX idx_tenant_contacts_type ON admin.tenant_contacts(contact_type);
CREATE INDEX idx_tenant_contacts_primary ON admin.tenant_contacts(is_primary);

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================

CREATE TRIGGER update_organizations_updated_at
    BEFORE UPDATE ON admin.organizations
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_regions_updated_at
    BEFORE UPDATE ON admin.regions
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_database_connections_updated_at
    BEFORE UPDATE ON admin.database_connections
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_tenants_updated_at
    BEFORE UPDATE ON admin.tenants
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_tenant_contacts_updated_at
    BEFORE UPDATE ON admin.tenant_contacts
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE admin.organizations IS 'Companies or entities that can have multiple tenants';
COMMENT ON TABLE admin.regions IS 'Geographic deployment regions with compliance and capacity info';
COMMENT ON TABLE admin.database_connections IS 'Database connection configurations per region';
COMMENT ON TABLE admin.tenants IS 'Individual tenant instances with deployment and configuration';
COMMENT ON TABLE admin.tenant_contacts IS 'Contact information and notification preferences for tenants';

-- Log migration completion
SELECT 'V004: Admin organization and tenant management tables created' as migration_status;