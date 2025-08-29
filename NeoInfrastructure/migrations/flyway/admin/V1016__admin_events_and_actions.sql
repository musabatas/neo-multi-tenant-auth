-- V1016: Admin Events and Actions Infrastructure
-- Creates comprehensive event-driven architecture for platform-wide events and actions
-- Applied to: Admin database only
-- Features: Event sourcing, action queuing, audit trails, replay support


-- ============================================================================
-- EVENTS TABLE (Event Sourcing + Audit Trail)
-- ============================================================================

CREATE TABLE admin.events (
    -- Core Identity
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    event_type VARCHAR(255) NOT NULL,           -- e.g., 'tenants.created', 'users.updated'
    aggregate_id UUID NOT NULL,                 -- ID of the entity that triggered the event
    aggregate_type VARCHAR(100) NOT NULL,       -- Type of entity (tenant, user, organization)
    
    -- Event Metadata
    event_version INTEGER DEFAULT 1,            -- Event schema version for evolution
    correlation_id UUID,                        -- Group related events together
    causation_id UUID,                         -- The event that caused this event
    
    -- Content and Context
    event_data JSONB NOT NULL DEFAULT '{}',     -- Event payload/data
    event_metadata JSONB DEFAULT '{}',          -- Additional metadata (IP, user agent, etc.)
    
    -- Processing Information
    status platform_common.event_status DEFAULT 'pending',
    priority platform_common.event_priority DEFAULT 'normal',
    scheduled_at TIMESTAMPTZ DEFAULT NOW(),     -- When event should be processed
    
    -- Performance and Monitoring
    processing_started_at TIMESTAMPTZ,
    processing_completed_at TIMESTAMPTZ,
    processing_duration_ms INTEGER,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Error Handling
    error_message TEXT,
    error_details JSONB DEFAULT '{}',
    
    -- Context Information
    tenant_id UUID,                             -- For tenant-scoped events
    organization_id UUID,                       -- For organization-scoped events
    user_id UUID,                              -- User who triggered the event
    source_service VARCHAR(100),               -- Service that created the event
    source_version VARCHAR(50),                -- Version of the source service
    
    -- Queue Integration
    queue_name VARCHAR(100),                   -- Redis stream/queue name
    message_id VARCHAR(100),                   -- Queue message identifier
    partition_key VARCHAR(100),               -- For queue partitioning
    
    -- Audit Fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT valid_retry_count CHECK (retry_count >= 0 AND retry_count <= max_retries),
    CONSTRAINT valid_processing_duration CHECK (processing_duration_ms >= 0),
    CONSTRAINT valid_event_type_format CHECK (event_type ~* '^[a-z_]+\.[a-z_]+$')
);

-- ============================================================================
-- ACTIONS TABLE (Action Definitions and Handlers)
-- ============================================================================

CREATE TABLE admin.actions (
    -- Core Identity
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    name VARCHAR(255) NOT NULL UNIQUE,          -- e.g., 'send_welcome_email', 'create_tenant_schema'
    action_type platform_common.action_type NOT NULL,
    
    -- Action Configuration
    handler_class VARCHAR(500) NOT NULL,        -- Python class path for action handler
    config JSONB DEFAULT '{}',                  -- Action-specific configuration
    
    -- Trigger Configuration
    event_patterns TEXT[] NOT NULL,             -- Event types this action responds to
    conditions JSONB DEFAULT '{}',              -- Additional trigger conditions
    
    -- Execution Settings
    is_active BOOLEAN DEFAULT true,
    priority platform_common.event_priority DEFAULT 'normal',
    timeout_seconds INTEGER DEFAULT 300,        -- 5 minutes default timeout
    retry_policy JSONB DEFAULT '{"max_retries": 3, "backoff_type": "exponential", "initial_delay_ms": 1000}',
    
    -- Resource Limits
    max_concurrent_executions INTEGER DEFAULT 1,
    rate_limit_per_minute INTEGER,              -- Rate limiting for the action
    
    -- Monitoring and Health
    is_healthy BOOLEAN DEFAULT true,
    last_health_check_at TIMESTAMPTZ,
    health_check_error TEXT,
    
    -- Statistics
    total_executions BIGINT DEFAULT 0,
    successful_executions BIGINT DEFAULT 0,
    failed_executions BIGINT DEFAULT 0,
    avg_execution_time_ms INTEGER DEFAULT 0,
    
    -- Metadata
    description TEXT,
    tags VARCHAR(50)[],
    owner_team VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    
    -- Audit Fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT valid_timeout CHECK (timeout_seconds > 0),
    CONSTRAINT valid_concurrent_executions CHECK (max_concurrent_executions > 0),
    CONSTRAINT valid_rate_limit CHECK (rate_limit_per_minute IS NULL OR rate_limit_per_minute > 0),
    CONSTRAINT valid_statistics CHECK (
        total_executions >= 0 AND 
        successful_executions >= 0 AND 
        failed_executions >= 0 AND
        (successful_executions + failed_executions) <= total_executions
    )
);

