-- Create addresses table.
create table if not exists public.addresses
(
    id              bigserial
        constraint addresses_pkey
            primary key,
    street          varchar(255)             default NULL::character varying,
    city            varchar(255),
    state           varchar(255)             default NULL::character varying,
    postal_code     varchar(20),
    country_code    varchar(2) not null
        constraint addresses_country_code_fkey
            references public.countries,
    additional_info text,
    latitude        numeric(9, 6),
    longitude       numeric(9, 6),
    created_at      timestamp with time zone default now(),
    updated_at      timestamp with time zone
);

-- Create indexes for addresses table.
create index if not exists idx_addresses_geo
    on public.addresses (latitude, longitude)
    where ((latitude IS NOT NULL) AND (longitude IS NOT NULL));

-- Create vendors table.
create table if not exists public.vendors
(
    id           serial
        constraint vendors_pkey
            primary key,
    name         varchar(255)                                 not null,
    country_code char(2)
        constraint vendors_country_code_fkey
            references public.countries,
    website_url  text,
    logo_url     text,
    meta_data    jsonb                    default '{}'::jsonb not null,
    is_deleted   boolean                  default false,
    created_at   timestamp with time zone default now(),
    updated_at   timestamp with time zone,
    deleted_at   timestamp with time zone,
    is_active    boolean                  default true        not null,
    constraint check_deleted_status
        check ((deleted_at IS NULL) = (is_deleted = false))
);

-- Create indexes for vendors table.
create unique index if not exists unique_vendor_name
    on public.vendors (name)
    where ((deleted_at IS NULL) AND (is_deleted = false));

create index if not exists idx_vendors_name_lower
    on public.vendors (lower(name::text))
    where ((deleted_at IS NULL) AND (is_deleted = false));

-- Create websites table.
create table if not exists public.websites
(
    id                    serial
        constraint websites_pkey
            primary key,
    vendor_id             integer
        constraint websites_vendor_id_fkey
            references public.vendors,
    code                  varchar(255),
    name                  varchar(255)                                       not null,
    description           text,
    url                   varchar(255),
    is_active             boolean                  default true,
    logo_url              text,
    meta_data             jsonb                    default '{}'::jsonb       not null,
    crawler_meta          jsonb                    default '{}'::jsonb       not null,
    deleted_at            timestamp with time zone,
    is_deleted            boolean                  default false,
    created_at            timestamp with time zone default CURRENT_TIMESTAMP not null,
    updated_at            timestamp with time zone,
    default_currency_code char(3)
        constraint websites_default_currency_code_fkey
            references public.currencies,
    constraint check_deleted_status_websites
        check ((deleted_at IS NULL) = (is_deleted = false))
);

-- Create indexes for websites table.
create index if not exists idx_websites_vendor
    on public.websites (vendor_id)
    where ((deleted_at IS NULL) AND (is_deleted = false) AND (is_active = true));

create index if not exists idx_websites_code_lower
    on public.websites (lower(code::text))
    where ((deleted_at IS NULL) AND (is_deleted = false));

-- Create unique index for websites table.
create unique index if not exists unique_website_code
    on public.websites (code)
    where ((deleted_at IS NULL) AND (is_deleted = false) AND (is_active = true));

-- Create stores table.
create table if not exists public.stores
(
    id                    serial
        constraint stores_pkey
            primary key,
    website_id            integer
        constraint stores_website_id_fkey
            references public.websites,
    name                  varchar(255),
    code                  varchar(100),
    api_code              varchar(100),
    phone                 varchar(50),
    address_id            bigint
        constraint stores_address_id_fkey
            references public.addresses,
    default_currency_code char(3)
        constraint stores_default_currency_code_fkey
            references public.currencies,
    is_active             boolean                  default true,
    is_default            boolean                  default false,
    is_reference_store    boolean                  default false,
    reference_priority    smallint                 default 0,
    meta_data             jsonb                    default '{}'::jsonb not null,
    crawler_meta          jsonb                    default '{}'::jsonb not null,
    deleted_reason        text,
    is_deleted            boolean                  default false,
    created_at            timestamp with time zone default now(),
    updated_at            timestamp with time zone,
    deleted_at            timestamp with time zone,
    constraint check_deleted_status_stores
        check ((deleted_at IS NULL) = (is_deleted = false))
);

