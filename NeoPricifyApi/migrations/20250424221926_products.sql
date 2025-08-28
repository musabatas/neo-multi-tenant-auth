create table if not exists public.products
(
    id             bigserial
        constraint products_pkey
            primary key,
    global_code    varchar(255),
    brand_id       integer
        constraint products_brand_id_fkey
            references public.brands,
    name           text,
    description    text,
    sku            varchar(255),
    product_type   product_type             default 'simple'::product_type not null,
    visibility     product_visibility       default 'visible'::product_visibility,
    sellable       boolean                  default true                   not null,
    base_image_url varchar,
    attribute_data jsonb                    default '{}'::jsonb,
    meta_data      jsonb                    default '{}'::jsonb,
    crawler_meta   jsonb                    default '{}'::jsonb,
    is_deleted     boolean                  default false,
    created_at     timestamp with time zone default CURRENT_TIMESTAMP      not null,
    updated_at     timestamp with time zone,
    deleted_at     timestamp with time zone,
    is_active      boolean                  default true,
    constraint check_deleted_status
        check ((deleted_at IS NULL) = (is_deleted = false))
)
    with (autovacuum_vacuum_scale_factor = 0.05, autovacuum_analyze_scale_factor = 0.02);

create index if not exists idx_products_brand
    on public.products (brand_id) include (id, name, product_type)
    where ((deleted_at IS NULL) AND (is_deleted = false));

create index if not exists idx_products_search
    on public.products (name, sku, global_code) include (id, product_type, visibility)
    where ((deleted_at IS NULL) AND (is_deleted = false));

create unique index if not exists unique_product_global_code
    on public.products (global_code)
    where ((deleted_at IS NULL) AND (is_deleted = false));

create unique index if not exists unique_product_sku
    on public.products (sku)
    where ((deleted_at IS NULL) AND (is_deleted = false));

create index if not exists idx_products_type_active_deleted
    on public.products (product_type, is_active, deleted_at, is_deleted)
    where ((deleted_at IS NULL) AND (is_deleted = false));

create index if not exists idx_products_sku_lower
    on public.products (lower(sku::text))
    where ((deleted_at IS NULL) AND (is_deleted = false));

create index if not exists idx_products_global_code_lower
    on public.products (lower(global_code::text))
    where ((deleted_at IS NULL) AND (is_deleted = false));

create index if not exists idx_products_name_lower_text
    on public.products (lower(name) pg_catalog.text_pattern_ops)
    where ((deleted_at IS NULL) AND (is_deleted = false));

create index if not exists idx_products_visibility_sellable_active
    on public.products (visibility, sellable, is_active) include (id, name, product_type)
    where ((deleted_at IS NULL) AND (is_deleted = false));

create index if not exists idx_products_name_deleted_full
    on public.products (name, deleted_at);

create index if not exists idx_products_name_covering
    on public.products (name)
    where (deleted_at IS NULL);

create index if not exists idx_products_in_queries_optimization
    on public.products (id, deleted_at, name)
    where (deleted_at IS NULL);

create index if not exists idx_products_deep_pagination_name_id
    on public.products (name, id)
    where (deleted_at IS NULL);

create index if not exists idx_products_pagination_covering
    on public.products (deleted_at, name, id) include (global_code, sku, product_type, visibility, sellable, is_active, base_image_url);

-- Create product categories table.
create table if not exists public.product_categories
(
    product_id  bigint  not null
        constraint product_categories_product_id_fkey
            references public.products
            on delete cascade,
    category_id integer not null
        constraint product_categories_category_id_fkey
            references public.categories,
    constraint product_categories_pkey
        primary key (product_id, category_id)
);

create index if not exists idx_product_categories_category_product
    on public.product_categories (category_id) include (product_id);

-- Create product collections table.
create table if not exists public.product_collections
(
    product_id    bigint  not null
        constraint product_collections_product_id_fkey
            references public.products
            on delete cascade,
    collection_id integer not null
        constraint product_collections_collection_id_fkey
            references public.collections,
    sort_order    integer default 0,
    website_id    integer
        constraint product_collections_website_id_fkey
            references public.websites,
    constraint product_collections_pkey
        primary key (product_id, collection_id)
);

create index if not exists idx_product_collections_collection
    on public.product_collections (collection_id, sort_order) include (product_id);

-- Create product attributes table.
create table if not exists public.product_attributes
(
    product_id          bigint            not null
        constraint product_attributes_product_id_fkey
            references public.products
            on delete cascade,
    attribute_option_id integer           not null
        constraint product_attributes_attribute_option_id_fkey
            references public.attribute_options
            on delete cascade,
    website_id          integer default 0 not null
        constraint product_attributes_website_id_fkey
            references public.websites,
    constraint product_attributes_pkey
        primary key (product_id, attribute_option_id, website_id)
);

