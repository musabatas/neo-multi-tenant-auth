"""Webhook endpoint repository implementation using existing database infrastructure.

This implementation follows the patterns established in the organizations feature,
leveraging existing database service without duplicating connection management.
"""

import json
import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from decimal import Decimal

from ....core.value_objects import WebhookEndpointId, UserId
from ....core.exceptions import EntityNotFoundError, EntityAlreadyExistsError, DatabaseError
from ....features.database.entities.protocols import DatabaseRepository
from ..entities.webhook_endpoint import WebhookEndpoint
from ..entities.protocols import WebhookEndpointRepository
from ..utils.queries import (
    WEBHOOK_ENDPOINT_INSERT,
    WEBHOOK_ENDPOINT_UPDATE,
    WEBHOOK_ENDPOINT_GET_BY_ID,
    WEBHOOK_ENDPOINT_GET_BY_CONTEXT,
    WEBHOOK_ENDPOINT_LIST_ACTIVE,
    WEBHOOK_ENDPOINT_DELETE,
    WEBHOOK_ENDPOINT_UPDATE_LAST_USED,
    WEBHOOK_ENDPOINT_EXISTS_BY_ID,
)
from ..utils.error_handling import handle_webhook_endpoint_error


logger = logging.getLogger(__name__)


class WebhookEndpointDatabaseRepository:
    """Database repository for webhook endpoint operations.
    
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
        self._table = f"{schema}.webhook_endpoints"
    
    async def save(self, endpoint: WebhookEndpoint) -> WebhookEndpoint:
        """Save a webhook endpoint to the database."""
        try:
            # Check if endpoint already exists
            existing = await self.get_by_id(endpoint.id)
            if existing:
                raise EntityAlreadyExistsError("WebhookEndpoint", str(endpoint.id.value))
            
            query = WEBHOOK_ENDPOINT_INSERT.format(schema=self._schema)
            
            row = await self._db.fetchrow(
                query,
                endpoint.id.value,
                endpoint.name,
                endpoint.description,
                endpoint.endpoint_url,
                endpoint.http_method,
                endpoint.secret_token,
                endpoint.signature_header,
                json.dumps(endpoint.custom_headers),
                endpoint.timeout_seconds,
                endpoint.follow_redirects,
                endpoint.verify_ssl,
                endpoint.max_retry_attempts,
                endpoint.retry_backoff_seconds,
                float(endpoint.retry_backoff_multiplier),
                endpoint.is_active,
                endpoint.is_verified,
                endpoint.created_by_user_id.value,
                endpoint.context_id,
                endpoint.created_at,
                endpoint.updated_at,
            )
            
            if row:
                return self._row_to_endpoint(row)
            
            return endpoint
            
        except Exception as e:
            handle_webhook_endpoint_error("save", endpoint.id, e, {"schema": self._schema})
            raise
    
    async def get_by_id(self, endpoint_id: WebhookEndpointId) -> Optional[WebhookEndpoint]:
        """Get a webhook endpoint by ID."""
        try:
            query = WEBHOOK_ENDPOINT_GET_BY_ID.format(schema=self._schema)
            row = await self._db.fetchrow(query, endpoint_id.value)
            return self._row_to_endpoint(row) if row else None
            
        except Exception as e:
            handle_webhook_endpoint_error("get_by_id", endpoint_id, e, {"schema": self._schema})
            raise
    
    async def get_by_context(self, context_id: UUID, active_only: bool = True) -> List[WebhookEndpoint]:
        """Get webhook endpoints by context ID."""
        try:
            query = WEBHOOK_ENDPOINT_GET_BY_CONTEXT.format(schema=self._schema)
            rows = await self._db.fetch(query, context_id, active_only)
            return [self._row_to_endpoint(row) for row in rows]
            
        except Exception as e:
            handle_webhook_endpoint_error(
                "get_by_context", 
                None, 
                e, 
                {"schema": self._schema, "context_id": str(context_id), "active_only": active_only}
            )
            raise
    
    async def get_active_endpoints(self) -> List[WebhookEndpoint]:
        """Get all active webhook endpoints."""
        try:
            query = WEBHOOK_ENDPOINT_LIST_ACTIVE.format(schema=self._schema)
            rows = await self._db.fetch(query)
            return [self._row_to_endpoint(row) for row in rows]
            
        except Exception as e:
            handle_webhook_endpoint_error("get_active_endpoints", None, e, {"schema": self._schema})
            raise
    
    async def update(self, endpoint: WebhookEndpoint) -> WebhookEndpoint:
        """Update webhook endpoint."""
        try:
            query = WEBHOOK_ENDPOINT_UPDATE.format(schema=self._schema)
            
            row = await self._db.fetchrow(
                query,
                endpoint.id.value,
                endpoint.name,
                endpoint.description,
                endpoint.endpoint_url,
                endpoint.http_method,
                endpoint.secret_token,
                endpoint.signature_header,
                json.dumps(endpoint.custom_headers),
                endpoint.timeout_seconds,
                endpoint.follow_redirects,
                endpoint.verify_ssl,
                endpoint.max_retry_attempts,
                endpoint.retry_backoff_seconds,
                float(endpoint.retry_backoff_multiplier),
                endpoint.is_active,
                endpoint.is_verified,
                endpoint.context_id,
                endpoint.last_used_at,
                endpoint.verified_at,
                endpoint.updated_at,
            )
            
            if row:
                return self._row_to_endpoint(row)
            
            raise EntityNotFoundError("WebhookEndpoint", str(endpoint.id.value))
            
        except Exception as e:
            handle_webhook_endpoint_error("update", endpoint.id, e, {"schema": self._schema})
            raise
    
    async def delete(self, endpoint_id: WebhookEndpointId) -> bool:
        """Delete a webhook endpoint."""
        try:
            query = WEBHOOK_ENDPOINT_DELETE.format(schema=self._schema)
            result = await self._db.execute(query, endpoint_id.value)
            return result == "DELETE 1"
            
        except Exception as e:
            handle_webhook_endpoint_error("delete", endpoint_id, e, {"schema": self._schema})
            raise
    
    async def update_last_used(self, endpoint_id: WebhookEndpointId) -> bool:
        """Update the last used timestamp for an endpoint."""
        try:
            query = WEBHOOK_ENDPOINT_UPDATE_LAST_USED.format(schema=self._schema)
            result = await self._db.execute(query, endpoint_id.value)
            return result == "UPDATE 1"
            
        except Exception as e:
            handle_webhook_endpoint_error("update_last_used", endpoint_id, e, {"schema": self._schema})
            raise
    
    async def exists(self, endpoint_id: WebhookEndpointId) -> bool:
        """Check if webhook endpoint exists."""
        try:
            query = WEBHOOK_ENDPOINT_EXISTS_BY_ID.format(schema=self._schema)
            result = await self._db.fetchval(query, endpoint_id.value)
            return bool(result)
            
        except Exception as e:
            handle_webhook_endpoint_error("exists", endpoint_id, e, {"schema": self._schema})
            raise
    
    def _row_to_endpoint(self, row) -> WebhookEndpoint:
        """Convert database row to WebhookEndpoint entity."""
        # Parse JSON fields
        custom_headers = json.loads(row["custom_headers"]) if row["custom_headers"] else {}
        
        return WebhookEndpoint(
            id=WebhookEndpointId(row["id"]),
            name=row["name"],
            description=row["description"],
            endpoint_url=row["endpoint_url"],
            http_method=row["http_method"],
            secret_token=row["secret_token"],
            signature_header=row["signature_header"],
            custom_headers=custom_headers,
            timeout_seconds=row["timeout_seconds"],
            follow_redirects=row["follow_redirects"],
            verify_ssl=row["verify_ssl"],
            max_retry_attempts=row["max_retry_attempts"],
            retry_backoff_seconds=row["retry_backoff_seconds"],
            retry_backoff_multiplier=Decimal(str(row["retry_backoff_multiplier"])),
            is_active=row["is_active"],
            is_verified=row["is_verified"],
            created_by_user_id=UserId(row["created_by_user_id"]),
            context_id=row["context_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_used_at=row["last_used_at"],
            verified_at=row["verified_at"],
        )