create index if not exists idx_stores_code_active
    on public.stores (code, is_active, api_code)
    where ((is_deleted = false) AND (is_active = true));

create index if not exists idx_stores_website
    on public.stores (website_id)
    where ((deleted_at IS NULL) AND (is_deleted = false) AND (is_active = true));

create unique index if not exists unique_default_store_per_website
    on public.stores (website_id)
    where ((is_default = true) AND (deleted_at IS NULL) AND (is_deleted = false) AND (is_active = true));

create unique index if not exists unique_store_code_per_website
    on public.stores (website_id, code)
    where ((deleted_at IS NULL) AND (is_deleted = false) AND (is_active = true));

create index if not exists idx_stores_api_code
    on public.stores (api_code)
    where ((deleted_at IS NULL) AND (is_deleted = false) AND (is_active = true));

-- Create categories table.
create table if not exists public.categories
(
    id           serial
        constraint categories_pkey
            primary key,
    parent_id    integer
        constraint categories_parent_id_fkey
            references public.categories,
    name         varchar(255)                           not null,
    description  text,
    slug         text
        constraint categories_slug_key
            unique,
    sort_order   integer                  default 1,
    image_url    text,
    meta_data    jsonb                    default '{}'::jsonb,
    crawler_meta jsonb                    default '{}'::jsonb,
    created_at   timestamp with time zone default now() not null,
    updated_at   timestamp with time zone default now(),
    deleted_at   timestamp with time zone,
    is_active    boolean                  default true
);

-- Create functions for categories table.
create or replace function public.refresh_category_paths() returns void
    language plpgsql
as
$$
DECLARE
    cat_record RECORD;
    path_text TEXT;
    path_ids INTEGER[];
    current_id INTEGER;
    current_name TEXT;
    current_parent_id INTEGER;
    level_count INTEGER;
BEGIN
    -- Clear existing data
    TRUNCATE public.category_paths;

    -- Process each category
    FOR cat_record IN
        SELECT c.id, c.name, c.parent_id
        FROM public.categories c
        WHERE c.is_active = true AND c.deleted_at IS NULL
        ORDER BY c.id
    LOOP
        -- Build path by walking up the hierarchy
        path_ids := ARRAY[]::INTEGER[];
        path_text := '';
        current_id := cat_record.id;
        level_count := 0;

        -- Walk up the hierarchy (max 5 levels)
        WHILE current_id IS NOT NULL AND level_count < 5 LOOP
            SELECT c.name, c.parent_id INTO current_name, current_parent_id
            FROM public.categories c
            WHERE c.id = current_id
            AND c.is_active = true
            AND c.deleted_at IS NULL;

            EXIT WHEN current_name IS NULL;

            -- Prepend to build root-to-leaf path
            path_ids := current_id || path_ids;
            IF path_text = '' THEN
                path_text := current_name;
            ELSE
                path_text := current_name || ' > ' || path_text;
            END IF;

            current_id := current_parent_id;
            level_count := level_count + 1;
        END LOOP;

        -- Insert the category path
        INSERT INTO public.category_paths (
            category_id,
            level_1_id,
            level_2_id,
            level_3_id,
            level_4_id,
            level_5_id,
            full_path,
            path_length
        ) VALUES (
            cat_record.id,
            CASE WHEN array_length(path_ids, 1) >= 1 THEN path_ids[1] ELSE NULL END,
            CASE WHEN array_length(path_ids, 1) >= 2 THEN path_ids[2] ELSE NULL END,
            CASE WHEN array_length(path_ids, 1) >= 3 THEN path_ids[3] ELSE NULL END,
            CASE WHEN array_length(path_ids, 1) >= 4 THEN path_ids[4] ELSE NULL END,
            CASE WHEN array_length(path_ids, 1) >= 5 THEN path_ids[5] ELSE NULL END,
            path_text,
            array_length(path_ids, 1)
        );
    END LOOP;

    -- Update timestamp
    UPDATE public.category_paths SET updated_at = NOW();

    -- Analyze for better performance
    ANALYZE public.category_paths;
