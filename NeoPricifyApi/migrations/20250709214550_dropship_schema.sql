create schema if not exists dropship;

create type dropship.marketplace_type as enum (
	'amazon', 'walmart', 'ebay', 'target', 'bestbuy', 
	'costco', 'homedept', 'shopify', 'woocommerce', 
	'own_website', 'etsy', 'facebook_marketplace', 'other'
);

create type dropship.listing_status as enum (
	'draft', 'pending', 'active', 'paused', 
	'out_of_stock', 'delisted', 'error', 'suspended'
);

create type dropship.sync_status as enum (
	'pending', 'in_progress', 'completed', 'failed', 'skipped'
);

create type dropship.alert_type as enum (
	'out_of_stock', 'low_stock', 'low_margin', 
	'low_profit', 'sync_error', 'rule_violation'
);

create type dropship.alert_severity as enum (
	'info', 'warning', 'critical', 'error'
);

create type dropship.rule_type as enum (
	'source_price_min', 'source_price_max', 
	'source_stock_min', 'source_stock_max', 
	'margin_min_amount', 'margin_min_percentage', 
	'profit_min_amount', 'profit_min_percentage', 
	'profit_max_amount', 'profit_max_percentage',
	'manufactured_country_restriction', 'category_restriction', 
	'brand_restriction', 'composite_rule'
);

create type dropship.rule_operator as enum (
	'equals', 'not_equals', 'greater_than', 
	'greater_than_or_equal', 'less_than', 
	'less_than_or_equal', 'between', 'not_between', 
	'in', 'not_in', 'contains', 'not_contains', 
	'starts_with', 'ends_with', 'is_null', 
	'is_not_null', 'is_empty', 'is_not_empty'
);

create type dropship.violation_type as enum (
	'new', 'ongoing', 'resolved', 'recurring'
);

create table if not exists dropship.marketplace_accounts
(
	id serial
		constraint marketplace_accounts_pkey
			primary key,
	user_id uuid not null
		constraint marketplace_accounts_user_id_fkey
			references auth.users
				on delete cascade,
	marketplace_type dropship.marketplace_type not null,
	account_name varchar(255) not null,
	account_identifier varchar(255),
	api_credentials jsonb default '{}'::jsonb,
	is_active boolean default true,
	is_test_mode boolean default false,
	default_currency_code char(3)
		constraint marketplace_accounts_default_currency_code_fkey
			references public.currencies,
	marketplace_settings jsonb default '{}'::jsonb,
	api_rate_limit integer,
	api_calls_remaining integer,
	api_limit_resets_at timestamp with time zone,
	last_sync_at timestamp with time zone,
	created_at timestamp with time zone default now(),
	updated_at timestamp with time zone default now(),
	constraint unique_user_marketplace_account
		unique (user_id, marketplace_type, account_identifier)
);

comment on table dropship.marketplace_accounts is 'Marketplace account credentials and settings for each user';

create index if not exists idx_marketplace_accounts_user_active
	on dropship.marketplace_accounts (user_id, is_active);

create policy "Users can view own marketplace accounts" on dropship.marketplace_accounts
	as permissive
	for select
	using (auth.uid() = user_id);

create policy "Users can manage own marketplace accounts" on dropship.marketplace_accounts
	as permissive
	for all
	using (auth.uid() = user_id);

create table if not exists dropship.listings
(
	id bigserial
		constraint listings_pkey
			primary key,
	product_store_id bigint not null
		constraint listings_product_store_id_fkey
			references public.product_stores
				on delete restrict,
	website_id integer not null
		constraint listings_website_id_fkey
			references public.websites
				on delete restrict,
	marketplace_account_id integer not null
		constraint listings_marketplace_account_id_fkey
			references dropship.marketplace_accounts
				on delete cascade,
	marketplace_listing_id varchar(255),
	marketplace_identifier_id bigint
		constraint listings_marketplace_identifier_id_fkey
			references public.product_identifiers,
	listing_url text,
	listing_title text,
	listing_description text,
	listing_status dropship.listing_status default 'draft'::dropship.listing_status not null,
	listing_price numeric(10,2),
	available_quantity integer,
	reserved_quantity integer default 0,
	total_sales integer default 0,
	total_revenue numeric(12,2) default 0,
	avg_profit_margin numeric(5,2),
	marketplace_fees jsonb default '{}'::jsonb,
	auto_update_price boolean default true,
	auto_update_stock boolean default true,
	listing_data jsonb default '{}'::jsonb,
	last_sync_at timestamp with time zone,
	last_error_message text,
	created_at timestamp with time zone default now(),
	updated_at timestamp with time zone default now(),
	last_compliance_check timestamp with time zone,
	compliance_score numeric(5,2),
	constraint unique_marketplace_listing
		unique (marketplace_account_id, marketplace_listing_id)
);

comment on table dropship.listings is 'Product listings on various marketplaces linked to product_stores';

create index if not exists idx_listings_product_store
	on dropship.listings (product_store_id);

create index if not exists idx_listings_website
	on dropship.listings (website_id);

create index if not exists idx_listings_marketplace_account
	on dropship.listings (marketplace_account_id, listing_status);

create index if not exists idx_listings_status_active
	on dropship.listings (listing_status)
	where (listing_status IN ('active', 'pending'));

create policy "Users can view own listings" on dropship.listings
	as permissive
	for select
	using (marketplace_account_id IN ( SELECT marketplace_accounts.id
   FROM dropship.marketplace_accounts
  WHERE (marketplace_accounts.user_id = auth.uid())));

create policy "Users can manage own listings" on dropship.listings
	as permissive
	for all
	using (marketplace_account_id IN ( SELECT marketplace_accounts.id
   FROM dropship.marketplace_accounts
  WHERE (marketplace_accounts.user_id = auth.uid())));

