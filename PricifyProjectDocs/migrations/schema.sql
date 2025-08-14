create type public.alert_status as enum ('active', 'inactive', 'triggered', 'acknowledged', 'resolved', 'snoozed', 'expired', 'deleted');

create type public.alert_type as enum ('price_change', 'stock_status', 'price_threshold', 'stock_threshold', 'competitor_price', 'margin_alert', 'trend_alert', 'promotion_alert');

create type public.attribute_input_type as enum ('text', 'number', 'select', 'multiselect', 'boolean', 'date', 'price', 'color', 'textarea', 'repeatable_text', 'repeatable_number', 'repeatable_select', 'repeatable_date', 'repeatable_price', 'repeatable_object', 'file', 'range', 'rating');

create type public.common_status as enum ('active', 'inactive', 'pending', 'archived', 'deleted');

create type public.connection_status as enum ('connected', 'disconnected', 'pending', 'failed', 'rate_limited', 'maintenance', 'deprecated', 'blocked');

create type public.continents as enum ('Europe', 'Asia', 'North America', 'South America', 'Africa', 'Oceania', 'Antarctica');

create type public.crawlab_task_status as enum ('pending', 'running', 'finished', 'error', 'cancelled');

create type public.data_source as enum ('keepa', 'amazon_sp_api', 'amazon_paapi', 'walmart_api', 'walmart_io_api', 'ebay_api', 'internal_estimate', 'other_api', 'easyparser', 'amazon_crawler', 'supplyspy', 'custom_spider', 'unknown');

create type public.delivery_method as enum ('standard', 'express', 'next_day', 'same_day', 'pickup', 'freight', 'digital', 'international', 'free');

create type public.delivery_zone as enum ('country', 'region', 'state', 'city', 'postal_code', 'radius', 'continent', 'custom_zone');

create type public.distance_calculation_method_enum as enum ('haversine', 'routing_api', 'manual', 'unknown');

create type public.distance_unit_enum as enum ('km', 'miles');

create type public.entity_type as enum ('product', 'category', 'vendor', 'store', 'website', 'brand', 'manufacturer');

create type public.identifier_type as enum ('sku', 'upc', 'ean', 'isbn', 'asin', 'mpn', 'gtin', 'barcode', 'source_id', 'supplier_id', 'supplier_code', 'supplier_sku', 'part_number', 'formatted_code', 'custom', 'api_code', 'global_code');

create type public.inventory_change_type as enum ('manual', 'order', 'return', 'import', 'sync', 'adjustment', 'transfer', 'correction', 'system', 'update', 'increase', 'decrease', 'initial');

create type public.media_role as enum ('primary', 'gallery', 'thumbnail', 'swatch', 'variant_specific', 'lifestyle', 'packaging', 'promotional', 'video', 'audio', 'user_manual', 'warranty', 'document', 'specification', 'instruction', 'certificate', 'size_chart');

create type public.media_type as enum ('image', 'video', 'audio', 'document', 'model_3d', 'ar_content');

create type public.notification_channel as enum ('email', 'telegram', 'webhook', 'push', 'sms', 'slack', 'discord', 'teams', 'whatsapp', 'api');

create type public.notification_log_status as enum ('sent', 'failed', 'pending', 'retry', 'blocked', 'bounced', 'expired', 'cancelled');

create type public.notification_status as enum ('read', 'unread', 'deleted', 'archived', 'snoozed');

create type public.notification_type as enum ('alert', 'system', 'info', 'warning', 'error', 'success', 'update', 'security', 'promotional');

create type public.opportunity_rule as enum ('price_gap', 'stock_alert', 'margin_based', 'competitive', 'trend_based', 'seasonal', 'flash_deal', 'bundle', 'clearance', 'reference_store', 'profit_margin', 'price_drop');

create type public.opportunity_rule_status as enum ('draft', 'active', 'inactive', 'archived', 'deleted', 'testing', 'scheduled');

create type public.price_multiplier_type as enum ('markup', 'markdown', 'fixed', 'override');

create type public.product_relationship_type as enum ('variant', 'grouped_item', 'bundle_component', 'related_product');

create type public.product_status as enum ('draft', 'active', 'inactive', 'pending_review', 'approved', 'rejected', 'archived', 'deleted');

create type public.product_type as enum ('simple', 'configurable', 'virtual', 'downloadable', 'bundle', 'grouped', 'subscription', 'service', 'variant');

create type public.product_visibility as enum ('visible', 'not_visible_individually', 'catalog', 'search');

create type public.stock_status as enum ('in_stock', 'low_stock', 'out_of_stock', 'pre_order', 'back_order', 'discontinued');

create type public.store_url_type as enum ('full_url', 'full_url_with_params', 'query_params_only', 'same_as_website', 'canonical_url');

create type public.subscription_status as enum ('active', 'inactive', 'trial', 'expired', 'cancelled', 'pending_payment', 'past_due', 'suspended');

create type public.task_status as enum ('pending', 'in_progress', 'completed', 'failed', 'cancelled', 'scheduled', 'retrying', 'blocked', 'skipped');

create type public.url_type as enum ('internal', 'external', 'affiliate', 'redirect', 'canonical');

create type public.user_preference_type as enum ('theme', 'language', 'notifications', 'dashboard', 'display', 'privacy', 'communication', 'alerts', 'reports', 'search', 'currency', 'timezone', 'accessibility', 'export', 'view_mode');

create type public.user_status as enum ('pending', 'active', 'inactive', 'suspended', 'banned', 'unverified', 'locked', 'deleted');

create type public.view_type as enum ('product_list', 'store_list', 'price_comparison', 'stock_monitoring', 'website_products', 'store_products', 'global_comparison', 'analytics_dashboard', 'reports');

create type public.widget_category as enum ('price_comparison', 'stock_monitoring', 'profit_calculation', 'market_analysis', 'store_comparison', 'price_history', 'stock_history', 'sales_analytics', 'custom');

create type public.widget_type as enum ('chart', 'table', 'metric', 'list', 'calendar', 'map', 'grid', 'card', 'timeline', 'feed', 'form', 'report', 'alert', 'custom', 'dashboard');

create type public.verification_status as enum ('pending', 'verified', 'failed');

create type public.trigger_type as enum ('scheduled', 'manual', 'dependency', 'retry');

create type public.execution_status as enum ('pending', 'running', 'completed', 'failed', 'cancelled', 'timeout', 'retrying');

