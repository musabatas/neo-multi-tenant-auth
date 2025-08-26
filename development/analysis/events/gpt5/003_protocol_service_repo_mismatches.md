# Protocol vs repository/service mismatches

## Summary
Services call protocol methods that repositories don’t implement; several optimized methods referenced by services don’t exist, causing runtime failures.

## Evidence
- Services expect optimized domain event methods:
```200:211:neo-commons/src/neo_commons/features/events/services/event_dispatcher_service.py
unprocessed_events = await self._event_repository.get_unprocessed_for_update(
    limit=actual_limit,
    skip_locked=True,
    select_columns=select_columns
)
```
- Protocol defines them:
```56:73:neo-commons/src/neo_commons/features/events/entities/protocols.py
async def get_unprocessed_for_update(...): ...
```
- Repository lacks implementations (no `get_unprocessed_for_update`, `get_unprocessed_paginated`, `mark_multiple_as_processed_bulk`, `count_unprocessed`, `count_processing`):
```37:259:neo-commons/src/neo_commons/features/events/repositories/domain_event_repository.py
# implements save/get/get_unprocessed/mark_as_processed/mark_multiple_as_processed/... but not the optimized variants
```
- Services expect optimized subscription query:
```988:997:neo-commons/src/neo_commons/features/events/services/event_dispatcher_service.py
matching_subscriptions = await self._subscription_repository.get_matching_subscriptions_optimized(
    event.event_type.value,
    event.context_id,
    select_columns=["id", "endpoint_id", "event_filters", "is_active"],
    use_index_only=True
)
```
- Protocol defines it:
```285:303:neo-commons/src/neo_commons/features/events/entities/protocols.py
async def get_matching_subscriptions_optimized(...): ...
```
- Repository doesn’t implement `get_matching_subscriptions_optimized`:
```37:246:neo-commons/src/neo_commons/features/events/repositories/webhook_subscription_repository.py
# only get_matching_subscriptions() exists
```

## Impact
- Event dispatching paths will raise `AttributeError`/`NotImplementedError` at runtime.
- Parallel/optimized flows can’t run; performance and correctness degrade.

## Recommendations
- Add the missing methods to repositories with SQL support (FOR UPDATE SKIP LOCKED, selective columns, bulk updates).
- Alternatively, update services to use only the implemented repository methods until optimized versions are added.
- Ensure protocol, services, and repositories stay in lockstep; add tests for interface adherence.

