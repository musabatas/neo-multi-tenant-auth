-- Function to cancel email change
create or replace function public.cancel_email_change() returns json
    security definer
    language plpgsql
as
$$
DECLARE
_uid uuid; -- for checking by 'is not found'
user_id uuid; -- to store the user id from the request
BEGIN

  -- Get user by his current auth.uid
  user_id := auth.uid();

  -- Then clear the relevant fields on the auth.users table
  UPDATE auth.users SET
    email_change = '',
    email_change_token_current = '',
    email_change_token_new = '',
    email_change_confirm_status = 0,
    email_change_sent_at = NULL
  WHERE id = user_id;

  RETURN '{ "success": true }';
END;
$$;

-- Function to clean up product store meta_data
create or replace function public.clean_up_product_store_meta_data(batch_size integer DEFAULT 10000) returns void
    language plpgsql
as
$$
DECLARE
    last_id BIGINT := 0;
    r RECORD;
    target_json JSONB := '{
      "priceMessage": [
        {
          "label": null,
          "tooltip": null
        }
      ]
    }'::jsonb;
BEGIN
    LOOP
        -- Fetch a batch of rows with id > last_id
        FOR r IN
            SELECT id, meta_data
            FROM public.product_store_prices
            WHERE id > last_id
            ORDER BY id
            LIMIT batch_size
        LOOP
            -- Advance the window
            last_id := r.id;

            -- Match meta_data exactly
            IF r.meta_data = target_json THEN
                UPDATE public.product_store_prices
                SET meta_data = '{}'::jsonb
                WHERE id = r.id;
            END IF;
        END LOOP;

        -- Exit if no more records
        EXIT WHEN NOT FOUND;
    END LOOP;

    RAISE NOTICE 'Finished cleaning meta_data';
END;
$$;

-- Function to create a default store for a website
create or replace function public.create_default_store_for_website() returns trigger
    language plpgsql
as
$$
BEGIN
    -- Insert a default store associated with the new website
    INSERT INTO public.stores (
        website_id, 
        name, 
        code, 
        is_active, 
        created_at, 
        meta_data, 
        is_default
    ) VALUES (
        NEW.id,
        NEW.name,
        NEW.code,
        true,
        now(),
        '{}'::jsonb,
        true
    );
    
    RETURN NEW;
END;
$$;

comment on function public.create_default_store_for_website() is 'Creates a default store when a new website is created';

-- Function to get filtered stores
create or replace function public.get_filtered_stores(p_website_code character varying, p_min_id integer DEFAULT NULL::integer, p_max_id integer DEFAULT NULL::integer, p_address_states text[] DEFAULT NULL::text[], p_name_searches text[] DEFAULT NULL::text[], p_sort_field character varying DEFAULT 'id'::character varying, p_sort_direction character varying DEFAULT 'ASC'::character varying, p_limit integer DEFAULT NULL::integer, p_offset integer DEFAULT 0)
    returns TABLE(store_id integer, store_api_code character varying)
    language plpgsql
as
$$
DECLARE
    v_website_id integer;
    v_sql text;
    v_allowed_sort_fields text[] := ARRAY['id', 'name', 'code', 'api_code', 'created_at', 'updated_at', 'reference_priority'];
    v_validated_sort_field text;
    v_validated_sort_direction text;
    v_name_filter_sql text := '';
    v_search_term text;
BEGIN
    -- Find the website_id
    SELECT id INTO v_website_id
    FROM public.websites w
    WHERE w.code = p_website_code
      AND w.is_deleted = false
      AND w.is_active = true
    LIMIT 1;

    IF v_website_id IS NULL THEN
        RAISE WARNING 'Website with code % not found or inactive.', p_website_code;
        RETURN; -- Exit function if website not found
    END IF;

    -- Validate sort field
    IF p_sort_field = ANY(v_allowed_sort_fields) THEN
        v_validated_sort_field := p_sort_field;
    ELSE
        v_validated_sort_field := 'id';
        RAISE WARNING 'Invalid sort field requested: %. Defaulting to ''id''.', p_sort_field;
    END IF;

    -- Validate sort direction
    IF UPPER(p_sort_direction) IN ('ASC', 'DESC') THEN
        v_validated_sort_direction := UPPER(p_sort_direction);
    ELSE
        v_validated_sort_direction := 'ASC';
        RAISE WARNING 'Invalid sort direction requested: %. Defaulting to ''ASC''.', p_sort_direction;
    END IF;

    -- Base query
    v_sql := 'SELECT s.id, s.api_code
              FROM public.stores s ';

    -- Optional join for address filtering (only join if needed)
    IF p_address_states IS NOT NULL AND array_length(p_address_states, 1) > 0 THEN
        v_sql := v_sql || ' LEFT JOIN public.addresses a ON s.address_id = a.id ';
    END IF;

    -- WHERE clauses
    v_sql := v_sql || ' WHERE s.website_id = ' || quote_literal(v_website_id) ||
             ' AND s.is_active = true ' ||
             ' AND s.is_deleted = false ' ||
             ' AND s.api_code IS NOT NULL ';

    -- Add optional filters
    IF p_min_id IS NOT NULL THEN
        v_sql := v_sql || ' AND s.id >= ' || quote_literal(p_min_id);
    END IF;

    IF p_max_id IS NOT NULL THEN
        v_sql := v_sql || ' AND s.id <= ' || quote_literal(p_max_id);
    END IF;

    -- Filter by array of states using ANY and ILIKE for case-insensitivity
    IF p_address_states IS NOT NULL AND array_length(p_address_states, 1) > 0 THEN
        -- *** CORRECTED LINE ***
        v_sql := v_sql || ' AND EXISTS (SELECT 1 FROM unnest(' || quote_literal(p_address_states) || '::text[]) state_val WHERE a.state ILIKE state_val)';
    END IF;

    -- Filter by array of name searches using OR and ILIKE
    IF p_name_searches IS NOT NULL AND array_length(p_name_searches, 1) > 0 THEN
        v_name_filter_sql := ' AND (';
        FOR v_search_term IN SELECT unnest(p_name_searches) LOOP
            IF v_name_filter_sql != ' AND (' THEN
                v_name_filter_sql := v_name_filter_sql || ' OR ';
            END IF;
            -- Ensure the search term is also treated as text for ILIKE
            v_name_filter_sql := v_name_filter_sql || ' s.name ILIKE ' || quote_literal('%' || v_search_term::text || '%');
        END LOOP;
        v_name_filter_sql := v_name_filter_sql || ')';
        v_sql := v_sql || v_name_filter_sql;
    END IF;


    -- ORDER BY clause
    v_sql := v_sql || format(' ORDER BY s.%I %s', v_validated_sort_field, v_validated_sort_direction);

    -- LIMIT and OFFSET clauses
    IF p_limit IS NOT NULL THEN
        v_sql := v_sql || ' LIMIT ' || quote_literal(p_limit);
    END IF;

    v_sql := v_sql || ' OFFSET ' || quote_literal(p_offset);

    -- Execute the dynamic query
    RAISE NOTICE 'Executing SQL: %', v_sql; -- For debugging
    RETURN QUERY EXECUTE v_sql;

END;
$$;



