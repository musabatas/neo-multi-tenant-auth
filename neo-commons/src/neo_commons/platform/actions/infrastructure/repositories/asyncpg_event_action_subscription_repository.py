"""AsyncPG implementation of EventActionSubscriptionRepositoryProtocol."""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime

import asyncpg

from ...domain.entities.event_action_subscription import EventActionSubscription
from ...domain.value_objects.subscription_id import SubscriptionId
from ...domain.value_objects.action_id import ActionId
from ...application.protocols.event_action_subscription_repository import EventActionSubscriptionRepositoryProtocol


class AsyncPGEventActionSubscriptionRepository(EventActionSubscriptionRepositoryProtocol):
    """
    PostgreSQL implementation of EventActionSubscriptionRepositoryProtocol using asyncpg.
    
    Provides schema-intensive operations for multi-tenant event-action subscription management.
    """
    
    def __init__(self, connection_pool: asyncpg.Pool):
        self.connection_pool = connection_pool
    
    async def save(self, subscription: EventActionSubscription, schema: str) -> EventActionSubscription:
        """Save an event-action subscription to the specified schema."""
        query = f"""
            INSERT INTO {schema}.event_subscriptions (
                id, action_id, event_pattern, conditions, is_active, priority,
                tenant_filter, organization_filter, source_service_filter,
                rate_limit_per_minute, rate_limit_per_hour, rate_limit_window_start,
                current_rate_count, name, description, created_by,
                created_at, updated_at, deleted_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19
            )
            ON CONFLICT (id) DO UPDATE SET
                event_pattern = EXCLUDED.event_pattern,
                conditions = EXCLUDED.conditions,
                is_active = EXCLUDED.is_active,
                priority = EXCLUDED.priority,
                tenant_filter = EXCLUDED.tenant_filter,
                organization_filter = EXCLUDED.organization_filter,
                source_service_filter = EXCLUDED.source_service_filter,
                rate_limit_per_minute = EXCLUDED.rate_limit_per_minute,
                rate_limit_per_hour = EXCLUDED.rate_limit_per_hour,
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                updated_at = EXCLUDED.updated_at,
                deleted_at = EXCLUDED.deleted_at
            RETURNING *
        """
        
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                subscription.id.value,
                subscription.action_id.value,
                subscription.event_pattern,
                json.dumps(subscription.conditions),
                subscription.is_active,
                subscription.priority,
                subscription.tenant_filter,
                subscription.organization_filter,
                subscription.source_service_filter,
                subscription.rate_limit_per_minute,
                subscription.rate_limit_per_hour,
                subscription.rate_limit_window_start,
                subscription.current_rate_count,
                subscription.name,
                subscription.description,
                subscription.created_by,
                subscription.created_at,
                subscription.updated_at,
                subscription.deleted_at
            )
            
            return self._row_to_subscription(row)
    
    async def get_by_id(self, subscription_id: SubscriptionId, schema: str) -> Optional[EventActionSubscription]:
        """Get event-action subscription by ID from the specified schema."""
        query = f"SELECT * FROM {schema}.event_subscriptions WHERE id = $1 AND deleted_at IS NULL"
        
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(query, subscription_id.value)
            return self._row_to_subscription(row) if row else None
    
    async def get_by_action_id(self, action_id: ActionId, schema: str) -> List[EventActionSubscription]:
        """Get all subscriptions for a specific action."""
        query = f"""
            SELECT * FROM {schema}.event_subscriptions 
            WHERE action_id = $1 AND deleted_at IS NULL
            ORDER BY priority DESC, created_at ASC
        """
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, action_id.value)
            return [self._row_to_subscription(row) for row in rows]
    
    async def find_matching_subscriptions(
        self, 
        event_type: str, 
        schema: str,
        tenant_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        source_service: Optional[str] = None
    ) -> List[EventActionSubscription]:
        """Find subscriptions that match an event type and optional filters."""
        where_conditions = [
            "deleted_at IS NULL",
            "is_active = true"
        ]
        params = [event_type]
        param_count = 1
        
        # Pattern matching conditions
        where_conditions.append(f"""
            ($1 LIKE event_pattern OR 
             event_pattern LIKE '%*%' AND $1 ~ REPLACE(REPLACE(event_pattern, '*', '.*'), '?', '.'))
        """)
        
        # Tenant filter
        if tenant_id:
            param_count += 1
            where_conditions.append(f"(tenant_filter IS NULL OR ${param_count}::uuid = ANY(tenant_filter))")
            params.append(tenant_id)
        else:
            where_conditions.append("tenant_filter IS NULL")
        
        # Organization filter
        if organization_id:
            param_count += 1
            where_conditions.append(f"(organization_filter IS NULL OR ${param_count}::uuid = ANY(organization_filter))")
            params.append(organization_id)
        else:
            where_conditions.append("organization_filter IS NULL")
        
        # Source service filter
        if source_service:
            param_count += 1
            where_conditions.append(f"(source_service_filter IS NULL OR ${param_count} = ANY(source_service_filter))")
            params.append(source_service)
        else:
            where_conditions.append("source_service_filter IS NULL")
        
        where_clause = " AND ".join(where_conditions)
        
        query = f"""
            SELECT * FROM {schema}.event_subscriptions
            WHERE {where_clause}
            ORDER BY priority DESC, created_at ASC
        """
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_subscription(row) for row in rows]
    
    async def list_subscriptions(
        self, 
        schema: str,
        limit: int = 50, 
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[EventActionSubscription]:
        """List subscriptions from the specified schema with optional filtering."""
        where_conditions = ["deleted_at IS NULL"]
        params = []
        param_count = 0
        
        if filters:
            if "action_id" in filters:
                param_count += 1
                where_conditions.append(f"action_id = ${param_count}")
                params.append(filters["action_id"])
            
            if "event_pattern" in filters:
                param_count += 1
                where_conditions.append(f"event_pattern ILIKE ${param_count}")
                params.append(f"%{filters['event_pattern']}%")
            
            if "is_active" in filters:
                param_count += 1
                where_conditions.append(f"is_active = ${param_count}")
                params.append(filters["is_active"])
            
            if "priority" in filters:
                param_count += 1
                where_conditions.append(f"priority = ${param_count}")
                params.append(filters["priority"])
            
            if "created_by" in filters:
                param_count += 1
                where_conditions.append(f"created_by = ${param_count}")
                params.append(filters["created_by"])
        
        where_clause = " AND ".join(where_conditions)
        param_count += 1
        limit_param = param_count
        param_count += 1
        offset_param = param_count
        
        query = f"""
            SELECT * FROM {schema}.event_subscriptions 
            WHERE {where_clause}
            ORDER BY priority DESC, created_at DESC
            LIMIT ${limit_param} OFFSET ${offset_param}
        """
        
        params.extend([limit, offset])
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_subscription(row) for row in rows]
    
    async def update(self, subscription: EventActionSubscription, schema: str) -> EventActionSubscription:
        """Update an existing subscription in the specified schema."""
        subscription.updated_at = datetime.now()
        return await self.save(subscription, schema)
    
    async def delete(self, subscription_id: SubscriptionId, schema: str) -> bool:
        """Soft delete a subscription by ID from the specified schema."""
        query = f"""
            UPDATE {schema}.event_subscriptions 
            SET deleted_at = $2, updated_at = $3
            WHERE id = $1 AND deleted_at IS NULL
        """
        
        now = datetime.now()
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(query, subscription_id.value, now, now)
            return result.split()[-1] == "1"
    
    async def activate_subscription(self, subscription_id: SubscriptionId, schema: str) -> bool:
        """Activate a subscription."""
        query = f"""
            UPDATE {schema}.event_subscriptions 
            SET is_active = true, updated_at = $2
            WHERE id = $1 AND deleted_at IS NULL
        """
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(query, subscription_id.value, datetime.now())
            return result.split()[-1] == "1"
    
    async def deactivate_subscription(self, subscription_id: SubscriptionId, schema: str) -> bool:
        """Deactivate a subscription."""
        query = f"""
            UPDATE {schema}.event_subscriptions 
            SET is_active = false, updated_at = $2
            WHERE id = $1 AND deleted_at IS NULL
        """
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(query, subscription_id.value, datetime.now())
            return result.split()[-1] == "1"
    
    async def update_rate_limit_counter(
        self, 
        subscription_id: SubscriptionId, 
        count: int,
        window_start: datetime,
        schema: str
    ) -> bool:
        """Update rate limit counter and window."""
        query = f"""
            UPDATE {schema}.event_subscriptions 
            SET current_rate_count = $2, rate_limit_window_start = $3, updated_at = $4
            WHERE id = $1 AND deleted_at IS NULL
        """
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(
                query, 
                subscription_id.value, 
                count, 
                window_start,
                datetime.now()
            )
            return result.split()[-1] == "1"
    
    async def reset_rate_limit_counters(self, schema: str) -> int:
        """Reset all rate limit counters (typically called by a scheduled job)."""
        query = f"""
            UPDATE {schema}.event_subscriptions 
            SET current_rate_count = 0, rate_limit_window_start = $1, updated_at = $2
            WHERE deleted_at IS NULL 
            AND (rate_limit_per_minute IS NOT NULL OR rate_limit_per_hour IS NOT NULL)
        """
        
        now = datetime.now()
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(query, now, now)
            return int(result.split()[-1])
    
    async def get_subscriptions_by_pattern(
        self, 
        pattern: str, 
        schema: str
    ) -> List[EventActionSubscription]:
        """Get subscriptions with a specific event pattern."""
        query = f"""
            SELECT * FROM {schema}.event_subscriptions 
            WHERE event_pattern = $1 AND deleted_at IS NULL
            ORDER BY priority DESC, created_at ASC
        """
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, pattern)
            return [self._row_to_subscription(row) for row in rows]
    
    async def get_active_subscriptions(self, schema: str) -> List[EventActionSubscription]:
        """Get all active subscriptions."""
        query = f"""
            SELECT * FROM {schema}.event_subscriptions 
            WHERE is_active = true AND deleted_at IS NULL
            ORDER BY priority DESC, created_at ASC
        """
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [self._row_to_subscription(row) for row in rows]
    
    async def count_subscriptions(
        self, 
        schema: str, 
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Count subscriptions in the specified schema."""
        where_conditions = ["deleted_at IS NULL"]
        params = []
        param_count = 0
        
        if filters:
            if "action_id" in filters:
                param_count += 1
                where_conditions.append(f"action_id = ${param_count}")
                params.append(filters["action_id"])
            
            if "is_active" in filters:
                param_count += 1
                where_conditions.append(f"is_active = ${param_count}")
                params.append(filters["is_active"])
            
            if "created_by" in filters:
                param_count += 1
                where_conditions.append(f"created_by = ${param_count}")
                params.append(filters["created_by"])
        
        where_clause = " AND ".join(where_conditions)
        query = f"SELECT COUNT(*) FROM {schema}.event_subscriptions WHERE {where_clause}"
        
        async with self.connection_pool.acquire() as conn:
            return await conn.fetchval(query, *params)
    
    async def get_subscription_statistics(
        self, 
        schema: str,
        action_id: Optional[ActionId] = None
    ) -> Dict[str, Any]:
        """Get subscription statistics."""
        where_conditions = ["deleted_at IS NULL"]
        params = []
        param_count = 0
        
        if action_id:
            param_count += 1
            where_conditions.append(f"action_id = ${param_count}")
            params.append(action_id.value)
        
        where_clause = " AND ".join(where_conditions)
        
        query = f"""
            SELECT 
                COUNT(*) as total_subscriptions,
                COUNT(*) FILTER (WHERE is_active = true) as active_subscriptions,
                COUNT(*) FILTER (WHERE is_active = false) as inactive_subscriptions,
                COUNT(*) FILTER (WHERE rate_limit_per_minute IS NOT NULL) as rate_limited_subscriptions,
                AVG(priority) as avg_priority,
                MIN(priority) as min_priority,
                MAX(priority) as max_priority,
                COUNT(DISTINCT action_id) as unique_actions,
                COUNT(DISTINCT event_pattern) as unique_patterns,
                MIN(created_at) as earliest_subscription,
                MAX(created_at) as latest_subscription
            FROM {schema}.event_subscriptions
            WHERE {where_clause}
        """
        
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
            
            if not row or row['total_subscriptions'] == 0:
                return {
                    'total_subscriptions': 0,
                    'active_subscriptions': 0,
                    'inactive_subscriptions': 0,
                    'rate_limited_subscriptions': 0,
                    'avg_priority': 0.0,
                    'min_priority': 0,
                    'max_priority': 0,
                    'unique_actions': 0,
                    'unique_patterns': 0,
                    'earliest_subscription': None,
                    'latest_subscription': None
                }
            
            return {
                'total_subscriptions': row['total_subscriptions'],
                'active_subscriptions': row['active_subscriptions'],
                'inactive_subscriptions': row['inactive_subscriptions'],
                'rate_limited_subscriptions': row['rate_limited_subscriptions'],
                'avg_priority': float(row['avg_priority']) if row['avg_priority'] else 0.0,
                'min_priority': row['min_priority'],
                'max_priority': row['max_priority'],
                'unique_actions': row['unique_actions'],
                'unique_patterns': row['unique_patterns'],
                'earliest_subscription': row['earliest_subscription'],
                'latest_subscription': row['latest_subscription']
            }
    
    def _row_to_subscription(self, row: asyncpg.Record) -> EventActionSubscription:
        """Convert database row to EventActionSubscription entity."""
        return EventActionSubscription(
            id=SubscriptionId(row['id']),
            action_id=ActionId(row['action_id']),
            event_pattern=row['event_pattern'],
            conditions=json.loads(row['conditions']) if row['conditions'] else {},
            is_active=row['is_active'],
            priority=row['priority'],
            tenant_filter=list(row['tenant_filter']) if row['tenant_filter'] else None,
            organization_filter=list(row['organization_filter']) if row['organization_filter'] else None,
            source_service_filter=list(row['source_service_filter']) if row['source_service_filter'] else None,
            rate_limit_per_minute=row['rate_limit_per_minute'],
            rate_limit_per_hour=row['rate_limit_per_hour'],
            rate_limit_window_start=row['rate_limit_window_start'],
            current_rate_count=row['current_rate_count'],
            name=row['name'],
            description=row['description'],
            created_by=row['created_by'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            deleted_at=row['deleted_at']
        )