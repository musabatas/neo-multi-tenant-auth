-- Create migration state table
create table if not exists public.migration_state
(
    process_name      text             not null
        constraint migration_state_pkey
            primary key,
    last_processed_id bigint default 0 not null
);

-- Drop existing function if it exists
drop function if exists public.migrate_ct_price_inventory;

-- Create function to migrate Canadiantire price inventory data
create or replace function public.migrate_ct_price_inventory(p_website_code text DEFAULT 'canadiantire_ca'::text, p_batch_limit integer DEFAULT 5000)
    returns TABLE(processed_count integer, error_count integer, final_last_id bigint)
    language plpgsql
as
$$
DECLARE
    src_record                    RECORD;
    v_website_id                  INTEGER;
    v_ps_id                       BIGINT;
    v_currency_code               CHAR(3);
    v_regular_price               NUMERIC(10,2);
    v_sale_price                  NUMERIC(10,2);
    v_price_meta_data             JSONB;
    v_price_updated_at            TIMESTAMPTZ;
    v_stock_qty                   INTEGER;
    v_stock_status                public.stock_status;
    v_manage_stock                BOOLEAN;
    v_inventory_meta_data         JSONB;
    v_inventory_updated_at        TIMESTAMPTZ;
    v_query_params                TEXT;
    v_processed_count             INTEGER := 0;
    v_error_count                 INTEGER := 0;
    v_last_id                     BIGINT;
    v_loop_count                  INTEGER := 0;
    v_batch_row_count             INTEGER := 0;
    v_deleted_row_count           INTEGER := 0;
    v_process_name                TEXT := 'ct_price_inventory';
    v_migration_state_update_count INTEGER;
