-- Create currencies table.
create table if not exists public.currencies
(
    code          char(3)     not null
        constraint currencies_pkey
            primary key,
    name          varchar(50) not null,
    symbol        char(5),
    exchange_rate numeric(10, 5),
    updated_at    timestamp with time zone default now(),
    is_active     boolean                  default true
);

-- Create indexes for currencies table.
create index if not exists idx_currencies_exchange_rate
    on public.currencies (exchange_rate asc, updated_at desc);

-- Create countries table.
create table if not exists public.countries
(
    code          varchar(2)   not null
        constraint countries_pkey
            primary key,
    name          varchar(100) not null,
    iso2          char(2),
    iso3          char(3),
    local_name    varchar(255),
    continent     continents,
    capital       varchar(255),
    currency_code char(3)
        constraint countries_currency_code_fkey
            references public.currencies,
    currency_name varchar(100),
    tld           char(3),
    phone_code    varchar(20),
    languages     varchar(255),
    timezone      varchar(100),
    region        varchar(100),
    population    serial,
    area_km2      numeric(10, 2)
);

-- Create indexes for countries table.
create index if not exists idx_countries_search
    on public.countries (name, iso2, iso3) include (currency_code, timezone, region);

create index if not exists idx_countries_region
    on public.countries (region, continent) include (code, name, currency_code);

-- Create languages table.
create table if not exists public.languages
(
    code        char(5)      not null
        constraint languages_pkey
            primary key,
    name        varchar(100) not null,
    native_name varchar(100),
    direction   varchar(3) default 'ltr'::character varying,
    is_active   boolean    default true,
    sort_order  integer,
    region_code char(4)
);

-- Create indexes for languages table.
create index if not exists idx_languages_active
    on public.languages (is_active)
    where (is_active = true);


CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Profile Information (fields not in auth.users)
    username TEXT UNIQUE,
    first_name TEXT,
    last_name TEXT,
    display_name TEXT,
    avatar_url TEXT,
    bio TEXT,
    
    -- Permission Cache (only for users with direct permissions)
    has_direct_permissions BOOLEAN DEFAULT false,
    direct_permissions TEXT[] DEFAULT ARRAY[]::TEXT[],
    denied_permissions TEXT[] DEFAULT ARRAY[]::TEXT[],
    
    -- Application-specific Metadata
    onboarding_completed BOOLEAN DEFAULT false,
    last_active_at TIMESTAMPTZ,
    
    -- Additional JSONB for flexibility
    metadata JSONB DEFAULT '{}'::JSONB,
    preferences JSONB DEFAULT '{}'::JSONB
);

-- Create indexes
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_last_active ON users(last_active_at);
CREATE INDEX idx_users_has_direct_permissions ON users(id) WHERE has_direct_permissions = true;

-- Enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own profile" ON users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON users
    FOR UPDATE USING (auth.uid() = id);


create table if not exists public.system_settings
(
    id            bigserial
        constraint system_settings_pkey
            primary key,
    setting_key   varchar(255)                           not null,
    setting_value jsonb                    default '{}'::jsonb,
    user_specific boolean                  default false,
    user_id       uuid
        constraint system_settings_user_id_fkey
            references public.users
            on delete set null,
    is_public     boolean                  default false not null,
    requires_auth boolean                  default false not null,
    is_active     boolean                  default true,
    active_at     timestamp with time zone,
    active_until  timestamp with time zone,
    created_at    timestamp with time zone default now(),
    updated_at    timestamp with time zone default now(),
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

-- Create user ui settings table.
create table if not exists public.user_ui_settings
(
    id            uuid                     default gen_random_uuid() not null
        constraint user_ui_settings_pkey
            primary key,
    user_id       uuid
        constraint user_ui_settings_user_id_fkey
            references auth.users
        on delete cascade,
    feature_key   text                                               not null,
    setting_key   text                                               not null,
    setting_value jsonb                                              not null,
    created_at    timestamp with time zone default now()             not null,
    updated_at    timestamp with time zone default now()             not null
);

-- Create indexes for user ui settings table.
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

-- Create policies for user ui settings table.
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

