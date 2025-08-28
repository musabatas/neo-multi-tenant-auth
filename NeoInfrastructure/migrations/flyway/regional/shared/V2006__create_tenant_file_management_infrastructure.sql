-- V2006: Tenant File Management Infrastructure
-- Creates file management tables for tenant template schema
-- Applied to: Regional shared databases (both US and EU)
-- Placeholders: ${region}, ${gdpr}

-- ============================================================================
-- TENANT FILE MANAGEMENT ENUM TYPES
-- ============================================================================

-- Storage provider types (local and S3 only for now)
CREATE TYPE tenant_template.storage_provider AS ENUM (
    'local', 's3'
);

-- File access levels (tenant-scoped)
CREATE TYPE tenant_template.file_access_level AS ENUM (
    'private', 'public', 'team', 'internal'
);

-- Virus scan status
CREATE TYPE tenant_template.virus_scan_status AS ENUM (
    'pending', 'clean', 'infected', 'failed', 'skipped'
);

-- Upload session status
CREATE TYPE tenant_template.upload_session_status AS ENUM (
    'active', 'completed', 'failed', 'expired'
);

-- ============================================================================
-- TENANT FILES (Tenant-specific file metadata)
-- ============================================================================

CREATE TABLE tenant_template.files (
    -- Core Identity
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    file_name VARCHAR(255) NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    
    -- Storage Configuration
    storage_provider tenant_template.storage_provider NOT NULL DEFAULT 'local',
    storage_key TEXT NOT NULL, -- S3 key or local file path
    storage_bucket VARCHAR(255), -- S3 bucket name (NULL for local)
    storage_region VARCHAR(50), -- S3 region (NULL for local)
    storage_metadata JSONB DEFAULT '{}',
    
    -- File Properties
    mime_type VARCHAR(100) NOT NULL,
    file_size BIGINT NOT NULL,
    checksum_sha256 CHAR(64),
    
    -- Context and Ownership (tenant-scoped)
    upload_session_id UUID,
    uploaded_by_user_id UUID REFERENCES tenant_template.users(id) ON DELETE SET NULL,
    team_id UUID REFERENCES tenant_template.teams(id) ON DELETE SET NULL, -- Team association
    
    -- File Metadata and Categorization
    file_metadata JSONB DEFAULT '{}', -- EXIF, dimensions, etc.
    tags TEXT[], -- Searchable file tags
    category VARCHAR(100), -- File category for organization
    description TEXT,
    alt_text TEXT, -- Alternative text for accessibility
    
    -- Security and Scanning
    virus_scan_status tenant_template.virus_scan_status DEFAULT 'pending',
    virus_scan_at TIMESTAMPTZ,
    virus_scan_result JSONB DEFAULT '{}',
    access_level tenant_template.file_access_level DEFAULT 'private',
    
    -- Permissions and Sharing
    is_public BOOLEAN DEFAULT false,
    public_url_expires_at TIMESTAMPTZ, -- For temporary public URLs
    download_count INTEGER DEFAULT 0, -- Track download statistics
    view_count INTEGER DEFAULT 0, -- Track view statistics
    
    -- Content Management
    parent_folder_id UUID REFERENCES tenant_template.files(id) ON DELETE CASCADE, -- For folder structure
    is_folder BOOLEAN DEFAULT false, -- Distinguish files from folders
    folder_path TEXT, -- Full folder path for navigation
    
    -- Lifecycle Management
    is_temporary BOOLEAN DEFAULT false, -- For temp files cleanup
    retention_policy VARCHAR(50) DEFAULT 'standard',
    auto_delete_at TIMESTAMPTZ, -- Automatic deletion date
    archived_at TIMESTAMPTZ, -- Archive date
    
    -- Version Control
    version_number INTEGER DEFAULT 1,
    is_current_version BOOLEAN DEFAULT true,
    parent_version_id UUID REFERENCES tenant_template.files(id) ON DELETE SET NULL,
    
    -- Audit Fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ, -- Soft delete
    
    -- Constraints
    CONSTRAINT tenant_files_size_positive CHECK (file_size > 0),
    CONSTRAINT tenant_files_name_not_empty CHECK (length(trim(file_name)) > 0),
    CONSTRAINT tenant_files_original_name_not_empty CHECK (length(trim(original_name)) > 0),
    CONSTRAINT tenant_files_storage_key_not_empty CHECK (length(trim(storage_key)) > 0),
    CONSTRAINT tenant_files_version_positive CHECK (version_number > 0),
    CONSTRAINT tenant_files_download_count_positive CHECK (download_count >= 0),
    CONSTRAINT tenant_files_view_count_positive CHECK (view_count >= 0),
    CONSTRAINT tenant_files_folder_constraints CHECK (
        (is_folder = true AND file_size = 0 AND mime_type = 'application/x-directory') OR
        (is_folder = false)
    ),
    CONSTRAINT tenant_files_s3_bucket_required CHECK (
        (storage_provider = 's3' AND storage_bucket IS NOT NULL AND length(trim(storage_bucket)) > 0) OR 
        (storage_provider = 'local')
    )
);

