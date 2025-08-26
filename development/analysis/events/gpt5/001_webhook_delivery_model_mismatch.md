# Webhook Delivery model and schema mismatch

## Summary
There is a fundamental mismatch between the in-memory `WebhookDelivery` entity, the repository implementation, and the database schema for deliveries.

## Evidence
- Entity definition expects an aggregate delivery with attempts:
```python
# neo-commons/src/neo_commons/features/events/entities/webhook_delivery.py
class WebhookDelivery:
    # Identification
    id: WebhookDeliveryId
    webhook_endpoint_id: WebhookEndpointId
    webhook_event_id: EventId
    # Current delivery state
    current_attempt: int = 1
    overall_status: DeliveryStatus = DeliveryStatus.PENDING
    # Retry configuration
    max_attempts: int = 3
    base_backoff_seconds: int = 5
    backoff_multiplier: float = 2.0
    # Attempt history
    attempts: List[WebhookDeliveryAttempt] = field(default_factory=list)
```
- Repository uses a completely different shape (request/response centric), not aligning with the entity above, and arguments do not match the SQL placeholders:
```python
# neo-commons/src/neo_commons/features/events/repositories/webhook_delivery_repository.py
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
- SQL schema (admin.webhook_deliveries) is per-attempt and expects columns like `attempt_number`, `delivery_status`, `request_*`, `response_*`, etc. It does not include fields like `delivery_url`, `payload`, `delivered_at`, `updated_at` used in the repository.
```sql
-- NeoInfrastructure/migrations/flyway/admin/V1012__create_webhook_infrastructure.sql
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
- Service layer also uses another conflicting shape and status values not present in `DeliveryStatus` enum (e.g., `RETRY_SCHEDULED`), and fields like `delivery_url`, `headers`, `payload`, `signature`, `attempt_count`, `last_error`, `delivered_at` that do not map to the schema.

## Impact
- Persistence of deliveries will fail at runtime due to parameter/column mismatch.
- Enum misuse (e.g., `RETRY_SCHEDULED`) can raise exceptions and break retry flows.
- Metrics, monitoring, and retries will be unreliable or inoperable.

## Recommendations
- Pick one model:
  - Either: model deliveries as per-attempt rows (align entity to schema), or
  - Keep aggregate entity, but add a separate `webhook_delivery_attempts` table and rewrite repository accordingly.
- Short-term minimal fixes:
  - Update repository to match schema and use attempt-centric writes, including correct field names (`request_*`, `response_*`).
  - Align `DeliveryStatus` usage. Remove `RETRY_SCHEDULED` or add it to the enum and reflect in schema if truly needed.
  - Update service to populate `attempt_number`, request/response and map overall state separately (e.g., compute from last attempt).
- Ensure `WebhookHeaderBuilder`/adapter populate `request_headers` consistently and persist response info into `response_*` columns.

