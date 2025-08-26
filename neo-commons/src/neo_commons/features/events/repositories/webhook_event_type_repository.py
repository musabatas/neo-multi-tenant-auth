"""Webhook event type repository implementation using existing database infrastructure.

This implementation follows the patterns established in the organizations feature,
leveraging existing database service without duplicating connection management.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from ....core.value_objects import WebhookEventTypeId
from ....core.exceptions import EntityNotFoundError, EntityAlreadyExistsError, DatabaseError
from ....features.database.entities.protocols import DatabaseRepository
from ..entities.webhook_event_type import WebhookEventType
from ..entities.protocols import WebhookEventTypeRepository
from ..utils.queries import (
    WEBHOOK_EVENT_TYPE_INSERT,
    WEBHOOK_EVENT_TYPE_UPDATE,
    WEBHOOK_EVENT_TYPE_GET_BY_ID,
    WEBHOOK_EVENT_TYPE_GET_BY_EVENT_TYPE,
    WEBHOOK_EVENT_TYPE_GET_BY_CATEGORY,
    WEBHOOK_EVENT_TYPE_LIST_ENABLED,
    WEBHOOK_EVENT_TYPE_DELETE,
)
from ..utils.error_handling import handle_event_type_error


logger = logging.getLogger(__name__)


class WebhookEventTypeDatabaseRepository:
    """Database repository for webhook event type operations.
    
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
        self._table = f"{schema}.webhook_event_types"
    
    async def save(self, event_type: WebhookEventType) -> WebhookEventType:
        """Save a webhook event type to the database."""
        try:
            # Check if event type already exists by ID
            existing = await self.get_by_id(event_type.id)
            if existing:
                raise EntityAlreadyExistsError("WebhookEventType", str(event_type.id.value))
            
            # Check if event_type string is already taken
            existing_by_type = await self.get_by_event_type(event_type.event_type)
            if existing_by_type:
                raise EntityAlreadyExistsError("WebhookEventType", f"event_type={event_type.event_type}")
            
            query = WEBHOOK_EVENT_TYPE_INSERT.format(schema=self._schema)
            
            row = await self._db.fetchrow(
                query,
                event_type.id.value,
                event_type.event_type,
                event_type.category,
                event_type.display_name,
                event_type.description,
                event_type.is_enabled,
                event_type.requires_verification,
                json.dumps(event_type.payload_schema) if event_type.payload_schema else None,
                json.dumps(event_type.example_payload) if event_type.example_payload else None,
                event_type.created_at,
                event_type.updated_at,
            )
            
            if row:
                return self._row_to_event_type(row)
            
            return event_type
            
        except Exception as e:
            handle_event_type_error("save", event_type.id, e, {"schema": self._schema})
            raise
    
    async def get_by_id(self, type_id: WebhookEventTypeId) -> Optional[WebhookEventType]:
        """Get a webhook event type by ID."""
        try:
            query = WEBHOOK_EVENT_TYPE_GET_BY_ID.format(schema=self._schema)
            row = await self._db.fetchrow(query, type_id.value)
            return self._row_to_event_type(row) if row else None
            
        except Exception as e:
            handle_event_type_error("get_by_id", type_id, e, {"schema": self._schema})
            raise
    
    async def get_by_event_type(self, event_type: str) -> Optional[WebhookEventType]:
        """Get a webhook event type by event type string."""
        try:
            query = WEBHOOK_EVENT_TYPE_GET_BY_EVENT_TYPE.format(schema=self._schema)
            row = await self._db.fetchrow(query, event_type)
            return self._row_to_event_type(row) if row else None
            
        except Exception as e:
            handle_event_type_error(
                "get_by_event_type", 
                None, 
                e, 
                {"schema": self._schema, "event_type": event_type}
            )
            raise
    
    async def get_by_category(self, category: str, enabled_only: bool = True) -> List[WebhookEventType]:
        """Get webhook event types by category."""
        try:
            query = WEBHOOK_EVENT_TYPE_GET_BY_CATEGORY.format(schema=self._schema)
            rows = await self._db.fetch(query, category, enabled_only)
            return [self._row_to_event_type(row) for row in rows]
            
        except Exception as e:
            handle_event_type_error(
                "get_by_category", 
                None, 
                e, 
                {"schema": self._schema, "category": category, "enabled_only": enabled_only}
            )
            raise
    
    async def get_enabled_types(self) -> List[WebhookEventType]:
        """Get all enabled webhook event types."""
        try:
            query = WEBHOOK_EVENT_TYPE_LIST_ENABLED.format(schema=self._schema)
            rows = await self._db.fetch(query)
            return [self._row_to_event_type(row) for row in rows]
            
        except Exception as e:
            handle_event_type_error("get_enabled_types", None, e, {"schema": self._schema})
            raise
    
    async def update(self, event_type: WebhookEventType) -> WebhookEventType:
        """Update webhook event type."""
        try:
            query = WEBHOOK_EVENT_TYPE_UPDATE.format(schema=self._schema)
            
            row = await self._db.fetchrow(
                query,
                event_type.id.value,
                event_type.display_name,
                event_type.description,
                event_type.is_enabled,
                event_type.requires_verification,
                json.dumps(event_type.payload_schema) if event_type.payload_schema else None,
                json.dumps(event_type.example_payload) if event_type.example_payload else None,
                event_type.updated_at,
            )
            
            if row:
                return self._row_to_event_type(row)
            
            raise EntityNotFoundError("WebhookEventType", str(event_type.id.value))
            
        except Exception as e:
            handle_event_type_error("update", event_type.id, e, {"schema": self._schema})
            raise
    
    async def delete(self, type_id: WebhookEventTypeId) -> bool:
        """Delete a webhook event type."""
        try:
            query = WEBHOOK_EVENT_TYPE_DELETE.format(schema=self._schema)
            result = await self._db.execute(query, type_id.value)
            return result == "DELETE 1"
            
        except Exception as e:
            handle_event_type_error("delete", type_id, e, {"schema": self._schema})
            raise
    
    def _row_to_event_type(self, row) -> WebhookEventType:
        """Convert database row to WebhookEventType entity."""
        # Parse JSON fields
        payload_schema = None
        if row["payload_schema"]:
            payload_schema = json.loads(row["payload_schema"])
        
        example_payload = None
        if row["example_payload"]:
            example_payload = json.loads(row["example_payload"])
        
        return WebhookEventType(
            id=WebhookEventTypeId(row["id"]),
            event_type=row["event_type"],
            category=row["category"],
            display_name=row["display_name"],
            description=row["description"],
            is_enabled=row["is_enabled"],
            requires_verification=row["requires_verification"],
            payload_schema=payload_schema,
            example_payload=example_payload,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )