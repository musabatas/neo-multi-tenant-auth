"""Events SQL query constants following DRY principles.

This module centralizes all SQL queries used across the events feature,
making them reusable, parameterized, and easily maintainable.
All queries are parameterized by schema for flexibility across admin/tenant contexts.
"""

# =====================================================================================
# WEBHOOK ENDPOINTS QUERIES
# =====================================================================================

WEBHOOK_ENDPOINT_INSERT = """
    INSERT INTO {schema}.webhook_endpoints (
        id, name, description, endpoint_url, http_method, secret_token,
        signature_header, custom_headers, timeout_seconds, follow_redirects,
        verify_ssl, max_retry_attempts, retry_backoff_seconds,
        retry_backoff_multiplier, is_active, is_verified, created_by_user_id,
        context_id, created_at, updated_at
    ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20
    ) RETURNING *
"""

WEBHOOK_ENDPOINT_UPDATE = """
    UPDATE {schema}.webhook_endpoints SET
        name = COALESCE($2, name),
        description = COALESCE($3, description),
        endpoint_url = COALESCE($4, endpoint_url),
        http_method = COALESCE($5, http_method),
        secret_token = COALESCE($6, secret_token),
        signature_header = COALESCE($7, signature_header),
        custom_headers = COALESCE($8, custom_headers),
        timeout_seconds = COALESCE($9, timeout_seconds),
        follow_redirects = COALESCE($10, follow_redirects),
        verify_ssl = COALESCE($11, verify_ssl),
        max_retry_attempts = COALESCE($12, max_retry_attempts),
        retry_backoff_seconds = COALESCE($13, retry_backoff_seconds),
        retry_backoff_multiplier = COALESCE($14, retry_backoff_multiplier),
        is_active = COALESCE($15, is_active),
        is_verified = COALESCE($16, is_verified),
        context_id = COALESCE($17, context_id),
        last_used_at = COALESCE($18, last_used_at),
        verified_at = COALESCE($19, verified_at),
        updated_at = $20
    WHERE id = $1
    RETURNING *
"""

WEBHOOK_ENDPOINT_GET_BY_ID = """
    SELECT * FROM {schema}.webhook_endpoints 
    WHERE id = $1
"""

WEBHOOK_ENDPOINT_GET_BY_CONTEXT = """
    SELECT * FROM {schema}.webhook_endpoints 
    WHERE context_id = $1 AND ($2 IS FALSE OR is_active = true)
    ORDER BY created_at ASC
"""

WEBHOOK_ENDPOINT_LIST_ACTIVE = """
    SELECT * FROM {schema}.webhook_endpoints 
    WHERE is_active = true
    ORDER BY created_at ASC
"""

WEBHOOK_ENDPOINT_DELETE = """
    DELETE FROM {schema}.webhook_endpoints 
    WHERE id = $1
"""

WEBHOOK_ENDPOINT_UPDATE_LAST_USED = """
    UPDATE {schema}.webhook_endpoints 
    SET last_used_at = NOW()
    WHERE id = $1
"""

WEBHOOK_ENDPOINT_EXISTS_BY_ID = """
    SELECT EXISTS(SELECT 1 FROM {schema}.webhook_endpoints WHERE id = $1)
"""

# =====================================================================================
# WEBHOOK EVENT TYPES QUERIES
# =====================================================================================

WEBHOOK_EVENT_TYPE_INSERT = """
    INSERT INTO {schema}.webhook_event_types (
        id, event_type, category, display_name, description, is_enabled,
        requires_verification, payload_schema, example_payload, created_at, updated_at
    ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
    ) RETURNING *
"""

WEBHOOK_EVENT_TYPE_UPDATE = """
    UPDATE {schema}.webhook_event_types SET
        display_name = COALESCE($2, display_name),
        description = COALESCE($3, description),
        is_enabled = COALESCE($4, is_enabled),
        requires_verification = COALESCE($5, requires_verification),
        payload_schema = COALESCE($6, payload_schema),
        example_payload = COALESCE($7, example_payload),
        updated_at = $8
    WHERE id = $1
    RETURNING *
"""

