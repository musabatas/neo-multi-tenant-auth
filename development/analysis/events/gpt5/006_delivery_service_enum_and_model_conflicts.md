# Delivery service enum and model conflicts

## Summary
`WebhookDeliveryService` uses status values and fields not defined in `DeliveryStatus` or the `WebhookDelivery` entity, and diverges from the per-attempt delivery schema.

## Evidence
- Service assigns non-existent enum value and fields:
```156:175:neo-commons/src/neo_commons/features/events/services/webhook_delivery_service.py
if delivery.attempt_count < delivery.max_attempts:
    delivery.status = DeliveryStatus.RETRY_SCHEDULED  # not in enum
    delivery.next_retry_at = self._calculate_next_retry_time(delivery.attempt_count)
...
else:
    delivery.status = DeliveryStatus.EXHAUSTED
```
- Enum values differ and include `DELIVERED`, `EXHAUSTED`, `CIRCUIT_BREAKER_OPEN` not present in schema valid set:
```16:27:neo-commons/src/neo_commons/features/events/entities/webhook_delivery.py
class DeliveryStatus(Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    EXHAUSTED = "exhausted"
    DELIVERED = "delivered"
```
- Schema `valid_delivery_status` constraint allows only: pending, success, failed, timeout, retrying, cancelled.
```249:253:NeoInfrastructure/migrations/flyway/admin/V1012__create_webhook_infrastructure.sql
CONSTRAINT valid_delivery_status CHECK (
    delivery_status IN ('pending', 'success', 'failed', 'timeout', 'retrying', 'cancelled')
)
```
- Service treats delivery as aggregate with `attempt_count`, `delivered_at`, `updated_at`, not present in schema rows that are per-attempt with `attempt_number`, `attempted_at`, `completed_at`.

## Impact
- Enum errors at runtime; DB constraint violations on invalid status values; broken persistence and retry logic.

## Recommendations
- Restrict `DeliveryStatus` to schema-allowed values and map circuit/open/exhausted states to allowed set (e.g., use `failed` plus flags).
- Rework service to create per-attempt records using `request_*`/`response_*` fields and manage next retry time based on endpoint retry policy.
- If aggregate tracking is needed, introduce an aggregate table or compute from last attempt.

