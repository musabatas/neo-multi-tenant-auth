create or replace function public.get_product_full_details_json(p_product_id bigint, p_in_stock_only boolean DEFAULT false, p_website_id integer DEFAULT NULL::integer, p_sort_by text DEFAULT 'price_asc'::text, p_limit integer DEFAULT 50, p_offset integer DEFAULT 0) returns jsonb
    language plpgsql
as
$$
DECLARE
    result jsonb;
BEGIN
    WITH base AS (
        SELECT
            -- Product core
            p.id AS product_id,
            p.global_code,
            p.brand_id,
            -- Remove direct parent_id reference, will be handled via relationships
            p.name AS product_name,
            p.description AS product_description,
            p.sku AS product_sku,
            p.product_type,
            p.visibility,
            p.sellable,
            p.base_image_url AS product_base_image_url,
            p.attribute_data AS product_attribute_data,
            p.meta_data AS product_meta_data,
            p.crawler_meta AS product_crawler_meta,
            p.is_deleted AS product_is_deleted,
            p.is_active AS product_is_active,
            p.created_at AS product_created_at,
            p.updated_at AS product_updated_at,
            p.deleted_at AS product_deleted_at,

            -- Product store
            ps.id AS product_store_id,
            ps.website_id AS store_website_id,
            ps.store_id,
            ps.store_url,
            ps.query_params,
            ps.url_type,
            ps.is_active AS product_store_is_active,
            ps.display_order,
            ps.meta_data AS product_store_meta_data,
            ps.created_at AS product_store_created_at,
            ps.updated_at AS product_store_updated_at,

            -- Website details
            pwd.name AS website_product_name,
            pwd.sku AS website_product_sku,
            pwd.base_image_url AS website_base_image_url,
            pwd.default_url AS website_default_url,
            pwd.url_type AS website_url_type,
            pwd.is_active AS website_product_is_active,
            pwd.sellable AS website_product_sellable,
            pwd.attribute_data AS website_attribute_data,
            pwd.meta_data AS website_meta_data,
            pwd.crawler_meta AS website_crawler_meta,
            pwd.seo_data AS website_seo_data,
            pwd.created_at AS website_product_created_at,
            pwd.updated_at AS website_product_updated_at,

            -- Store
            s.name AS store_name,
            s.code AS store_code,
            s.api_code AS store_api_code,
            s.phone AS store_phone,
            s.default_currency_code AS store_currency,
            s.is_active AS store_is_active,
            s.is_default AS store_is_default,
            s.is_reference_store AS store_is_reference,
            s.reference_priority AS store_reference_priority,
            s.meta_data AS store_meta_data,
            s.crawler_meta AS store_crawler_meta,

            -- Website
            w.name AS website_name,
            w.description AS website_description,
            w.url AS website_url,
            w.code AS website_code,
            w.logo_url AS website_logo_url,
            w.meta_data AS website_store_meta_data,
            w.crawler_meta AS website_store_crawler_meta,
            w.default_currency_code AS website_currency,

            -- Brand
            b.name AS brand_name,
            b.description AS brand_description,
            b.slug AS brand_slug,
            b.image_url AS brand_image_url,
            b.website_url AS brand_website_url,
            b.is_active AS brand_is_active,

            -- Vendor
            v.name AS vendor_name,
            v.country_code AS vendor_country,
            v.website_url AS vendor_website_url,
            v.logo_url AS vendor_logo_url,
            v.is_active AS vendor_is_active,

            -- Price
            psp.regular_price,
            psp.sale_price,
            psp.price AS effective_price,
            psp.currency_code AS price_currency,
            psp.meta_data AS price_meta_data,
            psp.updated_at AS price_updated_at,

            -- Inventory
            psi.stock_qty,
            psi.stock_status,
            psi.manage_stock,
            psi.meta_data AS inventory_meta_data,
            psi.updated_at AS inventory_updated_at,

            -- Parent product via relationships
            parent_rel.parent_product_id,
            parent.name AS parent_name,
            parent.global_code AS parent_global_code,
            parent.sku AS parent_sku,
            parent.product_type AS parent_product_type
            
        FROM products p
        LEFT JOIN product_stores ps ON ps.product_id = p.id
        LEFT JOIN product_website_details pwd ON pwd.product_id = p.id AND pwd.website_id = ps.website_id
        LEFT JOIN stores s ON s.id = ps.store_id
        LEFT JOIN websites w ON w.id = ps.website_id
        LEFT JOIN brands b ON b.id = p.brand_id
        LEFT JOIN vendors v ON v.id = w.vendor_id
        LEFT JOIN product_store_prices psp ON psp.product_store_id = ps.id
        LEFT JOIN product_store_inventory psi ON psi.product_store_id = ps.id
        -- Add parent relationship lookup
        LEFT JOIN product_relationships parent_rel ON parent_rel.child_product_id = p.id 
          AND parent_rel.relationship_type = 'variant' 
          AND parent_rel.website_id = 0
        LEFT JOIN products parent ON parent.id = parent_rel.parent_product_id
        
        WHERE p.id = p_product_id
          AND p.deleted_at IS NULL
          AND p.is_deleted = false
          AND (p_website_id IS NULL OR ps.website_id = p_website_id)
          AND (NOT p_in_stock_only OR psi.stock_status = 'in_stock')
          AND (ps.id IS NULL OR ps.is_active = true)
          AND (s.id IS NULL OR (s.is_active = true AND s.deleted_at IS NULL AND s.is_deleted = false))
          AND (w.id IS NULL OR (w.is_active = true AND w.deleted_at IS NULL AND w.is_deleted = false))
        
        -- Dynamic sorting
        ORDER BY 
          CASE 
            WHEN p_sort_by = 'price_asc' THEN psp.price
            WHEN p_sort_by = 'price_desc' THEN -psp.price
            WHEN p_sort_by = 'store_name_asc' THEN NULL
            WHEN p_sort_by = 'store_name_desc' THEN NULL
            WHEN p_sort_by = 'website_name_asc' THEN NULL
            WHEN p_sort_by = 'website_name_desc' THEN NULL
            ELSE NULL
          END ASC NULLS LAST,
          CASE 
            WHEN p_sort_by = 'store_name_asc' THEN s.name
            WHEN p_sort_by = 'website_name_asc' THEN w.name
            ELSE NULL
          END ASC NULLS LAST,
          CASE 
            WHEN p_sort_by = 'store_name_desc' THEN s.name
            WHEN p_sort_by = 'website_name_desc' THEN w.name
            ELSE NULL
          END DESC NULLS LAST,
          ps.display_order ASC,
          ps.id ASC
        
        LIMIT p_limit OFFSET p_offset
    )
    
    SELECT jsonb_build_object(
        'product', jsonb_build_object(
            'id', base.product_id,
            'global_code', base.global_code,
            'brand_id', base.brand_id,
            'name', base.product_name,
            'description', base.product_description,
            'sku', base.product_sku,
            'product_type', base.product_type,
            'visibility', base.visibility,
            'sellable', base.sellable,
            'base_image_url', base.product_base_image_url,
            'attribute_data', base.product_attribute_data,
            'meta_data', base.product_meta_data,
            'crawler_meta', base.product_crawler_meta,
            'is_deleted', base.product_is_deleted,
            'is_active', base.product_is_active,
            'created_at', base.product_created_at,
            'updated_at', base.product_updated_at,
            'deleted_at', base.product_deleted_at,
            -- Replace parent_id with parent relationship data
            'parent', CASE WHEN base.parent_product_id IS NOT NULL THEN jsonb_build_object(
                'id', base.parent_product_id,
                'name', base.parent_name,
                'global_code', base.parent_global_code,
                'sku', base.parent_sku,
                'product_type', base.parent_product_type
            ) END,
            'brand', CASE WHEN base.brand_name IS NOT NULL THEN jsonb_build_object(
                'id', base.brand_id,
                'name', base.brand_name,
                'description', base.brand_description,
                'slug', base.brand_slug,
                'image_url', base.brand_image_url,
                'website_url', base.brand_website_url,
                'is_active', base.brand_is_active
            ) END
        ),
        'stores', COALESCE((
            SELECT jsonb_agg(
                jsonb_build_object(
                    'product_store_id', base.product_store_id,
                    'store_url', base.store_url,
                    'query_params', base.query_params,
                    'url_type', base.url_type,
                    'is_active', base.product_store_is_active,
                    'display_order', base.display_order,
                    'meta_data', base.product_store_meta_data,
                    'created_at', base.product_store_created_at,
                    'updated_at', base.product_store_updated_at,
                    'website_details', CASE WHEN base.website_product_name IS NOT NULL THEN jsonb_build_object(
                        'name', base.website_product_name,
                        'sku', base.website_product_sku,
                        'base_image_url', base.website_base_image_url,
                        'default_url', base.website_default_url,
                        'url_type', base.website_url_type,
                        'is_active', base.website_product_is_active,
                        'sellable', base.website_product_sellable,
                        'attribute_data', base.website_attribute_data,
                        'meta_data', base.website_meta_data,
                        'crawler_meta', base.website_crawler_meta,
                        'seo_data', base.website_seo_data,
                        'created_at', base.website_product_created_at,
                        'updated_at', base.website_product_updated_at
                    ) END,
                    'store', CASE WHEN base.store_name IS NOT NULL THEN jsonb_build_object(
                        'id', base.store_id,
                        'name', base.store_name,
                        'code', base.store_code,
                        'api_code', base.store_api_code,
                        'phone', base.store_phone,
                        'default_currency_code', base.store_currency,
                        'is_active', base.store_is_active,
                        'is_default', base.store_is_default,
                        'is_reference_store', base.store_is_reference,
                        'reference_priority', base.store_reference_priority,
                        'meta_data', base.store_meta_data,
                        'crawler_meta', base.store_crawler_meta
                    ) END,
                    'website', CASE WHEN base.website_name IS NOT NULL THEN jsonb_build_object(
                        'id', base.store_website_id,
                        'name', base.website_name,
                        'description', base.website_description,
                        'url', base.website_url,
                        'code', base.website_code,
                        'logo_url', base.website_logo_url,
                        'meta_data', base.website_store_meta_data,
                        'crawler_meta', base.website_store_crawler_meta,
                        'default_currency_code', base.website_currency,
                        'vendor', CASE WHEN base.vendor_name IS NOT NULL THEN jsonb_build_object(
                            'name', base.vendor_name,
                            'country_code', base.vendor_country,
                            'website_url', base.vendor_website_url,
                            'logo_url', base.vendor_logo_url,
                            'is_active', base.vendor_is_active
                        ) END
                    ) END,
                    'price', CASE WHEN base.regular_price IS NOT NULL THEN jsonb_build_object(
                        'regular_price', base.regular_price,
                        'sale_price', base.sale_price,
                        'effective_price', base.effective_price,
                        'currency_code', base.price_currency,
                        'meta_data', base.price_meta_data,
                        'updated_at', base.price_updated_at
                    ) END,
                    'inventory', CASE WHEN base.stock_status IS NOT NULL THEN jsonb_build_object(
                        'stock_qty', base.stock_qty,
                        'stock_status', base.stock_status,
                        'manage_stock', base.manage_stock,
                        'meta_data', base.inventory_meta_data,
                        'updated_at', base.inventory_updated_at
                    ) END
                )
                ORDER BY base.display_order ASC, base.product_store_id ASC
            )
            FROM base
            WHERE base.product_store_id IS NOT NULL
        ), '[]'::jsonb)
    ) INTO result
    FROM base
    LIMIT 1;

    RETURN COALESCE(result, jsonb_build_object('product', NULL, 'stores', '[]'));
