-- Migration: Idempotency Keys Support
-- Description: Add table and functions for idempotency key management

-- Create idempotency_keys table
CREATE TABLE IF NOT EXISTS public.idempotency_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash TEXT NOT NULL,
    user_id UUID,
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    request_fingerprint TEXT,
    response_status INTEGER,
    response_headers JSONB,
    response_body JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    
    -- Constraints
    CONSTRAINT idempotency_keys_key_hash_unique UNIQUE (key_hash),
    CONSTRAINT idempotency_keys_method_check CHECK (method IN ('POST', 'PUT', 'PATCH', 'DELETE')),
    CONSTRAINT idempotency_keys_expires_at_check CHECK (expires_at > created_at)
);

-- Create indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_idempotency_keys_key_hash ON public.idempotency_keys (key_hash);
CREATE INDEX IF NOT EXISTS idx_idempotency_keys_user_id ON public.idempotency_keys (user_id);
CREATE INDEX IF NOT EXISTS idx_idempotency_keys_expires_at ON public.idempotency_keys (expires_at);
CREATE INDEX IF NOT EXISTS idx_idempotency_keys_created_at ON public.idempotency_keys (created_at);

-- Add comments for documentation
COMMENT ON TABLE public.idempotency_keys IS 'Store idempotency keys for safe request retries';
COMMENT ON COLUMN public.idempotency_keys.key_hash IS 'SHA-256 hash of the idempotency key for security';
COMMENT ON COLUMN public.idempotency_keys.user_id IS 'User who made the request (nullable for unauthenticated requests)';
COMMENT ON COLUMN public.idempotency_keys.method IS 'HTTP method of the original request';
COMMENT ON COLUMN public.idempotency_keys.path IS 'Request path without query parameters';
COMMENT ON COLUMN public.idempotency_keys.request_fingerprint IS 'Hash of request body and key headers';
COMMENT ON COLUMN public.idempotency_keys.response_status IS 'HTTP status code of the original response';
COMMENT ON COLUMN public.idempotency_keys.response_headers IS 'Selected response headers from original request';
COMMENT ON COLUMN public.idempotency_keys.response_body IS 'Response body from original request';
COMMENT ON COLUMN public.idempotency_keys.expires_at IS 'When this idempotency key expires';

-- Function to get idempotency key
CREATE OR REPLACE FUNCTION get_idempotency_key(
    p_key_hash TEXT
)
RETURNS TABLE (
    id UUID,
    key_hash TEXT,
    user_id UUID,
    method TEXT,
    path TEXT,
    request_fingerprint TEXT,
    response_status INTEGER,
    response_headers JSONB,
    response_body JSONB,
    created_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    is_expired BOOLEAN
) 
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ik.id,
        ik.key_hash,
        ik.user_id,
        ik.method,
        ik.path,
        ik.request_fingerprint,
        ik.response_status,
        ik.response_headers,
        ik.response_body,
        ik.created_at,
        ik.expires_at,
        (ik.expires_at <= NOW()) as is_expired
    FROM public.idempotency_keys ik
    WHERE ik.key_hash = p_key_hash;
END;
$$;