END;
$$;

comment on function public.refresh_category_paths() is 'Refreshes the category_paths materialized table with current category hierarchy using iterative approach';

create or replace function public.refresh_single_category_path(cat_id integer) returns void
    language plpgsql
as
$$
DECLARE
    path_text TEXT;
    path_ids INTEGER[];
    current_id INTEGER;
    current_name TEXT;
    current_parent_id INTEGER;
    level_count INTEGER;
BEGIN
    -- Delete existing entry
    DELETE FROM public.category_paths WHERE category_id = cat_id;

    -- Build path by walking up the hierarchy
    path_ids := ARRAY[]::INTEGER[];
    path_text := '';
    current_id := cat_id;
    level_count := 0;

    -- Walk up the hierarchy (max 5 levels)
    WHILE current_id IS NOT NULL AND level_count < 5 LOOP
        SELECT c.name, c.parent_id INTO current_name, current_parent_id
        FROM public.categories c
        WHERE c.id = current_id
        AND c.is_active = true
        AND c.deleted_at IS NULL;

        EXIT WHEN current_name IS NULL;

        -- Prepend to build root-to-leaf path
        path_ids := current_id || path_ids;
        IF path_text = '' THEN
            path_text := current_name;
        ELSE
            path_text := current_name || ' > ' || path_text;
        END IF;

        current_id := current_parent_id;
        level_count := level_count + 1;
    END LOOP;

    -- Insert the category path if we found a valid category
    IF array_length(path_ids, 1) > 0 THEN
        INSERT INTO public.category_paths (
            category_id,
            level_1_id,
            level_2_id,
            level_3_id,
            level_4_id,
            level_5_id,
            full_path,
            path_length,
            updated_at
        ) VALUES (
            cat_id,
            CASE WHEN array_length(path_ids, 1) >= 1 THEN path_ids[1] ELSE NULL END,
            CASE WHEN array_length(path_ids, 1) >= 2 THEN path_ids[2] ELSE NULL END,
            CASE WHEN array_length(path_ids, 1) >= 3 THEN path_ids[3] ELSE NULL END,
            CASE WHEN array_length(path_ids, 1) >= 4 THEN path_ids[4] ELSE NULL END,
            CASE WHEN array_length(path_ids, 1) >= 5 THEN path_ids[5] ELSE NULL END,
            path_text,
            array_length(path_ids, 1),
            NOW()
        );
    END IF;
END;
$$;

comment on function public.refresh_single_category_path(integer) is 'Refreshes path for a single category (useful for incremental updates)';

-- Create trigger functions for categories table.
create or replace function public.trigger_category_paths_bulk_refresh() returns trigger
    language plpgsql
as
$$
BEGIN
    PERFORM refresh_category_paths();
    RETURN NULL;
END;
$$;

create or replace function public.trigger_category_paths_update() returns trigger
    language plpgsql
