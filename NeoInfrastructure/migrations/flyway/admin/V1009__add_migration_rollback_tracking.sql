-- V009: Add migration rollback tracking table
-- This table tracks rollback attempts for audit and debugging purposes

CREATE TABLE IF NOT EXISTS admin.migration_rollbacks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    database_id UUID NOT NULL,
    database_name VARCHAR(255) NOT NULL,
    schema_name VARCHAR(255) NOT NULL,
    from_version VARCHAR(50),
    to_version VARCHAR(50),
    rollback_reason TEXT,
    status VARCHAR(50) NOT NULL, -- 'completed', 'failed', 'logged_only'
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) DEFAULT CURRENT_USER
);

-- Create indexes for efficient querying
CREATE INDEX idx_migration_rollbacks_database ON admin.migration_rollbacks(database_id);
CREATE INDEX idx_migration_rollbacks_created_at ON admin.migration_rollbacks(created_at DESC);
CREATE INDEX idx_migration_rollbacks_status ON admin.migration_rollbacks(status);

-- Add foreign key constraint
ALTER TABLE admin.migration_rollbacks 
    ADD CONSTRAINT fk_rollbacks_database_connection 
    FOREIGN KEY (database_id) 
    REFERENCES admin.database_connections(id) 
    ON DELETE CASCADE;

-- Add comment
COMMENT ON TABLE admin.migration_rollbacks IS 'Tracks migration rollback attempts for audit and debugging';