-- Function to store idempotency key
CREATE OR REPLACE FUNCTION store_idempotency_key(
    p_key_hash TEXT,
    p_user_id UUID,
    p_method TEXT,
    p_path TEXT,
    p_request_fingerprint TEXT,
    p_response_status INTEGER,
    p_response_headers JSONB,
    p_response_body JSONB,
    p_expires_at TIMESTAMPTZ
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    new_id UUID;
BEGIN
    INSERT INTO public.idempotency_keys (
        key_hash,
        user_id,
        method,
        path,
        request_fingerprint,
        response_status,
        response_headers,
        response_body,
        expires_at
    ) VALUES (
        p_key_hash,
        p_user_id,
        p_method,
        p_path,
        p_request_fingerprint,
        p_response_status,
        p_response_headers,
        p_response_body,
        p_expires_at
    )
    ON CONFLICT (key_hash) DO NOTHING
    RETURNING id INTO new_id;
    
    RETURN new_id;
END;
$$;

-- Function to validate idempotency key conflict
CREATE OR REPLACE FUNCTION validate_idempotency_key(
    p_key_hash TEXT,
    p_user_id UUID,
    p_method TEXT,
    p_path TEXT,
    p_request_fingerprint TEXT
)
RETURNS TABLE (
    is_valid BOOLEAN,
    conflict_reason TEXT,
    existing_response_status INTEGER,
    existing_response_headers JSONB,
    existing_response_body JSONB
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    existing_record RECORD;
BEGIN
    -- Get existing record
    SELECT * INTO existing_record
    FROM public.idempotency_keys
    WHERE key_hash = p_key_hash;
    
    -- If no existing record, it's valid
    IF NOT FOUND THEN
        RETURN QUERY SELECT true, NULL::TEXT, NULL::INTEGER, NULL::JSONB, NULL::JSONB;
        RETURN;
    END IF;
    
    -- Check if expired
    IF existing_record.expires_at <= NOW() THEN
        RETURN QUERY SELECT true, 'expired'::TEXT, NULL::INTEGER, NULL::JSONB, NULL::JSONB;
        RETURN;
    END IF;
    
    -- Check for conflicts
    -- Different user (if both are authenticated)
    IF existing_record.user_id IS NOT NULL AND p_user_id IS NOT NULL 
       AND existing_record.user_id != p_user_id THEN
        RETURN QUERY SELECT 
            false, 
            'different_user'::TEXT, 
            existing_record.response_status,
            existing_record.response_headers,
            existing_record.response_body;
        RETURN;
    END IF;
    
    -- Different method
    IF existing_record.method != p_method THEN
        RETURN QUERY SELECT 
            false, 
            'different_method'::TEXT, 
            existing_record.response_status,
            existing_record.response_headers,
            existing_record.response_body;
        RETURN;
    END IF;
    
    -- Different path
    IF existing_record.path != p_path THEN
        RETURN QUERY SELECT 
            false, 
            'different_path'::TEXT, 
            existing_record.response_status,
            existing_record.response_headers,
            existing_record.response_body;
        RETURN;
    END IF;
    
    -- Different request fingerprint (body/headers changed)
    IF existing_record.request_fingerprint != p_request_fingerprint THEN
        RETURN QUERY SELECT 
            false, 
            'different_request'::TEXT, 
            existing_record.response_status,
            existing_record.response_headers,
            existing_record.response_body;
        RETURN;
    END IF;
    
    -- Valid duplicate request - return cached response
    RETURN QUERY SELECT 
        true, 
        'duplicate'::TEXT, 
        existing_record.response_status,
        existing_record.response_headers,
        existing_record.response_body;
END;
$$;

-- Function to cleanup expired idempotency keys
CREATE OR REPLACE FUNCTION cleanup_expired_idempotency_keys()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM public.idempotency_keys
    WHERE expires_at <= NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;

-- Function to get idempotency key statistics
CREATE OR REPLACE FUNCTION get_idempotency_stats()
RETURNS TABLE (
    total_keys INTEGER,
    active_keys INTEGER,
    expired_keys INTEGER,
    keys_last_24h INTEGER,
    avg_ttl_hours NUMERIC
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (SELECT COUNT(*)::INTEGER FROM public.idempotency_keys) as total_keys,
        (SELECT COUNT(*)::INTEGER FROM public.idempotency_keys WHERE expires_at > NOW()) as active_keys,
        (SELECT COUNT(*)::INTEGER FROM public.idempotency_keys WHERE expires_at <= NOW()) as expired_keys,
        (SELECT COUNT(*)::INTEGER FROM public.idempotency_keys WHERE created_at >= NOW() - INTERVAL '24 hours') as keys_last_24h,
        (SELECT ROUND(AVG(EXTRACT(EPOCH FROM (expires_at - created_at)) / 3600)::NUMERIC, 2) 
         FROM public.idempotency_keys) as avg_ttl_hours;
END;
$$;

-- Grant necessary permissions
GRANT SELECT, INSERT, DELETE ON public.idempotency_keys TO authenticated;
GRANT EXECUTE ON FUNCTION get_idempotency_key(TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION store_idempotency_key(TEXT, UUID, TEXT, TEXT, TEXT, INTEGER, JSONB, JSONB, TIMESTAMPTZ) TO authenticated;
GRANT EXECUTE ON FUNCTION validate_idempotency_key(TEXT, UUID, TEXT, TEXT, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION cleanup_expired_idempotency_keys() TO authenticated;
GRANT EXECUTE ON FUNCTION get_idempotency_stats() TO authenticated;

-- Row Level Security (RLS)
ALTER TABLE public.idempotency_keys ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their own idempotency keys
CREATE POLICY "Users can manage their own idempotency keys"
    ON public.idempotency_keys
    FOR ALL
    TO authenticated
    USING (
        user_id = auth.uid() OR
        user_id IS NULL  -- Allow access to anonymous requests for the same session
    );

-- Policy: Service role can access all idempotency keys
CREATE POLICY "Service role can access all idempotency keys"
    ON public.idempotency_keys
    FOR ALL
    TO service_role
    USING (true);