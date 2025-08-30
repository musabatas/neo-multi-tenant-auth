"""AsyncPG implementation of ActionExecutionRepositoryProtocol."""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

import asyncpg

from ...domain.entities.action_execution import ActionExecution
from ...domain.entities.action import ActionStatus
from ...domain.value_objects.execution_id import ExecutionId
from ...domain.value_objects.action_id import ActionId
from ....events.domain.value_objects.event_id import EventId
from ...application.protocols.action_execution_repository import ActionExecutionRepositoryProtocol


class AsyncPGActionExecutionRepository(ActionExecutionRepositoryProtocol):
    """
    PostgreSQL implementation of ActionExecutionRepositoryProtocol using asyncpg.
    
    Provides schema-intensive operations for multi-tenant action execution management.
    """
    
    def __init__(self, connection_pool: asyncpg.Pool):
        self.connection_pool = connection_pool
    
    async def save(self, execution: ActionExecution, schema: str) -> ActionExecution:
        """Save an action execution to the specified schema."""
        query = f"""
            INSERT INTO {schema}.action_executions (
                id, event_id, action_id, execution_context, input_data, output_data,
                status, queued_at, started_at, completed_at, execution_duration_ms,
                attempt_number, is_retry, parent_execution_id, error_message,
                error_details, error_stack_trace, queue_message_id, worker_id,
                memory_usage_mb, cpu_time_ms, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                $16, $17, $18, $19, $20, $21, $22, $23
            )
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                started_at = EXCLUDED.started_at,
                completed_at = EXCLUDED.completed_at,
                execution_duration_ms = EXCLUDED.execution_duration_ms,
                error_message = EXCLUDED.error_message,
                error_details = EXCLUDED.error_details,
                error_stack_trace = EXCLUDED.error_stack_trace,
                output_data = EXCLUDED.output_data,
                worker_id = EXCLUDED.worker_id,
                memory_usage_mb = EXCLUDED.memory_usage_mb,
                cpu_time_ms = EXCLUDED.cpu_time_ms,
                updated_at = EXCLUDED.updated_at
            RETURNING *
        """
        
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                execution.id.value,
                execution.event_id.value,
                execution.action_id.value,
                json.dumps(execution.execution_context),
                json.dumps(execution.input_data),
                json.dumps(execution.output_data),
                execution.status.value,
                execution.queued_at,
                execution.started_at,
                execution.completed_at,
                execution.execution_duration_ms,
                execution.attempt_number,
                execution.is_retry,
                execution.parent_execution_id.value if execution.parent_execution_id else None,
                execution.error_message,
                json.dumps(execution.error_details) if execution.error_details else None,
                execution.error_stack_trace,
                execution.queue_message_id,
                execution.worker_id,
                execution.memory_usage_mb,
                execution.cpu_time_ms,
                execution.created_at,
                execution.updated_at
            )
            
            return self._row_to_execution(row)
    
    async def get_by_id(self, execution_id: ExecutionId, schema: str) -> Optional[ActionExecution]:
        """Get action execution by ID from the specified schema."""
        query = f"SELECT * FROM {schema}.action_executions WHERE id = $1"
        
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(query, execution_id.value)
            return self._row_to_execution(row) if row else None
    
    async def update(self, execution: ActionExecution, schema: str) -> ActionExecution:
        """Update an existing action execution in the specified schema."""
        execution.updated_at = datetime.now()
        return await self.save(execution, schema)
    
    async def list_executions(
        self, 
        schema: str,
        limit: int = 50, 
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ActionExecution]:
        """List action executions from the specified schema with optional filtering."""
        where_conditions = []
        params = []
        param_count = 0
        
        if filters:
            if "status" in filters:
                param_count += 1
                where_conditions.append(f"status = ${param_count}")
                params.append(filters["status"])
            
            if "action_id" in filters:
                param_count += 1
                where_conditions.append(f"action_id = ${param_count}")
                params.append(filters["action_id"])
            
            if "event_id" in filters:
                param_count += 1
                where_conditions.append(f"event_id = ${param_count}")
                params.append(filters["event_id"])
            
            if "is_retry" in filters:
                param_count += 1
                where_conditions.append(f"is_retry = ${param_count}")
                params.append(filters["is_retry"])
            
            if "worker_id" in filters:
                param_count += 1
                where_conditions.append(f"worker_id = ${param_count}")
                params.append(filters["worker_id"])
            
            if "from_date" in filters:
                param_count += 1
                where_conditions.append(f"created_at >= ${param_count}")
                params.append(filters["from_date"])
            
            if "to_date" in filters:
                param_count += 1
                where_conditions.append(f"created_at <= ${param_count}")
                params.append(filters["to_date"])
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        param_count += 1
        limit_param = param_count
        param_count += 1
        offset_param = param_count
        
        query = f"""
            SELECT * FROM {schema}.action_executions 
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ${limit_param} OFFSET ${offset_param}
        """
        
        params.extend([limit, offset])
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_execution(row) for row in rows]
    
    async def get_executions_by_action(
        self, 
        action_id: ActionId, 
        schema: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[ActionExecution]:
        """Get executions for a specific action."""
        query = f"""
            SELECT * FROM {schema}.action_executions 
            WHERE action_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, action_id.value, limit, offset)
            return [self._row_to_execution(row) for row in rows]
    
    async def get_executions_by_event(
        self, 
        event_id: EventId, 
        schema: str
    ) -> List[ActionExecution]:
        """Get executions for a specific event."""
        query = f"""
            SELECT * FROM {schema}.action_executions 
            WHERE event_id = $1
            ORDER BY created_at ASC
        """
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, event_id.value)
            return [self._row_to_execution(row) for row in rows]
    
    async def get_executions_by_status(
        self, 
        status: ActionStatus, 
        schema: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[ActionExecution]:
        """Get executions by status."""
        query = f"""
            SELECT * FROM {schema}.action_executions 
            WHERE status = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, status.value, limit, offset)
            return [self._row_to_execution(row) for row in rows]
    
    async def get_pending_executions(self, schema: str, limit: int = 100) -> List[ActionExecution]:
        """Get pending executions ready for processing."""
        query = f"""
            SELECT * FROM {schema}.action_executions 
            WHERE status = 'pending'
            ORDER BY queued_at ASC
            LIMIT $1
        """
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, limit)
            return [self._row_to_execution(row) for row in rows]
    
    async def get_failed_executions(
        self, 
        schema: str,
        retry_eligible_only: bool = False,
        limit: int = 100
    ) -> List[ActionExecution]:
        """Get failed executions, optionally only those eligible for retry."""
        if retry_eligible_only:
            # This would need action retry policy to determine eligibility
            # For now, just check if there are fewer attempts than typical max retries
            query = f"""
                SELECT * FROM {schema}.action_executions 
                WHERE status = 'failed' AND attempt_number < 4
                ORDER BY created_at DESC
                LIMIT $1
            """
        else:
            query = f"""
                SELECT * FROM {schema}.action_executions 
                WHERE status = 'failed'
                ORDER BY created_at DESC
                LIMIT $1
            """
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, limit)
            return [self._row_to_execution(row) for row in rows]
    
    async def get_retry_executions(
        self, 
        parent_execution_id: ExecutionId, 
        schema: str
    ) -> List[ActionExecution]:
        """Get all retry executions for a parent execution."""
        query = f"""
            SELECT * FROM {schema}.action_executions 
            WHERE parent_execution_id = $1
            ORDER BY attempt_number ASC
        """
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, parent_execution_id.value)
            return [self._row_to_execution(row) for row in rows]
    
    async def update_status(
        self, 
        execution_id: ExecutionId, 
        status: ActionStatus, 
        schema: str,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update execution status and related fields."""
        set_clauses = ["status = $2", "updated_at = $3"]
        params = [execution_id.value, status.value, datetime.now()]
        param_count = 3
        
        if error_message is not None:
            param_count += 1
            set_clauses.append(f"error_message = ${param_count}")
            params.append(error_message)
        
        if error_details is not None:
            param_count += 1
            set_clauses.append(f"error_details = ${param_count}")
            params.append(json.dumps(error_details))
        
        if output_data is not None:
            param_count += 1
            set_clauses.append(f"output_data = ${param_count}")
            params.append(json.dumps(output_data))
        
        # Update completed_at for terminal statuses
        if status in [ActionStatus.COMPLETED, ActionStatus.FAILED, ActionStatus.CANCELLED, ActionStatus.TIMEOUT]:
            param_count += 1
            set_clauses.append(f"completed_at = ${param_count}")
            params.append(datetime.now())
        
        query = f"""
            UPDATE {schema}.action_executions 
            SET {', '.join(set_clauses)}
            WHERE id = $1
        """
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(query, *params)
            return result.split()[-1] == "1"
    
    async def mark_as_started(
        self, 
        execution_id: ExecutionId, 
        worker_id: str,
        schema: str
    ) -> bool:
        """Mark execution as started by a worker."""
        query = f"""
            UPDATE {schema}.action_executions 
            SET status = $2, started_at = $3, worker_id = $4, updated_at = $5
            WHERE id = $1 AND status = 'pending'
        """
        
        now = datetime.now()
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(
                query, 
                execution_id.value, 
                ActionStatus.RUNNING.value,
                now, 
                worker_id, 
                now
            )
            return result.split()[-1] == "1"
    
    async def mark_as_completed(
        self, 
        execution_id: ExecutionId, 
        output_data: Dict[str, Any],
        execution_duration_ms: int,
        schema: str
    ) -> bool:
        """Mark execution as completed successfully."""
        query = f"""
            UPDATE {schema}.action_executions 
            SET status = $2, output_data = $3, execution_duration_ms = $4, 
                completed_at = $5, updated_at = $6
            WHERE id = $1
        """
        
        now = datetime.now()
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(
                query,
                execution_id.value,
                ActionStatus.COMPLETED.value,
                json.dumps(output_data),
                execution_duration_ms,
                now,
                now
            )
            return result.split()[-1] == "1"
    
    async def mark_as_failed(
        self, 
        execution_id: ExecutionId, 
        error_message: str,
        error_details: Dict[str, Any],
        error_stack_trace: Optional[str],
        execution_duration_ms: Optional[int],
        schema: str
    ) -> bool:
        """Mark execution as failed."""
        query = f"""
            UPDATE {schema}.action_executions 
            SET status = $2, error_message = $3, error_details = $4, 
                error_stack_trace = $5, execution_duration_ms = $6,
                completed_at = $7, updated_at = $8
            WHERE id = $1
        """
        
        now = datetime.now()
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(
                query,
                execution_id.value,
                ActionStatus.FAILED.value,
                error_message,
                json.dumps(error_details),
                error_stack_trace,
                execution_duration_ms,
                now,
                now
            )
            return result.split()[-1] == "1"
    
    async def update_performance_metrics(
        self, 
        execution_id: ExecutionId,
        memory_usage_mb: Optional[int],
        cpu_time_ms: Optional[int],
        schema: str
    ) -> bool:
        """Update execution performance metrics."""
        set_clauses = ["updated_at = $2"]
        params = [execution_id.value, datetime.now()]
        param_count = 2
        
        if memory_usage_mb is not None:
            param_count += 1
            set_clauses.append(f"memory_usage_mb = ${param_count}")
            params.append(memory_usage_mb)
        
        if cpu_time_ms is not None:
            param_count += 1
            set_clauses.append(f"cpu_time_ms = ${param_count}")
            params.append(cpu_time_ms)
        
        if len(set_clauses) == 1:  # Only updated_at
            return True
        
        query = f"""
            UPDATE {schema}.action_executions 
            SET {', '.join(set_clauses)}
            WHERE id = $1
        """
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(query, *params)
            return result.split()[-1] == "1"
    
    async def get_execution_statistics(
        self, 
        schema: str,
        action_id: Optional[ActionId] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get execution statistics for actions."""
        where_conditions = []
        params = []
        param_count = 0
        
        if action_id:
            param_count += 1
            where_conditions.append(f"action_id = ${param_count}")
            params.append(action_id.value)
        
        if start_date:
            param_count += 1
            where_conditions.append(f"created_at >= ${param_count}")
            params.append(start_date)
        
        if end_date:
            param_count += 1
            where_conditions.append(f"created_at <= ${param_count}")
            params.append(end_date)
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        query = f"""
            SELECT 
                COUNT(*) as total_executions,
                COUNT(*) FILTER (WHERE status = 'completed') as successful_executions,
                COUNT(*) FILTER (WHERE status = 'failed') as failed_executions,
                COUNT(*) FILTER (WHERE status = 'running') as running_executions,
                COUNT(*) FILTER (WHERE status = 'pending') as pending_executions,
                AVG(execution_duration_ms) FILTER (WHERE execution_duration_ms IS NOT NULL) as avg_execution_time_ms,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY execution_duration_ms) 
                    FILTER (WHERE execution_duration_ms IS NOT NULL) as median_execution_time_ms,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_duration_ms) 
                    FILTER (WHERE execution_duration_ms IS NOT NULL) as p95_execution_time_ms,
                AVG(memory_usage_mb) FILTER (WHERE memory_usage_mb IS NOT NULL) as avg_memory_usage_mb,
                AVG(cpu_time_ms) FILTER (WHERE cpu_time_ms IS NOT NULL) as avg_cpu_time_ms,
                MIN(created_at) as earliest_execution,
                MAX(created_at) as latest_execution
            FROM {schema}.action_executions
            WHERE {where_clause}
        """
        
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
            
            if not row or row['total_executions'] == 0:
                return {
                    'total_executions': 0,
                    'successful_executions': 0,
                    'failed_executions': 0,
                    'running_executions': 0,
                    'pending_executions': 0,
                    'success_rate': 0.0,
                    'avg_execution_time_ms': 0,
                    'median_execution_time_ms': 0,
                    'p95_execution_time_ms': 0,
                    'avg_memory_usage_mb': 0,
                    'avg_cpu_time_ms': 0,
                    'earliest_execution': None,
                    'latest_execution': None
                }
            
            success_rate = 0.0
            if row['total_executions'] > 0:
                success_rate = (row['successful_executions'] / row['total_executions']) * 100.0
            
            return {
                'total_executions': row['total_executions'],
                'successful_executions': row['successful_executions'],
                'failed_executions': row['failed_executions'],
                'running_executions': row['running_executions'],
                'pending_executions': row['pending_executions'],
                'success_rate': success_rate,
                'avg_execution_time_ms': float(row['avg_execution_time_ms']) if row['avg_execution_time_ms'] else 0.0,
                'median_execution_time_ms': float(row['median_execution_time_ms']) if row['median_execution_time_ms'] else 0.0,
                'p95_execution_time_ms': float(row['p95_execution_time_ms']) if row['p95_execution_time_ms'] else 0.0,
                'avg_memory_usage_mb': float(row['avg_memory_usage_mb']) if row['avg_memory_usage_mb'] else 0.0,
                'avg_cpu_time_ms': float(row['avg_cpu_time_ms']) if row['avg_cpu_time_ms'] else 0.0,
                'earliest_execution': row['earliest_execution'],
                'latest_execution': row['latest_execution']
            }
    
    async def cleanup_old_executions(
        self, 
        schema: str,
        older_than_days: int = 30,
        keep_failed: bool = True
    ) -> int:
        """Clean up old completed executions."""
        cutoff_date = datetime.now() - timedelta(days=older_than_days)
        
        if keep_failed:
            query = f"""
                DELETE FROM {schema}.action_executions 
                WHERE completed_at < $1 AND status = 'completed'
            """
        else:
            query = f"""
                DELETE FROM {schema}.action_executions 
                WHERE completed_at < $1 AND status IN ('completed', 'failed')
            """
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(query, cutoff_date)
            return int(result.split()[-1])
    
    async def count_executions(
        self, 
        schema: str, 
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Count executions in the specified schema."""
        where_conditions = []
        params = []
        param_count = 0
        
        if filters:
            if "status" in filters:
                param_count += 1
                where_conditions.append(f"status = ${param_count}")
                params.append(filters["status"])
            
            if "action_id" in filters:
                param_count += 1
                where_conditions.append(f"action_id = ${param_count}")
                params.append(filters["action_id"])
            
            if "event_id" in filters:
                param_count += 1
                where_conditions.append(f"event_id = ${param_count}")
                params.append(filters["event_id"])
            
            if "is_retry" in filters:
                param_count += 1
                where_conditions.append(f"is_retry = ${param_count}")
                params.append(filters["is_retry"])
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        query = f"SELECT COUNT(*) FROM {schema}.action_executions WHERE {where_clause}"
        
        async with self.connection_pool.acquire() as conn:
            return await conn.fetchval(query, *params)
    
    def _row_to_execution(self, row: asyncpg.Record) -> ActionExecution:
        """Convert database row to ActionExecution entity."""
        return ActionExecution(
            id=ExecutionId(row['id']),
            event_id=EventId(row['event_id']),
            action_id=ActionId(row['action_id']),
            execution_context=json.loads(row['execution_context']) if row['execution_context'] else {},
            input_data=json.loads(row['input_data']) if row['input_data'] else {},
            output_data=json.loads(row['output_data']) if row['output_data'] else {},
            status=ActionStatus(row['status']),
            queued_at=row['queued_at'],
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            execution_duration_ms=row['execution_duration_ms'],
            attempt_number=row['attempt_number'],
            is_retry=row['is_retry'],
            parent_execution_id=ExecutionId(row['parent_execution_id']) if row['parent_execution_id'] else None,
            error_message=row['error_message'],
            error_details=json.loads(row['error_details']) if row['error_details'] else None,
            error_stack_trace=row['error_stack_trace'],
            queue_message_id=row['queue_message_id'],
            worker_id=row['worker_id'],
            memory_usage_mb=row['memory_usage_mb'],
            cpu_time_ms=row['cpu_time_ms'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )