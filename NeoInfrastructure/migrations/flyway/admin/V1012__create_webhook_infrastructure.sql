-- =====================================================================================
-- Migration: V1012__Create_webhook_infrastructure.sql
-- Description: Create comprehensive webhook infrastructure for admin schema
-- Schema: admin
-- Features: Enterprise webhook system 
-- =====================================================================================

-- =====================================================================================
-- WEBHOOK ENDPOINTS TABLE
-- Stores webhook endpoint configurations for admin platform operations
-- =====================================================================================
CREATE TABLE IF NOT EXISTS admin.webhook_endpoints (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    
    -- Identification and naming
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Endpoint configuration
    endpoint_url TEXT NOT NULL,
    http_method VARCHAR(10) NOT NULL DEFAULT 'POST',
    
    -- Authentication and security
    secret_token VARCHAR(512) NOT NULL, -- Custom HMAC secret
    signature_header VARCHAR(100) NOT NULL DEFAULT 'X-Webhook-Signature',
    
    -- Custom headers (JSONB for flexibility)
    custom_headers JSONB NOT NULL DEFAULT '{}',
    
    -- Configuration options
    timeout_seconds INTEGER NOT NULL DEFAULT 30,
    follow_redirects BOOLEAN NOT NULL DEFAULT false,
    verify_ssl BOOLEAN NOT NULL DEFAULT true,
    
    -- Retry configuration
    max_retry_attempts INTEGER NOT NULL DEFAULT 3,
    retry_backoff_seconds INTEGER NOT NULL DEFAULT 5,
    retry_backoff_multiplier DECIMAL(3,2) NOT NULL DEFAULT 2.0,
    
    -- Status and lifecycle
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_verified BOOLEAN NOT NULL DEFAULT false, -- Endpoint verification status
    
    -- Generic context
    created_by_user_id UUID NOT NULL, -- User who created this webhook
    context_id UUID, -- Generic context (organization_id, team_id, etc.)
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    verified_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT valid_http_method CHECK (http_method IN ('POST', 'PUT', 'PATCH')),
    CONSTRAINT valid_timeout CHECK (timeout_seconds BETWEEN 5 AND 300),
    CONSTRAINT valid_retry_attempts CHECK (max_retry_attempts BETWEEN 0 AND 10),
    CONSTRAINT valid_backoff CHECK (retry_backoff_seconds BETWEEN 1 AND 3600),
    CONSTRAINT valid_multiplier CHECK (retry_backoff_multiplier BETWEEN 1.0 AND 5.0)
);

-- =====================================================================================
-- WEBHOOK EVENT TYPES TABLE  
-- Defines available event types for the platform
-- =====================================================================================
CREATE TABLE IF NOT EXISTS admin.webhook_event_types (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    
    -- Event identification
    event_type VARCHAR(255) NOT NULL UNIQUE, -- e.g., 'organization.created', 'user.updated'
    category VARCHAR(100) NOT NULL, -- e.g., 'organization', 'user', 'tenant'
    
    -- Event metadata
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Event configuration
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    requires_verification BOOLEAN NOT NULL DEFAULT false, -- Some events need verified endpoints
    
    -- Payload schema (for documentation/validation)
    payload_schema JSONB,
    example_payload JSONB,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================================================
-- WEBHOOK EVENT SUBSCRIPTIONS TABLE (Legacy compatibility)
-- Maps which endpoints subscribe to which event types (simple version)
-- =====================================================================================
CREATE TABLE IF NOT EXISTS admin.webhook_event_subscriptions (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    
    -- Foreign keys
    webhook_endpoint_id UUID NOT NULL REFERENCES admin.webhook_endpoints(id) ON DELETE CASCADE,
    event_type_id UUID NOT NULL REFERENCES admin.webhook_event_types(id) ON DELETE CASCADE,
    
    -- Subscription configuration
    is_active BOOLEAN NOT NULL DEFAULT true,
    
    -- Event filtering (optional JSONB filters)
    event_filters JSONB NOT NULL DEFAULT '{}', -- e.g., {"organization_id": "uuid", "status": "active"}
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Unique constraint
    UNIQUE(webhook_endpoint_id, event_type_id)
);

-- =====================================================================================
-- DETAILED WEBHOOK SUBSCRIPTIONS TABLE (New comprehensive version)
-- Advanced subscription management with full filtering capabilities
-- =====================================================================================
CREATE TABLE IF NOT EXISTS admin.webhook_subscriptions (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    
    -- Subscription identification
    endpoint_id UUID NOT NULL REFERENCES admin.webhook_endpoints(id) ON DELETE CASCADE,
    event_type_id UUID NOT NULL REFERENCES admin.webhook_event_types(id) ON DELETE CASCADE,
    
    -- Subscription configuration
    event_type VARCHAR(255) NOT NULL, -- Denormalized for performance (e.g., 'organization.created')
    event_filters JSONB NOT NULL DEFAULT '{}', -- Advanced filtering with operators
    is_active BOOLEAN NOT NULL DEFAULT true,
    
    -- Context information
    context_id UUID, -- Optional context restriction
    
    -- Subscription metadata
    subscription_name VARCHAR(255), -- Optional human-readable name
    description TEXT, -- Optional description
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_triggered_at TIMESTAMPTZ -- Last time this subscription was matched
);

-- =====================================================================================
-- WEBHOOK EVENTS TABLE
-- Audit trail and event log for all webhook events
-- =====================================================================================
CREATE TABLE IF NOT EXISTS admin.webhook_events (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    
    -- Event identification
    event_type VARCHAR(255) NOT NULL, -- Denormalized for performance
    event_name VARCHAR(255), -- Human readable name
    
    -- Event source
    aggregate_id UUID NOT NULL, -- ID of the entity that triggered the event
    aggregate_type VARCHAR(100) NOT NULL, -- Type of entity (organization, user, etc.)
    aggregate_version INTEGER NOT NULL DEFAULT 1, -- Entity version for event ordering
    
    -- Event data
    event_data JSONB NOT NULL DEFAULT '{}', -- Main event payload
    event_metadata JSONB NOT NULL DEFAULT '{}', -- Context (user_id, ip, source, etc.)
    
    -- Event context
    correlation_id UUID, -- For tracking related events
    causation_id UUID, -- The event that caused this event
    
    -- Generic context
    triggered_by_user_id UUID, -- User who triggered this event
    context_id UUID, -- Generic context (organization_id, team_id, etc.)
    
    -- Event lifecycle
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ, -- When webhook processing started
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================================================
-- WEBHOOK DELIVERIES TABLE
-- Tracks webhook delivery attempts and results for debugging
-- =====================================================================================
CREATE TABLE IF NOT EXISTS admin.webhook_deliveries (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    
    -- Foreign keys
    webhook_endpoint_id UUID NOT NULL REFERENCES admin.webhook_endpoints(id) ON DELETE CASCADE,
    webhook_event_id UUID NOT NULL REFERENCES admin.webhook_events(id) ON DELETE CASCADE,
    
    -- Delivery attempt
    attempt_number INTEGER NOT NULL DEFAULT 1,
    delivery_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    
    -- Request details
    request_url TEXT NOT NULL,
    request_method VARCHAR(10) NOT NULL,
    request_headers JSONB NOT NULL DEFAULT '{}',
    request_body TEXT,
    request_signature VARCHAR(255), -- HMAC signature sent
    
    -- Response details
    response_status_code INTEGER,
    response_headers JSONB,
    response_body TEXT,
    response_time_ms INTEGER,
    
    -- Error handling
    error_message TEXT,
    error_code VARCHAR(100),
    
    -- Retry information
    next_retry_at TIMESTAMPTZ,
    max_attempts_reached BOOLEAN NOT NULL DEFAULT false,
    
    -- Timestamps
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_delivery_status CHECK (
        delivery_status IN ('pending', 'success', 'failed', 'timeout', 'retrying', 'cancelled')
    ),
    CONSTRAINT valid_attempt_number CHECK (attempt_number >= 1)
);

-- =====================================================================================
-- WEBHOOK DELIVERY STATS TABLE (Optional - for performance monitoring)
-- Aggregated statistics for webhook endpoint performance
-- =====================================================================================
CREATE TABLE IF NOT EXISTS admin.webhook_delivery_stats (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    webhook_endpoint_id UUID NOT NULL REFERENCES admin.webhook_endpoints(id) ON DELETE CASCADE,
    
    -- Time period (daily stats)
    date_recorded DATE NOT NULL,
    
    -- Delivery metrics
    total_attempts INTEGER NOT NULL DEFAULT 0,
    successful_deliveries INTEGER NOT NULL DEFAULT 0,
    failed_deliveries INTEGER NOT NULL DEFAULT 0,
    timeout_deliveries INTEGER NOT NULL DEFAULT 0,
    
    -- Performance metrics
    avg_response_time_ms INTEGER,
    min_response_time_ms INTEGER,
    max_response_time_ms INTEGER,
    
    -- Error statistics
    most_common_error_code VARCHAR(100),
    error_rate DECIMAL(5,2), -- Percentage
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Unique constraint for daily stats
    UNIQUE(webhook_endpoint_id, date_recorded)
);

-- =====================================================================================
-- SEED INITIAL EVENT TYPES
-- Common platform events that admins might want to subscribe to
-- =====================================================================================
INSERT INTO admin.webhook_event_types (event_type, category, display_name, description, payload_schema) VALUES
-- Organization events
('organization.created', 'organization', 'Organization Created', 'Triggered when a new organization is created', '{"type": "object", "properties": {"organization": {"type": "object"}}}'),
('organization.updated', 'organization', 'Organization Updated', 'Triggered when an organization is updated', '{"type": "object", "properties": {"organization": {"type": "object"}, "changes": {"type": "object"}}}'),
('organization.verified', 'organization', 'Organization Verified', 'Triggered when an organization is verified', '{"type": "object", "properties": {"organization": {"type": "object"}}}'),
('organization.deactivated', 'organization', 'Organization Deactivated', 'Triggered when an organization is deactivated', '{"type": "object", "properties": {"organization": {"type": "object"}, "reason": {"type": "string"}}}'),

-- Tenant events  
('tenant.created', 'tenant', 'Tenant Created', 'Triggered when a new tenant is created', '{"type": "object", "properties": {"tenant": {"type": "object"}}}'),
('tenant.subscription_changed', 'tenant', 'Tenant Subscription Changed', 'Triggered when tenant subscription is modified', '{"type": "object", "properties": {"tenant": {"type": "object"}, "old_plan": {"type": "object"}, "new_plan": {"type": "object"}}}'),
('tenant.suspended', 'tenant', 'Tenant Suspended', 'Triggered when a tenant is suspended', '{"type": "object", "properties": {"tenant": {"type": "object"}, "reason": {"type": "string"}}}'),

-- User events
('user.created', 'user', 'User Created', 'Triggered when a new platform user is created', '{"type": "object", "properties": {"user": {"type": "object"}}}'),
('user.role_changed', 'user', 'User Role Changed', 'Triggered when a user role is modified', '{"type": "object", "properties": {"user": {"type": "object"}, "old_roles": {"type": "array"}, "new_roles": {"type": "array"}}}'),

-- System events
('system.maintenance_scheduled', 'system', 'Maintenance Scheduled', 'Triggered when system maintenance is scheduled', '{"type": "object", "properties": {"maintenance": {"type": "object"}}}'),
('system.backup_completed', 'system', 'Backup Completed', 'Triggered when system backup is completed', '{"type": "object", "properties": {"backup": {"type": "object"}}}')

ON CONFLICT (event_type) DO NOTHING;

-- =====================================================================================
-- TRIGGERS FOR AUTOMATIC TIMESTAMPS
-- Using existing platform_common.update_updated_at_column() function
-- =====================================================================================

-- Webhook endpoints updated_at trigger
CREATE TRIGGER trigger_webhook_endpoints_updated_at
    BEFORE UPDATE ON admin.webhook_endpoints
    FOR EACH ROW
    EXECUTE FUNCTION platform_common.update_updated_at_column();

-- Webhook event types updated_at trigger
CREATE TRIGGER trigger_webhook_event_types_updated_at
    BEFORE UPDATE ON admin.webhook_event_types
    FOR EACH ROW
    EXECUTE FUNCTION platform_common.update_updated_at_column();

-- Webhook subscriptions updated_at trigger (legacy)
CREATE TRIGGER trigger_webhook_event_subscriptions_updated_at
    BEFORE UPDATE ON admin.webhook_event_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION platform_common.update_updated_at_column();

-- Webhook subscriptions updated_at trigger (detailed)
CREATE TRIGGER trigger_webhook_subscriptions_updated_at
    BEFORE UPDATE ON admin.webhook_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION platform_common.update_updated_at_column();

-- Webhook delivery stats updated_at trigger  
CREATE TRIGGER trigger_webhook_delivery_stats_updated_at
    BEFORE UPDATE ON admin.webhook_delivery_stats
    FOR EACH ROW
    EXECUTE FUNCTION platform_common.update_updated_at_column();

-- =====================================================================================
-- HELPER FUNCTIONS
-- =====================================================================================
-- Function to generate webhook signature (HMAC-SHA256)
CREATE OR REPLACE FUNCTION admin.generate_webhook_signature(
    payload TEXT,
    secret TEXT,
    algorithm VARCHAR DEFAULT 'sha256'
)
RETURNS VARCHAR AS $$
BEGIN
    -- This would typically be implemented in application code
    -- Placeholder for webhook signature generation
    RETURN 'sha256=' || encode(hmac(payload, secret, algorithm), 'hex');
END;
$$ LANGUAGE plpgsql;

-- Function to validate webhook endpoint URL
CREATE OR REPLACE FUNCTION admin.validate_webhook_url(url TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    -- Basic URL validation
    RETURN url ~ '^https?://[^\s/$.?#].[^\s]*$';
END;
$$ LANGUAGE plpgsql;

-- =====================================================================================
-- COMMENTS FOR DOCUMENTATION
-- =====================================================================================
COMMENT ON TABLE admin.webhook_endpoints IS 'Webhook endpoint configurations for admin platform operations';
COMMENT ON TABLE admin.webhook_event_types IS 'Defines available event types for platform webhooks';
COMMENT ON TABLE admin.webhook_event_subscriptions IS 'Legacy webhook subscriptions (simple mapping)';
COMMENT ON TABLE admin.webhook_subscriptions IS 'Advanced webhook subscriptions with detailed filtering';
COMMENT ON TABLE admin.webhook_events IS 'Audit trail and event log for all platform webhook events';
COMMENT ON TABLE admin.webhook_deliveries IS 'Tracks webhook delivery attempts and results';
COMMENT ON TABLE admin.webhook_delivery_stats IS 'Aggregated webhook delivery statistics for monitoring';

-- =====================================================================================
-- EVENT ARCHIVAL TABLES
-- Long-term event storage and management for scalability
-- =====================================================================================

-- Event Archives Table
CREATE TABLE IF NOT EXISTS admin.event_archives (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    
    -- Archive identification
    archive_name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Archival configuration
    policy VARCHAR(50) NOT NULL CHECK (policy IN ('age_based', 'size_based', 'hybrid', 'custom')),
    storage_type VARCHAR(50) NOT NULL CHECK (storage_type IN ('database_partition', 'cold_storage', 'compressed_archive', 'data_warehouse')),
    storage_location TEXT NOT NULL,
    
    -- Archive status and lifecycle
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_at TIMESTAMPTZ,
    restored_at TIMESTAMPTZ,
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'restored')),
    
    -- Archive statistics
    event_count INTEGER NOT NULL DEFAULT 0 CHECK (event_count >= 0),
    size_bytes BIGINT NOT NULL DEFAULT 0 CHECK (size_bytes >= 0),
    compression_ratio DECIMAL(5,4) CHECK (compression_ratio BETWEEN 0 AND 1),
    checksum VARCHAR(128),
    
    -- Time range of archived events
    events_from TIMESTAMPTZ NOT NULL,
    events_to TIMESTAMPTZ NOT NULL,
    
    -- Context information
    context_ids UUID[] NOT NULL DEFAULT '{}',
    event_types TEXT[] NOT NULL DEFAULT '{}',
    
    -- Retention policies
    retention_days INTEGER CHECK (retention_days > 0),
    auto_delete_after_days INTEGER CHECK (auto_delete_after_days > 0),
    
    -- Metadata
    created_by_user_id UUID NOT NULL,
    tags JSONB NOT NULL DEFAULT '{}',
    
    -- Constraints
    CONSTRAINT valid_date_range CHECK (events_from < events_to)
);

-- Archival Rules Table
CREATE TABLE IF NOT EXISTS admin.archival_rules (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    
    -- Rule identification
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    
    -- Archival policy configuration
    policy VARCHAR(50) NOT NULL CHECK (policy IN ('age_based', 'size_based', 'hybrid', 'custom')),
    storage_type VARCHAR(50) NOT NULL CHECK (storage_type IN ('database_partition', 'cold_storage', 'compressed_archive', 'data_warehouse')),
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    
    -- Age-based rules
    archive_after_days INTEGER CHECK (archive_after_days > 0),
    
    -- Size-based rules  
    max_table_size_gb DECIMAL(10,2) CHECK (max_table_size_gb > 0),
    max_event_count INTEGER CHECK (max_event_count > 0),
    
    -- Filtering rules
    event_types_include TEXT[] NOT NULL DEFAULT '{}',
    event_types_exclude TEXT[] NOT NULL DEFAULT '{}',
    context_ids_include UUID[] NOT NULL DEFAULT '{}',
    context_ids_exclude UUID[] NOT NULL DEFAULT '{}',
    
    -- Scheduling configuration
    schedule_cron VARCHAR(100), -- Cron expression for scheduled execution
    next_run_at TIMESTAMPTZ,
    last_run_at TIMESTAMPTZ,
    
    -- Storage configuration
    storage_location_template TEXT NOT NULL,
    compression_enabled BOOLEAN NOT NULL DEFAULT true,
    encryption_enabled BOOLEAN NOT NULL DEFAULT false,
    
    -- Retention policies
    retention_days INTEGER CHECK (retention_days > 0),
    auto_delete_after_days INTEGER CHECK (auto_delete_after_days > 0),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_user_id UUID NOT NULL
);

-- Archival Jobs Table  
CREATE TABLE IF NOT EXISTS admin.archival_jobs (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    
    -- Job relationships
    rule_id UUID NOT NULL REFERENCES admin.archival_rules(id) ON DELETE CASCADE,
    archive_id UUID REFERENCES admin.event_archives(id) ON DELETE SET NULL,
    
    -- Job status
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'restored')),
    
    -- Job execution details
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Processing statistics
    events_processed INTEGER NOT NULL DEFAULT 0 CHECK (events_processed >= 0),
    events_archived INTEGER NOT NULL DEFAULT 0 CHECK (events_archived >= 0), 
    events_skipped INTEGER NOT NULL DEFAULT 0 CHECK (events_skipped >= 0),
    
    -- Performance metrics
    processing_time_seconds DECIMAL(10,3),
    throughput_events_per_second DECIMAL(10,2),
    
    -- Storage details
    storage_location TEXT,
    compressed_size_bytes BIGINT,
    uncompressed_size_bytes BIGINT,
    
    -- Error handling
    error_message TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
    max_retries INTEGER NOT NULL DEFAULT 3 CHECK (max_retries >= 0),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_retry_count CHECK (retry_count <= max_retries),
    CONSTRAINT valid_processing_stats CHECK (events_archived <= events_processed)
);