create table if not exists dropship.sync_history
(
	id bigserial
		constraint sync_history_pkey
			primary key,
	listing_id bigint not null
		constraint sync_history_listing_id_fkey
			references dropship.listings
				on delete cascade,
	sync_type varchar(50) not null,
	sync_status dropship.sync_status not null,
	product_store_price_id bigint
		constraint sync_history_product_store_price_id_fkey
			references public.product_store_prices,
	product_store_inventory_id bigint
		constraint sync_history_product_store_inventory_id_fkey
			references public.product_store_inventory,
	source_price_snapshot numeric(10,2),
	source_stock_snapshot integer,
	source_data jsonb default '{}'::jsonb,
	previous_price numeric(10,2),
	new_price numeric(10,2),
	previous_stock_qty integer,
	new_stock_qty integer,
	changes_detected boolean default false,
	changes_applied boolean default false,
	error_message text,
	started_at timestamp with time zone default now(),
	completed_at timestamp with time zone,
	duration_ms integer,
	sync_metadata jsonb default '{}'::jsonb
);

comment on table dropship.sync_history is 'Historical record of all synchronization operations with references to source data';

create index if not exists idx_sync_history_listing_date
	on dropship.sync_history (listing_id asc, started_at desc);

create table if not exists dropship.alert_configs
(
	id serial
		constraint alert_configs_pkey
			primary key,
	listing_id bigint not null
		constraint alert_configs_listing_id_fkey
			references dropship.listings
				on delete cascade,
	alert_type dropship.alert_type not null,
	is_enabled boolean default true,
	threshold_value numeric(10,2),
	threshold_percentage numeric(5,2),
	severity dropship.alert_severity default 'warning'::dropship.alert_severity,
	notification_channels notification_channel[] default ARRAY['email'::notification_channel],
	cooldown_minutes integer default 60,
	last_triggered_at timestamp with time zone,
	created_at timestamp with time zone default now(),
	updated_at timestamp with time zone default now(),
	constraint unique_listing_alert_type
		unique (listing_id, alert_type)
);

create table if not exists dropship.alerts
(
	id bigserial
		constraint alerts_pkey
			primary key,
	alert_config_id integer
		constraint alerts_alert_config_id_fkey
			references dropship.alert_configs
				on delete cascade,
	listing_id bigint not null
		constraint alerts_listing_id_fkey
			references dropship.listings
				on delete cascade,
	alert_type dropship.alert_type not null,
	severity dropship.alert_severity not null,
	title varchar(255) not null,
	message text,
	current_value numeric(10,2),
	threshold_value numeric(10,2),
	alert_data jsonb default '{}'::jsonb,
	is_acknowledged boolean default false,
	acknowledged_by uuid
		constraint alerts_acknowledged_by_fkey
			references auth.users,
	acknowledged_at timestamp with time zone,
	is_resolved boolean default false,
	resolved_at timestamp with time zone,
	resolution_notes text,
	created_at timestamp with time zone default now(),
	expires_at timestamp with time zone,
	snoozed_until timestamp with time zone
);

comment on table dropship.alerts is 'Active alerts for listings requiring attention';

comment on column dropship.alerts.alert_config_id is 'Reference to alert configuration. Can be null for system-generated alerts without specific configuration.';

create index if not exists idx_alerts_listing_unresolved
	on dropship.alerts (listing_id, is_resolved)
	where (is_resolved = false);

create table if not exists dropship.bulk_operations
(
	id bigserial
		constraint bulk_operations_pkey
			primary key,
	operation_type varchar(50) not null,
	status task_status default 'pending'::task_status,
	marketplace_account_id integer
		constraint bulk_operations_marketplace_account_id_fkey
			references dropship.marketplace_accounts,
	listing_ids bigint[],
	filter_criteria jsonb default '{}'::jsonb,
	total_items integer,
	processed_items integer default 0,
	successful_items integer default 0,
	failed_items integer default 0,
	operation_params jsonb default '{}'::jsonb,
	error_log jsonb default '[]'::jsonb,
	started_at timestamp with time zone,
	completed_at timestamp with time zone,
	created_at timestamp with time zone default now(),
	created_by uuid
		constraint bulk_operations_created_by_fkey
			references auth.users
);

create table if not exists dropship.rules
(
	id bigserial
		constraint rules_pkey
			primary key,
	name varchar(255) not null,
	description text,
	rule_type dropship.rule_type not null,
	user_id uuid not null
		constraint rules_user_id_fkey
			references auth.users
				on delete cascade,
	marketplace_account_id integer
		constraint rules_marketplace_account_id_fkey
			references dropship.marketplace_accounts
				on delete cascade,
	is_global boolean default false,
	priority integer default 0,
	is_active boolean default true,
	is_template boolean default false,
	value_numeric numeric(12,4),
	value_percentage numeric(5,2),
	value_text text,
	value_json jsonb default '{}'::jsonb,
	conditions jsonb default '[]'::jsonb,
	schedule jsonb,
	actions jsonb default '[]'::jsonb,
	evaluation_frequency_minutes integer default 60,
	last_evaluated_at timestamp with time zone,
	evaluation_count integer default 0,
	tags text[] default '{}'::text[],
	created_at timestamp with time zone default now(),
	updated_at timestamp with time zone default now(),
	created_by uuid
		constraint rules_created_by_fkey
			references auth.users,
	constraint rule_name_unique_per_user
		unique (user_id, name)
);

comment on table dropship.rules is 'Flexible rules for managing dropship listings including pricing, inventory, and business logic';

create index if not exists idx_rules_user_active
	on dropship.rules (user_id, is_active)
	where (is_active = true);

create index if not exists idx_rules_type
	on dropship.rules (rule_type);

create index if not exists idx_rules_evaluation
	on dropship.rules (last_evaluated_at, evaluation_frequency_minutes);

create policy "Users can view own rules" on dropship.rules
	as permissive
	for select
	using (auth.uid() = user_id);

create policy "Users can manage own rules" on dropship.rules
	as permissive
	for all
	using (auth.uid() = user_id);

create table if not exists dropship.listing_rules
(
	id bigserial
		constraint listing_rules_pkey
			primary key,
	listing_id bigint not null
		constraint listing_rules_listing_id_fkey
			references dropship.listings
				on delete cascade,
	rule_id bigint not null
		constraint listing_rules_rule_id_fkey
			references dropship.rules
				on delete cascade,
	is_active boolean default true,
	priority_override integer,
	value_override jsonb,
	applied_at timestamp with time zone default now(),
	applied_by uuid
		constraint listing_rules_applied_by_fkey
			references auth.users,
	last_evaluated_at timestamp with time zone,
	evaluation_count integer default 0,
	constraint unique_listing_rule
		unique (listing_id, rule_id)
);

