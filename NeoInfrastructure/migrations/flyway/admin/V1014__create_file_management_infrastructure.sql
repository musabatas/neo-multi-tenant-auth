-- V1014: File Management Infrastructure
-- Creates file management tables and types for platform-level file storage
-- Applied to: Admin database only

-- ============================================================================
-- FILE MANAGEMENT ENUM TYPES
-- ============================================================================

-- Storage provider types (local and S3 only for now)
CREATE TYPE admin.storage_provider AS ENUM (
    'local', 's3'
);

-- File access levels
CREATE TYPE admin.file_access_level AS ENUM (
    'private', 'public', 'tenant'
);

-- Virus scan status
CREATE TYPE admin.virus_scan_status AS ENUM (
    'pending', 'clean', 'infected', 'failed', 'skipped'
);

-- Upload session status
CREATE TYPE admin.upload_session_status AS ENUM (
    'active', 'completed', 'failed', 'expired'
);

-- ============================================================================
-- FILES (Platform-level file metadata)
-- ============================================================================

CREATE TABLE admin.files (
    -- Core Identity
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    file_name VARCHAR(255) NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    
    -- Storage Configuration
    storage_provider admin.storage_provider NOT NULL DEFAULT 'local',
    storage_key TEXT NOT NULL, -- S3 key or local file path
    storage_bucket VARCHAR(255), -- S3 bucket name (NULL for local)
    storage_region VARCHAR(50), -- S3 region (NULL for local)
    storage_metadata JSONB DEFAULT '{}',
    
    -- File Properties
    mime_type VARCHAR(100) NOT NULL,
    file_size BIGINT NOT NULL,
    checksum_sha256 CHAR(64),
    
    -- Context and Ownership
    upload_session_id UUID,
    uploaded_by_user_id UUID,
    tenant_id UUID, -- NULL for admin files
    organization_id UUID REFERENCES admin.organizations(id) ON DELETE SET NULL,
    
    -- File Metadata and Categorization
    file_metadata JSONB DEFAULT '{}', -- EXIF, dimensions, etc.
    tags TEXT[], -- Searchable file tags
    category VARCHAR(100), -- File category for organization
    description TEXT,
    
    -- Security and Scanning
    virus_scan_status admin.virus_scan_status DEFAULT 'pending',
    virus_scan_at TIMESTAMPTZ,
    virus_scan_result JSONB DEFAULT '{}',
    access_level admin.file_access_level DEFAULT 'private',
    
    -- Lifecycle Management
    is_temporary BOOLEAN DEFAULT false, -- For temp files cleanup
    retention_policy VARCHAR(50) DEFAULT 'standard',
    auto_delete_at TIMESTAMPTZ, -- Automatic deletion date
    
    -- Audit Fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ, -- Soft delete
    
    -- Constraints
    CONSTRAINT files_size_positive CHECK (file_size > 0),
    CONSTRAINT files_name_not_empty CHECK (length(trim(file_name)) > 0),
    CONSTRAINT files_original_name_not_empty CHECK (length(trim(original_name)) > 0),
    CONSTRAINT files_storage_key_not_empty CHECK (length(trim(storage_key)) > 0),
    CONSTRAINT files_s3_bucket_required CHECK (
        (storage_provider = 's3' AND storage_bucket IS NOT NULL AND length(trim(storage_bucket)) > 0) OR 
        (storage_provider = 'local')
    )
);

-- Indexes for files table
CREATE INDEX idx_files_tenant_id ON admin.files(tenant_id) WHERE tenant_id IS NOT NULL;
CREATE INDEX idx_files_organization_id ON admin.files(organization_id) WHERE organization_id IS NOT NULL;
CREATE INDEX idx_files_uploaded_by ON admin.files(uploaded_by_user_id) WHERE uploaded_by_user_id IS NOT NULL;
CREATE INDEX idx_files_storage_provider ON admin.files(storage_provider);
CREATE INDEX idx_files_mime_type ON admin.files(mime_type);
CREATE INDEX idx_files_created_at ON admin.files(created_at);
CREATE INDEX idx_files_file_name ON admin.files(file_name);
CREATE INDEX idx_files_original_name ON admin.files(original_name);
CREATE INDEX idx_files_tags ON admin.files USING GIN(tags) WHERE tags IS NOT NULL;
CREATE INDEX idx_files_storage_key ON admin.files(storage_key);
CREATE INDEX idx_files_access_level ON admin.files(access_level);
CREATE INDEX idx_files_virus_scan_status ON admin.files(virus_scan_status);
CREATE INDEX idx_files_category ON admin.files(category) WHERE category IS NOT NULL;
CREATE INDEX idx_files_is_temporary ON admin.files(is_temporary) WHERE is_temporary = true;
CREATE INDEX idx_files_auto_delete ON admin.files(auto_delete_at) WHERE auto_delete_at IS NOT NULL;
CREATE INDEX idx_files_deleted ON admin.files(deleted_at) WHERE deleted_at IS NOT NULL;

