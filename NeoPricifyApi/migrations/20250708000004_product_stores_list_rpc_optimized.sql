-- Drop existing function if exists
DROP FUNCTION IF EXISTS public.get_product_stores_list;

-- Create optimized RPC function for Product Stores List
CREATE OR REPLACE FUNCTION public.get_product_stores_list(
    p_search TEXT DEFAULT NULL::TEXT,
    p_brand_ids INTEGER[] DEFAULT NULL::INTEGER[],
    p_website_ids INTEGER[] DEFAULT NULL::INTEGER[],
    p_store_ids INTEGER[] DEFAULT NULL::INTEGER[],
    p_states VARCHAR[] DEFAULT NULL::VARCHAR[],
    p_category_ids INTEGER[] DEFAULT NULL::INTEGER[],
    p_product_types TEXT[] DEFAULT NULL::TEXT[],
    p_stock_statuses TEXT[] DEFAULT NULL::TEXT[],
    p_min_price NUMERIC DEFAULT NULL::NUMERIC,
    p_max_price NUMERIC DEFAULT NULL::NUMERIC,
    p_product_is_active BOOLEAN DEFAULT NULL,
    p_product_store_is_active BOOLEAN DEFAULT NULL,
    p_is_reference_store BOOLEAN DEFAULT NULL,
    p_updated_from TIMESTAMPTZ DEFAULT NULL,
    p_updated_to TIMESTAMPTZ DEFAULT NULL,
    p_page INTEGER DEFAULT 1,
    p_page_size INTEGER DEFAULT 25,
    p_sort_by TEXT DEFAULT 'updated_at',
    p_sort_direction TEXT DEFAULT 'desc'
) 
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_result JSONB;
    v_offset INT;
