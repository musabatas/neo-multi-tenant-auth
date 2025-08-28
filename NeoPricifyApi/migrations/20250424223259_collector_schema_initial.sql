-- Create schema for collector.
create schema if not exists collector;

-- Create enums for collector schema.
create type collector.crawl_status as enum ('pending', 'processing', 'completed', 'failed', 'discontinued', 'testing');

create type collector.crawler_config_status as enum ('ready', 'in_use', 'deprecated', 'disabled', 'testing');

create type collector.proxy_status_enum as enum ('in_use', 'pending', 'not_available');

create type collector.raw_data_type as enum ('product_data', 'product_price', 'product_inventory', 'full_data', 'product_search', 'brand', 'category', 'store', 'product_identifiers', 'search_data', 'other');

create type collector.crawler_task_status as enum ('pending', 'running', 'finished', 'error', 'cancelled');

-- Create API raw data table.
create table if not exists collector.api_raw_data
(
    id            bigserial
        constraint api_raw_data_pkey
            primary key,
    data_type     collector.raw_data_type                                            not null,
    api_id        text,
    website_id    integer
        constraint api_raw_data_website_id_fkey
            references public.websites,
    store_id      integer
        constraint api_raw_data_store_id_fkey
            references public.stores,
    raw_data      jsonb                    default '{}'::jsonb                       not null,
    sync_status   collector.crawl_status   default 'pending'::collector.crawl_status not null,
    error_message text,
    retry_count   integer                  default 0,
    last_retry_at timestamp with time zone,
    meta_data     jsonb                    default '{}'::jsonb,
    created_at    timestamp with time zone default CURRENT_TIMESTAMP,
    updated_at    timestamp with time zone default CURRENT_TIMESTAMP
)
    with (autovacuum_vacuum_scale_factor = 0.05, autovacuum_analyze_scale_factor = 0.02);

create index if not exists idx_api_raw_data_composite
    on collector.api_raw_data (data_type asc, sync_status asc, created_at desc) include (id);

create index if not exists idx_api_raw_data_latest
    on collector.api_raw_data (created_at desc) include (id, data_type, sync_status)
    where (sync_status = 'pending'::collector.crawl_status);

create unique index if not exists uniq_api_raw_data_store_api_type_partial
    on collector.api_raw_data (store_id, api_id, data_type)
    where ((store_id IS NOT NULL) AND (api_id IS NOT NULL) AND (data_type IS NOT NULL));

create table if not exists collector.available_spiders
(
    code        varchar(255)                           not null,
    description text,
    created_at  timestamp with time zone default now() not null
);

create table if not exists collector.barcode_lookup_results
(
    id            bigserial
        constraint barcode_lookup_results_pkey
            primary key,
    product_id    bigint                 not null
        constraint barcode_lookup_results_product_id_key
            unique
        constraint barcode_lookup_results_product_id_fkey
            references public.products
            on delete cascade,
    raw_data      jsonb                    default '{}'::jsonb,
    status        collector.crawl_status not null,
    error_message text,
    checked_at    timestamp with time zone default now(),
    created_at    timestamp with time zone default now(),
    updated_at    timestamp with time zone default now()
);

create index if not exists idx_barcode_lookup_results_product_id
    on collector.barcode_lookup_results (product_id);

create index if not exists idx_barcode_lookup_results_status
    on collector.barcode_lookup_results (status);

create table if not exists collector.proxies
(
    ip              varchar(45) not null,
    port            integer     not null,
    protocols       text[],
    country_code    varchar(10),
    city            text,
    asn             text,
    org             text,
    isp             text,
    anonymity_level varchar(20),
    latency         numeric(10, 3),
    speed           integer,
    last_checked_at timestamp with time zone,
    api_created_at  timestamp with time zone,
    api_updated_at  timestamp with time zone,
    last_scraped_at timestamp with time zone    default now(),
    username        text,
    password        text,
    source          varchar(50),
    status          collector.proxy_status_enum default 'pending'::collector.proxy_status_enum,
    constraint proxies_pkey
        primary key (ip, port)
);

create index if not exists idx_proxies_anonymity
    on collector.proxies (anonymity_level);

create index if not exists idx_proxies_country
    on collector.proxies (country_code);

create index if not exists idx_proxies_last_checked
    on collector.proxies (last_checked_at desc);

