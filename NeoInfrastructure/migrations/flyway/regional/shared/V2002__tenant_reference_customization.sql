-- V002: Tenant Reference Data Customization
-- Creates tenant-specific reference data customization tables
-- Applied to: Regional shared databases (tenant_template schema)
-- Placeholders: ${region}, ${gdpr}

-- ============================================================================
-- TENANT CURRENCIES (Rich Customization)
-- ============================================================================

CREATE TABLE tenant_template.currencies (
    -- Reference to master data
    code CHAR(3) PRIMARY KEY,                   -- No FK constraint (cross-schema)
    
    -- Tenant Customization
    is_default BOOLEAN DEFAULT false,           -- Tenant's base currency
    is_active BOOLEAN DEFAULT true,             -- Enable/disable for tenant
    sort_order INTEGER DEFAULT 999,             -- Custom ordering in dropdowns
    
    -- Display Customization
    custom_name VARCHAR(100),                   -- Override display name
    custom_symbol VARCHAR(10),                  -- Override symbol
    custom_format JSONB DEFAULT '{}',          -- Custom formatting rules
    
    -- Business Configuration
    auto_sync_rate BOOLEAN DEFAULT true,        -- Auto-sync master updates
    exchange_rate DECIMAL(15,8),                -- Current exchange rate to base
    exchange_rate_source VARCHAR(50),           -- Rate provider (manual, api, etc.)
    exchange_rate_updated_at TIMESTAMPTZ,       -- Last rate update
    
    -- Formatting and Display
    symbol_position VARCHAR(10) DEFAULT 'before', -- before, after
    space_between_symbol BOOLEAN DEFAULT false,
    thousands_separator CHAR(1) DEFAULT ',',
    decimal_separator CHAR(1) DEFAULT '.',
    decimal_places SMALLINT,                    -- Override minor_unit from master
    
    -- Business Rules
    min_amount DECIMAL(15,4) DEFAULT 0.01,     -- Minimum transaction amount
    max_amount DECIMAL(15,4),                   -- Maximum transaction amount
    rounding_increment DECIMAL(10,4),           -- Custom rounding rules
    
    -- Accounting Integration
    accounting_code VARCHAR(20),                -- GL account code
    tax_category VARCHAR(50),                   -- Tax classification
    
    -- Audit and Sync
    platform_sync_version INTEGER DEFAULT 1,             -- Track sync with master
    last_synced_at TIMESTAMPTZ,
    added_by UUID REFERENCES tenant_template.users(id),
    added_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_symbol_position CHECK (symbol_position IN ('before', 'after')),
    CONSTRAINT valid_decimal_places CHECK (decimal_places IS NULL OR (decimal_places >= 0 AND decimal_places <= 6)),
    CONSTRAINT valid_amounts CHECK (min_amount >= 0 AND (max_amount IS NULL OR max_amount >= min_amount)),
    CONSTRAINT valid_separators CHECK (thousands_separator != decimal_separator),
    CONSTRAINT valid_sort_order CHECK (sort_order > 0)
);

-- ============================================================================
-- TENANT COUNTRIES (Rich Customization)
-- ============================================================================

CREATE TABLE tenant_template.countries (
    -- Reference to master data
    code CHAR(2) PRIMARY KEY,                   -- No FK constraint (cross-schema)
    
    -- Tenant Customization
    is_default BOOLEAN DEFAULT false,           -- Tenant's primary country
    is_active BOOLEAN DEFAULT true,             -- Enable/disable for tenant
    sort_order INTEGER DEFAULT 999,             -- Custom ordering
    
    -- Display Customization
    custom_name VARCHAR(100),                   -- Override display name
    custom_format JSONB DEFAULT '{}',          -- Custom formatting rules
    
    -- Business Configuration
    is_billing_enabled BOOLEAN DEFAULT true,   -- Allow billing addresses
    is_shipping_enabled BOOLEAN DEFAULT true,  -- Allow shipping addresses
    requires_state_province BOOLEAN DEFAULT false, -- State/province required
    
    -- Address Validation
    postal_code_regex VARCHAR(100),            -- Custom postal code validation
    address_format_template TEXT,              -- Address formatting template
    
    -- Tax and Legal
    default_tax_rate DECIMAL(5,4),            -- Default tax rate
    tax_number_format VARCHAR(50),            -- Tax ID format/validation
    legal_entity_required BOOLEAN DEFAULT false, -- Business registration required
    
    -- Compliance and Restrictions
    data_retention_months INTEGER,             -- GDPR retention period
    restricted_services TEXT[],                -- Services not available
    compliance_notes TEXT,                     -- Special compliance requirements
    
    -- Audit and Sync
    platform_sync_version INTEGER DEFAULT 1,
    last_synced_at TIMESTAMPTZ,
    added_by UUID REFERENCES tenant_template.users(id),
    added_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_tax_rate CHECK (default_tax_rate IS NULL OR (default_tax_rate >= 0 AND default_tax_rate <= 1)),
    CONSTRAINT valid_retention CHECK (data_retention_months IS NULL OR data_retention_months > 0),
    CONSTRAINT valid_sort_order CHECK (sort_order > 0)
);