create index if not exists idx_product_attributes_product
    on public.product_attributes (product_id) include (attribute_option_id, website_id);

create index if not exists idx_product_attributes_website
    on public.product_attributes (website_id) include (product_id, attribute_option_id);

-- Create product identifiers table.
create table if not exists public.product_identifiers
(
    product_id          bigint          not null
        constraint product_identifiers_product_id_fkey
            references public.products
            on delete cascade,
    identifier_type     identifier_type not null,
    identifier_value    varchar(255)    not null,
    is_primary          boolean                  default false,
    is_verified         boolean                  default false,
    verified_at         timestamp with time zone,
    verified_by         uuid
        constraint product_identifiers_verified_by_fkey
            references public.users,
    meta_data           jsonb                    default '{"markets": []}'::jsonb,
    created_at          timestamp with time zone default now(),
    verification_status verification_status      default 'pending'::verification_status,
    id                  bigint generated by default as identity
        constraint product_identifiers_pkey
            primary key,
    constraint unique_product_identifier
        unique (product_id, identifier_type, identifier_value)
);

create index if not exists idx_product_identifiers_verification_status
    on public.product_identifiers (verification_status);

create index if not exists idx_product_identifiers_product_id
    on public.product_identifiers (product_id);

create index if not exists idx_product_identifiers_type_value_status
    on public.product_identifiers (identifier_type, identifier_value, verification_status);

create index if not exists idx_product_identifiers_product_primary
    on public.product_identifiers (product_id asc, is_primary desc, identifier_type asc) include (identifier_value, is_verified);

create index if not exists idx_product_identifiers_value_type
    on public.product_identifiers (identifier_value, identifier_type) include (product_id);

-- Create product identifier websites table.
create table if not exists public.product_identifier_websites
(
    website_id            integer not null
        constraint product_identifier_websites_website_id_fkey
            references public.websites
            on delete cascade,
    product_identifier_id bigint  not null
        constraint product_identifier_websites_product_identifier_id_fkey
            references public.product_identifiers
            on delete cascade,
    constraint product_identifier_websites_pkey
        primary key (product_identifier_id, website_id)
);

-- Create indexes for product identifier websites table.
create index if not exists idx_product_identifier_websites_identifier
    on public.product_identifier_websites (product_identifier_id) include (website_id);

create index if not exists idx_product_identifier_websites_website
    on public.product_identifier_websites (website_id) include (product_identifier_id);

-- Create product media table.
create table if not exists public.product_media
(
    product_id bigint            not null
        constraint product_media_product_id_fkey
            references public.products
            on delete cascade,
    website_id integer           not null
        constraint product_media_website_id_fkey
            references public.websites,
    media_type media_type        not null,
    media_role media_role        not null,
    url        text              not null,
    meta_data  jsonb   default '{}'::jsonb,
    sort_order integer default 0 not null,
    constraint product_media_pkey
        primary key (product_id, website_id, media_type, media_role, sort_order)
);

-- Create product website details table.
create table if not exists public.product_website_details
(
    product_id     bigint                                not null
        constraint product_website_details_product_id_fkey
            references public.products
            on delete cascade,
    website_id     integer                               not null
        constraint product_website_details_website_id_fkey
            references public.websites,
    name           text,
    sku            varchar(255),
    base_image_url text,
    default_url    text,
    url_type       url_type                 default 'external'::url_type,
    is_active      boolean                  default true,
    sellable       boolean                  default true not null,
    attribute_data jsonb                    default '{}'::jsonb,
    meta_data      jsonb                    default '{}'::jsonb,
    crawler_meta   jsonb                    default '{}'::jsonb,
    seo_data       jsonb                    default '{"robots": "index,follow"}'::jsonb,
    created_at     timestamp with time zone default now(),
    updated_at     timestamp with time zone,
    constraint product_website_details_pkey
        primary key (product_id, website_id)
);

create unique index if not exists unique_product_website_sku
    on public.product_website_details (website_id, sku)
    where ((sku IS NOT NULL) AND (is_active = true));

create index if not exists idx_product_website_details_product
    on public.product_website_details (product_id) include (website_id, name, sku, default_url);

create index if not exists idx_product_website_details_website_active
    on public.product_website_details (website_id, is_active)
    where (is_active = true);