WEBHOOK_EVENT_TYPE_GET_BY_ID = """
    SELECT * FROM {schema}.webhook_event_types 
    WHERE id = $1
"""

WEBHOOK_EVENT_TYPE_GET_BY_EVENT_TYPE = """
    SELECT * FROM {schema}.webhook_event_types 
    WHERE event_type = $1
"""

WEBHOOK_EVENT_TYPE_GET_BY_CATEGORY = """
    SELECT * FROM {schema}.webhook_event_types 
    WHERE category = $1 AND ($2 IS FALSE OR is_enabled = true)
    ORDER BY event_type ASC
"""

WEBHOOK_EVENT_TYPE_LIST_ENABLED = """
    SELECT * FROM {schema}.webhook_event_types 
    WHERE is_enabled = true
    ORDER BY category, event_type
"""

WEBHOOK_EVENT_TYPE_DELETE = """
    DELETE FROM {schema}.webhook_event_types 
    WHERE id = $1
"""

# =====================================================================================
# WEBHOOK EVENTS (DOMAIN EVENTS) QUERIES
# =====================================================================================

DOMAIN_EVENT_INSERT = """
    INSERT INTO {schema}.webhook_events (
        id, event_type, event_name, aggregate_id, aggregate_type, aggregate_version,
        event_data, event_metadata, correlation_id, causation_id, triggered_by_user_id,
        context_id, occurred_at, created_at
    ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14
    ) RETURNING *
"""

DOMAIN_EVENT_GET_BY_ID = """
    SELECT * FROM {schema}.webhook_events 
    WHERE id = $1
"""

DOMAIN_EVENT_GET_BY_AGGREGATE = """
    SELECT * FROM {schema}.webhook_events 
    WHERE aggregate_type = $1 AND aggregate_id = $2
    ORDER BY aggregate_version ASC, occurred_at ASC
"""

DOMAIN_EVENT_GET_UNPROCESSED = """
    SELECT * FROM {schema}.webhook_events 
    WHERE processed_at IS NULL
    ORDER BY occurred_at ASC
    LIMIT $1
"""

DOMAIN_EVENT_MARK_PROCESSED = """
    UPDATE {schema}.webhook_events 
    SET processed_at = NOW()
    WHERE id = $1 AND processed_at IS NULL
    RETURNING processed_at IS NOT NULL as success
"""

DOMAIN_EVENT_MARK_MULTIPLE_PROCESSED = """
    UPDATE {schema}.webhook_events 
    SET processed_at = NOW()
    WHERE id = ANY($1) AND processed_at IS NULL
    RETURNING id
"""

DOMAIN_EVENT_GET_BY_CORRELATION_ID = """
    SELECT * FROM {schema}.webhook_events 
    WHERE correlation_id = $1
    ORDER BY occurred_at ASC
"""

DOMAIN_EVENT_GET_BY_CONTEXT = """
    SELECT * FROM {schema}.webhook_events 
    WHERE context_id = $1
    ORDER BY occurred_at DESC
    LIMIT $2
"""

DOMAIN_EVENT_GET_BY_EVENT_TYPE = """
    SELECT * FROM {schema}.webhook_events 
    WHERE event_type = $1
    ORDER BY occurred_at DESC
    LIMIT $2
"""

DOMAIN_EVENT_GET_RECENT = """
    SELECT * FROM {schema}.webhook_events 
    WHERE occurred_at >= NOW() - INTERVAL '{hours} hours'
    ORDER BY occurred_at DESC
    LIMIT $1
"""

DOMAIN_EVENT_COUNT_BY_TYPE = """
    SELECT event_type, COUNT(*) as count
    FROM {schema}.webhook_events 
    WHERE occurred_at >= NOW() - INTERVAL '{hours} hours'
    GROUP BY event_type
    ORDER BY count DESC
"""

# =====================================================================================
# WEBHOOK DELIVERIES QUERIES
# =====================================================================================

