# Archival repositories vs migration schema alignment

## Summary
Archival repositories use unqualified table names (`event_archives`, `archival_rules`, `archival_jobs`) without schema prefix and import a different `DatabaseRepository` path than other repos. Migration defines these tables under `admin` schema.

## Evidence
- Migration defines archival tables in `admin` schema:
```405:461:NeoInfrastructure/migrations/flyway/admin/V1012__create_webhook_infrastructure.sql
CREATE TABLE IF NOT EXISTS admin.event_archives (...)
...
CREATE TABLE IF NOT EXISTS admin.archival_rules (...)
...
CREATE TABLE IF NOT EXISTS admin.archival_jobs (...)
```
- Repository SQL lacks `{schema}.` prefix and imports infra DB repository directly:
```154:178:neo-commons/src/neo_commons/features/events/repositories/event_archival_repository.py
INSERT INTO event_archives (
  ...
)
```
```7:7:neo-commons/src/neo_commons/features/events/repositories/event_archival_repository.py
from neo_commons.infrastructure.database.base_repository import DatabaseRepository
```

## Impact
- Queries will target default search_path instead of `admin` or tenant schema; multi-tenant scenarios will break.
- Divergent DB repository type reduces consistency and testability.

## Recommendations
- Add `schema` parameter to archival repositories and prefix tables with `{schema}.`.
- Align DB repository import to the same protocol used elsewhere.
- Ensure archival entity enums match migration allowed values; add queries for indexes if needed.

