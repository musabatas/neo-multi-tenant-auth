-- Migration: Create rate limiting table
-- Description: Tracks rate limits for API endpoints and user actions

CREATE TABLE auth_rate_limits (
    id BIGSERIAL PRIMARY KEY,
    identifier TEXT NOT NULL, -- IP address, user ID, API key, etc.
    action TEXT NOT NULL,     -- Action being rate limited (e.g., 'login', 'api_call', 'password_reset')
    attempts INTEGER DEFAULT 1,
    window_start TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    blocked_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    
    CONSTRAINT auth_rate_limits_unique_window UNIQUE(identifier, action, window_start)
);

-- Create indexes for performance
CREATE INDEX idx_auth_rate_limits_identifier_action ON auth_rate_limits(identifier, action, window_start);
CREATE INDEX idx_auth_rate_limits_blocked_until ON auth_rate_limits(blocked_until) 
    WHERE blocked_until IS NOT NULL;
CREATE INDEX idx_auth_rate_limits_window_start ON auth_rate_limits(window_start);

-- Function to check rate limit
CREATE OR REPLACE FUNCTION check_rate_limit(
    p_identifier TEXT,
    p_action TEXT,
    p_max_attempts INTEGER,
    p_window_minutes INTEGER,
    p_block_minutes INTEGER DEFAULT 15
)
RETURNS TABLE(
    allowed BOOLEAN,
    attempts_remaining INTEGER,
    blocked_until TIMESTAMPTZ
) AS $$
DECLARE
    current_window_start TIMESTAMPTZ;
    current_attempts INTEGER;
    existing_block TIMESTAMPTZ;
BEGIN
    -- Check if currently blocked
    SELECT rl.blocked_until INTO existing_block
    FROM auth_rate_limits rl
    WHERE rl.identifier = p_identifier
      AND rl.action = p_action
      AND rl.blocked_until > NOW()
    ORDER BY rl.blocked_until DESC
    LIMIT 1;
    
    IF existing_block IS NOT NULL THEN
        RETURN QUERY SELECT false, 0, existing_block;
        RETURN;
    END IF;
    
    -- Calculate current window using proper interval arithmetic
    current_window_start := date_trunc('minute', NOW()) - 
        (EXTRACT(MINUTE FROM NOW())::INTEGER % p_window_minutes) * INTERVAL '1 minute';
    
    -- Get or create rate limit entry
    INSERT INTO auth_rate_limits (identifier, action, window_start, attempts)
    VALUES (p_identifier, p_action, current_window_start, 1)
    ON CONFLICT (identifier, action, window_start) 
    DO UPDATE SET attempts = auth_rate_limits.attempts + 1
    RETURNING attempts INTO current_attempts;
    
    -- Check if limit exceeded
    IF current_attempts > p_max_attempts THEN
        -- Block the identifier
        UPDATE auth_rate_limits
        SET blocked_until = NOW() + (p_block_minutes || ' minutes')::INTERVAL
        WHERE identifier = p_identifier
          AND action = p_action
          AND window_start = current_window_start;
        
        RETURN QUERY SELECT false, 0, NOW() + (p_block_minutes || ' minutes')::INTERVAL;
    ELSE
        RETURN QUERY SELECT true, p_max_attempts - current_attempts, NULL::TIMESTAMPTZ;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to reset rate limit (for admin use)
CREATE OR REPLACE FUNCTION reset_rate_limit(p_identifier TEXT, p_action TEXT DEFAULT NULL)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    IF p_action IS NULL THEN
        -- Reset all actions for identifier
        DELETE FROM auth_rate_limits
        WHERE identifier = p_identifier;
    ELSE
        -- Reset specific action
        DELETE FROM auth_rate_limits
        WHERE identifier = p_identifier
          AND action = p_action;
    END IF;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to cleanup old rate limit entries
CREATE OR REPLACE FUNCTION cleanup_rate_limits(p_days_old INTEGER DEFAULT 7)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM auth_rate_limits
    WHERE created_at < NOW() - (p_days_old || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Permissions removed as requested

COMMENT ON TABLE auth_rate_limits IS 'Rate limiting tracking for security';
COMMENT ON FUNCTION check_rate_limit(TEXT, TEXT, INTEGER, INTEGER, INTEGER) IS 'Check and update rate limit for an action';
COMMENT ON FUNCTION reset_rate_limit(TEXT, TEXT) IS 'Reset rate limit for an identifier';
COMMENT ON FUNCTION cleanup_rate_limits(INTEGER) IS 'Remove old rate limit entries';