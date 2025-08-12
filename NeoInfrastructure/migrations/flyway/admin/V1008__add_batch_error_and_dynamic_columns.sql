-- V1008: Add error_message and dynamic batch columns to migration tables
-- This enhances the migration tables to support dynamic migrations

-- ============================================================================
-- MIGRATION_BATCHES TABLE ENHANCEMENTS
-- ============================================================================

-- Add error_message column for failure tracking
ALTER TABLE admin.migration_batches 
    ADD COLUMN IF NOT EXISTS error_message TEXT;

-- Add columns for dynamic batch tracking
ALTER TABLE admin.migration_batches 
    ADD COLUMN IF NOT EXISTS total_databases INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_schemas INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS successful_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS failed_count INTEGER DEFAULT 0;

-- Update constraint to allow 'dynamic' batch type
ALTER TABLE admin.migration_batches 
    DROP CONSTRAINT IF EXISTS valid_batch_type;

ALTER TABLE admin.migration_batches 
    ADD CONSTRAINT valid_batch_type CHECK (
        batch_type IN ('tenant_provisioning', 'platform_upgrade', 'regional_update', 
                      'tenant_migration', 'emergency_patch', 'scheduled_maintenance', 'dynamic')
    );

-- ============================================================================
-- MIGRATION_BATCH_DETAILS TABLE ENHANCEMENTS
-- ============================================================================

-- Add database connection tracking columns
ALTER TABLE admin.migration_batch_details
    ADD COLUMN IF NOT EXISTS database_connection_id UUID,
    ADD COLUMN IF NOT EXISTS database_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS schema_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS migrations_applied INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS execution_time_ms INTEGER,
    ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

-- Add foreign key constraint for database connection
ALTER TABLE admin.migration_batch_details
    ADD CONSTRAINT fk_batch_details_database_connection 
    FOREIGN KEY (database_connection_id) 
    REFERENCES admin.database_connections(id) 
    ON DELETE SET NULL;

-- Update status constraint to include more states
ALTER TABLE admin.migration_batch_details
    DROP CONSTRAINT IF EXISTS valid_detail_status;

ALTER TABLE admin.migration_batch_details
    ADD CONSTRAINT valid_detail_status CHECK (
        status IN ('pending', 'running', 'completed', 'failed', 'skipped', 'rolled_back', 'success')
    );

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Add indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_migration_batches_batch_type ON admin.migration_batches(batch_type);
CREATE INDEX IF NOT EXISTS idx_migration_batches_status ON admin.migration_batches(status);
CREATE INDEX IF NOT EXISTS idx_batch_details_connection ON admin.migration_batch_details(database_connection_id);
CREATE INDEX IF NOT EXISTS idx_batch_details_database_name ON admin.migration_batch_details(database_name);

-- ============================================================================
-- COMMENTS
-- ============================================================================

-- Migration batches
COMMENT ON COLUMN admin.migration_batches.error_message IS 'Error message if batch failed';
COMMENT ON COLUMN admin.migration_batches.total_databases IS 'Total number of databases in batch';
COMMENT ON COLUMN admin.migration_batches.total_schemas IS 'Total number of schemas to migrate';
COMMENT ON COLUMN admin.migration_batches.successful_count IS 'Number of successful migrations';
COMMENT ON COLUMN admin.migration_batches.failed_count IS 'Number of failed migrations';

-- Migration batch details
COMMENT ON COLUMN admin.migration_batch_details.database_connection_id IS 'Reference to database_connections table';
COMMENT ON COLUMN admin.migration_batch_details.database_name IS 'Database name for quick reference';
COMMENT ON COLUMN admin.migration_batch_details.schema_name IS 'Schema name being migrated';
COMMENT ON COLUMN admin.migration_batch_details.migrations_applied IS 'Number of migration files applied';
COMMENT ON COLUMN admin.migration_batch_details.execution_time_ms IS 'Time taken to execute migration';
COMMENT ON COLUMN admin.migration_batch_details.metadata IS 'Additional metadata (region, type, etc.)';