as
$$
BEGIN
    -- Handle INSERT operations
    IF TG_OP = 'INSERT' THEN
        -- Refresh the new category and potentially affected children
        PERFORM refresh_single_category_path(NEW.id);

        -- If this category has children, refresh them too
        PERFORM refresh_single_category_path(child.id)
        FROM public.categories child
        WHERE child.parent_id = NEW.id
        AND child.is_active = true
        AND child.deleted_at IS NULL;

        RETURN NEW;
    END IF;

    -- Handle UPDATE operations
    IF TG_OP = 'UPDATE' THEN
        -- If parent_id changed, name changed, or active status changed, refresh paths
        IF OLD.parent_id IS DISTINCT FROM NEW.parent_id
           OR OLD.name IS DISTINCT FROM NEW.name
           OR OLD.is_active IS DISTINCT FROM NEW.is_active
           OR OLD.deleted_at IS DISTINCT FROM NEW.deleted_at THEN

            -- Refresh the updated category
            PERFORM refresh_single_category_path(NEW.id);

            -- Refresh all children (they inherit the path change)
            WITH RECURSIVE child_categories AS (
                -- Direct children
                SELECT id
                FROM public.categories
                WHERE parent_id = NEW.id
                AND is_active = true
                AND deleted_at IS NULL

                UNION ALL

                -- Recursive children
                SELECT c.id
                FROM public.categories c
                JOIN child_categories cc ON c.parent_id = cc.id
                WHERE c.is_active = true
                AND c.deleted_at IS NULL
            )
            SELECT refresh_single_category_path(id) FROM child_categories;

            -- If parent changed, also refresh old parent's children
            IF OLD.parent_id IS DISTINCT FROM NEW.parent_id AND OLD.parent_id IS NOT NULL THEN
                PERFORM refresh_single_category_path(child.id)
                FROM public.categories child
                WHERE child.parent_id = OLD.parent_id
                AND child.is_active = true
                AND child.deleted_at IS NULL;
            END IF;
        END IF;

        RETURN NEW;
    END IF;

    -- Handle DELETE operations
    IF TG_OP = 'DELETE' THEN
        -- Remove the deleted category from paths table
        DELETE FROM public.category_paths WHERE category_id = OLD.id;

        -- Refresh all children (they may need to be orphaned or reparented)
        WITH RECURSIVE child_categories AS (
            -- Direct children
            SELECT id
            FROM public.categories
            WHERE parent_id = OLD.id
            AND is_active = true
            AND deleted_at IS NULL

            UNION ALL

            -- Recursive children
            SELECT c.id
            FROM public.categories c
            JOIN child_categories cc ON c.parent_id = cc.id
            WHERE c.is_active = true
            AND c.deleted_at IS NULL
        )
        SELECT refresh_single_category_path(id) FROM child_categories;

        RETURN OLD;
    END IF;

    RETURN NULL;
END;
$$;

comment on function public.trigger_category_paths_update() is 'Trigger function to automatically update category paths when categories change';


-- Create triggers for categories table.
create trigger category_paths_bulk_sync_trigger
    after insert or update or delete
    on public.categories
execute procedure public.trigger_category_paths_bulk_refresh();

create trigger category_paths_sync_trigger
    after insert or update or delete
    on public.categories
    for each row
execute procedure public.trigger_category_paths_update();

comment on trigger category_paths_sync_trigger on public.categories is 'Automatically maintains category_paths table when categories are modified';

-- Create brands table.
create table if not exists public.brands
(
    id           serial
        constraint brands_pkey
            primary key,
    name         varchar(255),
    description  text,
    slug         text
        constraint brands_slug_key
            unique,
    image_url    text,
    meta_data    jsonb                    default '{}'::jsonb,
    crawler_meta jsonb                    default '{}'::jsonb,
    created_at   timestamp with time zone default now(),
    updated_at   timestamp with time zone,
    deleted_at   timestamp with time zone,
    is_active    boolean                  default true,
    website_url  text,
    is_deleted   boolean                  default false,
    constraint check_deleted_status_brands
        check ((deleted_at IS NULL) = (is_deleted = false))
);

create index if not exists idx_brands_name
    on public.brands (name)
    where (deleted_at IS NULL);