END;
$$;

comment on function public.get_product_full_details_json(bigint, boolean, integer, text, integer, integer) is 'Returns comprehensive product details with stores, using product_relationships instead of parent_id';


create or replace function get_latest_store_changes_json(p_product_id bigint, p_from_date timestamp with time zone DEFAULT NULL::timestamp with time zone, p_to_date timestamp with time zone DEFAULT NULL::timestamp with time zone, p_sort_by text DEFAULT 'inventory_changed_at_desc'::text, p_limit integer DEFAULT 50, p_offset integer DEFAULT 0) returns jsonb
    language plpgsql
as
$$
DECLARE
    result jsonb;
BEGIN
    WITH changes_cte AS (
        SELECT
            ps.id AS product_store_id,
            ps.product_id,
            s.name AS store_name,
            w.name AS website_name,

            -- Inventory
            li.previous_stock_qty,
            li.new_stock_qty,
            li.previous_stock_status,
            li.new_stock_status,
            li.previous_manage_stock,
            li.new_manage_stock,
            li.change_type,
            li.date_changed AS inventory_changed_at,

            -- Price
            lp.currency_code,
            lp.previous_regular_price,
            lp.new_regular_price,
            lp.previous_sale_price,
            lp.new_sale_price,
            lp.previous_effective_price,
            lp.new_effective_price,
            lp.date_changed AS price_changed_at

        FROM product_stores ps
        LEFT JOIN LATERAL (
            SELECT *
            FROM inventory_history ih
            WHERE ih.product_store_id = ps.id
            ORDER BY ih.date_changed DESC
            LIMIT 1
        ) li ON true

        LEFT JOIN LATERAL (
            SELECT *
            FROM price_history ph
            WHERE ph.product_store_id = ps.id
            ORDER BY ph.date_changed DESC
            LIMIT 1
        ) lp ON true

        LEFT JOIN stores s ON s.id = ps.store_id
        LEFT JOIN websites w ON w.id = ps.website_id

        WHERE ps.product_id = p_product_id
          AND ps.is_active = true
          AND (
              p_from_date IS NULL
              OR (
                  (li.date_changed IS NOT NULL AND li.date_changed >= p_from_date)
                  OR (lp.date_changed IS NOT NULL AND lp.date_changed >= p_from_date)
              )
          )
          AND (
              p_to_date IS NULL
              OR (
                  (li.date_changed IS NOT NULL AND li.date_changed <= p_to_date)
                  OR (lp.date_changed IS NOT NULL AND lp.date_changed <= p_to_date)
              )
          )
    ),
    total_cte AS (
        SELECT COUNT(*) AS total_count FROM changes_cte
    ),
    data_cte AS (
        SELECT * FROM changes_cte
        ORDER BY
            CASE WHEN p_sort_by = 'inventory_changed_at_asc' THEN inventory_changed_at END ASC,
            CASE WHEN p_sort_by = 'inventory_changed_at_desc' THEN inventory_changed_at END DESC,
            CASE WHEN p_sort_by = 'price_changed_at_asc' THEN price_changed_at END ASC,
            CASE WHEN p_sort_by = 'price_changed_at_desc' THEN price_changed_at END DESC,
            CASE WHEN p_sort_by = 'store_name_asc' THEN store_name END ASC,
            CASE WHEN p_sort_by = 'store_name_desc' THEN store_name END DESC,
            CASE WHEN p_sort_by = 'website_name_asc' THEN website_name END ASC,
            CASE WHEN p_sort_by = 'website_name_desc' THEN website_name END DESC
        LIMIT p_limit OFFSET p_offset
    )
    SELECT jsonb_build_object(
        'total_count', (SELECT total_count FROM total_cte),
        'data', COALESCE(jsonb_agg(to_jsonb(data_cte)), '[]'::jsonb)
    )
    INTO result
    FROM data_cte;

    RETURN result;
END;
$$;

create or replace function public.get_latest_store_changes_json(p_product_id bigint, p_from_date timestamp with time zone DEFAULT NULL::timestamp with time zone, p_to_date timestamp with time zone DEFAULT NULL::timestamp with time zone, p_sort_by text DEFAULT 'inventory_changed_at_desc'::text, p_limit integer DEFAULT 50, p_offset integer DEFAULT 0) returns jsonb
    language plpgsql
as
$$
DECLARE
    result jsonb;
BEGIN
    WITH changes_cte AS (
        SELECT
            ps.id AS product_store_id,
            ps.product_id,
            s.name AS store_name,
            w.name AS website_name,

            -- Inventory
            li.previous_stock_qty,
            li.new_stock_qty,
            li.previous_stock_status,
            li.new_stock_status,
            li.previous_manage_stock,
            li.new_manage_stock,
            li.change_type,
            li.date_changed AS inventory_changed_at,

            -- Price
            lp.currency_code,
            lp.previous_regular_price,
            lp.new_regular_price,
            lp.previous_sale_price,
            lp.new_sale_price,
            lp.previous_effective_price,
            lp.new_effective_price,
            lp.date_changed AS price_changed_at

        FROM product_stores ps
        LEFT JOIN LATERAL (
            SELECT *
            FROM inventory_history ih
            WHERE ih.product_store_id = ps.id
            ORDER BY ih.date_changed DESC
            LIMIT 1
        ) li ON true

        LEFT JOIN LATERAL (
            SELECT *
            FROM price_history ph
            WHERE ph.product_store_id = ps.id
            ORDER BY ph.date_changed DESC
            LIMIT 1
        ) lp ON true

        LEFT JOIN stores s ON s.id = ps.store_id
        LEFT JOIN websites w ON w.id = ps.website_id

        WHERE ps.product_id = p_product_id
          AND ps.is_active = true
          AND (
              p_from_date IS NULL
              OR (
                  (li.date_changed IS NOT NULL AND li.date_changed >= p_from_date)
                  OR (lp.date_changed IS NOT NULL AND lp.date_changed >= p_from_date)
              )
          )
          AND (
              p_to_date IS NULL
              OR (
                  (li.date_changed IS NOT NULL AND li.date_changed <= p_to_date)
                  OR (lp.date_changed IS NOT NULL AND lp.date_changed <= p_to_date)
              )
          )
    ),
    total_cte AS (
        SELECT COUNT(*) AS total_count FROM changes_cte
    ),
    data_cte AS (
        SELECT * FROM changes_cte
        ORDER BY
            CASE WHEN p_sort_by = 'inventory_changed_at_asc' THEN inventory_changed_at END ASC,
            CASE WHEN p_sort_by = 'inventory_changed_at_desc' THEN inventory_changed_at END DESC,
            CASE WHEN p_sort_by = 'price_changed_at_asc' THEN price_changed_at END ASC,
            CASE WHEN p_sort_by = 'price_changed_at_desc' THEN price_changed_at END DESC,
            CASE WHEN p_sort_by = 'store_name_asc' THEN store_name END ASC,
            CASE WHEN p_sort_by = 'store_name_desc' THEN store_name END DESC,
            CASE WHEN p_sort_by = 'website_name_asc' THEN website_name END ASC,
            CASE WHEN p_sort_by = 'website_name_desc' THEN website_name END DESC
        LIMIT p_limit OFFSET p_offset
    )
    SELECT jsonb_build_object(
        'total_count', (SELECT total_count FROM total_cte),
        'data', COALESCE(jsonb_agg(to_jsonb(data_cte)), '[]'::jsonb)
    )
    INTO result
    FROM data_cte;

    RETURN result;
END;
$$;



create or replace function public.get_product_market_overview_json(p_product_id bigint) returns jsonb
    language plpgsql
as
$$
DECLARE
    result jsonb;
BEGIN
    SELECT jsonb_build_object(
        'store_count', COUNT(*),
        'avg_usd_price', ROUND(AVG(psp.price / c.exchange_rate), 2),
        'min_usd_price', ROUND(MIN(psp.price / c.exchange_rate), 2),
        'max_usd_price', ROUND(MAX(psp.price / c.exchange_rate), 2),
        'price_spread_percent', ROUND(
            CASE 
                WHEN MIN(psp.price / c.exchange_rate) > 0 
                THEN ((MAX(psp.price / c.exchange_rate) - MIN(psp.price / c.exchange_rate)) / MIN(psp.price / c.exchange_rate)) * 100
                ELSE 0
            END, 2
        ),
        'budget_store_count', COUNT(*) FILTER (WHERE psp.price / c.exchange_rate < 0.33),
        'mid_range_store_count', COUNT(*) FILTER (WHERE psp.price / c.exchange_rate BETWEEN 0.33 AND 0.66),
        'premium_store_count', COUNT(*) FILTER (WHERE psp.price / c.exchange_rate > 0.66)
    )
    INTO result
    FROM product_store_prices psp
    JOIN product_stores ps ON ps.id = psp.product_store_id AND ps.is_active = true
    JOIN currencies c ON c.code = psp.currency_code AND c.is_active = true
    WHERE ps.product_id = p_product_id;

    RETURN COALESCE(result, jsonb_build_object(
        'store_count', 0,
        'avg_usd_price', NULL,
        'min_usd_price', NULL,
        'max_usd_price', NULL,
        'price_spread_percent', NULL,
        'budget_store_count', 0,
        'mid_range_store_count', 0,
        'premium_store_count', 0
    ));
