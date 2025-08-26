# WebhookDelivery repository/query mismatches

## Summary
The `WebhookDeliveryDatabaseRepository` uses undefined query constants, wrong parameter orders/counts, and fields not present in the schema.

## Evidence
- Undefined constants imported and used:
```12:40:neo-commons/src/neo_commons/features/events/repositories/webhook_delivery_repository.py
from ..utils.queries import (
    WEBHOOK_DELIVERY_INSERT,
    WEBHOOK_DELIVERY_UPDATE,
    WEBHOOK_DELIVERY_GET_BY_ID,
    WEBHOOK_DELIVERY_GET_PENDING_RETRIES,
    WEBHOOK_DELIVERY_GET_BY_ENDPOINT,
    WEBHOOK_DELIVERY_GET_BY_EVENT,
    WEBHOOK_DELIVERY_GET_DELIVERY_STATS,
    WEBHOOK_DELIVERY_DELETE,
)
```
```215:299:neo-commons/src/neo_commons/features/events/utils/queries.py
WEBHOOK_DELIVERY_GET_STATS = """
    SELECT 
        COUNT(*) as total_attempts,
        COUNT(CASE WHEN delivery_status = 'success' THEN 1 END) as successful_deliveries,
        ...
"""
```
- Param count/order mismatch for pending retries (repo provides 2 args, query expects 1 `LIMIT` and uses NOW() inline):
```100:116:neo-commons/src/neo_commons/features/events/repositories/webhook_delivery_repository.py
query = WEBHOOK_DELIVERY_GET_PENDING_RETRIES.format(schema=self._schema)
current_time = datetime.now(timezone.utc)
rows = await self._db.fetch(query, current_time, limit)
```
```252:259:neo-commons/src/neo_commons/features/events/utils/queries.py
SELECT * FROM {schema}.webhook_deliveries 
WHERE delivery_status = 'retrying' 
AND next_retry_at <= NOW() 
AND max_attempts_reached = false
ORDER BY next_retry_at ASC
LIMIT $1
```
- Repository fields don’t exist in schema (`delivery_url`, `headers`, `payload`, `signature`, `status`, `attempt_count`, `delivered_at`, `updated_at`):
```59:79:neo-commons/src/neo_commons/features/events/repositories/webhook_delivery_repository.py
row = await self._db.fetchrow(
    query,
    delivery.id.value,
    delivery.event_id.value,
    delivery.endpoint_id.value,
    delivery.delivery_url,
    delivery.http_method,
    json.dumps(delivery.headers) if delivery.headers else None,
    json.dumps(delivery.payload),
    delivery.signature,
    delivery.status.value,
    delivery.attempt_count,
    delivery.max_attempts,
    delivery.next_retry_at,
    json.dumps(delivery.last_error) if delivery.last_error else None,
    delivery.delivered_at,
    delivery.created_at,
    delivery.updated_at,
)
```
```212:262:NeoInfrastructure/migrations/flyway/admin/V1012__create_webhook_infrastructure.sql
CREATE TABLE IF NOT EXISTS admin.webhook_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_uuid_v7(),
    webhook_endpoint_id UUID NOT NULL,
    webhook_event_id UUID NOT NULL,
    attempt_number INTEGER NOT NULL DEFAULT 1,
    delivery_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    request_url TEXT NOT NULL,
    request_method VARCHAR(10) NOT NULL,
    request_headers JSONB NOT NULL DEFAULT '{}',
    request_body TEXT,
    request_signature VARCHAR(255),
    response_status_code INTEGER,
    response_headers JSONB,
    response_body TEXT,
    response_time_ms INTEGER,
    error_message TEXT,
    error_code VARCHAR(100),
    next_retry_at TIMESTAMPTZ,
    max_attempts_reached BOOLEAN NOT NULL DEFAULT false,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## Impact
- Runtime errors due to missing constants and wrong parameter counts.
- Inserts/updates will fail due to column/field mismatches.

## Recommendations
- Replace `WEBHOOK_DELIVERY_GET_DELIVERY_STATS` with `WEBHOOK_DELIVERY_GET_STATS`; drop `WEBHOOK_DELIVERY_DELETE` or add it in queries if needed.
- Fix `get_pending_retries` to pass only `limit` or change query to parameterize timestamp.
- Rework save/update/_row_to_delivery to align with schema columns (`request_*`, `response_*`, `attempt_number`, `delivery_status`, timestamps). Align names consistently with entity and services (see 001).

