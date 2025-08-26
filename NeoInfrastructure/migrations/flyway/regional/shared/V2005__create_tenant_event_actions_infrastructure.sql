-- V2005__create_tenant_event_actions_infrastructure.sql
-- Create identical event actions infrastructure for tenant_template schema
-- Enables tenant-specific dynamic event actions system

-- =====================================================================================
-- EVENT ACTIONS TABLE (TENANT-SPECIFIC)
-- Core registry for configurable event actions per tenant
-- =====================================================================================
CREATE TABLE IF NOT EXISTS tenant_template.event_actions (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    
    -- Basic identification
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Action configuration
    handler_type VARCHAR(50) NOT NULL,
    configuration JSONB NOT NULL DEFAULT '{}',
    
    -- Event matching
    event_types JSONB NOT NULL DEFAULT '[]', -- Array of event type patterns
    conditions JSONB NOT NULL DEFAULT '[]',  -- Array of condition objects
    context_filters JSONB NOT NULL DEFAULT '{}', -- Key-value filters
    
    -- Execution settings
    execution_mode VARCHAR(20) NOT NULL DEFAULT 'async',
    priority VARCHAR(20) NOT NULL DEFAULT 'normal', 
    timeout_seconds INTEGER NOT NULL DEFAULT 30,
    max_retries INTEGER NOT NULL DEFAULT 3,
    retry_delay_seconds INTEGER NOT NULL DEFAULT 5,
    
    -- Status and lifecycle
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    
    -- Metadata
    tags JSONB NOT NULL DEFAULT '{}',
    tenant_id UUID, -- Always populated for tenant actions
    created_by_user_id UUID NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_triggered_at TIMESTAMPTZ,
    
    -- Statistics
    trigger_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    
    -- Constraints
    CONSTRAINT valid_handler_type CHECK (
        handler_type IN ('webhook', 'email', 'function', 'workflow', 'sms', 'slack', 'teams', 'custom')
    ),
    CONSTRAINT valid_execution_mode CHECK (
        execution_mode IN ('sync', 'async', 'queued')
    ),
    CONSTRAINT valid_priority CHECK (
        priority IN ('low', 'normal', 'high', 'critical')
    ),
    CONSTRAINT valid_status CHECK (
        status IN ('active', 'inactive', 'paused', 'archived')
    ),
    CONSTRAINT valid_timeout CHECK (timeout_seconds > 0 AND timeout_seconds <= 3600),
    CONSTRAINT valid_retries CHECK (max_retries >= 0 AND max_retries <= 10),
    CONSTRAINT valid_retry_delay CHECK (retry_delay_seconds >= 0 AND retry_delay_seconds <= 300),
    CONSTRAINT non_empty_event_types CHECK (jsonb_array_length(event_types) > 0),
    CONSTRAINT non_negative_stats CHECK (
        trigger_count >= 0 AND 
        success_count >= 0 AND 
        failure_count >= 0 AND
        success_count <= trigger_count AND 
        failure_count <= trigger_count
    )
);

-- Performance indexes for event actions
CREATE INDEX IF NOT EXISTS idx_tenant_event_actions_handler_type ON tenant_template.event_actions(handler_type);
CREATE INDEX IF NOT EXISTS idx_tenant_event_actions_status_enabled ON tenant_template.event_actions(status, is_enabled);
CREATE INDEX IF NOT EXISTS idx_tenant_event_actions_tenant_id ON tenant_template.event_actions(tenant_id) WHERE tenant_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tenant_event_actions_created_by ON tenant_template.event_actions(created_by_user_id);
CREATE INDEX IF NOT EXISTS idx_tenant_event_actions_updated_at ON tenant_template.event_actions(updated_at);

-- GIN indexes for JSONB fields for efficient filtering
CREATE INDEX IF NOT EXISTS idx_tenant_event_actions_event_types_gin ON tenant_template.event_actions USING GIN(event_types);
CREATE INDEX IF NOT EXISTS idx_tenant_event_actions_conditions_gin ON tenant_template.event_actions USING GIN(conditions);
CREATE INDEX IF NOT EXISTS idx_tenant_event_actions_context_filters_gin ON tenant_template.event_actions USING GIN(context_filters);
CREATE INDEX IF NOT EXISTS idx_tenant_event_actions_tags_gin ON tenant_template.event_actions USING GIN(tags);