create index if not exists idx_proxies_protocols
    on collector.proxies using gin (protocols);

create index if not exists idx_proxies_status
    on collector.proxies (status);

create table if not exists collector.spider_configurations
(
    id           bigserial
        constraint spider_configurations_pkey
            primary key,
    environment  varchar(50)                     default 'default'::character varying             not null,
    spider_name  varchar(255)                    default 'default'::character varying             not null,
    config_key   varchar(255)                                                                     not null,
    config_value jsonb,
    description  text,
    status       collector.crawler_config_status default 'ready'::collector.crawler_config_status not null,
    is_active    boolean                         default true                                     not null,
    is_secret    boolean                         default false                                    not null,
    created_at   timestamp with time zone        default now(),
    updated_at   timestamp with time zone        default now(),
    constraint spider_configurations_env_spider_key_key
        unique (environment, spider_name, config_key)
);

create index if not exists idx_spider_configurations_lookup
    on collector.spider_configurations (environment, spider_name, status, is_active);

create index if not exists idx_spider_configurations_status
    on collector.spider_configurations (status);

create table if not exists collector.temp_product_ids
(
    product_id    text                                                               not null
        constraint temp_product_ids_pkey
            primary key,
    product_url   text,
    website_id    integer
        constraint temp_product_ids_website_id_fkey
            references public.websites,
    status        collector.crawl_status   default 'pending'::collector.crawl_status not null,
    error_message text,
    created_at    timestamp with time zone default now(),
    retry_count   integer                  default 0,
    last_retry_at timestamp with time zone
);

create index if not exists idx_temp_product_ids_website
    on collector.temp_product_ids (website_id asc, created_at desc);

create table if not exists collector.crawlab_instances
(
    id          smallserial
        constraint crawlab_instances_pkey
            primary key,
    name        text                                   not null,
    description text,
    api_url     text                                   not null,
    api_token   text                                   not null,
    is_active   boolean                  default true  not null,
    is_deleted  boolean                  default false not null,
    created_at  timestamp with time zone default now() not null,
    updated_at  timestamp with time zone default now(),
    is_default  boolean                  default false not null
);

comment on column collector.crawlab_instances.is_default is 'Flag indicating if this is the default instance to use';

create unique index if not exists idx_crawlab_instances_is_default
    on collector.crawlab_instances (is_default)
    where (is_default = true);

create table if not exists collector.spiders
(
    id             serial
        constraint spiders_pkey
            primary key,
    code           text                                   not null
        constraint spiders_code_key
            unique,
    description    text,
    default_config jsonb,
    created_at     timestamp with time zone default now() not null,
    updated_at     timestamp with time zone default now()
);

create table if not exists collector.crawlab_spiders
(
    instance_id        smallserial
        constraint crawlab_spiders_instance_id_fkey
            references collector.crawlab_instances
            on delete cascade,
    spider_id          serial
        constraint crawlab_spiders_spider_id_fkey
            references collector.spiders
            on delete cascade,
    instance_spider_id text                                   not null,
    config             jsonb                    default '{}'::jsonb,
    is_active          boolean                  default true  not null,
    created_at         timestamp with time zone default now() not null,
    updated_at         timestamp with time zone default now(),
    constraint crawlab_spiders_pkey
        primary key (instance_id, spider_id)
);

create table if not exists collector.website_spiders
(
    id         serial
        constraint website_spiders_pkey
            primary key,
    website_id serial
        constraint website_spiders_website_id_fkey
            references public.websites
            on delete cascade,
    spider_id  serial
        constraint website_spiders_spider_id_fkey
            references collector.spiders
            on delete cascade,
    config     jsonb                    default '{}'::jsonb,
    is_enabled boolean                  default true  not null,
    created_at timestamp with time zone default now() not null,
    updated_at timestamp with time zone default now(),
    is_default boolean                  default false not null,
    constraint unique_website_spider
        unique (website_id, spider_id)
);

comment on column collector.website_spiders.is_default is 'Flag indicating if this is the default spider for the website';

create unique index if not exists idx_website_spiders_website_id_is_default
    on collector.website_spiders (website_id, is_default)
    where (is_default = true);

