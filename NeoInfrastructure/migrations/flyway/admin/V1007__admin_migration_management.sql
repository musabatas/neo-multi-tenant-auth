-- V008: Admin Migration Management
-- Creates minimal tables for programmatic migration orchestration
-- Applied to: Admin database only

-- ============================================================================
-- MIGRATION LOCKS (Prevent concurrent migrations on same resource)
-- ============================================================================

CREATE TABLE IF NOT EXISTS admin.migration_locks (
    resource_key VARCHAR(500) PRIMARY KEY,      -- Format: "db:{database}:schema:{schema}"
    locked_by VARCHAR(255) NOT NULL,            -- Service instance or job ID
    locked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,            -- Auto-release stale locks
    lock_purpose VARCHAR(100),                  -- 'migration', 'backup', 'maintenance'
    metadata JSONB DEFAULT '{}',                -- Additional lock context
    
    CONSTRAINT lock_not_expired CHECK (expires_at > locked_at),
    CONSTRAINT valid_lock_duration CHECK (
        EXTRACT(EPOCH FROM (expires_at - locked_at)) <= 3600  -- Max 1 hour lock
    )
);

-- Index for expired lock cleanup
CREATE INDEX idx_migration_locks_expires ON admin.migration_locks(expires_at);
CREATE INDEX idx_migration_locks_locked_by ON admin.migration_locks(locked_by);

-- ============================================================================
-- MIGRATION BATCHES (Track bulk migration operations)
-- ============================================================================

CREATE TABLE IF NOT EXISTS admin.migration_batches (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    batch_name VARCHAR(200) NOT NULL,
    batch_type VARCHAR(50) NOT NULL             -- 'tenant_provisioning', 'platform_upgrade', 'regional_update', 'tenant_migration'
        CONSTRAINT valid_batch_type CHECK (
            batch_type IN ('tenant_provisioning', 'platform_upgrade', 'regional_update', 'tenant_migration', 'emergency_patch', 'scheduled_maintenance')
        ),
    scope VARCHAR(50) NOT NULL                  -- 'admin', 'regional', 'tenants', 'specific'
        CONSTRAINT valid_scope CHECK (
            scope IN ('admin', 'regional', 'tenants', 'specific', 'all')
        ),
    target_version VARCHAR(50),                 -- Target migration version
    total_targets INTEGER NOT NULL DEFAULT 0,
    completed_targets INTEGER DEFAULT 0,
    failed_targets INTEGER DEFAULT 0,
    skipped_targets INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    estimated_completion_at TIMESTAMPTZ,
    executed_by VARCHAR(255) NOT NULL,          -- User or service that initiated
    execution_mode VARCHAR(20) DEFAULT 'auto'   -- 'auto', 'manual', 'scheduled'
        CONSTRAINT valid_execution_mode CHECK (
            execution_mode IN ('auto', 'manual', 'scheduled')
        ),
    status VARCHAR(30) DEFAULT 'pending'
        CONSTRAINT valid_batch_status CHECK (
            status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'paused')
        ),
    error_summary TEXT,
    rollback_initiated BOOLEAN DEFAULT false,
    rollback_completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',                -- Batch-specific details
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT targets_consistency CHECK (
        completed_targets + failed_targets + skipped_targets <= total_targets
    )
);

-- Indexes for migration_batches
CREATE INDEX idx_migration_batches_type ON admin.migration_batches(batch_type);
CREATE INDEX idx_migration_batches_scope ON admin.migration_batches(scope);
CREATE INDEX idx_migration_batches_status ON admin.migration_batches(status);
CREATE INDEX idx_migration_batches_started ON admin.migration_batches(started_at DESC);
CREATE INDEX idx_migration_batches_executed_by ON admin.migration_batches(executed_by);

-- ============================================================================
-- MIGRATION BATCH DETAILS (Individual target tracking within batches)
-- ============================================================================

