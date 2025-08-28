create table google_categories
(
    id           serial
        constraint google_categories_pkey
            primary key,
    parent_id    integer
        constraint google_categories_parent_id_fkey
            references google_categories,
    name         varchar(255)                           not null,
    description  text,
    slug         text
        constraint google_categories_slug_key
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

create index idx_google_categories_name
    on google_categories (name)
    where (deleted_at IS NULL);

create index idx_google_categories_hierarchy
    on google_categories (parent_id, sort_order) include (name);