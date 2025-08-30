"""AsyncPG implementation of ActionRepositoryProtocol."""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime

import asyncpg

from ...domain.entities.action import Action, ActionStatus
from ...domain.value_objects.action_id import ActionId
from ...domain.value_objects.action_type import ActionType
from ...application.protocols.action_repository import ActionRepositoryProtocol


class AsyncPGActionRepository(ActionRepositoryProtocol):
    """
    PostgreSQL implementation of ActionRepositoryProtocol using asyncpg.
    
    Provides schema-intensive operations for multi-tenant action management.
    """
    
    def __init__(self, connection_pool: asyncpg.Pool):
        self.connection_pool = connection_pool
    
    async def save(self, action: Action, schema: str) -> Action:
        """Save an action to the specified schema."""
        query = f"""
            INSERT INTO {schema}.actions (
                id, name, action_type, handler_class, config, event_patterns,
                conditions, is_active, priority, timeout_seconds, retry_policy,
                max_concurrent_executions, rate_limit_per_minute, is_healthy,
                last_health_check_at, health_check_error, total_executions,
                successful_executions, failed_executions, avg_execution_time_ms,
                description, tags, owner_team, metadata, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26
            )
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                config = EXCLUDED.config,
                event_patterns = EXCLUDED.event_patterns,
                conditions = EXCLUDED.conditions,
                is_active = EXCLUDED.is_active,
                priority = EXCLUDED.priority,
                timeout_seconds = EXCLUDED.timeout_seconds,
                retry_policy = EXCLUDED.retry_policy,
                max_concurrent_executions = EXCLUDED.max_concurrent_executions,
                rate_limit_per_minute = EXCLUDED.rate_limit_per_minute,
                is_healthy = EXCLUDED.is_healthy,
                last_health_check_at = EXCLUDED.last_health_check_at,
                health_check_error = EXCLUDED.health_check_error,
                total_executions = EXCLUDED.total_executions,
                successful_executions = EXCLUDED.successful_executions,
                failed_executions = EXCLUDED.failed_executions,
                avg_execution_time_ms = EXCLUDED.avg_execution_time_ms,
                description = EXCLUDED.description,
                tags = EXCLUDED.tags,
                owner_team = EXCLUDED.owner_team,
                metadata = EXCLUDED.metadata,
                updated_at = EXCLUDED.updated_at
            RETURNING *
        """
        
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                action.id.value,
                action.name,
                action.action_type.value,
                action.handler_class,
                json.dumps(action.config),
                action.event_patterns,
                json.dumps(action.conditions),
                action.is_active,
                action.priority,
                action.timeout_seconds,
                json.dumps(action.retry_policy),
                action.max_concurrent_executions,
                action.rate_limit_per_minute,
                action.is_healthy,
                action.last_health_check_at,
                action.health_check_error,
                action.total_executions,
                action.successful_executions,
                action.failed_executions,
                action.avg_execution_time_ms,
                action.description,
                action.tags,
                action.owner_team,
                json.dumps(action.metadata),
                action.created_at,
                action.updated_at
            )
            
            return self._row_to_action(row)
    
    async def get_by_id(self, action_id: ActionId, schema: str) -> Optional[Action]:
        """Get action by ID from the specified schema."""
        query = f"SELECT * FROM {schema}.actions WHERE id = $1 AND deleted_at IS NULL"
        
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(query, action_id.value)
            return self._row_to_action(row) if row else None
    
    async def get_by_name(self, name: str, schema: str) -> Optional[Action]:
        """Get action by name from the specified schema."""
        query = f"SELECT * FROM {schema}.actions WHERE name = $1 AND deleted_at IS NULL"
        
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(query, name)
            return self._row_to_action(row) if row else None
    
    async def list_actions(
        self, 
        schema: str,
        limit: int = 50, 
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Action]:
        """List actions from the specified schema with optional filtering."""
        where_conditions = ["deleted_at IS NULL"]
        params = []
        param_count = 0
        
        if filters:
            if "action_type" in filters:
                param_count += 1
                where_conditions.append(f"action_type = ${param_count}")
                params.append(filters["action_type"])
            
            if "is_active" in filters:
                param_count += 1
                where_conditions.append(f"is_active = ${param_count}")
                params.append(filters["is_active"])
            
            if "is_healthy" in filters:
                param_count += 1
                where_conditions.append(f"is_healthy = ${param_count}")
                params.append(filters["is_healthy"])
            
            if "owner_team" in filters:
                param_count += 1
                where_conditions.append(f"owner_team = ${param_count}")
                params.append(filters["owner_team"])
        
        where_clause = " AND ".join(where_conditions)
        param_count += 1
        limit_param = param_count
        param_count += 1
        offset_param = param_count
        
        query = f"""
            SELECT * FROM {schema}.actions 
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ${limit_param} OFFSET ${offset_param}
        """
        
        params.extend([limit, offset])
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_action(row) for row in rows]
    
    async def update(self, action: Action, schema: str) -> Action:
        """Update an existing action in the specified schema."""
        # Update the updated_at timestamp
        action.updated_at = datetime.now()
        return await self.save(action, schema)
    
    async def delete(self, action_id: ActionId, schema: str) -> bool:
        """Delete action by ID from the specified schema."""
        query = f"DELETE FROM {schema}.actions WHERE id = $1"
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(query, action_id.value)
            return result.split()[-1] == "1"  # Check if one row was deleted
    
    async def find_by_event_pattern(self, event_type: str, schema: str) -> List[Action]:
        """Find actions that match an event type pattern."""
        query = f"""
            SELECT * FROM {schema}.actions 
            WHERE is_active = true 
            AND is_healthy = true 
            AND deleted_at IS NULL
            AND (
                $1 = ANY(event_patterns) 
                OR EXISTS (
                    SELECT 1 FROM unnest(event_patterns) AS pattern 
                    WHERE $1 LIKE REPLACE(REPLACE(pattern, '*', '%'), '?', '_')
                )
            )
            ORDER BY priority DESC, created_at ASC
        """
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, event_type)
            return [self._row_to_action(row) for row in rows]
    
    async def find_by_type(self, action_type: ActionType, schema: str) -> List[Action]:
        """Find actions by action type."""
        query = f"""
            SELECT * FROM {schema}.actions 
            WHERE action_type = $1 AND deleted_at IS NULL
            ORDER BY created_at DESC
        """
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, action_type.value)
            return [self._row_to_action(row) for row in rows]
    
    async def find_active_actions(self, schema: str) -> List[Action]:
        """Find all active actions in the specified schema."""
        query = f"""
            SELECT * FROM {schema}.actions 
            WHERE is_active = true AND deleted_at IS NULL
            ORDER BY priority DESC, created_at ASC
        """
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [self._row_to_action(row) for row in rows]
    
    async def find_healthy_actions(self, schema: str) -> List[Action]:
        """Find all healthy actions in the specified schema."""
        query = f"""
            SELECT * FROM {schema}.actions 
            WHERE is_healthy = true AND deleted_at IS NULL
            ORDER BY created_at DESC
        """
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [self._row_to_action(row) for row in rows]
    
    async def update_health_status(
        self, 
        action_id: ActionId, 
        is_healthy: bool,
        error_message: Optional[str],
        schema: str
    ) -> bool:
        """Update action health status."""
        query = f"""
            UPDATE {schema}.actions 
            SET is_healthy = $1, health_check_error = $2, 
                last_health_check_at = $3, updated_at = $4
            WHERE id = $5
        """
        
        now = datetime.now()
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(query, is_healthy, error_message, now, now, action_id.value)
            return result.split()[-1] == "1"
    
    async def update_statistics(
        self, 
        action_id: ActionId,
        execution_time_ms: int,
        success: bool,
        schema: str
    ) -> bool:
        """Update action execution statistics."""
        if success:
            query = f"""
                UPDATE {schema}.actions 
                SET total_executions = total_executions + 1,
                    successful_executions = successful_executions + 1,
                    avg_execution_time_ms = CASE 
                        WHEN total_executions = 0 THEN $1
                        ELSE (avg_execution_time_ms * total_executions + $1) / (total_executions + 1)
                    END,
                    updated_at = $2
                WHERE id = $3
            """
        else:
            query = f"""
                UPDATE {schema}.actions 
                SET total_executions = total_executions + 1,
                    failed_executions = failed_executions + 1,
                    updated_at = $2
                WHERE id = $3
            """
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(query, execution_time_ms, datetime.now(), action_id.value)
            return result.split()[-1] == "1"
    
    async def get_action_statistics(
        self, 
        action_id: ActionId, 
        schema: str
    ) -> Optional[Dict[str, Any]]:
        """Get action execution statistics."""
        query = f"""
            SELECT total_executions, successful_executions, failed_executions,
                   avg_execution_time_ms, created_at, updated_at
            FROM {schema}.actions 
            WHERE id = $1
        """
        
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(query, action_id.value)
            if not row:
                return None
            
            success_rate = 0.0
            if row['total_executions'] > 0:
                success_rate = (row['successful_executions'] / row['total_executions']) * 100.0
            
            return {
                'total_executions': row['total_executions'],
                'successful_executions': row['successful_executions'],
                'failed_executions': row['failed_executions'],
                'success_rate': success_rate,
                'avg_execution_time_ms': row['avg_execution_time_ms'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            }
    
    async def count_actions(self, schema: str, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count actions in the specified schema."""
        where_conditions = ["deleted_at IS NULL"]
        params = []
        param_count = 0
        
        if filters:
            if "action_type" in filters:
                param_count += 1
                where_conditions.append(f"action_type = ${param_count}")
                params.append(filters["action_type"])
            
            if "is_active" in filters:
                param_count += 1
                where_conditions.append(f"is_active = ${param_count}")
                params.append(filters["is_active"])
        
        where_clause = " AND ".join(where_conditions)
        query = f"SELECT COUNT(*) FROM {schema}.actions WHERE {where_clause}"
        
        async with self.connection_pool.acquire() as conn:
            return await conn.fetchval(query, *params)
    
    def _row_to_action(self, row: asyncpg.Record) -> Action:
        """Convert database row to Action entity."""
        return Action(
            id=ActionId(row['id']),
            name=row['name'],
            action_type=ActionType(row['action_type']),
            handler_class=row['handler_class'],
            config=json.loads(row['config']) if row['config'] else {},
            event_patterns=row['event_patterns'] or [],
            conditions=json.loads(row['conditions']) if row['conditions'] else {},
            is_active=row['is_active'],
            priority=row['priority'],
            timeout_seconds=row['timeout_seconds'],
            retry_policy=json.loads(row['retry_policy']) if row['retry_policy'] else {},
            max_concurrent_executions=row['max_concurrent_executions'],
            rate_limit_per_minute=row['rate_limit_per_minute'],
            is_healthy=row['is_healthy'],
            last_health_check_at=row['last_health_check_at'],
            health_check_error=row['health_check_error'],
            total_executions=row['total_executions'],
            successful_executions=row['successful_executions'],
            failed_executions=row['failed_executions'],
            avg_execution_time_ms=row['avg_execution_time_ms'],
            description=row['description'],
            tags=row['tags'] or [],
            owner_team=row['owner_team'],
            metadata=json.loads(row['metadata']) if row['metadata'] else {},
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            deleted_at=row['deleted_at']
        )