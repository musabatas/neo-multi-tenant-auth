-- ============================================================================
-- ADMIN EVENTS AND ACTIONS SEED DATA
-- ============================================================================
--
-- Seeds default actions for the admin database event system
-- Run after: V1016__admin_events_and_actions.sql migration
--
-- These actions handle platform-wide events such as:
-- - Tenant lifecycle management
-- - Organization management  
-- - System-wide notifications and monitoring
-- - Security and compliance actions
--
-- Usage: Run via deployment API or manual execution
-- Environment: All (dev, staging, production)
--
-- ============================================================================

-- Insert common platform actions
INSERT INTO admin.actions (name, action_type, handler_class, event_patterns, description, tags) VALUES

-- ============================================================================
-- TENANT MANAGEMENT ACTIONS
-- ============================================================================
('create_tenant_schema', 'database_operation', 
 'neo_commons.features.actions.handlers.database.CreateTenantSchemaHandler', 
 ARRAY['tenants.created'], 
 'Creates database schema for new tenant', 
 ARRAY['tenant', 'database']),

('send_tenant_welcome_email', 'email', 
 'neo_commons.features.actions.handlers.email.SendWelcomeEmailHandler', 
 ARRAY['tenants.created'], 
 'Sends welcome email to new tenant admin', 
 ARRAY['tenant', 'email']),

('setup_tenant_keycloak_realm', 'external_api', 
 'neo_commons.features.actions.handlers.external_api.SetupTenantRealmHandler', 
 ARRAY['tenants.created'], 
 'Creates Keycloak realm for tenant', 
 ARRAY['tenant', 'auth']),

('execute_tenant_setup_function', 'function_execution', 
 'neo_commons.features.actions.handlers.function.TenantSetupFunctionHandler', 
 ARRAY['tenants.created'], 
 'Executes custom tenant setup functions', 
 ARRAY['tenant', 'function']),

('notify_tenant_provisioning', 'slack_notification', 
 'neo_commons.features.actions.handlers.slack.TenantProvisioningHandler', 
 ARRAY['tenants.created', 'tenants.provisioning_completed'], 
 'Notifies admin team about tenant provisioning status', 
 ARRAY['tenant', 'slack', 'admin']),

-- ============================================================================
-- USER MANAGEMENT ACTIONS
-- ============================================================================
('send_user_invitation_email', 'email', 
 'neo_commons.features.actions.handlers.email.SendInvitationEmailHandler', 
 ARRAY['users.invited'], 
 'Sends invitation email to new users', 
 ARRAY['user', 'email']),

('send_user_welcome_sms', 'sms', 
 'neo_commons.features.actions.handlers.sms.SendWelcomeSmsHandler', 
 ARRAY['users.created'], 
 'Sends welcome SMS to new users', 
 ARRAY['user', 'sms']),

('setup_user_permissions', 'database_operation', 
 'neo_commons.features.actions.handlers.database.SetupUserPermissionsHandler', 
 ARRAY['users.created'], 
 'Sets up default permissions for new user', 
 ARRAY['user', 'permissions']),

('send_user_push_notification', 'push_notification', 
 'neo_commons.features.actions.handlers.push.SendUserNotificationHandler', 
 ARRAY['users.created', 'users.updated'], 
 'Sends push notifications to users', 
 ARRAY['user', 'push']),

('trigger_user_security_scan', 'security_scan', 
 'neo_commons.features.actions.handlers.security.UserSecurityScanHandler', 
 ARRAY['users.created', 'users.role_changed'], 
 'Triggers security scan when user roles change', 
 ARRAY['user', 'security']),

-- ============================================================================
-- ORGANIZATION MANAGEMENT ACTIONS
-- ============================================================================
('send_organization_webhook', 'webhook', 
 'neo_commons.features.actions.handlers.webhook.OrganizationWebhookHandler', 
 ARRAY['organizations.created', 'organizations.updated'], 
 'Sends organization events to external webhooks', 
 ARRAY['organization', 'webhook']),

('notify_organization_slack', 'slack_notification', 
 'neo_commons.features.actions.handlers.slack.OrganizationSlackHandler', 
 ARRAY['organizations.created'], 
 'Sends organization notifications to Slack', 
 ARRAY['organization', 'slack']),

('sync_organization_crm', 'crm_sync', 
 'neo_commons.features.actions.handlers.crm.OrganizationCrmSyncHandler', 
 ARRAY['organizations.created', 'organizations.updated'], 
 'Syncs organization data with CRM system', 
 ARRAY['organization', 'crm', 'sync']),

('process_organization_billing', 'background_job', 
 'neo_commons.features.actions.handlers.billing.OrganizationBillingHandler', 
 ARRAY['organizations.billing_cycle'], 
 'Processes billing for organizations', 
 ARRAY['organization', 'billing', 'background']),

-- ============================================================================
-- SYSTEM ACTIONS
-- ============================================================================
('invalidate_cache', 'cache_invalidation', 
 'neo_commons.features.actions.handlers.cache.InvalidateCacheHandler', 
 ARRAY['*.updated', '*.deleted'], 
 'Invalidates related cache entries', 
 ARRAY['cache', 'system']),

