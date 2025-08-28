DROP FUNCTION IF EXISTS public.get_products_basic_info_json(integer, integer);

create or replace function public.get_products_basic_info_json(p_limit integer DEFAULT 50, p_offset integer DEFAULT 0, p_category_ids integer[] DEFAULT NULL::integer[]) returns jsonb
    language plpgsql
as
$$
DECLARE
    result jsonb;
    v_all_category_ids integer[];
    v_input_category_id integer;
BEGIN
    -- Prepare category filtering list
    IF p_category_ids IS NOT NULL AND array_length(p_category_ids, 1) > 0 THEN
        v_all_category_ids := '{}'::integer[];
        FOREACH v_input_category_id IN ARRAY p_category_ids
        LOOP
            SELECT array_agg(DISTINCT cat_id)
            INTO v_all_category_ids
            FROM (
                SELECT unnest(v_all_category_ids) AS cat_id
                UNION
                SELECT cat_id FROM public.get_category_and_descendants(v_input_category_id) AS cat_id
            ) AS combined_ids;
        END LOOP;
    END IF;

    WITH base AS (
        SELECT
            clr.product_id AS product_id,
            p.name AS product_name,
            p.base_image_url AS product_base_image_url,

            pwd.website_id,
            pwd.name AS website_product_name,
            pwd.default_url AS website_default_url,
            pwd.base_image_url AS website_base_image_url,

            clr.id AS crawl_result_id,
            clr.status AS crawl_result_status,
            clr.raw_data AS crawl_raw_data,

            -- Updated: Get product identifiers with their associated websites via junction table
            jsonb_agg(DISTINCT
                jsonb_build_object(
                    'identifier_type', pi.identifier_type,
                    'identifier_value', pi.identifier_value,
                    'is_primary', pi.is_primary,
                    'is_verified', pi.is_verified,
                    'websites', COALESCE(pi_websites.websites, '[]'::jsonb)
                )
            ) FILTER (WHERE pi.product_id IS NOT NULL) AS product_identifiers

        FROM collector.barcode_lookup_results clr
        JOIN public.products p ON p.id = clr.product_id
        LEFT JOIN public.product_categories pc ON pc.product_id = p.id
        LEFT JOIN public.product_website_details pwd ON pwd.product_id = p.id
        LEFT JOIN public.product_identifiers pi ON pi.product_id = p.id
        -- Updated: Join with websites via junction table
        LEFT JOIN LATERAL (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'website_id', piw.website_id,
                    'website_name', w.name,
                    'website_url', w.url
                )
            ) AS websites
            FROM product_identifier_websites piw
            LEFT JOIN websites w ON w.id = piw.website_id
            WHERE piw.product_identifier_id = pi.id
        ) pi_websites ON true

        WHERE
            p.is_deleted = FALSE
            AND p.is_active = TRUE
            AND (clr.status IS NULL OR clr.status NOT IN ('completed', 'failed'))
            AND (v_all_category_ids IS NULL OR pc.category_id = ANY(v_all_category_ids))

        GROUP BY
            clr.product_id, p.name, p.base_image_url,
            pwd.website_id, pwd.name, pwd.default_url, pwd.base_image_url,
            clr.id, clr.status, clr.raw_data

        ORDER BY clr.product_id
        LIMIT p_limit OFFSET p_offset
    ),
    -- ADDED: Calculate total count for pagination
    total_cte AS (
        SELECT COUNT(DISTINCT clr.product_id) AS total_count
        FROM collector.barcode_lookup_results clr
        JOIN public.products p ON p.id = clr.product_id
        LEFT JOIN public.product_categories pc ON pc.product_id = p.id
        WHERE
            p.is_deleted = FALSE
            AND p.is_active = TRUE
            AND (clr.status IS NULL OR clr.status NOT IN ('completed', 'failed'))
            AND (v_all_category_ids IS NULL OR pc.category_id = ANY(v_all_category_ids))
    )

    SELECT jsonb_build_object(
        'total_count', (SELECT total_count FROM total_cte),
        'data', COALESCE(jsonb_agg(
            jsonb_build_object(
                'product_id', base.product_id,
                'product_name', base.product_name,
                'product_base_image_url', base.product_base_image_url,
                'website_id', base.website_id,
                'website_product_name', base.website_product_name,
                'website_default_url', base.website_default_url,
                'website_base_image_url', base.website_base_image_url,
                'crawl_result_id', base.crawl_result_id,
                'crawl_result_status', base.crawl_result_status,
                'crawl_raw_data', base.crawl_raw_data,
                'product_identifiers', base.product_identifiers
            )
        ), '[]'::jsonb)
    ) INTO result
    FROM base;

    RETURN COALESCE(result, jsonb_build_object('total_count', 0, 'data', '[]'));
END;
$$;

comment on function public.get_products_basic_info_json(integer, integer, integer[]) is 'Fetches paginated basic product info with total count, potentially filtered by an array of category IDs (including descendants), excluding completed/failed crawl results. Returns product identifiers with their associated websites via junction table.';

