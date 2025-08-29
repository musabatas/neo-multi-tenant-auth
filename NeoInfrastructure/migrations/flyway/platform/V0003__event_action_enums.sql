-- ============================================================================
-- EVENT AND ACTION ENUM TYPES (Moved to platform_common schema for sharing)
-- ============================================================================

-- Event status lifecycle
CREATE TYPE platform_common.event_status AS ENUM (
    'pending',      -- Event created, waiting to be processed
    'processing',   -- Event is being processed
    'completed',    -- Event processing completed successfully
    'failed',       -- Event processing failed
    'retrying',     -- Event is being retried after failure
    'cancelled',    -- Event processing was cancelled
    'paused',       -- Event is paused
    'blocked'       -- Event is blocked
);

-- Event priority levels
CREATE TYPE platform_common.event_priority AS ENUM (
    'low',          -- Background tasks, non-critical events
    'normal',       -- Standard business events
    'high',         -- Important events requiring faster processing
    'very_high',    -- Very important events requiring immediate processing
    'critical'      -- System-critical events requiring immediate processing
);

-- Action types for polymorphic action handling (Extended for flexibility)
CREATE TYPE platform_common.action_type AS ENUM (
    -- Communication & Notifications
    'email',                    -- Send email notifications
    'sms',                      -- SMS notifications
    'push_notification',        -- Mobile/web push notifications  
    'webhook',                  -- HTTP webhook calls
    'system_notification',      -- Internal system notifications
    'slack_notification',       -- Slack messages
    'teams_notification',       -- Microsoft Teams messages
    
    -- Function & Code Execution
    'function_execution',       -- Execute Python functions/lambdas
    'script_execution',         -- Execute shell scripts
    'workflow_trigger',         -- Trigger complex workflows
    'lambda_function',          -- AWS Lambda or serverless functions
    'background_job',           -- Queue background jobs (Celery, etc.)
    
    -- Data & Storage Operations  
    'database_operation',       -- Database schema/data operations
    'file_operation',           -- File system operations
    'storage_operation',        -- Cloud storage (S3, etc.)
    'backup_operation',         -- Data backup operations
    'data_sync',               -- Data synchronization operations
    
    -- Cache & Performance
    'cache_invalidation',       -- Cache management operations
    'cache_warming',           -- Pre-populate caches
    'index_rebuild',           -- Database index operations
    
    -- External Integrations
    'external_api',            -- Third-party API calls
    'payment_processing',      -- Payment gateway operations
    'analytics_tracking',      -- Send data to analytics platforms
    'crm_sync',               -- CRM system synchronization
    'erp_sync',               -- ERP system synchronization
    
    -- Security & Compliance
    'security_scan',           -- Trigger security scans
    'compliance_check',        -- Run compliance validations
    'audit_log',              -- Create audit entries
    'access_review',          -- Trigger access reviews
    
    -- Infrastructure & DevOps
    'deployment_trigger',      -- Trigger deployments
    'scaling_operation',       -- Auto-scaling operations
    'monitoring_alert',        -- Create monitoring alerts
    'health_check',           -- Perform health checks
    
    -- Business Logic
    'report_generation',       -- Generate business reports
    'batch_processing',        -- Process data in batches
    'data_pipeline',          -- Execute data pipelines
    
    -- Extensibility
    'custom'                  -- Custom action handlers
);

-- Action execution status
CREATE TYPE platform_common.action_status AS ENUM (
    'pending',      -- Action queued, waiting to execute
    'running',      -- Action is currently executing
    'completed',    -- Action completed successfully
    'failed',       -- Action execution failed
    'retrying',     -- Action is being retried
    'cancelled',    -- Action was cancelled
    'timeout',      -- Action exceeded timeout limits
    'skipped',      -- Action was skipped
    'paused',       -- Action is paused
    'blocked'       -- Action is blocked
);
