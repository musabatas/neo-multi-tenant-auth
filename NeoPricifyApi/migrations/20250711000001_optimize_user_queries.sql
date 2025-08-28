-- Migration: Optimize user list queries to prevent N+1 problems
-- Created: 2025-07-11
-- Description: Creates optimized RPC function for fetching users with roles in single query

-- Function to get users with their roles in a single optimized query
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
    -- Build WHERE conditions for users table
    IF p_search IS NOT NULL AND LENGTH(TRIM(p_search)) > 0 THEN
        where_conditions := array_append(where_conditions, 
            format('(u.username ILIKE %L OR u.first_name ILIKE %L OR u.last_name ILIKE %L OR u.display_name ILIKE %L)', 
                   '%' || p_search || '%', '%' || p_search || '%', '%' || p_search || '%', '%' || p_search || '%'));
    END IF;
    
    IF p_is_active IS NOT NULL THEN
        where_conditions := array_append(where_conditions, 
            format('u.is_active = %L', p_is_active));
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
    
    -- Build ORDER BY clause (ensure valid column names)
    IF p_order_by IN ('created_at', 'updated_at', 'username', 'first_name', 'last_name', 'display_name') THEN
        IF p_order_desc THEN
            order_clause := format('ORDER BY u.%I DESC', p_order_by);
        ELSE
            order_clause := format('ORDER BY u.%I ASC', p_order_by);
        END IF;
    ELSE
        -- Default to created_at if invalid order_by
        order_clause := 'ORDER BY u.created_at DESC';
    END IF;
    
    -- Count query
    count_query_text := format('
        SELECT COUNT(DISTINCT u.id)
        FROM public.users u
        WHERE %s',
        CASE 
            WHEN array_length(where_conditions, 1) > 0 
            THEN array_to_string(where_conditions, ' AND ')
            ELSE 'TRUE'
        END
    );
    
    -- Execute count query
    EXECUTE count_query_text INTO total_count;
    
    -- Main query with roles aggregation
    query_text := format('
        SELECT json_build_object(
            ''users'', COALESCE(json_agg(user_with_roles), ''[]''::json),
            ''total'', %s
        )
        FROM (
            SELECT 
                u.id,
                u.username,
                u.first_name,
                u.last_name,
                u.display_name,
                u.avatar_url,
                u.bio,
                u.is_active,
                u.onboarding_completed,
                u.has_direct_permissions,
                u.cached_permissions,
                u.cached_roles,
                u.metadata,
                u.created_at,
                u.updated_at,
                u.last_active_at,
                COALESCE(
                    json_agg(
                        CASE 
                            WHEN r.id IS NOT NULL 
                            THEN json_build_object(
                                ''name'', r.name,
                                ''description'', r.description,
                                ''priority'', r.priority,
                                ''granted_at'', ur.granted_at,
                                ''expires_at'', ur.expires_at
                            )
                            ELSE NULL
                        END
                    ) FILTER (WHERE r.id IS NOT NULL),
                    ''[]''::json
                ) as roles
            FROM public.users u
            LEFT JOIN auth_user_roles ur ON u.id = ur.user_id 
                AND ur.revoked_at IS NULL
                AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
            LEFT JOIN auth_roles r ON ur.role_id = r.id 
                AND r.deleted_at IS NULL
            WHERE %s
            GROUP BY u.id, u.username, u.first_name, u.last_name, u.display_name, 
                     u.avatar_url, u.bio, u.is_active, u.onboarding_completed,
                     u.has_direct_permissions, u.cached_permissions, u.cached_roles,
                     u.metadata, u.created_at, u.updated_at, u.last_active_at
            %s
            LIMIT %s OFFSET %s
        ) as user_with_roles',
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

-- Grant execute permission to service role
GRANT EXECUTE ON FUNCTION get_users_with_roles_optimized(INTEGER, INTEGER, TEXT, TEXT, BOOLEAN, TEXT, BOOLEAN) TO service_role;

-- Create optimized indexes for the query performance (using btree since pg_trgm not available)
CREATE INDEX IF NOT EXISTS idx_users_search_optimization 
ON public.users USING btree(username text_pattern_ops, first_name text_pattern_ops, last_name text_pattern_ops);

CREATE INDEX IF NOT EXISTS idx_users_active_created 
ON public.users (last_active_at DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_user_roles_user_active 
ON auth_user_roles (user_id, role_id) WHERE revoked_at IS NULL;

-- Index for role filtering with expiration check (simplified - no NOW() function)
CREATE INDEX IF NOT EXISTS idx_user_roles_composite_active 
ON auth_user_roles (user_id, role_id, granted_at) 
WHERE revoked_at IS NULL;

-- Index for JOIN optimization
CREATE INDEX IF NOT EXISTS idx_auth_roles_active 
ON auth_roles (id, name) WHERE deleted_at IS NULL;

COMMENT ON FUNCTION get_users_with_roles_optimized IS 
'Optimized function to retrieve users with their roles in a single query, preventing N+1 problems. Uses JSON aggregation to combine user data with role information efficiently.';