-- ============================================================================
-- TENANT LANGUAGES (Rich Customization)
-- ============================================================================

CREATE TABLE tenant_template.languages (
    -- Reference to master data
    code VARCHAR(10) PRIMARY KEY,               -- No FK constraint (cross-schema)
    
    -- Tenant Customization
    is_default BOOLEAN DEFAULT false,           -- Tenant's primary language
    is_active BOOLEAN DEFAULT true,             -- Enable/disable for tenant
    sort_order INTEGER DEFAULT 999,             -- Custom ordering
    
    -- Feature Enablement
    ui_enabled BOOLEAN DEFAULT false,           -- Enable UI translation
    email_enabled BOOLEAN DEFAULT false,        -- Enable email templates
    notifications_enabled BOOLEAN DEFAULT false, -- Enable notifications
    documentation_enabled BOOLEAN DEFAULT false, -- Enable help docs
    
    -- Display Customization
    custom_name VARCHAR(100),                   -- Override display name
    custom_native_name VARCHAR(100),           -- Override native name
    
    -- Localization Configuration
    date_format VARCHAR(20) DEFAULT 'YYYY-MM-DD', -- Preferred date format
    time_format VARCHAR(20) DEFAULT '24h',      -- 12h or 24h
    number_format JSONB DEFAULT '{}',           -- Number formatting preferences
    currency_format JSONB DEFAULT '{}',         -- Currency formatting
    
    -- Content Configuration
    translation_quality_threshold DECIMAL(3,2) DEFAULT 0.80, -- Minimum quality score
    fallback_language_code VARCHAR(10),        -- Fallback if translation missing
    
    -- Business Rules
    legal_required BOOLEAN DEFAULT false,      -- Required for legal compliance
    customer_facing BOOLEAN DEFAULT true,      -- Show to customers
    internal_only BOOLEAN DEFAULT false,       -- Staff use only
    
    -- Progress Tracking
    translation_progress SMALLINT DEFAULT 0,   -- % of content translated
    last_translation_update TIMESTAMPTZ,       -- Last translation update
    
    -- Audit and Sync
    platform_sync_version INTEGER DEFAULT 1,
    last_synced_at TIMESTAMPTZ,
    added_by UUID REFERENCES tenant_template.users(id),
    added_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_progress CHECK (translation_progress >= 0 AND translation_progress <= 100),
    CONSTRAINT valid_quality_threshold CHECK (translation_quality_threshold >= 0 AND translation_quality_threshold <= 1),
    CONSTRAINT valid_time_format CHECK (time_format IN ('12h', '24h')),
    CONSTRAINT valid_sort_order CHECK (sort_order > 0)
);

-- ============================================================================
-- REFERENCE SYNC CONFIGURATION
-- ============================================================================

CREATE TABLE tenant_template.reference_sync_config (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    sync_type VARCHAR(20) NOT NULL,             -- 'currencies', 'countries', 'languages'
    auto_sync_enabled BOOLEAN DEFAULT true,     -- Auto-sync master updates
    sync_frequency_hours INTEGER DEFAULT 24,    -- How often to sync
    last_sync_at TIMESTAMPTZ,
    next_sync_at TIMESTAMPTZ,
    sync_strategy VARCHAR(20) DEFAULT 'merge',  -- merge, replace, manual
    
    -- Sync Rules
    auto_enable_new BOOLEAN DEFAULT false,      -- Auto-enable new master data
    sync_filters JSONB DEFAULT '{}',           -- Region-based filters
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_sync_type CHECK (sync_type IN ('currencies', 'countries', 'languages')),
    CONSTRAINT valid_sync_strategy CHECK (sync_strategy IN ('merge', 'replace', 'manual')),
    CONSTRAINT valid_frequency CHECK (sync_frequency_hours > 0),
    CONSTRAINT unique_sync_type UNIQUE (sync_type)
);

-- ============================================================================
-- REFERENCE SYNC HISTORY
-- ============================================================================

