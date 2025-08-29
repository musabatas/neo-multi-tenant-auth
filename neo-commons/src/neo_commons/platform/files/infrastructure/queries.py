"""File management SQL query constants.

Centralized SQL queries for file operations following DRY principles.
All queries are parameterized by schema for multi-tenancy support.

Following maximum separation architecture - one file = one purpose.
"""

# File metadata CRUD queries
FILE_INSERT = """
    INSERT INTO {schema}.files (
        id, file_name, original_name, file_path, storage_provider, storage_key, 
        storage_bucket, storage_region, storage_metadata, mime_type, file_size, 
        checksum_sha256, upload_session_id, uploaded_by_user_id, tenant_id, 
        organization_id, file_metadata, tags, category, description, 
        virus_scan_status, virus_scan_at, virus_scan_result, access_level, 
        is_temporary, retention_policy, auto_delete_at, created_at, updated_at
    ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, 
        $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29
    )
    RETURNING *
"""

FILE_GET_BY_ID = """
    SELECT * FROM {schema}.files 
    WHERE id = $1 AND tenant_id = $2 AND deleted_at IS NULL
"""

FILE_GET_BY_PATH = """
    SELECT * FROM {schema}.files 
    WHERE file_path = $1 AND tenant_id = $2 AND deleted_at IS NULL
"""

FILE_UPDATE = """
    UPDATE {schema}.files SET
        file_name = COALESCE($3, file_name),
        original_name = COALESCE($4, original_name),
        file_path = COALESCE($5, file_path),
        storage_provider = COALESCE($6, storage_provider),
        storage_key = COALESCE($7, storage_key),
        storage_bucket = COALESCE($8, storage_bucket),
        storage_region = COALESCE($9, storage_region),
        storage_metadata = COALESCE($10, storage_metadata),
        mime_type = COALESCE($11, mime_type),
        file_size = COALESCE($12, file_size),
        checksum_sha256 = COALESCE($13, checksum_sha256),
        upload_session_id = COALESCE($14, upload_session_id),
        uploaded_by_user_id = COALESCE($15, uploaded_by_user_id),
        organization_id = COALESCE($16, organization_id),
        file_metadata = COALESCE($17, file_metadata),
        tags = COALESCE($18, tags),
        category = COALESCE($19, category),
        description = COALESCE($20, description),
        virus_scan_status = COALESCE($21, virus_scan_status),
        virus_scan_at = COALESCE($22, virus_scan_at),
        virus_scan_result = COALESCE($23, virus_scan_result),
        access_level = COALESCE($24, access_level),
        is_temporary = COALESCE($25, is_temporary),
        retention_policy = COALESCE($26, retention_policy),
        auto_delete_at = COALESCE($27, auto_delete_at),
        updated_at = $28
    WHERE id = $1 AND tenant_id = $2
    RETURNING *
"""

FILE_DELETE = """
    UPDATE {schema}.files 
    SET deleted_at = NOW(), updated_at = NOW()
    WHERE id = $1 AND tenant_id = $2 AND deleted_at IS NULL
"""

FILE_LIST = """
    SELECT * FROM {schema}.files 
    WHERE tenant_id = $1 
    AND ($2::text IS NULL OR file_path LIKE $2 || '%')
    AND deleted_at IS NULL
    ORDER BY created_at DESC
    LIMIT $3 OFFSET $4
"""

FILE_SEARCH = """
    SELECT * FROM {schema}.files 
    WHERE tenant_id = $1 
    AND (
        original_name ILIKE '%' || $2 || '%' 
        OR file_name ILIKE '%' || $2 || '%'
        OR description ILIKE '%' || $2 || '%'
        OR $2 = ANY(tags)
    )
    AND deleted_at IS NULL
    ORDER BY created_at DESC
    LIMIT $3 OFFSET $4
"""

FILE_GET_BATCH = """
    SELECT * FROM {schema}.files 
    WHERE id = ANY($1) AND tenant_id = $2 AND deleted_at IS NULL
"""

FILE_DELETE_BATCH = """
    UPDATE {schema}.files 
    SET deleted_at = NOW(), updated_at = NOW()
    WHERE id = ANY($1) AND tenant_id = $2 AND deleted_at IS NULL
"""