create table if not exists collector.crawler_tasks
(
    task_id           text                                        not null
        constraint crawler_tasks_pkey
            primary key,
    website_spider_id serial
        constraint crawler_tasks_website_spider_id_fkey
            references collector.website_spiders
            on delete cascade,
    command           text                                        not null,
    params            text,
    status            collector.crawler_task_status default 'pending'::collector.crawler_task_status,
    data_downloaded   boolean                       default false not null,
    error_message     text,
    logs_url          text,
    results_url       text,
    created_at        timestamp with time zone      default now() not null,
    updated_at        timestamp with time zone      default now(),
    instance_id       smallint
        constraint crawler_tasks_instance_id_fkey
            references collector.crawlab_instances
            on delete set null,
    stats             jsonb                         default '{}'::jsonb
);

comment on column collector.crawler_tasks.instance_id is 'Reference to the Crawlab instance that executed this task';

create index if not exists idx_crawler_tasks_ws_id_updated_at
    on collector.crawler_tasks (website_spider_id asc, updated_at desc);

create index if not exists idx_crawler_tasks_instance_id
    on collector.crawler_tasks (instance_id);

create table if not exists collector.builtwith_reports
(
    id                serial
        constraint builtwith_reports_pkey
            primary key,
    domain            text                    not null
        constraint builtwith_reports_domain_key
            unique,
    location_on_site  text,
    tech_spend_usd    numeric,
    sales_revenue_usd numeric,
    social            text,
    employees         numeric,
    company           text,
    vertical          text,
    tranco            text,
    page_rank         text,
    majestic          text,
    umbrella          text,
    telephones        text,
    emails            text,
    twitter           text,
    facebook          text,
    linkedin          text,
    google            text,
    pinterest         text,
    github            text,
    instagram         text,
    vk                text,
    vimeo             text,
    youtube           text,
    tiktok            text,
    threads           text,
    x                 text,
    people            text,
    city              text,
    state             text,
    zip               text,
    country           text,
    first_detected    date,
    last_found        date,
    first_indexed     date,
    last_indexed      date,
    exclusion         text,
    compliance        text,
    created_at        timestamp default CURRENT_TIMESTAMP,
    is_processed      boolean   default false not null
);

create index if not exists idx_builtwith_domain
    on collector.builtwith_reports (domain);

create index if not exists idx_builtwith_company
    on collector.builtwith_reports (company);

create index if not exists idx_builtwith_country
    on collector.builtwith_reports (country);

create index if not exists idx_builtwith_sales_revenue
    on collector.builtwith_reports (sales_revenue_usd);

create index if not exists idx_builtwith_tech_spend
    on collector.builtwith_reports (tech_spend_usd);

create or replace function collector.get_spiders_list(p_limit integer DEFAULT 25, p_offset integer DEFAULT 0, p_sort_by text DEFAULT 'code'::text, p_sort_direction text DEFAULT 'asc'::text) returns jsonb
    language plpgsql
as
$$
DECLARE
    v_total_count integer;
    v_result jsonb;
