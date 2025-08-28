SELECT cron.schedule(
    'migrate_ct_price_inventory_job',        -- job name
    '*/50 * * * *',                          -- cron expression (every 50 minutes)
    $$SELECT * FROM public.migrate_ct_price_inventory('canadiantire_ca', 5000);$$
);

create or replace function public.delete_ct_store_price_inventory_batched(p_max_id bigint, p_batch_size integer DEFAULT 10000)
    returns TABLE(total_deleted integer)
    language plpgsql
as
$$
DECLARE
    v_deleted_count INTEGER := 0;
    v_total_deleted INTEGER := 0;
BEGIN
    RAISE NOTICE 'Starting batched delete up to ID % in batches of %...', p_max_id, p_batch_size;

    LOOP
        WITH to_delete AS (
            SELECT id
            FROM public.ct_store_price_inventory
            WHERE id < p_max_id
            ORDER BY id
            LIMIT p_batch_size
        )
        DELETE FROM public.ct_store_price_inventory
        USING to_delete
        WHERE ct_store_price_inventory.id = to_delete.id
        RETURNING ct_store_price_inventory.id;

        GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
        v_total_deleted := v_total_deleted + v_deleted_count;

        RAISE NOTICE 'Deleted % rows (total so far: %)...', v_deleted_count, v_total_deleted;

        -- Exit if less than one full batch
        EXIT WHEN v_deleted_count < p_batch_size;
    END LOOP;

    RETURN QUERY SELECT v_total_deleted;
END;
$$;

create or replace function public.delete_ct_store_price_inventory_one_batch(p_max_id bigint, p_batch_size integer DEFAULT 10000) returns integer
    language plpgsql
as
$$
DECLARE
    v_deleted_count INTEGER;
BEGIN
    WITH to_delete AS (
      SELECT id
        FROM public.ct_store_price_inventory
       WHERE id < p_max_id
       ORDER BY id
       LIMIT p_batch_size
    )
    DELETE FROM public.ct_store_price_inventory
     WHERE id IN (SELECT id FROM to_delete);

    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    RETURN v_deleted_count;
END;
$$;

create or replace function public.delete_ct_store_price_inventory_all(p_max_id bigint, p_batch_size integer DEFAULT 5000) returns integer
    language plpgsql
as
$$
DECLARE
    v_deleted_this_batch INTEGER;
    v_total_deleted      INTEGER := 0;
BEGIN
    LOOP
        -- delete one batch
        v_deleted_this_batch := public.delete_ct_store_price_inventory_one_batch(
            p_max_id,
            p_batch_size
        );

        -- accumulate and report
        v_total_deleted := v_total_deleted + v_deleted_this_batch;
        RAISE NOTICE 'Deleted % rows this batch (total so far: %)',
                     v_deleted_this_batch, v_total_deleted;

        -- stop when there’s nothing left below p_max_id
        EXIT WHEN v_deleted_this_batch = 0;
    END LOOP;

    RETURN v_total_deleted;
END;
$$;



-- Run the function to delete the rows
-- SELECT * FROM public.delete_ct_store_price_inventory_batched(8450245, 10000);

