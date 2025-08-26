# Queries module mismatches and missing definitions

## Summary
Imports in repositories reference query constants that don’t exist, and some repository modules import database protocols from a different package path than used elsewhere.

## Evidence
- Delivery repo imports non-existent `WEBHOOK_DELIVERY_DELETE`, `WEBHOOK_DELIVERY_GET_DELIVERY_STATS`:
```17:26:neo-commons/src/neo_commons/features/events/repositories/webhook_delivery_repository.py
from ..utils.queries import (
    ...
    WEBHOOK_DELIVERY_GET_DELIVERY_STATS,
    WEBHOOK_DELIVERY_DELETE,
)
```
- Queries file defines `WEBHOOK_DELIVERY_GET_STATS` only and no delete:
```274:286:neo-commons/src/neo_commons/features/events/utils/queries.py
WEBHOOK_DELIVERY_GET_STATS = """
    SELECT ...
"""
```
- Mixed database protocol import paths across repos:
```14:16:neo-commons/src/neo_commons/features/events/repositories/webhook_endpoint_repository.py
from ....features.database.entities.protocols import DatabaseRepository
```
```7:8:neo-commons/src/neo_commons/features/events/repositories/event_archival_repository.py
from neo_commons.infrastructure.database.base_repository import DatabaseRepository
```

## Impact
- Import errors at runtime; failing stats/deletes; inconsistent dependency boundaries.

## Recommendations
- Standardize on `....features.database.entities.protocols.DatabaseRepository` (or the correct shared interface) across all repos.
- Add missing constants if needed: `WEBHOOK_DELIVERY_DELETE`, or remove usages and provide soft-delete/cleanup via designed API.
- Rename usages to `WEBHOOK_DELIVERY_GET_STATS` to match existing constant.