# Storage statistics queries
FILE_STORAGE_USAGE = """
    SELECT 
        COUNT(*) as total_files,
        COALESCE(SUM(file_size), 0) as total_size_bytes,
        jsonb_object_agg(mime_type, file_count) as file_types,
        array_agg(
            jsonb_build_object(
                'id', id,
                'name', original_name, 
                'size', file_size
            ) ORDER BY file_size DESC
        ) FILTER (WHERE rn <= 10) as largest_files
    FROM (
        SELECT *,
            COUNT(*) OVER (PARTITION BY mime_type) as file_count,
            ROW_NUMBER() OVER (ORDER BY file_size DESC) as rn
        FROM {schema}.files 
        WHERE tenant_id = $1 AND deleted_at IS NULL
    ) f
"""

FILE_COUNT = """
    SELECT COUNT(*) as count FROM {schema}.files 
    WHERE tenant_id = $1 AND deleted_at IS NULL
"""

# Health check query
FILE_REPOSITORY_PING = """
    SELECT 1 as ping
"""

# Upload session queries (if using same schema)
UPLOAD_SESSION_INSERT = """
    INSERT INTO {schema}.upload_sessions (
        id, tenant_id, target_file_id, original_filename, target_path,
        expected_size, expected_mime_type, expected_checksum, upload_type,
        storage_provider, chunk_size, status, uploaded_size, total_chunks,
        completed_chunks, storage_upload_id, storage_key, storage_metadata,
        client_ip, user_agent, expires_at, created_at, updated_at
    ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, 
        $15, $16, $17, $18, $19, $20, $21, $22, $23
    )
    RETURNING *
"""

UPLOAD_SESSION_GET_BY_ID = """
    SELECT * FROM {schema}.upload_sessions 
    WHERE id = $1 AND tenant_id = $2
"""

UPLOAD_SESSION_UPDATE = """
    UPDATE {schema}.upload_sessions SET
        status = COALESCE($3, status),
        uploaded_size = COALESCE($4, uploaded_size),
        total_chunks = COALESCE($5, total_chunks),
        completed_chunks = COALESCE($6, completed_chunks),
        storage_upload_id = COALESCE($7, storage_upload_id),
        storage_key = COALESCE($8, storage_key),
        storage_metadata = COALESCE($9, storage_metadata),
        updated_at = $10
    WHERE id = $1 AND tenant_id = $2
    RETURNING *
"""

UPLOAD_SESSION_COMPLETE = """
    UPDATE {schema}.upload_sessions 
    SET status = 'completed', updated_at = NOW()
    WHERE id = $1 AND tenant_id = $2
"""

UPLOAD_SESSION_DELETE = """
    DELETE FROM {schema}.upload_sessions 
    WHERE id = $1 AND tenant_id = $2
"""

# File permission queries (tenant_template schema)
FILE_PERMISSION_INSERT = """
    INSERT INTO tenant_template.file_permissions (
        id, tenant_id, file_id, permission_type, permission_level,
        user_id, role_code, team_id, is_public, share_token,
        share_link_type, public_url, allowed_actions, denied_actions,
        conditions, expires_at, is_temporary, inherited_from_folder_id,
        is_inherited, can_be_inherited, ip_restrictions, created_by,
        created_at, updated_at
    ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
        $15, $16, $17, $18, $19, $20, $21, $22, $23, $24
    )
    RETURNING *
"""

FILE_PERMISSION_GET_BY_FILE = """
    SELECT * FROM tenant_template.file_permissions 
    WHERE file_id = $1 AND tenant_id = $2
"""

FILE_PERMISSION_CHECK = """
    SELECT 1 FROM tenant_template.file_permissions 
    WHERE file_id = $1 AND user_id = $2 AND tenant_id = $3
    AND (
        permission_level IN ('read', 'write', 'admin', 'owner')
        OR $4 = ANY(allowed_actions)
    )
    AND $4 != ANY(denied_actions)
    AND (expires_at IS NULL OR expires_at > NOW())
"""

FILE_PERMISSION_DELETE = """
    DELETE FROM tenant_template.file_permissions 
    WHERE file_id = $1 AND user_id = $2 AND tenant_id = $3
"""

# File version queries
FILE_VERSION_INSERT = """
    INSERT INTO {schema}.file_versions (
        id, file_id, tenant_id, version_number, storage_key, storage_provider,
        file_size, checksum_sha256, created_by, change_description,
        created_at
    ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
    )
    RETURNING *
"""

FILE_VERSION_GET_BY_FILE = """
    SELECT * FROM {schema}.file_versions 
    WHERE file_id = $1 AND tenant_id = $2
    ORDER BY version_number DESC
"""

FILE_VERSION_GET_SPECIFIC = """
    SELECT * FROM {schema}.file_versions 
    WHERE file_id = $1 AND version_number = $2 AND tenant_id = $3
"""