-- =====================================================================================
-- ARCHIVAL TRIGGERS
-- =====================================================================================

-- Update triggers for archival tables
CREATE TRIGGER trigger_event_archives_updated_at
    BEFORE UPDATE ON admin.event_archives
    FOR EACH ROW
    EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER trigger_archival_rules_updated_at
    BEFORE UPDATE ON admin.archival_rules
    FOR EACH ROW
    EXECUTE FUNCTION platform_common.update_updated_at_column();
    
CREATE TRIGGER trigger_archival_jobs_updated_at
    BEFORE UPDATE ON admin.archival_jobs
    FOR EACH ROW
    EXECUTE FUNCTION platform_common.update_updated_at_column();

-- =====================================================================================
-- ARCHIVAL HELPER FUNCTIONS
-- =====================================================================================

-- Function to calculate archive storage efficiency
CREATE OR REPLACE FUNCTION admin.calculate_archive_efficiency(
    archive_id UUID
)
RETURNS JSONB AS $$
DECLARE
    archive_rec admin.event_archives%ROWTYPE;
    efficiency JSONB;
BEGIN
    SELECT * INTO archive_rec FROM admin.event_archives WHERE id = archive_id;
    
    IF NOT FOUND THEN
        RETURN NULL;
    END IF;
    
    -- Calculate efficiency metrics
    efficiency := jsonb_build_object(
        'bytes_per_event', CASE WHEN archive_rec.event_count > 0 
                          THEN archive_rec.size_bytes::DECIMAL / archive_rec.event_count 
                          ELSE 0 END,
        'compression_efficiency', COALESCE(archive_rec.compression_ratio, 0),
        'storage_density', CASE WHEN archive_rec.size_bytes > 0 
                          THEN archive_rec.event_count::DECIMAL / (archive_rec.size_bytes::DECIMAL / (1024 * 1024))
                          ELSE 0 END
    );
    
    RETURN efficiency;