-- =====================================================================================
-- ACTION EXECUTIONS TABLE (TENANT-SPECIFIC)
-- Log of action execution attempts with results per tenant
-- =====================================================================================
CREATE TABLE IF NOT EXISTS tenant_template.action_executions (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    action_id UUID NOT NULL REFERENCES tenant_template.event_actions(id) ON DELETE CASCADE,
    
    -- Event context
    event_id UUID, -- Reference to the triggering event
    event_type VARCHAR(255) NOT NULL,
    event_data JSONB NOT NULL DEFAULT '{}',
    
    -- Execution tracking
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    
    -- Results and errors
    result JSONB,
    error_message TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    
    -- Execution context and metadata
    execution_context JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_execution_status CHECK (
        status IN ('pending', 'running', 'success', 'failed', 'timeout')
    ),
    CONSTRAINT valid_retry_count CHECK (retry_count >= 0),
    CONSTRAINT valid_duration CHECK (duration_ms IS NULL OR duration_ms >= 0),
    CONSTRAINT valid_timestamps CHECK (
        (started_at IS NULL) OR 
        (completed_at IS NULL OR completed_at >= started_at)
    )
);

-- Performance indexes for action executions
CREATE INDEX IF NOT EXISTS idx_tenant_action_executions_action_id ON tenant_template.action_executions(action_id);
CREATE INDEX IF NOT EXISTS idx_tenant_action_executions_status ON tenant_template.action_executions(status);
CREATE INDEX IF NOT EXISTS idx_tenant_action_executions_event_type ON tenant_template.action_executions(event_type);
CREATE INDEX IF NOT EXISTS idx_tenant_action_executions_created_at ON tenant_template.action_executions(created_at);
CREATE INDEX IF NOT EXISTS idx_tenant_action_executions_completed_at ON tenant_template.action_executions(completed_at);

-- Index for finding failed executions to retry
CREATE INDEX IF NOT EXISTS idx_tenant_action_executions_retry_lookup ON tenant_template.action_executions(status, retry_count, created_at) 
    WHERE status IN ('failed', 'timeout');

-- =====================================================================================
-- FUNCTIONS AND TRIGGERS
-- =====================================================================================

-- Trigger to automatically update updated_at on event_actions
DROP TRIGGER IF EXISTS trigger_update_tenant_event_actions_updated_at ON tenant_template.event_actions;
CREATE TRIGGER trigger_update_tenant_event_actions_updated_at
    BEFORE UPDATE ON tenant_template.event_actions
    FOR EACH ROW
    EXECUTE FUNCTION platform_common.update_updated_at_column();

-- Function to validate event action configuration based on handler type
CREATE OR REPLACE FUNCTION tenant_template.validate_action_configuration()
RETURNS TRIGGER AS $$
BEGIN
    -- Validate webhook handler configuration
    IF NEW.handler_type = 'webhook' THEN
        IF NOT (NEW.configuration ? 'url') THEN
            RAISE EXCEPTION 'Webhook handler requires url in configuration';
        END IF;
        IF NOT (NEW.configuration->>'url' ~ '^https?://') THEN
            RAISE EXCEPTION 'Webhook URL must start with http:// or https://';
        END IF;
    END IF;
    
    -- Validate email handler configuration  
    IF NEW.handler_type = 'email' THEN
        IF NOT (NEW.configuration ? 'to') THEN
            RAISE EXCEPTION 'Email handler requires to address in configuration';
        END IF;
        IF NOT (NEW.configuration ? 'template') THEN
            RAISE EXCEPTION 'Email handler requires template in configuration';
        END IF;
    END IF;
    
    -- Validate function handler configuration
    IF NEW.handler_type = 'function' THEN
        IF NOT (NEW.configuration ? 'module') THEN
            RAISE EXCEPTION 'Function handler requires module in configuration';
        END IF;
        IF NOT (NEW.configuration ? 'function') THEN
            RAISE EXCEPTION 'Function handler requires function name in configuration';
        END IF;
    END IF;
    
    -- Validate workflow handler configuration
    IF NEW.handler_type = 'workflow' THEN
        IF NOT (NEW.configuration ? 'steps') THEN
            RAISE EXCEPTION 'Workflow handler requires steps in configuration';
        END IF;
        IF jsonb_array_length(NEW.configuration->'steps') = 0 THEN
            RAISE EXCEPTION 'Workflow handler requires at least one step';
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to validate action configuration
DROP TRIGGER IF EXISTS trigger_validate_tenant_action_configuration ON tenant_template.event_actions;
CREATE TRIGGER trigger_validate_tenant_action_configuration
    BEFORE INSERT OR UPDATE OF configuration, handler_type ON tenant_template.event_actions
    FOR EACH ROW
    EXECUTE FUNCTION tenant_template.validate_action_configuration();