BEGIN
    RAISE NOTICE 'Starting BATCHED migration for %...', p_website_code;

    -- ensure state row
    INSERT INTO public.migration_state (process_name, last_processed_id)
    VALUES (v_process_name, 0)
    ON CONFLICT (process_name) DO NOTHING;

    -- load last checkpoint
    SELECT last_processed_id
      INTO v_last_id
      FROM public.migration_state
     WHERE process_name = v_process_name;

    -- lookup website
    SELECT id INTO v_website_id
      FROM public.websites
     WHERE code = p_website_code
       AND is_active = TRUE
       AND is_deleted = FALSE
     LIMIT 1;

    IF v_website_id IS NULL THEN
        RAISE EXCEPTION 'Website "%" not found or inactive.', p_website_code;
    END IF;

    -- batch loop
    LOOP
        v_loop_count := v_loop_count + 1;
        v_batch_row_count := 0;
        RAISE NOTICE 'Batch #% — processing IDs > %...', v_loop_count, v_last_id;

        FOR src_record IN
            SELECT *
              FROM public.ct_store_price_inventory
             WHERE id > v_last_id
             ORDER BY id
             LIMIT p_batch_limit
        LOOP
            BEGIN
                v_processed_count := v_processed_count + 1;
                v_batch_row_count := v_batch_row_count + 1;
                v_last_id := src_record.id;

                IF (v_processed_count % 5000) = 0 THEN
                    RAISE NOTICE '  … processed % records so far', v_processed_count;
                END IF;

                -- parse timestamps
                v_price_updated_at := COALESCE(
                  (src_record.priceavailability_meta_data->>'price_updated_at')::timestamptz,
                  now()
                );
                v_inventory_updated_at := COALESCE(
                  (src_record.priceavailability_meta_data->>'inventory_updated_at')::timestamptz,
                  now()
                );

                -- upsert product_store
                v_query_params := src_record.priceavailability_meta_data->>'query_params';
                INSERT INTO public.product_stores (
                  product_id, website_id, store_id, url_type,
                  query_params, is_active, created_at, updated_at
                ) VALUES (
                  src_record.product_id, v_website_id, src_record.store_id,
                  'query_params_only', v_query_params, TRUE,
                  v_price_updated_at, v_price_updated_at
                )
                ON CONFLICT (product_id, website_id, store_id)
                DO UPDATE SET
                  url_type     = EXCLUDED.url_type,
                  query_params = EXCLUDED.query_params,
                  is_active    = EXCLUDED.is_active,
                  updated_at   = EXCLUDED.updated_at
                RETURNING id INTO v_ps_id;

                -- upsert prices
                v_currency_code := src_record.priceavailability_meta_data->>'currency_code';
                v_regular_price := (src_record.priceavailability_meta_data->>'regular_price')::numeric;
                v_sale_price    := (src_record.priceavailability_meta_data->>'sale_price')::numeric;
                v_price_meta_data := src_record.priceavailability_meta_data->'price_meta_data';
                IF v_price_meta_data IS NULL OR jsonb_typeof(v_price_meta_data)<>'object' THEN
                    v_price_meta_data := '{}'::jsonb;
                END IF;

                IF v_ps_id IS NOT NULL
                   AND v_currency_code IS NOT NULL
                   AND v_regular_price IS NOT NULL
                THEN
                    INSERT INTO public.product_store_prices (
                      product_store_id, currency_code,
                      regular_price, sale_price,
                      meta_data, updated_at
                    ) VALUES (
                      v_ps_id, v_currency_code,
                      v_regular_price, v_sale_price,
                      v_price_meta_data, v_price_updated_at
                    )
                    ON CONFLICT (product_store_id, currency_code)
                    DO UPDATE SET
                      regular_price = EXCLUDED.regular_price,
                      sale_price    = EXCLUDED.sale_price,
                      meta_data     = EXCLUDED.meta_data,
                      updated_at    = EXCLUDED.updated_at;
                END IF;

                -- upsert inventory
                v_stock_qty        := (src_record.priceavailability_meta_data->>'stock_qty')::integer;
                v_stock_status     := (src_record.priceavailability_meta_data->>'stock_status')::public.stock_status;
                v_manage_stock     := (src_record.priceavailability_meta_data->>'manage_stock')::boolean;
                v_inventory_meta_data := src_record.priceavailability_meta_data->'inventory_meta_data';
                IF v_inventory_meta_data IS NULL OR jsonb_typeof(v_inventory_meta_data)<>'object' THEN
                    v_inventory_meta_data := '{}'::jsonb;
                END IF;

                IF v_ps_id IS NOT NULL
                   AND (v_stock_status IS NOT NULL OR v_stock_qty IS NOT NULL)
                THEN
                    v_manage_stock := COALESCE(v_manage_stock, TRUE);
                    v_stock_status := COALESCE(
                      v_stock_status,
                      CASE WHEN COALESCE(v_stock_qty,0)>0 THEN 'in_stock' ELSE 'out_of_stock' END
                    )::public.stock_status;

                    INSERT INTO public.product_store_inventory (
                      product_store_id, stock_qty, stock_status,
                      manage_stock, updated_at, meta_data
                    ) VALUES (
                      v_ps_id, v_stock_qty, v_stock_status,
                      v_manage_stock, v_inventory_updated_at, v_inventory_meta_data
                    )
                    ON CONFLICT (product_store_id)
                    DO UPDATE SET
                      stock_qty    = EXCLUDED.stock_qty,
                      stock_status = EXCLUDED.stock_status,
                      manage_stock = EXCLUDED.manage_stock,
                      updated_at   = EXCLUDED.updated_at,
                      meta_data    = EXCLUDED.meta_data;
                END IF;

            EXCEPTION WHEN OTHERS THEN
                v_error_count := v_error_count + 1;
                RAISE WARNING '[ID %] % (SQLSTATE %)', src_record.id, SQLERRM, SQLSTATE;
                CONTINUE;
            END;
        END LOOP;

        -- inline cleanup of processed rows
        IF v_batch_row_count > 0 THEN
            DELETE FROM public.ct_store_price_inventory
             WHERE id <= v_last_id;
            GET DIAGNOSTICS v_deleted_row_count = ROW_COUNT;
            RAISE NOTICE '  → deleted % source rows (up to %)', v_deleted_row_count, v_last_id;

            UPDATE public.migration_state
               SET last_processed_id = v_last_id
             WHERE process_name = v_process_name;
            GET DIAGNOSTICS v_migration_state_update_count = ROW_COUNT;
            RAISE NOTICE '  → checkpoint advanced to %', v_last_id;
        ELSE
            RAISE NOTICE 'No new records in batch #% — stopping.', v_loop_count;
        END IF;

        EXIT WHEN v_batch_row_count < p_batch_limit;
    END LOOP;

    RAISE NOTICE 'Migration complete. Processed %, Errors %, Final ID %',
      v_processed_count, v_error_count, v_last_id;

    RETURN QUERY SELECT v_processed_count, v_error_count, v_last_id;
END;
$$;

--- Execute the function example
--- select from migrate_ct_price_inventory('canadiantire_ca', 5000 );