END;
$$ LANGUAGE plpgsql;

-- Function to get archival statistics
CREATE OR REPLACE FUNCTION admin.get_archival_statistics()
RETURNS JSONB AS $$
DECLARE
    stats JSONB;
BEGIN
    SELECT jsonb_build_object(
        'total_archives', COUNT(*),
        'total_archived_events', SUM(event_count),
        'total_storage_bytes', SUM(size_bytes),
        'avg_compression_ratio', AVG(compression_ratio),
        'completed_archives', COUNT(*) FILTER (WHERE status = 'completed'),
        'failed_archives', COUNT(*) FILTER (WHERE status = 'failed'),
        'oldest_archived_date', MIN(events_from),
        'newest_archived_date', MAX(events_to),
        'active_rules', (SELECT COUNT(*) FROM admin.archival_rules WHERE is_enabled = true),
        'running_jobs', (SELECT COUNT(*) FROM admin.archival_jobs WHERE status = 'in_progress')
    ) INTO stats
    FROM admin.event_archives;
    
    RETURN stats;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================================
-- SEED DEFAULT ARCHIVAL RULES
-- =====================================================================================
INSERT INTO admin.archival_rules (
    id, name, description, policy, storage_type, archive_after_days, 
    max_table_size_gb, storage_location_template, created_by_user_id
) VALUES (
    platform_common.uuid_generate_v7(),
    'Default Age-Based Archive',
    'Archive events older than 90 days to compressed storage',
    'age_based',
    'compressed_archive',
    90,
    NULL,
    'archives/age_based/{rule_name}_{timestamp}',
    '00000000-0000-0000-0000-000000000000'::UUID
), (
    platform_common.uuid_generate_v7(), 
    'Size-Based Archive',
    'Archive events when table exceeds 10GB',
    'size_based',
    'database_partition',
    NULL,
    10.0,
    'partitions/size_based/{rule_name}_{timestamp}',
    '00000000-0000-0000-0000-000000000000'::UUID
)
ON CONFLICT (name) DO NOTHING;

