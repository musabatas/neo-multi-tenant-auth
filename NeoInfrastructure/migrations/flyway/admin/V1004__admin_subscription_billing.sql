-- V005: Admin Subscription and Billing System
-- Creates comprehensive subscription, billing, and payment tables
-- Applied to: Admin database only

-- ============================================================================
-- SUBSCRIPTION PLANS (Available plans for tenants)
-- ============================================================================

CREATE TABLE admin.subscription_plans (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    price_monthly_cents BIGINT NOT NULL,
    price_yearly_cents BIGINT NOT NULL,
    price_precision SMALLINT DEFAULT 2 
        CONSTRAINT valid_price_precision CHECK (price_precision >= 0 AND price_precision <= 8),
    currency CHAR(3) DEFAULT 'USD',
    plan_tier admin.plan_tier NOT NULL,
    is_public BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    is_legacy BOOLEAN DEFAULT false,
    trial_days INTEGER DEFAULT 0 
        CONSTRAINT valid_trial_days CHECK (trial_days >= 0 AND trial_days <= 365),
    features JSONB DEFAULT '{}',
    feature_limits JSONB DEFAULT '{}',
    marketing_highlight VARCHAR(100),
    sort_order INTEGER DEFAULT 0,
    billing_description VARCHAR(255),
    available_from DATE,
    available_until DATE,
    deprecated_at TIMESTAMPTZ,
    replacement_plan_id UUID REFERENCES admin.subscription_plans,
    setup_fee_cents BIGINT DEFAULT 0,
    cancellation_fee_cents BIGINT DEFAULT 0,
    overage_pricing JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT positive_pricing CHECK (
        price_monthly_cents >= 0 AND 
        price_yearly_cents >= 0 AND 
        setup_fee_cents >= 0 AND 
        cancellation_fee_cents >= 0
    )
);

-- Indexes for subscription_plans
CREATE INDEX idx_subscription_plans_code ON admin.subscription_plans(code);
CREATE INDEX idx_subscription_plans_tier ON admin.subscription_plans(plan_tier);
CREATE INDEX idx_subscription_plans_active ON admin.subscription_plans(is_active);
CREATE INDEX idx_subscription_plans_public ON admin.subscription_plans(is_public);

-- ============================================================================
-- PLAN QUOTAS (Quota definitions per plan)
-- ============================================================================

