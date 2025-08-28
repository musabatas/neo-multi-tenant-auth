-- MarketSpy Schema
create schema if not exists marketspy;

-- Create enums for marketspy schema
create type marketspy.opportunity_status as enum ('active', 'expired', 'out_of_stock', 'discontinued', 'unprofitable', 'pending');

-- Create sources table
create table if not exists marketspy.sources
(
    id          serial
        constraint sources_pkey
            primary key,
    name        varchar(255) not null,
    description text,
    url         text,
    api_key     text,
    api_secret  text,
    api_token   text,
    api_url     text,
    api_method  text,
    created_at  timestamp with time zone default now(),
    updated_at  timestamp with time zone default now()
);

-- Create opportunities table
create table if not exists marketspy.opportunities
(
    id                    bigserial
        constraint opportunities_pkey
            primary key,
    external_id           varchar(100),
    supplier_name         varchar(255) not null,
    asin                  varchar(20)  not null,
    upc                   varchar(30),
    supplier_sku          varchar(512),
    amazon_title          text,
    supplier_product_name text,
    supplier_title        text,
    weight                numeric(8, 4),
    dimensions            varchar(100),
    is_hazmat             boolean                      default false,
    available_quantity    integer,
    package_quantity      integer                      default 1,
    weight_in_bundle      numeric(8, 4),
    thumbnail_small_url   text,
    amazon_url            text,
    supplier_url          text,
    root_category_name    varchar(255),
    tags                  text[],
    map_price             numeric(10, 2),
    product_id            bigint
        constraint opportunities_product_id_fkey
            references public.products
            on delete set null,
    supplier_store_id     integer
        constraint opportunities_supplier_store_id_fkey
            references public.stores
            on delete set null,
    marketplace_store_id  integer
        constraint opportunities_marketplace_store_id_fkey
            references public.stores
            on delete set null,
    size_tier             varchar(100),
    case_quantity         integer,
    status                marketspy.opportunity_status default 'active'::marketspy.opportunity_status,
    confidence_score      numeric(3, 2)                default 0.0
        constraint valid_confidence
            check ((confidence_score >= 0.0) AND (confidence_score <= 1.0)),
    source_id             integer                      default 1
        constraint opportunities_source_id_fkey
            references marketspy.sources
            on delete cascade,
    import_batch_id       varchar(100),
    created_at            timestamp with time zone     default now(),
    updated_at            timestamp with time zone     default now()
);

comment on table marketspy.opportunities is 'Core opportunity records with comprehensive product data from SupplySpy CSV and JSON API responses';

-- Create indexes for opportunities table
create index if not exists idx_opportunities_asin
    on marketspy.opportunities (asin, status);

create index if not exists idx_opportunities_supplier_name
    on marketspy.opportunities (supplier_name, status);

create index if not exists idx_opportunities_supplier_store
    on marketspy.opportunities (supplier_store_id, status);

create index if not exists idx_opportunities_product
    on marketspy.opportunities (product_id, status);

create index if not exists idx_opportunities_batch
    on marketspy.opportunities (import_batch_id asc, created_at desc);

create index if not exists idx_opportunities_external_id
    on marketspy.opportunities (external_id)
    where (external_id IS NOT NULL);

create index if not exists idx_opportunities_category
    on marketspy.opportunities (root_category_name)
    where (root_category_name IS NOT NULL);

create index if not exists idx_opportunities_hazmat
    on marketspy.opportunities (is_hazmat)
    where (is_hazmat = true);

create index if not exists idx_opportunities_tags
    on marketspy.opportunities using gin (tags)
    where (tags IS NOT NULL);

