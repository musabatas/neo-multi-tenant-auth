-- Function to get category and descendants
create or replace function public.get_category_and_descendants(root_category_id integer) returns SETOF integer
    stable
    language sql
as
$$
    WITH RECURSIVE category_tree AS (
        -- Base case: Start with the initial root category ID
        SELECT id
        FROM public.categories
        WHERE id = root_category_id

        UNION ALL

        -- Recursive step: Find children of categories already in the tree
        SELECT c.id
        FROM public.categories c
        JOIN category_tree ct ON c.parent_id = ct.id
        -- Only follow active, non-deleted paths
        WHERE c.deleted_at IS NULL AND c.is_active = TRUE
    )
    -- Select all unique IDs found in the tree
    SELECT id FROM category_tree;
$$;

comment on function public.get_category_and_descendants(integer) is 'Returns a set containing the input category ID and all its active descendant category IDs.';

-- Function to fetch a paginated list of websites with vendor, store count, and country info
create or replace function public.get_websites_list(p_limit integer DEFAULT 25, p_offset integer DEFAULT 0, p_sort_by text DEFAULT 'id'::text, p_sort_direction text DEFAULT 'desc'::text, p_search_term text DEFAULT NULL::text, p_vendor_ids integer[] DEFAULT NULL::integer[], p_is_active boolean DEFAULT NULL::boolean, p_show_deleted boolean DEFAULT false) returns jsonb
    language plpgsql
as
$$
DECLARE
  v_sort_column text;
  v_total_count bigint;
  v_data jsonb;