-- Indexes for tenant files table
CREATE INDEX idx_tenant_files_uploaded_by ON tenant_template.files(uploaded_by_user_id) WHERE uploaded_by_user_id IS NOT NULL;
CREATE INDEX idx_tenant_files_team_id ON tenant_template.files(team_id) WHERE team_id IS NOT NULL;
CREATE INDEX idx_tenant_files_storage_provider ON tenant_template.files(storage_provider);
CREATE INDEX idx_tenant_files_mime_type ON tenant_template.files(mime_type);
CREATE INDEX idx_tenant_files_created_at ON tenant_template.files(created_at);
CREATE INDEX idx_tenant_files_file_name ON tenant_template.files(file_name);
CREATE INDEX idx_tenant_files_original_name ON tenant_template.files(original_name);
CREATE INDEX idx_tenant_files_tags ON tenant_template.files USING GIN(tags) WHERE tags IS NOT NULL;
CREATE INDEX idx_tenant_files_storage_key ON tenant_template.files(storage_key);
CREATE INDEX idx_tenant_files_access_level ON tenant_template.files(access_level);
CREATE INDEX idx_tenant_files_virus_scan_status ON tenant_template.files(virus_scan_status);
CREATE INDEX idx_tenant_files_category ON tenant_template.files(category) WHERE category IS NOT NULL;
CREATE INDEX idx_tenant_files_is_temporary ON tenant_template.files(is_temporary) WHERE is_temporary = true;
CREATE INDEX idx_tenant_files_is_folder ON tenant_template.files(is_folder);
CREATE INDEX idx_tenant_files_parent_folder ON tenant_template.files(parent_folder_id) WHERE parent_folder_id IS NOT NULL;
CREATE INDEX idx_tenant_files_is_public ON tenant_template.files(is_public) WHERE is_public = true;
CREATE INDEX idx_tenant_files_auto_delete ON tenant_template.files(auto_delete_at) WHERE auto_delete_at IS NOT NULL;
CREATE INDEX idx_tenant_files_archived ON tenant_template.files(archived_at) WHERE archived_at IS NOT NULL;
CREATE INDEX idx_tenant_files_deleted ON tenant_template.files(deleted_at) WHERE deleted_at IS NOT NULL;
CREATE INDEX idx_tenant_files_current_version ON tenant_template.files(parent_version_id, is_current_version) WHERE is_current_version = true;

-- Unique constraint on storage key per provider (within tenant)
CREATE UNIQUE INDEX idx_tenant_files_unique_storage_key ON tenant_template.files(storage_provider, storage_key) WHERE deleted_at IS NULL;

-- Ensure folder hierarchy consistency
CREATE INDEX idx_tenant_files_folder_path ON tenant_template.files(folder_path) WHERE folder_path IS NOT NULL;

-- ============================================================================
-- TENANT UPLOAD SESSIONS (Chunked/resumable upload tracking)
-- ============================================================================