comment on table dropship.listing_rules is 'Many-to-many relationship between rules and listings, allowing rules to be shared across listings';

create index if not exists idx_listing_rules_listing
	on dropship.listing_rules (listing_id, is_active)
	where (is_active = true);

create index if not exists idx_listing_rules_rule
	on dropship.listing_rules (rule_id);

create policy "Users can view own listing rules" on dropship.listing_rules
	as permissive
	for select
	using (listing_id IN ( SELECT l.id
   FROM (dropship.listings l
     JOIN dropship.marketplace_accounts ma ON ((ma.id = l.marketplace_account_id)))
  WHERE (ma.user_id = auth.uid())));

create policy "Users can manage own listing rules" on dropship.listing_rules
	as permissive
	for all
	using (listing_id IN ( SELECT l.id
   FROM (dropship.listings l
     JOIN dropship.marketplace_accounts ma ON ((ma.id = l.marketplace_account_id)))
  WHERE (ma.user_id = auth.uid())));

create table if not exists dropship.rule_templates
(
	id serial
		constraint rule_templates_pkey
			primary key,
	name varchar(255) not null
		constraint unique_template_name
			unique,
	description text,
	category varchar(100) not null,
	rule_type dropship.rule_type not null,
	default_values jsonb not null,
	default_conditions jsonb not null,
	default_actions jsonb not null,
	usage_count integer default 0,
	is_system boolean default false,
	created_at timestamp with time zone default now()
);

comment on table dropship.rule_templates is 'Predefined rule templates for common scenarios';

create table if not exists dropship.rule_violations
(
	id uuid default gen_random_uuid() not null
		constraint rule_violations_pkey
			primary key,
	listing_id integer not null
		constraint rule_violations_listing_id_fkey
			references dropship.listings
				on delete cascade,
	rule_id integer not null
		constraint rule_violations_rule_id_fkey
			references dropship.rules
				on delete cascade,
	rule_name varchar(255) not null,
	rule_type dropship.rule_type not null,
	severity dropship.alert_severity not null,
	violation_type dropship.violation_type default 'new'::dropship.violation_type not null,
	first_detected timestamp with time zone default now() not null,
	last_detected timestamp with time zone default now() not null,
	resolved_at timestamp with time zone,
	occurrence_count integer default 1 not null,
	current_value jsonb,
	expected_value jsonb,
	reason text not null,
	metadata jsonb default '{}'::jsonb,
	created_at timestamp with time zone default now(),
	updated_at timestamp with time zone default now()
);

comment on table dropship.rule_violations is 'Historical tracking of rule violations for compliance monitoring';

comment on column dropship.rule_violations.listing_id is 'Reference to the listing that violated the rule';

comment on column dropship.rule_violations.rule_id is 'Reference to the rule that was violated';

comment on column dropship.rule_violations.violation_type is 'Type of violation: new, ongoing, resolved, or recurring';

comment on column dropship.rule_violations.first_detected is 'When this violation was first detected';

comment on column dropship.rule_violations.last_detected is 'When this violation was last detected (for ongoing violations)';

comment on column dropship.rule_violations.resolved_at is 'When this violation was resolved (null if still active)';

comment on column dropship.rule_violations.occurrence_count is 'Number of times this violation has been detected';

comment on column dropship.rule_violations.current_value is 'The actual value that caused the violation';

comment on column dropship.rule_violations.expected_value is 'The expected/recommended value';

comment on column dropship.rule_violations.metadata is 'Additional metadata about the violation (listing title, marketplace type, etc.)';

create index if not exists idx_rule_violations_listing_id
	on dropship.rule_violations (listing_id);

create index if not exists idx_rule_violations_rule_id
	on dropship.rule_violations (rule_id);

create index if not exists idx_rule_violations_resolved_at
	on dropship.rule_violations (resolved_at);

create index if not exists idx_rule_violations_first_detected
	on dropship.rule_violations (first_detected);

create index if not exists idx_rule_violations_severity
	on dropship.rule_violations (severity);

create index if not exists idx_rule_violations_violation_type
	on dropship.rule_violations (violation_type);

create index if not exists idx_rule_violations_listing_active
	on dropship.rule_violations (listing_id, resolved_at)
	where (resolved_at IS NULL);

create index if not exists idx_rule_violations_rule_time
	on dropship.rule_violations (rule_id, first_detected, resolved_at);

create policy "Users can view their own rule violations" on dropship.rule_violations
	as permissive
	for select
	using (listing_id IN ( SELECT l.id
   FROM (dropship.listings l
     JOIN dropship.marketplace_accounts ma ON ((l.marketplace_account_id = ma.id)))
  WHERE (ma.user_id = auth.uid())));

create policy "Users can insert rule violations for their listings" on dropship.rule_violations
	as permissive
	for insert
	with check (listing_id IN ( SELECT l.id
   FROM (dropship.listings l
     JOIN dropship.marketplace_accounts ma ON ((l.marketplace_account_id = ma.id)))
  WHERE (ma.user_id = auth.uid())));

create policy "Users can update their own rule violations" on dropship.rule_violations
	as permissive
	for update
	using (listing_id IN ( SELECT l.id
   FROM (dropship.listings l
     JOIN dropship.marketplace_accounts ma ON ((l.marketplace_account_id = ma.id)))
  WHERE (ma.user_id = auth.uid())));

create or replace function dropship.update_updated_at_column() returns trigger
	language plpgsql
as $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

comment on function dropship.update_updated_at_column() is 'Updates the updated_at timestamp automatically';

create trigger update_listings_updated_at
	before update
	on dropship.listings
	for each row
	execute procedure dropship.update_updated_at_column();

create trigger update_rules_updated_at
	before update
	on dropship.rules
	for each row
	execute procedure dropship.update_updated_at_column();

create or replace function dropship.validate_listing_website_consistency() returns trigger
	language plpgsql
as $$
DECLARE
    v_product_store_website_id INTEGER;