BEGIN
  -- Map sort input to actual column names safely
  SELECT CASE p_sort_by
    WHEN 'name' THEN 'w.name'
    WHEN 'id' THEN 'w.id'
    WHEN 'code' THEN 'w.code'
    WHEN 'url' THEN 'w.url'
    WHEN 'created_at' THEN 'w.created_at'
    WHEN 'updated_at' THEN 'w.updated_at'
    ELSE 'w.id' -- Default sort column changed to id
  END INTO v_sort_column;

  -- Calculate total count based on filters first
  WITH base_query_for_count AS (
    SELECT w.id
    FROM websites w
    WHERE
      (p_show_deleted = true OR w.deleted_at IS NULL)
      AND (p_vendor_ids IS NULL OR w.vendor_id = ANY(p_vendor_ids))
      AND (p_is_active IS NULL OR w.is_active = p_is_active)
      AND (
        p_search_term IS NULL OR
        w.name ILIKE '%' || p_search_term || '%' OR
        w.code ILIKE '%' || p_search_term || '%' OR
        w.url ILIKE '%' || p_search_term || '%'
      )
  )
  SELECT count(*)
  INTO v_total_count
  FROM base_query_for_count;

  -- Now fetch and aggregate the paginated data
  WITH base_query_for_data AS (
    SELECT
      w.id, w.name, w.code, w.url, w.logo_url, w.description, w.vendor_id,
      w.is_active, w.is_deleted, w.meta_data, w.crawler_meta,
      w.default_currency_code, w.created_at, w.updated_at, w.deleted_at,
      v.name AS vendor_name
    FROM websites w
    LEFT JOIN vendors v ON w.vendor_id = v.id
    WHERE
      (p_show_deleted = true OR w.deleted_at IS NULL)
      AND (p_vendor_ids IS NULL OR w.vendor_id = ANY(p_vendor_ids))
      AND (p_is_active IS NULL OR w.is_active = p_is_active)
      AND (
        p_search_term IS NULL OR
        w.name ILIKE '%' || p_search_term || '%' OR
        w.code ILIKE '%' || p_search_term || '%' OR
        w.url ILIKE '%' || p_search_term || '%'
      )
  ),
  store_counts AS (
    SELECT
      s.website_id,
      count(s.id) AS store_count
    FROM stores s
    WHERE s.deleted_at IS NULL
    GROUP BY s.website_id
  ),
  spider_counts AS (
    SELECT
      ws.website_id,
      count(ws.id) AS spider_count
    FROM collector.website_spiders ws
    GROUP BY ws.website_id
  ),
  country_data AS (
    SELECT
      wc.website_id,
      COALESCE(array_agg(DISTINCT c.code ORDER BY c.code), '{}'::text[]) AS country_codes,
      COALESCE(array_agg(DISTINCT c.name || ' (' || c.code || ')' ORDER BY c.name || ' (' || c.code || ')'), '{}'::text[]) AS country_display_names
    FROM website_countries wc
    JOIN countries c ON wc.country_code = c.code
    GROUP BY wc.website_id
  ),
  paginated_data AS (
    SELECT
      bq.*,
      COALESCE(sc.store_count, 0) AS store_count,
      COALESCE(spc.spider_count, 0) AS spider_count,
      COALESCE(cd.country_codes, '{}'::text[]) AS country_codes,
      COALESCE(cd.country_display_names, '{}'::text[]) AS country_display_names
    FROM base_query_for_data bq
    LEFT JOIN store_counts sc ON bq.id = sc.website_id
    LEFT JOIN spider_counts spc ON bq.id = spc.website_id
    LEFT JOIN country_data cd ON bq.id = cd.website_id
    -- *** CORRECTED ORDER BY ***
    ORDER BY
      -- Text ASC
      CASE WHEN p_sort_direction = 'asc' AND v_sort_column IN ('w.name', 'w.code', 'w.url') THEN
        CASE v_sort_column WHEN 'w.name' THEN bq.name WHEN 'w.code' THEN bq.code WHEN 'w.url' THEN bq.url END
      END ASC NULLS LAST,
      -- Numeric ASC
      CASE WHEN p_sort_direction = 'asc' AND v_sort_column = 'w.id' THEN bq.id END ASC NULLS LAST,
      -- Timestamp ASC
      CASE WHEN p_sort_direction = 'asc' AND v_sort_column IN ('w.created_at', 'w.updated_at') THEN
        CASE v_sort_column WHEN 'w.created_at' THEN bq.created_at WHEN 'w.updated_at' THEN bq.updated_at END
      END ASC NULLS LAST,

      -- Text DESC
      CASE WHEN p_sort_direction = 'desc' AND v_sort_column IN ('w.name', 'w.code', 'w.url') THEN
        CASE v_sort_column WHEN 'w.name' THEN bq.name WHEN 'w.code' THEN bq.code WHEN 'w.url' THEN bq.url END
      END DESC NULLS FIRST,
      -- Numeric DESC
      CASE WHEN p_sort_direction = 'desc' AND v_sort_column = 'w.id' THEN bq.id END DESC NULLS FIRST,
      -- Timestamp DESC
      CASE WHEN p_sort_direction = 'desc' AND v_sort_column IN ('w.created_at', 'w.updated_at') THEN
        CASE v_sort_column WHEN 'w.created_at' THEN bq.created_at WHEN 'w.updated_at' THEN bq.updated_at END
      END DESC NULLS FIRST
    LIMIT p_limit
    OFFSET p_offset
  )
  -- Aggregate the paginated results into the v_data variable
  SELECT COALESCE(jsonb_agg(pd.*), '[]'::jsonb)
  INTO v_data
  FROM paginated_data pd;

  -- Build the final JSON object using the calculated variables
  RETURN jsonb_build_object(
    'total_count', COALESCE(v_total_count, 0),
    'data', v_data
  );

END;
$$;


create or replace procedure public.delete_products_batched(IN min_id bigint DEFAULT 322025, IN batch_size integer DEFAULT 100, IN sleep_ms numeric DEFAULT 0)
    language plpgsql
as
$$
DECLARE
    deleted_count INT;
    total_deleted BIGINT := 0;
    batch_number INT := 0;
BEGIN
    RAISE NOTICE 'Starting deletion of products with id > %', min_id;

    LOOP
        DELETE FROM products
        WHERE id IN (
            SELECT id FROM products
            WHERE id > min_id
            ORDER BY id
            LIMIT batch_size
        );

        GET DIAGNOSTICS deleted_count = ROW_COUNT;

        -- Exit if no more rows to delete
        EXIT WHEN deleted_count = 0;

        -- Update counters
        total_deleted := total_deleted + deleted_count;
        batch_number := batch_number + 1;

        -- COMMIT after each batch
        COMMIT;

        RAISE NOTICE 'Batch %: Deleted % rows (Total: %)', batch_number, deleted_count, total_deleted;

        -- Optional sleep to reduce load
        IF sleep_ms > 0 THEN
            PERFORM pg_sleep(sleep_ms / 1000.0);
        END IF;
    END LOOP;

    RAISE NOTICE 'Deletion completed. Total deleted: % rows in % batches', total_deleted, batch_number;
END;
$$;