-- =====================================================================================
-- ARCHIVAL COMMENTS  
-- =====================================================================================
COMMENT ON TABLE admin.event_archives IS 'Event archives for long-term storage and scalability';
COMMENT ON TABLE admin.archival_rules IS 'Rules for automatic event archival based on age, size, or custom criteria';
COMMENT ON TABLE admin.archival_jobs IS 'Job execution tracking for archival operations';

-- =====================================================================================
-- CREATE INDEXES FOR PERFORMANCE
-- =====================================================================================

-- Webhook event types indexes
CREATE INDEX IF NOT EXISTS idx_webhook_event_types_category ON admin.webhook_event_types(category);
CREATE INDEX IF NOT EXISTS idx_webhook_event_types_enabled ON admin.webhook_event_types(is_enabled);

-- Webhook subscriptions indexes (legacy)
CREATE INDEX IF NOT EXISTS idx_webhook_subscriptions_endpoint ON admin.webhook_event_subscriptions(webhook_endpoint_id);
CREATE INDEX IF NOT EXISTS idx_webhook_subscriptions_event_type ON admin.webhook_event_subscriptions(event_type_id);
CREATE INDEX IF NOT EXISTS idx_webhook_subscriptions_active ON admin.webhook_event_subscriptions(is_active);

-- Webhook subscriptions indexes (detailed)
CREATE INDEX IF NOT EXISTS idx_webhook_subscriptions_detailed_endpoint ON admin.webhook_subscriptions(endpoint_id);
CREATE INDEX IF NOT EXISTS idx_webhook_subscriptions_detailed_event_type ON admin.webhook_subscriptions(event_type);
CREATE INDEX IF NOT EXISTS idx_webhook_subscriptions_detailed_active ON admin.webhook_subscriptions(is_active);
CREATE INDEX IF NOT EXISTS idx_webhook_subscriptions_detailed_context ON admin.webhook_subscriptions(context_id);
CREATE INDEX IF NOT EXISTS idx_webhook_subscriptions_detailed_last_triggered ON admin.webhook_subscriptions(last_triggered_at);
CREATE INDEX IF NOT EXISTS idx_webhook_subscriptions_detailed_composite ON admin.webhook_subscriptions(event_type, is_active, context_id);