BEGIN
    -- Get the website_id from the product_store
    SELECT ps.website_id INTO v_product_store_website_id
    FROM public.product_stores ps
    WHERE ps.id = NEW.product_store_id;
    
    -- Check if the listing's website_id matches the product_store's website_id
    IF v_product_store_website_id != NEW.website_id THEN
        RAISE EXCEPTION 'Listing website_id (%) must match product_store website_id (%)', 
            NEW.website_id, v_product_store_website_id;
    END IF;
    
    RETURN NEW;
END;
$$;

comment on function dropship.validate_listing_website_consistency() is 'Ensures listing website_id matches product_store website_id';

create or replace function dropship.sync_listing(p_listing_id bigint) returns boolean
	language plpgsql
as $$
DECLARE
    v_listing RECORD;
    v_source_price NUMERIC;
    v_source_stock INTEGER;
    v_stock_status public.stock_status;
    v_sync_id BIGINT;
    v_price_id BIGINT;
    v_inventory_id BIGINT;
    v_changes_detected BOOLEAN := false;
    v_changes_applied BOOLEAN := false;
BEGIN
    -- Get listing details
    SELECT l.*, ps.id as product_store_id
    INTO v_listing
    FROM dropship.listings l
    JOIN public.product_stores ps ON ps.id = l.product_store_id
    WHERE l.id = p_listing_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Listing not found: %', p_listing_id;
    END IF;
    
    -- Get current source data
    SELECT psp.id, psp.price
    INTO v_price_id, v_source_price
    FROM public.product_store_prices psp
    WHERE psp.product_store_id = v_listing.product_store_id
    ORDER BY psp.updated_at DESC NULLS LAST
    LIMIT 1;
    
    SELECT psi.id, psi.stock_qty, psi.stock_status
    INTO v_inventory_id, v_source_stock, v_stock_status
    FROM public.product_store_inventory psi
    WHERE psi.product_store_id = v_listing.product_store_id
    ORDER BY psi.updated_at DESC NULLS LAST
    LIMIT 1;
    
    -- Create sync history record
    INSERT INTO dropship.sync_history (
        listing_id,
        sync_type,
        sync_status,
        product_store_price_id,
        product_store_inventory_id,
        source_price_snapshot,
        source_stock_snapshot,
        previous_price,
        previous_stock_qty,
        source_data
    ) VALUES (
        p_listing_id,
        'full_sync',
        'in_progress',
        v_price_id,
        v_inventory_id,
        v_source_price,
        v_source_stock,
        v_listing.listing_price,
        v_listing.available_quantity,
        jsonb_build_object(
            'stock_status', v_stock_status,
            'sync_timestamp', now()
        )
    ) RETURNING id INTO v_sync_id;
    
    -- Check for changes
    IF v_source_price IS DISTINCT FROM v_listing.listing_price OR 
       v_source_stock IS DISTINCT FROM v_listing.available_quantity THEN
        v_changes_detected := true;
    END IF;
    
    -- Apply changes if detected and auto-update is enabled
    IF v_changes_detected THEN
        BEGIN
            -- Update listing with new data
            UPDATE dropship.listings SET
                listing_price = CASE 
                    WHEN auto_update_price THEN v_source_price 
                    ELSE listing_price 
                END,
                available_quantity = CASE 
                    WHEN auto_update_stock THEN v_source_stock 
                    ELSE available_quantity 
                END,
                last_sync_at = now(),
                last_error_message = NULL
            WHERE id = p_listing_id;
            
            v_changes_applied := true;
            
        EXCEPTION WHEN OTHERS THEN
            -- Update sync history with error
            UPDATE dropship.sync_history SET
                sync_status = 'failed',
                error_message = SQLERRM,
                completed_at = now()
            WHERE id = v_sync_id;
            
            -- Update listing with error
            UPDATE dropship.listings SET
                last_error_message = SQLERRM,
                last_sync_at = now()
            WHERE id = p_listing_id;
            
            RETURN false;
        END;
    END IF;
    
    -- Complete sync history record
    UPDATE dropship.sync_history SET
        sync_status = 'completed',
        new_price = v_source_price,
        new_stock_qty = v_source_stock,
        changes_detected = v_changes_detected,
        changes_applied = v_changes_applied,
        completed_at = now(),
        duration_ms = EXTRACT(EPOCH FROM (now() - started_at)) * 1000
    WHERE id = v_sync_id;
    
    RETURN true;
END;
$$;

comment on function dropship.sync_listing(bigint) is 'Syncs a single listing with its source data, handling price and inventory updates';

create or replace function dropship.update_rule_violations_updated_at() returns trigger
	language plpgsql
as $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

create trigger rule_violations_updated_at
	before update
	on dropship.rule_violations
	for each row
	execute procedure dropship.update_rule_violations_updated_at();

create or replace function dropship.get_listing_sync_data(listing_id bigint) returns TABLE(listing jsonb, price_data jsonb, inventory_data jsonb)
	security definer
	language plpgsql
as $$
BEGIN
  RETURN QUERY
  SELECT 
    to_jsonb(l.*) ||
    jsonb_build_object(
      'product_stores', to_jsonb(ps.*) ||
        jsonb_build_object(
          'products', to_jsonb(p.*) ||
            jsonb_build_object('brands', to_jsonb(b.*)),
          'stores', to_jsonb(s.*),
          'websites', to_jsonb(w.*)
        ),
      'marketplace_accounts', to_jsonb(ma.*)
    ) as listing,
    to_jsonb(psp.*) as price_data,
    to_jsonb(psi.*) as inventory_data
  FROM dropship.listings l
  JOIN product_stores ps ON ps.id = l.product_store_id
  JOIN products p ON p.id = ps.product_id
  JOIN brands b ON b.id = p.brand_id
  JOIN stores s ON s.id = ps.store_id
  JOIN websites w ON w.id = ps.website_id
  JOIN dropship.marketplace_accounts ma ON ma.id = l.marketplace_account_id
  LEFT JOIN LATERAL (
    SELECT *
    FROM product_store_prices psp_inner
    WHERE psp_inner.product_store_id = ps.id
    ORDER BY psp_inner.updated_at DESC NULLS LAST
    LIMIT 1
  ) psp ON true
  LEFT JOIN LATERAL (
    SELECT *
    FROM product_store_inventory psi_inner
    WHERE psi_inner.product_store_id = ps.id
    ORDER BY psi_inner.updated_at DESC NULLS LAST
    LIMIT 1
  ) psi ON true
  WHERE l.id = get_listing_sync_data.listing_id;
