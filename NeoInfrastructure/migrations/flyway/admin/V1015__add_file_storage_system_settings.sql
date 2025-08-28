-- V1015: File Storage System Settings
-- Adds file storage configuration to admin system settings
-- Applied to: Admin database only

-- ============================================================================
-- FILE STORAGE SYSTEM SETTINGS
-- ============================================================================

-- Insert file storage system settings for platform-wide defaults
INSERT INTO admin.system_settings (
    tenant_id, setting_key, setting_value, setting_type, category, description, is_public
) VALUES

-- Storage Provider Configuration
(NULL, 'file_storage.default_provider', '"local"', 'select', 'file_storage', 'Default file storage provider (local, s3)', false),
(NULL, 'file_storage.providers_enabled', '["local", "s3"]', 'array', 'file_storage', 'Enabled storage providers for the platform', false),

-- Local Storage Configuration
(NULL, 'file_storage.local.base_path', '"/app/storage/files"', 'string', 'file_storage', 'Base directory for local file storage', false),
(NULL, 'file_storage.local.max_file_size_mb', '100', 'number', 'file_storage', 'Maximum file size in MB for local storage', false),
(NULL, 'file_storage.local.url_prefix', '"/files"', 'string', 'file_storage', 'URL prefix for serving local files', false),

-- S3 Storage Configuration
(NULL, 'file_storage.s3.default_bucket', '"neofast-files"', 'string', 'file_storage', 'Default S3 bucket name', false),
(NULL, 'file_storage.s3.default_region', '"us-east-1"', 'string', 'file_storage', 'Default S3 region', false),
(NULL, 'file_storage.s3.max_file_size_mb', '500', 'number', 'file_storage', 'Maximum file size in MB for S3 storage', false),
(NULL, 'file_storage.s3.presigned_url_expiry_minutes', '60', 'number', 'file_storage', 'Presigned URL expiry time in minutes', false),
(NULL, 'file_storage.s3.multipart_threshold_mb', '10', 'number', 'file_storage', 'File size threshold for multipart uploads in MB', false),
(NULL, 'file_storage.s3.use_cloudfront', 'false', 'boolean', 'file_storage', 'Use CloudFront for S3 file delivery', false),
(NULL, 'file_storage.s3.cloudfront_domain', '""', 'string', 'file_storage', 'CloudFront domain name for file delivery', false),

-- File Upload Configuration
(NULL, 'file_upload.max_file_size_mb', '100', 'number', 'file_upload', 'Global maximum file size in MB', false),
(NULL, 'file_upload.chunk_size_mb', '1', 'number', 'file_upload', 'Default chunk size for resumable uploads in MB', false),
(NULL, 'file_upload.session_timeout_hours', '24', 'number', 'file_upload', 'Upload session timeout in hours', false),
(NULL, 'file_upload.max_concurrent_uploads', '5', 'number', 'file_upload', 'Maximum concurrent uploads per user', false),
(NULL, 'file_upload.allowed_mime_types', '["image/jpeg", "image/png", "image/gif", "image/webp", "application/pdf", "text/plain", "text/csv", "application/json", "application/xml"]', 'array', 'file_upload', 'Allowed MIME types for file uploads', false),
(NULL, 'file_upload.blocked_extensions', '[".exe", ".bat", ".cmd", ".com", ".scr", ".vbs", ".js"]', 'array', 'file_upload', 'Blocked file extensions for security', false),

-- File Processing Configuration
(NULL, 'file_processing.enable_virus_scanning', 'true', 'boolean', 'file_processing', 'Enable virus scanning for uploaded files', false),
(NULL, 'file_processing.virus_scanner', '"clamav"', 'select', 'file_processing', 'Virus scanner to use (clamav, dummy)', false),
(NULL, 'file_processing.enable_thumbnails', 'true', 'boolean', 'file_processing', 'Enable thumbnail generation for images', false),
(NULL, 'file_processing.thumbnail_sizes', '[{"name": "small", "width": 150, "height": 150}, {"name": "medium", "width": 300, "height": 300}, {"name": "large", "width": 600, "height": 600}]', 'json', 'file_processing', 'Thumbnail size configurations', false),
(NULL, 'file_processing.image_max_dimensions', '{"width": 4096, "height": 4096}', 'json', 'file_processing', 'Maximum image dimensions (auto-resize)', false),

-- File Access and Security
(NULL, 'file_security.default_access_level', '"private"', 'select', 'file_security', 'Default file access level (private, public, tenant)', false),
(NULL, 'file_security.enable_public_files', 'true', 'boolean', 'file_security', 'Allow public file access', false),
(NULL, 'file_security.public_file_max_size_mb', '10', 'number', 'file_security', 'Maximum size for public files in MB', false),
(NULL, 'file_security.scan_timeout_seconds', '30', 'number', 'file_security', 'Timeout for virus scanning in seconds', false),
(NULL, 'file_security.quarantine_infected_files', 'true', 'boolean', 'file_security', 'Quarantine infected files instead of deleting', false),