-- Create opportunity pricing table
create table if not exists marketspy.opportunity_pricing
(
    id                         bigserial
        constraint opportunity_pricing_pkey
            primary key,
    opportunity_id             bigint         not null
        constraint opportunity_pricing_opportunity_id_fkey
            references marketspy.opportunities
            on delete cascade,
    total_cost                 numeric(10, 2) not null
        constraint positive_cost
            check (total_cost >= (0)::numeric),
    seller_price               numeric(10, 2),
    lowest_price               numeric(10, 2),
    lowest_fba_price           numeric(10, 2),
    lowest_price_week_avg      numeric(10, 2),
    lowest_price_month_avg     numeric(10, 2),
    lowest_fba_price_week_avg  numeric(10, 2),
    lowest_fba_price_month_avg numeric(10, 2),
    supplier_price             numeric(10, 2),
    supplier_adjusted_price    numeric(10, 2),
    sell_price                 numeric(10, 2),
    amazon_fees                numeric(10, 2),
    amazon_fulfillment_fees    numeric(10, 2),
    shipping_to_amazon         numeric(10, 2),
    inbound_shipping           numeric(10, 2),
    total_purchasing_cost      numeric(10, 2),
    amazon_package_quantity    integer                  default 1,
    supplier_package_quantity  integer                  default 1,
    profit_amount              numeric(10, 2),
    profit_fba_amount          numeric(10, 2),
    roi_percentage             numeric(7, 2),
    roi_fba_percentage         numeric(7, 2),
    proceed_amount             numeric(10, 2),
    proceed_fba_amount         numeric(10, 2),
    currency_code              char(3)                  default 'USD'::bpchar,
    pricing_date               date                     default CURRENT_DATE,
    created_at                 timestamp with time zone default now(),
    updated_at                 timestamp with time zone default now()
);

comment on table marketspy.opportunity_pricing is 'Detailed pricing, cost breakdown, and profit data that updates frequently';

-- Create indexes for opportunity pricing table
create index if not exists idx_pricing_opportunity
    on marketspy.opportunity_pricing (opportunity_id asc, created_at desc);

create index if not exists idx_pricing_profit
    on marketspy.opportunity_pricing (profit_amount desc, roi_percentage desc);

create index if not exists idx_pricing_fba_profit
    on marketspy.opportunity_pricing (profit_fba_amount desc, roi_fba_percentage desc);

create index if not exists idx_pricing_cost
    on marketspy.opportunity_pricing (total_cost);

create index if not exists idx_pricing_supplier_price
    on marketspy.opportunity_pricing (supplier_price)
    where (supplier_price IS NOT NULL);

create index if not exists idx_pricing_amazon_fees
    on marketspy.opportunity_pricing (amazon_fees desc)
    where (amazon_fees IS NOT NULL);

-- Create opportunity market data table
create table if not exists marketspy.opportunity_market_data
(
    id                   bigserial
        constraint opportunity_market_data_pkey
            primary key,
    opportunity_id       bigint not null
        constraint opportunity_market_data_opportunity_id_fkey
            references marketspy.opportunities
            on delete cascade,
    total_seller_count   integer,
    fba_seller_count     integer,
    sold_by_amazon       boolean                  default false,
    current_sales_rank   integer,
    historical_min_rank  integer,
    sales_rank_week_avg  integer,
    sales_rank_month_avg integer,
    sales_rank_best      integer,
    rank_category        varchar(100),
    data_source          varchar(50)              default 'supplyspy'::character varying,
    created_at           timestamp with time zone default now(),
    updated_at           timestamp with time zone default now()
);

comment on table marketspy.opportunity_market_data is 'Market intelligence and sales rank data that updates frequently';

-- Create indexes for opportunity market data table
create index if not exists idx_market_opportunity
    on marketspy.opportunity_market_data (opportunity_id asc, created_at desc);

create index if not exists idx_market_sales_rank
    on marketspy.opportunity_market_data (current_sales_rank)
    where (current_sales_rank IS NOT NULL);

create index if not exists idx_market_sales_rank_best
    on marketspy.opportunity_market_data (sales_rank_best)
    where (sales_rank_best IS NOT NULL);

create index if not exists idx_market_sellers
    on marketspy.opportunity_market_data (total_seller_count, fba_seller_count);

create index if not exists idx_market_amazon_seller
    on marketspy.opportunity_market_data (sold_by_amazon, current_sales_rank);

