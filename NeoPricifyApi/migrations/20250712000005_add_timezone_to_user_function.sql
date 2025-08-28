-- Drop the existing function if it exists
DROP FUNCTION IF EXISTS public.get_user_with_permissions(uuid);

-- Create the new function with timezone field
-- Add timezone field to get_user_with_permissions function
CREATE OR REPLACE FUNCTION public.get_user_with_permissions(p_user_id UUID)
RETURNS TABLE (
    -- Core fields
    id UUID,
    email TEXT,
    phone TEXT,
    
    -- Auth status fields
    email_verified BOOLEAN,
    phone_verified BOOLEAN,
    is_active BOOLEAN,
    is_super_admin BOOLEAN,
    is_sso_user BOOLEAN,
    is_anonymous BOOLEAN,
    
    -- Timestamps
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    last_sign_in_at TIMESTAMPTZ,
    email_confirmed_at TIMESTAMPTZ,
    phone_confirmed_at TIMESTAMPTZ,
    invited_at TIMESTAMPTZ,
    confirmed_at TIMESTAMPTZ,
    confirmation_sent_at TIMESTAMPTZ,
    recovery_sent_at TIMESTAMPTZ,
    email_change_sent_at TIMESTAMPTZ,
    banned_until TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,
    
    -- Auth metadata
    aud TEXT,
    role TEXT,
    email_change TEXT,
    raw_user_meta_data JSONB,
    
    -- RBAC fields
    primary_role TEXT,
    roles TEXT[],
    permissions TEXT[],
    
    -- Profile fields
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    display_name TEXT,
    avatar_url TEXT,
    bio TEXT,
    
    -- Permission fields
    has_direct_permissions BOOLEAN,
    direct_permissions TEXT[],
    denied_permissions TEXT[],
    
    -- Additional fields
    onboarding_completed BOOLEAN,
    last_active_at TIMESTAMPTZ,
    metadata JSONB,
    preferences JSONB,
    timezone TEXT  -- Added timezone field
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        -- Core fields
        au.id,
        au.email::TEXT,
        COALESCE(au.phone::TEXT, '') as phone,
        
        -- Auth status fields
        (au.email_confirmed_at IS NOT NULL) as email_verified,
        (au.phone_confirmed_at IS NOT NULL) as phone_verified,
        (au.deleted_at IS NULL AND (au.banned_until IS NULL OR au.banned_until < NOW())) as is_active,
        COALESCE(au.is_super_admin, FALSE) as is_super_admin,
        au.is_sso_user,
        au.is_anonymous,
        
        -- Timestamps
        au.created_at,
        au.updated_at,
        au.last_sign_in_at,
        au.email_confirmed_at,
        au.phone_confirmed_at,
        au.invited_at,
        au.confirmed_at,
        au.confirmation_sent_at,
        au.recovery_sent_at,
        au.email_change_sent_at,
        au.banned_until,
        au.deleted_at,
        
        -- Auth metadata
        au.aud::TEXT,
        au.role::TEXT,
        au.email_change::TEXT,
        au.raw_user_meta_data,
        
        -- RBAC fields
        (get_user_roles(au.id))[1] as primary_role,
        get_user_roles(au.id) as roles,
        get_user_permissions(au.id) as permissions,
        
        -- Profile fields
        u.username,
        u.first_name,
        u.last_name,
        u.display_name,
        u.avatar_url,
        u.bio,
        
        -- Permission fields
        COALESCE(u.has_direct_permissions, FALSE) as has_direct_permissions,
        COALESCE(u.direct_permissions, ARRAY[]::TEXT[]) as direct_permissions,
        COALESCE(u.denied_permissions, ARRAY[]::TEXT[]) as denied_permissions,
        
        -- Additional fields
        COALESCE(u.onboarding_completed, FALSE) as onboarding_completed,
        u.last_active_at,
        COALESCE(u.metadata, '{}'::jsonb) as metadata,
        COALESCE(u.preferences, '{}'::jsonb) as preferences,
        u.timezone  -- Added timezone field
    FROM auth.users au
    LEFT JOIN public.users u ON au.id = u.id
    WHERE au.id = p_user_id;
END;
$$;