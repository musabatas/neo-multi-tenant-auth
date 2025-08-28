-- Enhanced Rate Limiting System
-- This migration adds enhanced rate limiting functions with sliding window support

-- Enhanced rate limit check function with more detailed responses
CREATE OR REPLACE FUNCTION check_rate_limit_enhanced(
    p_identifier TEXT,
    p_action TEXT,
    p_max_attempts INTEGER,
    p_window_minutes INTEGER
)
RETURNS JSON AS $$
DECLARE
    current_attempts INTEGER;
    oldest_attempt TIMESTAMPTZ;
    window_start TIMESTAMPTZ;
    remaining_attempts INTEGER;
    reset_time TIMESTAMPTZ;
    retry_after_seconds INTEGER;
BEGIN
    window_start := NOW() - (p_window_minutes || ' minutes')::INTERVAL;
    
    -- Count current attempts in the window
    SELECT COUNT(*), MIN(created_at)
    INTO current_attempts, oldest_attempt
    FROM auth_rate_limits
    WHERE identifier = p_identifier
    AND action = p_action
    AND created_at > window_start
    AND (blocked_until IS NULL OR blocked_until <= NOW());
    
    -- Calculate remaining attempts and reset time
    remaining_attempts := GREATEST(0, p_max_attempts - current_attempts);
    reset_time := COALESCE(oldest_attempt, NOW()) + (p_window_minutes || ' minutes')::INTERVAL;
    
    -- Check if limit exceeded
    IF current_attempts >= p_max_attempts THEN
        retry_after_seconds := EXTRACT(EPOCH FROM (reset_time - NOW()))::INTEGER;
        retry_after_seconds := GREATEST(1, retry_after_seconds);
        
        RETURN json_build_object(
            'allowed', FALSE,
            'remaining_attempts', 0,
            'retry_after_seconds', retry_after_seconds,
            'reset_time', reset_time::TEXT,
            'current_attempts', current_attempts,
            'max_attempts', p_max_attempts
        );
    END IF;
    
    -- Record the attempt
    INSERT INTO auth_rate_limits (identifier, action, created_at)
    VALUES (p_identifier, p_action, NOW());
    
    -- Update remaining attempts after recording this attempt
    remaining_attempts := remaining_attempts - 1;
    
    RETURN json_build_object(
        'allowed', TRUE,
        'remaining_attempts', remaining_attempts,
        'reset_time', reset_time::TEXT,
        'current_attempts', current_attempts + 1,
        'max_attempts', p_max_attempts
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get rate limit statistics for monitoring
CREATE OR REPLACE FUNCTION get_rate_limit_stats(
    p_identifier TEXT DEFAULT NULL,
    p_action TEXT DEFAULT NULL,
    p_hours_back INTEGER DEFAULT 24
)
RETURNS JSON AS $$
DECLARE
    stats JSON;
    total_requests INTEGER;
    unique_identifiers INTEGER;
    unique_actions INTEGER;
    top_identifiers JSON;
    top_actions JSON;
BEGIN
    -- Calculate time window
    DECLARE
        window_start TIMESTAMPTZ := NOW() - (p_hours_back || ' hours')::INTERVAL;
    BEGIN
        -- Get basic statistics
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT identifier) as unique_ids,
            COUNT(DISTINCT action) as unique_acts
        INTO total_requests, unique_identifiers, unique_actions
        FROM auth_rate_limits
        WHERE created_at > window_start
        AND (p_identifier IS NULL OR identifier = p_identifier)
        AND (p_action IS NULL OR action = p_action);
        
        -- Get top identifiers by request count
        WITH top_ids AS (
            SELECT identifier, COUNT(*) as request_count
            FROM auth_rate_limits
            WHERE created_at > window_start
            AND (p_action IS NULL OR action = p_action)
            GROUP BY identifier
            ORDER BY request_count DESC
            LIMIT 10
        )
        SELECT json_agg(row_to_json(top_ids))
        INTO top_identifiers
        FROM top_ids;
        
        -- Get top actions by request count
        WITH top_acts AS (
            SELECT action, COUNT(*) as request_count
            FROM auth_rate_limits
            WHERE created_at > window_start
            AND (p_identifier IS NULL OR identifier = p_identifier)
            GROUP BY action
            ORDER BY request_count DESC
            LIMIT 10
        )
        SELECT json_agg(row_to_json(top_acts))
        INTO top_actions
        FROM top_acts;
        
        RETURN json_build_object(
            'time_window_hours', p_hours_back,
            'total_requests', total_requests,
            'unique_identifiers', unique_identifiers,
            'unique_actions', unique_actions,
            'top_identifiers', COALESCE(top_identifiers, '[]'::JSON),
            'top_actions', COALESCE(top_actions, '[]'::JSON),
            'generated_at', NOW()
        );
    END;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP FUNCTION IF EXISTS reset_rate_limit;

