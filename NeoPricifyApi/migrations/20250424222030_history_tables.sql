create table inventory_history
(
    product_store_id      bigint                                 not null
        constraint fk_inventory_history_product_store
            references product_stores
            on delete cascade,
    previous_stock_qty    integer,
    new_stock_qty         integer                                not null,
    previous_stock_status stock_status,
    new_stock_status      stock_status                           not null,
    previous_manage_stock boolean,
    new_manage_stock      boolean                                not null,
    change_type           inventory_change_type                  not null,
    date_changed          timestamp with time zone default now() not null,
    constraint inventory_history_pkey
        primary key (product_store_id, date_changed)
)
    partition by RANGE (date_changed);

create table price_history
(
    product_store_id         bigint                                 not null
        constraint fk_price_history_product_store
            references product_stores
            on delete cascade,
    currency_code            char(3)
        constraint price_history_currency_code_fkey
            references currencies,
    previous_regular_price   numeric(10, 2),
    new_regular_price        numeric(10, 2),
    previous_sale_price      numeric(10, 2),
    new_sale_price           numeric(10, 2),
    previous_effective_price numeric(10, 2),
    new_effective_price      numeric(10, 2),
    date_changed             timestamp with time zone default now() not null,
    constraint price_history_pkey
        primary key (product_store_id, date_changed)
)
    partition by RANGE (date_changed);

create or replace function create_history_partitions(start_date timestamp with time zone, num_future_partitions integer DEFAULT 4) returns void
    language plpgsql
as
$$
DECLARE
    partition_start timestamp with time zone;
    partition_end timestamp with time zone;
    partition_name text;
    quarter text;
    year text;
BEGIN
    FOR i IN 0..num_future_partitions-1 LOOP
        partition_start := date_trunc('quarter', start_date + (i * interval '3 months'));
        partition_end := partition_start + interval '3 months';
        year := to_char(partition_start, 'YYYY');
        quarter := 'q' || to_char(partition_start, 'Q');
        
        -- Create inventory history partition
        partition_name := 'inventory_history_' || year || '_' || quarter;
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF inventory_history 
            FOR VALUES FROM (%L) TO (%L)',
            partition_name, partition_start, partition_end
        );
        
        -- Create price history partition
        partition_name := 'price_history_' || year || '_' || quarter;
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF price_history 
            FOR VALUES FROM (%L) TO (%L)',
            partition_name, partition_start, partition_end
        );
    END LOOP;
END;
$$;

-- Create initial partitions
SELECT create_history_partitions(date_trunc('quarter', CURRENT_DATE), 2);

create or replace function maintain_history_partitions() returns void
    language plpgsql
as
$$
BEGIN
    -- Create partitions for next 2 quarters (2 quarters)
    PERFORM create_history_partitions(date_trunc('quarter', CURRENT_DATE + interval '3 months'), 2);
END;
$$;

-- Schedule the maintenance task (runs monthly)
SELECT cron.schedule(
    'maintain-history-partitions',
    '0 0 1 * *', -- At midnight on the first day of every month
    'SELECT maintain_history_partitions()'
); 

create or replace function log_price_change() returns trigger
    language plpgsql
as
$$
BEGIN
    -- Log price changes to price_history
    IF (TG_OP = 'INSERT') OR
       (OLD.regular_price != NEW.regular_price) OR
       (OLD.sale_price IS DISTINCT FROM NEW.sale_price) THEN

        INSERT INTO price_history (
            currency_code,
            previous_regular_price,
            new_regular_price,
            previous_sale_price,
            new_sale_price,
            product_store_id,
            date_changed,
            previous_effective_price,
            new_effective_price
        ) VALUES (
            NEW.currency_code,
            CASE WHEN TG_OP = 'UPDATE' THEN OLD.regular_price ELSE NEW.regular_price END,
            NEW.regular_price,
            CASE WHEN TG_OP = 'UPDATE' THEN OLD.sale_price ELSE NEW.sale_price END,
            NEW.sale_price,
            NEW.product_store_id,
            CURRENT_TIMESTAMP,
            CASE WHEN TG_OP = 'UPDATE' THEN OLD.price ELSE NEW.price END,
            NEW.price
        );
    END IF;

    RETURN NEW;
END;
$$;

comment on function log_price_change() is 'Logs price changes to price_history table. Handles both INSERT and UPDATE operations on product_store_prices.';

create or replace function log_inventory_change() returns trigger
    language plpgsql
as
$$
BEGIN
    -- Log inventory changes to inventory_history
    IF (TG_OP = 'INSERT') OR
       (OLD.stock_qty IS DISTINCT FROM NEW.stock_qty) OR
       (OLD.stock_status IS DISTINCT FROM NEW.stock_status) OR
       (OLD.manage_stock IS DISTINCT FROM NEW.manage_stock) THEN

        INSERT INTO inventory_history (
            previous_stock_qty,
            new_stock_qty,
            change_type,
            previous_stock_status,
            new_stock_status,
            previous_manage_stock,
            new_manage_stock,
            product_store_id,
            date_changed
        ) VALUES (
            CASE WHEN TG_OP = 'UPDATE' THEN OLD.stock_qty ELSE NEW.stock_qty END,
            NEW.stock_qty,
            CASE
                WHEN TG_OP = 'INSERT' THEN 'initial'::inventory_change_type
                WHEN NEW.stock_qty = 0 AND NEW.stock_status = 'out_of_stock' THEN 'decrease'::inventory_change_type
                WHEN NEW.stock_status = 'out_of_stock' AND OLD.stock_status = 'in_stock' AND NEW.manage_stock = true THEN 'decrease'::inventory_change_type
                WHEN NEW.stock_status = 'in_stock' AND OLD.stock_status = 'out_of_stock' THEN 'increase'::inventory_change_type
                WHEN NEW.stock_status = 'out_of_stock' AND NEW.stock_qty > 0 AND NEW.manage_stock = false THEN 'system'::inventory_change_type
                WHEN NEW.stock_qty > OLD.stock_qty THEN 'increase'::inventory_change_type
                WHEN NEW.stock_qty < OLD.stock_qty THEN 'decrease'::inventory_change_type
                ELSE 'update'::inventory_change_type
            END,
            CASE WHEN TG_OP = 'UPDATE' THEN OLD.stock_status ELSE NEW.stock_status END,
            NEW.stock_status,
            CASE WHEN TG_OP = 'UPDATE' THEN OLD.manage_stock ELSE NEW.manage_stock END,
            NEW.manage_stock,
            NEW.product_store_id,
            CURRENT_TIMESTAMP
        );
    END IF;

    RETURN NEW;
END;
$$;

comment on function log_inventory_change() is 'Logs inventory changes to inventory_history table. Handles both INSERT and UPDATE operations on product_store_inventory.';

-- Trigger for logging price changes
CREATE TRIGGER on_product_store_price_change
    AFTER INSERT OR UPDATE ON product_store_prices
    FOR EACH ROW
    EXECUTE FUNCTION log_price_change();

-- Trigger for logging inventory changes
CREATE TRIGGER on_product_store_inventory_change
    AFTER INSERT OR UPDATE ON product_store_inventory
    FOR EACH ROW
    EXECUTE FUNCTION log_inventory_change();

COMMENT ON TRIGGER on_product_store_price_change ON product_store_prices IS 'Logs price changes to price_history';
COMMENT ON TRIGGER on_product_store_inventory_change ON product_store_inventory IS 'Logs inventory changes to inventory_history'; 