-- Create external product mapping table
create table if not exists marketspy.external_product_mapping
(
    id               bigserial
        constraint external_product_mapping_pkey
            primary key,
    external_id      varchar(100) not null,
    external_type    varchar(20)  not null,
    external_source  varchar(50)  not null,
    product_id       bigint
        constraint external_product_mapping_product_id_fkey
            references public.products
            on delete cascade,
    confidence_score numeric(3, 2)            default 1.0,
    verified_at      timestamp with time zone,
    verified_by      varchar(100),
    created_at       timestamp with time zone default now(),
    updated_at       timestamp with time zone default now(),
    constraint unique_external_mapping
        unique (external_id, external_type, external_source)
);

comment on table marketspy.external_product_mapping is 'Maps external identifiers to internal products';

-- Create indexes for external product mapping table
create index if not exists idx_mapping_external
    on marketspy.external_product_mapping (external_id, external_type);

create index if not exists idx_mapping_product
    on marketspy.external_product_mapping (product_id);

-- Create opportunities full view
create or replace view marketspy.opportunities_full
            (id, external_id, supplier_name, asin, upc, supplier_sku, amazon_title, supplier_product_name,
             supplier_title, size_tier, case_quantity, status, confidence_score, product_id, supplier_store_id,
             marketplace_store_id, import_batch_id, weight, dimensions, is_hazmat, available_quantity, package_quantity,
             weight_in_bundle, thumbnail_small_url, amazon_url, supplier_url, root_category_name, tags, map_price,
             total_cost, seller_price, lowest_price, lowest_fba_price, lowest_price_week_avg, lowest_price_month_avg,
             lowest_fba_price_week_avg, lowest_fba_price_month_avg, supplier_price, supplier_adjusted_price, sell_price,
             amazon_fees, amazon_fulfillment_fees, shipping_to_amazon, inbound_shipping, total_purchasing_cost,
             amazon_package_quantity, supplier_package_quantity, profit_amount, profit_fba_amount, roi_percentage,
             roi_fba_percentage, proceed_amount, proceed_fba_amount, pricing_date, total_seller_count, fba_seller_count,
             current_sales_rank, historical_min_rank, sales_rank_week_avg, sales_rank_month_avg, sales_rank_best,
             sold_by_amazon, created_at, updated_at)
as
SELECT o.id,
       o.external_id,
       o.supplier_name,
       o.asin,
       o.upc,
       o.supplier_sku,
       o.amazon_title,
       o.supplier_product_name,
       o.supplier_title,
       o.size_tier,
       o.case_quantity,
       o.status,
       o.confidence_score,
       o.product_id,
       o.supplier_store_id,
       o.marketplace_store_id,
       o.import_batch_id,
       o.weight,
       o.dimensions,
       o.is_hazmat,
       o.available_quantity,
       o.package_quantity,
       o.weight_in_bundle,
       o.thumbnail_small_url,
       o.amazon_url,
       o.supplier_url,
       o.root_category_name,
       o.tags,
       o.map_price,
       p.total_cost,
       p.seller_price,
       p.lowest_price,
       p.lowest_fba_price,
       p.lowest_price_week_avg,
       p.lowest_price_month_avg,
       p.lowest_fba_price_week_avg,
       p.lowest_fba_price_month_avg,
       p.supplier_price,
       p.supplier_adjusted_price,
       p.sell_price,
       p.amazon_fees,
       p.amazon_fulfillment_fees,
       p.shipping_to_amazon,
       p.inbound_shipping,
       p.total_purchasing_cost,
       p.amazon_package_quantity,
       p.supplier_package_quantity,
       p.profit_amount,
       p.profit_fba_amount,
       p.roi_percentage,
       p.roi_fba_percentage,
       p.proceed_amount,
       p.proceed_fba_amount,
       p.pricing_date,
       m.total_seller_count,
       m.fba_seller_count,
       m.current_sales_rank,
       m.historical_min_rank,
       m.sales_rank_week_avg,
       m.sales_rank_month_avg,
       m.sales_rank_best,
       m.sold_by_amazon,
       o.created_at,
       o.updated_at