CREATE TABLE IF NOT EXISTS admin.migration_batch_details (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    batch_id UUID NOT NULL REFERENCES admin.migration_batches(id) ON DELETE CASCADE,
    target_database VARCHAR(255) NOT NULL,
    target_schema VARCHAR(255),
    target_type VARCHAR(30) NOT NULL            -- 'database', 'schema', 'tenant'
        CONSTRAINT valid_target_type CHECK (
            target_type IN ('database', 'schema', 'tenant')
        ),
    previous_version VARCHAR(50),               -- Version before migration
    target_version VARCHAR(50),                 -- Version to migrate to
    current_version VARCHAR(50),                -- Current version after attempt
    status VARCHAR(30) DEFAULT 'pending'
        CONSTRAINT valid_detail_status CHECK (
            status IN ('pending', 'running', 'completed', 'failed', 'skipped', 'rolled_back')
        ),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    attempt_count INTEGER DEFAULT 0,
    error_message TEXT,
    flyway_output TEXT,                         -- Captured Flyway output
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for migration_batch_details
CREATE INDEX idx_batch_details_batch_id ON admin.migration_batch_details(batch_id);
CREATE INDEX idx_batch_details_target ON admin.migration_batch_details(target_database, target_schema);
CREATE INDEX idx_batch_details_status ON admin.migration_batch_details(status);
CREATE INDEX idx_batch_details_started ON admin.migration_batch_details(started_at);

-- ============================================================================
-- MIGRATION SCHEDULES (For scheduled migration windows)
-- ============================================================================

CREATE TABLE IF NOT EXISTS admin.migration_schedules (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    schedule_name VARCHAR(200) NOT NULL UNIQUE,
    schedule_type VARCHAR(30) NOT NULL          -- 'one_time', 'recurring', 'maintenance_window'
        CONSTRAINT valid_schedule_type CHECK (
            schedule_type IN ('one_time', 'recurring', 'maintenance_window')
        ),
    cron_expression VARCHAR(100),                -- For recurring schedules (e.g., '0 2 * * SUN')
    next_run_at TIMESTAMPTZ,
    last_run_at TIMESTAMPTZ,
    scope VARCHAR(50) NOT NULL,                 -- What to migrate
    target_version VARCHAR(50),                 -- Version to migrate to
    max_duration_minutes INTEGER DEFAULT 120,   -- Maximum allowed duration
    is_active BOOLEAN DEFAULT true,
    created_by UUID REFERENCES admin.users,
    metadata JSONB DEFAULT '{}',                -- Schedule-specific configuration
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for migration_schedules
CREATE INDEX idx_migration_schedules_active ON admin.migration_schedules(is_active);
CREATE INDEX idx_migration_schedules_next_run ON admin.migration_schedules(next_run_at);
CREATE INDEX idx_migration_schedules_type ON admin.migration_schedules(schedule_type);

-- ============================================================================
-- VIEWS FOR MIGRATION MONITORING
-- ============================================================================

-- Current migration status overview
CREATE OR REPLACE VIEW admin.v_migration_status_overview AS
SELECT 
    mb.id as batch_id,
    mb.batch_name,
    mb.batch_type,
    mb.scope,
    mb.status,
    mb.total_targets,
    mb.completed_targets,
    mb.failed_targets,
    mb.started_at,
    mb.completed_at,
    CASE 
        WHEN mb.total_targets > 0 
        THEN ROUND((mb.completed_targets::NUMERIC / mb.total_targets) * 100, 2)
        ELSE 0 
    END as completion_percentage,
    EXTRACT(EPOCH FROM (COALESCE(mb.completed_at, NOW()) - mb.started_at))::INTEGER as duration_seconds,
    mb.executed_by
FROM admin.migration_batches mb
WHERE mb.started_at > NOW() - INTERVAL '30 days'
ORDER BY mb.started_at DESC;

-- Active locks view
CREATE OR REPLACE VIEW admin.v_active_migration_locks AS
SELECT 
    resource_key,
    locked_by,
    locked_at,
    expires_at,
    EXTRACT(EPOCH FROM (expires_at - NOW()))::INTEGER as expires_in_seconds,
    lock_purpose,
    metadata
FROM admin.migration_locks
WHERE expires_at > NOW()
ORDER BY locked_at DESC;

-- Failed migrations requiring attention
CREATE OR REPLACE VIEW admin.v_failed_migrations AS
SELECT 
    mbd.id,
    mb.batch_name,
    mbd.target_database,
    mbd.target_schema,
    mbd.error_message,
    mbd.attempt_count,
    mbd.started_at,
    mb.executed_by
FROM admin.migration_batch_details mbd
JOIN admin.migration_batches mb ON mbd.batch_id = mb.id
WHERE mbd.status = 'failed'
  AND mb.started_at > NOW() - INTERVAL '7 days'
ORDER BY mbd.started_at DESC;

-- ============================================================================
-- FUNCTIONS FOR MIGRATION MANAGEMENT
-- ============================================================================

-- Function to acquire a migration lock
CREATE OR REPLACE FUNCTION admin.acquire_migration_lock(
    p_resource_key VARCHAR(500),
    p_locked_by VARCHAR(255),
    p_lock_duration_seconds INTEGER DEFAULT 600,
    p_lock_purpose VARCHAR(100) DEFAULT 'migration'
) RETURNS BOOLEAN AS $$
DECLARE
    v_lock_acquired BOOLEAN;
BEGIN
    -- Clean up expired locks first
    DELETE FROM admin.migration_locks 
    WHERE expires_at < NOW();
    
    -- Try to acquire lock
    INSERT INTO admin.migration_locks (
        resource_key, 
        locked_by, 
        expires_at, 
        lock_purpose
    ) VALUES (
        p_resource_key,
        p_locked_by,
        NOW() + (p_lock_duration_seconds || ' seconds')::INTERVAL,
        p_lock_purpose
    )
    ON CONFLICT (resource_key) DO NOTHING;
    
    -- Check if we got the lock
    SELECT EXISTS(
        SELECT 1 FROM admin.migration_locks 
        WHERE resource_key = p_resource_key 
        AND locked_by = p_locked_by
        AND expires_at > NOW()
    ) INTO v_lock_acquired;
    
    RETURN v_lock_acquired;
END;
$$ LANGUAGE plpgsql;

-- Function to release a migration lock
CREATE OR REPLACE FUNCTION admin.release_migration_lock(
    p_resource_key VARCHAR(500),
    p_locked_by VARCHAR(255)
) RETURNS BOOLEAN AS $$
DECLARE
    v_rows_deleted INTEGER;
BEGIN
    DELETE FROM admin.migration_locks 
    WHERE resource_key = p_resource_key 
    AND locked_by = p_locked_by;
    
    GET DIAGNOSTICS v_rows_deleted = ROW_COUNT;
    
    RETURN v_rows_deleted > 0;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up expired locks
CREATE OR REPLACE FUNCTION admin.cleanup_expired_locks() RETURNS INTEGER AS $$
DECLARE
    v_rows_deleted INTEGER;
BEGIN
    DELETE FROM admin.migration_locks 
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS v_rows_deleted = ROW_COUNT;
    
    RETURN v_rows_deleted;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================

CREATE OR REPLACE FUNCTION admin.update_migration_batch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_migration_batches_updated_at
    BEFORE UPDATE ON admin.migration_batches
    FOR EACH ROW
    EXECUTE FUNCTION admin.update_migration_batch_updated_at();

CREATE TRIGGER update_migration_batch_details_updated_at
    BEFORE UPDATE ON admin.migration_batch_details
    FOR EACH ROW
    EXECUTE FUNCTION admin.update_migration_batch_updated_at();

CREATE TRIGGER update_migration_schedules_updated_at
    BEFORE UPDATE ON admin.migration_schedules
    FOR EACH ROW
    EXECUTE FUNCTION admin.update_migration_batch_updated_at();

-- ============================================================================
-- GRANTS
-- ============================================================================

-- Grant usage on tables to application role (adjust as needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA admin TO neofast_app;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA admin TO neofast_app;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE admin.migration_locks IS 'Distributed locks to prevent concurrent migrations on same resource';
COMMENT ON TABLE admin.migration_batches IS 'Track bulk migration operations across multiple targets';
COMMENT ON TABLE admin.migration_batch_details IS 'Individual target results within a migration batch';
COMMENT ON TABLE admin.migration_schedules IS 'Scheduled migration windows for maintenance';

COMMENT ON FUNCTION admin.acquire_migration_lock IS 'Safely acquire a distributed lock for migration operations';
COMMENT ON FUNCTION admin.release_migration_lock IS 'Release a previously acquired migration lock';
COMMENT ON FUNCTION admin.cleanup_expired_locks IS 'Remove expired locks from the system';

-- Log migration completion
SELECT 'V008: Admin migration management tables and functions created' as migration_status;