create index if not exists idx_product_website_details_n1_fix
    on public.product_website_details (product_id, website_id) include (name, sku, base_image_url, default_url, url_type, is_active, sellable);

-- Create product variant config table.
create table if not exists public.product_variant_config
(
    product_id         bigint  not null
        constraint product_variant_config_product_id_fkey
            references public.products
            on delete cascade,
    website_id         integer not null
        constraint product_variant_config_website_id_fkey
            references public.websites
            on delete cascade,
    variant_attributes text[],
    attribute_config   jsonb default '{}'::jsonb,
    constraint product_variant_config_pkey
        primary key (product_id, website_id)
);

create index if not exists idx_product_variant_config_lookup
    on public.product_variant_config (product_id, website_id);

-- Create product stores table.
create table if not exists public.product_stores
(
    id            bigserial
        constraint product_stores_pkey
            primary key,
    product_id    bigint                                                             not null
        constraint product_stores_product_id_fkey
            references public.products
            on delete cascade,
    website_id    integer                                                            not null
        constraint product_stores_website_id_fkey
            references public.websites,
    store_id      integer
        constraint product_stores_store_id_fkey
            references public.stores
            on delete cascade,
    store_url     text,
    query_params  text,
    url_type      store_url_type           default 'same_as_website'::store_url_type not null,
    is_active     boolean                  default true,
    display_order integer                  default 0,
    meta_data     jsonb                    default '{}'::jsonb,
    created_at    timestamp with time zone default now()                             not null,
    updated_at    timestamp with time zone default now(),
    constraint unique_product_store
        unique (product_id, website_id, store_id)
)
    with (autovacuum_vacuum_scale_factor = 0.05, autovacuum_analyze_scale_factor = 0.02);

create index if not exists idx_product_stores_store
    on public.product_stores (store_id);

create index if not exists idx_product_stores_product
    on public.product_stores (product_id);

-- Create product store inventory table.
create table if not exists public.product_store_inventory
(
    id               bigserial
        constraint product_store_inventory_pkey
            primary key,
    product_store_id bigint                                                    not null
        constraint unique_product_store_inventory
            unique
        constraint product_store_inventory_product_store_id_fkey
            references public.product_stores
            on delete cascade,
    stock_qty        integer,
    stock_status     stock_status             default 'in_stock'::stock_status not null,
    manage_stock     boolean                  default true                     not null,
    updated_at       timestamp with time zone default CURRENT_TIMESTAMP,
    meta_data        jsonb                    default '{}'::jsonb
)
    with (autovacuum_vacuum_scale_factor = 0.05, autovacuum_analyze_scale_factor = 0.02);

create index if not exists idx_product_store_inventory_date
    on public.product_store_inventory using brin (updated_at);

create index if not exists idx_product_store_inventory_store
    on public.product_store_inventory (product_store_id);

create index if not exists idx_product_store_inventory_status
    on public.product_store_inventory (product_store_id, stock_status) include (stock_qty);

-- Create product store prices table.
create table if not exists public.product_store_prices
(
    id               bigserial
        constraint product_store_prices_pkey
            primary key,
    product_store_id bigint         not null
        constraint product_store_prices_product_store_id_fkey
            references public.product_stores
            on delete cascade,
    currency_code    char(3)        not null
        constraint product_store_prices_currency_code_fkey
            references public.currencies,
    regular_price    numeric(10, 2) not null
        constraint product_store_prices_regular_price_check
            check (regular_price >= (0)::numeric),
    sale_price       numeric(10, 2),
    price            numeric(10, 2) generated always as (
        CASE
            WHEN (sale_price IS NOT NULL) THEN sale_price
            ELSE regular_price
            END) stored,
    meta_data        jsonb default '{}'::jsonb,
    updated_at       timestamp with time zone,
    constraint unique_product_store_currency
        unique (product_store_id, currency_code),
    constraint product_store_prices_check
        check ((sale_price IS NULL) OR ((sale_price <= regular_price) AND (sale_price >= (0)::numeric)))
)
    with (autovacuum_vacuum_scale_factor = 0.05, autovacuum_analyze_scale_factor = 0.02);

create index if not exists idx_product_store_prices_date
    on public.product_store_prices using brin (updated_at);

create index if not exists idx_product_store_prices_store
    on public.product_store_prices (product_store_id);

create table if not exists public.unmapped_products
(
    id   bigserial
        constraint unmapped_products_pkey
            primary key,
    gtin  varchar(20) not null,
    asin varchar(20) not null
);

create index if not exists idx_unmapped_products_gtin_asin
    on public.unmapped_products (gtin, asin);

