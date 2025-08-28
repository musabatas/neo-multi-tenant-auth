-- Migration: Create users table for application data and permission caching
-- Description: Extends auth.users with app-specific data and caches direct permissions
-- Users table created on base_tables.sql
-- Core function to create user profile and assign default role
CREATE OR REPLACE FUNCTION create_user_profile_core(auth_user auth.users)
RETURNS void AS $$
DECLARE
    default_role_id BIGINT;
    profile_exists BOOLEAN;
BEGIN
    -- Check if profile already exists
    SELECT EXISTS(SELECT 1 FROM public.users WHERE id = auth_user.id) INTO profile_exists;
    
    IF NOT profile_exists THEN
        -- Create user profile
        INSERT INTO public.users (
            id,
            username,
            first_name,
            last_name,
            display_name,
            has_direct_permissions,
            direct_permissions
        ) VALUES (
            auth_user.id,
            COALESCE(
                auth_user.raw_user_meta_data->>'username',
                'user_' || substring(replace(auth_user.id::TEXT, '-', '') from 1 for 8)
            ),
            auth_user.raw_user_meta_data->>'first_name',
            auth_user.raw_user_meta_data->>'last_name',
            COALESCE(
                auth_user.raw_user_meta_data->>'full_name',
                auth_user.raw_user_meta_data->>'name',
                split_part(auth_user.email, '@', 1)
            ),
            false,
            ARRAY[]::TEXT[]
        );
        
        -- Get default role ID
        SELECT id INTO default_role_id 
        FROM public.auth_roles 
        WHERE name = 'user' AND deleted_at IS NULL;
        
        -- Assign default role
        IF default_role_id IS NOT NULL THEN
            INSERT INTO public.auth_user_roles (user_id, role_id)
            VALUES (auth_user.id, default_role_id)
            ON CONFLICT (user_id, role_id) WHERE revoked_at IS NULL DO NOTHING;
        END IF;
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE LOG 'Error creating profile for user %: % %', auth_user.id, SQLERRM, SQLSTATE;
        RAISE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, auth;

-- Trigger function that uses the core function
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS trigger AS $$
BEGIN
    PERFORM create_user_profile_core(NEW);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, auth;

-- Create comprehensive trigger
CREATE TRIGGER on_auth_user_created
    AFTER INSERT OR UPDATE ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();


-- Also create a function for Supabase to call via RPC if triggers don't work
CREATE OR REPLACE FUNCTION ensure_user_has_profile(user_id UUID)
RETURNS void AS $$
DECLARE
    auth_user auth.users;
BEGIN
    -- Get auth user info
    SELECT * INTO auth_user FROM auth.users WHERE id = user_id;
    
    IF auth_user.id IS NULL THEN
        RAISE EXCEPTION 'User % not found', user_id;
    END IF;
    
    -- Use the core function to create profile
    PERFORM create_user_profile_core(auth_user);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to update user's direct permissions cache (both granted and denied)
CREATE OR REPLACE FUNCTION refresh_user_direct_permissions(p_user_id UUID)
RETURNS void AS $$
DECLARE
    granted_perms TEXT[];
    denied_perms TEXT[];
    has_perms BOOLEAN;
BEGIN
    -- Get direct granted permissions
    SELECT 
        ARRAY_AGG(DISTINCT p.name ORDER BY p.name)
    INTO granted_perms
    FROM auth_user_permissions up
    JOIN auth_permissions p ON up.permission_id = p.id
    WHERE up.user_id = p_user_id
      AND up.revoked_at IS NULL
      AND (up.expires_at IS NULL OR up.expires_at > NOW())
      AND up.grant_type = 'grant';
    
    -- Get direct denied permissions
    SELECT 
        ARRAY_AGG(DISTINCT p.name ORDER BY p.name)
    INTO denied_perms
    FROM auth_user_permissions up
    JOIN auth_permissions p ON up.permission_id = p.id
    WHERE up.user_id = p_user_id
      AND up.revoked_at IS NULL
      AND (up.expires_at IS NULL OR up.expires_at > NOW())
      AND up.grant_type = 'deny';
    
    -- Check if user has any direct permissions (granted or denied)
    has_perms := (granted_perms IS NOT NULL AND array_length(granted_perms, 1) > 0) OR
                 (denied_perms IS NOT NULL AND array_length(denied_perms, 1) > 0);
    
    -- Update users table
    UPDATE users
    SET 
        direct_permissions = COALESCE(granted_perms, ARRAY[]::TEXT[]),
        denied_permissions = COALESCE(denied_perms, ARRAY[]::TEXT[]),
        has_direct_permissions = has_perms
    WHERE id = p_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to update cache when user permissions change
CREATE OR REPLACE FUNCTION trigger_update_user_permissions_cache()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        PERFORM refresh_user_direct_permissions(OLD.user_id);
        RETURN OLD;
    ELSE
        PERFORM refresh_user_direct_permissions(NEW.user_id);
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auto_update_user_permissions_cache
AFTER INSERT OR UPDATE OR DELETE ON auth_user_permissions
FOR EACH ROW EXECUTE FUNCTION trigger_update_user_permissions_cache();

-- No updated_at trigger needed since we removed the updated_at column

-- Permissions removed as requested

COMMENT ON TABLE users IS 'Extension table for auth.users - contains only additional profile fields not present in auth.users';
COMMENT ON FUNCTION create_user_profile_core(auth.users) IS 'Core function to create user profile and assign default role';
COMMENT ON FUNCTION refresh_user_direct_permissions(UUID) IS 'Update cached direct permissions for a user';
COMMENT ON FUNCTION handle_new_user() IS 'Trigger function to create user profile on auth user creation';
COMMENT ON FUNCTION ensure_user_has_profile(UUID) IS 'Manually ensure a user has a profile - can be called via RPC';