create table if not exists public.amazon_categories
(
	id serial
		constraint amazon_categories_pkey
			primary key,
	parent_id integer
		constraint amazon_categories_parent_id_fkey
			references public.amazon_categories,
	name varchar(255) not null,
	description text,
	slug text
		constraint amazon_categories_slug_key
			unique,
	sort_order integer default 1,
	image_url text,
	meta_data jsonb default '{}'::jsonb,
	crawler_meta jsonb default '{}'::jsonb,
	created_at timestamp with time zone default now() not null,
	updated_at timestamp with time zone default now(),
	deleted_at timestamp with time zone,
	is_active boolean default true
);

create index if not exists idx_amazon_categories_hierarchy
	on public.amazon_categories (parent_id, sort_order) include (name);

create index if not exists idx_amazon_categories_name
	on public.amazon_categories (name)
	where (deleted_at IS NULL);

create table if not exists public.brands
(
	id serial
		constraint brands_pkey
			primary key,
	name varchar(255),
	description text,
	slug text
		constraint brands_slug_key
			unique,
	image_url text,
	meta_data jsonb default '{}'::jsonb,
	crawler_meta jsonb default '{}'::jsonb,
	created_at timestamp with time zone default now(),
	updated_at timestamp with time zone,
	deleted_at timestamp with time zone,
	is_active boolean default true,
	website_url text,
	is_deleted boolean default false,
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

create table if not exists public.categories
(
	id serial
		constraint categories_pkey
			primary key,
	parent_id integer
		constraint categories_parent_id_fkey
			references public.categories,
	name varchar(255) not null,
	description text,
	slug text
		constraint categories_slug_key
			unique,
	sort_order integer default 1,
	image_url text,
	meta_data jsonb default '{}'::jsonb,
	crawler_meta jsonb default '{}'::jsonb,
	created_at timestamp with time zone default now() not null,
	updated_at timestamp with time zone default now(),
	deleted_at timestamp with time zone,
	is_active boolean default true
);

create trigger category_paths_sync_trigger
	after insert or update or delete
	on public.categories
	for each row
	execute procedure public.trigger_category_paths_update();

comment on trigger category_paths_sync_trigger on public.categories is 'Automatically maintains category_paths table when categories are modified';

create trigger category_paths_bulk_sync_trigger
	after insert or update or delete
	on public.categories
	execute procedure public.trigger_category_paths_bulk_refresh();

create table if not exists public.collections
(
	id serial
		constraint collections_pkey
			primary key,
	name varchar(255) not null,
	slug text
		constraint unique_collection_slug
			unique,
	description text,
	image_url text,
	is_active boolean default true,
	meta_data jsonb default '{}'::jsonb,
	crawler_meta jsonb default '{}'::jsonb,
	created_at timestamp with time zone default now()
);

create index if not exists idx_collections_name
	on public.collections (name)
	where (is_active = true);

create index if not exists idx_collections_slug
	on public.collections (slug)
	where (is_active = true);

create table if not exists public.currencies
(
	code char(3) not null
		constraint currencies_pkey
			primary key,
	name varchar(50) not null,
	symbol char(5),
	exchange_rate numeric(10,5),
	updated_at timestamp with time zone default now(),
	is_active boolean default true
);

create table if not exists public.countries
(
	code varchar(2) not null
		constraint countries_pkey
			primary key,
	name varchar(100) not null,
	iso2 char(2),
	iso3 char(3),
	local_name varchar(255),
	continent continents,
	capital varchar(255),
	currency_code char(3)
		constraint countries_currency_code_fkey
			references public.currencies,
	currency_name varchar(100),
	tld char(3),
	phone_code varchar(20),
	languages varchar(255),
	timezone varchar(100),
	region varchar(100),
	population serial,
	area_km2 numeric(10,2)
);

create table if not exists public.addresses
(
	id bigserial
		constraint addresses_pkey
			primary key,
	street varchar(255) default NULL::character varying,
	city varchar(255),
	state varchar(255) default NULL::character varying,
	postal_code varchar(20),
	country_code varchar(2) not null
		constraint addresses_country_code_fkey
			references public.countries,
	additional_info text,
	latitude numeric(9,6),
	longitude numeric(9,6),
	created_at timestamp with time zone default now(),
	updated_at timestamp with time zone
);

create index if not exists idx_addresses_geo
	on public.addresses (latitude, longitude)
	where ((latitude IS NOT NULL) AND (longitude IS NOT NULL));

create index if not exists idx_countries_search
	on public.countries (name, iso2, iso3) include (currency_code, timezone, region);

create index if not exists idx_countries_region
	on public.countries (region, continent) include (code, name, currency_code);

create index if not exists idx_currencies_exchange_rate
	on public.currencies (exchange_rate asc, updated_at desc);

create table if not exists public.google_categories
(
	id serial
		constraint google_categories_pkey
			primary key,
	parent_id integer
		constraint google_categories_parent_id_fkey
			references public.google_categories,
	name varchar(255) not null,
	description text,
	slug text
		constraint google_categories_slug_key
			unique,
	sort_order integer default 1,
	image_url text,
	meta_data jsonb default '{}'::jsonb,
	crawler_meta jsonb default '{}'::jsonb,
	created_at timestamp with time zone default now() not null,
	updated_at timestamp with time zone default now(),
	deleted_at timestamp with time zone,
	is_active boolean default true
);

create index if not exists idx_google_categories_hierarchy
	on public.google_categories (parent_id, sort_order) include (name);

create index if not exists idx_google_categories_name
	on public.google_categories (name)
	where (deleted_at IS NULL);

create table if not exists public.languages
(
	code char(5) not null
		constraint languages_pkey
			primary key,
	name varchar(100) not null,
	native_name varchar(100),
	direction varchar(3) default 'ltr'::character varying,
	is_active boolean default true,
	sort_order integer,
	region_code char(4)
);

create index if not exists idx_languages_active
	on public.languages (is_active)
	where (is_active = true);

create table if not exists public.products
(
	id bigserial
		constraint products_pkey
			primary key,
	global_code varchar(255),
	brand_id integer
		constraint products_brand_id_fkey
			references public.brands,
	name text,
	description text,
	sku varchar(255),
	product_type product_type default 'simple'::product_type not null,
	visibility product_visibility default 'visible'::product_visibility,
	sellable boolean default true not null,
	base_image_url varchar,
	attribute_data jsonb default '{}'::jsonb,
	meta_data jsonb default '{}'::jsonb,
	crawler_meta jsonb default '{}'::jsonb,
	is_deleted boolean default false,
	created_at timestamp with time zone default CURRENT_TIMESTAMP not null,
	updated_at timestamp with time zone,
	deleted_at timestamp with time zone,
	is_active boolean default true,
	constraint check_deleted_status
		check ((deleted_at IS NULL) = (is_deleted = false))
)
with (autovacuum_vacuum_scale_factor=0.05, autovacuum_analyze_scale_factor=0.02);

create table if not exists public.product_categories
(
	product_id bigint not null
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

create table if not exists public.product_price_update_queue
(
	product_id bigint not null
		constraint product_price_update_queue_pkey
			primary key
		constraint product_price_update_queue_product_id_fkey
			references public.products
				on delete cascade,
	status task_status default 'pending'::task_status not null
);

create index if not exists idx_price_update_queue_status
	on public.product_price_update_queue (status);

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

create table if not exists public.user_ui_settings
(
	id uuid default gen_random_uuid() not null
		constraint user_ui_settings_pkey
			primary key,
	user_id uuid
		constraint user_ui_settings_user_id_fkey
			references auth.users
				on delete cascade,
	feature_key text not null,
	setting_key text not null,
	setting_value jsonb not null,
	created_at timestamp with time zone default now() not null,
	updated_at timestamp with time zone default now() not null
);

create index if not exists idx_user_ui_settings_feature_key
	on public.user_ui_settings (feature_key);

create index if not exists idx_user_ui_settings_user_id
	on public.user_ui_settings (user_id);

create unique index if not exists unique_global_setting
	on public.user_ui_settings (feature_key, setting_key)
	where (user_id IS NULL);

create unique index if not exists unique_user_setting
	on public.user_ui_settings (user_id, feature_key, setting_key)
	where (user_id IS NOT NULL);

create policy "Allow user DELETE access" on public.user_ui_settings
	as permissive
	for delete
	using (auth.uid() = user_id);

create policy "Allow user INSERT access" on public.user_ui_settings
	as permissive
	for insert
	with check (auth.uid() = user_id);

create policy "Allow user SELECT access" on public.user_ui_settings
	as permissive
	for select
	using ((auth.uid() = user_id) OR (user_id IS NULL));

create policy "Allow user UPDATE access" on public.user_ui_settings
	as permissive
	for update
	using (auth.uid() = user_id)
	with check (auth.uid() = user_id);

create table if not exists public.users
(
	id uuid not null
		constraint users_pkey
			primary key,
	username varchar(50) not null
		constraint users_username_key
			unique,
	first_name varchar(50),
	last_name varchar(50),
	full_name text generated always as (
CASE
    WHEN (last_name IS NULL) THEN (first_name)::text
    WHEN (first_name IS NULL) THEN (last_name)::text
    ELSE (((first_name)::text || ' '::text) || (last_name)::text)
END) stored,
	avatar_url text,
	bio text,
	preferred_language_code char(5)
		constraint users_preferred_language_code_fkey
			references public.languages
				on delete set null,
	preferred_country_code char(2)
		constraint users_preferred_country_code_fkey
			references public.countries
				on delete set null,
	preferred_currency_code char(3)
		constraint users_preferred_currency_code_fkey
			references public.currencies
				on delete set null,
	location point,
	billing_address jsonb,
	payment_method jsonb,
	is_active boolean default true,
	meta_data jsonb default '{}'::jsonb,
	created_at timestamp with time zone default now(),
	updated_at timestamp with time zone default now(),
	deleted_at timestamp with time zone
);

comment on table public.users is 'Stores extended user profile information';

create table if not exists public.attributes
(
	id serial
		constraint attributes_pkey
			primary key,
	code varchar(256) not null,
	name varchar(256) not null,
	description text,
	input_type attribute_input_type not null,
	is_system boolean default false,
	is_required boolean default false,
	is_unique boolean default false,
	is_filterable boolean default false,
	is_searchable boolean default false,
	is_comparable boolean default false,
	is_visible_on_front boolean default false,
	is_used_for_variants boolean default false,
	default_value jsonb,
	validation_rules jsonb default '{}'::jsonb,
	sort_order integer default 0,
	created_at timestamp with time zone default now(),
	updated_at timestamp with time zone,
	created_by uuid
		constraint attributes_created_by_fkey
			references public.users,
	updated_by uuid
		constraint attributes_updated_by_fkey
			references public.users,
	is_active boolean default true
);

create table if not exists public.attribute_options
(
	id serial
		constraint attribute_options_pkey
			primary key,
	attribute_id integer not null
		constraint attribute_options_attribute_id_fkey
			references public.attributes
				on delete cascade,
	code varchar(255),
	label varchar(255) not null,
	sort_order integer default 0,
	is_default boolean default false,
	swatch_data jsonb,
	created_at timestamp with time zone default now(),
	updated_at timestamp with time zone
);

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

create index if not exists idx_attributes_code
	on public.attributes (code)
	where (is_system = false);

create index if not exists idx_attributes_variants
	on public.attributes (is_used_for_variants, sort_order) include (code, name, input_type, validation_rules)
	where (is_used_for_variants = true);

create index if not exists idx_attributes_visible
	on public.attributes (is_visible_on_front, sort_order) include (code, name, input_type)
	where (is_visible_on_front = true);

create table if not exists public.opportunity_rules
(
	id bigserial
		constraint opportunity_rules_pkey
			primary key,
	name varchar(255) not null,
	description text,
	rule_type opportunity_rule not null,
	conditions jsonb default '{"price": {"max": null, "min": null, "currency": "USD"}, "stock": {"status": ["in_stock"], "min_quantity": null}, "profit": {"min_amount": null, "min_percentage": null}, "time_window": {"unit": "days", "value": 3}}'::jsonb not null,
	filters jsonb default '{"brands": {"exclude": [], "include": []}, "stores": {"exclude": [], "include": []}, "categories": {"exclude": [], "include": []}, "store_ranking": {"max_rank": null, "min_rating": null}, "reference_store": null}'::jsonb,
	actions jsonb default '{"expiry": {"enabled": false, "duration": {"unit": "hours", "value": 24}}, "auto_update": false, "notifications": {"roles": [], "users": [], "enabled": false, "channels": ["email"]}, "create_opportunity": true}'::jsonb,
	meta_data jsonb default '{"stats": {"last_run": null, "fail_count": 0, "success_count": 0, "average_profit": null}, "custom_data": {}}'::jsonb,
	priority integer default 0,
	status opportunity_rule_status default 'draft'::opportunity_rule_status,
	is_system boolean default false,
	created_by uuid
		constraint opportunity_rules_created_by_fkey
			references public.users,
	updated_by uuid
		constraint opportunity_rules_updated_by_fkey
			references public.users,
	created_at timestamp with time zone default now(),
	updated_at timestamp with time zone
);

create index if not exists idx_opportunity_rules_active
	on public.opportunity_rules (status asc, priority desc) include (name, rule_type)
	where (status = 'active'::opportunity_rule_status);

create index if not exists idx_opportunity_rules_conditions
	on public.opportunity_rules using gin (conditions)
	where (status = 'active'::opportunity_rule_status);

create table if not exists public.product_identifiers
(
	product_id bigint not null
		constraint product_identifiers_product_id_fkey
			references public.products
				on delete cascade,
	identifier_type identifier_type not null,
	identifier_value varchar(255) not null,
	is_primary boolean default false,
	is_verified boolean default false,
	verified_at timestamp with time zone,
	verified_by uuid
		constraint product_identifiers_verified_by_fkey
			references public.users,
	meta_data jsonb default '{"markets": []}'::jsonb,
	created_at timestamp with time zone default now(),
	verification_status verification_status default 'pending'::verification_status,
	id bigint generated by default as identity
		constraint product_identifiers_pkey
			primary key,
	constraint unique_product_identifier
		unique (product_id, identifier_type, identifier_value)
);

create index if not exists idx_product_identifiers_product_id
	on public.product_identifiers (product_id);

create index if not exists idx_product_identifiers_type_value_status
	on public.product_identifiers (identifier_type, identifier_value, verification_status);

create index if not exists idx_product_identifiers_product_primary
	on public.product_identifiers (product_id asc, is_primary desc, identifier_type asc) include (identifier_value, is_verified);

create index if not exists idx_product_identifiers_value_type
	on public.product_identifiers (identifier_value, identifier_type) include (product_id);

create table if not exists public.system_settings
(
	id bigserial
		constraint system_settings_pkey
			primary key,
	setting_key varchar(255) not null,
	setting_value jsonb default '{}'::jsonb,
	user_specific boolean default false,
	user_id uuid
		constraint system_settings_user_id_fkey
			references public.users
				on delete set null,
	is_public boolean default false not null,
	requires_auth boolean default false not null,
	is_active boolean default true,
	active_at timestamp with time zone,
	active_until timestamp with time zone,
	created_at timestamp with time zone default now(),
	updated_at timestamp with time zone default now(),
	constraint system_settings_setting_key_user_specific_user_id_key
		unique (setting_key, user_specific, user_id)
);

comment on table public.system_settings is 'Stores system-wide and user-specific settings with appropriate access controls';

create index if not exists idx_system_settings_active
	on public.system_settings (is_active, active_at, active_until)
	where (is_active = true);

create index if not exists idx_system_settings_public
	on public.system_settings (setting_key)
	where (is_public = true);

create index if not exists idx_system_settings_user
	on public.system_settings (user_id, setting_key)
	where (user_specific = true);

create index if not exists idx_users_active
	on public.users (is_active)
	where (is_active = true);

create index if not exists idx_users_location
	on public.users using gist (location);

create index if not exists idx_users_meta_data
	on public.users using gin (meta_data);

create table if not exists public.vendors
(
	id serial
		constraint vendors_pkey
			primary key,
	name varchar(255) not null,
	country_code char(2)
		constraint vendors_country_code_fkey
			references public.countries,
	website_url text,
	logo_url text,
	meta_data jsonb default '{}'::jsonb not null,
	is_deleted boolean default false,
	created_at timestamp with time zone default now(),
	updated_at timestamp with time zone,
	deleted_at timestamp with time zone,
	is_active boolean default true not null,
	constraint check_deleted_status
		check ((deleted_at IS NULL) = (is_deleted = false))
);

create unique index if not exists unique_vendor_name
	on public.vendors (name)
	where ((deleted_at IS NULL) AND (is_deleted = false));

create index if not exists idx_vendors_name_lower
	on public.vendors (lower(name::text))
	where ((deleted_at IS NULL) AND (is_deleted = false));

create table if not exists public.websites
(
	id serial
		constraint websites_pkey
			primary key,
	vendor_id integer
		constraint websites_vendor_id_fkey
			references public.vendors,
	code varchar(255),
	name varchar(255) not null,
	description text,
	url varchar(255),
	is_active boolean default true,
	logo_url text,
	meta_data jsonb default '{}'::jsonb not null,
	crawler_meta jsonb default '{}'::jsonb not null,
	deleted_at timestamp with time zone,
	is_deleted boolean default false,
	created_at timestamp with time zone default CURRENT_TIMESTAMP not null,
	updated_at timestamp with time zone,
	default_currency_code char(3)
		constraint websites_default_currency_code_fkey
			references public.currencies,
	constraint check_deleted_status_websites
		check ((deleted_at IS NULL) = (is_deleted = false))
);

create table if not exists public.product_attributes
(
	product_id bigint not null
		constraint product_attributes_product_id_fkey
			references public.products
				on delete cascade,
	attribute_option_id integer not null
		constraint product_attributes_attribute_option_id_fkey
			references public.attribute_options
				on delete cascade,
	website_id integer default 0 not null
		constraint product_attributes_website_id_fkey
			references public.websites,
	constraint product_attributes_pkey
		primary key (product_id, attribute_option_id, website_id)
);

create index if not exists idx_product_attributes_product
	on public.product_attributes (product_id) include (attribute_option_id, website_id);

create index if not exists idx_product_attributes_website
	on public.product_attributes (website_id) include (product_id, attribute_option_id);

create table if not exists public.product_collections
(
	product_id bigint not null
		constraint product_collections_product_id_fkey
			references public.products
				on delete cascade,
	collection_id integer not null
		constraint product_collections_collection_id_fkey
			references public.collections,
	sort_order integer default 0,
	website_id integer
		constraint product_collections_website_id_fkey
			references public.websites,
	constraint product_collections_pkey
		primary key (product_id, collection_id)
);

create index if not exists idx_product_collections_collection
	on public.product_collections (collection_id, sort_order) include (product_id);

create table if not exists public.product_media
(
	product_id bigint not null
		constraint product_media_product_id_fkey
			references public.products
				on delete cascade,
	website_id integer not null
		constraint product_media_website_id_fkey
			references public.websites,
	media_type media_type not null,
	media_role media_role not null,
	url text not null,
	meta_data jsonb default '{}'::jsonb,
	sort_order integer default 0 not null,
	constraint product_media_pkey
		primary key (product_id, website_id, media_type, media_role, sort_order)
);

create table if not exists public.product_relationships
(
	parent_product_id bigint not null
		constraint fk_parent_product
			references public.products
				on delete cascade,
	child_product_id bigint not null
		constraint fk_child_product
			references public.products
				on delete cascade,
	relationship_type product_relationship_type not null,
	meta_data jsonb default '{}'::jsonb,
	created_at timestamp with time zone default now(),
	website_id bigint default 0 not null
		constraint fk_product_relationships_website
			references public.websites
				on delete cascade,
	id bigint generated always as identity
		constraint product_relationships_pkey
			primary key,
	constraint uq_product_relationships_natural
		unique (parent_product_id, child_product_id, relationship_type, website_id)
);

comment on table public.product_relationships is 'Stores relationships between products, such as parent-variant, grouped items, etc. Enforces that a child product can only have one parent for a specific relationship type.';

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

create table if not exists public.product_variant_config
(
	product_id bigint not null
		constraint product_variant_config_product_id_fkey
			references public.products
				on delete cascade,
	website_id integer not null
		constraint product_variant_config_website_id_fkey
			references public.websites
				on delete cascade,
	variant_attributes text[],
	attribute_config jsonb default '{}'::jsonb,
	constraint product_variant_config_pkey
		primary key (product_id, website_id)
);

create index if not exists idx_product_variant_config_lookup
	on public.product_variant_config (product_id, website_id);

create table if not exists public.product_website_details
(
	product_id bigint not null
		constraint product_website_details_product_id_fkey
			references public.products
				on delete cascade,
	website_id integer not null
		constraint product_website_details_website_id_fkey
			references public.websites,
	name text,
	sku varchar(255),
	base_image_url text,
	default_url text,
	url_type url_type default 'external'::url_type,
	is_active boolean default true,
	sellable boolean default true not null,
	attribute_data jsonb default '{}'::jsonb,
	meta_data jsonb default '{}'::jsonb,
	crawler_meta jsonb default '{}'::jsonb,
	seo_data jsonb default '{"robots": "index,follow"}'::jsonb,
	created_at timestamp with time zone default now(),
	updated_at timestamp with time zone,
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

create table if not exists public.stores
(
	id serial
		constraint stores_pkey
			primary key,
	website_id integer
		constraint stores_website_id_fkey
			references public.websites,
	name varchar(255),
	code varchar(100),
	api_code varchar(100),
	phone varchar(50),
	address_id bigint
		constraint stores_address_id_fkey
			references public.addresses,
	default_currency_code char(3)
		constraint stores_default_currency_code_fkey
			references public.currencies,
	is_active boolean default true,
	is_default boolean default false,
	is_reference_store boolean default false,
	reference_priority smallint default 0,
	meta_data jsonb default '{}'::jsonb not null,
	crawler_meta jsonb default '{}'::jsonb not null,
	deleted_reason text,
	is_deleted boolean default false,
	created_at timestamp with time zone default now(),
	updated_at timestamp with time zone,
	deleted_at timestamp with time zone,
	constraint check_deleted_status_stores
		check ((deleted_at IS NULL) = (is_deleted = false))
);

create table if not exists public.opportunity_history
(
	id bigserial
		constraint opportunity_history_pkey
			primary key,
	rule_id bigint
		constraint opportunity_history_rule_id_fkey
			references public.opportunity_rules,
	product_id bigint
		constraint opportunity_history_product_id_fkey
			references public.products,
	source_store_id integer
		constraint opportunity_history_source_store_id_fkey
			references public.stores,
	target_store_id integer
		constraint opportunity_history_target_store_id_fkey
			references public.stores,
	source_price numeric(10,2),
	target_price numeric(10,2),
	price_difference numeric(10,2),
	difference_percentage numeric(5,2),
	currency_code char(3)
		constraint opportunity_history_currency_code_fkey
			references public.currencies,
	meta_data jsonb default '{}'::jsonb,
	created_at timestamp with time zone default now(),
	updated_at timestamp with time zone default now(),
	constraint opportunity_history_rule_product_key
		unique (rule_id, product_id)
);

create index if not exists idx_opportunity_history_product
	on public.opportunity_history (product_id asc, created_at desc) include (source_store_id, target_store_id, price_difference, difference_percentage);

create index if not exists idx_opportunity_history_rule
	on public.opportunity_history (rule_id asc, created_at desc) include (product_id, source_store_id, target_store_id, price_difference);

create index if not exists idx_opportunity_history_updated_at
	on public.opportunity_history (updated_at desc);

create table if not exists public.product_marketplace_metrics
(
	product_id bigint not null
		constraint fk_pmm_product
			references public.products
				on delete cascade,
	store_id integer not null
		constraint fk_pmm_store
			references public.stores
				on delete cascade,
	marketplace_product_id text not null,
	data_source data_source not null,
	updated_at timestamp with time zone default now() not null,
	sales_rank integer,
	sales_rank_30d_avg integer,
	sales_rank_90d_avg integer,
	sales_rank_365d_avg integer,
	review_count integer,
	review_rating numeric(3,2),
	monthly_sales integer,
	monthly_sales_30d_avg integer,
	monthly_sales_90d_avg integer,
	monthly_sales_365d_avg integer,
	marketplace_fee_sum numeric(10,2),
	currency_code char(3)
		constraint marketplace_currency_code_fkey
			references public.currencies,
	is_marketplace_seller boolean,
	referral_fee_percentage numeric(5,2),
	referral_fee_amount numeric(10,2),
	is_hazmat boolean,
	adult_product boolean,
	primary_identifier varchar(50),
	primary_identifier_type identifier_type,
	offer_count integer,
	additional_data jsonb default '{}'::jsonb,
	raw_data jsonb default '{}'::jsonb,
	constraint product_marketplace_metrics_pkey
		primary key (product_id, store_id, marketplace_product_id, data_source)
);

create index if not exists idx_pmm_product_store_time
	on public.product_marketplace_metrics (product_id asc, store_id asc, updated_at desc);

create index if not exists idx_pmm_store_sales_rank_time
	on public.product_marketplace_metrics (store_id asc, sales_rank asc, updated_at desc);

create index if not exists idx_pmm_store_updated_at
	on public.product_marketplace_metrics (store_id asc, updated_at desc);

create table if not exists public.product_price_aggregates
(
	product_id bigint not null
		constraint product_price_aggregates_pkey
			primary key
		constraint product_price_aggregates_product_id_fkey
			references public.products
				on delete cascade,
	min_price_usd numeric not null,
	max_price_usd numeric not null,
	min_price_store_id integer
		constraint product_price_aggregates_min_price_store_id_fkey
			references public.stores
				on delete set null,
	max_price_store_id integer
		constraint product_price_aggregates_max_price_store_id_fkey
			references public.stores
				on delete set null,
	reference_prices jsonb,
	updated_at timestamp default now(),
	profit_amount numeric(10,2) generated always as ((max_price_usd - min_price_usd)) stored,
	profit_percentage numeric(10,2) generated always as (((((max_price_usd - min_price_usd) / NULLIF(min_price_usd, (0)::numeric)) * (100)::numeric))::numeric(10,2)) stored
);

create index if not exists idx_product_price_aggregates_price_time
	on public.product_price_aggregates (min_price_usd, max_price_usd, updated_at);

create index if not exists idx_product_price_aggregates_profit
	on public.product_price_aggregates (profit_amount, profit_percentage);

create index if not exists idx_product_price_aggregates_reference_prices
	on public.product_price_aggregates using gin (reference_prices);

create index if not exists idx_product_price_aggregates_updated
	on public.product_price_aggregates (updated_at) include (product_id, min_price_usd, max_price_usd);

create table if not exists public.product_stores
(
	id bigserial
		constraint product_stores_pkey
			primary key,
	product_id bigint not null
		constraint product_stores_product_id_fkey
			references public.products
				on delete cascade,
	website_id integer not null
		constraint product_stores_website_id_fkey
			references public.websites,
	store_id integer
		constraint product_stores_store_id_fkey
			references public.stores
				on delete cascade,
	store_url text,
	query_params text,
	url_type store_url_type default 'same_as_website'::store_url_type not null,
	is_active boolean default true,
	display_order integer default 0,
	meta_data jsonb default '{}'::jsonb,
	created_at timestamp with time zone default now() not null,
	updated_at timestamp with time zone default now(),
	constraint unique_product_store
		unique (product_id, website_id, store_id)
)
with (autovacuum_vacuum_scale_factor=0.05, autovacuum_analyze_scale_factor=0.02);

create table if not exists public.inventory_history
(
	product_store_id bigint not null
		constraint fk_inventory_history_product_store
			references public.product_stores
				on delete cascade,
	previous_stock_qty integer,
	new_stock_qty integer not null,
	previous_stock_status stock_status,
	new_stock_status stock_status not null,
	previous_manage_stock boolean,
	new_manage_stock boolean not null,
	change_type inventory_change_type not null,
	date_changed timestamp with time zone default now() not null,
	constraint inventory_history_pkey
		primary key (product_store_id, date_changed)
)
partition by RANGE (date_changed);

create table if not exists public.inventory_history_2025_q1
partition of public.inventory_history
(
	constraint fk_inventory_history_product_store
		foreign key (product_store_id) references public.product_stores
			on delete cascade
)
FOR VALUES FROM ('2025-01-01 00:00:00+00') TO ('2025-04-01 00:00:00+00');

create table if not exists public.inventory_history_2025_q2
partition of public.inventory_history
(
	constraint fk_inventory_history_product_store
		foreign key (product_store_id) references public.product_stores
			on delete cascade
)
FOR VALUES FROM ('2025-04-01 00:00:00+00') TO ('2025-07-01 00:00:00+00');

create table if not exists public.inventory_history_2025_q3
partition of public.inventory_history
(
	constraint fk_inventory_history_product_store
		foreign key (product_store_id) references public.product_stores
			on delete cascade
)
FOR VALUES FROM ('2025-07-01 00:00:00+00') TO ('2025-10-01 00:00:00+00');

create table if not exists public.inventory_history_2025_q4
partition of public.inventory_history
(
	constraint fk_inventory_history_product_store
		foreign key (product_store_id) references public.product_stores
			on delete cascade
)
FOR VALUES FROM ('2025-10-01 00:00:00+00') TO ('2026-01-01 00:00:00+00');

create table if not exists public.inventory_history_2026_q1
partition of public.inventory_history
(
	constraint fk_inventory_history_product_store
		foreign key (product_store_id) references public.product_stores
			on delete cascade
)
FOR VALUES FROM ('2026-01-01 00:00:00+00') TO ('2026-04-01 00:00:00+00');

create table if not exists public.inventory_history_2026_q2
partition of public.inventory_history
(
	constraint fk_inventory_history_product_store
		foreign key (product_store_id) references public.product_stores
			on delete cascade
)
FOR VALUES FROM ('2026-04-01 00:00:00+00') TO ('2026-07-01 00:00:00+00');

create table if not exists public.price_history
(
	product_store_id bigint not null
		constraint fk_price_history_product_store
			references public.product_stores
				on delete cascade,
	currency_code char(3)
		constraint price_history_currency_code_fkey
			references public.currencies,
	previous_regular_price numeric(10,2),
	new_regular_price numeric(10,2),
	previous_sale_price numeric(10,2),
	new_sale_price numeric(10,2),
	previous_effective_price numeric(10,2),
	new_effective_price numeric(10,2),
	date_changed timestamp with time zone default now() not null,
	constraint price_history_pkey
		primary key (product_store_id, date_changed)
)
partition by RANGE (date_changed);

create index if not exists idx_price_history_product_store_date_desc
	on public.price_history (product_store_id asc, date_changed desc) include (previous_effective_price, new_effective_price, currency_code);

create table if not exists public.price_history_2025_q1
partition of public.price_history
(
	constraint fk_price_history_product_store
		foreign key (product_store_id) references public.product_stores
			on delete cascade,
	constraint price_history_currency_code_fkey
		foreign key (currency_code) references public.currencies
)
FOR VALUES FROM ('2025-01-01 00:00:00+00') TO ('2025-04-01 00:00:00+00');

create table if not exists public.price_history_2025_q2
partition of public.price_history
(
	constraint fk_price_history_product_store
		foreign key (product_store_id) references public.product_stores
			on delete cascade,
	constraint price_history_currency_code_fkey
		foreign key (currency_code) references public.currencies
)
FOR VALUES FROM ('2025-04-01 00:00:00+00') TO ('2025-07-01 00:00:00+00');

create table if not exists public.price_history_2025_q3
partition of public.price_history
(
	constraint fk_price_history_product_store
		foreign key (product_store_id) references public.product_stores
			on delete cascade,
	constraint price_history_currency_code_fkey
		foreign key (currency_code) references public.currencies
)
FOR VALUES FROM ('2025-07-01 00:00:00+00') TO ('2025-10-01 00:00:00+00');

create table if not exists public.price_history_2025_q4
partition of public.price_history
(
	constraint fk_price_history_product_store
		foreign key (product_store_id) references public.product_stores
			on delete cascade,
	constraint price_history_currency_code_fkey
		foreign key (currency_code) references public.currencies
)
FOR VALUES FROM ('2025-10-01 00:00:00+00') TO ('2026-01-01 00:00:00+00');

create table if not exists public.price_history_2026_q1
partition of public.price_history
(
	constraint fk_price_history_product_store
		foreign key (product_store_id) references public.product_stores
			on delete cascade,
	constraint price_history_currency_code_fkey
		foreign key (currency_code) references public.currencies
)
FOR VALUES FROM ('2026-01-01 00:00:00+00') TO ('2026-04-01 00:00:00+00');

create table if not exists public.price_history_2026_q2
partition of public.price_history
(
	constraint fk_price_history_product_store
		foreign key (product_store_id) references public.product_stores
			on delete cascade,
	constraint price_history_currency_code_fkey
		foreign key (currency_code) references public.currencies
)
FOR VALUES FROM ('2026-04-01 00:00:00+00') TO ('2026-07-01 00:00:00+00');

create table if not exists public.product_store_inventory
(
	id bigserial
		constraint product_store_inventory_pkey
			primary key,
	product_store_id bigint not null
		constraint unique_product_store_inventory
			unique
		constraint product_store_inventory_product_store_id_fkey
			references public.product_stores
				on delete cascade,
	stock_qty integer,
	stock_status stock_status default 'in_stock'::stock_status not null,
	manage_stock boolean default true not null,
	updated_at timestamp with time zone default CURRENT_TIMESTAMP,
	meta_data jsonb default '{}'::jsonb
)
with (autovacuum_vacuum_scale_factor=0.05, autovacuum_analyze_scale_factor=0.02);

create index if not exists idx_product_store_inventory_date
	on public.product_store_inventory using brin (updated_at);

create index if not exists idx_product_store_inventory_store
	on public.product_store_inventory (product_store_id);

create index if not exists idx_product_store_inventory_status
	on public.product_store_inventory (product_store_id, stock_status) include (stock_qty);

create trigger on_product_store_inventory_change
	after insert or update
	on public.product_store_inventory
	for each row
	execute procedure public.log_inventory_change();

comment on trigger on_product_store_inventory_change on public.product_store_inventory is 'Logs inventory changes to inventory_history';

create trigger on_inventory_stock_status_change
	after insert or update
	on public.product_store_inventory
	for each row
	execute procedure public.queue_product_price_update();

comment on trigger on_inventory_stock_status_change on public.product_store_inventory is 'Queues product update when stock_status changes';

create table if not exists public.product_store_prices
(
	id bigserial
		constraint product_store_prices_pkey
			primary key,
	product_store_id bigint not null
		constraint product_store_prices_product_store_id_fkey
			references public.product_stores
				on delete cascade,
	currency_code char(3) not null
		constraint product_store_prices_currency_code_fkey
			references public.currencies,
	regular_price numeric(10,2) not null
		constraint product_store_prices_regular_price_check
			check (regular_price >= (0)::numeric),
	sale_price numeric(10,2),
	price numeric(10,2) generated always as (
CASE
    WHEN (sale_price IS NOT NULL) THEN sale_price
    ELSE regular_price
END) stored,
	meta_data jsonb default '{}'::jsonb,
	updated_at timestamp with time zone,
	constraint unique_product_store_currency
		unique (product_store_id, currency_code),
	constraint product_store_prices_check
		check ((sale_price IS NULL) OR ((sale_price <= regular_price) AND (sale_price >= (0)::numeric)))
)
with (autovacuum_vacuum_scale_factor=0.05, autovacuum_analyze_scale_factor=0.02);

create index if not exists idx_product_store_prices_date
	on public.product_store_prices using brin (updated_at);

create index if not exists idx_product_store_prices_store
	on public.product_store_prices (product_store_id);

create trigger on_product_store_price_change
	after insert or update
	on public.product_store_prices
	for each row
	execute procedure public.log_price_change();

comment on trigger on_product_store_price_change on public.product_store_prices is 'Logs price changes to price_history';

create trigger on_price_change_queue
	after insert or update
	on public.product_store_prices
	for each row
	execute procedure public.queue_product_price_update();

comment on trigger on_price_change_queue on public.product_store_prices is 'Queues product update when price changes';

create index if not exists idx_product_stores_store
	on public.product_stores (store_id);

create index if not exists idx_product_stores_product
	on public.product_stores (product_id);

create table if not exists public.store_company_address_distances
(
	store_id integer not null
		constraint store_company_address_distances_store_id_fkey
			references public.stores
				on delete cascade,
	company_address_id bigint not null
		constraint store_company_address_distances_address_id_fkey
			references public.addresses
				on delete cascade,
	distance numeric(10,2) not null,
	distance_unit distance_unit_enum default 'km'::distance_unit_enum not null,
	calculation_method distance_calculation_method_enum default 'unknown'::distance_calculation_method_enum not null,
	created_at timestamp with time zone default now(),
	updated_at timestamp with time zone,
	constraint store_company_address_distances_pkey
		primary key (store_id, company_address_id, calculation_method)
);

create index if not exists idx_store_company_distances_addr_store_method
	on public.store_company_address_distances (company_address_id, store_id, calculation_method);

create index if not exists idx_store_company_distances_store_addr_method
	on public.store_company_address_distances (store_id, company_address_id, calculation_method);

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

create table if not exists public.website_countries
(
	website_id integer not null
		constraint website_countries_website_id_fkey
			references public.websites
				on delete cascade,
	country_code char(2) not null
		constraint website_countries_country_code_fkey
			references public.countries,
	created_at timestamp with time zone default now(),
	constraint website_countries_pkey
		primary key (website_id, country_code)
);

create index if not exists idx_websites_vendor
	on public.websites (vendor_id)
	where ((deleted_at IS NULL) AND (is_deleted = false) AND (is_active = true));

create unique index if not exists unique_website_code
	on public.websites (code)
	where ((deleted_at IS NULL) AND (is_deleted = false) AND (is_active = true));

create index if not exists idx_websites_code_lower
	on public.websites (lower(code::text))
	where ((deleted_at IS NULL) AND (is_deleted = false));

create table if not exists public.product_identifier_websites
(
	website_id integer not null
		constraint product_identifier_websites_website_id_fkey
			references public.websites
				on delete cascade,
	product_identifier_id bigint not null
		constraint product_identifier_websites_product_identifier_id_fkey
			references public.product_identifiers
				on delete cascade,
	constraint product_identifier_websites_pkey
		primary key (product_identifier_id, website_id)
);

create index if not exists idx_product_identifier_websites_identifier
	on public.product_identifier_websites (product_identifier_id) include (website_id);

create index if not exists idx_product_identifier_websites_website
	on public.product_identifier_websites (website_id) include (product_identifier_id);

create table if not exists public.category_paths
(
	category_id integer not null
		constraint category_paths_pkey
			primary key,
	level_1_id integer,
	level_2_id integer,
	level_3_id integer,
	level_4_id integer,
	level_5_id integer,
	full_path text not null,
	path_length integer not null,
	updated_at timestamp with time zone default now()
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

create or replace function public.create_history_partitions(start_date timestamp with time zone, num_future_partitions integer DEFAULT 4) returns void
	language plpgsql
as $$
DECLARE
    partition_start timestamp with time zone;
    partition_end timestamp with time zone;
    partition_name text;
    quarter text;
    year text;
BEGIN
    FOR i IN 0..num_future_partitions-1 LOOP
        partition_start := date_trunc('quarter', start_date + (i * interval '3 months'));
        partition_end := partition_start + interval '3 months';
        year := to_char(partition_start, 'YYYY');
        quarter := 'q' || to_char(partition_start, 'Q');
        
        -- Create inventory history partition
        partition_name := 'inventory_history_' || year || '_' || quarter;
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF inventory_history 
            FOR VALUES FROM (%L) TO (%L)',
            partition_name, partition_start, partition_end
        );
        
        -- Create price history partition
        partition_name := 'price_history_' || year || '_' || quarter;
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF price_history 
            FOR VALUES FROM (%L) TO (%L)',
            partition_name, partition_start, partition_end
        );
    END LOOP;
END;
$$;

create or replace function public.get_category_and_descendants(root_category_id integer) returns SETOF integer
	stable
	language sql
as $$
    WITH RECURSIVE category_tree AS (
        -- Base case: Start with the initial root category ID
        SELECT id
        FROM public.categories
        WHERE id = root_category_id

        UNION ALL

        -- Recursive step: Find children of categories already in the tree
        SELECT c.id
        FROM public.categories c
        JOIN category_tree ct ON c.parent_id = ct.id
        -- Only follow active, non-deleted paths
        WHERE c.deleted_at IS NULL AND c.is_active = TRUE
    )
    -- Select all unique IDs found in the tree
    SELECT id FROM category_tree;
$$;

comment on function public.get_category_and_descendants(integer) is 'Returns a set containing the input category ID and all its active descendant category IDs.';

create or replace function public.log_inventory_change() returns trigger
	language plpgsql
as $$
BEGIN
    -- Log inventory changes to inventory_history
    IF (TG_OP = 'INSERT') OR
       (OLD.stock_qty IS DISTINCT FROM NEW.stock_qty) OR
       (OLD.stock_status IS DISTINCT FROM NEW.stock_status) OR
       (OLD.manage_stock IS DISTINCT FROM NEW.manage_stock) THEN

        INSERT INTO inventory_history (
            previous_stock_qty,
            new_stock_qty,
            change_type,
            previous_stock_status,
            new_stock_status,
            previous_manage_stock,
            new_manage_stock,
            product_store_id,
            date_changed
        ) VALUES (
            CASE WHEN TG_OP = 'UPDATE' THEN OLD.stock_qty ELSE NEW.stock_qty END,
            NEW.stock_qty,
            CASE
                WHEN TG_OP = 'INSERT' THEN 'initial'::inventory_change_type
                WHEN NEW.stock_qty = 0 AND NEW.stock_status = 'out_of_stock' THEN 'decrease'::inventory_change_type
                WHEN NEW.stock_status = 'out_of_stock' AND OLD.stock_status = 'in_stock' AND NEW.manage_stock = true THEN 'decrease'::inventory_change_type
                WHEN NEW.stock_status = 'in_stock' AND OLD.stock_status = 'out_of_stock' THEN 'increase'::inventory_change_type
                WHEN NEW.stock_status = 'out_of_stock' AND NEW.stock_qty > 0 AND NEW.manage_stock = false THEN 'system'::inventory_change_type
                WHEN NEW.stock_qty > OLD.stock_qty THEN 'increase'::inventory_change_type
                WHEN NEW.stock_qty < OLD.stock_qty THEN 'decrease'::inventory_change_type
                ELSE 'update'::inventory_change_type
            END,
            CASE WHEN TG_OP = 'UPDATE' THEN OLD.stock_status ELSE NEW.stock_status END,
            NEW.stock_status,
            CASE WHEN TG_OP = 'UPDATE' THEN OLD.manage_stock ELSE NEW.manage_stock END,
            NEW.manage_stock,
            NEW.product_store_id,
            CURRENT_TIMESTAMP
        );
    END IF;

    RETURN NEW;
END;
$$;

comment on function public.log_inventory_change() is 'Logs inventory changes to inventory_history table. Handles both INSERT and UPDATE operations on product_store_inventory.';

create or replace function public.log_price_change() returns trigger
	language plpgsql
as $$
BEGIN
    -- Log price changes to price_history
    IF (TG_OP = 'INSERT') OR
       (OLD.regular_price != NEW.regular_price) OR
       (OLD.sale_price IS DISTINCT FROM NEW.sale_price) THEN

        INSERT INTO price_history (
            currency_code,
            previous_regular_price,
            new_regular_price,
            previous_sale_price,
            new_sale_price,
            product_store_id,
            date_changed,
            previous_effective_price,
            new_effective_price
        ) VALUES (
            NEW.currency_code,
            CASE WHEN TG_OP = 'UPDATE' THEN OLD.regular_price ELSE NEW.regular_price END,
            NEW.regular_price,
            CASE WHEN TG_OP = 'UPDATE' THEN OLD.sale_price ELSE NEW.sale_price END,
            NEW.sale_price,
            NEW.product_store_id,
            CURRENT_TIMESTAMP,
            CASE WHEN TG_OP = 'UPDATE' THEN OLD.price ELSE NEW.price END,
            NEW.price
        );
    END IF;

    RETURN NEW;
END;
$$;

comment on function public.log_price_change() is 'Logs price changes to price_history table. Handles both INSERT and UPDATE operations on product_store_prices.';

create or replace function public.maintain_history_partitions() returns void
	language plpgsql
as $$
BEGIN
    -- Create partitions for next 2 quarters (2 quarters)
    PERFORM create_history_partitions(date_trunc('quarter', CURRENT_DATE + interval '3 months'), 2);
END;
$$;

create or replace function public.refresh_category_paths() returns void
	language plpgsql
as $$
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

create or replace function public.find_category_by_path(search_path text) returns TABLE(category_id integer, full_path text, path_length integer)
	language plpgsql
as $$
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

create or replace function public.get_category_path(cat_id integer) returns TABLE(category_id integer, level_1_id integer, level_2_id integer, level_3_id integer, level_4_id integer, level_5_id integer, full_path text, path_length integer)
	language plpgsql
as $$
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

create or replace function public.refresh_single_category_path(cat_id integer) returns void
	language plpgsql
as $$
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

create or replace function public.trigger_category_paths_update() returns trigger
	language plpgsql
as $$
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

create or replace function public.trigger_category_paths_bulk_refresh() returns trigger
	language plpgsql
as $$
BEGIN
    PERFORM refresh_category_paths();
    RETURN NULL;
END;
$$;

