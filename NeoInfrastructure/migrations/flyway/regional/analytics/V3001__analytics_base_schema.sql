-- V001: Analytics Base Schema
-- Creates basic analytics and reporting structure for regional databases
-- Applied to: Regional analytics databases (both US and EU)
-- Placeholders: ${region}, ${gdpr}

-- ============================================================================
-- ANALYTICS SCHEMA
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS analytics;

-- Grant usage permissions
GRANT USAGE ON SCHEMA analytics TO PUBLIC;

-- ============================================================================
-- EVENT TRACKING (Basic event logging for analytics)
-- ============================================================================

CREATE TABLE analytics.events (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    tenant_id UUID NOT NULL, -- Reference to tenant in admin database
    user_id UUID, -- Reference to user (could be platform or tenant user)
    event_type VARCHAR(100) NOT NULL,
    event_name VARCHAR(200) NOT NULL,
    event_data JSONB DEFAULT '{}',
    event_properties JSONB DEFAULT '{}',
    session_id VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    referrer VARCHAR(2048),
    page_url VARCHAR(2048),
    region VARCHAR(20) DEFAULT '${region}',
    gdpr_region BOOLEAN DEFAULT ${gdpr},
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for events
CREATE INDEX idx_analytics_events_tenant ON analytics.events(tenant_id);
CREATE INDEX idx_analytics_events_user ON analytics.events(user_id);
CREATE INDEX idx_analytics_events_type ON analytics.events(event_type);
CREATE INDEX idx_analytics_events_name ON analytics.events(event_name);
CREATE INDEX idx_analytics_events_session ON analytics.events(session_id);
CREATE INDEX idx_analytics_events_created ON analytics.events(created_at);
CREATE INDEX idx_analytics_events_properties ON analytics.events USING GIN(event_properties);

-- ============================================================================
-- USAGE METRICS (Aggregated usage data)
-- ============================================================================

CREATE TABLE analytics.usage_metrics (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    tenant_id UUID NOT NULL,
    metric_type VARCHAR(100) NOT NULL,
    metric_name VARCHAR(200) NOT NULL,
    metric_value NUMERIC(15,4) NOT NULL DEFAULT 0,
    dimensions JSONB DEFAULT '{}',
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    granularity VARCHAR(20) NOT NULL DEFAULT 'hour', -- hour, day, week, month
    region VARCHAR(20) DEFAULT '${region}',
    aggregated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for usage_metrics
CREATE INDEX idx_analytics_usage_tenant ON analytics.usage_metrics(tenant_id);
CREATE INDEX idx_analytics_usage_type ON analytics.usage_metrics(metric_type);
CREATE INDEX idx_analytics_usage_name ON analytics.usage_metrics(metric_name);
CREATE INDEX idx_analytics_usage_period ON analytics.usage_metrics(period_start, period_end);
CREATE INDEX idx_analytics_usage_granularity ON analytics.usage_metrics(granularity);
CREATE INDEX idx_analytics_usage_dimensions ON analytics.usage_metrics USING GIN(dimensions);

-- ============================================================================
-- PERFORMANCE METRICS (System performance tracking)
-- ============================================================================

CREATE TABLE analytics.performance_metrics (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    tenant_id UUID,
    metric_type VARCHAR(100) NOT NULL,
    endpoint VARCHAR(500),
    response_time_ms INTEGER,
    status_code INTEGER,
    error_message TEXT,
    request_size_bytes BIGINT,
    response_size_bytes BIGINT,
    database_query_time_ms INTEGER,
    database_query_count INTEGER,
    cache_hit BOOLEAN,
    region VARCHAR(20) DEFAULT '${region}',
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance_metrics
CREATE INDEX idx_analytics_perf_tenant ON analytics.performance_metrics(tenant_id);
CREATE INDEX idx_analytics_perf_type ON analytics.performance_metrics(metric_type);
CREATE INDEX idx_analytics_perf_endpoint ON analytics.performance_metrics(endpoint);
CREATE INDEX idx_analytics_perf_status ON analytics.performance_metrics(status_code);
CREATE INDEX idx_analytics_perf_timestamp ON analytics.performance_metrics(timestamp);

-- ============================================================================
-- DATA RETENTION POLICIES (GDPR-aware)
-- ============================================================================

-- Function to anonymize old events for GDPR compliance
CREATE OR REPLACE FUNCTION analytics.anonymize_old_events(retention_days INTEGER DEFAULT 365) 
RETURNS INTEGER 
LANGUAGE plpgsql
AS $$
DECLARE
    anonymized_count INTEGER;
    cutoff_date TIMESTAMPTZ;
BEGIN
    cutoff_date := NOW() - (retention_days || ' days')::INTERVAL;
    
    -- Only anonymize if in GDPR region
    IF ${gdpr} THEN
        UPDATE analytics.events 
        SET 
            user_id = NULL,
            ip_address = NULL,
            user_agent = 'anonymized',
            event_data = event_data - 'user_email' - 'user_name' - 'personal_data',
            event_properties = event_properties - 'email' - 'phone' - 'personal_info'
        WHERE created_at < cutoff_date 
        AND user_id IS NOT NULL;
        
        GET DIAGNOSTICS anonymized_count = ROW_COUNT;
        
        RAISE NOTICE 'Anonymized % events older than % days for GDPR compliance', anonymized_count, retention_days;
        RETURN anonymized_count;
    ELSE
        RAISE NOTICE 'GDPR anonymization skipped - not in GDPR region';
        RETURN 0;
    END IF;
END;
$$;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON SCHEMA analytics IS 'Analytics and reporting schema for region: ${region}';
COMMENT ON TABLE analytics.events IS 'Event tracking for user actions and system events';
COMMENT ON TABLE analytics.usage_metrics IS 'Aggregated usage metrics and statistics';
COMMENT ON TABLE analytics.performance_metrics IS 'System performance and response time tracking';
COMMENT ON FUNCTION analytics.anonymize_old_events IS 'GDPR-compliant data anonymization for old events';

-- ============================================================================
-- GDPR-SPECIFIC SETUP
-- ============================================================================

-- GDPR-specific tracking table (only created in EU regions)
-- Note: This will be created for both EU and US, but only actively used in EU
CREATE TABLE IF NOT EXISTS analytics.gdpr_compliance_log (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    tenant_id UUID NOT NULL,
    user_id UUID,
    action_type VARCHAR(100) NOT NULL, -- 'consent_given', 'consent_withdrawn', 'data_exported', 'data_deleted'
    action_details JSONB DEFAULT '{}',
    legal_basis VARCHAR(100),
    consent_timestamp TIMESTAMPTZ,
    data_subject_request_id UUID,
    compliance_officer UUID,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for GDPR compliance log
CREATE INDEX IF NOT EXISTS idx_analytics_gdpr_tenant ON analytics.gdpr_compliance_log(tenant_id);
CREATE INDEX IF NOT EXISTS idx_analytics_gdpr_user ON analytics.gdpr_compliance_log(user_id);
CREATE INDEX IF NOT EXISTS idx_analytics_gdpr_action ON analytics.gdpr_compliance_log(action_type);
CREATE INDEX IF NOT EXISTS idx_analytics_gdpr_created ON analytics.gdpr_compliance_log(created_at);

COMMENT ON TABLE analytics.gdpr_compliance_log IS 'GDPR compliance tracking and audit log (primarily for EU regions)';

-- Log migration completion
SELECT 'V001: Analytics base schema created for region ${region} (GDPR: ${gdpr})' as migration_status;