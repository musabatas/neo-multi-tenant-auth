-- Migration: Create auth helper functions
-- Description: Core functions for permission checking and user management

-- Optimized function to get user permissions using cached data
-- Now excludes denied permissions
CREATE OR REPLACE FUNCTION get_user_permissions(p_user_id UUID)
RETURNS TEXT[] AS $$
DECLARE
    granted_perms TEXT[];
    denied_perms TEXT[];
BEGIN
    -- Get all granted permissions
    granted_perms := ARRAY(
        SELECT DISTINCT perm FROM (
            -- Permissions from roles (using cached column in auth_roles)
            SELECT UNNEST(r.cached_permissions) as perm
            FROM auth_user_roles ur
            JOIN auth_roles r ON ur.role_id = r.id
            WHERE ur.user_id = p_user_id
              AND ur.revoked_at IS NULL
              AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
              AND r.deleted_at IS NULL
            
            UNION ALL
            
            -- Direct permissions (from users table cache)
            SELECT UNNEST(u.direct_permissions)
            FROM users u
            WHERE u.id = p_user_id
              AND u.has_direct_permissions = true
        ) all_perms
        WHERE perm IS NOT NULL
    );
    
    -- Get denied permissions from cache
    SELECT denied_permissions INTO denied_perms
    FROM users
    WHERE id = p_user_id;
    
    -- Return granted permissions minus denied ones
    -- array_remove doesn't work well with arrays, so we use EXCEPT
    RETURN ARRAY(
        SELECT UNNEST(granted_perms)
        EXCEPT
        SELECT UNNEST(COALESCE(denied_perms, ARRAY[]::TEXT[]))
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get user roles
CREATE OR REPLACE FUNCTION get_user_roles(p_user_id UUID)
RETURNS TEXT[] AS $$
DECLARE
    user_roles TEXT[];
BEGIN
    SELECT array_agg(r.name ORDER BY r.priority DESC) INTO user_roles
    FROM auth_user_roles ur
    JOIN auth_roles r ON ur.role_id = r.id
    WHERE ur.user_id = p_user_id
      AND ur.revoked_at IS NULL
      AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
      AND r.deleted_at IS NULL;
    
    RETURN COALESCE(user_roles, ARRAY[]::TEXT[]);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- Function to check if user has permission
-- Now checks denied permissions first
CREATE OR REPLACE FUNCTION has_permission(p_user_id UUID, p_permission TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    user_permissions TEXT[];
    denied_perms TEXT[];
BEGIN
    -- First check if permission is explicitly denied
    SELECT denied_permissions INTO denied_perms
    FROM users
    WHERE id = p_user_id;
    
    IF p_permission = ANY(COALESCE(denied_perms, ARRAY[]::TEXT[])) THEN
        RETURN FALSE;  -- Explicitly denied
    END IF;
    
    -- Then check granted permissions
    user_permissions := get_user_permissions(p_user_id);
    RETURN p_permission = ANY(user_permissions) OR 'admin.*' = ANY(user_permissions);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Note: Default role assignment is handled in handle_new_user() function
-- in the users table migration to avoid trigger conflicts

-- Function to get role ID by name (helper function)
CREATE OR REPLACE FUNCTION get_role_id(p_role_name TEXT)
RETURNS BIGINT AS $$
DECLARE
    role_id BIGINT;
BEGIN
    SELECT id INTO role_id FROM auth_roles WHERE name = p_role_name AND deleted_at IS NULL;
    RETURN role_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get permission ID by name (helper function)
CREATE OR REPLACE FUNCTION get_permission_id(p_permission_name TEXT)
RETURNS BIGINT AS $$
DECLARE
    permission_id BIGINT;
BEGIN
    SELECT id INTO permission_id FROM auth_permissions WHERE name = p_permission_name;
    RETURN permission_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to update user's permission caches (both granted and denied)
CREATE OR REPLACE FUNCTION update_user_permission_cache(p_user_id UUID)
RETURNS VOID AS $$
DECLARE
    direct_granted TEXT[];
    direct_denied TEXT[];
    has_direct BOOLEAN;
BEGIN
    -- Get direct granted permissions
    SELECT array_agg(p.name) INTO direct_granted
    FROM auth_user_permissions up
    JOIN auth_permissions p ON up.permission_id = p.id
    WHERE up.user_id = p_user_id
      AND up.revoked_at IS NULL
      AND (up.expires_at IS NULL OR up.expires_at > NOW())
      AND up.grant_type = 'grant';
    
    -- Get direct denied permissions
    SELECT array_agg(p.name) INTO direct_denied
    FROM auth_user_permissions up
    JOIN auth_permissions p ON up.permission_id = p.id
    WHERE up.user_id = p_user_id
      AND up.revoked_at IS NULL
      AND (up.expires_at IS NULL OR up.expires_at > NOW())
      AND up.grant_type = 'deny';
    
    -- Check if user has any direct permissions
    has_direct := (direct_granted IS NOT NULL AND array_length(direct_granted, 1) > 0) OR
                  (direct_denied IS NOT NULL AND array_length(direct_denied, 1) > 0);
    
    -- Update the users table cache
    UPDATE users
    SET 
        has_direct_permissions = has_direct,
        direct_permissions = COALESCE(direct_granted, ARRAY[]::TEXT[]),
        denied_permissions = COALESCE(direct_denied, ARRAY[]::TEXT[])
    WHERE id = p_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Permissions removed as requested

COMMENT ON FUNCTION get_user_permissions(UUID) IS 'Get all permissions for a user (excludes denied permissions)';
COMMENT ON FUNCTION get_user_roles(UUID) IS 'Get all active roles for a user';
COMMENT ON FUNCTION has_permission(UUID, TEXT) IS 'Check if user has a specific permission (considers denials)';
COMMENT ON FUNCTION get_role_id(TEXT) IS 'Get role ID by name';
COMMENT ON FUNCTION get_permission_id(TEXT) IS 'Get permission ID by name';
COMMENT ON FUNCTION update_user_permission_cache(UUID) IS 'Update user permission caches for both granted and denied permissions';