-- File Sharing Configuration
(NULL, 'file_sharing.enable_public_shares', 'true', 'boolean', 'file_sharing', 'Enable public file sharing', false),
(NULL, 'file_sharing.default_share_expiry_days', '30', 'number', 'file_sharing', 'Default expiry for file shares in days', false),
(NULL, 'file_sharing.max_share_expiry_days', '365', 'number', 'file_sharing', 'Maximum allowed expiry for file shares in days', false),
(NULL, 'file_sharing.enable_password_protection', 'true', 'boolean', 'file_sharing', 'Enable password-protected file shares', false),
(NULL, 'file_sharing.max_downloads_per_share', '1000', 'number', 'file_sharing', 'Maximum downloads per file share', false),

-- File Retention and Cleanup
(NULL, 'file_retention.default_policy', '"standard"', 'select', 'file_retention', 'Default file retention policy (standard, extended, permanent)', false),
(NULL, 'file_retention.temp_file_cleanup_hours', '24', 'number', 'file_retention', 'Hours before temporary files are cleaned up', false),
(NULL, 'file_retention.failed_upload_cleanup_hours', '72', 'number', 'file_retention', 'Hours before failed upload sessions are cleaned up', false),
(NULL, 'file_retention.deleted_file_retention_days', '30', 'number', 'file_retention', 'Days to retain soft-deleted files before permanent deletion', false),
(NULL, 'file_retention.version_history_limit', '10', 'number', 'file_retention', 'Maximum number of file versions to retain', false),

-- Storage Quotas
(NULL, 'storage_quota.default_tenant_quota_gb', '10', 'number', 'storage_quota', 'Default storage quota per tenant in GB', false),
(NULL, 'storage_quota.default_user_quota_gb', '1', 'number', 'storage_quota', 'Default storage quota per user in GB', false),
(NULL, 'storage_quota.enable_quota_enforcement', 'true', 'boolean', 'storage_quota', 'Enable storage quota enforcement', false),
(NULL, 'storage_quota.quota_warning_threshold', '0.8', 'number', 'storage_quota', 'Quota usage threshold for warnings (0.0-1.0)', false),

-- Performance and Optimization
(NULL, 'file_performance.enable_cdn', 'false', 'boolean', 'file_performance', 'Enable CDN for file delivery', false),
(NULL, 'file_performance.cache_static_files_seconds', '86400', 'number', 'file_performance', 'Cache duration for static files in seconds', false),
(NULL, 'file_performance.enable_compression', 'true', 'boolean', 'file_performance', 'Enable file compression for storage', false),
(NULL, 'file_performance.max_parallel_uploads', '3', 'number', 'file_performance', 'Maximum parallel uploads per user', false),

-- Audit and Monitoring
(NULL, 'file_audit.log_file_access', 'true', 'boolean', 'file_audit', 'Log file access events for audit', false),
(NULL, 'file_audit.log_upload_events', 'true', 'boolean', 'file_audit', 'Log file upload events for audit', false),
(NULL, 'file_audit.log_deletion_events', 'true', 'boolean', 'file_audit', 'Log file deletion events for audit', false),
(NULL, 'file_audit.retention_days', '365', 'number', 'file_audit', 'Days to retain file audit logs', false)

-- Handle conflicts by doing nothing (preserve existing settings)
ON CONFLICT (setting_key) WHERE tenant_id IS NULL DO NOTHING;

-- ============================================================================
-- STORAGE QUOTA MANAGEMENT FUNCTIONS
-- ============================================================================

-- Function to calculate storage usage for a tenant
CREATE OR REPLACE FUNCTION admin.calculate_tenant_storage_usage(p_tenant_id UUID)
RETURNS BIGINT AS $$
DECLARE
    usage_bytes BIGINT;
BEGIN
    -- Calculate total file size for the tenant
    SELECT COALESCE(SUM(file_size), 0)
    INTO usage_bytes
    FROM admin.files 
    WHERE tenant_id = p_tenant_id 
      AND deleted_at IS NULL;
    
    RETURN usage_bytes;
END;
$$ LANGUAGE plpgsql;

-- Function to check if tenant is over storage quota
CREATE OR REPLACE FUNCTION admin.check_tenant_storage_quota(
    p_tenant_id UUID,
    p_additional_bytes BIGINT DEFAULT 0
)
RETURNS BOOLEAN AS $$
DECLARE
    quota_gb NUMERIC;
    quota_bytes BIGINT;
    current_usage_bytes BIGINT;
    total_usage_bytes BIGINT;
BEGIN
    -- Get tenant's storage quota (with fallback to default)
    quota_gb := COALESCE(
        (admin.get_setting(p_tenant_id, 'storage_quota.tenant_quota_gb')::TEXT)::NUMERIC,
        (admin.get_setting(NULL, 'storage_quota.default_tenant_quota_gb')::TEXT)::NUMERIC
    );
    
    -- Convert GB to bytes
    quota_bytes := (quota_gb * 1024 * 1024 * 1024)::BIGINT;
    
    -- Get current usage
    current_usage_bytes := admin.calculate_tenant_storage_usage(p_tenant_id);
    
    -- Calculate total usage with additional bytes
    total_usage_bytes := current_usage_bytes + p_additional_bytes;
    
    -- Return true if under quota, false if over quota
    RETURN total_usage_bytes <= quota_bytes;