create unique index if not exists unique_brand_slug
    on public.brands (slug)
    where (deleted_at IS NULL);

create index if not exists idx_brands_name_lower
    on public.brands (lower(name::text))
    where (deleted_at IS NULL);

-- Create collections table.
create table if not exists public.collections
(
    id           serial
        constraint collections_pkey
            primary key,
    name         varchar(255) not null,
    slug         text
        constraint unique_collection_slug
            unique,
    description  text,
    image_url    text,
    is_active    boolean                  default true,
    meta_data    jsonb                    default '{}'::jsonb,
    crawler_meta jsonb                    default '{}'::jsonb,
    created_at   timestamp with time zone default now()
);

create index if not exists idx_collections_name
    on public.collections (name)
    where (is_active = true);

create index if not exists idx_collections_slug
    on public.collections (slug)
    where (is_active = true);

-- Create amazon categories table.
create table if not exists public.amazon_categories
(
    id           serial
        constraint amazon_categories_pkey
            primary key,
    parent_id    integer
        constraint amazon_categories_parent_id_fkey
            references public.amazon_categories,
    name         varchar(255)                           not null,
    description  text,
    slug         text
        constraint amazon_categories_slug_key
            unique,
    sort_order   integer                  default 1,
    image_url    text,
    meta_data    jsonb                    default '{}'::jsonb,
    crawler_meta jsonb                    default '{}'::jsonb,
    created_at   timestamp with time zone default now() not null,
    updated_at   timestamp with time zone default now(),
    deleted_at   timestamp with time zone,
    is_active    boolean                  default true
);

create index if not exists idx_amazon_categories_hierarchy
    on public.amazon_categories (parent_id, sort_order) include (name);

create index if not exists idx_amazon_categories_name
    on public.amazon_categories (name)
    where (deleted_at IS NULL);




-- Create companies table.
create table if not exists public.companies
(
    id           serial
        constraint companies_pkey
            primary key,
    name         varchar(255)                          not null,
    website_url  text,
    phone_number varchar(50),
    meta_data    jsonb                    default '{}'::jsonb,
    is_active    boolean                  default true not null,
    created_at   timestamp with time zone default now(),
    updated_at   timestamp with time zone,
    deleted_at   timestamp with time zone,
    is_deleted   boolean                  default false,
    constraint check_deleted_status_companies
        check ((deleted_at IS NULL) = (is_deleted = false))
);

comment on table public.companies is 'Stores company information, linked uniquely to a user account.';

create index if not exists idx_companies_active
    on public.companies (is_active)
    where ((is_active = true) AND (deleted_at IS NULL));

create unique index if not exists unique_company_name
    on public.companies (name)
    where ((deleted_at IS NULL) AND (is_deleted = false));

-- Create company addresses table.
create table if not exists public.company_addresses
(
    company_id   integer                                not null
        constraint company_addresses_company_id_fkey
            references public.companies
            on delete cascade,
    address_id   bigint                                 not null
        constraint company_addresses_address_id_fkey
            references public.addresses
            on delete cascade,
    address_name varchar(100)                           not null,
    is_primary   boolean                  default false not null,
    meta_data    jsonb                    default '{}'::jsonb,
    created_at   timestamp with time zone default now(),
    constraint company_addresses_pkey
        primary key (company_id, address_id)
);

create index if not exists idx_company_addresses_address_id
    on public.company_addresses (address_id);

create index if not exists idx_company_addresses_company_id
    on public.company_addresses (company_id);

create unique index if not exists unique_company_primary_address
    on public.company_addresses (company_id)
    where (is_primary = true);

-- Create website countries table.
create table if not exists public.website_countries
(
    website_id   integer not null
        constraint website_countries_website_id_fkey
            references public.websites
            on delete cascade,
    country_code char(2) not null
        constraint website_countries_country_code_fkey
            references public.countries,
    created_at   timestamp with time zone default now(),
    constraint website_countries_pkey
        primary key (website_id, country_code)
);

