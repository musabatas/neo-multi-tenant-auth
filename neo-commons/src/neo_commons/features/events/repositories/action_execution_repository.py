"""
Action Execution Repository Implementation

Provides database operations for action executions using asyncpg.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, timezone

from ....core.value_objects.identifiers import ActionId, ActionExecutionId
from ....infrastructure.database.connection_manager import ConnectionManager
from ..entities.protocols import ActionExecutionRepository

logger = logging.getLogger(__name__)


class ActionExecutionPostgresRepository:
    """PostgreSQL implementation of ActionExecutionRepository."""
    
    def __init__(
        self, 
        connection_manager: ConnectionManager,
        schema: str = "admin"
    ):
        self._connection_manager = connection_manager
        self._schema = schema
        self._table = f"{schema}.action_executions"
    
    async def save_execution(self, execution) -> Any:
        """Save an action execution record."""
        query = f"""
            INSERT INTO {self._table} (
                id, action_id, event_id, event_type, event_data,
                status, started_at, completed_at, duration_ms,
                result, error_message, retry_count, execution_context
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
            ) ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                started_at = EXCLUDED.started_at,
                completed_at = EXCLUDED.completed_at,
                duration_ms = EXCLUDED.duration_ms,
                result = EXCLUDED.result,
                error_message = EXCLUDED.error_message,
                retry_count = EXCLUDED.retry_count,
                execution_context = EXCLUDED.execution_context
            RETURNING 
                id, action_id, event_id, event_type, event_data,
                status, started_at, completed_at, duration_ms,
                result, error_message, retry_count, execution_context, created_at
        """
        
        async with self._connection_manager.get_connection(self._schema.split('.')[0]) as conn:
            row = await conn.fetchrow(
                query,
                str(execution.id.value) if hasattr(execution.id, 'value') else str(execution.id),
                str(execution.action_id.value) if hasattr(execution.action_id, 'value') else str(execution.action_id),
                execution.event_id,
                execution.event_type,
                json.dumps(execution.event_data) if execution.event_data else '{}',
                execution.status if isinstance(execution.status, str) else execution.status.value,
                execution.started_at,
                execution.completed_at,
                execution.duration_ms,
                json.dumps(execution.result) if execution.result else None,
                execution.error_message,
                execution.retry_count,
                json.dumps(execution.execution_context) if execution.execution_context else '{}'
            )
            
            return self._row_to_execution(row)
    
    async def get_execution_by_id(self, execution_id) -> Optional[Any]:
        """Get execution by ID."""
        query = f"""
            SELECT 
                id, action_id, event_id, event_type, event_data,
                status, started_at, completed_at, duration_ms,
                result, error_message, retry_count, execution_context, created_at
            FROM {self._table}
            WHERE id = $1
        """
        
        async with self._connection_manager.get_connection(self._schema.split('.')[0]) as conn:
            row = await conn.fetchrow(
                query, 
                str(execution_id.value) if hasattr(execution_id, 'value') else str(execution_id)
            )
            
            if row:
                return self._row_to_execution(row)
            return None
    
    async def get_executions_by_action(self, action_id, limit: int = 100) -> List[Any]:
        """Get executions for a specific action."""
        query = f"""
            SELECT 
                id, action_id, event_id, event_type, event_data,
                status, started_at, completed_at, duration_ms,
                result, error_message, retry_count, execution_context, created_at
            FROM {self._table}
            WHERE action_id = $1
            ORDER BY created_at DESC
            LIMIT $2
        """
        
        async with self._connection_manager.get_connection(self._schema.split('.')[0]) as conn:
            rows = await conn.fetch(
                query, 
                str(action_id.value) if hasattr(action_id, 'value') else str(action_id), 
                limit
            )
            return [self._row_to_execution(row) for row in rows]
    
    async def get_failed_executions(self, limit: int = 100) -> List[Any]:
        """Get failed executions for retry."""
        query = f"""
            SELECT 
                id, action_id, event_id, event_type, event_data,
                status, started_at, completed_at, duration_ms,
                result, error_message, retry_count, execution_context, created_at
            FROM {self._table}
            WHERE status IN ('failed', 'timeout')
            ORDER BY created_at ASC
            LIMIT $1
        """
        
        async with self._connection_manager.get_connection(self._schema.split('.')[0]) as conn:
            rows = await conn.fetch(query, limit)
            return [self._row_to_execution(row) for row in rows]
    
    async def update_execution(self, execution) -> Any:
        """Update an execution record."""
        query = f"""
            UPDATE {self._table}
            SET 
                status = $2,
                started_at = $3,
                completed_at = $4,
                duration_ms = $5,
                result = $6,
                error_message = $7,
                retry_count = $8,
                execution_context = $9
            WHERE id = $1
            RETURNING 
                id, action_id, event_id, event_type, event_data,
                status, started_at, completed_at, duration_ms,
                result, error_message, retry_count, execution_context, created_at
        """
        
        async with self._connection_manager.get_connection(self._schema.split('.')[0]) as conn:
            row = await conn.fetchrow(
                query,
                str(execution.id.value) if hasattr(execution.id, 'value') else str(execution.id),
                execution.status if isinstance(execution.status, str) else execution.status.value,
                execution.started_at,
                execution.completed_at,
                execution.duration_ms,
                json.dumps(execution.result) if execution.result else None,
                execution.error_message,
                execution.retry_count,
                json.dumps(execution.execution_context) if execution.execution_context else '{}'
            )
            
            if row:
                return self._row_to_execution(row)
            
            raise ValueError(f"Execution with ID {execution.id} not found")
    
    async def get_execution_stats(self, action_id, days: int = 7) -> Dict[str, Any]:
        """Get execution statistics for an action."""
        query = f"""
            SELECT 
                COUNT(*) as total_executions,
                COUNT(*) FILTER (WHERE status = 'success') as successful_executions,
                COUNT(*) FILTER (WHERE status IN ('failed', 'timeout')) as failed_executions,
                COUNT(*) FILTER (WHERE status = 'timeout') as timeout_executions,
                COUNT(*) FILTER (WHERE retry_count > 0) as retry_executions,
                AVG(duration_ms) FILTER (WHERE duration_ms IS NOT NULL) as avg_duration_ms,
                MIN(duration_ms) FILTER (WHERE duration_ms IS NOT NULL) as min_duration_ms,
                MAX(duration_ms) FILTER (WHERE duration_ms IS NOT NULL) as max_duration_ms,
                MIN(created_at) as first_execution,
                MAX(created_at) as last_execution
            FROM {self._table}
            WHERE action_id = $1 
                AND created_at >= NOW() - INTERVAL '{days} days'
        """
        
        async with self._connection_manager.get_connection(self._schema.split('.')[0]) as conn:
            row = await conn.fetchrow(
                query, 
                str(action_id.value) if hasattr(action_id, 'value') else str(action_id)
            )
            
            if row:
                total = row['total_executions'] or 0
                successful = row['successful_executions'] or 0
                
                return {
                    "total_executions": total,
                    "successful_executions": successful,
                    "failed_executions": row['failed_executions'] or 0,
                    "timeout_executions": row['timeout_executions'] or 0,
                    "retry_executions": row['retry_executions'] or 0,
                    "success_rate_percent": (successful / total * 100) if total > 0 else 0.0,
                    "avg_duration_ms": float(row['avg_duration_ms']) if row['avg_duration_ms'] else 0.0,
                    "min_duration_ms": row['min_duration_ms'],
                    "max_duration_ms": row['max_duration_ms'],
                    "first_execution": row['first_execution'],
                    "last_execution": row['last_execution'],
                    "period_days": days
                }
            
            return {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "timeout_executions": 0,
                "retry_executions": 0,
                "success_rate_percent": 0.0,
                "avg_duration_ms": 0.0,
                "min_duration_ms": None,
                "max_duration_ms": None,
                "first_execution": None,
                "last_execution": None,
                "period_days": days
            }
    
    async def get_executions_by_status(
        self, 
        status: str, 
        limit: int = 100,
        action_id: Optional[Any] = None
    ) -> List[Any]:
        """Get executions by status with optional action filter."""
        base_query = f"""
            SELECT 
                id, action_id, event_id, event_type, event_data,
                status, started_at, completed_at, duration_ms,
                result, error_message, retry_count, execution_context, created_at
            FROM {self._table}
            WHERE status = $1
        """
        
        params = [status]
        
        if action_id:
            base_query += " AND action_id = $2"
            params.append(str(action_id.value) if hasattr(action_id, 'value') else str(action_id))
        
        base_query += " ORDER BY created_at DESC LIMIT $" + str(len(params) + 1)
        params.append(limit)
        
        async with self._connection_manager.get_connection(self._schema.split('.')[0]) as conn:
            rows = await conn.fetch(base_query, *params)
            return [self._row_to_execution(row) for row in rows]
    
    async def get_recent_executions(
        self, 
        hours: int = 24, 
        limit: int = 100
    ) -> List[Any]:
        """Get recent executions within specified hours."""
        query = f"""
            SELECT 
                id, action_id, event_id, event_type, event_data,
                status, started_at, completed_at, duration_ms,
                result, error_message, retry_count, execution_context, created_at
            FROM {self._table}
            WHERE created_at >= NOW() - INTERVAL '{hours} hours'
            ORDER BY created_at DESC
            LIMIT $1
        """
        
        async with self._connection_manager.get_connection(self._schema.split('.')[0]) as conn:
            rows = await conn.fetch(query, limit)
            return [self._row_to_execution(row) for row in rows]
    
    async def cleanup_old_executions(
        self, 
        days_to_keep: int = 30,
        statuses_to_cleanup: Optional[List[str]] = None
    ) -> int:
        """Clean up old execution records."""
        base_query = f"""
            DELETE FROM {self._table}
            WHERE created_at < NOW() - INTERVAL '{days_to_keep} days'
        """
        
        params = []
        
        if statuses_to_cleanup:
            placeholders = ','.join(f'${i+1}' for i in range(len(statuses_to_cleanup)))
            base_query += f" AND status IN ({placeholders})"
            params.extend(statuses_to_cleanup)
        
        async with self._connection_manager.get_connection(self._schema.split('.')[0]) as conn:
            result = await conn.execute(base_query, *params)
            deleted_count = int(result.split()[-1]) if result else 0
            
            logger.info(f"Cleaned up {deleted_count} old execution records (older than {days_to_keep} days)")
            return deleted_count
    
    async def get_execution_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get execution summary statistics for the specified time period."""
        query = f"""
            SELECT 
                COUNT(*) as total_executions,
                COUNT(*) FILTER (WHERE status = 'success') as successful,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                COUNT(*) FILTER (WHERE status = 'timeout') as timeout,
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                COUNT(*) FILTER (WHERE status = 'running') as running,
                COUNT(*) FILTER (WHERE retry_count > 0) as retries,
                AVG(duration_ms) FILTER (WHERE duration_ms IS NOT NULL AND status = 'success') as avg_duration_ms,
                COUNT(DISTINCT action_id) as unique_actions,
                COUNT(DISTINCT event_type) as unique_event_types
            FROM {self._table}
            WHERE created_at >= NOW() - INTERVAL '{hours} hours'
        """
        
        async with self._connection_manager.get_connection(self._schema.split('.')[0]) as conn:
            row = await conn.fetchrow(query)
            
            if row:
                total = row['total_executions'] or 0
                successful = row['successful'] or 0
                
                return {
                    "period_hours": hours,
                    "total_executions": total,
                    "successful_executions": successful,
                    "failed_executions": row['failed'] or 0,
                    "timeout_executions": row['timeout'] or 0,
                    "pending_executions": row['pending'] or 0,
                    "running_executions": row['running'] or 0,
                    "retry_executions": row['retries'] or 0,
                    "success_rate_percent": (successful / total * 100) if total > 0 else 0.0,
                    "avg_duration_ms": float(row['avg_duration_ms']) if row['avg_duration_ms'] else 0.0,
                    "unique_actions": row['unique_actions'] or 0,
                    "unique_event_types": row['unique_event_types'] or 0
                }
            
            return {
                "period_hours": hours,
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "timeout_executions": 0,
                "pending_executions": 0,
                "running_executions": 0,
                "retry_executions": 0,
                "success_rate_percent": 0.0,
                "avg_duration_ms": 0.0,
                "unique_actions": 0,
                "unique_event_types": 0
            }
    
    def _row_to_execution(self, row) -> Dict[str, Any]:
        """Convert database row to execution dict."""
        return {
            "id": row['id'],
            "action_id": row['action_id'],
            "event_id": row['event_id'],
            "event_type": row['event_type'],
            "event_data": row['event_data'] if row['event_data'] else {},
            "status": row['status'],
            "started_at": row['started_at'],
            "completed_at": row['completed_at'],
            "duration_ms": row['duration_ms'],
            "result": row['result'] if row['result'] else None,
            "error_message": row['error_message'],
            "retry_count": row['retry_count'],
            "execution_context": row['execution_context'] if row['execution_context'] else {},
            "created_at": row['created_at']
        }