END;
$$ LANGUAGE plpgsql;

-- Function to get storage quota information for a tenant
CREATE OR REPLACE FUNCTION admin.get_tenant_storage_info(p_tenant_id UUID)
RETURNS JSON AS $$
DECLARE
    quota_gb NUMERIC;
    quota_bytes BIGINT;
    used_bytes BIGINT;
    warning_threshold NUMERIC;
    result JSON;
BEGIN
    -- Get quota and usage information
    quota_gb := COALESCE(
        (admin.get_setting(p_tenant_id, 'storage_quota.tenant_quota_gb')::TEXT)::NUMERIC,
        (admin.get_setting(NULL, 'storage_quota.default_tenant_quota_gb')::TEXT)::NUMERIC
    );
    
    quota_bytes := (quota_gb * 1024 * 1024 * 1024)::BIGINT;
    used_bytes := admin.calculate_tenant_storage_usage(p_tenant_id);
    
    warning_threshold := COALESCE(
        (admin.get_setting(p_tenant_id, 'storage_quota.quota_warning_threshold')::TEXT)::NUMERIC,
        (admin.get_setting(NULL, 'storage_quota.quota_warning_threshold')::TEXT)::NUMERIC,
        0.8
    );
    
    -- Build result JSON
    result := json_build_object(
        'tenant_id', p_tenant_id,
        'quota_gb', quota_gb,
        'quota_bytes', quota_bytes,
        'used_bytes', used_bytes,
        'used_gb', ROUND(used_bytes / (1024.0 * 1024.0 * 1024.0), 2),
        'usage_percentage', CASE 
            WHEN quota_bytes > 0 THEN ROUND((used_bytes::NUMERIC / quota_bytes::NUMERIC) * 100, 2)
            ELSE 0
        END,
        'available_bytes', GREATEST(0, quota_bytes - used_bytes),
        'available_gb', ROUND(GREATEST(0, quota_bytes - used_bytes) / (1024.0 * 1024.0 * 1024.0), 2),
        'is_over_quota', used_bytes > quota_bytes,
        'is_over_warning_threshold', used_bytes > (quota_bytes * warning_threshold)
    );
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FILE CONFIGURATION HELPER FUNCTIONS
-- ============================================================================

-- Function to check if a MIME type is allowed
CREATE OR REPLACE FUNCTION admin.is_mime_type_allowed(
    p_tenant_id UUID,
    p_mime_type VARCHAR
)
RETURNS BOOLEAN AS $$
DECLARE
    allowed_types JSONB;
BEGIN
    -- Get allowed MIME types (tenant-specific or platform default)
    allowed_types := COALESCE(
        admin.get_setting(p_tenant_id, 'file_upload.allowed_mime_types'),
        admin.get_setting(NULL, 'file_upload.allowed_mime_types')
    );
    
    -- Check if MIME type is in the allowed list
    RETURN allowed_types ? p_mime_type;
END;
$$ LANGUAGE plpgsql;

-- Function to check if a file extension is blocked
CREATE OR REPLACE FUNCTION admin.is_extension_blocked(
    p_tenant_id UUID,
    p_filename VARCHAR
)
RETURNS BOOLEAN AS $$
DECLARE
    blocked_extensions JSONB;
    file_extension VARCHAR;
BEGIN
    -- Extract file extension
    file_extension := LOWER('.' || SPLIT_PART(p_filename, '.', -1));
    
    -- Get blocked extensions (tenant-specific or platform default)
    blocked_extensions := COALESCE(
        admin.get_setting(p_tenant_id, 'file_upload.blocked_extensions'),
        admin.get_setting(NULL, 'file_upload.blocked_extensions')
    );
    
    -- Check if extension is in the blocked list
    RETURN blocked_extensions ? file_extension;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON FUNCTION admin.calculate_tenant_storage_usage(UUID) IS 'Calculate total storage usage in bytes for a tenant';
COMMENT ON FUNCTION admin.check_tenant_storage_quota(UUID, BIGINT) IS 'Check if tenant would exceed storage quota with additional bytes';
COMMENT ON FUNCTION admin.get_tenant_storage_info(UUID) IS 'Get comprehensive storage quota information for a tenant';
COMMENT ON FUNCTION admin.is_mime_type_allowed(UUID, VARCHAR) IS 'Check if a MIME type is allowed for uploads';
COMMENT ON FUNCTION admin.is_extension_blocked(UUID, VARCHAR) IS 'Check if a file extension is blocked for uploads';

-- Log migration completion
SELECT 'V1015: File storage system settings and quota management added' as migration_status;