END;
$$;

create or replace function public.get_product_store_history_json(p_product_id bigint, p_store_id integer, p_from_date timestamp with time zone DEFAULT (now() - '30 days'::interval), p_to_date timestamp with time zone DEFAULT now()) returns jsonb
    language plpgsql
as
$$
DECLARE
    result jsonb;
BEGIN
    SELECT jsonb_build_object(
        'inventory', COALESCE(jsonb_agg(
            jsonb_build_object(
                'd', ih.date_changed,
                'x', ih.previous_stock_qty,
                'y', ih.new_stock_qty
            )
            ORDER BY ih.date_changed
        ), '[]'::jsonb),
        
        'price', COALESCE(jsonb_agg(
            jsonb_build_object(
                'd', ph.date_changed,
                'x', ph.previous_effective_price,
                'y', ph.new_effective_price
            )
            ORDER BY ph.date_changed
        ), '[]'::jsonb)
    )
    INTO result
    FROM product_stores ps
    LEFT JOIN inventory_history ih ON ih.product_store_id = ps.id
        AND ih.date_changed BETWEEN p_from_date AND p_to_date
    LEFT JOIN price_history ph ON ph.product_store_id = ps.id
        AND ph.date_changed BETWEEN p_from_date AND p_to_date
    WHERE ps.product_id = p_product_id
      AND ps.store_id = p_store_id
      AND ps.is_active = true;

    RETURN COALESCE(result, jsonb_build_object('inventory', '[]', 'price', '[]'));