CREATE TABLE tenant_template.reference_sync_history (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    sync_type VARCHAR(20) NOT NULL,
    sync_action VARCHAR(20) NOT NULL,           -- 'added', 'updated', 'removed', 'skipped'
    reference_code VARCHAR(10) NOT NULL,        -- Currency/country/language code
    changes JSONB DEFAULT '{}',                -- What changed
    sync_source VARCHAR(20) DEFAULT 'auto',    -- auto, manual, admin
    synced_by UUID REFERENCES tenant_template.users(id),
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_sync_type_history CHECK (sync_type IN ('currencies', 'countries', 'languages')),
    CONSTRAINT valid_sync_action CHECK (sync_action IN ('added', 'updated', 'removed', 'skipped')),
    CONSTRAINT valid_sync_source CHECK (sync_source IN ('auto', 'manual', 'admin'))
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Currency indexes
CREATE INDEX idx_tenant_currencies_active ON tenant_template.currencies(is_active) WHERE is_active = true;
CREATE INDEX idx_tenant_currencies_default ON tenant_template.currencies(is_default) WHERE is_default = true;
CREATE INDEX idx_tenant_currencies_sort ON tenant_template.currencies(sort_order);
CREATE INDEX idx_tenant_currencies_added_by ON tenant_template.currencies(added_by);

-- Country indexes
CREATE INDEX idx_tenant_countries_active ON tenant_template.countries(is_active) WHERE is_active = true;
CREATE INDEX idx_tenant_countries_default ON tenant_template.countries(is_default) WHERE is_default = true;
CREATE INDEX idx_tenant_countries_sort ON tenant_template.countries(sort_order);
CREATE INDEX idx_tenant_countries_billing ON tenant_template.countries(is_billing_enabled) WHERE is_billing_enabled = true;
CREATE INDEX idx_tenant_countries_shipping ON tenant_template.countries(is_shipping_enabled) WHERE is_shipping_enabled = true;

-- Language indexes
CREATE INDEX idx_tenant_languages_active ON tenant_template.languages(is_active) WHERE is_active = true;
CREATE INDEX idx_tenant_languages_default ON tenant_template.languages(is_default) WHERE is_default = true;
CREATE INDEX idx_tenant_languages_sort ON tenant_template.languages(sort_order);
CREATE INDEX idx_tenant_languages_ui ON tenant_template.languages(ui_enabled) WHERE ui_enabled = true;

-- Sync config indexes
CREATE INDEX idx_sync_config_type ON tenant_template.reference_sync_config(sync_type);
CREATE INDEX idx_sync_config_next_sync ON tenant_template.reference_sync_config(next_sync_at);

-- Sync history indexes
CREATE INDEX idx_sync_history_type ON tenant_template.reference_sync_history(sync_type);
CREATE INDEX idx_sync_history_action ON tenant_template.reference_sync_history(sync_action);
CREATE INDEX idx_sync_history_code ON tenant_template.reference_sync_history(reference_code);
CREATE INDEX idx_sync_history_synced_at ON tenant_template.reference_sync_history(synced_at);

-- ============================================================================
-- UNIQUE CONSTRAINTS FOR DEFAULT VALUES
-- ============================================================================

-- Ensure only one default currency per tenant
CREATE UNIQUE INDEX idx_tenant_currencies_one_default 
ON tenant_template.currencies(is_default) 
WHERE is_default = true;

-- Ensure only one default country per tenant
CREATE UNIQUE INDEX idx_tenant_countries_one_default 
ON tenant_template.countries(is_default) 
WHERE is_default = true;

-- Ensure only one default language per tenant
CREATE UNIQUE INDEX idx_tenant_languages_one_default 
ON tenant_template.languages(is_default) 
WHERE is_default = true;

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================

CREATE TRIGGER update_tenant_currencies_updated_at
    BEFORE UPDATE ON tenant_template.currencies
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_tenant_countries_updated_at
    BEFORE UPDATE ON tenant_template.countries
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_tenant_languages_updated_at
    BEFORE UPDATE ON tenant_template.languages
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_sync_config_updated_at
    BEFORE UPDATE ON tenant_template.reference_sync_config
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

-- ============================================================================
-- DEFAULT SYNC CONFIGURATION
-- ============================================================================

-- Insert default sync configuration for all reference types
INSERT INTO tenant_template.reference_sync_config (sync_type, auto_sync_enabled, sync_frequency_hours, sync_strategy) VALUES
('currencies', true, 24, 'merge'),
('countries', true, 168, 'merge'),    -- Weekly for countries (less frequent changes)
('languages', true, 24, 'merge');

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE tenant_template.currencies IS 'Tenant-specific currency customization with exchange rates and formatting';
COMMENT ON TABLE tenant_template.countries IS 'Tenant-specific country customization with business rules and compliance';
COMMENT ON TABLE tenant_template.languages IS 'Tenant-specific language customization with localization features';
COMMENT ON TABLE tenant_template.reference_sync_config IS 'Configuration for syncing reference data from master sources';
COMMENT ON TABLE tenant_template.reference_sync_history IS 'Audit trail for reference data synchronization activities';

-- Column comments for complex fields
COMMENT ON COLUMN tenant_template.currencies.exchange_rate IS 'Exchange rate relative to tenant default currency';
COMMENT ON COLUMN tenant_template.currencies.custom_format IS 'JSON formatting rules: {"prefix": "$", "suffix": "", "grouping": [3]}';
COMMENT ON COLUMN tenant_template.countries.address_format_template IS 'Template for address formatting: {line1}\n{city}, {state} {postal}\n{country}';
COMMENT ON COLUMN tenant_template.languages.number_format IS 'JSON number formatting: {"decimal": ".", "thousand": ",", "grouping": [3]}';

-- Log migration completion
SELECT 'V002: Tenant reference data customization tables created for region ${region} (GDPR: ${gdpr})' as migration_status;