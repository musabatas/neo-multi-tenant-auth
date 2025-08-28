-- Session Management Functions
-- This migration adds functions to safely access auth.sessions table

-- Function to get user sessions
CREATE OR REPLACE FUNCTION get_user_sessions(p_user_id UUID)
RETURNS TABLE (
    id UUID,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    refreshed_at TIMESTAMP,
    user_agent TEXT,
    ip INET
) 
LANGUAGE plpgsql 
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.id,
        s.created_at,
        s.updated_at,
        s.refreshed_at,
        s.user_agent,
        s.ip
    FROM auth.sessions s
    WHERE s.user_id = p_user_id
    ORDER BY s.created_at DESC;
END;
$$;

-- Function to revoke a user session
CREATE OR REPLACE FUNCTION revoke_user_session(p_user_id UUID, p_session_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql 
SECURITY DEFINER
AS $$
DECLARE
    session_exists BOOLEAN;
BEGIN
    -- Check if session exists and belongs to user
    SELECT EXISTS(
        SELECT 1 FROM auth.sessions 
        WHERE id = p_session_id AND user_id = p_user_id
    ) INTO session_exists;
    
    IF NOT session_exists THEN
        RETURN FALSE;
    END IF;
    
    -- Delete the session
    DELETE FROM auth.sessions 
    WHERE id = p_session_id AND user_id = p_user_id;
    
    RETURN TRUE;
END;
$$;

-- Function to get session count for a user
CREATE OR REPLACE FUNCTION get_user_session_count(p_user_id UUID)
RETURNS INTEGER
LANGUAGE plpgsql 
SECURITY DEFINER
AS $$
DECLARE
    session_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO session_count
    FROM auth.sessions
    WHERE user_id = p_user_id;
    
    RETURN session_count;
END;
$$;

-- Grant execute permissions to authenticated users
GRANT EXECUTE ON FUNCTION get_user_sessions(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION revoke_user_session(UUID, UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_session_count(UUID) TO authenticated;