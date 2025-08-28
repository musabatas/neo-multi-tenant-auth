create or replace view public.scrapy_commands
            (website_id, store_id, website_url, website_default_currency, command, command_with_operation_type) as
SELECT w.id                                                                                            AS website_id,
       s.id                                                                                            AS store_id,
       w.url                                                                                           AS website_url,
       w.default_currency_code                                                                         AS website_default_currency,
       concat('scrapy crawl shopify_universal', ' -a url=', w.url, ' -a currency=',
              COALESCE(s.default_currency_code, w.default_currency_code, 'USD'::bpchar), ' -a api_enabled=true',
              ' -a website_id=', w.id, ' -a store_id=', s.id, ' -L INFO')                              AS command,
       concat('scrapy crawl shopify_universal', ' -a url=', w.url, ' -a currency=',
              COALESCE(s.default_currency_code, w.default_currency_code, 'USD'::bpchar), ' -a api_enabled=true',
              ' -a website_id=', w.id, ' -a store_id=', s.id, ' -a operation_type=upsert',
              ' -L INFO')                                                                              AS command_with_operation_type
FROM websites w
         JOIN collector.website_spiders ws ON w.id = ws.website_id
         JOIN stores s ON w.id = s.website_id
WHERE ws.spider_id = 1
  AND ws.is_enabled = true
  AND w.is_active = true
  AND w.is_deleted = false
  AND w.deleted_at IS NULL
  AND s.is_active = true
  AND s.is_deleted = false
  AND s.deleted_at IS NULL
  AND w.url IS NOT NULL
ORDER BY w.id, s.id;