WEBHOOK_DELIVERY_INSERT = """
    INSERT INTO {schema}.webhook_deliveries (
        id, webhook_endpoint_id, webhook_event_id, attempt_number, delivery_status,
        request_url, request_method, request_headers, request_body, request_signature,
        response_status_code, response_headers, response_body, response_time_ms,
        error_message, error_code, next_retry_at, max_attempts_reached,
        attempted_at, completed_at, created_at
    ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21
    ) RETURNING *
"""

WEBHOOK_DELIVERY_UPDATE = """
    UPDATE {schema}.webhook_deliveries SET
        delivery_status = COALESCE($2, delivery_status),
        response_status_code = COALESCE($3, response_status_code),
        response_headers = COALESCE($4, response_headers),
        response_body = COALESCE($5, response_body),
        response_time_ms = COALESCE($6, response_time_ms),
        error_message = COALESCE($7, error_message),
        error_code = COALESCE($8, error_code),
        next_retry_at = COALESCE($9, next_retry_at),
        max_attempts_reached = COALESCE($10, max_attempts_reached),
        completed_at = COALESCE($11, completed_at)
    WHERE id = $1
    RETURNING *
"""

WEBHOOK_DELIVERY_GET_BY_ID = """
    SELECT * FROM {schema}.webhook_deliveries 
    WHERE id = $1
"""

WEBHOOK_DELIVERY_GET_PENDING_RETRIES = """
    SELECT * FROM {schema}.webhook_deliveries 
    WHERE delivery_status = 'retrying' 
    AND next_retry_at <= NOW() 
    AND max_attempts_reached = false
    ORDER BY next_retry_at ASC
    LIMIT $1
"""

WEBHOOK_DELIVERY_GET_BY_ENDPOINT = """
    SELECT * FROM {schema}.webhook_deliveries 
    WHERE webhook_endpoint_id = $1
    ORDER BY attempted_at DESC
    LIMIT $2
"""

WEBHOOK_DELIVERY_GET_BY_EVENT = """
    SELECT * FROM {schema}.webhook_deliveries 
    WHERE webhook_event_id = $1
    ORDER BY attempted_at DESC
"""

WEBHOOK_DELIVERY_GET_STATS = """
    SELECT 
        COUNT(*) as total_attempts,
        COUNT(CASE WHEN delivery_status = 'success' THEN 1 END) as successful_deliveries,
        COUNT(CASE WHEN delivery_status = 'failed' THEN 1 END) as failed_deliveries,
        COUNT(CASE WHEN delivery_status = 'timeout' THEN 1 END) as timeout_deliveries,
        AVG(response_time_ms) as avg_response_time_ms,
        MIN(response_time_ms) as min_response_time_ms,
        MAX(response_time_ms) as max_response_time_ms
    FROM {schema}.webhook_deliveries 
    WHERE webhook_endpoint_id = $1 
    AND attempted_at >= NOW() - INTERVAL '{days} days'
"""

# =====================================================================================
# WEBHOOK EVENT SUBSCRIPTIONS QUERIES
# =====================================================================================

# Legacy subscription queries for compatibility
WEBHOOK_SUBSCRIPTION_INSERT = """
    INSERT INTO {schema}.webhook_event_subscriptions (
        id, webhook_endpoint_id, event_type_id, is_active, event_filters, created_at, updated_at
    ) VALUES (
        $1, $2, $3, $4, $5, $6, $7
    ) RETURNING *
"""

WEBHOOK_SUBSCRIPTION_DELETE = """
    DELETE FROM {schema}.webhook_event_subscriptions 
    WHERE webhook_endpoint_id = $1 AND event_type_id = $2
"""

WEBHOOK_SUBSCRIPTION_GET_BY_ENDPOINT = """
    SELECT s.*, et.event_type
    FROM {schema}.webhook_event_subscriptions s
    JOIN {schema}.webhook_event_types et ON s.event_type_id = et.id
    WHERE s.webhook_endpoint_id = $1 AND s.is_active = true
"""

