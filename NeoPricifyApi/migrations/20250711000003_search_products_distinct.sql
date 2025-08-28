-- Fix the SELECT DISTINCT ORDER BY issue in search_products function
CREATE OR REPLACE FUNCTION public.search_products(
  -- Search parameters
  p_search TEXT DEFAULT NULL,
  p_identifier_search TEXT DEFAULT NULL,
  p_identifier_types identifier_type[] DEFAULT NULL,
  
  -- Entity filters
  p_website_ids INTEGER[] DEFAULT NULL,
  p_store_ids INTEGER[] DEFAULT NULL,
  p_brand_ids INTEGER[] DEFAULT NULL,
  p_vendor_ids INTEGER[] DEFAULT NULL,
  p_category_ids INTEGER[] DEFAULT NULL,
  
  -- Product filters  
  p_product_types product_type[] DEFAULT NULL,
  p_visibility product_visibility[] DEFAULT NULL,
  p_product_ids BIGINT[] DEFAULT NULL,
  
  -- Price filters
  p_min_price DECIMAL DEFAULT NULL,
  p_max_price DECIMAL DEFAULT NULL,
  p_currency_code CHAR(3) DEFAULT 'USD',
  
  -- Status filters
  p_is_active BOOLEAN DEFAULT NULL,
  p_is_sellable BOOLEAN DEFAULT NULL,
  p_show_deleted BOOLEAN DEFAULT FALSE,
  p_in_stock_only BOOLEAN DEFAULT FALSE,
  
  -- Pagination and sorting
  p_limit INTEGER DEFAULT 25,
  p_offset INTEGER DEFAULT 0,
  p_sort_by TEXT DEFAULT 'name',
  p_sort_direction TEXT DEFAULT 'asc',
  
  -- Output options
  p_include_relationships BOOLEAN DEFAULT TRUE,
  p_include_prices BOOLEAN DEFAULT TRUE,
  p_include_inventory BOOLEAN DEFAULT FALSE
)
RETURNS TABLE(
  total_count BIGINT,
  data JSON
) 
LANGUAGE plpgsql
SECURITY definer
SET search_path = public
AS $$
DECLARE
  v_total_count BIGINT;
  v_data JSON;
  v_where_conditions TEXT[];
  v_join_conditions TEXT[];
  v_order_clause TEXT;
  v_search_query TEXT;
  v_select_order_columns TEXT;
