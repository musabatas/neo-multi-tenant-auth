create table if not exists public.ct_store_price_inventory
(
    id                          bigserial
        constraint ct_store_price_inventory_pkey
            primary key,
    product_id                  bigint  not null
        constraint fk_ctspi_product
            references public.products,
    store_id                    integer not null
        constraint fk_ctspi_store
            references public.stores,
    priceavailability_meta_data jsonb default '{}'::jsonb,
    constraint ct_store_price_inventory_product_store_unique
        unique (product_id, store_id)
);

create index if not exists idx_ctspi_product_id
    on public.ct_store_price_inventory (product_id);

create index if not exists idx_ctspi_store_id
    on public.ct_store_price_inventory (store_id);

