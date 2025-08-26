"""
Event Action Repository Implementation

Provides database operations for event actions using asyncpg.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from uuid import UUID

from ....core.value_objects.identifiers import ActionId
from ....infrastructure.database.connection_manager import ConnectionManager
from ..entities.protocols import EventActionRepository
from ..entities.event_action import EventAction, HandlerType, ExecutionMode, ActionPriority, ActionStatus
from ..entities.action_conditions import ActionCondition

logger = logging.getLogger(__name__)


class EventActionPostgresRepository:
    """PostgreSQL implementation of EventActionRepository."""
    
    def __init__(
        self, 
        connection_manager: ConnectionManager,
        schema: str = "admin"
    ):
        self._connection_manager = connection_manager
        self._schema = schema
        self._table = f"{schema}.event_actions"
    
    async def save(self, action: EventAction) -> EventAction:
        """Save an event action."""
        query = f"""
            INSERT INTO {self._table} (
                id, name, description, handler_type, configuration,
                event_types, conditions, context_filters, execution_mode,
                priority, timeout_seconds, max_retries, retry_delay_seconds,
                status, is_enabled, tags, tenant_id, created_by_user_id
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18
            ) RETURNING 
                id, name, description, handler_type, configuration,
                event_types, conditions, context_filters, execution_mode,
                priority, timeout_seconds, max_retries, retry_delay_seconds,
                status, is_enabled, tags, tenant_id, created_by_user_id,
                created_at, updated_at, last_triggered_at,
                trigger_count, success_count, failure_count
        """
        
        # Convert conditions to JSONB format
        conditions_json = [condition.to_dict() for condition in action.conditions]
        
        async with self._connection_manager.get_connection(self._schema.split('.')[0]) as conn:
            row = await conn.fetchrow(
                query,
                str(action.id.value),
                action.name,
                action.description,
                action.handler_type.value,
                json.dumps(action.configuration),
                json.dumps(action.event_types),
                json.dumps(conditions_json),
                json.dumps(action.context_filters),
                action.execution_mode.value,
                action.priority.value,
                action.timeout_seconds,
                action.max_retries,
                action.retry_delay_seconds,
                action.status.value,
                action.is_enabled,
                json.dumps(action.tags),
                action.tenant_id,
                str(action.created_by_user_id.value) if action.created_by_user_id else None
            )
            
            return self._row_to_event_action(row)
    
    async def get_by_id(self, action_id: ActionId) -> Optional[EventAction]:
        """Get action by ID."""
        query = f"""
            SELECT 
                id, name, description, handler_type, configuration,
                event_types, conditions, context_filters, execution_mode,
                priority, timeout_seconds, max_retries, retry_delay_seconds,
                status, is_enabled, tags, tenant_id, created_by_user_id,
                created_at, updated_at, last_triggered_at,
                trigger_count, success_count, failure_count
            FROM {self._table}
            WHERE id = $1
        """
        
        async with self._connection_manager.get_connection(self._schema.split('.')[0]) as conn:
            row = await conn.fetchrow(query, str(action_id.value))
            
            if row:
                return self._row_to_event_action(row)
            return None
    
    async def get_actions_for_event(
        self, 
        event_type: str, 
        context_filters: Optional[Dict[str, Any]] = None
    ) -> List[EventAction]:
        """Get actions that should be triggered for the given event."""
        # Base query for active actions
        query = f"""
            SELECT 
                id, name, description, handler_type, configuration,
                event_types, conditions, context_filters, execution_mode,
                priority, timeout_seconds, max_retries, retry_delay_seconds,
                status, is_enabled, tags, tenant_id, created_by_user_id,
                created_at, updated_at, last_triggered_at,
                trigger_count, success_count, failure_count
            FROM {self._table}
            WHERE status = 'active' 
                AND is_enabled = true
                AND (
                    event_types @> $1::jsonb  -- Direct event type match
                    OR EXISTS (
                        SELECT 1 FROM jsonb_array_elements_text(event_types) AS et
                        WHERE $2 ~ et  -- Regex pattern match
                    )
                )
        """
        
        params = [
            json.dumps([event_type]),  # For direct match
            event_type  # For regex match
        ]
        
        # Add context filter if provided
        if context_filters:
            query += " AND (context_filters = '{}'::jsonb OR context_filters @> $3::jsonb)"
            params.append(json.dumps(context_filters))
        
        # Order by priority and creation time
        query += " ORDER BY priority DESC, created_at ASC"
        
        async with self._connection_manager.get_connection(self._schema.split('.')[0]) as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_event_action(row) for row in rows]
    
    async def get_active_actions(self) -> List[EventAction]:
        """Get all active actions."""
        query = f"""
            SELECT 
                id, name, description, handler_type, configuration,
                event_types, conditions, context_filters, execution_mode,
                priority, timeout_seconds, max_retries, retry_delay_seconds,
                status, is_enabled, tags, tenant_id, created_by_user_id,
                created_at, updated_at, last_triggered_at,
                trigger_count, success_count, failure_count
            FROM {self._table}
            WHERE status = 'active' AND is_enabled = true
            ORDER BY priority DESC, created_at ASC
        """
        
        async with self._connection_manager.get_connection(self._schema.split('.')[0]) as conn:
            rows = await conn.fetch(query)
            return [self._row_to_event_action(row) for row in rows]
    
    async def get_actions_by_handler_type(self, handler_type: str) -> List[EventAction]:
        """Get actions by handler type."""
        query = f"""
            SELECT 
                id, name, description, handler_type, configuration,
                event_types, conditions, context_filters, execution_mode,
                priority, timeout_seconds, max_retries, retry_delay_seconds,
                status, is_enabled, tags, tenant_id, created_by_user_id,
                created_at, updated_at, last_triggered_at,
                trigger_count, success_count, failure_count
            FROM {self._table}
            WHERE handler_type = $1
            ORDER BY status DESC, created_at ASC
        """
        
        async with self._connection_manager.get_connection(self._schema.split('.')[0]) as conn:
            rows = await conn.fetch(query, handler_type)
            return [self._row_to_event_action(row) for row in rows]
    
    async def update(self, action: EventAction) -> EventAction:
        """Update an existing action."""
        query = f"""
            UPDATE {self._table}
            SET 
                name = $2,
                description = $3,
                handler_type = $4,
                configuration = $5,
                event_types = $6,
                conditions = $7,
                context_filters = $8,
                execution_mode = $9,
                priority = $10,
                timeout_seconds = $11,
                max_retries = $12,
                retry_delay_seconds = $13,
                status = $14,
                is_enabled = $15,
                tags = $16,
                tenant_id = $17
            WHERE id = $1
            RETURNING 
                id, name, description, handler_type, configuration,
                event_types, conditions, context_filters, execution_mode,
                priority, timeout_seconds, max_retries, retry_delay_seconds,
                status, is_enabled, tags, tenant_id, created_by_user_id,
                created_at, updated_at, last_triggered_at,
                trigger_count, success_count, failure_count
        """
        
        # Convert conditions to JSONB format
        conditions_json = [condition.to_dict() for condition in action.conditions]
        
        async with self._connection_manager.get_connection(self._schema.split('.')[0]) as conn:
            row = await conn.fetchrow(
                query,
                str(action.id.value),
                action.name,
                action.description,
                action.handler_type.value,
                json.dumps(action.configuration),
                json.dumps(action.event_types),
                json.dumps(conditions_json),
                json.dumps(action.context_filters),
                action.execution_mode.value,
                action.priority.value,
                action.timeout_seconds,
                action.max_retries,
                action.retry_delay_seconds,
                action.status.value,
                action.is_enabled,
                json.dumps(action.tags),
                action.tenant_id
            )
            
            if row:
                return self._row_to_event_action(row)
            
            # If no row returned, action doesn't exist
            raise ValueError(f"Action with ID {action.id.value} not found")
    
    async def delete(self, action_id: ActionId) -> bool:
        """Delete an action."""
        query = f"DELETE FROM {self._table} WHERE id = $1"
        
        async with self._connection_manager.get_connection(self._schema.split('.')[0]) as conn:
            result = await conn.execute(query, str(action_id.value))
            return result.split()[-1] == "1"  # Check if one row was deleted
    
    async def get_by_tenant(self, tenant_id: str) -> List[EventAction]:
        """Get actions for a specific tenant."""
        query = f"""
            SELECT 
                id, name, description, handler_type, configuration,
                event_types, conditions, context_filters, execution_mode,
                priority, timeout_seconds, max_retries, retry_delay_seconds,
                status, is_enabled, tags, tenant_id, created_by_user_id,
                created_at, updated_at, last_triggered_at,
                trigger_count, success_count, failure_count
            FROM {self._table}
            WHERE tenant_id = $1
            ORDER BY status DESC, created_at ASC
        """
        
        async with self._connection_manager.get_connection(self._schema.split('.')[0]) as conn:
            rows = await conn.fetch(query, tenant_id)
            return [self._row_to_event_action(row) for row in rows]
    
    async def update_statistics(
        self, 
        action_id: ActionId, 
        trigger_increment: int = 0,
        success_increment: int = 0,
        failure_increment: int = 0
    ) -> bool:
        """Update action statistics."""
        query = f"""
            UPDATE {self._table}
            SET 
                trigger_count = trigger_count + $2,
                success_count = success_count + $3,
                failure_count = failure_count + $4,
                last_triggered_at = CASE WHEN $2 > 0 THEN NOW() ELSE last_triggered_at END
            WHERE id = $1
        """
        
        async with self._connection_manager.get_connection(self._schema.split('.')[0]) as conn:
            result = await conn.execute(
                query,
                str(action_id.value),
                trigger_increment,
                success_increment,
                failure_increment
            )
            return result.split()[-1] == "1"
    
    def _row_to_event_action(self, row) -> EventAction:
        """Convert database row to EventAction entity."""
        from ....core.value_objects.identifiers import UserId
        
        # Parse conditions from JSONB
        conditions_data = row['conditions'] if row['conditions'] else []
        conditions = [
            ActionCondition.from_dict(cond) 
            for cond in conditions_data 
            if isinstance(cond, dict)
        ]
        
        return EventAction(
            id=ActionId(UUID(row['id'])),
            name=row['name'],
            description=row['description'],
            handler_type=HandlerType(row['handler_type']),
            configuration=row['configuration'] if row['configuration'] else {},
            event_types=row['event_types'] if row['event_types'] else [],
            conditions=conditions,
            context_filters=row['context_filters'] if row['context_filters'] else {},
            execution_mode=ExecutionMode(row['execution_mode']),
            priority=ActionPriority(row['priority']),
            timeout_seconds=row['timeout_seconds'],
            max_retries=row['max_retries'],
            retry_delay_seconds=row['retry_delay_seconds'],
            status=ActionStatus(row['status']),
            is_enabled=row['is_enabled'],
            tags=row['tags'] if row['tags'] else {},
            tenant_id=row['tenant_id'],
            created_by_user_id=UserId(UUID(row['created_by_user_id'])) if row['created_by_user_id'] else None,
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            last_triggered_at=row['last_triggered_at'],
            trigger_count=row['trigger_count'],
            success_count=row['success_count'],
            failure_count=row['failure_count']
        )