END;
$$;

create or replace function public.get_opportunity_product_json(p_opportunity_id bigint) returns jsonb
    language plpgsql
as
$$
BEGIN
    RETURN (
        SELECT jsonb_build_object(
          'id', oh.id,
          'rule', jsonb_build_object(
            'id', oru.id,
            'name', oru.name,
            'description', oru.description,
            'rule_type', oru.rule_type,
            'status', oru.status
          ),
          'product', jsonb_build_object(
            'id', p.id,
            'global_code', p.global_code,
            'brand_id', p.brand_id,
            'name', p.name,
            'description', p.description,
            'sku', p.sku,
            'product_type', p.product_type,
            'visibility', p.visibility,
            'sellable', p.sellable,
            'base_image_url', p.base_image_url,
            'attribute_data', p.attribute_data,
            'meta_data', p.meta_data,
            'crawler_meta', p.crawler_meta,
            'is_deleted', p.is_deleted,
            'is_active', p.is_active,
            'created_at', p.created_at,
            'updated_at', p.updated_at,
            'deleted_at', p.deleted_at,
            'brand', CASE WHEN b.id IS NOT NULL THEN jsonb_build_object(
              'id', b.id,
              'name', b.name,
              'slug', b.slug,
              'description', b.description,
              'image_url', b.image_url,
              'website_url', b.website_url,
              'is_active', b.is_active
            ) END,
            -- Replace parent_id with parent relationship lookup
            'parent', CASE WHEN parent_rel.parent_product_id IS NOT NULL THEN jsonb_build_object(
              'id', parent.id,
              'name', parent.name,
              'global_code', parent.global_code,
              'sku', parent.sku,
              'product_type', parent.product_type
            ) END
          ),
          'opportunity_details', jsonb_build_object(
            'source_store', jsonb_build_object(
              'id', ss.id,
              'name', ss.name,
              'code', ss.code,
              'api_code', ss.api_code,
              'website', jsonb_build_object(
                'id', sw.id,
                'name', sw.name,
                'url', sw.url
              )
            ),
            'target_store', jsonb_build_object(
              'id', max_store.id,
              'name', max_store.name,
              'code', max_store.code,
              'api_code', max_store.api_code,
              'website', jsonb_build_object(
                'id', max_web.id,
                'name', max_web.name,
                'url', max_web.url
              )
            ),
            'source_price', oh.source_price,
            'target_price', oh.target_price,
            'price_difference', oh.price_difference,
            'difference_percentage', oh.difference_percentage,
            'currency_code', oh.currency_code,
            'min_price_usd', ppa.min_price_usd,
            'max_price_usd', ppa.max_price_usd,
            'profit_amount', ppa.profit_amount,
            'profit_percentage', ppa.profit_percentage,
            'reference_prices', COALESCE((
              SELECT jsonb_agg(
                jsonb_build_object(
                  'store', jsonb_build_object(
                    'id', rs.id,
                    'name', rs.name,
                    'code', rs.code,
                    'api_code', rs.api_code,
                    'min_price_usd', rs_pa.min_price_usd,
                    'max_price_usd', rs_pa.max_price_usd,
                    'website', jsonb_build_object(
                      'id', rw.id,
                      'name', rw.name,
                      'url', rw.url
                    )
                  ),
                  'price_usd', rp->>'price_usd',
                  'profit_amount', rp->>'profit_amount',
                  'profit_percentage', rp->>'profit_percentage'
                )
              )
              FROM jsonb_array_elements(ppa.reference_prices) rp
              LEFT JOIN stores rs ON rs.id = (rp->>'store_id')::int
              LEFT JOIN websites rw ON rw.id = rs.website_id
              LEFT JOIN product_price_aggregates rs_pa ON rs_pa.product_id = p.id
            ), '[]'::jsonb)
          ),
          'created_at', oh.created_at,
          'updated_at', oh.updated_at
        )
        FROM opportunity_history oh
        JOIN opportunity_rules oru ON oru.id = oh.rule_id
        JOIN products p ON p.id = oh.product_id
        -- Replace parent_id JOIN with product_relationships lookup
        LEFT JOIN product_relationships parent_rel ON parent_rel.child_product_id = p.id 
          AND parent_rel.relationship_type = 'variant' 
          AND parent_rel.website_id = 0
        LEFT JOIN products parent ON parent.id = parent_rel.parent_product_id
        LEFT JOIN brands b ON b.id = p.brand_id
        LEFT JOIN stores ss ON ss.id = oh.source_store_id
        LEFT JOIN websites sw ON sw.id = ss.website_id
        LEFT JOIN product_price_aggregates ppa ON ppa.product_id = p.id
        LEFT JOIN stores min_store ON min_store.id = ppa.min_price_store_id
        LEFT JOIN stores max_store ON max_store.id = ppa.max_price_store_id
        LEFT JOIN websites min_web ON min_web.id = min_store.website_id
        LEFT JOIN websites max_web ON max_web.id = max_store.website_id
        WHERE oh.id = p_opportunity_id
    );