BEGIN
    -- Base query with all necessary joins and calculations
    WITH base_query AS (
        SELECT 
            s.id,
            s.code,
            s.description,
            s.default_config,
            s.created_at,
            s.updated_at,
            -- Count of websites using this spider
            COUNT(DISTINCT ws.website_id) as website_count,
            -- Last run date from tasks
            MAX(ct.created_at) as last_run_date,
            -- Success rate calculation
            ROUND(
                CAST(COUNT(CASE WHEN ct.status = 'finished' THEN 1 END) AS numeric) /
                NULLIF(COUNT(ct.task_id), 0) * 100,
                2
            ) as success_rate,
            -- Count of instances this spider is configured on
            COUNT(DISTINCT cs.instance_id) as instance_count
        FROM collector.spiders s
        LEFT JOIN collector.website_spiders ws ON ws.spider_id = s.id
        LEFT JOIN collector.crawlab_spiders cs ON cs.spider_id = s.id
        LEFT JOIN collector.crawler_tasks ct ON ct.website_spider_id = ws.id
        GROUP BY s.id, s.code, s.description, s.default_config, s.created_at, s.updated_at
    ),
    -- Get total count
    total_cte AS (
        SELECT COUNT(*) as total_count FROM base_query
    ),
    -- Get paginated and sorted data
    data_cte AS (
        SELECT *
        FROM base_query
        ORDER BY
            CASE 
                WHEN p_sort_by = 'code' AND p_sort_direction = 'asc' THEN code END ASC,
            CASE 
                WHEN p_sort_by = 'code' AND p_sort_direction = 'desc' THEN code END DESC,
            CASE 
                WHEN p_sort_by = 'website_count' AND p_sort_direction = 'asc' THEN website_count END ASC,
            CASE 
                WHEN p_sort_by = 'website_count' AND p_sort_direction = 'desc' THEN website_count END DESC,
            CASE 
                WHEN p_sort_by = 'last_run_date' AND p_sort_direction = 'asc' THEN last_run_date END ASC,
            CASE 
                WHEN p_sort_by = 'last_run_date' AND p_sort_direction = 'desc' THEN last_run_date END DESC,
            CASE 
                WHEN p_sort_by = 'success_rate' AND p_sort_direction = 'asc' THEN success_rate END ASC,
            CASE 
                WHEN p_sort_by = 'success_rate' AND p_sort_direction = 'desc' THEN success_rate END DESC,
            CASE 
                WHEN p_sort_by = 'instance_count' AND p_sort_direction = 'asc' THEN instance_count END ASC,
            CASE 
                WHEN p_sort_by = 'instance_count' AND p_sort_direction = 'desc' THEN instance_count END DESC,
            CASE 
                WHEN p_sort_by = 'created_at' AND p_sort_direction = 'asc' THEN created_at END ASC,
            CASE 
                WHEN p_sort_by = 'created_at' AND p_sort_direction = 'desc' THEN created_at END DESC,
            CASE 
                WHEN p_sort_by = 'updated_at' AND p_sort_direction = 'asc' THEN updated_at END ASC,
            CASE 
                WHEN p_sort_by = 'updated_at' AND p_sort_direction = 'desc' THEN updated_at END DESC
        LIMIT p_limit
        OFFSET p_offset
    )
    -- Combine total count with paginated data
    SELECT 
        jsonb_build_object(
            'total_count', (SELECT total_count FROM total_cte),
            'data', COALESCE(
                (
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'id', id,
                            'code', code,
                            'description', description,
                            'default_config', default_config,
                            'created_at', created_at,
                            'updated_at', updated_at,
                            'website_count', website_count,
                            'last_run_date', last_run_date,
                            'success_rate', success_rate,
                            'instance_count', instance_count
                        )
                    )
                    FROM data_cte
                ),
                '[]'::jsonb
            )
        )
    INTO v_result;

    RETURN v_result;
END;
$$;

create or replace function collector.get_crawlab_instances_with_relations(p_search text DEFAULT NULL::text, p_active_only boolean DEFAULT true, p_deleted_only boolean DEFAULT false, p_page integer DEFAULT 1, p_page_size integer DEFAULT 25, p_sort_by text DEFAULT 'created_at'::text, p_sort_direction text DEFAULT 'desc'::text) returns jsonb
    language plpgsql
as
$$
DECLARE
    v_result JSONB;
    v_offset INT;