CREATE TABLE admin.plan_quotas (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    plan_id UUID NOT NULL REFERENCES admin.subscription_plans ON DELETE CASCADE,
    quota_type VARCHAR(50) NOT NULL,
    quota_value NUMERIC(15,2) NOT NULL 
        CONSTRAINT positive_quota CHECK (quota_value >= 0),
    is_unlimited BOOLEAN DEFAULT false,
    allows_overage BOOLEAN DEFAULT false,
    overage_price_per_unit_cents BIGINT DEFAULT 0 
        CONSTRAINT valid_overage_price CHECK (overage_price_per_unit_cents >= 0),
    overage_price_precision SMALLINT DEFAULT 4 
        CONSTRAINT valid_overage_precision CHECK (overage_price_precision >= 0 AND overage_price_precision <= 8),
    overage_free_tier NUMERIC(10,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(plan_id, quota_type)
);

-- Indexes for plan_quotas
CREATE INDEX idx_plan_quotas_plan ON admin.plan_quotas(plan_id);
CREATE INDEX idx_plan_quotas_type ON admin.plan_quotas(quota_type);

-- ============================================================================
-- TENANT SUBSCRIPTIONS (Active subscriptions)
-- ============================================================================

CREATE TABLE admin.tenant_subscriptions (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    tenant_id UUID NOT NULL REFERENCES admin.tenants,
    plan_id UUID NOT NULL REFERENCES admin.subscription_plans,
    external_subscription_id VARCHAR(255),
    status admin.subscription_status DEFAULT 'trial',
    billing_cycle admin.billing_cycle NOT NULL,
    current_period_start DATE NOT NULL,
    current_period_end DATE NOT NULL,
    trial_start DATE,
    trial_end DATE,
    trial_extended_days INTEGER DEFAULT 0 
        CONSTRAINT valid_trial_extension CHECK (trial_extended_days >= 0),
    auto_renew BOOLEAN DEFAULT true,
    payment_method_id VARCHAR(255),
    next_billing_date DATE,
    price_cents BIGINT NOT NULL 
        CONSTRAINT positive_subscription_price CHECK (price_cents >= 0),
    currency CHAR(3) DEFAULT 'USD',
    discount_percentage NUMERIC(5,2) DEFAULT 0 
        CONSTRAINT valid_discount CHECK (discount_percentage >= 0 AND discount_percentage <= 100),
    custom_pricing BOOLEAN DEFAULT false,
    subscribed_at TIMESTAMPTZ DEFAULT NOW(),
    activated_at TIMESTAMPTZ,
    canceled_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    suspended_at TIMESTAMPTZ,
    cancellation_reason VARCHAR(100),
    cancellation_feedback TEXT,
    canceled_by UUID REFERENCES admin.users,
    last_billing_at TIMESTAMPTZ,
    next_renewal_notification_sent_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Indexes for tenant_subscriptions
CREATE INDEX idx_tenant_subscriptions_tenant ON admin.tenant_subscriptions(tenant_id);
CREATE INDEX idx_tenant_subscriptions_plan ON admin.tenant_subscriptions(plan_id);
CREATE INDEX idx_tenant_subscriptions_status ON admin.tenant_subscriptions(status);
CREATE INDEX idx_tenant_subscriptions_billing_cycle ON admin.tenant_subscriptions(billing_cycle);
CREATE INDEX idx_tenant_subscriptions_external ON admin.tenant_subscriptions(external_subscription_id);

-- ============================================================================
-- SUBSCRIPTION ADDONS (Additional features/quotas)
-- ============================================================================

CREATE TABLE admin.subscription_addons (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    subscription_id UUID NOT NULL REFERENCES admin.tenant_subscriptions ON DELETE CASCADE,
    addon_name VARCHAR(100) NOT NULL,
    addon_description TEXT,
    addon_type VARCHAR(50) NOT NULL,
    price_cents BIGINT NOT NULL 
        CONSTRAINT positive_addon_price CHECK (price_cents >= 0),
    price_precision SMALLINT DEFAULT 2 
        CONSTRAINT valid_addon_precision CHECK (price_precision >= 0 AND price_precision <= 8),
    currency CHAR(3) DEFAULT 'USD',
    billing_cycle admin.billing_cycle NOT NULL,
    quota_additions JSONB DEFAULT '{}',
    feature_additions JSONB DEFAULT '{}',
    added_at TIMESTAMPTZ DEFAULT NOW(),
    removed_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true
);

-- Indexes for subscription_addons
CREATE INDEX idx_subscription_addons_subscription ON admin.subscription_addons(subscription_id);
CREATE INDEX idx_subscription_addons_active ON admin.subscription_addons(is_active);

-- ============================================================================
-- INVOICES (Detailed billing)
-- ============================================================================

CREATE TABLE admin.invoices (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    tenant_id UUID NOT NULL REFERENCES admin.tenants,
    subscription_id UUID REFERENCES admin.tenant_subscriptions,
    invoice_number VARCHAR(50) NOT NULL UNIQUE,
    external_invoice_id VARCHAR(255),
    invoice_type VARCHAR(30) DEFAULT 'subscription',
    billing_reason VARCHAR(50),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    subtotal_cents BIGINT NOT NULL,
    tax_cents BIGINT DEFAULT 0,
    discount_cents BIGINT DEFAULT 0,
    total_cents BIGINT NOT NULL,
    currency CHAR(3) DEFAULT 'USD',
    tax_rate NUMERIC(5,4) DEFAULT 0 
        CONSTRAINT valid_tax_rate CHECK (tax_rate >= 0 AND tax_rate <= 1),
    tax_description VARCHAR(100),
    tax_jurisdiction VARCHAR(100),
    status admin.invoice_status DEFAULT 'draft',
    issued_at TIMESTAMPTZ,
    due_at TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    voided_at TIMESTAMPTZ,
    payment_method VARCHAR(50),
    payment_intent_id VARCHAR(255),
    payment_processor VARCHAR(30) DEFAULT 'stripe',
    failure_reason VARCHAR(255),
    retry_count INTEGER DEFAULT 0 
        CONSTRAINT valid_retry_count CHECK (retry_count >= 0),
    collection_method VARCHAR(20) DEFAULT 'charge_automatically' 
        CONSTRAINT valid_collection_method CHECK (collection_method IN ('charge_automatically', 'send_invoice')),
    days_until_due INTEGER DEFAULT 30,
    customer_notes TEXT,
    internal_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT positive_invoice_amounts CHECK (
        subtotal_cents >= 0 AND 
        total_cents >= 0 AND 
        tax_cents >= 0 AND 
        discount_cents >= 0
    )
);

-- Indexes for invoices
CREATE INDEX idx_invoices_tenant ON admin.invoices(tenant_id);
CREATE INDEX idx_invoices_subscription ON admin.invoices(subscription_id);
CREATE INDEX idx_invoices_number ON admin.invoices(invoice_number);
CREATE INDEX idx_invoices_status ON admin.invoices(status);
CREATE INDEX idx_invoices_external ON admin.invoices(external_invoice_id);
CREATE INDEX idx_invoices_period ON admin.invoices(period_start, period_end);

-- ============================================================================
-- INVOICE LINE ITEMS (Line-by-line billing details)
-- ============================================================================

CREATE TABLE admin.invoice_line_items (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    invoice_id UUID NOT NULL REFERENCES admin.invoices ON DELETE CASCADE,
    description VARCHAR(255) NOT NULL,
    detailed_description TEXT,
    quantity NUMERIC(10,2) DEFAULT 1,
    unit_price_cents BIGINT NOT NULL,
    total_cents BIGINT NOT NULL,
    price_precision SMALLINT DEFAULT 2 
        CONSTRAINT valid_line_item_precision CHECK (price_precision >= 0 AND price_precision <= 8),
    item_type admin.line_item_type NOT NULL,
    product_code VARCHAR(50),
    sku VARCHAR(100),
    period_start DATE,
    period_end DATE,
    is_prorated BOOLEAN DEFAULT false,
    proration_details JSONB DEFAULT '{}',
    taxable BOOLEAN DEFAULT true,
    tax_amount_cents BIGINT DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT positive_line_item_amounts CHECK (
        quantity > 0 AND 
        unit_price_cents >= 0 AND 
        total_cents >= 0 AND 
        tax_amount_cents >= 0
    )
);

-- Indexes for invoice_line_items
CREATE INDEX idx_invoice_line_items_invoice ON admin.invoice_line_items(invoice_id);
CREATE INDEX idx_invoice_line_items_type ON admin.invoice_line_items(item_type);
CREATE INDEX idx_invoice_line_items_product ON admin.invoice_line_items(product_code);

-- ============================================================================
-- PAYMENT TRANSACTIONS (Payment processing)
-- ============================================================================

CREATE TABLE admin.payment_transactions (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    tenant_id UUID NOT NULL REFERENCES admin.tenants,
    invoice_id UUID REFERENCES admin.invoices,
    transaction_id VARCHAR(255) NOT NULL UNIQUE,
    external_reference VARCHAR(255),
    transaction_type VARCHAR(30) NOT NULL 
        CONSTRAINT valid_transaction_type CHECK (transaction_type IN ('payment', 'refund', 'chargeback', 'fee', 'payout')),
    amount_cents BIGINT NOT NULL,
    currency CHAR(3) DEFAULT 'USD',
    payment_method_type VARCHAR(30),
    payment_method_details JSONB DEFAULT '{}',
    status VARCHAR(30) NOT NULL 
        CONSTRAINT valid_transaction_status CHECK (status IN ('pending', 'succeeded', 'failed', 'canceled', 'refunded')),
    failure_reason VARCHAR(255),
    processor VARCHAR(30) DEFAULT 'stripe',
    processor_fee_cents BIGINT DEFAULT 0,
    net_amount_cents BIGINT,
    processed_at TIMESTAMPTZ,
    settled_at TIMESTAMPTZ,
    parent_transaction_id UUID REFERENCES admin.payment_transactions,
    refund_amount_cents BIGINT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT positive_transaction_amounts CHECK (
        amount_cents >= 0 AND 
        processor_fee_cents >= 0 AND 
        refund_amount_cents >= 0
    )
);

-- Indexes for payment_transactions
CREATE INDEX idx_payment_transactions_tenant ON admin.payment_transactions(tenant_id);
CREATE INDEX idx_payment_transactions_invoice ON admin.payment_transactions(invoice_id);
CREATE INDEX idx_payment_transactions_transaction_id ON admin.payment_transactions(transaction_id);
CREATE INDEX idx_payment_transactions_status ON admin.payment_transactions(status);
CREATE INDEX idx_payment_transactions_type ON admin.payment_transactions(transaction_type);

-- ============================================================================
-- BILLING ALERTS (Billing-related notifications)
-- ============================================================================

CREATE TABLE admin.billing_alerts (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    tenant_id UUID NOT NULL REFERENCES admin.tenants,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) DEFAULT 'medium' 
        CONSTRAINT valid_alert_severity CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    related_invoice_id UUID REFERENCES admin.invoices,
    related_subscription_id UUID REFERENCES admin.tenant_subscriptions,
    is_resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES admin.users,
    notification_sent BOOLEAN DEFAULT false,
    notification_sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for billing_alerts
CREATE INDEX idx_billing_alerts_tenant ON admin.billing_alerts(tenant_id);
CREATE INDEX idx_billing_alerts_type ON admin.billing_alerts(alert_type);
CREATE INDEX idx_billing_alerts_severity ON admin.billing_alerts(severity);
CREATE INDEX idx_billing_alerts_resolved ON admin.billing_alerts(is_resolved);

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================

CREATE TRIGGER update_subscription_plans_updated_at
    BEFORE UPDATE ON admin.subscription_plans
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_plan_quotas_updated_at
    BEFORE UPDATE ON admin.plan_quotas
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_tenant_subscriptions_updated_at
    BEFORE UPDATE ON admin.tenant_subscriptions
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_invoices_updated_at
    BEFORE UPDATE ON admin.invoices
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_payment_transactions_updated_at
    BEFORE UPDATE ON admin.payment_transactions
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE admin.subscription_plans IS 'Available subscription plans with pricing and features';
COMMENT ON TABLE admin.plan_quotas IS 'Quota definitions and limits for each subscription plan';
COMMENT ON TABLE admin.tenant_subscriptions IS 'Active tenant subscriptions and billing information';
COMMENT ON TABLE admin.subscription_addons IS 'Additional features or quotas added to subscriptions';
COMMENT ON TABLE admin.invoices IS 'Detailed billing invoices for tenant subscriptions';
COMMENT ON TABLE admin.invoice_line_items IS 'Line-by-line details for invoice items';
COMMENT ON TABLE admin.payment_transactions IS 'Payment processing and transaction records';
COMMENT ON TABLE admin.billing_alerts IS 'Billing-related alerts and notifications';

-- Log migration completion
SELECT 'V005: Admin subscription and billing system created' as migration_status;