END;
$$;

create or replace function dropship.get_listing_counts_by_account_ids(account_ids integer[]) returns TABLE(marketplace_account_id integer, listing_count bigint)
	security definer
	language plpgsql
as $$
BEGIN
  RETURN QUERY
  SELECT 
    l.marketplace_account_id,
    COUNT(*) as listing_count
  FROM dropship.listings l
  WHERE l.marketplace_account_id = ANY(account_ids)
    AND l.listing_status = 'active'
  GROUP BY l.marketplace_account_id;
END;
$$;

-- Add country_of_origin to dropship.get_listings_with_relations function
CREATE OR REPLACE FUNCTION dropship.get_listings_with_relations(
	p_search text DEFAULT NULL::text, 
	p_listing_ids bigint[] DEFAULT NULL::bigint[], 
	p_marketplace_account_ids integer[] DEFAULT NULL::integer[], 
	p_marketplace_types text[] DEFAULT NULL::text[], 
	p_listing_statuses text[] DEFAULT NULL::text[], 
	p_product_store_ids bigint[] DEFAULT NULL::bigint[], 
	p_website_ids integer[] DEFAULT NULL::integer[], 
	p_store_ids integer[] DEFAULT NULL::integer[], 
	p_product_ids bigint[] DEFAULT NULL::bigint[], 
	p_brand_ids integer[] DEFAULT NULL::integer[], 
	p_category_ids integer[] DEFAULT NULL::integer[], 
	p_auto_update_price boolean DEFAULT NULL::boolean, 
	p_auto_update_stock boolean DEFAULT NULL::boolean, 
	p_has_sync_errors boolean DEFAULT NULL::boolean, 
	p_out_of_stock boolean DEFAULT NULL::boolean, 
	p_min_listing_price numeric DEFAULT NULL::numeric, 
	p_max_listing_price numeric DEFAULT NULL::numeric, 
	p_min_source_price numeric DEFAULT NULL::numeric, 
	p_max_source_price numeric DEFAULT NULL::numeric, 
	p_min_profit_amount numeric DEFAULT NULL::numeric, 
	p_max_profit_amount numeric DEFAULT NULL::numeric, 
	p_min_profit_margin numeric DEFAULT NULL::numeric, 
	p_max_profit_margin numeric DEFAULT NULL::numeric, 
	p_min_stock integer DEFAULT NULL::integer, 
	p_max_stock integer DEFAULT NULL::integer, 
	p_created_after timestamp without time zone DEFAULT NULL::timestamp without time zone, 
	p_created_before timestamp without time zone DEFAULT NULL::timestamp without time zone, 
	p_updated_after timestamp without time zone DEFAULT NULL::timestamp without time zone, 
	p_updated_before timestamp without time zone DEFAULT NULL::timestamp without time zone, 
	p_last_sync_after timestamp without time zone DEFAULT NULL::timestamp without time zone, 
	p_last_sync_before timestamp without time zone DEFAULT NULL::timestamp without time zone, 
	p_has_rules boolean DEFAULT NULL::boolean, 
	p_has_alerts boolean DEFAULT NULL::boolean, 
	p_rule_types text[] DEFAULT NULL::text[], 
	p_page integer DEFAULT 1, 
	p_page_size integer DEFAULT 25, 
	p_sort_by text DEFAULT 'created_at'::text, 
	p_sort_direction text DEFAULT 'desc'::text) returns jsonb
	security definer
	language plpgsql
as $$
DECLARE
    v_result JSONB;
    v_offset INT;