BEGIN
    v_offset := (p_page - 1) * p_page_size;

    WITH base AS (
        SELECT 
            ci.id,
            ci.name,
            ci.description,
            ci.api_url,
            ci.api_token,
            ci.is_active,
            ci.is_deleted,
            ci.created_at,
            ci.updated_at,
            (
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'spider_id', cs.spider_id,
                        'instance_spider_id', cs.instance_spider_id,
                        'config', cs.config,
                        'is_active', cs.is_active,
                        'created_at', cs.created_at,
                        'updated_at', cs.updated_at,
                        'spider', jsonb_build_object(
                            'id', s.id,
                            'code', s.code,
                            'description', s.description,
                            'default_config', s.default_config,
                            'created_at', s.created_at,
                            'updated_at', s.updated_at
                        )
                    )
                )
                FROM collector.crawlab_spiders cs
                JOIN collector.spiders s ON s.id = cs.spider_id
                WHERE cs.instance_id = ci.id
            ) AS spiders
        FROM collector.crawlab_instances ci
        WHERE (p_active_only IS FALSE OR ci.is_active = TRUE)
          AND (p_deleted_only IS FALSE OR ci.is_deleted = TRUE)
          AND (
            p_search IS NULL OR
            ci.name ILIKE '%' || p_search || '%' OR
            ci.description ILIKE '%' || p_search || '%' OR
            ci.api_url ILIKE '%' || p_search || '%'
          )
    ),
    total_cte AS (
        SELECT count(*) AS total_count FROM base
    ),
    data_cte AS (
        SELECT * FROM base
        ORDER BY 
            CASE WHEN p_sort_by = 'name' AND p_sort_direction = 'asc' THEN name END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'name' AND p_sort_direction = 'desc' THEN name END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'created_at' AND p_sort_direction = 'asc' THEN created_at END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'created_at' AND p_sort_direction = 'desc' THEN created_at END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'updated_at' AND p_sort_direction = 'asc' THEN updated_at END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'updated_at' AND p_sort_direction = 'desc' THEN updated_at END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'id' OR p_sort_by IS NULL THEN id END DESC NULLS LAST
        LIMIT p_page_size OFFSET v_offset
    )
    SELECT jsonb_build_object(
        'data', COALESCE(jsonb_agg(
            jsonb_build_object(
                'id', d.id,
                'name', d.name,
                'description', d.description,
                'api_url', d.api_url,
                'is_active', d.is_active,
                'is_deleted', d.is_deleted,
                'created_at', d.created_at,
                'updated_at', d.updated_at,
                'spiders', COALESCE(d.spiders, '[]'::jsonb)
            )
        ), '[]'::jsonb),
        'pagination', jsonb_build_object(
            'total_count', (SELECT total_count FROM total_cte),
            'page_size', p_page_size,
            'page', p_page,
            'total_pages', CEIL((SELECT total_count FROM total_cte)::float / p_page_size)::INTEGER
        ),
        'sorting', jsonb_build_object(
            'fields', ARRAY['id', 'name', 'created_at', 'updated_at'],
            'directions', ARRAY['asc', 'desc']
        )
    )
    INTO v_result
    FROM data_cte d;

    RETURN v_result;
END;
$$;

create or replace function collector.get_spider_details_with_websites_and_instances(p_spider_id integer, p_website_ids integer[] DEFAULT NULL::integer[], p_page integer DEFAULT 1, p_page_size integer DEFAULT 25, p_sort_by text DEFAULT 'created_at'::text, p_sort_direction text DEFAULT 'desc'::text) returns jsonb
    language plpgsql
as
$$
DECLARE
    v_result JSONB;
    v_offset INT;
