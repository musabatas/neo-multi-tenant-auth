-- Create attributes table.
create table if not exists public.attributes
(
    id                   serial
        constraint attributes_pkey
            primary key,
    code                 varchar(256)         not null,
    name                 varchar(256)         not null,
    description          text,
    input_type           attribute_input_type not null,
    is_system            boolean                  default false,
    is_required          boolean                  default false,
    is_unique            boolean                  default false,
    is_filterable        boolean                  default false,
    is_searchable        boolean                  default false,
    is_comparable        boolean                  default false,
    is_visible_on_front  boolean                  default false,
    is_used_for_variants boolean                  default false,
    default_value        jsonb,
    validation_rules     jsonb                    default '{}'::jsonb,
    sort_order           integer                  default 0,
    created_at           timestamp with time zone default now(),
    updated_at           timestamp with time zone,
    created_by           uuid
        constraint attributes_created_by_fkey
            references public.users,
    updated_by           uuid
        constraint attributes_updated_by_fkey
            references public.users,
    is_active            boolean                  default true
);

-- Create indexes for attributes table.
create index if not exists idx_attributes_code
    on public.attributes (code)
    where (is_system = false);

create index if not exists idx_attributes_variants
    on public.attributes (is_used_for_variants, sort_order) include (code, name, input_type, validation_rules)
    where (is_used_for_variants = true);

create index if not exists idx_attributes_visible
    on public.attributes (is_visible_on_front, sort_order) include (code, name, input_type)
    where (is_visible_on_front = true);

-- Create attribute options table.
create table if not exists public.attribute_options
(
    id           serial
        constraint attribute_options_pkey
            primary key,
    attribute_id integer      not null
        constraint attribute_options_attribute_id_fkey
            references public.attributes
            on delete cascade,
    code         varchar(255),
    label        varchar(255) not null,
    sort_order   integer                  default 0,
    is_default   boolean                  default false,
    swatch_data  jsonb,
    created_at   timestamp with time zone default now(),
    updated_at   timestamp with time zone
);

-- Create indexes for attribute options table.
create index if not exists idx_attribute_options_attribute
    on public.attribute_options (attribute_id, sort_order) include (code, label, is_default);

create index if not exists idx_attribute_options_code
    on public.attribute_options (code)
    where (code IS NOT NULL);

create unique index if not exists idx_attribute_options_default
    on public.attribute_options (attribute_id)
    where (is_default = true);

create index if not exists idx_attribute_options_attribute_label_lower
    on public.attribute_options (attribute_id, lower(label::text)) include (id);
