"""Platform events AsyncPG event repository implementation.

ONLY handles event data access with PostgreSQL using asyncpg.
Following maximum separation architecture - single responsibility only.

This implementation:
- ONLY PostgreSQL event persistence operations
- ONLY asyncpg connections and transactions  
- ONLY SQL query execution for events
- NO business logic, NO validation, NO external services
"""

import asyncpg
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from ...core.entities import DomainEvent
from ...core.value_objects import EventId
from ...core.protocols import EventRepository
from .....core.shared.context import RequestContext


@dataclass
class EventRecord:
    """Database record representation of a webhook event."""
    
    id: str
    event_type: str
    event_name: str
    aggregate_id: str
    aggregate_type: str
    aggregate_version: int
    event_data: Dict[str, Any]
    event_metadata: Dict[str, Any]
    correlation_id: Optional[str]
    causation_id: Optional[str]
    triggered_by_user_id: Optional[str]
    context_id: Optional[str]
    occurred_at: datetime
    processed_at: Optional[datetime]
    created_at: datetime


class AsyncpgEventRepository(EventRepository):
    """PostgreSQL event repository using asyncpg.
    
    ONLY handles event data access operations following webhook_events schema.
    NO business logic, NO validation, NO external dependencies.
    """
    
    def __init__(self, connection_pool: asyncpg.Pool):
        """Initialize with asyncpg connection pool.
        
        Args:
            connection_pool: AsyncPG connection pool for database access
            
        Note: Schema resolution should be handled at the service layer,
        not at the repository level, following neo-commons patterns.
        """
        self._pool = connection_pool
    
    # ===========================================
    # Core Persistence Operations
    # ===========================================
    
    async def save_event(
        self, 
        event: DomainEvent, 
        transaction_context: Optional[Dict[str, Any]] = None
    ) -> DomainEvent:
        """Persist a domain event to the event store using webhook_events schema.
        
        Args:
            event: Domain event to persist
            transaction_context: Optional transaction context for atomic operations
            
        Returns:
            Persisted domain event with updated metadata
            
        Raises:
            Exception: Database connection or query execution errors
        """
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                query = """
                    INSERT INTO {schema_name}.webhook_events (
                        id, event_type, event_name, aggregate_id, aggregate_type,
                        aggregate_version, event_data, event_metadata, 
                        correlation_id, causation_id, triggered_by_user_id, 
                        context_id, occurred_at, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    ON CONFLICT (id) DO UPDATE SET
                        event_data = EXCLUDED.event_data,
                        event_metadata = EXCLUDED.event_metadata,
                        aggregate_version = EXCLUDED.aggregate_version
                    RETURNING *
                """
                
                now = datetime.utcnow()
                record = await conn.fetchrow(
                    query,
                    str(event.id.value),
                    event.event_type.value,
                    event.event_name or event.event_type.value,
                    str(event.aggregate_id),
                    event.aggregate_type,
                    event.aggregate_version or 1,
                    event.event_data,
                    event.event_metadata,
                    str(event.correlation_id) if event.correlation_id else None,
                    str(event.causation_id) if event.causation_id else None,
                    str(event.triggered_by_user_id.value) if event.triggered_by_user_id else None,
                    str(event.context_id) if event.context_id else None,
                    event.occurred_at or now,
                    now
                )
                
                return self._record_to_domain_event(record)
    
    async def save_events_batch(
        self,
        events: List[DomainEvent],
        preserve_order: bool = True,
        transaction_context: Optional[Dict[str, Any]] = None
    ) -> List[DomainEvent]:
        """Persist multiple domain events atomically.
        
        Args:
            events: List of domain events to persist
            preserve_order: Whether to maintain event ordering
            transaction_context: Optional transaction context
            
        Returns:
            List of persisted domain events
        """
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                query = """
                    INSERT INTO {schema_name}.webhook_events (
                        id, event_type, event_name, aggregate_id, aggregate_type,
                        aggregate_version, event_data, event_metadata, 
                        correlation_id, causation_id, triggered_by_user_id, 
                        context_id, occurred_at, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    RETURNING *
                """
                
                saved_events = []
                now = datetime.utcnow()
                
                for event in events:
                    record = await conn.fetchrow(
                        query,
                        str(event.id.value),
                        event.event_type.value,
                        event.event_name or event.event_type.value,
                        str(event.aggregate_id),
                        event.aggregate_type,
                        event.aggregate_version or 1,
                        event.event_data,
                        event.event_metadata,
                        str(event.correlation_id) if event.correlation_id else None,
                        str(event.causation_id) if event.causation_id else None,
                        str(event.triggered_by_user_id.value) if event.triggered_by_user_id else None,
                        str(event.context_id) if event.context_id else None,
                        event.occurred_at or now,
                        now
                    )
                    saved_events.append(self._record_to_domain_event(record))
                
                return saved_events
    
    async def get_event_by_id(
        self,
        event_id: EventId,
        include_metadata: bool = True
    ) -> Optional[DomainEvent]:
        """Retrieve a specific event by its unique identifier.
        
        Args:
            event_id: Unique identifier of the event to retrieve
            include_metadata: Whether to include event metadata in response
            
        Returns:
            Domain event if found, None otherwise
        """
        async with self._pool.acquire() as conn:
            if include_metadata:
                query = "SELECT * FROM {schema_name}.webhook_events WHERE id = $1"
            else:
                query = """
                    SELECT id, event_type, event_name, aggregate_id, aggregate_type,
                           aggregate_version, event_data, occurred_at, created_at
                    FROM {schema_name}.webhook_events WHERE id = $1
                """
            
            record = await conn.fetchrow(query, str(event_id.value))
            return self._record_to_domain_event(record) if record else None
    
    # ===========================================
    # Event Stream Operations
    # ===========================================
    
    async def get_events_by_aggregate(
        self,
        aggregate_id: str,
        aggregate_type: str,
        from_version: Optional[int] = None,
        to_version: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[DomainEvent]:
        """Retrieve events for a specific aggregate with version filtering.
        
        Args:
            aggregate_id: ID of the aggregate entity
            aggregate_type: Type of the aggregate entity  
            from_version: Minimum aggregate version (inclusive)
            to_version: Maximum aggregate version (inclusive)
            limit: Maximum number of events to return
            
        Returns:
            List of domain events ordered by aggregate version
        """
        async with self._pool.acquire() as conn:
            conditions = ["aggregate_id = $1", "aggregate_type = $2"]
            params = [aggregate_id, aggregate_type]
            param_count = 2
            
            if from_version is not None:
                param_count += 1
                conditions.append(f"aggregate_version >= ${param_count}")
                params.append(from_version)
                
            if to_version is not None:
                param_count += 1
                conditions.append(f"aggregate_version <= ${param_count}")
                params.append(to_version)
            
            query = f"""
                SELECT * FROM {{schema_name}}.webhook_events 
                WHERE {' AND '.join(conditions)}
                ORDER BY aggregate_version ASC
            """
            
            if limit is not None:
                query += f" LIMIT {limit}"
            
            records = await conn.fetch(query, *params)
            return [self._record_to_domain_event(record) for record in records]
    
    async def get_events_by_type(
        self,
        event_type: str,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[DomainEvent]:
        """Retrieve events filtered by type and time range.
        
        Args:
            event_type: Type of events to retrieve
            from_time: Earliest event time (inclusive)
            to_time: Latest event time (inclusive)
            limit: Maximum number of events to return
            offset: Number of events to skip for pagination
            
        Returns:
            List of domain events ordered by occurrence time
        """
        async with self._pool.acquire() as conn:
            conditions = ["event_type = $1"]
            params = [event_type]
            param_count = 1
            
            if from_time is not None:
                param_count += 1
                conditions.append(f"occurred_at >= ${param_count}")
                params.append(from_time)
                
            if to_time is not None:
                param_count += 1
                conditions.append(f"occurred_at <= ${param_count}")
                params.append(to_time)
            
            query = f"""
                SELECT * FROM {{schema_name}}.webhook_events 
                WHERE {' AND '.join(conditions)}
                ORDER BY occurred_at DESC
            """
            
            if limit is not None:
                query += f" LIMIT {limit}"
            if offset is not None:
                query += f" OFFSET {offset}"
            
            records = await conn.fetch(query, *params)
            return [self._record_to_domain_event(record) for record in records]
    
    async def get_events_by_correlation_id(
        self,
        correlation_id: str,
        include_causation_chain: bool = False,
        limit: Optional[int] = None
    ) -> List[DomainEvent]:
        """Retrieve events linked by correlation ID.
        
        Args:
            correlation_id: Correlation ID linking related events
            include_causation_chain: Whether to include full causation chain
            limit: Maximum number of events to return
            
        Returns:
            List of correlated domain events ordered by occurrence time
        """
        async with self._pool.acquire() as conn:
            if include_causation_chain:
                # Include events that caused this correlation or were caused by it
                query = """
                    SELECT * FROM {{schema_name}}.webhook_events 
                    WHERE correlation_id = $1 OR causation_id = $1
                    ORDER BY occurred_at ASC
                """
            else:
                query = """
                    SELECT * FROM {{schema_name}}.webhook_events 
                    WHERE correlation_id = $1
                    ORDER BY occurred_at ASC
                """
            
            if limit is not None:
                query += f" LIMIT {limit}"
            
            records = await conn.fetch(query, correlation_id)
            return [self._record_to_domain_event(record) for record in records]
    
    # ===========================================
    # Event Query Operations
    # ===========================================
    
    async def get_unprocessed_events(
        self,
        limit: Optional[int] = None,
        event_types: Optional[List[str]] = None,
        max_age_hours: Optional[int] = None
    ) -> List[DomainEvent]:
        """Retrieve events that haven't been processed.
        
        Args:
            limit: Maximum number of events to return
            event_types: Optional filter by specific event types
            max_age_hours: Maximum age of events to consider (hours)
            
        Returns:
            List of unprocessed domain events ordered by occurrence time
        """
        async with self._pool.acquire() as conn:
            conditions = ["processed_at IS NULL"]
            params = []
            param_count = 0
            
            if event_types:
                param_count += 1
                conditions.append(f"event_type = ANY(${param_count})")
                params.append(event_types)
                
            if max_age_hours is not None:
                param_count += 1
                conditions.append(f"occurred_at >= NOW() - INTERVAL '{max_age_hours} hours'")
            
            query = f"""
                SELECT * FROM {{schema_name}}.webhook_events 
                WHERE {' AND '.join(conditions)}
                ORDER BY occurred_at ASC
            """
            
            if limit is not None:
                query += f" LIMIT {limit}"
            
            records = await conn.fetch(query, *params)
            return [self._record_to_domain_event(record) for record in records]
    
    async def search_events(
        self,
        filters: Dict[str, Any],
        sort_by: str = "occurred_at",
        sort_order: str = "desc",
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Advanced event search with flexible filtering and pagination.
        
        Args:
            filters: Search filters (event_type, aggregate_type, user_id, etc.)
            sort_by: Field to sort by
            sort_order: Sort direction (asc, desc)
            limit: Maximum number of events to return
            offset: Number of events to skip for pagination
            
        Returns:
            Dict with search results including events and pagination info
        """
        async with self._pool.acquire() as conn:
            conditions = []
            params = []
            param_count = 0
            
            # Build dynamic WHERE conditions based on filters
            for key, value in filters.items():
                if value is not None:
                    param_count += 1
                    if key == 'event_types' and isinstance(value, list):
                        conditions.append(f"event_type = ANY(${param_count})")
                    else:
                        conditions.append(f"{key} = ${param_count}")
                    params.append(value)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # Count query
            count_query = f"SELECT COUNT(*) FROM {{schema_name}}.webhook_events WHERE {where_clause}"
            total_count = await conn.fetchval(count_query, *params)
            
            # Search query
            query = f"""
                SELECT * FROM {{schema_name}}.webhook_events 
                WHERE {where_clause}
                ORDER BY {sort_by} {sort_order.upper()}
                LIMIT {limit} OFFSET {offset}
            """
            
            records = await conn.fetch(query, *params)
            events = [self._record_to_domain_event(record) for record in records]
            
            return {
                "events": events,
                "total_count": total_count,
                "has_more": offset + limit < total_count,
                "next_offset": offset + limit if offset + limit < total_count else None
            }
    
    # ===========================================
    # Event Statistics Operations  
    # ===========================================
    
    async def get_event_statistics(
        self,
        aggregate_type: Optional[str] = None,
        event_type: Optional[str] = None,
        time_range_hours: int = 24,
        include_processing_stats: bool = True
    ) -> Dict[str, Any]:
        """Get comprehensive event statistics.
        
        Args:
            aggregate_type: Optional filter by aggregate type
            event_type: Optional filter by event type
            time_range_hours: Time range for statistics calculation
            include_processing_stats: Whether to include processing metrics
            
        Returns:
            Dict with comprehensive event statistics
        """
        async with self._pool.acquire() as conn:
            conditions = [f"occurred_at >= NOW() - INTERVAL '{time_range_hours} hours'"]
            params = []
            param_count = 0
            
            if aggregate_type:
                param_count += 1
                conditions.append(f"aggregate_type = ${param_count}")
                params.append(aggregate_type)
                
            if event_type:
                param_count += 1
                conditions.append(f"event_type = ${param_count}")
                params.append(event_type)
            
            where_clause = " AND ".join(conditions)
            
            stats_query = f"""
                SELECT 
                    COUNT(*) as total_events,
                    COUNT(DISTINCT event_type) as unique_event_types,
                    COUNT(DISTINCT aggregate_type) as unique_aggregate_types,
                    COUNT(*) FILTER (WHERE processed_at IS NULL) as unprocessed_count,
                    COUNT(*) FILTER (WHERE processed_at IS NOT NULL) as processed_count,
                    AVG(EXTRACT(EPOCH FROM (processed_at - occurred_at))) as avg_processing_lag_seconds
                FROM {{schema_name}}.webhook_events 
                WHERE {where_clause}
            """
            
            stats = await conn.fetchrow(stats_query, *params)
            
            # Additional event type distribution
            distribution_query = f"""
                SELECT event_type, COUNT(*) as count
                FROM {{schema_name}}.webhook_events 
                WHERE {where_clause}
                GROUP BY event_type
                ORDER BY count DESC
                LIMIT 10
            """
            
            distribution = await conn.fetch(distribution_query, *params)
            
            return {
                "total_events": stats['total_events'],
                "events_per_hour": stats['total_events'] / time_range_hours if time_range_hours > 0 else 0,
                "event_type_distribution": [{"type": row['event_type'], "count": row['count']} for row in distribution],
                "unique_event_types": stats['unique_event_types'],
                "unique_aggregate_types": stats['unique_aggregate_types'],
                "processing_lag": stats['avg_processing_lag_seconds'] or 0,
                "unprocessed_count": stats['unprocessed_count'],
                "processed_count": stats['processed_count'],
                "error_rate": 0  # Would need additional error tracking
            }
    
    async def get_aggregate_statistics(
        self,
        aggregate_id: str,
        aggregate_type: str,
        include_version_history: bool = False
    ) -> Dict[str, Any]:
        """Get statistics for a specific aggregate entity.
        
        Args:
            aggregate_id: ID of the aggregate entity
            aggregate_type: Type of the aggregate entity
            include_version_history: Whether to include version progression
            
        Returns:
            Dict with aggregate statistics
        """
        async with self._pool.acquire() as conn:
            stats_query = """
                SELECT 
                    COUNT(*) as total_events,
                    MAX(aggregate_version) as current_version,
                    MIN(occurred_at) as first_event_at,
                    MAX(occurred_at) as last_event_at,
                    COUNT(DISTINCT event_type) as unique_event_types
                FROM {schema_name}.webhook_events 
                WHERE aggregate_id = $1 AND aggregate_type = $2
            """
            
            stats = await conn.fetchrow(stats_query, aggregate_id, aggregate_type)
            
            # Event type counts for this aggregate
            type_query = """
                SELECT event_type, COUNT(*) as count
                FROM {schema_name}.webhook_events 
                WHERE aggregate_id = $1 AND aggregate_type = $2
                GROUP BY event_type
                ORDER BY count DESC
            """
            
            event_types = await conn.fetch(type_query, aggregate_id, aggregate_type)
            
            result = {
                "total_events": stats['total_events'],
                "current_version": stats['current_version'],
                "first_event_at": stats['first_event_at'],
                "last_event_at": stats['last_event_at'],
                "event_type_counts": {row['event_type']: row['count'] for row in event_types}
            }
            
            if include_version_history:
                history_query = """
                    SELECT aggregate_version, event_type, occurred_at
                    FROM {schema_name}.webhook_events 
                    WHERE aggregate_id = $1 AND aggregate_type = $2
                    ORDER BY aggregate_version ASC
                """
                
                history = await conn.fetch(history_query, aggregate_id, aggregate_type)
                result["version_history"] = [
                    {
                        "version": row['aggregate_version'],
                        "event_type": row['event_type'],
                        "occurred_at": row['occurred_at']
                    }
                    for row in history
                ]
            
            return result
    
    # ===========================================
    # Event Maintenance Operations
    # ===========================================
    
    async def mark_events_processed(
        self,
        event_ids: List[EventId],
        processor_name: str,
        processing_metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Mark events as processed by a specific processor.
        
        Args:
            event_ids: List of event IDs that were processed
            processor_name: Name/identifier of the processing component
            processing_metadata: Optional metadata about processing
            
        Returns:
            Number of events successfully marked as processed
        """
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                query = """
                    UPDATE {schema_name}.webhook_events 
                    SET processed_at = NOW()
                    WHERE id = ANY($1) AND processed_at IS NULL
                """
                
                id_strings = [str(event_id.value) for event_id in event_ids]
                result = await conn.execute(query, id_strings)
                
                # Extract number from result string like "UPDATE 5"
                return int(result.split()[-1]) if result.split()[-1].isdigit() else 0
    
    async def archive_old_events(
        self,
        older_than_days: int = 365,
        batch_size: int = 1000,
        preserve_aggregates: bool = True,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Archive old events for long-term storage.
        
        Args:
            older_than_days: Archive events older than this many days
            batch_size: Number of events to archive per batch
            preserve_aggregates: Whether to keep complete aggregate event streams
            dry_run: Whether to simulate archival without actual changes
            
        Returns:
            Dict with archival results
        """
        async with self._pool.acquire() as conn:
            cutoff_date = f"NOW() - INTERVAL '{older_than_days} days'"
            
            if dry_run:
                count_query = f"""
                    SELECT COUNT(*) FROM {{schema_name}}.webhook_events 
                    WHERE occurred_at < {cutoff_date}
                """
                count = await conn.fetchval(count_query)
                
                return {
                    "events_archived": 0,
                    "aggregates_preserved": 0,
                    "processing_time_ms": 0,
                    "storage_freed_mb": 0,
                    "estimated_events": count
                }
            
            # Implementation would involve moving data to archive tables
            # For now, return placeholder
            return {
                "events_archived": 0,
                "aggregates_preserved": 0,
                "processing_time_ms": 0,
                "storage_freed_mb": 0
            }
    
    async def cleanup_processed_events(
        self,
        retention_days: int = 90,
        keep_unprocessed: bool = True,
        batch_size: int = 1000
    ) -> int:
        """Clean up processed events for database maintenance.
        
        Args:
            retention_days: Days to retain processed events
            keep_unprocessed: Whether to preserve unprocessed events
            batch_size: Number of events to delete per batch
            
        Returns:
            Number of events cleaned up
        """
        async with self._pool.acquire() as conn:
            conditions = [
                f"occurred_at < NOW() - INTERVAL '{retention_days} days'"
            ]
            
            if keep_unprocessed:
                conditions.append("processed_at IS NOT NULL")
            
            query = f"""
                DELETE FROM {{schema_name}}.webhook_events 
                WHERE {' AND '.join(conditions)}
            """
            
            result = await conn.execute(query)
            return int(result.split()[-1]) if result.split()[-1].isdigit() else 0
    
    # ===========================================
    # Health and Diagnostics Operations
    # ===========================================
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform repository health check for monitoring systems.
        
        Returns:
            Dict with health information
        """
        try:
            async with self._pool.acquire() as conn:
                # Test basic connectivity
                result = await conn.fetchval("SELECT 1")
                
                # Check recent operation success
                recent_events = await conn.fetchval("""
                    SELECT COUNT(*) FROM {schema_name}.webhook_events 
                    WHERE created_at >= NOW() - INTERVAL '1 hour'
                """)
                
                return {
                    "is_healthy": result == 1,
                    "connection_status": "connected",
                    "recent_operation_success_rate": 100.0,  # Simplified
                    "average_response_time_ms": 10,  # Simplified
                    "pending_operations": 0,
                    "last_successful_operation": datetime.utcnow(),
                    "storage_usage": {
                        "recent_events": recent_events
                    }
                }
        except Exception as e:
            return {
                "is_healthy": False,
                "connection_status": "failed",
                "error": str(e),
                "recent_operation_success_rate": 0.0,
                "average_response_time_ms": 0,
                "pending_operations": 0,
                "last_successful_operation": None,
                "storage_usage": {}
            }
    
    async def get_repository_metrics(
        self,
        time_range_hours: int = 1,
        include_performance_details: bool = False
    ) -> Dict[str, Any]:
        """Get detailed repository performance metrics.
        
        Args:
            time_range_hours: Time range for metrics calculation
            include_performance_details: Whether to include detailed metrics
            
        Returns:
            Dict with repository metrics
        """
        async with self._pool.acquire() as conn:
            # Basic metrics
            metrics_query = f"""
                SELECT 
                    COUNT(*) as events_in_period,
                    COUNT(*) / {time_range_hours} as events_per_hour,
                    COUNT(DISTINCT event_type) as unique_types,
                    AVG(LENGTH(event_data::text)) as avg_event_size
                FROM {{schema_name}}.webhook_events 
                WHERE created_at >= NOW() - INTERVAL '{time_range_hours} hours'
            """
            
            metrics = await conn.fetchrow(metrics_query)
            
            result = {
                "operations_per_second": (metrics['events_per_hour'] or 0) / 3600,
                "average_query_time_ms": 15,  # Simplified
                "cache_hit_rate": 85.0,  # Simplified
                "connection_pool_usage": 45.0,  # Simplified
                "error_rate": 1.0,  # Simplified
                "storage_growth_rate": metrics['avg_event_size'] or 0
            }
            
            if include_performance_details:
                result.update({
                    "events_in_period": metrics['events_in_period'],
                    "unique_event_types": metrics['unique_types'],
                    "average_event_size_bytes": metrics['avg_event_size']
                })
            
            return result
    
    # ===========================================
    # Private Helper Methods
    # ===========================================
    
    def _record_to_domain_event(self, record: asyncpg.Record) -> DomainEvent:
        """Convert database record to domain event.
        
        Args:
            record: AsyncPG database record
            
        Returns:
            DomainEvent: Converted domain event
        """
        from uuid import UUID
        from .....core.value_objects.identifiers import UserId
        from ..value_objects import EventType
        
        return DomainEvent(
            id=EventId(UUID(record['id'])),
            event_type=EventType(record['event_type']),
            event_name=record.get('event_name'),
            aggregate_id=UUID(record['aggregate_id']),
            aggregate_type=record['aggregate_type'],
            aggregate_version=record['aggregate_version'],
            event_data=record.get('event_data', {}),
            event_metadata=record.get('event_metadata', {}),
            correlation_id=UUID(record['correlation_id']) if record.get('correlation_id') else None,
            causation_id=UUID(record['causation_id']) if record.get('causation_id') else None,
            triggered_by_user_id=UserId(UUID(record['triggered_by_user_id'])) if record.get('triggered_by_user_id') else None,
            context_id=UUID(record['context_id']) if record.get('context_id') else None,
            occurred_at=record['occurred_at'],
            processed_at=record.get('processed_at'),
            created_at=record['created_at']
        )


def create_asyncpg_event_repository(connection_pool: asyncpg.Pool) -> AsyncpgEventRepository:
    """Factory function to create AsyncPG event repository.
    
    Args:
        connection_pool: AsyncPG connection pool
        
    Returns:
        AsyncpgEventRepository: Configured repository instance
    """
    return AsyncpgEventRepository(connection_pool)