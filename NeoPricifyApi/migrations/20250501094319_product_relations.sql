-- Create product relationships table
create table if not exists public.product_relationships
(
    parent_product_id bigint                             not null
        constraint fk_parent_product
            references public.products
            on delete cascade,
    child_product_id  bigint                             not null
        constraint fk_child_product
            references public.products
            on delete cascade,
    relationship_type product_relationship_type          not null,
    meta_data         jsonb                    default '{}'::jsonb,
    created_at        timestamp with time zone default now(),
    website_id        bigint                   default 0 not null
        constraint fk_product_relationships_website
            references public.websites
            on delete cascade,
    id                bigint generated always as identity
        constraint product_relationships_pkey
            primary key,
    constraint uq_product_relationships_natural
        unique (parent_product_id, child_product_id, relationship_type, website_id)
);

comment on table public.product_relationships is 'Stores relationships between products, such as parent-variant, grouped items, etc. Enforces that a child product can only have one parent for a specific relationship type.';

-- Create indexes for product relationships table
create index if not exists idx_product_relationships_parent_product_id_website_id
    on public.product_relationships (parent_product_id, website_id);

create index if not exists idx_product_relationships_parent_type_website
    on public.product_relationships (parent_product_id, relationship_type, website_id)
    where (relationship_type = 'variant'::product_relationship_type);

create index if not exists idx_product_relationships_child_type_website
    on public.product_relationships (child_product_id, relationship_type, website_id)
    where (relationship_type = 'variant'::product_relationship_type);

create index if not exists idx_product_relationships_parent_distinct
    on public.product_relationships (parent_product_id)
    where ((relationship_type = 'variant'::product_relationship_type) AND (website_id = 0));

create index if not exists idx_product_relationships_has_variants_filter
    on public.product_relationships (relationship_type, website_id, parent_product_id)
    where ((relationship_type = 'variant'::product_relationship_type) AND (website_id = 0));

create index if not exists idx_product_relationships_n1_fix
    on public.product_relationships (parent_product_id, relationship_type, website_id, child_product_id)
    where (relationship_type = 'variant'::product_relationship_type);

