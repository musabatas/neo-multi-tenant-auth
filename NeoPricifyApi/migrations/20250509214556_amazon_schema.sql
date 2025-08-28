-- Amazon Data Schema
create schema if not exists amazon_data;

-- Create enums for amazon_data schema
create type amazon_data.currencies as enum ('USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY', 'INR', 'MXN', 'BRL', 'ARS', 'CLP', 'COP', 'NZD', 'PLN', 'RUB', 'SAR', 'SEK', 'SGD', 'TRY', 'TWD', 'ZAR');

create type amazon_data.domains as enum ('amazon.com', 'amazon.ae', 'amazon.com.au', 'amazon.com.be', 'amazon.com.br', 'amazon.ca', 'amazon.de', 'amazon.es', 'amazon.fr', 'amazon.it', 'amazon.co.jp', 'amazon.com.mx', 'amazon.nl', 'amazon.pl', 'amazon.sa', 'amazon.se', 'amazon.sg', 'amazon.com.tr', 'amazon.co.uk');

create table if not exists amazon_data.products
(
    asin          varchar(16)                            not null
        constraint products_pkey
            primary key,
    title         text,
    description   text,
    image_url     text,
    identifiers   jsonb,
    root_category text,
    meta_data     jsonb,
    raw_data      jsonb,
    created_at    timestamp with time zone default now() not null,
    updated_at    timestamp with time zone default now() not null
);

create table if not exists amazon_data.product_marketplaces
(
    id         bigserial
        constraint product_marketplaces_pkey
            primary key,
    asin       varchar(16)                            not null
        constraint product_marketplaces_asin_fkey
            references amazon_data.products,
    domain     amazon_data.domains                    not null,
    url        text                                   not null,
    created_at timestamp with time zone default now() not null,
    updated_at timestamp with time zone default now() not null,
    constraint unique_asin_domain
        unique (asin, domain)
);

create table if not exists amazon_data.amazon_metrics
(
    product_marketplace_id       bigint                                 not null
        constraint amazon_metrics_pkey
            primary key
        constraint amazon_metrics_product_marketplace_id_fkey
            references amazon_data.product_marketplaces,
    sales_rank                   integer,
    sales_rank_7_days_avg        integer,
    sales_rank_30_days_avg       integer,
    sales_rank_90_days_avg       integer,
    sales_rank_365_days_avg      integer,
    sales_rank_best              integer,
    sold_by_amazon               boolean,
    sell_price                   numeric(10, 2),
    currency_code                amazon_data.currencies                 not null,
    is_prime                     boolean,
    is_fba                       boolean,
    bought_last_30_days          boolean,
    lowest_price                 numeric(10, 2),
    lowest_price_week_avg        numeric(10, 2),
    lowest_price_30_days_avg     numeric(10, 2),
    lowest_fba_price             numeric(10, 2),
    lowest_fba_price_week_avg    numeric(10, 2),
    lowest_fba_price_30_days_avg numeric(10, 2),
    offer_count                  integer,
    amazon_fee                   numeric(10, 2),
    fba_fee                      numeric(10, 2),
    shipping_fee                 numeric(10, 2),
    other_fee                    numeric(10, 2),
    total_fee                    numeric(10, 2) generated always as ((((amazon_fee + fba_fee) + shipping_fee) + other_fee)) stored,
    number_of_sellers            integer,
    number_of_reviews            integer,
    rating                       numeric(3, 2),
    created_at                   timestamp with time zone default now() not null,
    updated_at                   timestamp with time zone default now()
);

create index if not exists idx_amazon_metrics_currency_code
    on amazon_data.amazon_metrics (currency_code);

create index if not exists idx_amazon_metrics_product_marketplace_id
    on amazon_data.amazon_metrics (product_marketplace_id);

create index if not exists idx_amazon_metrics_rating
    on amazon_data.amazon_metrics (rating)
    where (rating IS NOT NULL);

create index if not exists idx_amazon_metrics_sales_rank
    on amazon_data.amazon_metrics (sales_rank)
    where (sales_rank IS NOT NULL);

create index if not exists idx_amazon_metrics_sell_price
    on amazon_data.amazon_metrics (sell_price)
    where (sell_price IS NOT NULL);

create table if not exists amazon_data.amazon_opportunities
(
    asin                        varchar(16)                            not null
        constraint amazon_opportunities_asin_fkey
            references amazon_data.products,
    from_domain                 amazon_data.domains                    not null,
    to_domain                   amazon_data.domains                    not null,
    from_product_marketplace_id bigint                                 not null
        constraint amazon_opportunities_from_product_marketplace_id_fkey
            references amazon_data.product_marketplaces,
    to_product_marketplace_id   bigint                                 not null
        constraint amazon_opportunities_to_product_marketplace_id_fkey
            references amazon_data.product_marketplaces,
    usd_profit                  numeric(10, 2),
    usd_profit_margin           numeric(10, 2),
    roi                         numeric(10, 2),
    created_at                  timestamp with time zone default now() not null,
    updated_at                  timestamp with time zone default now() not null,
    constraint amazon_opportunities_pkey
        primary key (asin, from_domain, to_domain)
);