CREATE TABLE tenant_template.upload_sessions (
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
    storage_provider tenant_template.storage_provider NOT NULL DEFAULT 'local',
    storage_bucket VARCHAR(255), -- S3 bucket for multipart upload
    multipart_upload_id TEXT, -- S3 multipart upload ID
    
    -- Context and Ownership (tenant-scoped)
    uploaded_by_user_id UUID NOT NULL REFERENCES tenant_template.users(id) ON DELETE CASCADE,
    team_id UUID REFERENCES tenant_template.teams(id) ON DELETE SET NULL,
    target_folder_id UUID REFERENCES tenant_template.files(id) ON DELETE SET NULL,
    
    -- Session Management
    status tenant_template.upload_session_status DEFAULT 'active',
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
    CONSTRAINT tenant_upload_sessions_size_positive CHECK (expected_size > 0),
    CONSTRAINT tenant_upload_sessions_chunks_positive CHECK (total_chunks > 0),
    CONSTRAINT tenant_upload_sessions_chunk_size_positive CHECK (chunk_size > 0),
    CONSTRAINT tenant_upload_sessions_uploaded_chunks_valid CHECK (uploaded_chunks >= 0 AND uploaded_chunks <= total_chunks),
    CONSTRAINT tenant_upload_sessions_uploaded_bytes_valid CHECK (uploaded_bytes >= 0 AND uploaded_bytes <= expected_size),
    CONSTRAINT tenant_upload_sessions_filename_not_empty CHECK (length(trim(original_filename)) > 0),
    CONSTRAINT tenant_upload_sessions_user_not_null CHECK (uploaded_by_user_id IS NOT NULL),
    CONSTRAINT tenant_upload_sessions_s3_bucket_required CHECK (
        (storage_provider = 's3' AND storage_bucket IS NOT NULL AND length(trim(storage_bucket)) > 0) OR 
        (storage_provider = 'local')
    )
);

-- Indexes for tenant upload_sessions table
CREATE INDEX idx_tenant_upload_sessions_user ON tenant_template.upload_sessions(uploaded_by_user_id);
CREATE INDEX idx_tenant_upload_sessions_team ON tenant_template.upload_sessions(team_id) WHERE team_id IS NOT NULL;
CREATE INDEX idx_tenant_upload_sessions_target_folder ON tenant_template.upload_sessions(target_folder_id) WHERE target_folder_id IS NOT NULL;
CREATE INDEX idx_tenant_upload_sessions_status ON tenant_template.upload_sessions(status);
CREATE INDEX idx_tenant_upload_sessions_expires ON tenant_template.upload_sessions(expires_at);
CREATE INDEX idx_tenant_upload_sessions_created ON tenant_template.upload_sessions(created_at);
CREATE INDEX idx_tenant_upload_sessions_storage_provider ON tenant_template.upload_sessions(storage_provider);
CREATE UNIQUE INDEX idx_tenant_upload_sessions_key ON tenant_template.upload_sessions(session_key);

-- Index for cleanup operations (expired or failed sessions)
CREATE INDEX idx_tenant_upload_sessions_cleanup ON tenant_template.upload_sessions(status, expires_at) 
WHERE status IN ('expired', 'failed');

-- ============================================================================
-- FILE PERMISSIONS (Fine-grained file access control)
-- ============================================================================

CREATE TABLE tenant_template.file_permissions (
    -- Core Identity
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    file_id UUID NOT NULL REFERENCES tenant_template.files(id) ON DELETE CASCADE,
    
    -- Permission Subject (either user or team)
    user_id UUID REFERENCES tenant_template.users(id) ON DELETE CASCADE,
    team_id UUID REFERENCES tenant_template.teams(id) ON DELETE CASCADE,
    
    -- Permission Type
    permission_type VARCHAR(20) NOT NULL, -- read, write, delete, share
    is_granted BOOLEAN DEFAULT true,
    
    -- Grant Information
    granted_by_user_id UUID REFERENCES tenant_template.users(id) ON DELETE SET NULL,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    
    -- Audit Fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT file_permissions_subject_check CHECK (
        (user_id IS NOT NULL AND team_id IS NULL) OR
        (user_id IS NULL AND team_id IS NOT NULL)
    ),
    CONSTRAINT file_permissions_type_valid CHECK (permission_type IN ('read', 'write', 'delete', 'share', 'admin'))
);

