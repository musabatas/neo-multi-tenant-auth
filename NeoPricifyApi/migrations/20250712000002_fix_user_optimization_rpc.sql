-- Migration: Fix get_users_with_roles_optimized function to use correct column names and merge permissions
-- Created: 2025-07-12
-- Description: Updates the RPC function to fix column references and properly merge role + direct permissions

-- Drop and recreate the function with correct column names and permission merging
DROP FUNCTION IF EXISTS get_users_with_roles_optimized(INTEGER, INTEGER, TEXT, TEXT, BOOLEAN, TEXT, BOOLEAN);

CREATE OR REPLACE FUNCTION get_users_with_roles_optimized(
    p_limit INTEGER DEFAULT 20,
    p_offset INTEGER DEFAULT 0,
    p_search TEXT DEFAULT NULL,
    p_role_filter TEXT DEFAULT NULL,
    p_is_active BOOLEAN DEFAULT NULL,
    p_order_by TEXT DEFAULT 'created_at',
    p_order_desc BOOLEAN DEFAULT TRUE
)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    query_text TEXT;
    count_query_text TEXT;
    order_clause TEXT;
    where_conditions TEXT[] := ARRAY[]::TEXT[];
    total_count INTEGER;
    users_result JSON;
BEGIN
    -- Build WHERE conditions - search across both users and auth.users tables
    IF p_search IS NOT NULL AND LENGTH(TRIM(p_search)) > 0 THEN
        where_conditions := array_append(where_conditions, 
            format('(u.username ILIKE %L OR u.first_name ILIKE %L OR u.last_name ILIKE %L OR u.display_name ILIKE %L OR au.email ILIKE %L)', 
                   '%' || p_search || '%', '%' || p_search || '%', '%' || p_search || '%', '%' || p_search || '%', '%' || p_search || '%'));
    END IF;
    
    -- is_active needs to be computed from auth.users table
    IF p_is_active IS NOT NULL THEN
        IF p_is_active THEN
            where_conditions := array_append(where_conditions, 
                '(au.deleted_at IS NULL AND (au.banned_until IS NULL OR au.banned_until < NOW()))');
        ELSE
            where_conditions := array_append(where_conditions, 
                '(au.deleted_at IS NOT NULL OR (au.banned_until IS NOT NULL AND au.banned_until >= NOW()))');
        END IF;
    END IF;
    
    IF p_role_filter IS NOT NULL AND LENGTH(TRIM(p_role_filter)) > 0 THEN
        where_conditions := array_append(where_conditions, 
            'EXISTS (SELECT 1 FROM auth_user_roles ur 
                    JOIN auth_roles r ON ur.role_id = r.id 
                    WHERE ur.user_id = u.id 
                    AND ur.revoked_at IS NULL 
                    AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                    AND r.name = ' || quote_literal(p_role_filter) || ')');
    END IF;
    
    -- Build ORDER BY clause (ensure valid column names from auth.users for created_at)
    IF p_order_by IN ('created_at', 'updated_at') THEN
        IF p_order_desc THEN
            order_clause := format('ORDER BY au.%I DESC', p_order_by);
        ELSE
            order_clause := format('ORDER BY au.%I ASC', p_order_by);
        END IF;
    ELSIF p_order_by IN ('username', 'first_name', 'last_name', 'display_name') THEN
        IF p_order_desc THEN
            order_clause := format('ORDER BY u.%I DESC NULLS LAST', p_order_by);
        ELSE
            order_clause := format('ORDER BY u.%I ASC NULLS LAST', p_order_by);
        END IF;
    ELSE
        -- Default to created_at if invalid order_by
        order_clause := 'ORDER BY au.created_at DESC';
    END IF;
    
    -- Count query (need to join with auth.users for proper filtering)
    count_query_text := format('
        SELECT COUNT(DISTINCT u.id)
        FROM public.users u
        LEFT JOIN auth.users au ON u.id = au.id
        WHERE %s',
        CASE 
            WHEN array_length(where_conditions, 1) > 0 
            THEN array_to_string(where_conditions, ' AND ')
            ELSE 'TRUE'
        END
    );
    
    -- Execute count query
    EXECUTE count_query_text INTO total_count;
    
    -- Main query with roles aggregation and merged permissions
    query_text := format('
        SELECT json_build_object(
            ''users'', COALESCE(json_agg(user_with_roles), ''[]''::json),
            ''total'', %s
        )
        FROM (
            SELECT json_build_object(
                ''id'', u.id,
                ''username'', u.username,
                ''first_name'', u.first_name,
                ''last_name'', u.last_name,
                ''display_name'', u.display_name,
                ''avatar_url'', u.avatar_url,
                ''bio'', u.bio,
                ''email'', au.email,
                ''phone'', au.phone,
                ''is_active'', (au.deleted_at IS NULL AND (au.banned_until IS NULL OR au.banned_until < NOW())),
                ''email_verified'', (au.email_confirmed_at IS NOT NULL),
                ''phone_verified'', (au.phone_confirmed_at IS NOT NULL),
                ''onboarding_completed'', COALESCE(u.onboarding_completed, false),
                ''has_direct_permissions'', COALESCE(u.has_direct_permissions, false),
                ''metadata'', COALESCE(u.metadata, ''{}''::jsonb),
                ''created_at'', au.created_at,
                ''updated_at'', au.updated_at,
                ''last_sign_in_at'', au.last_sign_in_at,
                ''email_confirmed_at'', au.email_confirmed_at,
                ''phone_confirmed_at'', au.phone_confirmed_at,
                ''last_active_at'', u.last_active_at,
                ''roles'', COALESCE(role_agg.roles, ''[]''::json),
                ''permissions'', COALESCE(merged_perms.all_permissions, ''[]''::json),
                ''denied_permissions'', COALESCE(u.denied_permissions, ''[]''::text[])
            ) as user_with_roles
            FROM public.users u
            LEFT JOIN auth.users au ON u.id = au.id
            LEFT JOIN (
                -- Aggregate roles for each user
                SELECT 
                    ur.user_id,
                    json_agg(
                        json_build_object(
                            ''name'', r.name,
                            ''description'', r.description,
                            ''priority'', r.priority,
                            ''granted_at'', ur.granted_at,
                            ''expires_at'', ur.expires_at
                        )
                        ORDER BY r.priority DESC
                    ) as roles
                FROM auth_user_roles ur 
                JOIN auth_roles r ON ur.role_id = r.id 
                WHERE ur.revoked_at IS NULL
                  AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                  AND r.deleted_at IS NULL
                GROUP BY ur.user_id
            ) role_agg ON u.id = role_agg.user_id
            LEFT JOIN (
                -- Merge role permissions with direct permissions
                SELECT 
                    u_perm.id as user_id,
                    COALESCE(
                        (
                            SELECT array_agg(DISTINCT perm) 
                            FROM (
                                -- Permissions from roles
                                SELECT UNNEST(r.cached_permissions) as perm
                                FROM auth_user_roles ur
                                JOIN auth_roles r ON ur.role_id = r.id
                                WHERE ur.user_id = u_perm.id
                                  AND ur.revoked_at IS NULL
                                  AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                                  AND r.deleted_at IS NULL
                                
                                UNION ALL
                                
                                -- Direct permissions
                                SELECT UNNEST(u_perm.direct_permissions)
                                WHERE u_perm.has_direct_permissions = true
                            ) all_granted_perms
                            WHERE perm IS NOT NULL
                              AND perm != ALL(COALESCE(u_perm.denied_permissions, ARRAY[]::TEXT[]))
                        ),
                        ARRAY[]::TEXT[]
                    ) as all_permissions
                FROM public.users u_perm
            ) merged_perms ON u.id = merged_perms.user_id
            WHERE %s
            %s
            LIMIT %s OFFSET %s
        ) as user_data',
        total_count,
        CASE 
            WHEN array_length(where_conditions, 1) > 0 
            THEN array_to_string(where_conditions, ' AND ')
            ELSE 'TRUE'
        END,
        order_clause,
        p_limit,
        p_offset
    );
    
    -- Execute main query
    EXECUTE query_text INTO users_result;
    
    RETURN users_result;
END;
$$;

-- Grant execute permission to service role and authenticated users
GRANT EXECUTE ON FUNCTION get_users_with_roles_optimized(INTEGER, INTEGER, TEXT, TEXT, BOOLEAN, TEXT, BOOLEAN) TO service_role;
GRANT EXECUTE ON FUNCTION get_users_with_roles_optimized(INTEGER, INTEGER, TEXT, TEXT, BOOLEAN, TEXT, BOOLEAN) TO authenticated;

COMMENT ON FUNCTION get_users_with_roles_optimized IS 
'Optimized function to retrieve users with their roles and merged permissions in a single query. Properly merges role permissions with direct permissions and excludes denied permissions. Uses correct column references for public.users and auth.users tables.';