BEGIN
    IF p_spider_id IS NULL THEN
        RAISE EXCEPTION 'p_spider_id cannot be null';
    END IF;

    v_offset := (p_page - 1) * p_page_size;

    WITH spider_base AS (
        SELECT
            s.id,
            s.code,
            s.description,
            s.default_config,
            s.created_at,
            s.updated_at
        FROM collector.spiders s
        WHERE s.id = p_spider_id
    ),
    website_spiders_base AS (
        SELECT
            ws.id,
            ws.website_id,
            ws.config,
            ws.is_enabled,
            ws.created_at,
            ws.updated_at,
            w.name AS website_name,
            w.url AS website_url,
            w.logo_url AS website_logo,
            w.is_active AS website_is_active
        FROM collector.website_spiders ws
        JOIN public.websites w ON w.id = ws.website_id
        WHERE ws.spider_id = p_spider_id
          AND (p_website_ids IS NULL OR ws.website_id = ANY(p_website_ids))
    ),
    total_cte AS (
        SELECT count(*) AS total_count FROM website_spiders_base
    ),
    website_data_cte AS (
        SELECT * FROM website_spiders_base
        ORDER BY 
            CASE WHEN p_sort_by = 'website_name' AND p_sort_direction = 'asc' THEN website_name END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'website_name' AND p_sort_direction = 'desc' THEN website_name END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'created_at' AND p_sort_direction = 'asc' THEN created_at END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'created_at' AND p_sort_direction = 'desc' THEN created_at END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'updated_at' AND p_sort_direction = 'asc' THEN updated_at END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'updated_at' AND p_sort_direction = 'desc' THEN updated_at END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'id' OR p_sort_by IS NULL THEN id END DESC NULLS LAST
        LIMIT p_page_size OFFSET v_offset
    ),
    spider_instances AS (
        SELECT
            cs.instance_id,
            cs.instance_spider_id,
            cs.config,
            cs.is_active,
            cs.created_at,
            cs.updated_at,
            ci.name AS instance_name,
            ci.api_url AS instance_api_url,
            ci.is_active AS instance_is_active
        FROM collector.crawlab_spiders cs
        JOIN collector.crawlab_instances ci ON ci.id = cs.instance_id
        WHERE cs.spider_id = p_spider_id
    )
    SELECT jsonb_build_object(
        'data', jsonb_build_object(
            'spider', (
                SELECT jsonb_build_object(
                    'id', sb.id,
                    'code', sb.code,
                    'description', sb.description,
                    'default_config', sb.default_config,
                    'created_at', sb.created_at,
                    'updated_at', sb.updated_at
                )
                FROM spider_base sb
            ),
            'website_spiders', COALESCE(jsonb_agg(
                jsonb_build_object(
                    'id', wd.id,
                    'website', jsonb_build_object(
                        'id', wd.website_id,
                        'name', wd.website_name,
                        'url', wd.website_url,
                        'logo_url', wd.website_logo,
                        'is_active', wd.website_is_active
                    ),
                    'config', wd.config,
                    'is_enabled', wd.is_enabled,
                    'created_at', wd.created_at,
                    'updated_at', wd.updated_at
                )
            ) FILTER (WHERE wd.id IS NOT NULL), '[]'::jsonb),
            'instances', COALESCE((
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'instance_id', si.instance_id,
                        'instance_spider_id', si.instance_spider_id,
                        'config', si.config,
                        'is_active', si.is_active,
                        'created_at', si.created_at,
                        'updated_at', si.updated_at,
                        'instance', jsonb_build_object(
                            'name', si.instance_name,
                            'api_url', si.instance_api_url,
                            'is_active', si.instance_is_active
                        )
                    )
                ) FROM spider_instances si
            ), '[]'::jsonb)
        ),
        'pagination', jsonb_build_object(
            'total_count', (SELECT total_count FROM total_cte),
            'page_size', p_page_size,
            'page', p_page,
            'total_pages', CEIL((SELECT total_count FROM total_cte)::float / p_page_size)::INTEGER
        ),
        'sorting', jsonb_build_object(
            'fields', ARRAY['id', 'website_name', 'created_at', 'updated_at'],
            'directions', ARRAY['asc', 'desc']
        )
    )
    INTO v_result
    FROM website_data_cte wd;

    RETURN v_result;
END;
$$;

create or replace function collector.get_spiders_with_relations(p_search text DEFAULT NULL::text, p_active_only boolean DEFAULT true, p_website_ids integer[] DEFAULT NULL::integer[], p_page integer DEFAULT 1, p_page_size integer DEFAULT 25, p_sort_by text DEFAULT 'created_at'::text, p_sort_direction text DEFAULT 'desc'::text) returns jsonb
    language plpgsql
as
$$
DECLARE
    v_result JSONB;
    v_offset INT;
BEGIN
    v_offset := (p_page - 1) * p_page_size;

    WITH base AS (
        SELECT 
            s.id,
            s.code,
            s.description,
            s.default_config,
            s.created_at,
            s.updated_at,
            (
                SELECT COUNT(*)
                FROM collector.website_spiders ws
                WHERE ws.spider_id = s.id
                AND (p_website_ids IS NULL OR ws.website_id = ANY(p_website_ids))
            ) AS website_count
        FROM collector.spiders s
        WHERE (
            p_search IS NULL OR
            s.code ILIKE '%' || p_search || '%' OR
            s.description ILIKE '%' || p_search || '%'
        )
        AND (p_active_only IS FALSE OR EXISTS (
            SELECT 1 FROM collector.website_spiders ws
            WHERE ws.spider_id = s.id AND ws.is_enabled = TRUE
        ))
        AND (p_website_ids IS NULL OR EXISTS (
            SELECT 1 FROM collector.website_spiders ws_filter
            WHERE ws_filter.spider_id = s.id
            AND ws_filter.website_id = ANY(p_website_ids)
        ))
    ),
    total_cte AS (
        SELECT count(*) AS total_count FROM base
    ),
    data_cte AS (
        SELECT * FROM base
        ORDER BY
            CASE WHEN p_sort_by = 'id' THEN id END,
            CASE WHEN p_sort_by = 'code' THEN code END,
            CASE WHEN p_sort_by = 'created_at' THEN created_at END,
            CASE WHEN p_sort_by = 'updated_at' THEN updated_at END
        -- Direction handling after the field selection:
        -- This way planner orders by dynamic column
        -- Direction applied on planner level.
        -- Safe fallback to id DESC for NULL sort_by.
        -- Safe NULLS handling.
        ,
        id DESC
        LIMIT p_page_size OFFSET v_offset
    )
    SELECT jsonb_build_object(
        'data', COALESCE(jsonb_agg(
            jsonb_build_object(
                'id', d.id,
                'code', d.code,
                'description', d.description,
                'default_config', d.default_config,
                'created_at', d.created_at,
                'updated_at', d.updated_at,
                'website_count', d.website_count
            )
        ), '[]'::jsonb),
        'pagination', jsonb_build_object(
            'total_count', (SELECT total_count FROM total_cte),
            'page_size', p_page_size,
            'page', p_page,
            'total_pages', CEIL((SELECT total_count FROM total_cte)::float / p_page_size)::INTEGER
        ),
        'sorting', jsonb_build_object(
            'fields', ARRAY['id', 'code', 'created_at', 'updated_at'],
            'directions', ARRAY['asc', 'desc']
        )
    )
    INTO v_result
    FROM data_cte d;

    RETURN v_result;
