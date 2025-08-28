create table if not exists public.opportunity_rules
(
    id          bigserial
        constraint opportunity_rules_pkey
            primary key,
    name        varchar(255)                                                                                                                                                                                                                                                     not null,
    description text,
    rule_type   opportunity_rule                                                                                                                                                                                                                                                 not null,
    conditions  jsonb                    default '{"price": {"max": null, "min": null, "currency": "USD"}, "stock": {"status": ["in_stock"], "min_quantity": null}, "profit": {"min_amount": null, "min_percentage": null}, "time_window": {"unit": "days", "value": 3}}'::jsonb not null,
    filters     jsonb                    default '{"brands": {"exclude": [], "include": []}, "stores": {"exclude": [], "include": []}, "categories": {"exclude": [], "include": []}, "store_ranking": {"max_rank": null, "min_rating": null}, "reference_store": null}'::jsonb,
    actions     jsonb                    default '{"expiry": {"enabled": false, "duration": {"unit": "hours", "value": 24}}, "auto_update": false, "notifications": {"roles": [], "users": [], "enabled": false, "channels": ["email"]}, "create_opportunity": true}'::jsonb,
    meta_data   jsonb                    default '{"stats": {"last_run": null, "fail_count": 0, "success_count": 0, "average_profit": null}, "custom_data": {}}'::jsonb,
    priority    integer                  default 0,
    status      opportunity_rule_status  default 'draft'::opportunity_rule_status,
    is_system   boolean                  default false,
    created_by  uuid
        constraint opportunity_rules_created_by_fkey
            references public.users,
    updated_by  uuid
        constraint opportunity_rules_updated_by_fkey
            references public.users,
    created_at  timestamp with time zone default now(),
    updated_at  timestamp with time zone
);

create index if not exists idx_opportunity_rules_active
    on public.opportunity_rules (status asc, priority desc) include (name, rule_type)
    where (status = 'active'::opportunity_rule_status);

create index if not exists idx_opportunity_rules_conditions
    on public.opportunity_rules using gin (conditions)
    where (status = 'active'::opportunity_rule_status);

-- Create opportunity history table.
create table if not exists public.opportunity_history
(
    id                    bigserial
        constraint opportunity_history_pkey
            primary key,
    rule_id               bigint
        constraint opportunity_history_rule_id_fkey
            references public.opportunity_rules,
    product_id            bigint
        constraint opportunity_history_product_id_fkey
            references public.products,
    source_store_id       integer
        constraint opportunity_history_source_store_id_fkey
            references public.stores,
    target_store_id       integer
        constraint opportunity_history_target_store_id_fkey
            references public.stores,
    source_price          numeric(10, 2),
    target_price          numeric(10, 2),
    price_difference      numeric(10, 2),
    difference_percentage numeric(5, 2),
    currency_code         char(3)
        constraint opportunity_history_currency_code_fkey
            references public.currencies,
    meta_data             jsonb                    default '{}'::jsonb,
    created_at            timestamp with time zone default now(),
    updated_at            timestamp with time zone default now(),
    constraint opportunity_history_rule_product_key
        unique (rule_id, product_id)
);

create index if not exists idx_opportunity_history_product
    on public.opportunity_history (product_id asc, created_at desc) include (source_store_id, target_store_id, price_difference, difference_percentage);

create index if not exists idx_opportunity_history_rule
    on public.opportunity_history (rule_id asc, created_at desc) include (product_id, source_store_id, target_store_id, price_difference);

create index if not exists idx_opportunity_history_updated_at
    on public.opportunity_history (updated_at desc);



