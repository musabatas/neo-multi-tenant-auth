-- Create RPC function to check if session is active
-- This allows us to validate JWT sessions after logout

CREATE OR REPLACE FUNCTION check_session_active(session_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Check if session exists and is not expired
    RETURN EXISTS (
        SELECT 1 
        FROM auth.sessions 
        WHERE id = session_id 
        AND (not_after IS NULL OR not_after > NOW())
    );
END;
$$;

-- Grant execute permission to authenticated role
GRANT EXECUTE ON FUNCTION check_session_active(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION check_session_active(UUID) TO service_role;

-- Create a more detailed session check function that returns session info
CREATE OR REPLACE FUNCTION get_session_info(session_id UUID)
RETURNS TABLE (
    is_active BOOLEAN,
    user_id UUID,
    expires_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        CASE 
            WHEN s.id IS NOT NULL AND (s.not_after IS NULL OR s.not_after > NOW()) 
            THEN TRUE 
            ELSE FALSE 
        END as is_active,
        s.user_id,
        s.not_after as expires_at
    FROM auth.sessions s
    WHERE s.id = session_id;
    
    -- If no session found, return false
    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, NULL::UUID, NULL::TIMESTAMPTZ;
    END IF;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION get_session_info(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION get_session_info(UUID) TO service_role;