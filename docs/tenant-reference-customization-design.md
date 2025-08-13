# Tenant Reference Data Customization Design

## Overview

This document outlines the tenant-level customization tables that enable rich business-specific configuration of reference data while maintaining sync with simplified master data in `platform_common`.

## Architecture Pattern

```
platform_common.currencies (simplified master)
        ↓ sync
tenant_acme.currencies (rich customization)
```

## Tenant Currency Customization

### Table: `currencies`

```sql
CREATE TABLE currencies (
    -- Reference to master data
    code CHAR(3) PRIMARY KEY REFERENCES platform_common.currencies(code),
    
    -- Tenant Customization
    is_default BOOLEAN DEFAULT false,           -- Tenant's base currency
    is_active BOOLEAN DEFAULT true,             -- Enable/disable for tenant
    sort_order INTEGER DEFAULT 999,             -- Custom ordering in dropdowns
    
    -- Display Customization
    custom_name VARCHAR(100),                   -- Override display name
    custom_symbol VARCHAR(10),                  -- Override symbol
    custom_format JSONB DEFAULT '{}',          -- Custom formatting rules
    
    -- Business Configuration
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
    sync_version INTEGER DEFAULT 1,             -- Track sync with master
    last_synced_at TIMESTAMPTZ,
    added_by UUID REFERENCES users(id),
    added_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_symbol_position CHECK (symbol_position IN ('before', 'after')),
    CONSTRAINT valid_decimal_places CHECK (decimal_places >= 0 AND decimal_places <= 6),
    CONSTRAINT valid_amounts CHECK (min_amount >= 0 AND (max_amount IS NULL OR max_amount >= min_amount)),
    CONSTRAINT one_default_currency UNIQUE (is_default) WHERE is_default = true
);
```

## Tenant Country Customization

### Table: `countries`

```sql
CREATE TABLE countries (
    -- Reference to master data
    code CHAR(2) PRIMARY KEY REFERENCES platform_common.countries(code),
    
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
    sync_version INTEGER DEFAULT 1,
    last_synced_at TIMESTAMPTZ,
    added_by UUID REFERENCES users(id),
    added_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_tax_rate CHECK (default_tax_rate IS NULL OR (default_tax_rate >= 0 AND default_tax_rate <= 1)),
    CONSTRAINT valid_retention CHECK (data_retention_months IS NULL OR data_retention_months > 0),
    CONSTRAINT one_default_country UNIQUE (is_default) WHERE is_default = true
);
```

## Tenant Language Customization

### Table: `languages`

```sql
CREATE TABLE languages (
    -- Reference to master data
    code VARCHAR(10) PRIMARY KEY REFERENCES platform_common.languages(code),
    
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
    sync_version INTEGER DEFAULT 1,
    last_synced_at TIMESTAMPTZ,
    added_by UUID REFERENCES users(id),
    added_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_progress CHECK (translation_progress >= 0 AND translation_progress <= 100),
    CONSTRAINT valid_quality_threshold CHECK (translation_quality_threshold >= 0 AND translation_quality_threshold <= 1),
    CONSTRAINT one_default_language UNIQUE (is_default) WHERE is_default = true
);
```

## Sync Mechanism Design

### Sync Configuration Table

```sql
CREATE TABLE reference_sync_config (
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
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Sync History Table

```sql
CREATE TABLE reference_sync_history (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    sync_type VARCHAR(20) NOT NULL,
    sync_action VARCHAR(20) NOT NULL,           -- 'added', 'updated', 'removed'
    reference_code VARCHAR(10) NOT NULL,        -- Currency/country/language code
    changes JSONB DEFAULT '{}',                -- What changed
    sync_source VARCHAR(20) DEFAULT 'auto',    -- auto, manual, admin
    synced_by UUID REFERENCES users(id),
    synced_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Repository Pattern Examples

### Currency Repository

```python
class TenantCurrencyRepository:
    async def get_active_currencies(self, tenant_schema: str) -> List[CurrencyWithDetails]:
        """Get tenant's active currencies with master data and customizations"""
        return await self.db.fetch_all(f"""
            SELECT 
                tc.*,
                pc.name as master_name,
                pc.symbol as master_symbol,
                pc.minor_unit as master_minor_unit,
                COALESCE(tc.custom_name, pc.name) as display_name,
                COALESCE(tc.custom_symbol, pc.symbol) as display_symbol,
                COALESCE(tc.decimal_places, pc.minor_unit) as decimal_places
            FROM {tenant_schema}.currencies tc
            JOIN platform_common.currencies pc ON tc.code = pc.code
            WHERE tc.is_active = true AND pc.status = 'active'
            ORDER BY tc.sort_order, display_name
        """)
    
    async def sync_from_master(self, tenant_schema: str, region_filter: str = None):
        """Sync new currencies from master data with smart defaults"""
        # Implementation for syncing master data to tenant
        pass
    
    async def update_exchange_rates(self, tenant_schema: str, provider: str = "manual"):
        """Update exchange rates from external provider or manual input"""
        # Implementation for rate updates
        pass
```

## Admin UI Configuration

### Currency Management Screen

```javascript
// Tenant currency configuration interface
const CurrencyConfig = {
  // Enable/disable currencies
  toggleCurrency: (code) => {},
  
  // Set default currency
  setDefaultCurrency: (code) => {},
  
  // Customize display
  updateDisplaySettings: (code, settings) => {},
  
  // Manage exchange rates
  updateExchangeRate: (code, rate, source) => {},
  
  // Bulk operations
  enableRegionCurrencies: (region) => {},
  disableCryptocurrencies: () => {},
  
  // Sync operations
  syncFromMaster: () => {},
  checkForUpdates: () => {}
};
```

## Benefits Summary

1. **Simplified Master Data**: Fast sync, minimal storage, ISO compliance
2. **Rich Tenant Customization**: Business-specific formatting, rates, rules
3. **Performance Optimized**: Small tenant tables, focused queries
4. **Business Logic Ready**: Exchange rates, tax integration, compliance
5. **Admin Friendly**: Easy configuration, bulk operations, sync control
6. **Audit Compliant**: Full change history, sync tracking

## Migration Strategy

1. **Phase 1**: Deploy simplified V0002 master data
2. **Phase 2**: Add tenant customization tables to tenant_template
3. **Phase 3**: Implement sync mechanism and admin UI
4. **Phase 4**: Migrate existing tenants with smart defaults

This design provides the flexibility of rich customization while maintaining the simplicity and performance of centralized master data.