"""Webhook subscription repository implementation using existing database infrastructure.

This implementation follows the patterns established in the organizations feature,
leveraging existing database service without duplicating connection management.
"""

import json
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone

from ....core.value_objects import WebhookSubscriptionId, WebhookEndpointId, WebhookEventTypeId
from ....core.exceptions import EntityNotFoundError, EntityAlreadyExistsError, DatabaseError
from ....features.database.entities.protocols import DatabaseRepository
from ..entities.webhook_subscription import WebhookSubscription
from ..entities.protocols import WebhookSubscriptionRepository
from ..utils.queries import (
    WEBHOOK_SUBSCRIPTION_INSERT_DETAILED,
    WEBHOOK_SUBSCRIPTION_UPDATE_DETAILED,
    WEBHOOK_SUBSCRIPTION_GET_BY_ID,
    WEBHOOK_SUBSCRIPTION_GET_BY_ENDPOINT_ID,
    WEBHOOK_SUBSCRIPTION_GET_BY_EVENT_TYPE,
    WEBHOOK_SUBSCRIPTION_GET_ACTIVE,
    WEBHOOK_SUBSCRIPTION_GET_BY_CONTEXT,
    WEBHOOK_SUBSCRIPTION_DELETE_BY_ID,
    WEBHOOK_SUBSCRIPTION_EXISTS_BY_ID,
    WEBHOOK_SUBSCRIPTION_UPDATE_LAST_TRIGGERED,
    WEBHOOK_SUBSCRIPTION_GET_MATCHING_SUBSCRIPTIONS,
)
from ..utils.error_handling import handle_webhook_error


logger = logging.getLogger(__name__)