WEBHOOK_SUBSCRIPTION_GET_SUBSCRIBERS = """
    SELECT we.*, s.event_filters
    FROM {schema}.webhook_endpoints we
    JOIN {schema}.webhook_event_subscriptions s ON we.id = s.webhook_endpoint_id
    JOIN {schema}.webhook_event_types et ON s.event_type_id = et.id
    WHERE et.event_type = $1 
    AND we.is_active = true 
    AND s.is_active = true
    AND (et.requires_verification = false OR we.is_verified = true)
    AND ($2 IS NULL OR we.context_id = $2)
"""

# =====================================================================================
# DETAILED WEBHOOK SUBSCRIPTION QUERIES (WebhookSubscription Entity)
# =====================================================================================

WEBHOOK_SUBSCRIPTION_INSERT_DETAILED = """
    INSERT INTO {schema}.webhook_subscriptions (
        id, endpoint_id, event_type_id, event_type, event_filters, is_active, 
        context_id, subscription_name, description, created_at, updated_at, last_triggered_at
    ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
    ) RETURNING *
"""

WEBHOOK_SUBSCRIPTION_UPDATE_DETAILED = """
    UPDATE {schema}.webhook_subscriptions SET
        endpoint_id = COALESCE($2, endpoint_id),
        event_type_id = COALESCE($3, event_type_id),
        event_type = COALESCE($4, event_type),
        event_filters = COALESCE($5, event_filters),
        is_active = COALESCE($6, is_active),
        context_id = COALESCE($7, context_id),
        subscription_name = COALESCE($8, subscription_name),
        description = COALESCE($9, description),
        updated_at = $10,
        last_triggered_at = COALESCE($11, last_triggered_at)
    WHERE id = $1
    RETURNING *
"""

WEBHOOK_SUBSCRIPTION_GET_BY_ID = """
    SELECT * FROM {schema}.webhook_subscriptions 
    WHERE id = $1
"""

WEBHOOK_SUBSCRIPTION_GET_BY_ENDPOINT_ID = """
    SELECT * FROM {schema}.webhook_subscriptions 
    WHERE endpoint_id = $1 AND ($2 IS FALSE OR is_active = true)
    ORDER BY created_at ASC
"""

WEBHOOK_SUBSCRIPTION_GET_BY_EVENT_TYPE = """
    SELECT * FROM {schema}.webhook_subscriptions 
    WHERE event_type = $1 AND ($2 IS FALSE OR is_active = true)
    ORDER BY created_at ASC
"""

WEBHOOK_SUBSCRIPTION_GET_BY_CONTEXT = """
    SELECT * FROM {schema}.webhook_subscriptions 
    WHERE context_id = $1 AND ($2 IS FALSE OR is_active = true)
    ORDER BY created_at ASC
"""

WEBHOOK_SUBSCRIPTION_GET_ACTIVE = """
    SELECT * FROM {schema}.webhook_subscriptions 
    WHERE is_active = true
    ORDER BY created_at ASC
"""

WEBHOOK_SUBSCRIPTION_GET_MATCHING_SUBSCRIPTIONS = """
    SELECT * FROM {schema}.webhook_subscriptions 
    WHERE event_type = $1 
    AND is_active = true
    AND ($2 IS NULL OR context_id IS NULL OR context_id = $2)
    ORDER BY created_at ASC
"""

WEBHOOK_SUBSCRIPTION_DELETE_BY_ID = """
    DELETE FROM {schema}.webhook_subscriptions 
    WHERE id = $1
"""

WEBHOOK_SUBSCRIPTION_UPDATE_LAST_TRIGGERED = """
    UPDATE {schema}.webhook_subscriptions 
    SET last_triggered_at = NOW(), updated_at = NOW()
    WHERE id = $1
"""

WEBHOOK_SUBSCRIPTION_EXISTS_BY_ID = """
    SELECT EXISTS(SELECT 1 FROM {schema}.webhook_subscriptions WHERE id = $1)
"""