-- Function to reset rate limits for a specific identifier/action
CREATE OR REPLACE FUNCTION reset_rate_limit(
    p_identifier TEXT,
    p_action TEXT DEFAULT NULL
)
RETURNS JSON AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete rate limit records
    WITH deleted AS (
        DELETE FROM auth_rate_limits
        WHERE identifier = p_identifier
        AND (p_action IS NULL OR action = p_action)
        RETURNING id
    )
    SELECT COUNT(*) INTO deleted_count FROM deleted;
    
    -- Also clear any blocks
    UPDATE auth_rate_limits
    SET blocked_until = NULL
    WHERE identifier = p_identifier
    AND (p_action IS NULL OR action = p_action)
    AND blocked_until IS NOT NULL;
    
    RETURN json_build_object(
        'success', TRUE,
        'deleted_records', deleted_count,
        'identifier', p_identifier,
        'action', COALESCE(p_action, 'all')
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to block an identifier temporarily
CREATE OR REPLACE FUNCTION block_identifier(
    p_identifier TEXT,
    p_action TEXT,
    p_block_minutes INTEGER DEFAULT 60,
    p_reason TEXT DEFAULT 'Administrative block'
)
RETURNS JSON AS $$
DECLARE
    block_until TIMESTAMPTZ;
BEGIN
    block_until := NOW() + (p_block_minutes || ' minutes')::INTERVAL;
    
    -- Insert or update block record
    INSERT INTO auth_rate_limits (identifier, action, created_at, blocked_until, metadata)
    VALUES (p_identifier, p_action, NOW(), block_until, json_build_object('reason', p_reason, 'type', 'manual_block'))
    ON CONFLICT (identifier, action, created_at)
    DO UPDATE SET 
        blocked_until = EXCLUDED.blocked_until,
        metadata = EXCLUDED.metadata;
    
    RETURN json_build_object(
        'success', TRUE,
        'identifier', p_identifier,
        'action', p_action,
        'blocked_until', block_until,
        'reason', p_reason
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if an identifier is currently blocked
CREATE OR REPLACE FUNCTION is_identifier_blocked(
    p_identifier TEXT,
    p_action TEXT DEFAULT NULL
)
RETURNS JSON AS $$
DECLARE
    block_info RECORD;
BEGIN
    SELECT blocked_until, metadata
    INTO block_info
    FROM auth_rate_limits
    WHERE identifier = p_identifier
    AND (p_action IS NULL OR action = p_action)
    AND blocked_until IS NOT NULL
    AND blocked_until > NOW()
    ORDER BY blocked_until DESC
    LIMIT 1;
    
    IF FOUND THEN
        RETURN json_build_object(
            'blocked', TRUE,
            'blocked_until', block_info.blocked_until,
            'reason', COALESCE(block_info.metadata->>'reason', 'Rate limit exceeded'),
            'retry_after_seconds', EXTRACT(EPOCH FROM (block_info.blocked_until - NOW()))::INTEGER
        );
    ELSE
        RETURN json_build_object('blocked', FALSE);
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to clean up old rate limit records
CREATE OR REPLACE FUNCTION cleanup_old_rate_limits(p_days_old INTEGER DEFAULT 7)
RETURNS JSON AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    WITH deleted AS (
        DELETE FROM auth_rate_limits
        WHERE created_at < NOW() - (p_days_old || ' days')::INTERVAL
        RETURNING id
    )
    SELECT COUNT(*) INTO deleted_count FROM deleted;
    
    RETURN json_build_object(
        'deleted_records', deleted_count,
        'days_old', p_days_old,
        'cleaned_at', NOW()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permissions on new functions
GRANT EXECUTE ON FUNCTION check_rate_limit_enhanced(TEXT, TEXT, INTEGER, INTEGER) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION get_rate_limit_stats(TEXT, TEXT, INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION reset_rate_limit(TEXT, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION block_identifier(TEXT, TEXT, INTEGER, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION is_identifier_blocked(TEXT, TEXT) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION cleanup_old_rate_limits(INTEGER) TO service_role;

-- Create indexes for improved performance on new query patterns
CREATE INDEX IF NOT EXISTS idx_auth_rate_limits_identifier_action_created 
ON auth_rate_limits(identifier, action, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_auth_rate_limits_blocked_until 
ON auth_rate_limits(blocked_until) WHERE blocked_until IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_auth_rate_limits_created_at_action 
ON auth_rate_limits(created_at, action);

-- Add comments for documentation
COMMENT ON FUNCTION check_rate_limit_enhanced(TEXT, TEXT, INTEGER, INTEGER) IS 'Enhanced rate limiting with detailed response information';
COMMENT ON FUNCTION get_rate_limit_stats(TEXT, TEXT, INTEGER) IS 'Get comprehensive rate limiting statistics for monitoring';
COMMENT ON FUNCTION reset_rate_limit(TEXT, TEXT) IS 'Reset rate limits for specific identifier/action combination';
COMMENT ON FUNCTION block_identifier(TEXT, TEXT, INTEGER, TEXT) IS 'Manually block an identifier for specified duration';
COMMENT ON FUNCTION is_identifier_blocked(TEXT, TEXT) IS 'Check if identifier is currently blocked';
COMMENT ON FUNCTION cleanup_old_rate_limits(INTEGER) IS 'Clean up old rate limit records for maintenance';