BEGIN
  -- Build WHERE conditions array
  v_where_conditions := ARRAY['p.deleted_at IS NULL'];
  v_join_conditions := ARRAY[]::TEXT[];
  
  -- Handle deleted products filter
  IF NOT p_show_deleted THEN
    v_where_conditions := array_append(v_where_conditions, 'p.is_deleted = false');
  END IF;
  
  -- Text search across multiple fields
  IF p_search IS NOT NULL AND trim(p_search) != '' THEN
    v_where_conditions := array_append(v_where_conditions, format(
      '(p.name ILIKE ''%%%s%%'' OR p.sku ILIKE ''%%%s%%'' OR p.global_code ILIKE ''%%%s%%'' OR pwd.name ILIKE ''%%%s%%'' OR pwd.sku ILIKE ''%%%s%%'' OR b.name ILIKE ''%%%s%%'')',
      p_search, p_search, p_search, p_search, p_search, p_search
    ));
  END IF;
  
  -- Identifier search
  IF p_identifier_search IS NOT NULL AND trim(p_identifier_search) != '' THEN
    v_join_conditions := array_append(v_join_conditions, 'LEFT JOIN product_identifiers pi ON p.id = pi.product_id');
    v_where_conditions := array_append(v_where_conditions, format(
      'pi.identifier_value ILIKE ''%%%s%%''', p_identifier_search
    ));
    
    IF p_identifier_types IS NOT NULL THEN
      v_where_conditions := array_append(v_where_conditions, format(
        'pi.identifier_type = ANY(''%s'')', p_identifier_types
      ));
    END IF;
  END IF;
  
  -- Website filter
  IF p_website_ids IS NOT NULL THEN
    v_where_conditions := array_append(v_where_conditions, format(
      'pwd.website_id = ANY(ARRAY[%s])', array_to_string(p_website_ids, ',')
    ));
  END IF;
  
  -- Store filter
  IF p_store_ids IS NOT NULL THEN
    v_join_conditions := array_append(v_join_conditions, 'LEFT JOIN product_stores ps ON p.id = ps.product_id');
    v_where_conditions := array_append(v_where_conditions, format(
      'ps.store_id = ANY(ARRAY[%s])', array_to_string(p_store_ids, ',')
    ));
    v_where_conditions := array_append(v_where_conditions, 'ps.is_active = true');
  END IF;
  
  -- Brand filter
  IF p_brand_ids IS NOT NULL THEN
    v_where_conditions := array_append(v_where_conditions, format(
      'p.brand_id = ANY(ARRAY[%s])', array_to_string(p_brand_ids, ',')
    ));
  END IF;
  
  -- Vendor filter (through websites)
  IF p_vendor_ids IS NOT NULL THEN
    v_join_conditions := array_append(v_join_conditions, 'LEFT JOIN websites w ON pwd.website_id = w.id');
    v_where_conditions := array_append(v_where_conditions, format(
      'w.vendor_id = ANY(ARRAY[%s])', array_to_string(p_vendor_ids, ',')
    ));
  END IF;
  
  -- Category filter
  IF p_category_ids IS NOT NULL THEN
    v_join_conditions := array_append(v_join_conditions, 'LEFT JOIN product_categories pc ON p.id = pc.product_id');
    v_where_conditions := array_append(v_where_conditions, format(
      'pc.category_id = ANY(ARRAY[%s])', array_to_string(p_category_ids, ',')
    ));
  END IF;
  
  -- Product IDs filter
  IF p_product_ids IS NOT NULL THEN
    v_where_conditions := array_append(v_where_conditions, format(
      'p.id = ANY(ARRAY[%s])', array_to_string(p_product_ids, ',')
    ));
  END IF;
  
  -- Product type filter
  IF p_product_types IS NOT NULL THEN
    v_where_conditions := array_append(v_where_conditions, format(
      'p.product_type = ANY(''%s'')', p_product_types
    ));
  END IF;
  
  -- Visibility filter
  IF p_visibility IS NOT NULL THEN
    v_where_conditions := array_append(v_where_conditions, format(
      'p.visibility = ANY(''%s'')', p_visibility
    ));
  END IF;
  
  -- Active status filter
  IF p_is_active IS NOT NULL THEN
    v_where_conditions := array_append(v_where_conditions, format(
      'p.is_active = %s', p_is_active
    ));
  END IF;
  
  -- Sellable filter
  IF p_is_sellable IS NOT NULL THEN
    v_where_conditions := array_append(v_where_conditions, format(
      'p.sellable = %s', p_is_sellable
    ));
  END IF;
  
  -- Price filters
  IF p_min_price IS NOT NULL OR p_max_price IS NOT NULL THEN
    IF p_include_prices THEN
      v_join_conditions := array_append(v_join_conditions, 'LEFT JOIN product_price_aggregates ppa ON p.id = ppa.product_id');
      
      IF p_min_price IS NOT NULL THEN
        v_where_conditions := array_append(v_where_conditions, format(
          'ppa.min_price_usd >= %s', p_min_price
        ));
      END IF;
      
      IF p_max_price IS NOT NULL THEN
        v_where_conditions := array_append(v_where_conditions, format(
          'ppa.max_price_usd <= %s', p_max_price
        ));
      END IF;
    END IF;
  END IF;
  
  -- Stock filter
  IF p_in_stock_only THEN
    v_join_conditions := array_append(v_join_conditions, 'LEFT JOIN product_stores ps2 ON p.id = ps2.product_id');
    v_join_conditions := array_append(v_join_conditions, 'LEFT JOIN product_store_inventory psi ON ps2.id = psi.product_store_id');
    v_where_conditions := array_append(v_where_conditions, 'psi.stock_status = ''in_stock''');
  END IF;
  
  -- Build ORDER BY clause with additional columns for DISTINCT
  -- Include the order column in the SELECT to satisfy DISTINCT requirements
  v_order_clause := CASE 
    WHEN p_sort_by = 'name' THEN 'p.name'
    WHEN p_sort_by = 'id' THEN 'p.id'
    WHEN p_sort_by = 'created_at' THEN 'p.created_at'
    WHEN p_sort_by = 'updated_at' THEN 'p.updated_at'
    WHEN p_sort_by = 'global_code' THEN 'p.global_code'
    WHEN p_sort_by = 'sku' THEN 'p.sku'
    WHEN p_sort_by = 'brand' THEN 'b.name'
    WHEN p_sort_by = 'price' AND p_include_prices THEN 'ppa.min_price_usd'
    ELSE 'p.name'
  END;
  
  -- Additional columns needed for ORDER BY with DISTINCT
  v_select_order_columns := CASE 
    WHEN p_sort_by = 'name' THEN ', p.name'
    WHEN p_sort_by = 'created_at' THEN ', p.created_at'
    WHEN p_sort_by = 'updated_at' THEN ', p.updated_at'
    WHEN p_sort_by = 'global_code' THEN ', p.global_code'
    WHEN p_sort_by = 'sku' THEN ', p.sku'
    WHEN p_sort_by = 'brand' THEN ', b.name'
    WHEN p_sort_by = 'price' AND p_include_prices THEN ', ppa.min_price_usd'
    WHEN p_sort_by != 'id' THEN ', p.name'
    ELSE ''
  END;
  
  v_order_clause := v_order_clause || CASE 
    WHEN LOWER(p_sort_direction) = 'desc' THEN ' DESC'
    ELSE ' ASC'
  END;
  
  -- Get total count
  v_search_query := format('
    SELECT COUNT(DISTINCT p.id)
    FROM products p
    LEFT JOIN brands b ON p.brand_id = b.id
    LEFT JOIN product_website_details pwd ON p.id = pwd.product_id
    %s
    WHERE %s',
    CASE WHEN array_length(v_join_conditions, 1) > 0 THEN array_to_string(v_join_conditions, ' ') ELSE '' END,
    array_to_string(v_where_conditions, ' AND ')
  );
  
  EXECUTE v_search_query INTO v_total_count;
  
  -- Get paginated data with relationships
  -- Modified to include order columns in SELECT DISTINCT
  v_search_query := format('
    WITH paginated_products AS (
      SELECT DISTINCT p.id%s
      FROM products p
      LEFT JOIN brands b ON p.brand_id = b.id
      LEFT JOIN product_website_details pwd ON p.id = pwd.product_id
      %s
      WHERE %s
      ORDER BY %s
      LIMIT %s OFFSET %s
    )
    SELECT json_agg(
      json_build_object(
        ''id'', p.id,
        ''name'', p.name,
        ''sku'', p.sku,
        ''global_code'', p.global_code,
        ''product_type'', p.product_type,
        ''visibility'', p.visibility,
        ''sellable'', p.sellable,
        ''is_active'', p.is_active,
        ''base_image_url'', p.base_image_url,
        ''created_at'', p.created_at,
        ''updated_at'', p.updated_at,
        ''brand'', CASE 
          WHEN b.id IS NOT NULL THEN json_build_object(
            ''id'', b.id,
            ''name'', b.name,
            ''website_url'', b.website_url
          )
          ELSE NULL
        END%s%s%s
      )
    )
    FROM paginated_products pp
    INNER JOIN products p ON p.id = pp.id
    LEFT JOIN brands b ON p.brand_id = b.id%s',
    v_select_order_columns,
    CASE WHEN array_length(v_join_conditions, 1) > 0 THEN array_to_string(v_join_conditions, ' ') ELSE '' END,
    array_to_string(v_where_conditions, ' AND '),
    v_order_clause,
    p_limit,
    p_offset,
    CASE WHEN p_include_relationships THEN ',
        ''websites'', (
          SELECT json_agg(
            json_build_object(
              ''website_id'', pwd2.website_id,
              ''name'', pwd2.name,
              ''sku'', pwd2.sku,
              ''base_image_url'', pwd2.base_image_url,
              ''default_url'', pwd2.default_url,
              ''is_active'', pwd2.is_active,
              ''sellable'', pwd2.sellable,
              ''website'', json_build_object(
                ''id'', w2.id,
                ''name'', w2.name,
                ''url'', w2.url
              )
            )
          )
          FROM product_website_details pwd2
          LEFT JOIN websites w2 ON pwd2.website_id = w2.id
          WHERE pwd2.product_id = p.id
        ),
        ''identifiers'', (
          SELECT json_agg(
            json_build_object(
              ''identifier_type'', pi2.identifier_type,
              ''identifier_value'', pi2.identifier_value,
              ''is_primary'', pi2.is_primary,
              ''is_verified'', pi2.is_verified
            )
          )
          FROM product_identifiers pi2
          WHERE pi2.product_id = p.id
        )' ELSE '' END,
    CASE WHEN p_include_prices THEN ',
        ''price_data'', (
          SELECT row_to_json(ppa2.*)
          FROM product_price_aggregates ppa2
          WHERE ppa2.product_id = p.id
        )' ELSE '' END,
    CASE WHEN p_include_inventory THEN ',
        ''stores'', (
          SELECT json_agg(
            json_build_object(
              ''store_id'', s2.id,
              ''store_name'', s2.name,
              ''store_code'', s2.code,
              ''is_active'', ps2.is_active,
              ''stock_status'', psi2.stock_status,
              ''stock_qty'', psi2.stock_qty
            )
          )
          FROM product_stores ps2
          LEFT JOIN stores s2 ON ps2.store_id = s2.id
          LEFT JOIN product_store_inventory psi2 ON ps2.id = psi2.product_store_id
          WHERE ps2.product_id = p.id AND ps2.is_active = true
        )' ELSE '' END,
    CASE WHEN p_include_prices THEN '
    LEFT JOIN product_price_aggregates ppa2 ON p.id = ppa2.product_id' ELSE '' END
  );
  
  EXECUTE v_search_query INTO v_data;
  
  -- Return results
  RETURN QUERY
  SELECT v_total_count, COALESCE(v_data, '[]'::json);
END;
$$;

-- Add comment
COMMENT ON FUNCTION public.search_products IS 'Universal search function for products with comprehensive filtering options including text search, identifier search, entity filters, price filters, and pagination. Fixed SELECT DISTINCT ORDER BY issue.';