-- Migration: Create API keys table for programmatic access
-- Description: Enables API key authentication with flexible permission inheritance

CREATE TABLE auth_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    key_name TEXT NOT NULL,
    key_prefix TEXT NOT NULL, -- Prefix from environment (e.g., "sk_test_")
    key_hash TEXT NOT NULL UNIQUE, -- Hashed full API key
    key_suffix TEXT NOT NULL, -- Last 4 chars for user identification
    key_start TEXT NOT NULL, -- First 3 chars after prefix for better UX
    inherit_user_permissions BOOLEAN DEFAULT true, -- If true, inherit all user permissions
    allowed_permissions TEXT[], -- If set, restricts the API key to only these permissions, even if the user has more
    
    -- Key metadata
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMPTZ,
    usage_count BIGINT DEFAULT 0,
    use_user_rate_limits BOOLEAN DEFAULT true, -- If true, use user's global rate limits
    rate_limit_per_minute INTEGER, -- Custom rate limit (only used if use_user_rate_limits=false)
    rate_limit_per_hour INTEGER, -- Custom rate limit (only used if use_user_rate_limits=false)
    
    -- Security and audit
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    expires_at TIMESTAMPTZ, -- Optional expiration
    revoked_at TIMESTAMPTZ,
    revoked_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    revoked_reason TEXT,
    
    -- Request metadata
    created_from_ip INET,
    created_user_agent TEXT,
    
    CONSTRAINT auth_api_keys_valid_dates CHECK (
        (expires_at IS NULL OR expires_at > created_at) AND
        (revoked_at IS NULL OR revoked_at >= created_at)
    ),
    
    CONSTRAINT auth_api_keys_revoked_logic CHECK (
        (revoked_at IS NULL AND revoked_by IS NULL AND revoked_reason IS NULL) OR
        (revoked_at IS NOT NULL AND revoked_by IS NOT NULL)
    )
);

-- Create indexes for performance
CREATE INDEX idx_auth_api_keys_user_id ON auth_api_keys(user_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_auth_api_keys_key_hash ON auth_api_keys(key_hash) WHERE is_active = true AND revoked_at IS NULL;
CREATE INDEX idx_auth_api_keys_key_prefix ON auth_api_keys(key_prefix);
CREATE INDEX idx_auth_api_keys_expires_at ON auth_api_keys(expires_at) 
    WHERE expires_at IS NOT NULL AND revoked_at IS NULL;
CREATE INDEX idx_auth_api_keys_last_used ON auth_api_keys(last_used_at) WHERE is_active = true;

-- Unique constraint for active keys per user (same name)
CREATE UNIQUE INDEX idx_auth_api_keys_user_name_active 
    ON auth_api_keys(user_id, key_name) 
    WHERE revoked_at IS NULL;

-- Enable RLS
ALTER TABLE auth_api_keys ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own API keys" ON auth_api_keys
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create own API keys" ON auth_api_keys
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own API keys" ON auth_api_keys
    FOR UPDATE USING (auth.uid() = user_id);

-- Function to update last_used_at and usage_count
CREATE OR REPLACE FUNCTION update_api_key_usage(p_key_hash TEXT)
RETURNS VOID AS $$
BEGIN
    UPDATE auth_api_keys 
    SET 
        last_used_at = NOW(),
        usage_count = usage_count + 1
    WHERE key_hash = p_key_hash 
      AND is_active = true 
      AND revoked_at IS NULL
      AND (expires_at IS NULL OR expires_at > NOW());
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to validate API key and get user info with inheritance support
CREATE OR REPLACE FUNCTION validate_api_key(p_key_hash TEXT)
RETURNS TABLE(
    user_id UUID,
    key_id UUID,
    inherit_user_permissions BOOLEAN,
    allowed_permissions TEXT[],
    use_user_rate_limits BOOLEAN,
    rate_limit_per_minute INTEGER,
    rate_limit_per_hour INTEGER,
    is_valid BOOLEAN
) AS $$
DECLARE
    user_permissions TEXT[];
    default_rate_minute INTEGER := 60;
    default_rate_hour INTEGER := 1000;
BEGIN
    RETURN QUERY
    SELECT 
        ak.user_id,
        ak.id as key_id,
        ak.inherit_user_permissions,
        CASE 
            WHEN ak.inherit_user_permissions THEN get_user_permissions(ak.user_id)
            ELSE COALESCE(ak.allowed_permissions, ARRAY[]::TEXT[])
        END as effective_scopes,
        ak.use_user_rate_limits,
        CASE 
            WHEN ak.use_user_rate_limits THEN default_rate_minute
            ELSE COALESCE(ak.rate_limit_per_minute, default_rate_minute)
        END as effective_rate_minute,
        CASE 
            WHEN ak.use_user_rate_limits THEN default_rate_hour
            ELSE COALESCE(ak.rate_limit_per_hour, default_rate_hour)
        END as effective_rate_hour,
        (ak.is_active AND ak.revoked_at IS NULL AND (ak.expires_at IS NULL OR ak.expires_at > NOW())) as is_valid
    FROM auth_api_keys ak
    WHERE ak.key_hash = p_key_hash;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to revoke API key
CREATE OR REPLACE FUNCTION revoke_api_key(
    p_key_id UUID,
    p_revoked_by UUID,
    p_reason TEXT DEFAULT 'Manually revoked'
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE auth_api_keys 
    SET 
        revoked_at = NOW(),
        revoked_by = p_revoked_by,
        revoked_reason = p_reason,
        is_active = false
    WHERE id = p_key_id 
      AND user_id = p_revoked_by  -- Only allow users to revoke their own keys
      AND revoked_at IS NULL;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create a cleanup function for expired API keys
CREATE OR REPLACE FUNCTION cleanup_expired_api_keys()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    cleaned_count INTEGER;
BEGIN
    -- Mark expired keys as inactive
    UPDATE auth_api_keys 
    SET is_active = false
    WHERE expires_at IS NOT NULL 
      AND expires_at <= NOW() 
      AND is_active = true;
      
    GET DIAGNOSTICS cleaned_count = ROW_COUNT;
    
    RETURN cleaned_count;
END;
$$;

-- Permissions removed as requested

COMMENT ON TABLE auth_api_keys IS 'User-generated API keys for programmatic access';
COMMENT ON COLUMN auth_api_keys.allowed_permissions IS 'If set, restricts the API key to only these permissions, even if the user has more. NULL means inherit all user permissions.';
COMMENT ON FUNCTION validate_api_key(TEXT) IS 'Validate API key and return user permissions';
COMMENT ON FUNCTION revoke_api_key(UUID, UUID, TEXT) IS 'Revoke an API key';
COMMENT ON FUNCTION cleanup_expired_api_keys() IS 'Mark expired API keys as inactive';