-- Function to update action statistics
CREATE OR REPLACE FUNCTION tenant_template.update_action_statistics()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.status IN ('success', 'failed', 'timeout') THEN
        UPDATE tenant_template.event_actions 
        SET 
            trigger_count = trigger_count + 1,
            success_count = success_count + CASE WHEN NEW.status = 'success' THEN 1 ELSE 0 END,
            failure_count = failure_count + CASE WHEN NEW.status IN ('failed', 'timeout') THEN 1 ELSE 0 END,
            last_triggered_at = NEW.created_at,
            updated_at = NOW()
        WHERE id = NEW.action_id;
    END IF;
    
    IF TG_OP = 'UPDATE' AND OLD.status != NEW.status AND NEW.status IN ('success', 'failed', 'timeout') THEN
        UPDATE tenant_template.event_actions 
        SET
            success_count = success_count + CASE 
                WHEN NEW.status = 'success' AND OLD.status != 'success' THEN 1 
                WHEN OLD.status = 'success' AND NEW.status != 'success' THEN -1 
                ELSE 0 END,
            failure_count = failure_count + CASE 
                WHEN NEW.status IN ('failed', 'timeout') AND OLD.status NOT IN ('failed', 'timeout') THEN 1
                WHEN OLD.status IN ('failed', 'timeout') AND NEW.status NOT IN ('failed', 'timeout') THEN -1
                ELSE 0 END,
            updated_at = NOW()
        WHERE id = NEW.action_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update action statistics when executions complete
DROP TRIGGER IF EXISTS trigger_update_tenant_action_statistics ON tenant_template.action_executions;
CREATE TRIGGER trigger_update_tenant_action_statistics
    AFTER INSERT OR UPDATE OF status ON tenant_template.action_executions
    FOR EACH ROW
    EXECUTE FUNCTION tenant_template.update_action_statistics();

-- =====================================================================================
-- VIEWS FOR REPORTING AND MONITORING
-- =====================================================================================

-- View for action performance metrics
CREATE OR REPLACE VIEW tenant_template.v_action_performance AS
SELECT 
    ea.id,
    ea.name,
    ea.handler_type,
    ea.status,
    ea.is_enabled,
    ea.trigger_count,
    ea.success_count,
    ea.failure_count,
    CASE 
        WHEN ea.trigger_count > 0 THEN ROUND((ea.success_count::decimal / ea.trigger_count) * 100, 2)
        ELSE 0 
    END as success_rate_percent,
    ea.last_triggered_at,
    ea.created_at,
    ea.updated_at,
    -- Recent execution stats (last 24 hours)
    COUNT(ae.id) FILTER (WHERE ae.created_at >= NOW() - INTERVAL '24 hours') as executions_24h,
    COUNT(ae.id) FILTER (WHERE ae.created_at >= NOW() - INTERVAL '24 hours' AND ae.status = 'success') as successes_24h,
    COUNT(ae.id) FILTER (WHERE ae.created_at >= NOW() - INTERVAL '24 hours' AND ae.status IN ('failed', 'timeout')) as failures_24h
FROM tenant_template.event_actions ea
LEFT JOIN tenant_template.action_executions ae ON ea.id = ae.action_id
GROUP BY ea.id, ea.name, ea.handler_type, ea.status, ea.is_enabled, ea.trigger_count, 
         ea.success_count, ea.failure_count, ea.last_triggered_at, ea.created_at, ea.updated_at;

-- View for execution monitoring 
CREATE OR REPLACE VIEW tenant_template.v_execution_monitoring AS
SELECT 
    ae.id as execution_id,
    ea.name as action_name,
    ea.handler_type,
    ae.event_type,
    ae.status,
    ae.started_at,
    ae.completed_at,
    ae.duration_ms,
    ae.retry_count,
    ae.error_message,
    ae.created_at,
    -- Calculate execution time for running executions
    CASE 
        WHEN ae.status = 'running' AND ae.started_at IS NOT NULL 
        THEN EXTRACT(EPOCH FROM (NOW() - ae.started_at)) * 1000 
        ELSE ae.duration_ms 
    END as current_duration_ms
FROM tenant_template.action_executions ae
JOIN tenant_template.event_actions ea ON ae.action_id = ea.id
ORDER BY ae.created_at DESC;

-- =====================================================================================
-- INITIAL DATA AND CONFIGURATION
-- =====================================================================================

-- Add comments describing the tenant event actions system
COMMENT ON TABLE tenant_template.event_actions IS 
'Tenant-specific event actions registry for dynamic event-driven automation. Enables configurable actions to be triggered by tenant domain events.';

COMMENT ON TABLE tenant_template.action_executions IS 
'Log of tenant event action executions with results, errors, and performance metrics.';

-- =====================================================================================
-- CLEANUP FUNCTIONS
-- =====================================================================================

-- Function to archive old executions (can be called by scheduled job per tenant)
CREATE OR REPLACE FUNCTION tenant_template.archive_old_action_executions(retention_days INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM tenant_template.action_executions 
    WHERE created_at < NOW() - (retention_days || ' days')::INTERVAL
    AND status IN ('success', 'failed', 'timeout');
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;