BEGIN
    v_offset := (p_page - 1) * p_page_size;

    -- CTE for recursive category hierarchy
    WITH RECURSIVE category_descendants AS (
        SELECT DISTINCT descendant_id
        FROM unnest(p_category_ids) AS category_id
        CROSS JOIN LATERAL get_category_and_descendants(category_id) AS descendant_id
        WHERE p_category_ids IS NOT NULL
    ),
    base AS (
        SELECT 
            ps.id,
            ps.product_id,
            ps.store_id,
            ps.website_id,
            ps.store_url,
            ps.query_params,
            ps.url_type,
            ps.is_active,
            ps.display_order,
            ps.created_at,
            ps.updated_at,
            
            -- Product details
            p.name as product_name,
            p.global_code,
            p.sku as product_sku,
            p.product_type,
            p.base_image_url as product_image_url,
            p.is_active as product_is_active,
            p.description as product_description,
            
            -- Brand details
            b.id as brand_id,
            b.name as brand_name,
            b.slug as brand_slug,
            b.image_url as brand_image_url,
            
            -- Store details
            s.name as store_name,
            s.code as store_code,
            s.is_active as store_is_active,
            s.is_reference_store,
            
            -- Store address
            a.state as store_state,
            a.city as store_city,
            a.country_code as store_country_code,
            
            -- Website details
            w.name as website_name,
            w.url as website_url,
            w.logo_url as website_logo_url,
            w.code as website_code,
            
            -- Vendor details
            v.id as vendor_id,
            v.name as vendor_name,
            
            -- Latest price information
            psp.regular_price,
            psp.sale_price,
            psp.price as current_price,
            psp.currency_code,
            psp.updated_at as price_updated_at,
            
            -- Latest inventory information
            psi.stock_qty,
            psi.stock_status,
            psi.manage_stock,
            psi.updated_at as inventory_updated_at,
            
            -- Product website details
            pwd.name as website_product_name,
            pwd.sku as website_product_sku,
            pwd.default_url as website_default_url,
            
            -- Calculate full URL for the product store
            CASE 
                WHEN ps.url_type = 'full_url' THEN ps.store_url
                WHEN ps.url_type = 'full_url_with_params' AND ps.store_url IS NOT NULL THEN 
                    ps.store_url || CASE 
                        WHEN position('?' in ps.store_url) > 0 THEN '&' 
                        ELSE '?' 
                    END || COALESCE(ps.query_params, '')
                WHEN ps.url_type = 'query_params_only' AND pwd.default_url IS NOT NULL THEN 
                    pwd.default_url || CASE 
                        WHEN position('?' in pwd.default_url) > 0 THEN '&' 
                        ELSE '?' 
                    END || COALESCE(ps.query_params, '')
                WHEN ps.url_type = 'same_as_website' THEN pwd.default_url
                ELSE NULL
            END as full_url,
            
            -- For sorting
            GREATEST(
                COALESCE(psp.updated_at, ps.created_at), 
                COALESCE(psi.updated_at, ps.created_at), 
                ps.updated_at
            ) as last_updated
            
        FROM public.product_stores ps
        JOIN public.products p ON p.id = ps.product_id
        LEFT JOIN public.brands b ON b.id = p.brand_id
        JOIN public.stores s ON s.id = ps.store_id
        LEFT JOIN public.addresses a ON a.id = s.address_id
        JOIN public.websites w ON w.id = ps.website_id
        LEFT JOIN public.vendors v ON v.id = w.vendor_id
        LEFT JOIN LATERAL (
            SELECT * FROM public.product_store_prices
            WHERE product_store_id = ps.id
            ORDER BY updated_at DESC
            LIMIT 1
        ) psp ON true
        LEFT JOIN LATERAL (
            SELECT * FROM public.product_store_inventory
            WHERE product_store_id = ps.id
            ORDER BY updated_at DESC
            LIMIT 1
        ) psi ON true
        LEFT JOIN public.product_website_details pwd ON pwd.product_id = p.id AND pwd.website_id = w.id
        
        WHERE 
            -- Base filters
            p.deleted_at IS NULL 
            AND s.deleted_at IS NULL
            AND w.deleted_at IS NULL
            
            -- Search filter
            AND (
                p_search IS NULL OR (
                    p.name ILIKE '%' || p_search || '%' OR
                    p.global_code ILIKE '%' || p_search || '%' OR
                    p.sku ILIKE '%' || p_search || '%' OR
                    COALESCE(pwd.name, '') ILIKE '%' || p_search || '%' OR
                    COALESCE(pwd.sku, '') ILIKE '%' || p_search || '%' OR
                    COALESCE(b.name, '') ILIKE '%' || p_search || '%' OR
                    s.name ILIKE '%' || p_search || '%' OR
                    w.name ILIKE '%' || p_search || '%'
                )
            )
            
            -- Brand filter
            AND (p_brand_ids IS NULL OR b.id = ANY(p_brand_ids))
            
            -- Website filter
            AND (p_website_ids IS NULL OR w.id = ANY(p_website_ids))
            
            -- Store filter
            AND (p_store_ids IS NULL OR s.id = ANY(p_store_ids))
            
            -- State filter
            AND (p_states IS NULL OR a.state = ANY(p_states))
            
            -- Category filter with hierarchy
            AND (p_category_ids IS NULL OR EXISTS (
                SELECT 1 
                FROM product_categories pc 
                WHERE pc.product_id = p.id 
                AND pc.category_id IN (SELECT descendant_id FROM category_descendants)
            ))
            
            -- Product type filter
            AND (p_product_types IS NULL OR p.product_type::TEXT = ANY(p_product_types))
            
            -- Stock status filter
            AND (p_stock_statuses IS NULL OR COALESCE(psi.stock_status::TEXT, 'unknown') = ANY(p_stock_statuses))
            
            -- Price range filters
            AND (p_min_price IS NULL OR COALESCE(psp.price, 0) >= p_min_price)
            AND (p_max_price IS NULL OR COALESCE(psp.price, 0) <= p_max_price)
            
            -- Active filters
            AND (p_product_is_active IS NULL OR p.is_active = p_product_is_active)
            AND (p_product_store_is_active IS NULL OR ps.is_active = p_product_store_is_active)
            
            -- Reference store filter
            AND (p_is_reference_store IS NULL OR s.is_reference_store = p_is_reference_store)
            
            -- Last updated date filters
            AND (
                p_updated_from IS NULL OR 
                GREATEST(
                    COALESCE(psp.updated_at, ps.created_at), 
                    COALESCE(psi.updated_at, ps.created_at), 
                    ps.updated_at
                ) >= p_updated_from
            )
            AND (
                p_updated_to IS NULL OR 
                GREATEST(
                    COALESCE(psp.updated_at, ps.created_at), 
                    COALESCE(psi.updated_at, ps.created_at), 
                    ps.updated_at
                ) <= p_updated_to
            )
    ),
    total_cte AS (
        SELECT COUNT(*) as total_count FROM base
    ),
    data_cte AS (
        SELECT * FROM base
        ORDER BY 
            CASE WHEN p_sort_by = 'product_name' AND p_sort_direction = 'asc' THEN product_name END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'product_name' AND p_sort_direction = 'desc' THEN product_name END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'store_name' AND p_sort_direction = 'asc' THEN store_name END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'store_name' AND p_sort_direction = 'desc' THEN store_name END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'website_name' AND p_sort_direction = 'asc' THEN website_name END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'website_name' AND p_sort_direction = 'desc' THEN website_name END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'brand_name' AND p_sort_direction = 'asc' THEN brand_name END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'brand_name' AND p_sort_direction = 'desc' THEN brand_name END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'price' AND p_sort_direction = 'asc' THEN current_price END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'price' AND p_sort_direction = 'desc' THEN current_price END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'stock_qty' AND p_sort_direction = 'asc' THEN stock_qty END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'stock_qty' AND p_sort_direction = 'desc' THEN stock_qty END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'stock_status' AND p_sort_direction = 'asc' THEN stock_status END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'stock_status' AND p_sort_direction = 'desc' THEN stock_status END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'updated_at' AND p_sort_direction = 'asc' THEN last_updated END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'updated_at' AND p_sort_direction = 'desc' THEN last_updated END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'created_at' AND p_sort_direction = 'asc' THEN created_at END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'created_at' AND p_sort_direction = 'desc' THEN created_at END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'id' OR p_sort_by IS NULL THEN id END DESC NULLS LAST
        LIMIT p_page_size OFFSET v_offset
    )
    SELECT jsonb_build_object(
        'data', COALESCE(jsonb_agg(
            jsonb_build_object(
                'id', d.id,
                'product_id', d.product_id,
                'store_id', d.store_id,
                'website_id', d.website_id,
                'store_url', d.store_url,
                'query_params', d.query_params,
                'store_url_type', d.url_type,
                'full_url', d.full_url,
                'is_active', d.is_active,
                'display_order', d.display_order,
                'created_at', d.created_at,
                'updated_at', d.updated_at,
                'last_updated', d.last_updated,
                
                'product', jsonb_build_object(
                    'id', d.product_id,
                    'name', COALESCE(d.website_product_name, d.product_name),
                    'global_code', d.global_code,
                    'sku', COALESCE(d.website_product_sku, d.product_sku),
                    'product_type', d.product_type,
                    'description', d.product_description,
                    'image_url', d.product_image_url,
                    'is_active', d.product_is_active,
                    'categories', '[]'::jsonb  -- Removed subquery for performance
                ),
                
                'brand', CASE 
                    WHEN d.brand_id IS NOT NULL THEN jsonb_build_object(
                        'id', d.brand_id,
                        'name', d.brand_name,
                        'slug', d.brand_slug,
                        'image_url', d.brand_image_url
                    )
                    ELSE NULL 
                END,
                
                'store', jsonb_build_object(
                    'id', d.store_id,
                    'name', d.store_name,
                    'code', d.store_code,
                    'is_active', d.store_is_active,
                    'is_reference_store', d.is_reference_store,
                    'address', CASE 
                        WHEN d.store_state IS NOT NULL THEN jsonb_build_object(
                            'state', d.store_state,
                            'city', d.store_city,
                            'country_code', d.store_country_code
                        )
                        ELSE NULL
                    END
                ),
                
                'website', jsonb_build_object(
                    'id', d.website_id,
                    'name', d.website_name,
                    'url', d.website_url,
                    'logo_url', d.website_logo_url,
                    'code', d.website_code,
                    'vendor', CASE 
                        WHEN d.vendor_id IS NOT NULL THEN jsonb_build_object(
                            'id', d.vendor_id,
                            'name', d.vendor_name
                        )
                        ELSE NULL
                    END
                ),
                
                'price_data', jsonb_build_object(
                    'regular_price', d.regular_price,
                    'sale_price', d.sale_price,
                    'current_price', d.current_price,
                    'currency_code', d.currency_code,
                    'updated_at', d.price_updated_at
                ),
                
                'inventory_data', jsonb_build_object(
                    'stock_qty', d.stock_qty,
                    'stock_status', d.stock_status,
                    'manage_stock', d.manage_stock,
                    'updated_at', d.inventory_updated_at
                )
            )
        ), '[]'::jsonb),
        'pagination', jsonb_build_object(
            'total_count', (SELECT total_count FROM total_cte),
            'page_size', p_page_size,
            'page', p_page,
            'total_pages', CEIL((SELECT total_count FROM total_cte)::FLOAT / p_page_size)::INTEGER
        ),
        'sorting', jsonb_build_object(
            'fields', ARRAY[
                'id', 'product_name', 'store_name', 'website_name', 'brand_name',
                'price', 'stock_qty', 'stock_status',
                'updated_at', 'created_at'
            ],
            'directions', ARRAY['asc', 'desc']
        )
    )
    INTO v_result
    FROM data_cte d;

    RETURN v_result;
END;
$$;

-- Add comment
COMMENT ON FUNCTION public.get_product_stores_list IS 'Optimized function for fetching paginated product stores with comprehensive filtering, sorting, and search capabilities';

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_product_stores_product_website 
ON public.product_stores(product_id, website_id, store_id);

CREATE INDEX IF NOT EXISTS idx_product_store_prices_updated 
ON public.product_store_prices(product_store_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_product_store_inventory_updated 
ON public.product_store_inventory(product_store_id, updated_at DESC);