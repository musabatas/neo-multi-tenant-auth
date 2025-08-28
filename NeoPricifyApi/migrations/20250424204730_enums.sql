create type public.alert_status as enum ('active', 'inactive', 'triggered', 'acknowledged', 'resolved', 'snoozed', 'expired', 'deleted');

create type public.alert_type as enum ('price_change', 'stock_status', 'price_threshold', 'stock_threshold', 'competitor_price', 'margin_alert', 'trend_alert', 'promotion_alert');

create type public.attribute_input_type as enum ('text', 'number', 'select', 'multiselect', 'boolean', 'date', 'price', 'color', 'textarea', 'repeatable_text', 'repeatable_number', 'repeatable_select', 'repeatable_date', 'repeatable_price', 'repeatable_object', 'file', 'range', 'rating');

create type public.common_status as enum ('active', 'inactive', 'pending', 'archived', 'deleted');

create type public.connection_status as enum ('connected', 'disconnected', 'pending', 'failed', 'rate_limited', 'maintenance', 'deprecated', 'blocked');

create type public.continents as enum ('Europe', 'Asia', 'North America', 'South America', 'Africa', 'Oceania', 'Antarctica');

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

create type public.crawlab_task_status as enum ('pending', 'running', 'finished', 'error', 'cancelled');

create type public.verification_status as enum ('pending', 'verified', 'failed');