END;
$$;

create or replace function collector.get_website_spiders_with_instances(p_website_id integer) returns jsonb
    language plpgsql
as
$$
DECLARE
    v_result jsonb;
BEGIN
    -- Website data
    WITH website_data AS (
        SELECT
            w.id,
            w.name,
            w.url,
            w.logo_url,
            w.is_active,
            w.crawler_meta,
            w.default_currency_code
        FROM public.websites w
        WHERE w.id = p_website_id AND w.is_deleted = false
    ),
    
    -- Website spiders data
    website_spiders AS (
        SELECT
            ws.id AS website_spider_id,
            ws.spider_id,
            s.code,
            s.description,
            s.default_config,
            ws.config AS website_config,
            ws.is_enabled,
            ws.is_default
        FROM collector.website_spiders ws
        JOIN collector.spiders s ON s.id = ws.spider_id
        WHERE ws.website_id = p_website_id
    ),
    
    -- Crawlab instances with spiders
    instances AS (
        SELECT
            ci.id,
            ci.name,
            ci.description,
            ci.api_url,
            ci.api_token,
            ci.is_active,
            ci.is_default,
            (
                SELECT
                    COALESCE(jsonb_agg(
                        jsonb_build_object(
                            'spider_id', cs.spider_id,
                            'instance_spider_id', cs.instance_spider_id,
                            'config', cs.config
                        )
                    ), '[]'::jsonb)
                FROM collector.crawlab_spiders cs
                WHERE cs.instance_id = ci.id
                AND cs.is_active = true
                AND EXISTS (
                    -- Only include spiders associated with this website
                    SELECT 1 FROM collector.website_spiders ws
                    WHERE ws.website_id = p_website_id
                    AND ws.spider_id = cs.spider_id
                )
            ) AS spiders
        FROM collector.crawlab_instances ci
        WHERE ci.is_active = true
        AND ci.is_deleted = false
    ),
    
    -- Success rates calculation
    instance_success_rates AS (
        SELECT
            ct.instance_id,
            ROUND(
                CAST(COUNT(CASE WHEN ct.status = 'finished' THEN 1 END) AS numeric) /
                NULLIF(COUNT(ct.task_id), 0) * 100,
                2
            ) as success_rate
        FROM collector.crawler_tasks ct
        JOIN collector.website_spiders ws ON ws.id = ct.website_spider_id
        WHERE ws.website_id = p_website_id
        GROUP BY ct.instance_id
    )
    
    -- Build final result
    SELECT jsonb_build_object(
        'website', CASE 
            WHEN EXISTS (SELECT 1 FROM website_data) THEN
                (
                    SELECT jsonb_build_object(
                        'id', wd.id,
                        'name', wd.name,
                        'url', wd.url,
                        'logo_url', wd.logo_url,
                        'is_active', wd.is_active,
                        'crawler_meta', wd.crawler_meta,
                        'default_currency_code', wd.default_currency_code
                    )
                    FROM website_data wd
                )
            ELSE NULL
        END,
        'spiders', COALESCE(
            (
                SELECT jsonb_agg(ws.*)
                FROM website_spiders ws
            ),
            '[]'::jsonb
        ),
        'instances', COALESCE(
            (
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'id', i.id,
                        'name', i.name,
                        'description', i.description,
                        'api_url', i.api_url,
                        'api_token', i.api_token,
                        'is_active', i.is_active,
                        'is_default', i.is_default,
                        'success_rate', sr.success_rate,
                        'spiders', i.spiders
                    )
                )
                FROM instances i
                LEFT JOIN instance_success_rates sr ON sr.instance_id = i.id
                WHERE EXISTS (
                    SELECT 1 
                    FROM jsonb_array_elements(i.spiders) AS spider_elem
                    -- Only include instances that have at least one compatible spider
                )
            ),
            '[]'::jsonb
        )
    ) INTO v_result;

    RETURN v_result;
