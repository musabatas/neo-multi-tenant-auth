DROP FUNCTION IF EXISTS public.get_products_with_relations;

create or replace function public.get_products_with_relations(p_search text DEFAULT NULL::text, p_brand_ids integer[] DEFAULT NULL::integer[], p_product_types text[] DEFAULT NULL::text[], p_visibilities text[] DEFAULT NULL::text[], p_category_ids integer[] DEFAULT NULL::integer[], p_collection_ids integer[] DEFAULT NULL::integer[], p_website_ids integer[] DEFAULT NULL::integer[], p_attribute_option_ids integer[] DEFAULT NULL::integer[], p_min_price numeric DEFAULT NULL::numeric, p_max_price numeric DEFAULT NULL::numeric, p_min_profit_amount numeric DEFAULT NULL::numeric, p_max_profit_amount numeric DEFAULT NULL::numeric, p_min_profit_percentage numeric DEFAULT NULL::numeric, p_max_profit_percentage numeric DEFAULT NULL::numeric, p_ref_store_ids integer[] DEFAULT NULL::integer[], p_ref_min_profit_amount numeric DEFAULT NULL::numeric, p_ref_max_profit_amount numeric DEFAULT NULL::numeric, p_ref_min_profit_percentage numeric DEFAULT NULL::numeric, p_ref_max_profit_percentage numeric DEFAULT NULL::numeric, p_page integer DEFAULT 1, p_page_size integer DEFAULT 25, p_sort_by text DEFAULT 'ref_profit_percentage'::text, p_sort_direction text DEFAULT 'desc'::text) returns jsonb
    language plpgsql
as
$$
DECLARE
    v_result JSONB;
    v_offset INT;
BEGIN
    v_offset := (p_page - 1) * p_page_size;

    WITH RECURSIVE category_descendants AS (
        SELECT DISTINCT descendant_id
        FROM unnest(p_category_ids) AS category_id
        CROSS JOIN LATERAL get_category_and_descendants(category_id) AS descendant_id
        WHERE p_category_ids IS NOT NULL
    ),
    base AS (
        SELECT 
            p.id,
            p.global_code,
            p.name,
            p.description,
            p.sku,
            p.product_type,
            p.visibility,
            p.sellable,
            p.base_image_url,
            p.attribute_data,
            p.meta_data,
            p.is_active,
            p.created_at,
            p.updated_at,
            b.id as brand_id,
            b.name as brand_name,
            ppa.min_price_usd,
            ppa.max_price_usd,
            ppa.profit_amount,
            ppa.profit_percentage,
            ppa.updated_at as price_updated_at,
            min_s.id as min_price_store_id,
            min_s.name as min_price_store_name,
            min_w.id as min_price_website_id,
            min_w.name as min_price_website_name,
            min_w.url as min_price_website_url,
            min_w.logo_url as min_price_website_logo,
            max_s.id as max_price_store_id,
            max_s.name as max_price_store_name,
            max_w.id as max_price_website_id,
            max_w.name as max_price_website_name,
            max_w.url as max_price_website_url,
            max_w.logo_url as max_price_website_logo,
            pwd.name as website_product_name,
            pwd.sku as website_product_sku,
            pwd.base_image_url as website_base_image_url,
            pwd.is_active as website_is_active,

            -- Reference profit sorting fields
            (
                SELECT MAX((ref_price ->> 'profit_amount')::numeric)
                FROM jsonb_array_elements(ppa.reference_prices) AS ref_price
                WHERE (p_ref_store_ids IS NULL OR (ref_price ->> 'store_id')::integer = ANY(p_ref_store_ids))
            ) AS ref_profit_amount,
            (
                SELECT MAX((ref_price ->> 'profit_percentage')::numeric)
                FROM jsonb_array_elements(ppa.reference_prices) AS ref_price
                WHERE (p_ref_store_ids IS NULL OR (ref_price ->> 'store_id')::integer = ANY(p_ref_store_ids))
            ) AS ref_profit_percentage,

            -- Reference prices
            COALESCE(
                (
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'store', jsonb_build_object(
                                'id', ref_s.id,
                                'name', ref_s.name,
                                'website', CASE
                                    WHEN ref_w.id IS NOT NULL THEN jsonb_build_object(
                                        'id', ref_w.id,
                                        'name', ref_w.name,
                                        'url', ref_w.url,
                                        'logo_url', ref_w.logo_url
                                    )
                                    ELSE NULL
                                END
                            ),
                            'price_usd', (rp_elem ->> 'price_usd')::numeric,
                            'profit_amount', (rp_elem ->> 'profit_amount')::numeric,
                            'profit_percentage', (rp_elem ->> 'profit_percentage')::numeric
                        )
                    )
                    FROM jsonb_array_elements(ppa.reference_prices) AS rp_elem
                    LEFT JOIN stores ref_s ON ref_s.id = (rp_elem ->> 'store_id')::integer
                    LEFT JOIN websites ref_w ON ref_w.id = ref_s.website_id
                    WHERE (rp_elem ->> 'store_id') IS NOT NULL
                ),
                '[]'::jsonb
            ) as enhanced_reference_prices

        FROM product_price_aggregates ppa
        JOIN products p ON p.id = ppa.product_id
        LEFT JOIN brands b ON b.id = p.brand_id
        LEFT JOIN stores min_s ON min_s.id = ppa.min_price_store_id
        LEFT JOIN websites min_w ON min_w.id = min_s.website_id
        LEFT JOIN stores max_s ON max_s.id = ppa.max_price_store_id
        LEFT JOIN websites max_w ON max_w.id = max_s.website_id
        LEFT JOIN LATERAL (
            SELECT 
                pwd.name,
                pwd.sku,
                pwd.base_image_url,
                pwd.is_active
            FROM product_website_details pwd
            WHERE pwd.product_id = p.id
              AND pwd.is_active = true
              AND (p_website_ids IS NULL OR pwd.website_id = ANY(p_website_ids))
            ORDER BY pwd.website_id
            LIMIT 1
        ) pwd ON true
        WHERE p.deleted_at IS NULL
        AND (
            p_search IS NULL OR 
            pwd.name ILIKE '%' || p_search || '%' OR 
            pwd.sku ILIKE '%' || p_search || '%' OR 
            p.global_code ILIKE '%' || p_search || '%' OR
            EXISTS (
                SELECT 1 FROM product_identifiers pi
                -- Join with product_identifier_websites to check website_ids if needed
                LEFT JOIN product_identifier_websites piw ON piw.product_identifier_id = pi.id
                WHERE pi.product_id = p.id
                AND pi.identifier_value ILIKE '%' || p_search || '%'
                -- Optionally filter by website_ids if provided
                AND (p_website_ids IS NULL OR piw.website_id = ANY(p_website_ids))
            )
        )
        AND (p_brand_ids IS NULL OR b.id = ANY(p_brand_ids))
        AND (p_product_types IS NULL OR p.product_type::text = ANY(p_product_types))
        AND (p_visibilities IS NULL OR p.visibility::text = ANY(p_visibilities))
        AND (p_category_ids IS NULL OR EXISTS (
            SELECT 1 FROM product_categories pc
            WHERE pc.product_id = p.id
            AND pc.category_id IN (SELECT descendant_id FROM category_descendants)
        ))
        AND (p_collection_ids IS NULL OR EXISTS (
            SELECT 1 FROM product_collections pcoll
            WHERE pcoll.product_id = p.id
            AND pcoll.collection_id = ANY(p_collection_ids)
        ))
        AND (p_website_ids IS NULL OR EXISTS (
            SELECT 1 FROM product_website_details pwd_filter 
            WHERE pwd_filter.product_id = p.id 
            AND pwd_filter.website_id = ANY(p_website_ids)
        ))
        AND (
            p_attribute_option_ids IS NULL OR 
            array_length(p_attribute_option_ids, 1) IS NULL OR 
            EXISTS (
                SELECT 1 
                FROM product_attributes pa
                WHERE pa.product_id = p.id
                AND pa.attribute_option_id = ANY(p_attribute_option_ids)
            )
        )
        AND (p_min_price IS NULL OR ppa.min_price_usd >= p_min_price)
        AND (p_max_price IS NULL OR ppa.max_price_usd <= p_max_price)
        AND (p_min_profit_amount IS NULL OR ppa.profit_amount >= p_min_profit_amount)
        AND (p_max_profit_amount IS NULL OR ppa.profit_amount <= p_max_profit_amount)
        AND (p_min_profit_percentage IS NULL OR ppa.profit_percentage >= p_min_profit_percentage)
        AND (p_max_profit_percentage IS NULL OR ppa.profit_percentage <= p_max_profit_percentage)

        AND (
            p_ref_store_ids IS NULL AND (
                p_ref_min_profit_amount IS NULL AND
                p_ref_max_profit_amount IS NULL AND
                p_ref_min_profit_percentage IS NULL AND
                p_ref_max_profit_percentage IS NULL
            )
            OR EXISTS (
                SELECT 1
                FROM jsonb_array_elements(ppa.reference_prices) AS ref_price
                WHERE (
                    (p_ref_store_ids IS NULL OR (ref_price ->> 'store_id')::integer = ANY(p_ref_store_ids))
                )
                AND (
                    p_ref_min_profit_amount IS NULL OR (ref_price ->> 'profit_amount')::numeric >= p_ref_min_profit_amount
                )
                AND (
                    p_ref_max_profit_amount IS NULL OR (ref_price ->> 'profit_amount')::numeric <= p_ref_max_profit_amount
                )
                AND (
                    p_ref_min_profit_percentage IS NULL OR (ref_price ->> 'profit_percentage')::numeric >= p_ref_min_profit_percentage
                )
                AND (
                    p_ref_max_profit_percentage IS NULL OR (ref_price ->> 'profit_percentage')::numeric <= p_ref_max_profit_percentage
                )
            )
        )
    ),
    total_cte AS (
        SELECT count(*) as total_count FROM base
    ),
    data_cte AS (
        SELECT * FROM base
        ORDER BY 
            CASE WHEN p_sort_by = 'name' AND p_sort_direction = 'asc' THEN website_product_name END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'name' AND p_sort_direction = 'desc' THEN website_product_name END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'global_code' AND p_sort_direction = 'asc' THEN global_code END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'global_code' AND p_sort_direction = 'desc' THEN global_code END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'min_price' AND p_sort_direction = 'asc' THEN min_price_usd END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'min_price' AND p_sort_direction = 'desc' THEN min_price_usd END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'max_price' AND p_sort_direction = 'asc' THEN max_price_usd END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'max_price' AND p_sort_direction = 'desc' THEN max_price_usd END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'profit_amount' AND p_sort_direction = 'asc' THEN profit_amount END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'profit_amount' AND p_sort_direction = 'desc' THEN profit_amount END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'profit_percentage' AND p_sort_direction = 'asc' THEN profit_percentage END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'profit_percentage' AND p_sort_direction = 'desc' THEN profit_percentage END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'ref_profit_amount' AND p_sort_direction = 'asc' THEN ref_profit_amount END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'ref_profit_amount' AND p_sort_direction = 'desc' THEN ref_profit_amount END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'ref_profit_percentage' AND p_sort_direction = 'asc' THEN ref_profit_percentage END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'ref_profit_percentage' AND p_sort_direction = 'desc' THEN ref_profit_percentage END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'id' OR p_sort_by IS NULL THEN id END DESC NULLS LAST
        LIMIT p_page_size OFFSET v_offset
    )
    SELECT jsonb_build_object(
        'data', COALESCE(jsonb_agg(
            jsonb_build_object(
                'id', d.id,
                'global_code', d.global_code,
                'name', d.website_product_name,
                'description', d.description,
                'sku', COALESCE(d.website_product_sku, d.sku),
                'product_type', d.product_type,
                'visibility', d.visibility,
                'sellable', d.sellable,
                'base_image_url', COALESCE(d.website_base_image_url, d.base_image_url),
                'attribute_data', d.attribute_data,
                'meta_data', d.meta_data,
                'is_active', d.is_active,
                'brand', CASE 
                    WHEN d.brand_id IS NOT NULL THEN jsonb_build_object('id', d.brand_id, 'name', d.brand_name)
                    ELSE NULL 
                END,
                'price_data', jsonb_build_object(
                    'profit_amount', d.profit_amount,
                    'profit_percentage', d.profit_percentage,
                    'reference_prices', d.enhanced_reference_prices,
                    'updated_at', d.price_updated_at,
                    'min_price_store', CASE 
                        WHEN d.min_price_store_id IS NOT NULL THEN jsonb_build_object(
                            'id', d.min_price_store_id,
                            'name', d.min_price_store_name,
                            'price_usd', d.min_price_usd,
                            'website', jsonb_build_object(
                                'id', d.min_price_website_id,
                                'name', d.min_price_website_name,
                                'url', d.min_price_website_url,
                                'logo_url', d.min_price_website_logo
                            )
                        ) ELSE NULL 
                    END,
                    'max_price_store', CASE 
                        WHEN d.max_price_store_id IS NOT NULL THEN jsonb_build_object(
                            'id', d.max_price_store_id,
                            'name', d.max_price_store_name,
                            'price_usd', d.max_price_usd,
                            'website', jsonb_build_object(
                                'id', d.max_price_website_id,
                                'name', d.max_price_website_name,
                                'url', d.max_price_website_url,
                                'logo_url', d.max_price_website_logo
                            )
                        ) ELSE NULL 
                    END
                ),
                'created_at', d.created_at,
                'updated_at', d.updated_at
            )
        ), '[]'::jsonb),
        'pagination', jsonb_build_object(
            'total_count', (SELECT total_count FROM total_cte),
            'page_size', p_page_size,
            'page', p_page,
            'total_pages', CEIL((SELECT total_count FROM total_cte)::float / p_page_size)::INTEGER
        ),
        'sorting', jsonb_build_object(
            'fields', ARRAY[
                'id', 'name', 'global_code',
                'min_price', 'max_price',
                'profit_amount', 'profit_percentage',
                'ref_profit_amount', 'ref_profit_percentage'
            ],
            'directions', ARRAY['asc', 'desc']
        )
    )
    INTO v_result
    FROM data_cte d;

    RETURN v_result;
END;
$$;


-- Example usage
-- SELECT *
-- FROM public.get_products_with_relations(
--     p_ref_min_profit_percentage := 50,
--     p_sort_by := 'ref_profit_amount',
--     p_sort_direction := 'desc',
--     p_page := 1,
--     p_page_size := 10
-- );