END;
$$;

comment on function public.get_opportunity_product_json(bigint) is 'Returns detailed opportunity product data as JSON, using product_relationships instead of parent_id';


create or replace function public.get_store_states()
    returns TABLE(state character varying, store_count bigint)
    language plpgsql
as
$$
BEGIN
    RETURN QUERY
    SELECT DISTINCT a.state, COUNT(s.id)::bigint as store_count
    FROM addresses a
    JOIN stores s ON s.address_id = a.id
    WHERE s.is_deleted = false 
    AND s.is_active = true
    AND a.state IS NOT NULL
    GROUP BY a.state
    ORDER BY store_count DESC;
END;
$$;

create or replace function public.get_opportunity_products_json(p_rule_id bigint DEFAULT NULL::bigint, p_brand_ids integer[] DEFAULT NULL::integer[], p_website_ids integer[] DEFAULT NULL::integer[], p_store_ids integer[] DEFAULT NULL::integer[], p_states character varying[] DEFAULT NULL::character varying[], p_min_diff_percent numeric DEFAULT NULL::numeric, p_max_diff_percent numeric DEFAULT NULL::numeric, p_min_diff_amount numeric DEFAULT NULL::numeric, p_max_diff_amount numeric DEFAULT NULL::numeric, p_created_from timestamp with time zone DEFAULT NULL::timestamp with time zone, p_created_to timestamp with time zone DEFAULT NULL::timestamp with time zone, p_sort_by text DEFAULT 'updated_at_desc'::text, p_limit integer DEFAULT 50, p_offset integer DEFAULT 0) returns jsonb
    language plpgsql
as
$$
DECLARE
    v_filtered_store_ids integer[];
    v_result jsonb;