-- Indexes for file_permissions table
CREATE INDEX idx_tenant_file_permissions_file ON tenant_template.file_permissions(file_id);
CREATE INDEX idx_tenant_file_permissions_user ON tenant_template.file_permissions(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_tenant_file_permissions_team ON tenant_template.file_permissions(team_id) WHERE team_id IS NOT NULL;
CREATE INDEX idx_tenant_file_permissions_type ON tenant_template.file_permissions(permission_type);
CREATE INDEX idx_tenant_file_permissions_granted ON tenant_template.file_permissions(is_granted);
CREATE INDEX idx_tenant_file_permissions_expires ON tenant_template.file_permissions(expires_at) WHERE expires_at IS NOT NULL;

-- Unique constraint to prevent duplicate permissions
CREATE UNIQUE INDEX idx_tenant_file_permissions_unique ON tenant_template.file_permissions(
    file_id, 
    COALESCE(user_id, '00000000-0000-0000-0000-000000000000'::UUID),
    COALESCE(team_id, '00000000-0000-0000-0000-000000000000'::UUID),
    permission_type
);

-- ============================================================================
-- FILE SHARES (Public and private file sharing)
-- ============================================================================

CREATE TABLE tenant_template.file_shares (
    -- Core Identity
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    file_id UUID NOT NULL REFERENCES tenant_template.files(id) ON DELETE CASCADE,
    share_token VARCHAR(64) UNIQUE NOT NULL,
    
    -- Share Configuration
    share_type VARCHAR(20) NOT NULL DEFAULT 'public', -- public, private, password
    password_hash VARCHAR(255), -- For password-protected shares
    max_downloads INTEGER, -- NULL for unlimited
    download_count INTEGER DEFAULT 0,
    
    -- Access Control
    allow_preview BOOLEAN DEFAULT true,
    allow_download BOOLEAN DEFAULT true,
    require_login BOOLEAN DEFAULT false,
    allowed_user_ids UUID[], -- Specific users for private shares
    allowed_team_ids UUID[], -- Specific teams for private shares
    
    -- Lifecycle Management
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    
    -- Context
    created_by_user_id UUID REFERENCES tenant_template.users(id) ON DELETE SET NULL,
    
    -- Audit Fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT file_shares_type_valid CHECK (share_type IN ('public', 'private', 'password')),
    CONSTRAINT file_shares_download_counts_valid CHECK (
        download_count >= 0 AND 
        (max_downloads IS NULL OR download_count <= max_downloads)
    ),
    CONSTRAINT file_shares_password_required CHECK (
        (share_type = 'password' AND password_hash IS NOT NULL) OR
        (share_type != 'password')
    )
);

-- Indexes for file_shares table
CREATE INDEX idx_tenant_file_shares_file ON tenant_template.file_shares(file_id);
CREATE INDEX idx_tenant_file_shares_token ON tenant_template.file_shares(share_token);
CREATE INDEX idx_tenant_file_shares_type ON tenant_template.file_shares(share_type);
CREATE INDEX idx_tenant_file_shares_active ON tenant_template.file_shares(is_active);
CREATE INDEX idx_tenant_file_shares_expires ON tenant_template.file_shares(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_tenant_file_shares_created_by ON tenant_template.file_shares(created_by_user_id) WHERE created_by_user_id IS NOT NULL;

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================

CREATE TRIGGER update_tenant_files_updated_at
    BEFORE UPDATE ON tenant_template.files
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_tenant_upload_sessions_updated_at
    BEFORE UPDATE ON tenant_template.upload_sessions
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

CREATE TRIGGER update_tenant_file_shares_updated_at
    BEFORE UPDATE ON tenant_template.file_shares
    FOR EACH ROW EXECUTE FUNCTION platform_common.update_updated_at_column();

-- ============================================================================
-- FUNCTIONS FOR TENANT FILE MANAGEMENT
-- ============================================================================

-- Function to clean up expired upload sessions
CREATE OR REPLACE FUNCTION tenant_template.cleanup_expired_upload_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Mark expired sessions as expired
    UPDATE tenant_template.upload_sessions 
    SET status = 'expired', updated_at = NOW()
    WHERE status = 'active' AND expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to update upload session progress
CREATE OR REPLACE FUNCTION tenant_template.update_upload_progress(
    p_session_id UUID,
    p_chunk_number INTEGER,
    p_chunk_size_bytes INTEGER
)
RETURNS BOOLEAN AS $$
DECLARE
    updated_rows INTEGER;
BEGIN
    UPDATE tenant_template.upload_sessions 
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
        UPDATE tenant_template.upload_sessions 
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

-- Function to increment file statistics
CREATE OR REPLACE FUNCTION tenant_template.increment_file_stats(
    p_file_id UUID,
    p_stat_type VARCHAR(20)
)
RETURNS BOOLEAN AS $$
DECLARE
    updated_rows INTEGER;
BEGIN
    IF p_stat_type = 'download' THEN
        UPDATE tenant_template.files 
        SET download_count = download_count + 1, updated_at = NOW()
        WHERE id = p_file_id;
    ELSIF p_stat_type = 'view' THEN
        UPDATE tenant_template.files 
        SET view_count = view_count + 1, updated_at = NOW()
        WHERE id = p_file_id;
    ELSE
        RETURN FALSE;
    END IF;
    
    GET DIAGNOSTICS updated_rows = ROW_COUNT;
    RETURN updated_rows > 0;
END;
$$ LANGUAGE plpgsql;

-- Function to update folder paths when folders are moved
CREATE OR REPLACE FUNCTION tenant_template.update_folder_paths()
RETURNS TRIGGER AS $$
BEGIN
    -- Update folder_path for the current record if it's a folder or file
    IF NEW.parent_folder_id IS NOT NULL THEN
        SELECT folder_path || '/' || NEW.file_name 
        INTO NEW.folder_path
        FROM tenant_template.files 
        WHERE id = NEW.parent_folder_id;
    ELSE
        NEW.folder_path := NEW.file_name;
    END IF;
    
    -- Update all child items if this is a folder
    IF NEW.is_folder THEN
        UPDATE tenant_template.files 
        SET folder_path = NEW.folder_path || '/' || file_name,
            updated_at = NOW()
        WHERE parent_folder_id = NEW.id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for folder path updates
CREATE TRIGGER update_folder_paths_trigger
    BEFORE INSERT OR UPDATE OF parent_folder_id, file_name ON tenant_template.files
    FOR EACH ROW 
    EXECUTE FUNCTION tenant_template.update_folder_paths();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE tenant_template.files IS 'Tenant-specific file metadata and storage information for region: ${region}';
COMMENT ON TABLE tenant_template.upload_sessions IS 'Chunked and resumable upload session tracking for tenants in region: ${region}';
COMMENT ON TABLE tenant_template.file_permissions IS 'Fine-grained file access control for tenant users and teams';
COMMENT ON TABLE tenant_template.file_shares IS 'Public and private file sharing with access control';

COMMENT ON COLUMN tenant_template.files.storage_key IS 'S3 object key or local file path relative to tenant storage root';
COMMENT ON COLUMN tenant_template.files.file_metadata IS 'File-specific metadata like EXIF data, dimensions, etc.';
COMMENT ON COLUMN tenant_template.files.tags IS 'Searchable tags for file categorization and discovery';
COMMENT ON COLUMN tenant_template.files.is_folder IS 'Distinguishes folders from files for hierarchical organization';
COMMENT ON COLUMN tenant_template.files.folder_path IS 'Full folder path for navigation and breadcrumbs';

COMMENT ON COLUMN tenant_template.upload_sessions.session_key IS 'Unique session identifier for client-server coordination';
COMMENT ON COLUMN tenant_template.upload_sessions.multipart_upload_id IS 'S3 multipart upload ID for large file uploads';
COMMENT ON COLUMN tenant_template.upload_sessions.progress_percentage IS 'Automatically calculated upload progress';

COMMENT ON FUNCTION tenant_template.cleanup_expired_upload_sessions() IS 'Marks expired upload sessions for cleanup';
COMMENT ON FUNCTION tenant_template.update_upload_progress(UUID, INTEGER, INTEGER) IS 'Updates upload session progress and handles completion';
COMMENT ON FUNCTION tenant_template.increment_file_stats(UUID, VARCHAR) IS 'Increments file download or view statistics';

-- Log migration completion
SELECT 'V2006: Tenant file management infrastructure created for region ${region} (GDPR: ${gdpr})' as migration_status;