-- ============================================================================
-- ACTION_EXECUTIONS TABLE (Action Execution History)
-- ============================================================================

CREATE TABLE admin.action_executions (
    -- Core Identity
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    event_id UUID NOT NULL REFERENCES admin.events(id) ON DELETE CASCADE,
    action_id UUID NOT NULL REFERENCES admin.actions(id) ON DELETE CASCADE,
    
    -- Execution Context
    execution_context JSONB DEFAULT '{}',       -- Context passed to action handler
    input_data JSONB DEFAULT '{}',              -- Input data for the action
    output_data JSONB DEFAULT '{}',             -- Output/result data from action
    
    -- Execution Status
    status platform_common.action_status DEFAULT 'pending',
    
    -- Timing Information
    queued_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    execution_duration_ms INTEGER,
    
    -- Retry Handling
    attempt_number INTEGER DEFAULT 1,
    is_retry BOOLEAN DEFAULT false,
    parent_execution_id UUID REFERENCES admin.action_executions(id),
    
    -- Error Handling
    error_message TEXT,
    error_details JSONB DEFAULT '{}',
    error_stack_trace TEXT,
    
    -- Queue Integration
    queue_message_id VARCHAR(100),
    worker_id VARCHAR(100),                     -- Identifier of the worker that processed this
    
    -- Performance Metrics
    memory_usage_mb INTEGER,
    cpu_time_ms INTEGER,
    
    -- Audit Fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_attempt_number CHECK (attempt_number > 0),
    CONSTRAINT valid_execution_duration CHECK (execution_duration_ms >= 0),
    CONSTRAINT valid_timing CHECK (
        (started_at IS NULL OR started_at >= queued_at) AND
        (completed_at IS NULL OR completed_at >= started_at)
    )
);

-- ============================================================================
-- EVENT_SUBSCRIPTIONS TABLE (Dynamic Event-Action Mappings)
-- ============================================================================

CREATE TABLE admin.event_subscriptions (
    -- Core Identity
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    action_id UUID NOT NULL REFERENCES admin.actions(id) ON DELETE CASCADE,
    
    -- Subscription Configuration
    event_pattern VARCHAR(255) NOT NULL,        -- Event pattern to match (supports wildcards)
    conditions JSONB DEFAULT '{}',              -- Additional filtering conditions
    
    -- Subscription Settings
    is_active BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 0,                 -- Higher number = higher priority
    
    -- Filtering and Routing
    tenant_filter UUID[],                       -- Limit to specific tenants
    organization_filter UUID[],                 -- Limit to specific organizations
    source_service_filter VARCHAR(100)[],       -- Limit to specific services
    
    -- Rate Limiting (per subscription)
    rate_limit_per_minute INTEGER,
    rate_limit_per_hour INTEGER,
    rate_limit_window_start TIMESTAMPTZ,
    current_rate_count INTEGER DEFAULT 0,
    
    -- Metadata
    name VARCHAR(255),
    description TEXT,
    created_by UUID,                            -- User who created this subscription
    
    -- Audit Fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT valid_priority CHECK (priority >= 0),
    CONSTRAINT valid_rate_limits CHECK (
        (rate_limit_per_minute IS NULL OR rate_limit_per_minute > 0) AND
        (rate_limit_per_hour IS NULL OR rate_limit_per_hour > 0)
    ),
    CONSTRAINT unique_action_pattern UNIQUE (action_id, event_pattern, deleted_at)
);

-- ============================================================================
-- QUEUE_METRICS TABLE (Queue Performance Monitoring)
-- ============================================================================

CREATE TABLE admin.queue_metrics (
    -- Core Identity
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    queue_name VARCHAR(100) NOT NULL,
    
    -- Metrics Data
    metrics_timestamp TIMESTAMPTZ DEFAULT NOW(),
    pending_messages INTEGER DEFAULT 0,
    processing_messages INTEGER DEFAULT 0,
    completed_messages INTEGER DEFAULT 0,
    failed_messages INTEGER DEFAULT 0,
    
    -- Performance Metrics
    avg_processing_time_ms DECIMAL(10,2),
    throughput_per_minute INTEGER,
    error_rate_percentage DECIMAL(5,2),
    
    -- Resource Usage
    memory_usage_mb INTEGER,
    cpu_usage_percentage DECIMAL(5,2),
    active_workers INTEGER,
    
    -- Health Status
    is_healthy BOOLEAN DEFAULT true,
    last_message_processed_at TIMESTAMPTZ,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Constraints
    CONSTRAINT valid_percentages CHECK (
        (error_rate_percentage IS NULL OR (error_rate_percentage >= 0 AND error_rate_percentage <= 100)) AND
        (cpu_usage_percentage IS NULL OR (cpu_usage_percentage >= 0 AND cpu_usage_percentage <= 100))
    )
);