-- Webhook events indexes
CREATE INDEX IF NOT EXISTS idx_webhook_events_type ON admin.webhook_events(event_type);
CREATE INDEX IF NOT EXISTS idx_webhook_events_aggregate ON admin.webhook_events(aggregate_type, aggregate_id);
CREATE INDEX IF NOT EXISTS idx_webhook_events_occurred ON admin.webhook_events(occurred_at);
CREATE INDEX IF NOT EXISTS idx_webhook_events_processed ON admin.webhook_events(processed_at);
CREATE INDEX IF NOT EXISTS idx_webhook_events_correlation ON admin.webhook_events(correlation_id);
CREATE INDEX IF NOT EXISTS idx_webhook_events_context ON admin.webhook_events(context_id);

-- Webhook deliveries indexes
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_endpoint ON admin.webhook_deliveries(webhook_endpoint_id);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_event ON admin.webhook_deliveries(webhook_event_id);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_status ON admin.webhook_deliveries(delivery_status);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_attempted ON admin.webhook_deliveries(attempted_at);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_next_retry ON admin.webhook_deliveries(next_retry_at);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_composite ON admin.webhook_deliveries(webhook_endpoint_id, delivery_status, attempted_at);

-- Webhook stats indexes
CREATE INDEX IF NOT EXISTS idx_webhook_stats_endpoint_date ON admin.webhook_delivery_stats(webhook_endpoint_id, date_recorded);
CREATE INDEX IF NOT EXISTS idx_webhook_stats_date ON admin.webhook_delivery_stats(date_recorded);

