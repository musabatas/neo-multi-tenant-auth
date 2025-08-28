-- Migration: Essential search optimization - only necessary indexes
-- Created: 2025-07-11

-- B-tree indexes for individual field searches (pg_trgm not available)
-- These provide good performance for prefix matches and equality searches
CREATE INDEX IF NOT EXISTS idx_users_username_search 
ON public.users USING btree(username text_pattern_ops);

CREATE INDEX IF NOT EXISTS idx_users_display_name_search 
ON public.users USING btree(display_name text_pattern_ops);

CREATE INDEX IF NOT EXISTS idx_users_name_search 
ON public.users USING btree(first_name text_pattern_ops, last_name text_pattern_ops);

-- Add email search index on auth.users table for email searches
CREATE INDEX IF NOT EXISTS idx_auth_users_email_search
ON auth.users USING btree(email text_pattern_ops);

-- Index for common user listing with filters
CREATE INDEX IF NOT EXISTS idx_users_active_created 
ON public.users (last_active_at DESC NULLS LAST) 
WHERE last_active_at IS NOT NULL;

-- Essential foreign key indexes (only if missing)

-- User roles lookup optimization (already exists but let's ensure it's optimal)
CREATE INDEX IF NOT EXISTS idx_auth_user_roles_user_lookup 
ON auth_user_roles (user_id) 
WHERE revoked_at IS NULL;

-- API key hash lookup (only if table exists and index missing)
-- Note: Checking if auth_api_keys table exists first
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'auth_api_keys' AND table_schema = 'public') THEN
        -- Create index only if it doesn't exist
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_auth_api_keys_hash_lookup') THEN
            CREATE INDEX idx_auth_api_keys_hash_lookup 
            ON auth_api_keys (key_hash) 
            WHERE revoked_at IS NULL;
        END IF;
    END IF;
END $$;

-- Create a function to get combined search text for a user (for testing)
CREATE OR REPLACE FUNCTION get_user_search_text(p_user_id UUID)
RETURNS TEXT AS $$
DECLARE
    auth_email TEXT;
    user_text TEXT;
    combined_text TEXT;
BEGIN
    -- Get email from auth.users
    SELECT email INTO auth_email 
    FROM auth.users 
    WHERE id = p_user_id;
    
    -- Get user profile text
    SELECT 
        COALESCE(username, '') || ' ' || 
        COALESCE(display_name, '') || ' ' || 
        COALESCE(first_name, '') || ' ' || 
        COALESCE(last_name, '')
    INTO user_text
    FROM public.users 
    WHERE id = p_user_id;
    
    -- Combine all text
    combined_text := COALESCE(auth_email, '') || ' ' || COALESCE(user_text, '');
    
    RETURN combined_text;
END;
$$ LANGUAGE plpgsql;

-- Index creation complete