-- Create store company address distances table.
create table if not exists public.store_company_address_distances
(
    store_id           integer                                                                              not null
        constraint store_company_address_distances_store_id_fkey
            references public.stores
            on delete cascade,
    company_address_id bigint                                                                               not null
        constraint store_company_address_distances_address_id_fkey
            references public.addresses
            on delete cascade,
    distance           numeric(10, 2)                                                                       not null,
    distance_unit      distance_unit_enum               default 'km'::distance_unit_enum                    not null,
    calculation_method distance_calculation_method_enum default 'unknown'::distance_calculation_method_enum not null,
    created_at         timestamp with time zone         default now(),
    updated_at         timestamp with time zone,
    constraint store_company_address_distances_pkey
        primary key (store_id, company_address_id, calculation_method)
);

create index if not exists idx_store_company_distances_addr_store_method
    on public.store_company_address_distances (company_address_id, store_id, calculation_method);

create index if not exists idx_store_company_distances_store_addr_method
    on public.store_company_address_distances (store_id, company_address_id, calculation_method);

create table if not exists public.category_paths
(
    category_id integer not null
        constraint category_paths_pkey
            primary key,
    level_1_id  integer,
    level_2_id  integer,
    level_3_id  integer,
    level_4_id  integer,
    level_5_id  integer,
    full_path   text    not null,
    path_length integer not null,
    updated_at  timestamp with time zone default now()
);

comment on table public.category_paths is 'Materialized table for fast category path lookups and hierarchy navigation';

create index if not exists idx_category_paths_level_1
    on public.category_paths (level_1_id);

create index if not exists idx_category_paths_level_2
    on public.category_paths (level_2_id);

create index if not exists idx_category_paths_level_3
    on public.category_paths (level_3_id);

create index if not exists idx_category_paths_level_4
    on public.category_paths (level_4_id);

create index if not exists idx_category_paths_level_5
    on public.category_paths (level_5_id);

create index if not exists idx_category_paths_full_path
    on public.category_paths using gin (to_tsvector('english'::regconfig, full_path));

create index if not exists idx_category_paths_lower_full_path
    on public.category_paths (lower(full_path) pg_catalog.text_pattern_ops);

create index if not exists idx_category_paths_path_length
    on public.category_paths (path_length);

create index if not exists idx_category_paths_covering
    on public.category_paths (lower(full_path) pg_catalog.text_pattern_ops, path_length) include (category_id);

create or replace function public.find_category_by_path(search_path text)
    returns TABLE(category_id integer, full_path text, path_length integer)
    language plpgsql
as
$$
BEGIN
    RETURN QUERY
    SELECT
        cp.category_id,
        cp.full_path,
        cp.path_length
    FROM public.category_paths cp
    WHERE cp.full_path ILIKE '%' || search_path || '%'
    ORDER BY
        -- Prefer exact matches
        CASE WHEN cp.full_path ILIKE search_path THEN 1 ELSE 2 END,
        -- Then prefer shorter paths (more specific)
        cp.path_length,
        cp.full_path;
END;
$$;

comment on function public.find_category_by_path(text) is 'Finds categories by partial path matching';

create or replace function public.get_category_path(cat_id integer)
    returns TABLE(category_id integer, level_1_id integer, level_2_id integer, level_3_id integer, level_4_id integer, level_5_id integer, full_path text, path_length integer)
    language plpgsql
as
$$
BEGIN
    RETURN QUERY
    SELECT 
        cp.category_id,
        cp.level_1_id,
        cp.level_2_id,
        cp.level_3_id,
        cp.level_4_id,
        cp.level_5_id,
        cp.full_path,
        cp.path_length
    FROM public.category_paths cp
    WHERE cp.category_id = cat_id;
END;
$$;

comment on function public.get_category_path(integer) is 'Gets complete path information for a specific category';

