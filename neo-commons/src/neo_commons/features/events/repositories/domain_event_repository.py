"""Domain event repository implementation using existing database infrastructure.

This implementation follows the patterns established in the organizations feature,
leveraging existing database service without duplicating connection management.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from datetime import datetime, timezone

from ....core.value_objects import EventId, UserId
from ....core.exceptions import EntityNotFoundError, EntityAlreadyExistsError, DatabaseError
from ....features.database.entities.protocols import DatabaseRepository
from ..entities.domain_event import DomainEvent
from ..entities.protocols import EventRepository
from ..utils.queries import (
    DOMAIN_EVENT_INSERT,
    DOMAIN_EVENT_GET_BY_ID,
    DOMAIN_EVENT_GET_BY_AGGREGATE,
    DOMAIN_EVENT_GET_UNPROCESSED,
    DOMAIN_EVENT_MARK_PROCESSED,
    DOMAIN_EVENT_MARK_MULTIPLE_PROCESSED,
    DOMAIN_EVENT_GET_BY_CORRELATION_ID,
    DOMAIN_EVENT_GET_BY_CONTEXT,
    DOMAIN_EVENT_GET_BY_EVENT_TYPE,
    DOMAIN_EVENT_GET_RECENT,
    DOMAIN_EVENT_COUNT_BY_TYPE,
)
from ..utils.error_handling import handle_domain_event_error


logger = logging.getLogger(__name__)


class DomainEventDatabaseRepository:
    """Database repository for domain event operations.
    
    Uses existing database infrastructure following DRY principles.
    Accepts any database connection and schema via dependency injection.
    """
    
    def __init__(self, database_repository: DatabaseRepository, schema: str):
        """Initialize with existing database repository.
        
        Args:
            database_repository: Database repository from neo-commons
            schema: Database schema name (admin, tenant-specific, etc.)
        """
        self._db = database_repository
        self._schema = schema
        self._table = f"{schema}.webhook_events"
    
    async def save(self, event: DomainEvent) -> DomainEvent:
        """Save a domain event to the database."""
        try:
            # Check if event already exists
            existing = await self.get_by_id(event.id)
            if existing:
                raise EntityAlreadyExistsError("DomainEvent", str(event.id.value))
            
            query = DOMAIN_EVENT_INSERT.format(schema=self._schema)
            
            row = await self._db.fetchrow(
                query,
                event.id.value,
                event.event_type.value,
                event.event_name,
                event.aggregate_id,
                event.aggregate_type,
                event.aggregate_version,
                json.dumps(event.event_data) if event.event_data else "{}",
                json.dumps(event.event_metadata) if event.event_metadata else "{}",
                event.correlation_id,
                event.causation_id,
                event.triggered_by_user_id.value if event.triggered_by_user_id else None,
                event.context_id,
                event.occurred_at,
                event.created_at,
            )
            
            if row:
                return self._row_to_event(row)
            
            return event
            
        except Exception as e:
            handle_domain_event_error("save", event.id, e, {"schema": self._schema})
            raise
    
    async def get_by_id(self, event_id: EventId) -> Optional[DomainEvent]:
        """Get a domain event by ID."""
        try:
            query = DOMAIN_EVENT_GET_BY_ID.format(schema=self._schema)
            row = await self._db.fetchrow(query, event_id.value)
            return self._row_to_event(row) if row else None
            
        except Exception as e:
            handle_domain_event_error("get_by_id", event_id, e, {"schema": self._schema})
            raise
    
    async def get_by_aggregate(self, aggregate_type: str, aggregate_id: UUID) -> List[DomainEvent]:
        """Get all events for a specific aggregate."""
        try:
            query = DOMAIN_EVENT_GET_BY_AGGREGATE.format(schema=self._schema)
            rows = await self._db.fetch(query, aggregate_type, aggregate_id)
            return [self._row_to_event(row) for row in rows]
            
        except Exception as e:
            handle_domain_event_error(
                "get_by_aggregate", 
                None, 
                e, 
                {"schema": self._schema, "aggregate_type": aggregate_type, "aggregate_id": str(aggregate_id)}
            )
            raise
    
    async def get_unprocessed(self, limit: int = 100) -> List[DomainEvent]:
        """Get unprocessed events for webhook delivery."""
        try:
            query = DOMAIN_EVENT_GET_UNPROCESSED.format(schema=self._schema)
            rows = await self._db.fetch(query, limit)
            return [self._row_to_event(row) for row in rows]
            
        except Exception as e:
            handle_domain_event_error(
                "get_unprocessed", 
                None, 
                e, 
                {"schema": self._schema, "limit": limit}
            )
            raise

    async def get_unprocessed_for_update(self, 
                                      limit: int = 100, 
                                      skip_locked: bool = False,
                                      select_columns: Optional[List[str]] = None) -> List[DomainEvent]:
        """Get unprocessed events for update with locking options."""
        try:
            # Build column selection
            columns = "*"
            if select_columns:
                # Ensure essential columns are included
                essential_columns = {"id", "aggregate_id", "event_type", "event_data", "occurred_at", "processed_at", "version"}
                all_columns = set(select_columns) | essential_columns
                columns = ", ".join(sorted(all_columns))
            
            # Build query with FOR UPDATE and optional SKIP LOCKED
            lock_clause = "FOR UPDATE"
            if skip_locked:
                lock_clause += " SKIP LOCKED"
                
            query = f"""
                SELECT {columns} FROM {{schema}}.webhook_events 
                WHERE processed_at IS NULL 
                ORDER BY occurred_at ASC 
                LIMIT $1 
                {lock_clause}
            """.format(schema=self._schema)
            
            rows = await self._db.fetch(query, limit)
            return [self._row_to_event(row) for row in rows]
            
        except Exception as e:
            handle_domain_event_error(
                "get_unprocessed_for_update", 
                None, 
                e, 
                {"schema": self._schema, "limit": limit, "skip_locked": skip_locked}
            )
            raise

    async def get_unprocessed_paginated(self, 
                                      offset: int = 0,
                                      limit: int = 100) -> Tuple[List[DomainEvent], int]:
        """Get unprocessed events with pagination."""
        try:
            # Get total count
            count_query = f"SELECT COUNT(*) FROM {{schema}}.webhook_events WHERE processed_at IS NULL".format(schema=self._schema)
            total_count = await self._db.fetchval(count_query)
            
            # Get paginated results
            query = DOMAIN_EVENT_GET_UNPROCESSED.format(schema=self._schema) + " OFFSET $2"
            rows = await self._db.fetch(query, limit, offset)
            events = [self._row_to_event(row) for row in rows]
            
            return events, total_count
            
        except Exception as e:
            handle_domain_event_error(
                "get_unprocessed_paginated", 
                None, 
                e, 
                {"schema": self._schema, "limit": limit, "offset": offset}
            )
            raise

    async def mark_multiple_as_processed_bulk(self, event_ids: List[EventId]) -> int:
        """Mark multiple events as processed using bulk update for performance."""
        if not event_ids:
            return 0
            
        try:
            processed_at = datetime.now(timezone.utc)
            id_values = [event_id.value for event_id in event_ids]
            
            # Use unnest for efficient bulk update
            query = f"""
                UPDATE {{schema}}.webhook_events 
                SET processed_at = $1 
                WHERE id = ANY($2::uuid[]) 
                AND processed_at IS NULL
                RETURNING id
            """.format(schema=self._schema)
            
            rows = await self._db.fetch(query, processed_at, id_values)
            return len(rows)
            
        except Exception as e:
            handle_domain_event_error(
                "mark_multiple_as_processed_bulk", 
                None, 
                e, 
                {"schema": self._schema, "event_count": len(event_ids)}
            )
            raise

    async def count_unprocessed(self) -> int:
        """Count unprocessed events."""
        try:
            query = f"SELECT COUNT(*) FROM {{schema}}.webhook_events WHERE processed_at IS NULL".format(schema=self._schema)
            return await self._db.fetchval(query)
            
        except Exception as e:
            handle_domain_event_error(
                "count_unprocessed", 
                None, 
                e, 
                {"schema": self._schema}
            )
            raise

    async def count_processing(self) -> int:
        """Count events currently being processed (locked but not yet marked processed)."""
        try:
            # This is a conceptual count - in practice, events are either processed or not
            # We can implement this by checking for events that were selected for update
            # but not yet processed within a reasonable timeframe
            query = f"""
                SELECT COUNT(*) FROM {{schema}}.webhook_events 
                WHERE processed_at IS NULL 
                AND occurred_at < NOW() - INTERVAL '1 minute'
            """.format(schema=self._schema)
            return await self._db.fetchval(query)
            
        except Exception as e:
            handle_domain_event_error(
                "count_processing", 
                None, 
                e, 
                {"schema": self._schema}
            )
            raise
    
    async def mark_as_processed(self, event_id: EventId) -> bool:
        """Mark an event as processed for webhook delivery."""
        try:
            query = DOMAIN_EVENT_MARK_PROCESSED.format(schema=self._schema)
            result = await self._db.fetchrow(query, event_id.value)
            return result["success"] if result else False
            
        except Exception as e:
            handle_domain_event_error("mark_as_processed", event_id, e, {"schema": self._schema})
            raise
    
    async def mark_multiple_as_processed(self, event_ids: List[EventId]) -> int:
        """Mark multiple events as processed for webhook delivery.
        
        Args:
            event_ids: List of event IDs to mark as processed
            
        Returns:
            Number of events successfully marked as processed
        """
        if not event_ids:
            return 0
            
        try:
            # Convert EventId objects to UUID values for the database query
            uuid_values = [event_id.value for event_id in event_ids]
            
            query = DOMAIN_EVENT_MARK_MULTIPLE_PROCESSED.format(schema=self._schema)
            rows = await self._db.fetch(query, uuid_values)
            
            # Count successful updates
            processed_count = len(rows)
            
            logger.info(f"Marked {processed_count} events as processed (requested: {len(event_ids)})")
            return processed_count
            
        except Exception as e:
            handle_domain_event_error(
                "mark_multiple_as_processed", 
                None, 
                e, 
                {"schema": self._schema, "event_count": len(event_ids)}
            )
            raise
    
    async def get_by_correlation_id(self, correlation_id: UUID) -> List[DomainEvent]:
        """Get events by correlation ID for tracking related events."""
        try:
            query = DOMAIN_EVENT_GET_BY_CORRELATION_ID.format(schema=self._schema)
            rows = await self._db.fetch(query, correlation_id)
            return [self._row_to_event(row) for row in rows]
            
        except Exception as e:
            handle_domain_event_error(
                "get_by_correlation_id", 
                None, 
                e, 
                {"schema": self._schema, "correlation_id": str(correlation_id)}
            )
            raise
    
    async def get_by_context(self, context_id: UUID, limit: int = 100) -> List[DomainEvent]:
        """Get events by context ID (organization, team, etc.)."""
        try:
            query = DOMAIN_EVENT_GET_BY_CONTEXT.format(schema=self._schema)
            rows = await self._db.fetch(query, context_id, limit)
            return [self._row_to_event(row) for row in rows]
            
        except Exception as e:
            handle_domain_event_error(
                "get_by_context", 
                None, 
                e, 
                {"schema": self._schema, "context_id": str(context_id), "limit": limit}
            )
            raise
    
    async def get_by_event_type(self, event_type: str, limit: int = 100) -> List[DomainEvent]:
        """Get events by event type."""
        try:
            query = DOMAIN_EVENT_GET_BY_EVENT_TYPE.format(schema=self._schema)
            rows = await self._db.fetch(query, event_type, limit)
            return [self._row_to_event(row) for row in rows]
            
        except Exception as e:
            handle_domain_event_error(
                "get_by_event_type", 
                None, 
                e, 
                {"schema": self._schema, "event_type": event_type, "limit": limit}
            )
            raise
    
    async def get_recent_events(self, hours: int = 24, limit: int = 100) -> List[DomainEvent]:
        """Get recent events within specified hours."""
        try:
            query = DOMAIN_EVENT_GET_RECENT.format(schema=self._schema, hours=hours)
            rows = await self._db.fetch(query, limit)
            return [self._row_to_event(row) for row in rows]
            
        except Exception as e:
            handle_domain_event_error(
                "get_recent_events", 
                None, 
                e, 
                {"schema": self._schema, "hours": hours, "limit": limit}
            )
            raise
    
    async def count_by_type(self, hours: int = 24) -> Dict[str, int]:
        """Get event counts by type within specified hours."""
        try:
            query = DOMAIN_EVENT_COUNT_BY_TYPE.format(schema=self._schema, hours=hours)
            rows = await self._db.fetch(query)
            return {row["event_type"]: row["count"] for row in rows}
            
        except Exception as e:
            handle_domain_event_error(
                "count_by_type", 
                None, 
                e, 
                {"schema": self._schema, "hours": hours}
            )
            raise
    
    def _row_to_event(self, row) -> DomainEvent:
        """Convert database row to DomainEvent entity."""
        from ....core.value_objects import EventType
        
        # Parse JSON fields
        event_data = json.loads(row["event_data"]) if row["event_data"] else {}
        event_metadata = json.loads(row["event_metadata"]) if row["event_metadata"] else {}
        
        # Convert triggered_by_user_id if present
        triggered_by_user_id = None
        if row["triggered_by_user_id"]:
            triggered_by_user_id = UserId(row["triggered_by_user_id"])
        
        return DomainEvent(
            id=EventId(row["id"]),
            event_type=EventType(row["event_type"]),
            aggregate_id=row["aggregate_id"],
            aggregate_type=row["aggregate_type"],
            aggregate_version=row["aggregate_version"],
            event_data=event_data,
            event_metadata=event_metadata,
            event_name=row["event_name"],
            correlation_id=row["correlation_id"],
            causation_id=row["causation_id"],
            triggered_by_user_id=triggered_by_user_id,
            context_id=row["context_id"],
            occurred_at=row["occurred_at"],
            processed_at=row.get("processed_at"),
            created_at=row["created_at"],
        )