class WebhookSubscriptionDatabaseRepository:
    """Database repository for webhook subscription operations.
    
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
        self._table = f"{schema}.webhook_subscriptions"
    
    async def save(self, subscription: WebhookSubscription) -> WebhookSubscription:
        """Save a webhook subscription to the database."""
        try:
            # Check if subscription already exists
            existing = await self.get_by_id(subscription.id)
            if existing:
                raise EntityAlreadyExistsError("WebhookSubscription", str(subscription.id.value))
            
            query = WEBHOOK_SUBSCRIPTION_INSERT_DETAILED.format(schema=self._schema)
            
            row = await self._db.fetchrow(
                query,
                subscription.id.value,
                subscription.endpoint_id.value,
                subscription.event_type_id.value,
                subscription.event_type,
                json.dumps(subscription.event_filters),
                subscription.is_active,
                subscription.context_id,
                subscription.subscription_name,
                subscription.description,
                subscription.created_at,
                subscription.updated_at,
                subscription.last_triggered_at,
            )
            
            if row:
                return self._row_to_subscription(row)
            
            return subscription
            
        except Exception as e:
            handle_webhook_error("save", "webhook_subscription", subscription.id, e, {"schema": self._schema})
            raise
    
    async def get_by_id(self, subscription_id: WebhookSubscriptionId) -> Optional[WebhookSubscription]:
        """Get a webhook subscription by ID."""
        try:
            query = WEBHOOK_SUBSCRIPTION_GET_BY_ID.format(schema=self._schema)
            row = await self._db.fetchrow(query, subscription_id.value)
            return self._row_to_subscription(row) if row else None
            
        except Exception as e:
            handle_webhook_error("get_by_id", "webhook_subscription", subscription_id, e, {"schema": self._schema})
            raise
    
    async def get_by_endpoint_id(self, endpoint_id: WebhookEndpointId, active_only: bool = True) -> List[WebhookSubscription]:
        """Get webhook subscriptions by endpoint ID."""
        try:
            query = WEBHOOK_SUBSCRIPTION_GET_BY_ENDPOINT_ID.format(schema=self._schema)
            rows = await self._db.fetch(query, endpoint_id.value, active_only)
            return [self._row_to_subscription(row) for row in rows]
            
        except Exception as e:
            handle_webhook_error(
                "get_by_endpoint_id", 
                "webhook_subscription", 
                None, 
                e, 
                {"schema": self._schema, "endpoint_id": str(endpoint_id.value), "active_only": active_only}
            )
            raise
    
    async def get_by_event_type(self, event_type: str, active_only: bool = True) -> List[WebhookSubscription]:
        """Get webhook subscriptions by event type."""
        try:
            query = WEBHOOK_SUBSCRIPTION_GET_BY_EVENT_TYPE.format(schema=self._schema)
            rows = await self._db.fetch(query, event_type, active_only)
            return [self._row_to_subscription(row) for row in rows]
            
        except Exception as e:
            handle_webhook_error(
                "get_by_event_type", 
                "webhook_subscription", 
                None, 
                e, 
                {"schema": self._schema, "event_type": event_type, "active_only": active_only}
            )
            raise
    
    async def get_by_context(self, context_id: UUID, active_only: bool = True) -> List[WebhookSubscription]:
        """Get webhook subscriptions by context ID."""
        try:
            query = WEBHOOK_SUBSCRIPTION_GET_BY_CONTEXT.format(schema=self._schema)
            rows = await self._db.fetch(query, context_id, active_only)
            return [self._row_to_subscription(row) for row in rows]
            
        except Exception as e:
            handle_webhook_error(
                "get_by_context", 
                "webhook_subscription", 
                None, 
                e, 
                {"schema": self._schema, "context_id": str(context_id), "active_only": active_only}
            )
            raise
    
    async def get_active_subscriptions(self) -> List[WebhookSubscription]:
        """Get all active webhook subscriptions."""
        try:
            query = WEBHOOK_SUBSCRIPTION_GET_ACTIVE.format(schema=self._schema)
            rows = await self._db.fetch(query)
            return [self._row_to_subscription(row) for row in rows]
            
        except Exception as e:
            handle_webhook_error("get_active_subscriptions", "webhook_subscription", None, e, {"schema": self._schema})
            raise
    
    async def get_matching_subscriptions(
        self, 
        event_type: str, 
        context_id: Optional[UUID] = None
    ) -> List[WebhookSubscription]:
        """Get subscriptions that match the given event type and context."""
        try:
            query = WEBHOOK_SUBSCRIPTION_GET_MATCHING_SUBSCRIPTIONS.format(schema=self._schema)
            rows = await self._db.fetch(query, event_type, context_id)
            return [self._row_to_subscription(row) for row in rows]
            
        except Exception as e:
            handle_webhook_error(
                "get_matching_subscriptions", 
                "webhook_subscription", 
                None, 
                e, 
                {"schema": self._schema, "event_type": event_type, "context_id": str(context_id) if context_id else None}
            )
            raise

    async def get_matching_subscriptions_optimized(
        self, 
        event_type: str, 
        context_id: Optional[UUID] = None,
        select_columns: Optional[List[str]] = None,
        use_index_only: bool = False
    ) -> List[WebhookSubscription]:
        """Get subscriptions that match the given event type and context with optimizations."""
        try:
            # Build column selection
            columns = "*"
            if select_columns:
                # Ensure essential columns are included for object construction
                essential_columns = {"id", "endpoint_id", "event_types", "context_filters", "is_active"}
                all_columns = set(select_columns) | essential_columns
                columns = ", ".join(sorted(all_columns))
            
            # Use index-only scan hint if requested
            index_hint = ""
            if use_index_only:
                index_hint = "/*+ INDEX_ONLY_SCAN(webhook_subscriptions) */"
            
            query = f"""
                {index_hint}
                SELECT {columns} FROM {{schema}}.webhook_subscriptions 
                WHERE is_active = true
                AND (
                    event_types @> $1::jsonb 
                    OR event_types @> '["*"]'::jsonb
                )
                AND (
                    $2::uuid IS NULL 
                    OR context_filters IS NULL 
                    OR context_filters @> $2::text::jsonb
                )
                ORDER BY created_at ASC
            """.format(schema=self._schema)
            
            rows = await self._db.fetch(query, f'["{event_type}"]', context_id)
            return [self._row_to_subscription(row) for row in rows]
            
        except Exception as e:
            handle_webhook_error(
                "get_matching_subscriptions_optimized", 
                "webhook_subscription", 
                None, 
                e, 
                {
                    "schema": self._schema, 
                    "event_type": event_type, 
                    "context_id": str(context_id) if context_id else None,
                    "use_index_only": use_index_only
                }
            )
            raise
    
    async def update(self, subscription: WebhookSubscription) -> WebhookSubscription:
        """Update webhook subscription."""
        try:
            query = WEBHOOK_SUBSCRIPTION_UPDATE_DETAILED.format(schema=self._schema)
            
            row = await self._db.fetchrow(
                query,
                subscription.id.value,
                subscription.endpoint_id.value,
                subscription.event_type_id.value,
                subscription.event_type,
                json.dumps(subscription.event_filters),
                subscription.is_active,
                subscription.context_id,
                subscription.subscription_name,
                subscription.description,
                subscription.updated_at,
                subscription.last_triggered_at,
            )
            
            if row:
                return self._row_to_subscription(row)
            
            raise EntityNotFoundError("WebhookSubscription", str(subscription.id.value))
            
        except Exception as e:
            handle_webhook_error("update", "webhook_subscription", subscription.id, e, {"schema": self._schema})
            raise
    
    async def delete(self, subscription_id: WebhookSubscriptionId) -> bool:
        """Delete a webhook subscription."""
        try:
            query = WEBHOOK_SUBSCRIPTION_DELETE_BY_ID.format(schema=self._schema)
            result = await self._db.execute(query, subscription_id.value)
            return result == "DELETE 1"
            
        except Exception as e:
            handle_webhook_error("delete", "webhook_subscription", subscription_id, e, {"schema": self._schema})
            raise
    
    async def update_last_triggered(self, subscription_id: WebhookSubscriptionId) -> bool:
        """Update the last triggered timestamp for a subscription."""
        try:
            query = WEBHOOK_SUBSCRIPTION_UPDATE_LAST_TRIGGERED.format(schema=self._schema)
            result = await self._db.execute(query, subscription_id.value)
            return result == "UPDATE 1"
            
        except Exception as e:
            handle_webhook_error("update_last_triggered", "webhook_subscription", subscription_id, e, {"schema": self._schema})
            raise
    
    async def exists(self, subscription_id: WebhookSubscriptionId) -> bool:
        """Check if webhook subscription exists."""
        try:
            query = WEBHOOK_SUBSCRIPTION_EXISTS_BY_ID.format(schema=self._schema)
            result = await self._db.fetchval(query, subscription_id.value)
            return bool(result)
            
        except Exception as e:
            handle_webhook_error("exists", "webhook_subscription", subscription_id, e, {"schema": self._schema})
            raise
    
    def _row_to_subscription(self, row) -> WebhookSubscription:
        """Convert database row to WebhookSubscription entity."""
        # Parse JSON fields
        event_filters = json.loads(row["event_filters"]) if row["event_filters"] else {}
        
        return WebhookSubscription(
            id=WebhookSubscriptionId(row["id"]),
            endpoint_id=WebhookEndpointId(row["endpoint_id"]),
            event_type_id=WebhookEventTypeId(row["event_type_id"]),
            event_type=row["event_type"],
            event_filters=event_filters,
            is_active=row["is_active"],
            context_id=row["context_id"],
            subscription_name=row["subscription_name"],
            description=row["description"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_triggered_at=row["last_triggered_at"],
        )