END;
$$;

create or replace function collector.get_builtwith_reports_json(p_country text DEFAULT NULL::text, p_company text DEFAULT NULL::text, p_domain text DEFAULT NULL::text, p_is_processed boolean DEFAULT NULL::boolean, p_sort_by text DEFAULT 'domain_asc'::text, p_limit integer DEFAULT 50, p_offset integer DEFAULT 0) returns jsonb
    language plpgsql
as
$$
DECLARE
    result JSONB;
BEGIN
    WITH base AS (
        SELECT
            id,
            domain,
            location_on_site,
            tech_spend_usd,
            sales_revenue_usd,
            social,
            employees,
            company,
            vertical,
            tranco,
            page_rank,
            majestic,
            umbrella,
            telephones,
            emails,
            twitter,
            facebook,
            linkedin,
            google,
            pinterest,
            github,
            instagram,
            vk,
            vimeo,
            youtube,
            tiktok,
            threads,
            x,
            people,
            city,
            state,
            zip,
            country,
            first_detected,
            last_found,
            first_indexed,
            last_indexed,
            exclusion,
            compliance,
            is_processed,  -- Added field
            created_at
        FROM collector.builtwith_reports
        WHERE (p_country IS NULL OR country ILIKE p_country)
          AND (p_company IS NULL OR company ILIKE p_company)
          AND (p_domain IS NULL OR domain ILIKE p_domain)
          AND (p_is_processed IS NULL OR is_processed = p_is_processed)  -- Optional filter
    ),
    total_cte AS (
        SELECT COUNT(*) AS total_count FROM base
    ),
    data_cte AS (
        SELECT * FROM base
        ORDER BY
            CASE WHEN p_sort_by = 'domain_asc' THEN domain END ASC,
            CASE WHEN p_sort_by = 'domain_desc' THEN domain END DESC,
            CASE WHEN p_sort_by = 'sales_revenue_asc' THEN sales_revenue_usd END ASC,
            CASE WHEN p_sort_by = 'sales_revenue_desc' THEN sales_revenue_usd END DESC,
            CASE WHEN p_sort_by = 'tech_spend_asc' THEN tech_spend_usd END ASC,
            CASE WHEN p_sort_by = 'tech_spend_desc' THEN tech_spend_usd END DESC,
            CASE WHEN p_sort_by = 'company_asc' THEN company END ASC,
            CASE WHEN p_sort_by = 'company_desc' THEN company END DESC,
            CASE WHEN p_sort_by = 'created_at_asc' THEN created_at END ASC,
            CASE WHEN p_sort_by = 'created_at_desc' THEN created_at END DESC
        LIMIT p_limit OFFSET p_offset
    )
    SELECT jsonb_build_object(
        'total_count', (SELECT total_count FROM total_cte),
        'data', COALESCE(jsonb_agg(to_jsonb(data_cte)), '[]'::jsonb)
    )
    INTO result
    FROM data_cte;

    RETURN COALESCE(result, jsonb_build_object('total_count', 0, 'data', '[]'::jsonb));
END;
$$;

GRANT USAGE ON SCHEMA collector TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA collector TO anon, authenticated, service_role;
GRANT ALL ON ALL ROUTINES IN SCHEMA collector TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA collector TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA collector GRANT ALL ON TABLES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA collector GRANT ALL ON ROUTINES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA collector GRANT ALL ON SEQUENCES TO anon, authenticated, service_role;