FROM marketspy.opportunities o
         LEFT JOIN LATERAL ( SELECT opportunity_pricing.id,
                                    opportunity_pricing.opportunity_id,
                                    opportunity_pricing.total_cost,
                                    opportunity_pricing.seller_price,
                                    opportunity_pricing.lowest_price,
                                    opportunity_pricing.lowest_fba_price,
                                    opportunity_pricing.lowest_price_week_avg,
                                    opportunity_pricing.lowest_price_month_avg,
                                    opportunity_pricing.lowest_fba_price_week_avg,
                                    opportunity_pricing.lowest_fba_price_month_avg,
                                    opportunity_pricing.supplier_price,
                                    opportunity_pricing.supplier_adjusted_price,
                                    opportunity_pricing.sell_price,
                                    opportunity_pricing.amazon_fees,
                                    opportunity_pricing.amazon_fulfillment_fees,
                                    opportunity_pricing.shipping_to_amazon,
                                    opportunity_pricing.inbound_shipping,
                                    opportunity_pricing.total_purchasing_cost,
                                    opportunity_pricing.amazon_package_quantity,
                                    opportunity_pricing.supplier_package_quantity,
                                    opportunity_pricing.profit_amount,
                                    opportunity_pricing.profit_fba_amount,
                                    opportunity_pricing.roi_percentage,
                                    opportunity_pricing.roi_fba_percentage,
                                    opportunity_pricing.proceed_amount,
                                    opportunity_pricing.proceed_fba_amount,
                                    opportunity_pricing.currency_code,
                                    opportunity_pricing.pricing_date,
                                    opportunity_pricing.created_at,
                                    opportunity_pricing.updated_at
                             FROM marketspy.opportunity_pricing
                             WHERE opportunity_pricing.opportunity_id = o.id
                             ORDER BY opportunity_pricing.created_at DESC
                             LIMIT 1) p ON true
         LEFT JOIN LATERAL ( SELECT opportunity_market_data.id,
                                    opportunity_market_data.opportunity_id,
                                    opportunity_market_data.total_seller_count,
                                    opportunity_market_data.fba_seller_count,
                                    opportunity_market_data.sold_by_amazon,
                                    opportunity_market_data.current_sales_rank,
                                    opportunity_market_data.historical_min_rank,
                                    opportunity_market_data.sales_rank_week_avg,
                                    opportunity_market_data.sales_rank_month_avg,
                                    opportunity_market_data.sales_rank_best,
                                    opportunity_market_data.rank_category,
                                    opportunity_market_data.data_source,
                                    opportunity_market_data.created_at,
                                    opportunity_market_data.updated_at
                             FROM marketspy.opportunity_market_data
                             WHERE opportunity_market_data.opportunity_id = o.id
                             ORDER BY opportunity_market_data.created_at DESC
                             LIMIT 1) m ON true;

create or replace function marketspy.update_updated_at() returns trigger
    language plpgsql
as
$$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- Create triggers for updated_at
create trigger trigger_sources_updated_at
    before update
    on marketspy.sources
    for each row
execute procedure marketspy.update_updated_at();

create trigger trigger_opportunities_updated_at
    before update
    on marketspy.opportunities
    for each row
execute procedure marketspy.update_updated_at();

create trigger trigger_pricing_updated_at
    before update
    on marketspy.opportunity_pricing
    for each row
execute procedure marketspy.update_updated_at();

create trigger trigger_market_data_updated_at
    before update
    on marketspy.opportunity_market_data
    for each row
execute procedure marketspy.update_updated_at();

create trigger trigger_mapping_updated_at
    before update
    on marketspy.external_product_mapping
    for each row
execute procedure marketspy.update_updated_at();

-- Grant permissions to the schema
GRANT USAGE ON SCHEMA marketspy TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA marketspy TO anon, authenticated, service_role;
GRANT ALL ON ALL ROUTINES IN SCHEMA marketspy TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA marketspy TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA marketspy GRANT ALL ON TABLES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA marketspy GRANT ALL ON ROUTINES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA marketspy GRANT ALL ON SEQUENCES TO anon, authenticated, service_role;