-- Event archives indexes
CREATE INDEX IF NOT EXISTS idx_event_archives_status ON admin.event_archives(status);
CREATE INDEX IF NOT EXISTS idx_event_archives_policy ON admin.event_archives(policy);
CREATE INDEX IF NOT EXISTS idx_event_archives_storage_type ON admin.event_archives(storage_type);
CREATE INDEX IF NOT EXISTS idx_event_archives_created_at ON admin.event_archives(created_at);
CREATE INDEX IF NOT EXISTS idx_event_archives_archived_at ON admin.event_archives(archived_at);
CREATE INDEX IF NOT EXISTS idx_event_archives_events_from ON admin.event_archives(events_from);
CREATE INDEX IF NOT EXISTS idx_event_archives_events_to ON admin.event_archives(events_to);
CREATE INDEX IF NOT EXISTS idx_event_archives_retention ON admin.event_archives(auto_delete_after_days, archived_at);
CREATE INDEX IF NOT EXISTS idx_event_archives_context_ids ON admin.event_archives USING GIN(context_ids);
CREATE INDEX IF NOT EXISTS idx_event_archives_event_types ON admin.event_archives USING GIN(event_types);
CREATE INDEX IF NOT EXISTS idx_event_archives_tags ON admin.event_archives USING GIN(tags);

-- Archival rules indexes
CREATE INDEX IF NOT EXISTS idx_archival_rules_enabled ON admin.archival_rules(is_enabled);
CREATE INDEX IF NOT EXISTS idx_archival_rules_policy ON admin.archival_rules(policy);
CREATE INDEX IF NOT EXISTS idx_archival_rules_next_run ON admin.archival_rules(next_run_at);
CREATE INDEX IF NOT EXISTS idx_archival_rules_last_run ON admin.archival_rules(last_run_at);
CREATE INDEX IF NOT EXISTS idx_archival_rules_event_types_include ON admin.archival_rules USING GIN(event_types_include);
CREATE INDEX IF NOT EXISTS idx_archival_rules_context_ids_include ON admin.archival_rules USING GIN(context_ids_include);

-- Archival jobs indexes
CREATE INDEX IF NOT EXISTS idx_archival_jobs_rule ON admin.archival_jobs(rule_id);
CREATE INDEX IF NOT EXISTS idx_archival_jobs_archive ON admin.archival_jobs(archive_id);
CREATE INDEX IF NOT EXISTS idx_archival_jobs_status ON admin.archival_jobs(status);
CREATE INDEX IF NOT EXISTS idx_archival_jobs_started_at ON admin.archival_jobs(started_at);
CREATE INDEX IF NOT EXISTS idx_archival_jobs_completed_at ON admin.archival_jobs(completed_at);
CREATE INDEX IF NOT EXISTS idx_archival_jobs_retry ON admin.archival_jobs(status, retry_count, max_retries);
CREATE INDEX IF NOT EXISTS idx_archival_jobs_performance ON admin.archival_jobs(throughput_events_per_second);

-- =====================================================================================
-- MIGRATION COMPLETE
-- =====================================================================================