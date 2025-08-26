# DomainEvent repository schema/table mismatches

## Summary
`DomainEventDatabaseRepository` correctly targets `{schema}.webhook_events`, but other parts of metrics code use `domain_events` table naming not present in the migration.

## Evidence
- Migration defines `admin.webhook_events`:
```168:206:NeoInfrastructure/migrations/flyway/admin/V1012__create_webhook_infrastructure.sql
CREATE TABLE IF NOT EXISTS admin.webhook_events (
  id UUID PRIMARY KEY DEFAULT gen_uuid_v7(),
  event_type VARCHAR(255) NOT NULL,
  ...
);
```
- Repository uses `webhook_events` consistently:
```51:54:neo-commons/src/neo_commons/features/events/repositories/domain_event_repository.py
self._table = f"{schema}.webhook_events"
```
- Metrics service uses `domain_events` (non-existent):
```964:974:neo-commons/src/neo_commons/features/events/services/webhook_metrics_service.py
query = f"SELECT COUNT(*) FROM {self._schema}.domain_events"
...
query = f"SELECT COUNT(*) FROM {self._schema}.domain_events WHERE processed_at IS NOT NULL"
```

## Impact
- Metrics endpoints will fail with "relation does not exist" errors.

## Recommendations
- Replace `domain_events` with `webhook_events` in metrics service queries.
- Add integration test to catch table name regressions.

