-- Create price inventory batch tracking table.
create table if not exists public.price_inventory_batch_tracking
(
    id              bigserial
        constraint price_inventory_batch_tracking_pkey
            primary key,
    batch_index     integer                                                       not null,
    store_id        integer                                                       not null
        constraint price_inventory_batch_tracking_store_id_fkey
            references stores,
    status          varchar(20)              default 'pending'::character varying not null,
    products_count  integer                                                       not null,
    processed_count integer                  default 0,
    started_at      timestamp with time zone,
    completed_at    timestamp with time zone,
    error_message   text,
    created_at      timestamp with time zone default now()
);

-- Create product price aggregates table.
create table if not exists public.product_price_aggregates
(
    product_id         bigint  not null
        constraint product_price_aggregates_pkey
            primary key
        constraint product_price_aggregates_product_id_fkey
            references public.products
            on delete cascade,
    min_price_usd      numeric not null,
    max_price_usd      numeric not null,
    min_price_store_id integer
        constraint product_price_aggregates_min_price_store_id_fkey
            references public.stores
            on delete set null,
    max_price_store_id integer
        constraint product_price_aggregates_max_price_store_id_fkey
            references public.stores
            on delete set null,
    reference_prices   jsonb,
    updated_at         timestamp default now(),
    profit_amount      numeric(10, 2) generated always as ((max_price_usd - min_price_usd)) stored,
    profit_percentage  numeric(10, 2) generated always as (((
        ((max_price_usd - min_price_usd) / NULLIF(min_price_usd, (0)::numeric)) *
        (100)::numeric))::numeric(10, 2)) stored
);

create index if not exists idx_product_price_aggregates_price_time
    on public.product_price_aggregates (min_price_usd, max_price_usd, updated_at);

create index if not exists idx_product_price_aggregates_profit
    on public.product_price_aggregates (profit_amount, profit_percentage);

create index if not exists idx_product_price_aggregates_reference_prices
    on public.product_price_aggregates using gin (reference_prices);

create index if not exists idx_product_price_aggregates_updated
    on public.product_price_aggregates (updated_at) include (product_id, min_price_usd, max_price_usd);

-- Create product price update queue table.
create table if not exists public.product_price_update_queue
(
    product_id bigint not null
        constraint product_price_update_queue_pkey
            primary key
        constraint product_price_update_queue_product_id_fkey
            references public.products
            on delete cascade,
    created_at timestamp with time zone default now()
);

create index if not exists idx_price_update_queue_created
    on public.product_price_update_queue (created_at) include (product_id);

-- Create cron job logs table.
create table if not exists public.cron_job_logs
(
    id            bigserial
        constraint cron_job_logs_pkey
            primary key,
    job_name      text not null,
    rows_affected integer,
    error_message text,
    executed_at   timestamp with time zone default now()
);

create index if not exists idx_cron_job_logs_job_name_date
    on public.cron_job_logs (job_name asc, executed_at desc);

