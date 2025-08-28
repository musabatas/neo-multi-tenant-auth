-- Migration: Create cache management functions and triggers
-- Description: Manages automatic cache updates for role permissions

-- Function to refresh role permissions cache
CREATE OR REPLACE FUNCTION refresh_role_permissions(p_role_id BIGINT DEFAULT NULL)
RETURNS void AS $$
BEGIN
    IF p_role_id IS NULL THEN
        -- Refresh all roles
        UPDATE auth_roles r
        SET cached_permissions = (
            SELECT COALESCE(ARRAY_AGG(DISTINCT p.name ORDER BY p.name), ARRAY[]::TEXT[])
            FROM auth_role_permissions rp
            JOIN auth_permissions p ON rp.permission_id = p.id
            WHERE rp.role_id = r.id
        )
        WHERE deleted_at IS NULL;
    ELSE
        -- Refresh specific role
        UPDATE auth_roles
        SET cached_permissions = (
            SELECT COALESCE(ARRAY_AGG(DISTINCT p.name ORDER BY p.name), ARRAY[]::TEXT[])
            FROM auth_role_permissions rp
            JOIN auth_permissions p ON rp.permission_id = p.id
            WHERE rp.role_id = p_role_id
        )
        WHERE id = p_role_id;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to auto-update cache when role permissions change
CREATE OR REPLACE FUNCTION trigger_refresh_role_permissions()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        PERFORM refresh_role_permissions(OLD.role_id);
        RETURN OLD;
    ELSE
        PERFORM refresh_role_permissions(NEW.role_id);
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auto_refresh_role_permissions
AFTER INSERT OR UPDATE OR DELETE ON auth_role_permissions
FOR EACH ROW EXECUTE FUNCTION trigger_refresh_role_permissions();

-- Trigger to refresh role permissions cache when permissions change
CREATE OR REPLACE FUNCTION trigger_permission_change()
RETURNS TRIGGER AS $$
BEGIN
    -- Find and update all roles that have this permission
    UPDATE auth_roles r
    SET cached_permissions = (
        SELECT COALESCE(ARRAY_AGG(DISTINCT p.name ORDER BY p.name), ARRAY[]::TEXT[])
        FROM auth_role_permissions rp
        JOIN auth_permissions p ON rp.permission_id = p.id
        WHERE rp.role_id = r.id
    )
    WHERE r.id IN (
        SELECT DISTINCT role_id 
        FROM auth_role_permissions 
        WHERE permission_id = COALESCE(NEW.id, OLD.id)
    );
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Add trigger for when permission definitions change
CREATE TRIGGER auto_update_role_cache_on_permission_change
AFTER UPDATE OR DELETE ON auth_permissions
FOR EACH ROW EXECUTE FUNCTION trigger_permission_change();

-- Function to handle temporal permission expiration
CREATE OR REPLACE FUNCTION check_and_refresh_expired_permissions(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    has_expired_permissions BOOLEAN;
BEGIN
    -- Check if user has any expired permissions
    SELECT EXISTS (
        SELECT 1 
        FROM auth_user_roles ur
        WHERE ur.user_id = p_user_id
          AND ur.expires_at IS NOT NULL
          AND ur.expires_at <= NOW()
          AND ur.revoked_at IS NULL
        UNION
        SELECT 1
        FROM auth_user_permissions up
        WHERE up.user_id = p_user_id
          AND up.expires_at IS NOT NULL
          AND up.expires_at <= NOW()
          AND up.revoked_at IS NULL
    ) INTO has_expired_permissions;
    
    -- If expired permissions found, refresh user's direct permissions cache
    IF has_expired_permissions THEN
        PERFORM refresh_user_direct_permissions(p_user_id);
    END IF;
    
    RETURN has_expired_permissions;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Initial population of role permissions cache
SELECT refresh_role_permissions();

-- Permissions removed as requested

-- Comments
COMMENT ON FUNCTION refresh_role_permissions(BIGINT) IS 'Refresh cached permissions for roles';
COMMENT ON FUNCTION trigger_permission_change() IS 'Update role cache when permission definitions change';
COMMENT ON FUNCTION check_and_refresh_expired_permissions(UUID) IS 'Check and refresh cache for expired permissions';