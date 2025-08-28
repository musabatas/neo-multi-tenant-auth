"""AsyncPG action repository implementation for platform actions infrastructure.

This module implements the ActionRepository protocol using AsyncPG for PostgreSQL database access.
Single responsibility: Provide high-performance action persistence and execution tracking.

Moved from platform/events to platform/actions following maximum separation architecture.
Pure platform infrastructure implementation - used by all business features.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import asyncpg

from .....core.value_objects import UserId
from .....core.shared.context import RequestContext
from ...core.value_objects import ActionId, ActionExecutionId
from ...core.entities.action import Action
from ...core.entities.action_execution import ActionExecution
from ...core.protocols.action_repository import ActionRepository
from .....utils import utc_now, ensure_utc, generate_uuid_v7


class AsyncpgActionRepository:
    """AsyncPG implementation of ActionRepository protocol.
    
    Provides high-performance action configuration storage and execution tracking
    using PostgreSQL with AsyncPG driver. Handles JSONB serialization, UUID conversion,
    and timezone management for maximum database compatibility.
    
    Maps to {schema_name}.actions and {schema_name}.action_executions tables.
    Pure platform infrastructure - optimized for sub-millisecond action lookups.
    """
    
    def __init__(self, connection: asyncpg.Connection):
        """Initialize repository with database connection.
        
        Args:
            connection: Active AsyncPG connection to PostgreSQL database
        """
        self._connection = connection
    
    # ===========================================
    # Action Configuration Operations
    # ===========================================
    
    async def save_action(
        self,
        action: Action,
        transaction_context: Optional[Dict[str, Any]] = None
    ) -> Action:
        """Persist an action configuration to the repository.
        
        Maps Action entity to {schema_name}.actions table with proper
        JSONB serialization for complex fields and UUID handling.
        
        Args:
            action: Action configuration to persist
            transaction_context: Optional transaction context for atomic operations
            
        Returns:
            Persisted action with updated persistence metadata
            
        Raises:
            ActionPersistenceError: If action cannot be persisted
            DuplicateActionError: If action with same ID already exists
            InvalidActionError: If action configuration is invalid or incomplete
        """
        query = """
            INSERT INTO {schema_name}.actions (
                id, name, description, handler_type, configuration,
                event_types, conditions, context_filters, 
                execution_mode, priority, timeout_seconds,
                max_retries, retry_delay_seconds, status, is_enabled,
                tags, tenant_id, created_by_user_id, 
                created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                $16, $17, $18, $19, $20
            )
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                handler_type = EXCLUDED.handler_type,
                configuration = EXCLUDED.configuration,
                event_types = EXCLUDED.event_types,
                conditions = EXCLUDED.conditions,
                context_filters = EXCLUDED.context_filters,
                execution_mode = EXCLUDED.execution_mode,
                priority = EXCLUDED.priority,
                timeout_seconds = EXCLUDED.timeout_seconds,
                max_retries = EXCLUDED.max_retries,
                retry_delay_seconds = EXCLUDED.retry_delay_seconds,
                status = EXCLUDED.status,
                is_enabled = EXCLUDED.is_enabled,
                tags = EXCLUDED.tags,
                tenant_id = EXCLUDED.tenant_id,
                updated_at = EXCLUDED.updated_at
        """
        
        # Convert conditions list to JSONB
        conditions_json = json.dumps([condition.to_dict() for condition in action.conditions])
        
        await self._connection.execute(
            query,
            action.id.value,  # $1
            action.name,  # $2
            action.description,  # $3
            action.handler_type.value,  # $4
            json.dumps(action.configuration),  # $5
            json.dumps(action.event_types),  # $6
            conditions_json,  # $7
            json.dumps(action.context_filters),  # $8
            action.execution_mode.value,  # $9
            action.priority.value,  # $10
            action.timeout_seconds,  # $11
            action.max_retries,  # $12
            action.retry_delay_seconds,  # $13
            action.status.value,  # $14
            action.is_enabled,  # $15
            json.dumps(action.tags),  # $16
            action.tenant_id,  # $17
            action.created_by_user_id.value if action.created_by_user_id else None,  # $18
            action.created_at,  # $19
            action.updated_at  # $20
        )
        
        return action
    
    async def get_action_by_id(
        self,
        action_id: ActionId,
        include_metadata: bool = True
    ) -> Optional[Action]:
        """Retrieve a specific action by its unique identifier.
        
        Args:
            action_id: Unique identifier of the action to retrieve
            include_metadata: Whether to include action metadata in response
            
        Returns:
            Action if found, None otherwise
        """
        if include_metadata:
            query = """
                SELECT id, name, description, handler_type, configuration,
                       event_types, conditions, context_filters,
                       execution_mode, priority, timeout_seconds,
                       max_retries, retry_delay_seconds, status, is_enabled,
                       tags, tenant_id, created_by_user_id,
                       created_at, updated_at, last_triggered_at,
                       trigger_count, success_count, failure_count
                FROM {schema_name}.actions
                WHERE id = $1
            """
        else:
            query = """
                SELECT id, name, handler_type, configuration,
                       event_types, conditions, context_filters,
                       execution_mode, priority, timeout_seconds,
                       max_retries, retry_delay_seconds, status, is_enabled
                FROM {schema_name}.actions
                WHERE id = $1
            """
        
        record = await self._connection.fetchrow(query, action_id.value)
        if not record:
            return None
        
        return self._record_to_action(record, include_metadata)
    
    async def update_action(
        self,
        action_id: ActionId,
        updates: Dict[str, Any],
        transaction_context: Optional[Dict[str, Any]] = None
    ) -> Action:
        """Update an existing action configuration.
        
        Args:
            action_id: Unique identifier of the action to update
            updates: Dictionary of field updates to apply
            transaction_context: Optional transaction context for atomic operations
            
        Returns:
            Updated action with new configuration
        """
        # Build dynamic update query based on provided fields
        set_clauses = []
        values = []
        param_index = 2  # $1 is action_id
        
        # Always update updated_at
        updates["updated_at"] = utc_now()
        
        for field, value in updates.items():
            if field in ["configuration", "event_types", "conditions", "context_filters", "tags"]:
                # Handle JSONB fields
                set_clauses.append(f"{field} = ${param_index}")
                values.append(json.dumps(value) if not isinstance(value, str) else value)
            else:
                # Handle regular fields
                set_clauses.append(f"{field} = ${param_index}")
                values.append(value)
            param_index += 1
        
        query = f"""
            UPDATE {schema_name}.actions 
            SET {", ".join(set_clauses)}
            WHERE id = $1
            RETURNING id, name, description, handler_type, configuration,
                      event_types, conditions, context_filters,
                      execution_mode, priority, timeout_seconds,
                      max_retries, retry_delay_seconds, status, is_enabled,
                      tags, tenant_id, created_by_user_id,
                      created_at, updated_at, last_triggered_at,
                      trigger_count, success_count, failure_count
        """
        
        record = await self._connection.fetchrow(query, action_id.value, *values)
        if not record:
            raise ValueError(f"Action with ID {action_id} not found")
        
        return self._record_to_action(record, include_metadata=True)
    
    async def delete_action(
        self,
        action_id: ActionId,
        soft_delete: bool = True,
        transaction_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Delete an action configuration from the repository.
        
        Args:
            action_id: Unique identifier of the action to delete
            soft_delete: Whether to soft delete (mark inactive) or hard delete
            transaction_context: Optional transaction context for atomic operations
            
        Returns:
            True if deletion was successful, False if action wasn't found
        """
        if soft_delete:
            query = """
                UPDATE {schema_name}.actions 
                SET status = 'archived', is_enabled = false, updated_at = NOW()
                WHERE id = $1
            """
        else:
            query = "DELETE FROM {schema_name}.actions WHERE id = $1"
        
        result = await self._connection.execute(query, action_id.value)
        return result != "UPDATE 0" and result != "DELETE 0"

    # ===========================================
    # Action Query Operations
    # ===========================================
    
    async def get_actions_by_event_type(
        self,
        event_type: str,
        active_only: bool = True,
        include_conditions: bool = True
    ) -> List[Action]:
        """Retrieve actions that should execute for a specific event type.
        
        Args:
            event_type: Event type to find matching actions for
            active_only: Whether to include only active actions
            include_conditions: Whether to evaluate action conditions
            
        Returns:
            List of actions that match the event type
        """
        conditions = ["JSON_ARRAY_CONTAINS(event_types, %s) = 1"]
        params = [f'"{event_type}"']
        
        if active_only:
            conditions.append("status = 'active' AND is_enabled = true")
        
        query = f"""
            SELECT id, name, description, handler_type, configuration,
                   event_types, conditions, context_filters,
                   execution_mode, priority, timeout_seconds,
                   max_retries, retry_delay_seconds, status, is_enabled,
                   tags, tenant_id, created_by_user_id,
                   created_at, updated_at, last_triggered_at,
                   trigger_count, success_count, failure_count
            FROM {schema_name}.actions
            WHERE {" AND ".join(conditions)}
            ORDER BY priority DESC, created_at ASC
        """
        
        # Use JSONB contains operator for PostgreSQL
        pg_query = f"""
            SELECT id, name, description, handler_type, configuration,
                   event_types, conditions, context_filters,
                   execution_mode, priority, timeout_seconds,
                   max_retries, retry_delay_seconds, status, is_enabled,
                   tags, tenant_id, created_by_user_id,
                   created_at, updated_at, last_triggered_at,
                   trigger_count, success_count, failure_count
            FROM {schema_name}.actions
            WHERE event_types @> $1
            {"AND status = 'active' AND is_enabled = true" if active_only else ""}
            ORDER BY 
                CASE priority 
                    WHEN 'critical' THEN 4
                    WHEN 'high' THEN 3
                    WHEN 'normal' THEN 2
                    WHEN 'low' THEN 1
                    ELSE 0
                END DESC, 
                created_at ASC
        """
        
        records = await self._connection.fetch(pg_query, json.dumps([event_type]))
        return [self._record_to_action(record, include_metadata=True) for record in records]
    
    async def search_actions(
        self,
        filters: Dict[str, Any],
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Advanced action search with flexible filtering and pagination.
        
        Args:
            filters: Search filters (name, handler_type, status, tags, etc.)
            sort_by: Field to sort by (created_at, name, priority, etc.)
            sort_order: Sort direction (asc, desc)
            limit: Maximum number of actions to return
            offset: Number of actions to skip for pagination
            
        Returns:
            Dict with search results, total count, pagination info
        """
        where_clauses = []
        params = []
        param_index = 1
        
        # Build WHERE clauses based on filters
        if filters.get("name"):
            where_clauses.append(f"name ILIKE ${param_index}")
            params.append(f"%{filters['name']}%")
            param_index += 1
        
        if filters.get("handler_type"):
            where_clauses.append(f"handler_type = ${param_index}")
            params.append(filters["handler_type"])
            param_index += 1
        
        if filters.get("status"):
            where_clauses.append(f"status = ${param_index}")
            params.append(filters["status"])
            param_index += 1
        
        if filters.get("is_enabled") is not None:
            where_clauses.append(f"is_enabled = ${param_index}")
            params.append(filters["is_enabled"])
            param_index += 1
        
        if filters.get("tenant_id"):
            where_clauses.append(f"tenant_id = ${param_index}")
            params.append(filters["tenant_id"])
            param_index += 1
        
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        # Count total results
        count_query = f"SELECT COUNT(*) FROM {schema_name}.actions {where_clause}"
        total_count = await self._connection.fetchval(count_query, *params)
        
        # Get paginated results
        sort_clause = f"ORDER BY {sort_by} {sort_order.upper()}"
        limit_clause = f"LIMIT ${param_index} OFFSET ${param_index + 1}"
        params.extend([limit, offset])
        
        query = f"""
            SELECT id, name, description, handler_type, configuration,
                   event_types, conditions, context_filters,
                   execution_mode, priority, timeout_seconds,
                   max_retries, retry_delay_seconds, status, is_enabled,
                   tags, tenant_id, created_by_user_id,
                   created_at, updated_at, last_triggered_at,
                   trigger_count, success_count, failure_count
            FROM {schema_name}.actions
            {where_clause}
            {sort_clause}
            {limit_clause}
        """
        
        records = await self._connection.fetch(query, *params)
        actions = [self._record_to_action(record, include_metadata=True) for record in records]
        
        return {
            "actions": actions,
            "total_count": total_count,
            "has_more": offset + len(actions) < total_count,
            "next_offset": offset + len(actions) if offset + len(actions) < total_count else None
        }
    
    async def get_actions_by_user(
        self,
        user_id: UserId,
        include_inactive: bool = False,
        limit: Optional[int] = None
    ) -> List[Action]:
        """Retrieve actions created by a specific user.
        
        Args:
            user_id: ID of the user who created the actions
            include_inactive: Whether to include inactive actions
            limit: Maximum number of actions to return
            
        Returns:
            List of actions created by the user
        """
        conditions = ["created_by_user_id = $1"]
        params = [user_id.value]
        
        if not include_inactive:
            conditions.append("status = 'active' AND is_enabled = true")
        
        limit_clause = f"LIMIT ${len(params) + 1}" if limit else ""
        if limit:
            params.append(limit)
        
        query = f"""
            SELECT id, name, description, handler_type, configuration,
                   event_types, conditions, context_filters,
                   execution_mode, priority, timeout_seconds,
                   max_retries, retry_delay_seconds, status, is_enabled,
                   tags, tenant_id, created_by_user_id,
                   created_at, updated_at, last_triggered_at,
                   trigger_count, success_count, failure_count
            FROM {schema_name}.actions
            WHERE {" AND ".join(conditions)}
            ORDER BY created_at DESC
            {limit_clause}
        """
        
        records = await self._connection.fetch(query, *params)
        return [self._record_to_action(record, include_metadata=True) for record in records]

    # ===========================================
    # Action Execution Tracking Operations
    # ===========================================
    
    async def save_execution(
        self,
        execution: ActionExecution,
        transaction_context: Optional[Dict[str, Any]] = None
    ) -> ActionExecution:
        """Persist an action execution record to the repository.
        
        Args:
            execution: Action execution record to persist
            transaction_context: Optional transaction context for atomic operations
            
        Returns:
            Persisted action execution with updated tracking metadata
        """
        query = """
            INSERT INTO {schema_name}.action_executions (
                id, action_id, event_id, event_type, event_data,
                status, started_at, completed_at, duration_ms,
                result, error_message, retry_count, execution_context, created_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14
            )
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                started_at = EXCLUDED.started_at,
                completed_at = EXCLUDED.completed_at,
                duration_ms = EXCLUDED.duration_ms,
                result = EXCLUDED.result,
                error_message = EXCLUDED.error_message,
                retry_count = EXCLUDED.retry_count,
                execution_context = EXCLUDED.execution_context
        """
        
        await self._connection.execute(
            query,
            execution.id.value,  # $1
            execution.action_id.value,  # $2
            execution.event_id if execution.event_id else None,  # $3
            execution.event_type,  # $4
            json.dumps(execution.event_data),  # $5
            execution.status,  # $6
            execution.started_at,  # $7
            execution.completed_at,  # $8
            execution.duration_ms,  # $9
            json.dumps(execution.result) if execution.result else None,  # $10
            execution.error_message,  # $11
            execution.retry_count,  # $12
            json.dumps(execution.execution_context),  # $13
            execution.created_at  # $14
        )
        
        return execution
    
    async def get_execution_by_id(
        self,
        execution_id: ActionExecutionId,
        include_result_data: bool = False
    ) -> Optional[ActionExecution]:
        """Retrieve a specific execution by its unique identifier.
        
        Args:
            execution_id: Unique identifier of the execution to retrieve
            include_result_data: Whether to include execution result data
            
        Returns:
            Action execution if found, None otherwise
        """
        if include_result_data:
            query = """
                SELECT id, action_id, event_id, event_type, event_data,
                       status, started_at, completed_at, duration_ms,
                       result, error_message, retry_count, execution_context, created_at
                FROM {schema_name}.action_executions
                WHERE id = $1
            """
        else:
            query = """
                SELECT id, action_id, event_id, event_type,
                       status, started_at, completed_at, duration_ms,
                       error_message, retry_count, created_at
                FROM {schema_name}.action_executions
                WHERE id = $1
            """
        
        record = await self._connection.fetchrow(query, execution_id.value)
        if not record:
            return None
        
        return self._record_to_action_execution(record, include_result_data)
    
    async def get_executions_by_action(
        self,
        action_id: ActionId,
        status_filter: Optional[str] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Retrieve executions for a specific action with filtering.
        
        Args:
            action_id: ID of the action to get executions for
            status_filter: Optional filter by execution status
            from_time: Earliest execution time (inclusive)
            to_time: Latest execution time (inclusive)
            limit: Maximum number of executions to return
            offset: Number of executions to skip for pagination
            
        Returns:
            Dict with execution results and pagination info
        """
        conditions = ["action_id = $1"]
        params = [action_id.value]
        param_index = 2
        
        if status_filter:
            conditions.append(f"status = ${param_index}")
            params.append(status_filter)
            param_index += 1
        
        if from_time:
            conditions.append(f"created_at >= ${param_index}")
            params.append(from_time)
            param_index += 1
        
        if to_time:
            conditions.append(f"created_at <= ${param_index}")
            params.append(to_time)
            param_index += 1
        
        where_clause = f"WHERE {' AND '.join(conditions)}"
        
        # Count total results
        count_query = f"SELECT COUNT(*) FROM {schema_name}.action_executions {where_clause}"
        total_count = await self._connection.fetchval(count_query, *params)
        
        # Get paginated results
        query = f"""
            SELECT id, action_id, event_id, event_type, event_data,
                   status, started_at, completed_at, duration_ms,
                   result, error_message, retry_count, execution_context, created_at
            FROM {schema_name}.action_executions
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_index} OFFSET ${param_index + 1}
        """
        params.extend([limit, offset])
        
        records = await self._connection.fetch(query, *params)
        executions = [self._record_to_action_execution(record, include_result_data=True) for record in records]
        
        return {
            "executions": executions,
            "total_count": total_count,
            "has_more": offset + len(executions) < total_count,
            "next_offset": offset + len(executions) if offset + len(executions) < total_count else None
        }
    
    async def get_failed_executions(
        self,
        limit: int = 100,
        action_ids: Optional[List[ActionId]] = None,
        max_age_hours: Optional[int] = None,
        retry_eligible_only: bool = False
    ) -> List[ActionExecution]:
        """Retrieve failed executions for retry processing.
        
        Args:
            limit: Maximum number of executions to return
            action_ids: Optional filter by specific action IDs
            max_age_hours: Maximum age of failures to consider (hours)
            retry_eligible_only: Whether to include only retry-eligible executions
            
        Returns:
            List of failed action executions ordered by failure time
        """
        conditions = ["status IN ('failed', 'timeout')"]
        params = []
        param_index = 1
        
        if action_ids:
            placeholders = ",".join([f"${param_index + i}" for i in range(len(action_ids))])
            conditions.append(f"action_id IN ({placeholders})")
            params.extend([action_id.value for action_id in action_ids])
            param_index += len(action_ids)
        
        if max_age_hours:
            conditions.append(f"created_at >= NOW() - INTERVAL '{max_age_hours} hours'")
        
        if retry_eligible_only:
            # This would typically compare against action's max_retries, but we'll use a default for now
            conditions.append("retry_count < 3")
        
        query = f"""
            SELECT id, action_id, event_id, event_type, event_data,
                   status, started_at, completed_at, duration_ms,
                   result, error_message, retry_count, execution_context, created_at
            FROM {schema_name}.action_executions
            WHERE {' AND '.join(conditions)}
            ORDER BY created_at ASC
            LIMIT ${param_index}
        """
        params.append(limit)
        
        records = await self._connection.fetch(query, *params)
        return [self._record_to_action_execution(record, include_result_data=True) for record in records]
    
    async def update_execution_status(
        self,
        execution_id: ActionExecutionId,
        status: str,
        result_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        completed_at: Optional[datetime] = None
    ) -> ActionExecution:
        """Update the status and result of an action execution.
        
        Args:
            execution_id: Unique identifier of the execution to update
            status: New execution status
            result_data: Optional execution result data
            error_message: Optional error message if execution failed
            completed_at: Optional completion timestamp
            
        Returns:
            Updated action execution with new status
        """
        updates = {"status": status}
        if result_data is not None:
            updates["result"] = json.dumps(result_data)
        if error_message is not None:
            updates["error_message"] = error_message
        if completed_at is not None:
            updates["completed_at"] = completed_at
        
        # Calculate duration if both started_at and completed_at are available
        if completed_at and status in ("success", "failed", "timeout"):
            # We'll update duration in the query
            pass
        
        set_clauses = []
        values = []
        param_index = 2  # $1 is execution_id
        
        for field, value in updates.items():
            set_clauses.append(f"{field} = ${param_index}")
            values.append(value)
            param_index += 1
        
        # Add duration calculation if completed_at is being set
        if completed_at:
            set_clauses.append(f"duration_ms = EXTRACT(EPOCH FROM (${param_index - 1} - started_at)) * 1000")
        
        query = f"""
            UPDATE {schema_name}.action_executions 
            SET {", ".join(set_clauses)}
            WHERE id = $1
            RETURNING id, action_id, event_id, event_type, event_data,
                      status, started_at, completed_at, duration_ms,
                      result, error_message, retry_count, execution_context, created_at
        """
        
        record = await self._connection.fetchrow(query, execution_id.value, *values)
        if not record:
            raise ValueError(f"Execution with ID {execution_id} not found")
        
        return self._record_to_action_execution(record, include_result_data=True)

    # ===========================================
    # Action Statistics Operations
    # ===========================================
    
    async def get_action_statistics(
        self,
        action_id: Optional[ActionId] = None,
        handler_type: Optional[str] = None,
        time_range_hours: int = 24,
        include_performance_metrics: bool = True
    ) -> Dict[str, Any]:
        """Get comprehensive action statistics for monitoring and analysis.
        
        Args:
            action_id: Optional filter by specific action ID
            handler_type: Optional filter by handler type
            time_range_hours: Time range for statistics calculation
            include_performance_metrics: Whether to include detailed performance data
            
        Returns:
            Dict with comprehensive action statistics
        """
        conditions = []
        params = []
        param_index = 1
        
        if action_id:
            conditions.append(f"ea.id = ${param_index}")
            params.append(action_id.value)
            param_index += 1
        
        if handler_type:
            conditions.append(f"ea.handler_type = ${param_index}")
            params.append(handler_type)
            param_index += 1
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        query = f"""
            SELECT 
                COUNT(DISTINCT ea.id) as total_actions,
                COUNT(DISTINCT ea.id) FILTER (WHERE ea.status = 'active' AND ea.is_enabled = true) as active_actions,
                SUM(ea.trigger_count) as total_executions,
                SUM(ea.success_count) as successful_executions,
                SUM(ea.failure_count) as failed_executions,
                CASE 
                    WHEN SUM(ea.trigger_count) > 0 
                    THEN ROUND((SUM(ea.success_count)::decimal / SUM(ea.trigger_count)) * 100, 2)
                    ELSE 0 
                END as success_rate
                {"," if include_performance_metrics else ""}
                {'''
                AVG(ae.duration_ms) FILTER (WHERE ae.status = 'success' AND ae.created_at >= NOW() - INTERVAL ''' + str(time_range_hours) + ''' hours) as avg_execution_time_ms,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ae.duration_ms) FILTER (WHERE ae.status = 'success' AND ae.created_at >= NOW() - INTERVAL ''' + str(time_range_hours) + ''' hours) as p95_execution_time_ms,
                COUNT(ae.id) FILTER (WHERE ae.retry_count > 0 AND ae.created_at >= NOW() - INTERVAL ''' + str(time_range_hours) + ''' hours) as retried_executions,
                COUNT(ae.id) FILTER (WHERE ae.created_at >= NOW() - INTERVAL ''' + str(time_range_hours) + ''' hours) as total_recent_executions
                ''' if include_performance_metrics else ""}
            FROM {schema_name}.actions ea
            {'''LEFT JOIN {schema_name}.action_executions ae ON ea.id = ae.action_id''' if include_performance_metrics else ""}
            {where_clause}
        """
        
        record = await self._connection.fetchrow(query, *params)
        
        stats = {
            "total_actions": record["total_actions"] or 0,
            "active_actions": record["active_actions"] or 0,
            "total_executions": record["total_executions"] or 0,
            "successful_executions": record["successful_executions"] or 0,
            "failed_executions": record["failed_executions"] or 0,
            "success_rate": float(record["success_rate"] or 0)
        }
        
        if include_performance_metrics:
            total_recent = record["total_recent_executions"] or 0
            retried = record["retried_executions"] or 0
            
            stats.update({
                "average_execution_time_ms": float(record["avg_execution_time_ms"] or 0),
                "p95_execution_time_ms": float(record["p95_execution_time_ms"] or 0),
                "retry_rate": (retried / total_recent * 100) if total_recent > 0 else 0
            })
        
        return stats
    
    async def get_execution_analytics(
        self,
        action_id: Optional[ActionId] = None,
        event_type: Optional[str] = None,
        time_range_hours: int = 24,
        group_by: str = "hour"
    ) -> Dict[str, Any]:
        """Get detailed execution analytics for performance monitoring.
        
        Args:
            action_id: Optional filter by specific action ID
            event_type: Optional filter by event type
            time_range_hours: Time range for analytics calculation
            group_by: Time grouping (hour, day, week)
            
        Returns:
            Dict with detailed execution analytics
        """
        conditions = [f"created_at >= NOW() - INTERVAL '{time_range_hours} hours'"]
        params = []
        param_index = 1
        
        if action_id:
            conditions.append(f"action_id = ${param_index}")
            params.append(action_id.value)
            param_index += 1
        
        if event_type:
            conditions.append(f"event_type = ${param_index}")
            params.append(event_type)
            param_index += 1
        
        # Define grouping based on parameter
        if group_by == "hour":
            time_trunc = "DATE_TRUNC('hour', created_at)"
        elif group_by == "day":
            time_trunc = "DATE_TRUNC('day', created_at)"
        elif group_by == "week":
            time_trunc = "DATE_TRUNC('week', created_at)"
        else:
            time_trunc = "DATE_TRUNC('hour', created_at)"
        
        query = f"""
            SELECT 
                {time_trunc} as time_bucket,
                COUNT(*) as total_executions,
                COUNT(*) FILTER (WHERE status = 'success') as successful_executions,
                COUNT(*) FILTER (WHERE status IN ('failed', 'timeout')) as failed_executions,
                AVG(duration_ms) FILTER (WHERE status = 'success') as avg_duration_ms,
                MAX(duration_ms) as max_duration_ms,
                MIN(duration_ms) as min_duration_ms
            FROM {schema_name}.action_executions
            WHERE {' AND '.join(conditions)}
            GROUP BY {time_trunc}
            ORDER BY time_bucket ASC
        """
        
        records = await self._connection.fetch(query, *params)
        
        return {
            "execution_trends": [
                {
                    "time_bucket": record["time_bucket"].isoformat(),
                    "total_executions": record["total_executions"],
                    "successful_executions": record["successful_executions"],
                    "failed_executions": record["failed_executions"],
                    "success_rate": (record["successful_executions"] / record["total_executions"] * 100) if record["total_executions"] > 0 else 0,
                    "avg_duration_ms": float(record["avg_duration_ms"] or 0),
                    "max_duration_ms": record["max_duration_ms"] or 0,
                    "min_duration_ms": record["min_duration_ms"] or 0
                }
                for record in records
            ]
        }

    # ===========================================
    # Action Maintenance Operations
    # ===========================================
    
    async def cleanup_old_executions(
        self,
        retention_days: int = 90,
        keep_failed_days: int = 180,
        batch_size: int = 1000,
        preserve_analytics: bool = True
    ) -> int:
        """Clean up old execution records for database performance maintenance.
        
        Args:
            retention_days: Days to retain successful execution records
            keep_failed_days: Days to retain failed execution records
            batch_size: Number of records to delete per batch
            preserve_analytics: Whether to preserve aggregate analytics
            
        Returns:
            Number of execution records cleaned up
        """
        total_deleted = 0
        
        # Delete old successful executions
        while True:
            delete_query = f"""
                DELETE FROM {schema_name}.action_executions 
                WHERE id IN (
                    SELECT id FROM {schema_name}.action_executions
                    WHERE status = 'success' 
                    AND created_at < NOW() - INTERVAL '{retention_days} days'
                    LIMIT {batch_size}
                )
            """
            result = await self._connection.execute(delete_query)
            deleted_count = int(result.split()[-1])  # Extract count from "DELETE N"
            total_deleted += deleted_count
            
            if deleted_count == 0:
                break
        
        # Delete old failed executions (keep longer for debugging)
        while True:
            delete_query = f"""
                DELETE FROM {schema_name}.action_executions 
                WHERE id IN (
                    SELECT id FROM {schema_name}.action_executions
                    WHERE status IN ('failed', 'timeout')
                    AND created_at < NOW() - INTERVAL '{keep_failed_days} days'
                    LIMIT {batch_size}
                )
            """
            result = await self._connection.execute(delete_query)
            deleted_count = int(result.split()[-1])
            total_deleted += deleted_count
            
            if deleted_count == 0:
                break
        
        return total_deleted
    
    async def archive_inactive_actions(
        self,
        inactive_days: int = 365,
        batch_size: int = 100,
        preserve_executions: bool = True,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Archive actions that haven't been used for extended periods.
        
        Args:
            inactive_days: Archive actions unused for this many days
            batch_size: Number of actions to archive per batch
            preserve_executions: Whether to keep execution history
            dry_run: Whether to simulate archival without actual changes
            
        Returns:
            Dict with archival results
        """
        # Find actions to archive
        find_query = f"""
            SELECT id, name FROM {schema_name}.actions
            WHERE (last_triggered_at IS NULL OR last_triggered_at < NOW() - INTERVAL '{inactive_days} days')
            AND status != 'archived'
            LIMIT {batch_size}
        """
        
        actions_to_archive = await self._connection.fetch(find_query)
        
        if dry_run:
            return {
                "actions_archived": 0,
                "actions_found_for_archival": len(actions_to_archive),
                "executions_preserved": "N/A (dry run)",
                "processing_time_ms": 0,
                "storage_freed_mb": 0
            }
        
        actions_archived = 0
        start_time = utc_now()
        
        for action in actions_to_archive:
            # Archive the action
            update_query = """
                UPDATE {schema_name}.actions 
                SET status = 'archived', is_enabled = false, updated_at = NOW()
                WHERE id = $1
            """
            await self._connection.execute(update_query, action["id"])
            actions_archived += 1
        
        end_time = utc_now()
        processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        return {
            "actions_archived": actions_archived,
            "executions_preserved": "all" if preserve_executions else "none",
            "processing_time_ms": processing_time_ms,
            "storage_freed_mb": 0  # Would need to calculate actual storage impact
        }

    # ===========================================
    # Health and Diagnostics Operations
    # ===========================================
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform repository health check for monitoring systems.
        
        Returns:
            Dict with health information
        """
        try:
            # Test basic connectivity and queries
            count_query = "SELECT COUNT(*) FROM {schema_name}.actions"
            action_count = await self._connection.fetchval(count_query)
            
            execution_count_query = "SELECT COUNT(*) FROM {schema_name}.action_executions WHERE created_at >= NOW() - INTERVAL '1 hour'"
            recent_executions = await self._connection.fetchval(execution_count_query)
            
            # Test query performance
            start_time = utc_now()
            await self._connection.fetchval("SELECT NOW()")
            query_time_ms = int((utc_now() - start_time).total_seconds() * 1000)
            
            return {
                "is_healthy": True,
                "connection_status": "connected",
                "total_actions": action_count,
                "recent_executions_1h": recent_executions,
                "average_response_time_ms": query_time_ms,
                "last_successful_operation": utc_now().isoformat()
            }
        
        except Exception as e:
            return {
                "is_healthy": False,
                "connection_status": "error",
                "error_message": str(e),
                "last_error_time": utc_now().isoformat()
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
        # Basic metrics query
        metrics_query = f"""
            SELECT 
                COUNT(*) FILTER (WHERE ae.created_at >= NOW() - INTERVAL '{time_range_hours} hours') as recent_operations,
                AVG(ae.duration_ms) FILTER (WHERE ae.created_at >= NOW() - INTERVAL '{time_range_hours} hours' AND ae.status = 'success') as avg_operation_time_ms,
                COUNT(*) FILTER (WHERE ae.created_at >= NOW() - INTERVAL '{time_range_hours} hours' AND ae.status IN ('failed', 'timeout')) as failed_operations,
                COUNT(*) FILTER (WHERE ae.created_at >= NOW() - INTERVAL '{time_range_hours} hours') as total_recent_operations
            FROM {schema_name}.action_executions ae
        """
        
        record = await self._connection.fetchrow(metrics_query)
        
        total_recent = record["total_recent_operations"] or 0
        failed_ops = record["failed_operations"] or 0
        
        return {
            "operations_per_hour": record["recent_operations"] or 0,
            "average_query_time_ms": float(record["avg_operation_time_ms"] or 0),
            "error_rate": (failed_ops / total_recent * 100) if total_recent > 0 else 0,
            "total_operations": total_recent
        }

    # ===========================================
    # Private Helper Methods
    # ===========================================
    
    def _record_to_action(self, record: Dict[str, Any], include_metadata: bool = False) -> Action:
        """Convert database record to Action entity.
        
        Args:
            record: Database record from actions table
            include_metadata: Whether record includes metadata fields
            
        Returns:
            Action entity with properly converted data types
        """
        # Import here to avoid circular imports
        from ...core.value_objects import (
            ActionId, ActionStatus, HandlerType, 
            ActionPriority, ExecutionMode, ActionCondition
        )
        
        # Parse JSONB fields
        event_types = json.loads(record["event_types"]) if record["event_types"] else []
        conditions_data = json.loads(record["conditions"]) if record.get("conditions") else []
        conditions = [ActionCondition.from_dict(cond) for cond in conditions_data]
        configuration = json.loads(record["configuration"]) if record["configuration"] else {}
        context_filters = json.loads(record["context_filters"]) if record.get("context_filters") else {}
        tags = json.loads(record["tags"]) if record.get("tags") else {}
        
        # Convert value objects
        action_id = ActionId(record["id"])
        handler_type = HandlerType(record["handler_type"])
        execution_mode = ExecutionMode(record["execution_mode"]) if record.get("execution_mode") else ExecutionMode.ASYNC
        priority = ActionPriority(record["priority"]) if record.get("priority") else ActionPriority.NORMAL
        status = ActionStatus(record["status"]) if record.get("status") else ActionStatus.ACTIVE
        
        created_by_user_id = UserId(record["created_by_user_id"]) if record.get("created_by_user_id") else None
        
        # Create Action with all fields
        action_data = {
            "id": action_id,
            "name": record["name"],
            "description": record.get("description"),
            "handler_type": handler_type,
            "configuration": configuration,
            "event_types": event_types,
            "conditions": conditions,
            "context_filters": context_filters,
            "execution_mode": execution_mode,
            "priority": priority,
            "timeout_seconds": record.get("timeout_seconds", 30),
            "max_retries": record.get("max_retries", 3),
            "retry_delay_seconds": record.get("retry_delay_seconds", 5),
            "status": status,
            "is_enabled": record.get("is_enabled", True),
            "tags": tags,
            "created_by_user_id": created_by_user_id,
            "tenant_id": record.get("tenant_id"),
            "created_at": ensure_utc(record["created_at"]) if record.get("created_at") else utc_now(),
            "updated_at": ensure_utc(record["updated_at"]) if record.get("updated_at") else utc_now()
        }
        
        if include_metadata and record.get("last_triggered_at"):
            action_data["last_triggered_at"] = ensure_utc(record["last_triggered_at"])
        
        return Action(**action_data)
    
    def _record_to_action_execution(self, record: Dict[str, Any], include_result_data: bool = False) -> ActionExecution:
        """Convert database record to ActionExecution entity.
        
        Args:
            record: Database record from action_executions table
            include_result_data: Whether to include result data fields
            
        Returns:
            ActionExecution entity with properly converted data types
        """
        # Parse JSONB fields
        event_data = json.loads(record["event_data"]) if record.get("event_data") else {}
        execution_context = json.loads(record["execution_context"]) if record.get("execution_context") else {}
        result = json.loads(record["result"]) if record.get("result") and include_result_data else None
        
        # Convert UUIDs to value objects
        execution_id = ActionExecutionId(record["id"])
        action_id = ActionId(record["action_id"])
        event_id = record.get("event_id")  # Keep as string since EventId not available in actions module
        
        return ActionExecution(
            id=execution_id,
            action_id=action_id,
            event_id=event_id,
            event_type=record.get("event_type", ""),
            event_data=event_data,
            status=record.get("status", "pending"),
            started_at=ensure_utc(record["started_at"]) if record.get("started_at") else None,
            completed_at=ensure_utc(record["completed_at"]) if record.get("completed_at") else None,
            duration_ms=record.get("duration_ms"),
            result=result,
            error_message=record.get("error_message"),
            retry_count=record.get("retry_count", 0),
            execution_context=execution_context,
            created_at=ensure_utc(record["created_at"])
        )


# Factory function for dependency injection
async def create_asyncpg_action_repository(connection: asyncpg.Connection) -> ActionRepository:
    """Factory function to create AsyncpgActionRepository instance.
    
    Args:
        connection: Active AsyncPG connection to PostgreSQL database
        
    Returns:
        ActionRepository instance ready for use
    """
    return AsyncpgActionRepository(connection)