BEGIN
    v_offset := (p_page - 1) * p_page_size;

    WITH RECURSIVE category_descendants AS (
        SELECT DISTINCT descendant_id
        FROM unnest(p_category_ids) AS category_id
        CROSS JOIN LATERAL get_category_and_descendants(category_id) AS descendant_id
        WHERE p_category_ids IS NOT NULL
    ),
    base AS (
        SELECT 
            l.id,
            l.product_store_id,
            l.website_id,
            l.marketplace_account_id,
            l.marketplace_listing_id,
            l.marketplace_identifier_id,
            l.listing_url,
            l.listing_title,
            l.listing_description,
            l.listing_status,
            l.listing_price,
            l.available_quantity,
            l.reserved_quantity,
            l.total_sales,
            l.total_revenue,
            l.avg_profit_margin,
            l.marketplace_fees,
            l.auto_update_price,
            l.auto_update_stock,
            l.listing_data,
            l.last_sync_at,
            l.last_error_message,
            l.created_at,
            l.updated_at,
            l.last_compliance_check,
            l.compliance_score,
            
            -- Product information
            p.id as product_id,
            p.global_code as product_global_code,
            p.name as product_name,
            p.sku as product_sku,
            p.base_image_url as product_base_image_url,
            p.visibility as product_visibility,
            p.product_type,
            
            -- Brand information
            b.id as brand_id,
            b.name as brand_name,
            
            -- Store information
            s.id as store_id,
            s.name as store_name,
            s.code as store_code,
            
            -- Website information
            w.name as website_name,
            w.code as website_code,
            w.url as website_url,
            
            -- Marketplace account information
            ma.id as account_id,
            ma.account_name,
            ma.marketplace_type,
            ma.default_currency_code,
            ma.is_active as account_is_active,
            
            -- Website-specific product details (fallback to products table)
            COALESCE(pwd.name, p.name) as final_product_name,
            COALESCE(pwd.sku, p.sku) as final_product_sku,
            COALESCE(pwd.base_image_url, p.base_image_url) as final_product_image,
            pwd.is_active as website_product_active,
            
            -- Latest pricing data
            psp.price as source_price,
            psp.regular_price as source_regular_price,
            psp.sale_price as source_sale_price,
            psp.currency_code as source_currency,
            psp.updated_at as price_updated_at,
            
            -- Latest inventory data
            psi.stock_qty as source_stock_qty,
            psi.stock_status as source_stock_status,
            psi.updated_at as stock_updated_at,
            
            -- Profit calculations removed - will be handled by rule engine
            NULL::numeric as profit_amount,
            NULL::numeric as calculated_profit_margin,
            
            -- Stock status calculation
            CASE
                WHEN l.available_quantity IS NULL OR l.available_quantity <= 0 THEN 'out_of_stock'
                WHEN l.available_quantity < 10 THEN 'low_stock'
                ELSE 'in_stock'
            END as stock_status,
            
            -- Country of origin
            coo.option_label as country_of_origin_label,
            coo.option_code as country_of_origin_code
            
        FROM dropship.listings l
        JOIN product_stores ps ON ps.id = l.product_store_id
        JOIN products p ON p.id = ps.product_id
        LEFT JOIN brands b ON b.id = p.brand_id
        JOIN stores s ON s.id = ps.store_id
        JOIN websites w ON w.id = l.website_id
        JOIN dropship.marketplace_accounts ma ON ma.id = l.marketplace_account_id
        
        -- Website-specific product details with fallback using LATERAL join
        LEFT JOIN LATERAL (
            SELECT 
                pwd_inner.name,
                pwd_inner.sku,
                pwd_inner.base_image_url,
                pwd_inner.is_active
            FROM product_website_details pwd_inner
            WHERE pwd_inner.product_id = p.id
              AND pwd_inner.website_id = l.website_id
            LIMIT 1
        ) pwd ON true
        
        -- Latest pricing data
        LEFT JOIN LATERAL (
            SELECT *
            FROM product_store_prices psp_inner
            WHERE psp_inner.product_store_id = ps.id
            ORDER BY psp_inner.updated_at DESC NULLS LAST
            LIMIT 1
        ) psp ON true
        
        -- Latest inventory data
        LEFT JOIN LATERAL (
            SELECT *
            FROM product_store_inventory psi_inner
            WHERE psi_inner.product_store_id = ps.id
            ORDER BY psi_inner.updated_at DESC NULLS LAST
            LIMIT 1
        ) psi ON true
        
        -- Country of origin attribute
        LEFT JOIN LATERAL (
            SELECT 
                ao.label as option_label,
                ao.code as option_code
            FROM product_attributes pa
            JOIN attribute_options ao ON ao.id = pa.attribute_option_id
            JOIN attributes a ON a.id = ao.attribute_id
            WHERE pa.product_id = p.id
              AND pa.website_id = l.website_id
              AND a.code = 'country_of_origin'
              AND a.is_active = true
            LIMIT 1
        ) coo ON true
        
        WHERE 1=1  -- Filter by listing_status only, no redundant is_active field
        
        -- Apply filters
        AND (p_listing_ids IS NULL OR l.id = ANY(p_listing_ids))
        AND (p_marketplace_account_ids IS NULL OR l.marketplace_account_id = ANY(p_marketplace_account_ids))
        AND (p_marketplace_types IS NULL OR ma.marketplace_type::text = ANY(p_marketplace_types))
        AND (p_listing_statuses IS NULL OR l.listing_status::text = ANY(p_listing_statuses))
        AND (p_product_store_ids IS NULL OR l.product_store_id = ANY(p_product_store_ids))
        AND (p_website_ids IS NULL OR l.website_id = ANY(p_website_ids))
        AND (p_store_ids IS NULL OR s.id = ANY(p_store_ids))
        AND (p_product_ids IS NULL OR p.id = ANY(p_product_ids))
        AND (p_brand_ids IS NULL OR b.id = ANY(p_brand_ids))
        
        -- Category filter
        AND (p_category_ids IS NULL OR EXISTS (
            SELECT 1 FROM product_categories pc
            WHERE pc.product_id = p.id
            AND pc.category_id IN (SELECT descendant_id FROM category_descendants)
        ))
        
        -- Status filters (removed p_is_active)
        AND (p_auto_update_price IS NULL OR l.auto_update_price = p_auto_update_price)
        AND (p_auto_update_stock IS NULL OR l.auto_update_stock = p_auto_update_stock)
        AND (p_has_sync_errors IS NULL OR 
             (p_has_sync_errors = true AND l.last_error_message IS NOT NULL) OR
             (p_has_sync_errors = false AND l.last_error_message IS NULL))
        AND (p_out_of_stock IS NULL OR 
             (p_out_of_stock = true AND (l.available_quantity IS NULL OR l.available_quantity <= 0)) OR
             (p_out_of_stock = false AND l.available_quantity > 0))
        
        -- Price filters
        AND (p_min_listing_price IS NULL OR l.listing_price >= p_min_listing_price)
        AND (p_max_listing_price IS NULL OR l.listing_price <= p_max_listing_price)
        AND (p_min_source_price IS NULL OR psp.price >= p_min_source_price)
        AND (p_max_source_price IS NULL OR psp.price <= p_max_source_price)
        -- Profit filters removed - will be handled by rule engine
        AND (p_min_profit_amount IS NULL)
        AND (p_max_profit_amount IS NULL)
        AND (p_min_profit_margin IS NULL)
        AND (p_max_profit_margin IS NULL)
        
        -- Stock filters
        AND (p_min_stock IS NULL OR l.available_quantity >= p_min_stock)
        AND (p_max_stock IS NULL OR l.available_quantity <= p_max_stock)
        
        -- Date filters
        AND (p_created_after IS NULL OR l.created_at >= p_created_after)
        AND (p_created_before IS NULL OR l.created_at <= p_created_before)
        AND (p_updated_after IS NULL OR l.updated_at >= p_updated_after)
        AND (p_updated_before IS NULL OR l.updated_at <= p_updated_before)
        AND (p_last_sync_after IS NULL OR l.last_sync_at >= p_last_sync_after)
        AND (p_last_sync_before IS NULL OR l.last_sync_at <= p_last_sync_before)
        
        -- Rule filters
        AND (p_has_rules IS NULL OR 
             (p_has_rules = true AND EXISTS (SELECT 1 FROM dropship.listing_rules lr WHERE lr.listing_id = l.id AND lr.is_active = true)) OR
             (p_has_rules = false AND NOT EXISTS (SELECT 1 FROM dropship.listing_rules lr WHERE lr.listing_id = l.id AND lr.is_active = true)))
        AND (p_rule_types IS NULL OR EXISTS (
            SELECT 1 FROM dropship.listing_rules lr
            JOIN dropship.rules r ON r.id = lr.rule_id
            WHERE lr.listing_id = l.id AND lr.is_active = true AND r.rule_type::text = ANY(p_rule_types)
        ))
        
        -- Alert filters
        AND (p_has_alerts IS NULL OR 
             (p_has_alerts = true AND EXISTS (SELECT 1 FROM dropship.alerts a WHERE a.listing_id = l.id AND a.is_resolved = false)) OR
             (p_has_alerts = false AND NOT EXISTS (SELECT 1 FROM dropship.alerts a WHERE a.listing_id = l.id AND a.is_resolved = false)))
        
        -- Search filter
        AND (p_search IS NULL OR 
             l.listing_title ILIKE '%' || p_search || '%' OR
             l.marketplace_listing_id ILIKE '%' || p_search || '%' OR
             COALESCE(pwd.name, p.name) ILIKE '%' || p_search || '%' OR
             COALESCE(pwd.sku, p.sku) ILIKE '%' || p_search || '%' OR
             p.global_code ILIKE '%' || p_search || '%')
    ),
    
    -- Get rules and alerts for listings
    listing_rules AS (
        SELECT 
            lr.listing_id,
            jsonb_agg(
                jsonb_build_object(
                    'rule_id', r.id,
                    'rule_name', r.name,
                    'rule_type', r.rule_type,
                    'is_active', lr.is_active,
                    'priority_override', lr.priority_override,
                    'last_evaluated_at', lr.last_evaluated_at,
                    'applied_at', lr.applied_at
                )
            ) as rules
        FROM dropship.listing_rules lr
        JOIN dropship.rules r ON r.id = lr.rule_id
        WHERE lr.is_active = true
        GROUP BY lr.listing_id
    ),
    
    listing_alerts AS (
        SELECT 
            a.listing_id,
            jsonb_agg(
                jsonb_build_object(
                    'alert_id', a.id,
                    'alert_type', a.alert_type,
                    'severity', a.severity,
                    'title', a.title,
                    'message', a.message,
                    'is_acknowledged', a.is_acknowledged,
                    'is_resolved', a.is_resolved,
                    'created_at', a.created_at
                )
            ) as alerts
        FROM dropship.alerts a
        WHERE a.is_resolved = false
        GROUP BY a.listing_id
    ),
    
    total_cte AS (
        SELECT count(*) as total_count FROM base
    ),
    
    data_cte AS (
        SELECT 
            b.*,
            COALESCE(lr.rules, '[]'::jsonb) as listing_rules,
            COALESCE(la.alerts, '[]'::jsonb) as listing_alerts
        FROM base b
        LEFT JOIN listing_rules lr ON lr.listing_id = b.id
        LEFT JOIN listing_alerts la ON la.listing_id = b.id
        ORDER BY 
            CASE WHEN p_sort_by = 'listing_title' AND p_sort_direction = 'asc' THEN b.listing_title END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'listing_title' AND p_sort_direction = 'desc' THEN b.listing_title END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'listing_price' AND p_sort_direction = 'asc' THEN b.listing_price END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'listing_price' AND p_sort_direction = 'desc' THEN b.listing_price END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'source_price' AND p_sort_direction = 'asc' THEN b.source_price END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'source_price' AND p_sort_direction = 'desc' THEN b.source_price END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'profit_amount' AND p_sort_direction = 'asc' THEN NULL END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'profit_amount' AND p_sort_direction = 'desc' THEN NULL END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'profit_margin' AND p_sort_direction = 'asc' THEN b.avg_profit_margin END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'profit_margin' AND p_sort_direction = 'desc' THEN b.avg_profit_margin END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'total_sales' AND p_sort_direction = 'asc' THEN b.total_sales END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'total_sales' AND p_sort_direction = 'desc' THEN b.total_sales END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'total_revenue' AND p_sort_direction = 'asc' THEN b.total_revenue END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'total_revenue' AND p_sort_direction = 'desc' THEN b.total_revenue END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'last_sync_at' AND p_sort_direction = 'asc' THEN b.last_sync_at END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'last_sync_at' AND p_sort_direction = 'desc' THEN b.last_sync_at END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'created_at' AND p_sort_direction = 'asc' THEN b.created_at END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'created_at' AND p_sort_direction = 'desc' THEN b.created_at END DESC NULLS LAST,
            CASE WHEN p_sort_by = 'updated_at' AND p_sort_direction = 'asc' THEN b.updated_at END ASC NULLS LAST,
            CASE WHEN p_sort_by = 'updated_at' AND p_sort_direction = 'desc' THEN b.updated_at END DESC NULLS LAST,
            b.id DESC NULLS LAST
        LIMIT p_page_size OFFSET v_offset
    )
    
    SELECT jsonb_build_object(
        'data', COALESCE(jsonb_agg(
            jsonb_build_object(
                -- Listing basic info
                'id', d.id,
                'product_store_id', d.product_store_id,
                'website_id', d.website_id,
                'marketplace_account_id', d.marketplace_account_id,
                'marketplace_listing_id', d.marketplace_listing_id,
                'marketplace_identifier_id', d.marketplace_identifier_id,
                'listing_url', d.listing_url,
                'listing_title', d.listing_title,
                'listing_description', d.listing_description,
                'listing_status', d.listing_status,
                'created_at', d.created_at,
                'updated_at', d.updated_at,
                
                -- Product information
                'product', jsonb_build_object(
                    'id', d.product_id,
                    'global_code', d.product_global_code,
                    'name', d.final_product_name,
                    'sku', d.final_product_sku,
                    'base_image_url', d.final_product_image,
                    'visibility', d.product_visibility,
                    'product_type', d.product_type,
                    'country_of_origin', CASE 
                        WHEN d.country_of_origin_label IS NOT NULL OR d.country_of_origin_code IS NOT NULL THEN 
                            jsonb_build_object(
                                'label', d.country_of_origin_label,
                                'code', d.country_of_origin_code
                            )
                        ELSE NULL 
                    END,
                    'brand', CASE 
                        WHEN d.brand_id IS NOT NULL THEN jsonb_build_object(
                            'id', d.brand_id,
                            'name', d.brand_name
                        ) ELSE NULL 
                    END
                ),
                
                -- Store information
                'store', jsonb_build_object(
                    'id', d.store_id,
                    'name', d.store_name,
                    'code', d.store_code,
                    'website', jsonb_build_object(
                        'id', d.website_id,
                        'name', d.website_name,
                        'code', d.website_code,
                        'url', d.website_url
                    )
                ),
                
                -- Marketplace account information
                'marketplace_account', jsonb_build_object(
                    'id', d.account_id,
                    'account_name', d.account_name,
                    'marketplace_type', d.marketplace_type,
                    'default_currency_code', d.default_currency_code,
                    'is_active', d.account_is_active
                ),
                
                -- Source data (from product store - the source of truth)
                'source', jsonb_build_object(
                    'pricing', jsonb_build_object(
                        'price', d.source_price,
                        'regular_price', d.source_regular_price,
                        'sale_price', d.source_sale_price,
                        'currency', d.source_currency,
                        'updated_at', d.price_updated_at
                    ),
                    'inventory', jsonb_build_object(
                        'quantity', COALESCE(d.source_stock_qty, 0),
                        'status', COALESCE(d.source_stock_status, 'out_of_stock'),
                        'updated_at', d.stock_updated_at
                    )
                ),
                
                -- Marketplace data (current listing state)
                'marketplace', jsonb_build_object(
                    'pricing', jsonb_build_object(
                        'current_price', d.listing_price,
                        'currency', d.default_currency_code,
                        'auto_update_enabled', d.auto_update_price
                    ) || COALESCE(d.marketplace_fees, '{}'::jsonb),
                    'inventory', jsonb_build_object(
                        'available_quantity', d.available_quantity,
                        'reserved_quantity', d.reserved_quantity,
                        'status', d.stock_status,
                        'auto_update_enabled', d.auto_update_stock
                    ),
                    'metrics', jsonb_build_object(
                        'rank', (d.listing_data->>'rank')::integer,
                        'rating', (d.listing_data->>'rating')::numeric,
                        'reviews', (d.listing_data->>'reviews')::integer
                    )
                ),
                
                -- Comparison metrics
                'metrics', jsonb_build_object(
                    'total_sales', d.total_sales,
                    'total_revenue', d.total_revenue,
                    'avg_profit_margin', d.avg_profit_margin,
                    'sync_health', CASE 
                        WHEN d.last_error_message IS NOT NULL THEN 'error'
                        WHEN d.last_sync_at IS NULL THEN 'never_synced'
                        WHEN d.last_sync_at < NOW() - INTERVAL '24 hours' THEN 'stale'
                        ELSE 'healthy'
                    END,
                    'last_sync_at', d.last_sync_at,
                    'last_error_message', d.last_error_message,
                    'compliance_score', d.compliance_score,
                    'auto_update_enabled', jsonb_build_object(
                        'price', d.auto_update_price,
                        'stock', d.auto_update_stock
                    )
                ),
                
                -- Product categories (for detail pages)
                'categories', COALESCE(
                    (SELECT jsonb_agg(
                        jsonb_build_object(
                            'id', c.id,
                            'name', c.name,
                            'slug', c.slug,
                            'parent_id', c.parent_id
                        )
                    )
                    FROM product_categories pc
                    JOIN categories c ON c.id = pc.category_id
                    WHERE pc.product_id = d.product_id
                    AND c.deleted_at IS NULL
                    AND c.is_active = true),
                    '[]'::jsonb
                ),
                
                -- Recent sync history (last 5 syncs)
                'sync_history', COALESCE(
                    (SELECT jsonb_agg(
                        jsonb_build_object(
                            'id', sh.id,
                            'sync_type', sh.sync_type,
                            'sync_status', sh.sync_status,
                            'started_at', sh.started_at,
                            'completed_at', sh.completed_at,
                            'duration_ms', sh.duration_ms,
                            'error_message', sh.error_message,
                            'changes_detected', sh.changes_detected,
                            'changes_applied', sh.changes_applied,
                            'previous_price', sh.previous_price,
                            'new_price', sh.new_price,
                            'previous_stock_qty', sh.previous_stock_qty,
                            'new_stock_qty', sh.new_stock_qty,
                            'source_data', sh.source_data,
                            'sync_metadata', sh.sync_metadata
                        )
                        ORDER BY sh.started_at DESC
                    )
                    FROM (
                        SELECT * FROM dropship.sync_history 
                        WHERE listing_id = d.id 
                        ORDER BY started_at DESC 
                        LIMIT 5
                    ) sh),
                    '[]'::jsonb
                ),
                
                -- Rules and alerts
                'rules_applied', d.listing_rules,
                'active_alerts', d.listing_alerts
            )
        ), '[]'::jsonb),
        
        'pagination', jsonb_build_object(
            'total_count', (SELECT total_count FROM total_cte),
            'page_size', p_page_size,
            'page', p_page,
            'total_pages', CEIL((SELECT total_count FROM total_cte)::float / p_page_size)::INTEGER
        ),
        
        'sorting', jsonb_build_object(
            'fields', ARRAY[
                'id', 'listing_title', 'listing_price', 'source_price',
                'profit_amount', 'profit_margin', 'total_sales', 'total_revenue',
                'last_sync_at', 'created_at', 'updated_at'
            ],
            'directions', ARRAY['asc', 'desc']
        )
    )
    INTO v_result
    FROM data_cte d;

    RETURN v_result;
END;
$$;


GRANT USAGE ON SCHEMA dropship TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA dropship TO anon, authenticated, service_role;
GRANT ALL ON ALL ROUTINES IN SCHEMA dropship TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA dropship TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA dropship GRANT ALL ON TABLES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA dropship GRANT ALL ON ROUTINES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA dropship GRANT ALL ON SEQUENCES TO anon, authenticated, service_role;