-- ============================================================================
-- ESSENTIAL INDEXES FOR HIGH-PERFORMANCE EVENT PROCESSING
-- ============================================================================

-- Events table indexes (core operational queries only)
CREATE INDEX idx_events_status_priority ON admin.events(status, priority);
CREATE INDEX idx_events_scheduled_at ON admin.events(scheduled_at) WHERE status = 'pending';
CREATE INDEX idx_events_event_type ON admin.events(event_type);
CREATE INDEX idx_events_created_at ON admin.events(created_at);

-- Actions table indexes (event matching and lookup)
CREATE INDEX idx_actions_active ON admin.actions(is_active);
CREATE INDEX idx_actions_patterns ON admin.actions USING GIN(event_patterns);
CREATE INDEX idx_actions_type ON admin.actions(action_type);

-- Action executions indexes (foreign keys and status tracking)
CREATE INDEX idx_action_executions_event_id ON admin.action_executions(event_id);
CREATE INDEX idx_action_executions_action_id ON admin.action_executions(action_id);
CREATE INDEX idx_action_executions_status ON admin.action_executions(status);

-- Event subscriptions indexes (subscription matching)
CREATE INDEX idx_event_subscriptions_active ON admin.event_subscriptions(is_active);
CREATE INDEX idx_event_subscriptions_pattern ON admin.event_subscriptions(event_pattern);

-- Queue metrics indexes (monitoring queries)
CREATE INDEX idx_queue_metrics_queue_name ON admin.queue_metrics(queue_name);
CREATE INDEX idx_queue_metrics_timestamp ON admin.queue_metrics(metrics_timestamp);

-- ============================================================================
-- TRIGGERS FOR AUTOMATIC UPDATES (Using platform_common functions)
-- ============================================================================

-- Update events.updated_at on changes
CREATE TRIGGER trigger_events_updated_at
    BEFORE UPDATE ON admin.events
    FOR EACH ROW
    EXECUTE FUNCTION platform_common.update_updated_at_column();

-- Update actions.updated_at on changes
CREATE TRIGGER trigger_actions_updated_at
    BEFORE UPDATE ON admin.actions
    FOR EACH ROW
    EXECUTE FUNCTION platform_common.update_updated_at_column();

-- Update action_executions.updated_at on changes
CREATE TRIGGER trigger_action_executions_updated_at
    BEFORE UPDATE ON admin.action_executions
    FOR EACH ROW
    EXECUTE FUNCTION platform_common.update_updated_at_column();

-- Update event_subscriptions.updated_at on changes
CREATE TRIGGER trigger_event_subscriptions_updated_at
    BEFORE UPDATE ON admin.event_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION platform_common.update_updated_at_column();

-- ============================================================================
-- SEED DATA NOTE
-- ============================================================================
-- 
-- Seed data for actions has been moved to:
-- /migrations/seeds/admin/08_events_and_actions_seed.sql
--
-- This separation allows for:
-- - Clean schema migrations without data
-- - Optional seeding for different environments  
-- - Better maintenance and updates of seed data

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON SCHEMA admin IS 'Admin schema containing platform-wide event and action management';

COMMENT ON TABLE admin.events IS 'Event sourcing table storing all platform events with full audit trail and replay support';
COMMENT ON TABLE admin.actions IS 'Action definitions that can be triggered by events';
COMMENT ON TABLE admin.action_executions IS 'Execution history and status tracking for action runs';
COMMENT ON TABLE admin.event_subscriptions IS 'Dynamic mappings between events and actions with filtering';
COMMENT ON TABLE admin.queue_metrics IS 'Queue performance monitoring and health metrics';

COMMENT ON COLUMN admin.events.event_type IS 'Dot-notation event type (e.g., tenants.created, users.updated)';
COMMENT ON COLUMN admin.events.aggregate_id IS 'ID of the entity that triggered this event';
COMMENT ON COLUMN admin.events.correlation_id IS 'Groups related events together for tracking';
COMMENT ON COLUMN admin.events.causation_id IS 'The event that caused this event (causality chain)';

COMMENT ON COLUMN admin.actions.event_patterns IS 'Array of event patterns this action responds to (supports wildcards)';
COMMENT ON COLUMN admin.actions.handler_class IS 'Full Python class path for the action handler implementation';

COMMENT ON COLUMN admin.action_executions.attempt_number IS 'Retry attempt number (1 for first attempt)';
COMMENT ON COLUMN admin.action_executions.parent_execution_id IS 'Links to original execution for retry tracking';