BEGIN
    -- Get store IDs based on states if states are provided
    IF p_states IS NOT NULL AND array_length(p_states, 1) > 0 THEN
        SELECT array_agg(DISTINCT s.id)
        INTO v_filtered_store_ids
        FROM stores s
        JOIN addresses a ON a.id = s.address_id
        WHERE a.state = ANY(p_states)
        AND s.is_deleted = false
        AND s.is_active = true;

        -- Combine with existing store_ids filter if it exists
        IF p_store_ids IS NOT NULL AND array_length(p_store_ids, 1) > 0 THEN
            v_filtered_store_ids := array(
                SELECT unnest(v_filtered_store_ids)
                INTERSECT
                SELECT unnest(p_store_ids)
            );
        END IF;
    ELSE
        v_filtered_store_ids := p_store_ids;
    END IF;

    WITH filtered_opportunities AS (
        SELECT oh.*
        FROM opportunity_history oh
        JOIN products p ON p.id = oh.product_id
        LEFT JOIN brands b ON b.id = p.brand_id
        LEFT JOIN stores ss ON ss.id = oh.source_store_id
        LEFT JOIN stores ts ON ts.id = oh.target_store_id
        WHERE (
            p_rule_id IS NULL OR oh.rule_id = p_rule_id
        )
        AND (
            p_brand_ids IS NULL OR p.brand_id = ANY(p_brand_ids)
        )
        AND (
            p_website_ids IS NULL OR ss.website_id = ANY(p_website_ids) OR ts.website_id = ANY(p_website_ids)
        )
        AND (
            v_filtered_store_ids IS NULL OR 
            oh.source_store_id = ANY(v_filtered_store_ids) OR 
            oh.target_store_id = ANY(v_filtered_store_ids)
        )
        AND (
            p_min_diff_percent IS NULL OR oh.difference_percentage >= p_min_diff_percent
        )
        AND (
            p_max_diff_percent IS NULL OR oh.difference_percentage <= p_max_diff_percent
        )
        AND (
            p_min_diff_amount IS NULL OR oh.price_difference >= p_min_diff_amount
        )
        AND (
            p_max_diff_amount IS NULL OR oh.price_difference <= p_max_diff_amount
        )
        AND (
            p_created_from IS NULL OR oh.created_at >= p_created_from
        )
        AND (
            p_created_to IS NULL OR oh.created_at <= p_created_to
        )
        ORDER BY
            CASE WHEN p_sort_by = 'updated_at_asc' THEN oh.updated_at END ASC,
            CASE WHEN p_sort_by = 'updated_at_desc' THEN oh.updated_at END DESC,
            CASE WHEN p_sort_by = 'price_diff_asc' THEN oh.price_difference END ASC,
            CASE WHEN p_sort_by = 'price_diff_desc' THEN oh.price_difference END DESC,
            CASE WHEN p_sort_by = 'diff_percent_asc' THEN oh.difference_percentage END ASC,
            CASE WHEN p_sort_by = 'diff_percent_desc' THEN oh.difference_percentage END DESC
        LIMIT p_limit OFFSET p_offset
    ),
    total_count_cte AS (
        SELECT COUNT(*) AS total_count
        FROM opportunity_history oh
        JOIN products p ON p.id = oh.product_id
        LEFT JOIN brands b ON b.id = p.brand_id
        LEFT JOIN stores ss ON ss.id = oh.source_store_id
        LEFT JOIN stores ts ON ts.id = oh.target_store_id
        WHERE (
            p_rule_id IS NULL OR oh.rule_id = p_rule_id
        )
        AND (
            p_brand_ids IS NULL OR p.brand_id = ANY(p_brand_ids)
        )
        AND (
            p_website_ids IS NULL OR ss.website_id = ANY(p_website_ids) OR ts.website_id = ANY(p_website_ids)
        )
        AND (
            v_filtered_store_ids IS NULL OR 
            oh.source_store_id = ANY(v_filtered_store_ids) OR 
            oh.target_store_id = ANY(v_filtered_store_ids)
        )
        AND (
            p_min_diff_percent IS NULL OR oh.difference_percentage >= p_min_diff_percent
        )
        AND (
            p_max_diff_percent IS NULL OR oh.difference_percentage <= p_max_diff_percent
        )
        AND (
            p_min_diff_amount IS NULL OR oh.price_difference >= p_min_diff_amount
        )
        AND (
            p_max_diff_amount IS NULL OR oh.price_difference <= p_max_diff_amount
        )
        AND (
            p_created_from IS NULL OR oh.created_at >= p_created_from
        )
        AND (
            p_created_to IS NULL OR oh.created_at <= p_created_to
        )
    )

    SELECT jsonb_build_object(
        'total_count', (SELECT total_count FROM total_count_cte),
        'data', jsonb_agg(op_data.result)
    )
    INTO v_result
    FROM (
        SELECT get_opportunity_product_json(oh.id) AS result
        FROM filtered_opportunities oh
    ) op_data;

    RETURN COALESCE(v_result, jsonb_build_object('total_count', 0, 'data', '[]'));
END;
$$;



