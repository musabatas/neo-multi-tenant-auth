-- Task Management System Migration
-- Creates tables for automated task management and execution tracking

-- Create custom enums
CREATE TYPE trigger_type AS ENUM ('scheduled', 'manual', 'dependency', 'retry');
CREATE TYPE execution_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled', 'timeout', 'retrying');

-- Table 1: tasks
-- Purpose: Master task configuration and definitions
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    task_name VARCHAR(100) NOT NULL UNIQUE,
    task_type VARCHAR(50) NOT NULL, -- 'price_aggregation', 'inventory_sync', 'opportunity_detection', etc.
    description TEXT,
    
    -- Basic Configuration
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    
    -- Flexible Configuration (JSONB)
    configuration JSONB NOT NULL DEFAULT '{}',
    
    -- Audit Fields
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Table 2: task_executions
-- Purpose: Detailed execution history and real-time execution tracking
CREATE TABLE task_executions (
    id BIGSERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    
    -- Execution Identity
    trigger_type trigger_type NOT NULL,
    
    -- Execution Lifecycle
    status execution_status NOT NULL DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    
    -- Processing Metrics
    items_total INTEGER,
    items_processed INTEGER DEFAULT 0,
    items_successful INTEGER DEFAULT 0,
    items_failed INTEGER DEFAULT 0,
    
    -- Processing Tracking (moved from tasks table)
    processing_range_start BIGINT,
    processing_range_end BIGINT,
    last_processed_id BIGINT,
    
    -- Error Handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Execution Context (JSONB)
    execution_context JSONB DEFAULT '{}', -- Runtime parameters, environment info
    performance_metrics JSONB DEFAULT '{}', -- Custom metrics per task type
    
    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Table 3: task_checkpoints (Optional - for large batch processing)
-- Purpose: Checkpoint management for resumable large-scale operations
CREATE TABLE task_checkpoints (
    id BIGSERIAL PRIMARY KEY,
    execution_id BIGINT NOT NULL REFERENCES task_executions(id) ON DELETE CASCADE,
    
    -- Checkpoint Identity
    checkpoint_name VARCHAR(100) NOT NULL,
    checkpoint_type VARCHAR(50) NOT NULL, -- 'batch', 'time', 'custom'
    
    -- Progress Tracking
    processed_up_to_id BIGINT,
    processed_count INTEGER DEFAULT 0,
    total_count INTEGER,
    completion_percentage DECIMAL(5,2),
    
    -- State Persistence
    checkpoint_data JSONB NOT NULL DEFAULT '{}', -- Serialized state
    
    -- Timing
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(execution_id, checkpoint_name)
);

-- Performance Indexes
CREATE INDEX idx_tasks_enabled 
ON tasks(is_enabled, task_type) WHERE is_enabled = true;

CREATE INDEX idx_task_executions_status_started 
ON task_executions(status, started_at DESC);

CREATE INDEX idx_task_executions_task_performance 
ON task_executions(task_id, completed_at DESC, duration_seconds);

-- JSONB indexes for flexible querying
CREATE INDEX idx_tasks_config_gin 
ON tasks USING GIN(configuration);

CREATE INDEX idx_task_executions_metrics_gin 
ON task_executions USING GIN(performance_metrics);

-- Index for task execution lookups
CREATE INDEX idx_task_executions_task_id_status
ON task_executions(task_id, status);

-- Index for checkpoint lookups
CREATE INDEX idx_task_checkpoints_execution_id
ON task_checkpoints(execution_id);

-- Sample data for testing
INSERT INTO tasks (task_name, task_type, description, configuration) VALUES
('price_aggregation_daily', 'price_aggregation', 'Daily price aggregation for all products', '{
    "batch_size": 10000,
    "target_table": "product_price_aggregates",
    "source_tables": ["product_store_prices", "product_store_inventory"],
    "processing_mode": "incremental",
    "filters": {
        "min_price_threshold": 0.01,
        "exclude_out_of_stock": false
    }
}'),

('inventory_sync_realtime', 'inventory_sync', 'Real-time inventory synchronization', '{
    "sync_frequency": "real-time",
    "batch_size": 5000,
    "source_apis": ["canadiantire", "amazon", "walmart"],
    "data_validation": {
        "required_fields": ["sku", "quantity", "last_updated"],
        "business_rules": ["quantity >= 0"]
    }
}'),

('opportunity_detection', 'opportunity_detection', 'Detect profit opportunities between stores', '{
    "analysis_scope": {
        "profit_margin_threshold": 0.15,
        "minimum_volume_threshold": 100,
        "geographic_regions": ["CA", "US"]
    },
    "data_sources": ["internal_prices", "competitor_prices", "marketspy_data"],
    "output_destinations": ["opportunity_history"]
}'),

('cleanup_old_executions', 'maintenance', 'Clean up old task execution records', '{
    "retention_days": 90,
    "batch_size": 1000,
    "target_tables": ["task_executions", "task_checkpoints"]
}');