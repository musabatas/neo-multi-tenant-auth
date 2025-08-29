-- V2007: Tenant Template Events and Actions Infrastructure
-- Creates comprehensive event-driven architecture for tenant-level events and actions
-- Applied to: Regional shared databases (tenant_template schema)
-- Features: Event sourcing, action queuing, audit trails, replay support
-- Note: Identical structure to admin schema for multi-region consistency

-- ============================================================================
-- EVENT AND ACTION ENUM TYPES (Using shared platform_common types)
-- ============================================================================

-- Note: Enum types are defined in platform_common schema and shared across all databases
-- This ensures consistency and reduces duplication across admin and tenant schemas

-- ============================================================================
-- EVENTS TABLE (Event Sourcing + Audit Trail)
-- ============================================================================

CREATE TABLE tenant_template.events (
    -- Core Identity
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    event_type VARCHAR(255) NOT NULL,           -- e.g., 'users.created', 'orders.updated'
    aggregate_id UUID NOT NULL,                 -- ID of the entity that triggered the event
    aggregate_type VARCHAR(100) NOT NULL,       -- Type of entity (user, order, product)
    
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
    
    -- Context Information (tenant-scoped)
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

CREATE TABLE tenant_template.actions (
    -- Core Identity
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    name VARCHAR(255) NOT NULL UNIQUE,          -- e.g., 'send_order_confirmation', 'update_inventory'
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

CREATE TABLE tenant_template.action_executions (
    -- Core Identity
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    event_id UUID NOT NULL REFERENCES tenant_template.events(id) ON DELETE CASCADE,
    action_id UUID NOT NULL REFERENCES tenant_template.actions(id) ON DELETE CASCADE,
    
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
    parent_execution_id UUID REFERENCES tenant_template.action_executions(id),
    
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

CREATE TABLE tenant_template.event_subscriptions (
    -- Core Identity
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    action_id UUID NOT NULL REFERENCES tenant_template.actions(id) ON DELETE CASCADE,
    
    -- Subscription Configuration
    event_pattern VARCHAR(255) NOT NULL,        -- Event pattern to match (supports wildcards)
    conditions JSONB DEFAULT '{}',              -- Additional filtering conditions
    
    -- Subscription Settings
    is_active BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 0,                 -- Higher number = higher priority
    
    -- Filtering and Routing (tenant-scoped)
    user_filter UUID[],                         -- Limit to specific users
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

CREATE TABLE tenant_template.queue_metrics (
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
CREATE INDEX idx_tenant_events_status_priority ON tenant_template.events(status, priority);
CREATE INDEX idx_tenant_events_scheduled_at ON tenant_template.events(scheduled_at) WHERE status = 'pending';
CREATE INDEX idx_tenant_events_event_type ON tenant_template.events(event_type);
CREATE INDEX idx_tenant_events_created_at ON tenant_template.events(created_at);

-- Actions table indexes (event matching and lookup)
CREATE INDEX idx_tenant_actions_active ON tenant_template.actions(is_active);
CREATE INDEX idx_tenant_actions_patterns ON tenant_template.actions USING GIN(event_patterns);
CREATE INDEX idx_tenant_actions_type ON tenant_template.actions(action_type);

-- Action executions indexes (foreign keys and status tracking)
CREATE INDEX idx_tenant_action_executions_event_id ON tenant_template.action_executions(event_id);
CREATE INDEX idx_tenant_action_executions_action_id ON tenant_template.action_executions(action_id);
CREATE INDEX idx_tenant_action_executions_status ON tenant_template.action_executions(status);

-- Event subscriptions indexes (subscription matching)
CREATE INDEX idx_tenant_event_subscriptions_active ON tenant_template.event_subscriptions(is_active);
CREATE INDEX idx_tenant_event_subscriptions_pattern ON tenant_template.event_subscriptions(event_pattern);

-- Queue metrics indexes (monitoring queries)
CREATE INDEX idx_tenant_queue_metrics_queue_name ON tenant_template.queue_metrics(queue_name);
CREATE INDEX idx_tenant_queue_metrics_timestamp ON tenant_template.queue_metrics(metrics_timestamp);

-- ============================================================================
-- TRIGGERS FOR AUTOMATIC UPDATES (Using platform_common functions)
-- ============================================================================

-- Update events.updated_at on changes
CREATE TRIGGER trigger_events_updated_at
    BEFORE UPDATE ON tenant_template.events
    FOR EACH ROW
    EXECUTE FUNCTION platform_common.update_updated_at_column();

-- Update actions.updated_at on changes
CREATE TRIGGER trigger_actions_updated_at
    BEFORE UPDATE ON tenant_template.actions
    FOR EACH ROW
    EXECUTE FUNCTION platform_common.update_updated_at_column();

-- Update action_executions.updated_at on changes
CREATE TRIGGER trigger_action_executions_updated_at
    BEFORE UPDATE ON tenant_template.action_executions
    FOR EACH ROW
    EXECUTE FUNCTION platform_common.update_updated_at_column();

-- Update event_subscriptions.updated_at on changes
CREATE TRIGGER trigger_event_subscriptions_updated_at
    BEFORE UPDATE ON tenant_template.event_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION platform_common.update_updated_at_column();

-- ============================================================================
-- TENANT TEMPLATE SEED DATA NOTE
-- ============================================================================
--
-- NOTE: Tenant template schemas should NOT be seeded with data.
-- The tenant_template is a template that gets copied for each tenant.
-- Any seed data would be duplicated across all tenant schemas.
--
-- Tenant-specific actions should be:
-- - Registered dynamically by the application when tenants are created
-- - Added via tenant management APIs
-- - Configured per-tenant based on subscription plans and features
--
-- For common tenant actions, use the neo-commons action registry
-- to register actions programmatically when needed.

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON SCHEMA tenant_template IS 'Tenant template schema containing tenant-level event and action management';

COMMENT ON TABLE tenant_template.events IS 'Tenant-scoped event sourcing table storing all tenant events with full audit trail';
COMMENT ON TABLE tenant_template.actions IS 'Tenant-level action definitions that can be triggered by events';
COMMENT ON TABLE tenant_template.action_executions IS 'Execution history and status tracking for tenant action runs';
COMMENT ON TABLE tenant_template.event_subscriptions IS 'Dynamic mappings between tenant events and actions';
COMMENT ON TABLE tenant_template.queue_metrics IS 'Tenant-scoped queue performance monitoring and health metrics';

COMMENT ON COLUMN tenant_template.events.event_type IS 'Dot-notation event type (e.g., users.created, orders.updated)';
COMMENT ON COLUMN tenant_template.events.aggregate_id IS 'ID of the tenant entity that triggered this event';
COMMENT ON COLUMN tenant_template.events.correlation_id IS 'Groups related tenant events together for tracking';
COMMENT ON COLUMN tenant_template.events.causation_id IS 'The event that caused this event (tenant causality chain)';

COMMENT ON COLUMN tenant_template.actions.event_patterns IS 'Array of event patterns this tenant action responds to';
COMMENT ON COLUMN tenant_template.actions.handler_class IS 'Full Python class path for the tenant action handler';

COMMENT ON COLUMN tenant_template.action_executions.attempt_number IS 'Retry attempt number for tenant action (1 for first attempt)';
COMMENT ON COLUMN tenant_template.action_executions.parent_execution_id IS 'Links to original tenant execution for retry tracking';