-- Unique constraint on storage key per provider
CREATE UNIQUE INDEX idx_files_unique_storage_key ON admin.files(storage_provider, storage_key) WHERE deleted_at IS NULL;

-- ============================================================================
-- UPLOAD SESSIONS (Chunked/resumable upload tracking)
-- ============================================================================

CREATE TABLE admin.upload_sessions (
    -- Core Identity
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    session_key VARCHAR(255) UNIQUE NOT NULL,
    
    -- File Information
    original_filename VARCHAR(255) NOT NULL,
    expected_size BIGINT NOT NULL,
    expected_checksum_sha256 CHAR(64), -- Optional checksum validation
    mime_type VARCHAR(100),
    
    -- Chunking Configuration
    chunk_size INTEGER NOT NULL DEFAULT 1048576, -- 1MB chunks
    total_chunks INTEGER NOT NULL,
    uploaded_chunks INTEGER DEFAULT 0,
    uploaded_bytes BIGINT DEFAULT 0,
    
    -- Storage Configuration
    upload_path TEXT,
    storage_provider admin.storage_provider NOT NULL DEFAULT 'local',
    storage_bucket VARCHAR(255), -- S3 bucket for multipart upload
    multipart_upload_id TEXT, -- S3 multipart upload ID
    
    -- Context and Ownership
    uploaded_by_user_id UUID NOT NULL,
    tenant_id UUID,
    organization_id UUID REFERENCES admin.organizations(id) ON DELETE SET NULL,
    
    -- Session Management
    status admin.upload_session_status DEFAULT 'active',
    session_metadata JSONB DEFAULT '{}',
    upload_metadata JSONB DEFAULT '{}', -- Client-provided metadata
    
    -- Progress Tracking
    last_chunk_uploaded_at TIMESTAMPTZ,
    progress_percentage SMALLINT GENERATED ALWAYS AS (
        CASE 
            WHEN total_chunks > 0 THEN (uploaded_chunks * 100 / total_chunks)::SMALLINT
            ELSE 0
        END
    ) STORED,
    
    -- Lifecycle Management
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours'),
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    failure_reason TEXT,
    
    -- Audit Fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT upload_sessions_size_positive CHECK (expected_size > 0),
    CONSTRAINT upload_sessions_chunks_positive CHECK (total_chunks > 0),
    CONSTRAINT upload_sessions_chunk_size_positive CHECK (chunk_size > 0),
    CONSTRAINT upload_sessions_uploaded_chunks_valid CHECK (uploaded_chunks >= 0 AND uploaded_chunks <= total_chunks),
    CONSTRAINT upload_sessions_uploaded_bytes_valid CHECK (uploaded_bytes >= 0 AND uploaded_bytes <= expected_size),
    CONSTRAINT upload_sessions_filename_not_empty CHECK (length(trim(original_filename)) > 0),
    CONSTRAINT upload_sessions_user_not_null CHECK (uploaded_by_user_id IS NOT NULL),
    CONSTRAINT upload_sessions_s3_bucket_required CHECK (
        (storage_provider = 's3' AND storage_bucket IS NOT NULL AND length(trim(storage_bucket)) > 0) OR 
        (storage_provider = 'local')
    )
);

-- Indexes for upload_sessions table
CREATE INDEX idx_upload_sessions_user ON admin.upload_sessions(uploaded_by_user_id);
CREATE INDEX idx_upload_sessions_tenant ON admin.upload_sessions(tenant_id) WHERE tenant_id IS NOT NULL;
CREATE INDEX idx_upload_sessions_organization ON admin.upload_sessions(organization_id) WHERE organization_id IS NOT NULL;
CREATE INDEX idx_upload_sessions_status ON admin.upload_sessions(status);
CREATE INDEX idx_upload_sessions_expires ON admin.upload_sessions(expires_at);
CREATE INDEX idx_upload_sessions_created ON admin.upload_sessions(created_at);
CREATE INDEX idx_upload_sessions_storage_provider ON admin.upload_sessions(storage_provider);
CREATE UNIQUE INDEX idx_upload_sessions_key ON admin.upload_sessions(session_key);

-- Index for cleanup operations (expired or failed sessions)
CREATE INDEX idx_upload_sessions_cleanup ON admin.upload_sessions(status, expires_at) 
WHERE status IN ('expired', 'failed');

-- ============================================================================
-- FILE VERSIONS (File version history tracking)
-- ============================================================================

CREATE TABLE admin.file_versions (
    -- Core Identity
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    file_id UUID NOT NULL REFERENCES admin.files(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    
    -- Version Properties
    file_size BIGINT NOT NULL,
    checksum_sha256 CHAR(64),
    storage_key TEXT NOT NULL, -- Different storage key per version
    
    -- Version Metadata
    version_metadata JSONB DEFAULT '{}',
    change_description TEXT,
    is_current BOOLEAN DEFAULT false, -- Only one current version per file
    
    -- Context
    created_by_user_id UUID,
    
    -- Audit Fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT file_versions_size_positive CHECK (file_size > 0),
    CONSTRAINT file_versions_version_positive CHECK (version_number > 0),
    CONSTRAINT file_versions_storage_key_not_empty CHECK (length(trim(storage_key)) > 0)
);

-- Indexes for file_versions table
CREATE INDEX idx_file_versions_file_id ON admin.file_versions(file_id);
CREATE INDEX idx_file_versions_version ON admin.file_versions(file_id, version_number);
CREATE INDEX idx_file_versions_current ON admin.file_versions(file_id, is_current) WHERE is_current = true;
CREATE INDEX idx_file_versions_created_by ON admin.file_versions(created_by_user_id) WHERE created_by_user_id IS NOT NULL;
CREATE INDEX idx_file_versions_created_at ON admin.file_versions(created_at);

-- Ensure only one current version per file
CREATE UNIQUE INDEX idx_file_versions_unique_current ON admin.file_versions(file_id) 
WHERE is_current = true;

-- Ensure unique version numbers per file
CREATE UNIQUE INDEX idx_file_versions_unique_number ON admin.file_versions(file_id, version_number);

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================

CREATE TRIGGER update_files_updated_at
    BEFORE UPDATE ON admin.files
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_upload_sessions_updated_at
    BEFORE UPDATE ON admin.upload_sessions
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

-- ============================================================================
-- FUNCTIONS FOR FILE MANAGEMENT
-- ============================================================================

-- Function to clean up expired upload sessions
CREATE OR REPLACE FUNCTION admin.cleanup_expired_upload_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Mark expired sessions as expired
    UPDATE admin.upload_sessions 
    SET status = 'expired', updated_at = NOW()
    WHERE status = 'active' AND expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to update upload session progress
CREATE OR REPLACE FUNCTION admin.update_upload_progress(
    p_session_id UUID,
    p_chunk_number INTEGER,
    p_chunk_size_bytes INTEGER
)
RETURNS BOOLEAN AS $$
DECLARE
    updated_rows INTEGER;
BEGIN
    UPDATE admin.upload_sessions 
    SET 
        uploaded_chunks = uploaded_chunks + 1,
        uploaded_bytes = uploaded_bytes + p_chunk_size_bytes,
        last_chunk_uploaded_at = NOW(),
        updated_at = NOW()
    WHERE id = p_session_id 
      AND status = 'active'
      AND uploaded_chunks < total_chunks;
    
    GET DIAGNOSTICS updated_rows = ROW_COUNT;
    
    -- Mark as completed if all chunks uploaded
    IF updated_rows > 0 THEN
        UPDATE admin.upload_sessions 
        SET 
            status = 'completed',
            completed_at = NOW(),
            updated_at = NOW()
        WHERE id = p_session_id 
          AND uploaded_chunks = total_chunks
          AND status = 'active';
    END IF;
    
    RETURN updated_rows > 0;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE admin.files IS 'Platform-level file metadata and storage information';
COMMENT ON TABLE admin.upload_sessions IS 'Chunked and resumable upload session tracking';
COMMENT ON TABLE admin.file_versions IS 'File version history and change tracking';

COMMENT ON COLUMN admin.files.storage_key IS 'S3 object key or local file path relative to storage root';
COMMENT ON COLUMN admin.files.file_metadata IS 'File-specific metadata like EXIF data, dimensions, etc.';
COMMENT ON COLUMN admin.files.tags IS 'Searchable tags for file categorization and discovery';
COMMENT ON COLUMN admin.files.is_temporary IS 'Temporary files for cleanup processes';

COMMENT ON COLUMN admin.upload_sessions.session_key IS 'Unique session identifier for client-server coordination';
COMMENT ON COLUMN admin.upload_sessions.multipart_upload_id IS 'S3 multipart upload ID for large file uploads';
COMMENT ON COLUMN admin.upload_sessions.progress_percentage IS 'Automatically calculated upload progress';

COMMENT ON FUNCTION admin.cleanup_expired_upload_sessions() IS 'Marks expired upload sessions for cleanup';
COMMENT ON FUNCTION admin.update_upload_progress(UUID, INTEGER, INTEGER) IS 'Updates upload session progress and handles completion';

-- Log migration completion
SELECT 'V1014: File management infrastructure created in admin database' as migration_status;