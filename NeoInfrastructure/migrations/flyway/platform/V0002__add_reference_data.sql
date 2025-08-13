-- V002: Platform Common Reference Data (Simplified Master Data)
-- Creates essential ISO-standard reference data for tenant synchronization
-- Applied to: All databases (via platform_common schema replication)

-- ============================================================================
-- SIMPLIFIED REFERENCE DATA TYPES
-- ============================================================================

-- Simple status for all reference data
CREATE TYPE platform_common.reference_status AS ENUM (
    'active', 'inactive', 'historical'
);

-- ============================================================================
-- CURRENCIES (ISO 4217 - Essential Fields Only)
-- ============================================================================

CREATE TABLE platform_common.currencies (
    -- ISO 4217 Standard (Primary Key)
    code CHAR(3) PRIMARY KEY,                        -- ISO 4217 alphabetic code (USD, EUR, etc.)
    numeric_code CHAR(3),                            -- ISO 4217 numeric code (840, 978, etc.)
    minor_unit SMALLINT DEFAULT 2,                   -- Number of decimal places (0-6)
    
    -- Essential Information
    name VARCHAR(100) NOT NULL,                      -- Official currency name
    symbol VARCHAR(5),                               -- Currency symbol ($, €, ¥, etc.)
    
    -- Basic Metadata
    status platform_common.reference_status DEFAULT 'active',
    is_cryptocurrency BOOLEAN DEFAULT false,
    is_legal_tender BOOLEAN DEFAULT true,
    
    -- System Fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_minor_unit CHECK (minor_unit >= 0 AND minor_unit <= 6)
);

-- ============================================================================
-- COUNTRIES (ISO 3166 - Essential Fields Only)
-- ============================================================================

CREATE TABLE platform_common.countries (
    -- ISO 3166-1 Standard (Primary Key)
    code CHAR(2) PRIMARY KEY,                       -- ISO 3166-1 alpha-2 (US, GB, etc.)
    code3 CHAR(3) NOT NULL UNIQUE,                  -- ISO 3166-1 alpha-3 (USA, GBR, etc.)
    numeric_code CHAR(3) NOT NULL UNIQUE,           -- ISO 3166-1 numeric (840, 826, etc.)
    
    -- Essential Information
    name VARCHAR(100) NOT NULL,                     -- Official short name
    official_name VARCHAR(200),                     -- Official full name
    region VARCHAR(50) NOT NULL,                    -- Geographic region
    continent VARCHAR(20) NOT NULL,                 -- Continent
    
    -- Basic Metadata
    status platform_common.reference_status DEFAULT 'active',
    calling_code VARCHAR(10),                       -- International calling code (+1, +44, etc.)
    default_currency_code CHAR(3),                  -- Primary currency
    
    -- Compliance Flags
    gdpr_applicable BOOLEAN DEFAULT false,
    data_localization_required BOOLEAN DEFAULT false,
    
    -- System Fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- LANGUAGES (ISO 639 - Essential Fields Only)
-- ============================================================================

CREATE TABLE platform_common.languages (
    -- ISO 639 Standard (Primary Key)
    code VARCHAR(10) PRIMARY KEY,                   -- ISO 639-1/639-3 code (en, en-US, etc.)
    iso639_1 CHAR(2),                               -- ISO 639-1 two-letter code
    iso639_2 CHAR(3),                               -- ISO 639-2 three-letter code
    
    -- Essential Information
    name VARCHAR(100) NOT NULL,                     -- English name
    native_name VARCHAR(100) NOT NULL,              -- Native name
    
    -- Basic Metadata
    status platform_common.reference_status DEFAULT 'active',
    writing_direction VARCHAR(10) DEFAULT 'ltr',    -- ltr, rtl, ttb
    
    -- System Fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_writing_direction CHECK (writing_direction IN ('ltr', 'rtl', 'ttb'))
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE (Minimal)
-- ============================================================================

-- Currencies indexes (code is primary key)
CREATE INDEX idx_currencies_status ON platform_common.currencies(status);
CREATE INDEX idx_currencies_crypto ON platform_common.currencies(is_cryptocurrency);

-- Countries indexes (code is primary key)
CREATE INDEX idx_countries_code3 ON platform_common.countries(code3);
CREATE INDEX idx_countries_numeric ON platform_common.countries(numeric_code);
CREATE INDEX idx_countries_status ON platform_common.countries(status);
CREATE INDEX idx_countries_region ON platform_common.countries(region);
CREATE INDEX idx_countries_gdpr ON platform_common.countries(gdpr_applicable) WHERE gdpr_applicable = true;

-- Languages indexes (code is primary key)
CREATE INDEX idx_languages_iso639_1 ON platform_common.languages(iso639_1);
CREATE INDEX idx_languages_status ON platform_common.languages(status);

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================

CREATE TRIGGER update_currencies_updated_at
    BEFORE UPDATE ON platform_common.currencies
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_countries_updated_at
    BEFORE UPDATE ON platform_common.countries
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_languages_updated_at
    BEFORE UPDATE ON platform_common.languages
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE platform_common.currencies IS 'Simplified ISO 4217 currencies for tenant synchronization';
COMMENT ON TABLE platform_common.countries IS 'Simplified ISO 3166 countries for tenant synchronization';
COMMENT ON TABLE platform_common.languages IS 'Simplified ISO 639 languages for tenant synchronization';

-- Log migration completion
SELECT 'V002: Simplified platform common reference data created' as migration_status;