('warm_cache', 'cache_warming', 
 'neo_commons.features.actions.handlers.cache.WarmCacheHandler', 
 ARRAY['*.created'], 
 'Pre-populates cache for new entities', 
 ARRAY['cache', 'performance']),

('audit_log_event', 'audit_log', 
 'neo_commons.features.actions.handlers.audit.AuditLogHandler', 
 ARRAY['*'], 
 'Logs events for audit trail', 
 ARRAY['audit', 'system']),

('trigger_security_scan', 'security_scan', 
 'neo_commons.features.actions.handlers.security.SecurityScanHandler', 
 ARRAY['*.security_event'], 
 'Triggers security scans on events', 
 ARRAY['security', 'scan']),

('send_monitoring_alert', 'monitoring_alert', 
 'neo_commons.features.actions.handlers.monitoring.MonitoringAlertHandler', 
 ARRAY['system.error', 'system.performance_degraded'], 
 'Sends monitoring alerts for system issues', 
 ARRAY['monitoring', 'alert', 'system']),

('trigger_health_check', 'health_check', 
 'neo_commons.features.actions.handlers.health.HealthCheckHandler', 
 ARRAY['system.health_check_requested'], 
 'Performs comprehensive system health checks', 
 ARRAY['health', 'monitoring', 'system']),

-- ============================================================================
-- REPORTING & ANALYTICS ACTIONS
-- ============================================================================
('generate_monthly_report', 'report_generation', 
 'neo_commons.features.actions.handlers.reporting.MonthlyReportHandler', 
 ARRAY['reports.monthly_requested'], 
 'Generates monthly business reports', 
 ARRAY['reporting', 'business']),

('track_platform_analytics', 'analytics_tracking', 
 'neo_commons.features.actions.handlers.analytics.PlatformAnalyticsHandler', 
 ARRAY['*.created', '*.updated'], 
 'Tracks platform usage analytics', 
 ARRAY['analytics', 'platform', 'tracking']),

('generate_compliance_report', 'report_generation', 
 'neo_commons.features.actions.handlers.reporting.ComplianceReportHandler', 
 ARRAY['compliance.audit_requested'], 
 'Generates compliance and audit reports', 
 ARRAY['compliance', 'reporting', 'audit']),

-- ============================================================================
-- BACKGROUND PROCESSING ACTIONS
-- ============================================================================
('process_payment_batch', 'background_job', 
 'neo_commons.features.actions.handlers.background.PaymentBatchHandler', 
 ARRAY['payments.batch_ready'], 
 'Processes payment batches in background', 
 ARRAY['payment', 'batch']),

('cleanup_expired_data', 'background_job', 
 'neo_commons.features.actions.handlers.cleanup.ExpiredDataCleanupHandler', 
 ARRAY['system.cleanup_scheduled'], 
 'Cleans up expired data and temporary files', 
 ARRAY['cleanup', 'maintenance', 'background']),

('backup_critical_data', 'backup_operation', 
 'neo_commons.features.actions.handlers.backup.CriticalDataBackupHandler', 
 ARRAY['system.backup_scheduled'], 
 'Performs backup of critical system data', 
 ARRAY['backup', 'critical', 'system']),

-- ============================================================================
-- DEPLOYMENT & INFRASTRUCTURE ACTIONS
-- ============================================================================
('trigger_deployment', 'deployment_trigger', 
 'neo_commons.features.actions.handlers.deployment.DeploymentTriggerHandler', 
 ARRAY['deployment.requested'], 
 'Triggers application deployments', 
 ARRAY['deployment', 'infrastructure']),

('scale_infrastructure', 'scaling_operation', 
 'neo_commons.features.actions.handlers.scaling.InfrastructureScalingHandler', 
 ARRAY['system.scaling_required'], 
 'Handles infrastructure scaling operations', 
 ARRAY['scaling', 'infrastructure', 'performance']),

('index_rebuild', 'index_rebuild', 
 'neo_commons.features.actions.handlers.database.IndexRebuildHandler', 
 ARRAY['database.index_rebuild_scheduled'], 
 'Rebuilds database indexes for performance optimization', 
 ARRAY['database', 'performance', 'index']);

-- ============================================================================
-- SEED DATA VERIFICATION
-- ============================================================================

-- Verify that all actions were inserted successfully
DO $$
DECLARE
    action_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO action_count FROM admin.actions;
    RAISE NOTICE 'Successfully seeded % admin actions', action_count;
    
    -- Verify all expected action types are present
    IF EXISTS (
        SELECT 1 FROM admin.actions 
        WHERE action_type IN (
            'email', 'sms', 'push_notification', 'webhook', 'slack_notification',
            'database_operation', 'function_execution', 'background_job',
            'cache_invalidation', 'cache_warming', 'audit_log', 'security_scan',
            'monitoring_alert', 'health_check', 'report_generation', 
            'analytics_tracking', 'backup_operation', 'deployment_trigger',
            'scaling_operation', 'index_rebuild', 'crm_sync'
        )
    ) THEN
        RAISE NOTICE 'All expected action types are present';
    ELSE
        RAISE WARNING 'Some expected action types may be missing';
    END IF;
END $$;

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON SCHEMA admin IS 'Admin schema containing platform-wide event and action management with seed data';