"""SQL queries for event operations."""

# ============================================================================
# EVENT INSERT QUERIES
# ============================================================================

EVENT_INSERT = """
    INSERT INTO {schema}.events (
        id, event_type, aggregate_id, aggregate_type,
        event_version, correlation_id, causation_id,
        event_data, event_metadata,
        status, priority, scheduled_at,
        retry_count, max_retries,
        queue_name, message_id, partition_key,
        created_at, updated_at
    ) VALUES (
        $1, $2, $3, $4,
        $5, $6, $7,
        $8, $9,
        $10, $11, $12,
        $13, $14,
        $15, $16, $17,
        $18, $19
    )
    RETURNING *
"""

# ============================================================================
# EVENT UPDATE QUERIES
# ============================================================================

EVENT_UPDATE = """
    UPDATE {schema}.events SET
        status = $2,
        processing_started_at = $3,
        processing_completed_at = $4,
        processing_duration_ms = $5,
        retry_count = $6,
        error_message = $7,
        error_details = $8,
        queue_name = $9,
        message_id = $10,
        partition_key = $11,
        updated_at = NOW()
    WHERE id = $1 AND deleted_at IS NULL
    RETURNING *
"""

# ============================================================================
# EVENT SELECT QUERIES
# ============================================================================

EVENT_GET_BY_ID = """
    SELECT * FROM {schema}.events 
    WHERE id = $1 AND deleted_at IS NULL
"""

EVENT_LIST_ALL = """
    SELECT * FROM {schema}.events 
    WHERE deleted_at IS NULL
    ORDER BY created_at DESC
    LIMIT $1 OFFSET $2
"""

EVENT_LIST_FILTERED = """
    SELECT * FROM {schema}.events 
    WHERE deleted_at IS NULL
    {filters}
    ORDER BY created_at DESC
    LIMIT $1 OFFSET $2
"""

EVENT_COUNT_FILTERED = """
    SELECT COUNT(*) FROM {schema}.events 
    WHERE deleted_at IS NULL
    {filters}
"""

EVENT_GET_HISTORY = """
    SELECT * FROM {schema}.events 
    WHERE correlation_id = $1 AND deleted_at IS NULL
    ORDER BY created_at ASC
    LIMIT $2
"""

EVENT_GET_PENDING = """
    SELECT * FROM {schema}.events 
    WHERE status = 'pending' 
    AND deleted_at IS NULL
    AND scheduled_at <= NOW()
    ORDER BY 
        CASE priority
            WHEN 'critical' THEN 1
            WHEN 'very_high' THEN 2  
            WHEN 'high' THEN 3
            WHEN 'normal' THEN 4
            WHEN 'low' THEN 5
        END,
        created_at ASC
    LIMIT $1
"""

EVENT_GET_FAILED = """
    SELECT * FROM {schema}.events 
    WHERE status = 'failed' 
    AND deleted_at IS NULL
    {can_retry_filter}
    ORDER BY created_at ASC
    LIMIT $1
"""

# ============================================================================
# EVENT DELETE QUERIES  
# ============================================================================

EVENT_DELETE_SOFT = """
    UPDATE {schema}.events 
    SET deleted_at = NOW(), updated_at = NOW()
    WHERE id = $1 AND deleted_at IS NULL
    RETURNING id
"""

# ============================================================================
# EVENT UTILITY QUERIES
# ============================================================================

EVENT_EXISTS_BY_ID = """
    SELECT EXISTS(
        SELECT 1 FROM {schema}.events 
        WHERE id = $1 AND deleted_at IS NULL
    )
"""

# ============================================================================
# FILTER BUILDING HELPERS
# ============================================================================

def build_event_filters(filters: dict) -> tuple[str, list]:
    """
    Build WHERE clause filters and parameters for event queries.
    
    Args:
        filters: Dictionary of filter criteria
        
    Returns:
        Tuple of (filter_clause, parameters)
    """
    conditions = []
    params = []
    param_count = 1  # Start from 1 since $1 is usually limit/offset
    
    if filters.get('event_types'):
        event_types = filters['event_types']
        placeholders = ', '.join([f'${param_count + i}' for i in range(len(event_types))])
        conditions.append(f'AND event_type = ANY(ARRAY[{placeholders}])')
        params.extend(event_types)
        param_count += len(event_types)
    
    if filters.get('statuses'):
        statuses = filters['statuses']
        placeholders = ', '.join([f'${param_count + i}' for i in range(len(statuses))])
        conditions.append(f'AND status = ANY(ARRAY[{placeholders}])')
        params.extend(statuses)
        param_count += len(statuses)
    
    if filters.get('priorities'):
        priorities = filters['priorities']
        placeholders = ', '.join([f'${param_count + i}' for i in range(len(priorities))])
        conditions.append(f'AND priority = ANY(ARRAY[{placeholders}])')
        params.extend(priorities)
        param_count += len(priorities)
    
    if filters.get('aggregate_id'):
        conditions.append(f'AND aggregate_id = ${param_count}')
        params.append(filters['aggregate_id'])
        param_count += 1
    
    if filters.get('aggregate_type'):
        conditions.append(f'AND aggregate_type = ${param_count}')
        params.append(filters['aggregate_type'])
        param_count += 1
    
    if filters.get('correlation_id'):
        conditions.append(f'AND correlation_id = ${param_count}')
        params.append(filters['correlation_id'])
        param_count += 1
    
    if filters.get('from_date'):
        conditions.append(f'AND created_at >= ${param_count}')
        params.append(filters['from_date'])
        param_count += 1
    
    if filters.get('to_date'):
        conditions.append(f'AND created_at <= ${param_count}')
        params.append(filters['to_date'])
        param_count += 1
    
    filter_clause = ' '.join(conditions) if conditions else ''
    
    return filter_clause, params