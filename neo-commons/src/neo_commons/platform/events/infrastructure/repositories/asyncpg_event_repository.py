"""AsyncPG-based PostgreSQL repository for event operations.

This implementation follows existing patterns from organizations repository
and uses the database service from neo-commons for connection management.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from ....core.value_objects import EventId
from ....core.exceptions import EntityNotFoundError, DatabaseError
from ....features.database.entities.protocols import DatabaseRepository
from ....domain.entities.event import Event, EventStatus, EventPriority
from ....application.protocols.event_repository import EventRepositoryProtocol
from ..queries.event_queries import (
    EVENT_INSERT,
    EVENT_UPDATE,
    EVENT_GET_BY_ID,
    EVENT_LIST_FILTERED,
    EVENT_COUNT_FILTERED,
    EVENT_GET_HISTORY,
    EVENT_GET_PENDING,
    EVENT_GET_FAILED,
    EVENT_DELETE_SOFT,
    EVENT_EXISTS_BY_ID,
    build_event_filters
)
import json

logger = logging.getLogger(__name__)


class AsyncPGEventRepository(EventRepositoryProtocol):
    """AsyncPG-based PostgreSQL repository for event operations.
    
    Follows existing patterns from organizations repository and uses the 
    database service for connection management. Implements the EventRepositoryProtocol
    for schema-intensive multi-tenant operations.
    """
    
    def __init__(self, database_repository: DatabaseRepository):
        """Initialize with existing database repository.
        
        Args:
            database_repository: Database repository from neo-commons
        """
        self._db = database_repository
    
    async def save(self, event: Event, schema: str) -> Event:
        """Save event to database in the specified schema."""
        try:
            query = EVENT_INSERT.format(schema=schema)
            
            # Prepare parameters matching the table structure
            params = [
                str(event.id.value),                           # id
                event.event_type.value,                        # event_type
                str(event.aggregate_reference.aggregate_id),   # aggregate_id
                event.aggregate_reference.aggregate_type,      # aggregate_type
                event.event_version,                           # event_version
                str(event.correlation_id) if event.correlation_id else None,  # correlation_id
                str(event.causation_id) if event.causation_id else None,      # causation_id
                json.dumps(event.event_data),                  # event_data
                json.dumps(event.event_metadata),              # event_metadata
                event.status.value,                            # status
                event.priority.value,                          # priority
                event.scheduled_at,                            # scheduled_at
                event.retry_count,                             # retry_count
                event.max_retries,                             # max_retries
                event.queue_name,                              # queue_name
                event.message_id,                              # message_id
                event.partition_key,                           # partition_key
                event.created_at,                              # created_at
                event.updated_at                               # updated_at
            ]
            
            result = await self._db.execute_query(query, params)
            if result:
                logger.info(f"Created event {event.id} of type '{event.event_type}' in schema '{schema}'")
                return event
            
            raise DatabaseError("Failed to create event")
            
        except Exception as e:
            logger.error(f"Failed to save event {event.id} in schema '{schema}': {e}")
            raise DatabaseError(f"Failed to save event: {e}")
    
    async def get_by_id(self, event_id: EventId, schema: str) -> Optional[Event]:
        """Get event by ID from the specified schema."""
        try:
            query = EVENT_GET_BY_ID.format(schema=schema)
            result = await self._db.fetch_one(query, [str(event_id.value)])
            
            if result:
                return self._map_row_to_event(result)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get event {event_id} from schema '{schema}': {e}")
            raise DatabaseError(f"Failed to get event: {e}")
    
    async def update(self, event: Event, schema: str) -> Event:
        """Update event in the specified schema."""
        try:
            # Update the timestamp
            event.updated_at = datetime.now(event.updated_at.tzinfo)
            
            query = EVENT_UPDATE.format(schema=schema)
            
            params = [
                str(event.id.value),                # id (WHERE clause)
                event.status.value,                 # status
                event.processing_started_at,        # processing_started_at
                event.processing_completed_at,      # processing_completed_at
                event.processing_duration_ms,       # processing_duration_ms
                event.retry_count,                  # retry_count
                event.error_message,                # error_message
                json.dumps(event.error_details) if event.error_details else None,  # error_details
                event.queue_name,                   # queue_name
                event.message_id,                   # message_id
                event.partition_key                 # partition_key
            ]
            
            result = await self._db.execute_query(query, params)
            if result:
                logger.info(f"Updated event {event.id} in schema '{schema}'")
                return event
            
            raise EntityNotFoundError(f"Event {event.id} not found in schema '{schema}'")
            
        except Exception as e:
            logger.error(f"Failed to update event {event.id} in schema '{schema}': {e}")
            raise DatabaseError(f"Failed to update event: {e}")
    
    async def delete(self, event_id: EventId, schema: str) -> bool:
        """Soft delete event in the specified schema."""
        try:
            query = EVENT_DELETE_SOFT.format(schema=schema)
            result = await self._db.execute_query(query, [str(event_id.value)])
            
            if result:
                logger.info(f"Soft deleted event {event_id} in schema '{schema}'")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete event {event_id} in schema '{schema}': {e}")
            raise DatabaseError(f"Failed to delete event: {e}")
    
    async def exists(self, event_id: EventId, schema: str) -> bool:
        """Check if event exists in the specified schema."""
        try:
            query = EVENT_EXISTS_BY_ID.format(schema=schema)
            result = await self._db.fetch_one(query, [str(event_id.value)])
            return result and result.get("exists", False)
            
        except Exception as e:
            logger.error(f"Failed to check event existence {event_id} in schema '{schema}': {e}")
            raise DatabaseError(f"Failed to check event existence: {e}")
    
    async def list_events(
        self, 
        schema: str,
        limit: int = 50, 
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Event]:
        """List events with optional filtering in the specified schema."""
        try:
            if filters:
                filter_clause, filter_params = build_event_filters(filters)
                query = EVENT_LIST_FILTERED.format(schema=schema, filters=filter_clause)
                params = [limit, offset] + filter_params
            else:
                # Use simple list all query without filters
                query = f"""
                    SELECT * FROM {schema}.events 
                    WHERE deleted_at IS NULL
                    ORDER BY created_at DESC
                    LIMIT $1 OFFSET $2
                """
                params = [limit, offset]
            
            results = await self._db.fetch_all(query, params)
            return [self._map_row_to_event(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to list events in schema '{schema}': {e}")
            raise DatabaseError(f"Failed to list events: {e}")
    
    async def count_events(
        self, 
        schema: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Count events with optional filtering in the specified schema."""
        try:
            if filters:
                filter_clause, filter_params = build_event_filters(filters)
                query = EVENT_COUNT_FILTERED.format(schema=schema, filters=filter_clause)
                params = filter_params
            else:
                # Use simple count query without filters
                query = f"SELECT COUNT(*) FROM {schema}.events WHERE deleted_at IS NULL"
                params = []
            
            result = await self._db.fetch_one(query, params)
            return result.get("count", 0) if result else 0
            
        except Exception as e:
            logger.error(f"Failed to count events in schema '{schema}': {e}")
            raise DatabaseError(f"Failed to count events: {e}")
    
    async def get_event_history(
        self, 
        correlation_id: UUID, 
        schema: str,
        limit: int = 100
    ) -> List[Event]:
        """Get event history by correlation_id in the specified schema."""
        try:
            query = EVENT_GET_HISTORY.format(schema=schema)
            results = await self._db.fetch_all(query, [str(correlation_id), limit])
            return [self._map_row_to_event(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get event history for correlation_id {correlation_id} in schema '{schema}': {e}")
            raise DatabaseError(f"Failed to get event history: {e}")
    
    async def get_pending_events(
        self, 
        schema: str,
        limit: int = 100
    ) -> List[Event]:
        """Get pending events ordered by priority and creation time in the specified schema."""
        try:
            query = EVENT_GET_PENDING.format(schema=schema)
            results = await self._db.fetch_all(query, [limit])
            return [self._map_row_to_event(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get pending events in schema '{schema}': {e}")
            raise DatabaseError(f"Failed to get pending events: {e}")
    
    async def get_failed_events(
        self, 
        schema: str,
        can_retry: bool = True,
        limit: int = 100
    ) -> List[Event]:
        """Get failed events that can be retried in the specified schema."""
        try:
            # Build retry filter condition
            can_retry_filter = "AND retry_count < max_retries" if can_retry else ""
            query = EVENT_GET_FAILED.format(schema=schema, can_retry_filter=can_retry_filter)
            results = await self._db.fetch_all(query, [limit])
            return [self._map_row_to_event(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get failed events in schema '{schema}': {e}")
            raise DatabaseError(f"Failed to get failed events: {e}")
    
    def _map_row_to_event(self, row: Dict[str, Any]) -> Event:
        """Map database row to Event entity."""
        return Event(
            id=EventId(row["id"]),
            event_type=row["event_type"],
            aggregate_id=UUID(row["aggregate_id"]),
            aggregate_type=row["aggregate_type"],
            event_version=row.get("event_version", 1),
            correlation_id=UUID(row["correlation_id"]) if row.get("correlation_id") else None,
            causation_id=UUID(row["causation_id"]) if row.get("causation_id") else None,
            event_data=self._parse_json_field(row.get("event_data")) or {},
            event_metadata=self._parse_json_field(row.get("event_metadata")) or {},
            status=EventStatus(row.get("status", "pending")),
            priority=EventPriority(row.get("priority", "normal")),
            scheduled_at=row.get("scheduled_at"),
            processing_started_at=row.get("processing_started_at"),
            processing_completed_at=row.get("processing_completed_at"),
            processing_duration_ms=row.get("processing_duration_ms"),
            retry_count=row.get("retry_count", 0),
            max_retries=row.get("max_retries", 3),
            error_message=row.get("error_message"),
            error_details=self._parse_json_field(row.get("error_details")) or {},
            tenant_id=UUID(row["tenant_id"]) if row.get("tenant_id") else None,
            organization_id=UUID(row["organization_id"]) if row.get("organization_id") else None,
            user_id=UUID(row["user_id"]) if row.get("user_id") else None,
            source_service=row.get("source_service"),
            source_version=row.get("source_version"),
            queue_name=row.get("queue_name"),
            message_id=row.get("message_id"),
            partition_key=row.get("partition_key"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            deleted_at=row.get("deleted_at")
        )
    
    def _parse_json_field(self, field_value: Any) -> Any:
        """Parse JSON field value - handles both dict and string representations."""
        if field_value is None:
            return {}
        if isinstance(field_value, dict):
            return field_value
        if isinstance(field_value, str):
            try:
                return json.loads(field_value)
            except (json.JSONDecodeError, ValueError):
                return {}
        return field_value or {}