create index if not exists idx_amazon_opportunities_asin
    on amazon_data.amazon_opportunities (asin);

create index if not exists idx_amazon_opportunities_from_domain
    on amazon_data.amazon_opportunities (from_domain);

create index if not exists idx_amazon_opportunities_roi
    on amazon_data.amazon_opportunities (roi);

create index if not exists idx_amazon_opportunities_to_domain
    on amazon_data.amazon_opportunities (to_domain);

create index if not exists idx_amazon_opportunities_usd_profit
    on amazon_data.amazon_opportunities (usd_profit);

create index if not exists idx_product_marketplaces_asin
    on amazon_data.product_marketplaces (asin);

create index if not exists idx_product_marketplaces_domain
    on amazon_data.product_marketplaces (domain);

create index if not exists idx_products_identifiers
    on amazon_data.products using gin (identifiers);

create or replace function amazon_data.get_product_prices_in_usd(p_asins text[] DEFAULT NULL::text[], p_domains amazon_data.domains[] DEFAULT NULL::amazon_data.domains[], p_min_price numeric DEFAULT NULL::numeric, p_max_price numeric DEFAULT NULL::numeric, p_min_usd_price numeric DEFAULT NULL::numeric, p_max_usd_price numeric DEFAULT NULL::numeric, p_limit integer DEFAULT 50, p_offset integer DEFAULT 0) returns jsonb
    language plpgsql
as
$$
DECLARE
    v_result JSONB;
BEGIN
    WITH base AS (
        SELECT
            pm.asin,
            pm.domain,
            am.sell_price AS original_price,
            am.currency_code,
            ROUND(
                CASE
                    WHEN am.currency_code = 'USD' THEN am.sell_price
                    ELSE am.sell_price / c.exchange_rate
                END,
                2
            ) AS usd_price
        FROM amazon_data.amazon_metrics am
        JOIN amazon_data.product_marketplaces pm
          ON am.product_marketplace_id = pm.id
        JOIN public.currencies c
          ON c.code = am.currency_code::text
        WHERE am.sell_price IS NOT NULL
          AND c.exchange_rate IS NOT NULL
          AND (p_asins IS NULL OR pm.asin = ANY(p_asins))
          AND (p_domains IS NULL OR pm.domain = ANY(p_domains))
          AND (p_min_price IS NULL OR am.sell_price >= p_min_price)
          AND (p_max_price IS NULL OR am.sell_price <= p_max_price)
          AND (
              p_min_usd_price IS NULL OR
              (CASE WHEN am.currency_code = 'USD' THEN am.sell_price ELSE am.sell_price / c.exchange_rate END) >= p_min_usd_price
          )
          AND (
              p_max_usd_price IS NULL OR
              (CASE WHEN am.currency_code = 'USD' THEN am.sell_price ELSE am.sell_price / c.exchange_rate END) <= p_max_usd_price
          )
    ),
    total_cte AS (
        SELECT COUNT(*) AS total_count FROM base
    ),
    data_cte AS (
        SELECT * FROM base
        ORDER BY usd_price DESC
        LIMIT p_limit OFFSET p_offset
    )
    SELECT jsonb_build_object(
        'data', COALESCE(jsonb_agg(
            jsonb_build_object(
                'asin', d.asin,
                'domain', d.domain,
                'original_price', d.original_price,
                'currency_code', d.currency_code,
                'usd_price', d.usd_price
            )
        ), '[]'::jsonb),
        'pagination', jsonb_build_object(
            'total_count', (SELECT total_count FROM total_cte),
            'page', (p_offset / p_limit) + 1,
            'page_size', p_limit,
            'total_pages', CEIL((SELECT total_count FROM total_cte)::NUMERIC / p_limit)::INT
        )
    )
    INTO v_result
    FROM data_cte d;

    RETURN v_result;
END;
$$;

GRANT USAGE ON SCHEMA amazon_data TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA amazon_data TO anon, authenticated, service_role;
GRANT ALL ON ALL ROUTINES IN SCHEMA amazon_data TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA amazon_data TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA amazon_data GRANT ALL ON TABLES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA amazon_data GRANT ALL ON ROUTINES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA amazon_data GRANT ALL ON SEQUENCES TO anon, authenticated, service_role;