"""Webhook delivery repository implementation using existing database infrastructure.

This implementation follows the patterns established in the organizations feature,
leveraging existing database service without duplicating connection management.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta

from ....core.value_objects import WebhookDeliveryId, WebhookEndpointId, EventId
from ....core.exceptions import EntityNotFoundError, EntityAlreadyExistsError, DatabaseError
from ....features.database.entities.protocols import DatabaseRepository
from ..entities.webhook_delivery import WebhookDelivery, DeliveryStatus
from ..entities.protocols import WebhookDeliveryRepository
from ..utils.queries import (
    WEBHOOK_DELIVERY_INSERT,
    WEBHOOK_DELIVERY_UPDATE,
    WEBHOOK_DELIVERY_GET_BY_ID,
    WEBHOOK_DELIVERY_GET_PENDING_RETRIES,
    WEBHOOK_DELIVERY_GET_BY_ENDPOINT,
    WEBHOOK_DELIVERY_GET_BY_EVENT,
    WEBHOOK_DELIVERY_GET_STATS,  # Fixed: was WEBHOOK_DELIVERY_GET_DELIVERY_STATS
)
from ..utils.error_handling import handle_delivery_error


logger = logging.getLogger(__name__)


class WebhookDeliveryDatabaseRepository:
    """Database repository for webhook delivery operations.
    
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
        self._table = f"{schema}.webhook_deliveries"
    
    async def save(self, delivery: WebhookDelivery) -> WebhookDelivery:
        """Save a webhook delivery to the database by storing each attempt as a separate row."""
        try:
            # Check if delivery already exists by ID (check if any attempts exist)
            existing = await self.get_by_id(delivery.id)
            if existing:
                raise EntityAlreadyExistsError("WebhookDelivery", str(delivery.id.value))
            
            query = WEBHOOK_DELIVERY_INSERT.format(schema=self._schema)
            
            # Store each attempt as a separate row
            saved_attempts = []
            for attempt in delivery.attempts:
                row = await self._db.fetchrow(
                    query,
                    delivery.id.value,  # $1 - id (use delivery ID as base, attempts will have same delivery ID)
                    delivery.webhook_endpoint_id.value,  # $2 - webhook_endpoint_id  
                    delivery.webhook_event_id.value,  # $3 - webhook_event_id
                    attempt.attempt_number,  # $4 - attempt_number
                    attempt.delivery_status.value,  # $5 - delivery_status
                    attempt.request_url,  # $6 - request_url
                    attempt.request_method,  # $7 - request_method
                    json.dumps(attempt.request_headers),  # $8 - request_headers
                    attempt.request_body,  # $9 - request_body
                    attempt.request_signature,  # $10 - request_signature
                    attempt.response_status_code,  # $11 - response_status_code
                    json.dumps(attempt.response_headers) if attempt.response_headers else None,  # $12 - response_headers
                    attempt.response_body,  # $13 - response_body
                    attempt.response_time_ms,  # $14 - response_time_ms
                    attempt.error_message,  # $15 - error_message
                    attempt.error_code,  # $16 - error_code
                    delivery.next_retry_at,  # $17 - next_retry_at (from delivery level)
                    delivery.max_attempts_reached,  # $18 - max_attempts_reached
                    attempt.attempted_at,  # $19 - attempted_at
                    attempt.completed_at,  # $20 - completed_at
                    delivery.created_at,  # $21 - created_at (from delivery level)
                )
                
                if row:
                    saved_attempts.append(self._row_to_attempt(row))
            
            # If no attempts, create a placeholder pending attempt  
            if not delivery.attempts:
                # Create a default pending attempt for new deliveries
                from ..entities.webhook_delivery import WebhookDeliveryAttempt, DeliveryStatus
                from datetime import datetime, timezone
                
                default_attempt = WebhookDeliveryAttempt(
                    attempt_number=1,
                    delivery_status=DeliveryStatus.PENDING,
                    request_url="",  # Will be filled by delivery service
                    request_method="POST",
                    attempted_at=datetime.now(timezone.utc)
                )
                
                row = await self._db.fetchrow(
                    query,
                    delivery.id.value,
                    delivery.webhook_endpoint_id.value,
                    delivery.webhook_event_id.value,
                    default_attempt.attempt_number,
                    default_attempt.delivery_status.value,
                    default_attempt.request_url,
                    default_attempt.request_method,
                    json.dumps(default_attempt.request_headers),
                    default_attempt.request_body,
                    default_attempt.request_signature,
                    default_attempt.response_status_code,
                    json.dumps(default_attempt.response_headers) if default_attempt.response_headers else None,
                    default_attempt.response_body,
                    default_attempt.response_time_ms,
                    default_attempt.error_message,
                    default_attempt.error_code,
                    delivery.next_retry_at,
                    delivery.max_attempts_reached,
                    default_attempt.attempted_at,
                    default_attempt.completed_at,
                    delivery.created_at,
                )
                
                if row:
                    saved_attempts.append(self._row_to_attempt(row))
            
            # Return delivery with updated attempts
            delivery.attempts = saved_attempts
            return delivery
            
        except Exception as e:
            handle_delivery_error("save", delivery.id, e, {"schema": self._schema})
            raise
    
    async def get_by_id(self, delivery_id: WebhookDeliveryId) -> Optional[WebhookDelivery]:
        """Get a webhook delivery by ID by loading all attempts and building the aggregate."""
        try:
            # Get all attempts for this delivery ID
            query = f"""
                SELECT * FROM {self._schema}.webhook_deliveries 
                WHERE id = $1 
                ORDER BY attempt_number ASC
            """
            rows = await self._db.fetch(query, delivery_id.value)
            
            if not rows:
                return None
            
            # Build aggregate from all attempts
            first_row = rows[0]
            attempts = [self._row_to_attempt(row) for row in rows]
            
            # Determine overall status from latest attempt
            latest_attempt = attempts[-1] if attempts else None
            overall_status = latest_attempt.delivery_status if latest_attempt else DeliveryStatus.PENDING
            
            # Calculate current attempt number
            current_attempt = max(attempt.attempt_number for attempt in attempts) if attempts else 1
            
            # Determine if max attempts reached (check if any attempt has max_attempts_reached=true)
            max_attempts_reached = any(row["max_attempts_reached"] for row in rows)
            
            return WebhookDelivery(
                id=WebhookDeliveryId(first_row["id"]),
                webhook_endpoint_id=WebhookEndpointId(first_row["webhook_endpoint_id"]),
                webhook_event_id=EventId(first_row["webhook_event_id"]),
                current_attempt=current_attempt,
                overall_status=overall_status,
                max_attempts=3,  # Default - should be loaded from endpoint config in real implementation
                next_retry_at=first_row["next_retry_at"],  # Use from latest attempt
                max_attempts_reached=max_attempts_reached,
                attempts=attempts,
                created_at=first_row["created_at"],
            )
            
        except Exception as e:
            handle_delivery_error("get_by_id", delivery_id, e, {"schema": self._schema})
            raise
    
    async def get_pending_retries(self, limit: int = 100) -> List[WebhookDelivery]:
        """Get webhook deliveries that are ready for retry."""
        try:
            query = WEBHOOK_DELIVERY_GET_PENDING_RETRIES.format(schema=self._schema)
            # Fixed: Query uses NOW() inline, only pass limit parameter
            rows = await self._db.fetch(query, limit)
            return [self._row_to_delivery(row) for row in rows]
            
        except Exception as e:
            handle_delivery_error(
                "get_pending_retries", 
                None, 
                e, 
                {"schema": self._schema, "limit": limit}
            )
            raise
    
    async def get_by_endpoint(self, endpoint_id: WebhookEndpointId, limit: int = 100) -> List[WebhookDelivery]:
        """Get webhook deliveries for a specific endpoint."""
        try:
            query = WEBHOOK_DELIVERY_GET_BY_ENDPOINT.format(schema=self._schema)
            rows = await self._db.fetch(query, endpoint_id.value, limit)
            return [self._row_to_delivery(row) for row in rows]
            
        except Exception as e:
            handle_delivery_error(
                "get_by_endpoint", 
                None, 
                e, 
                {"schema": self._schema, "endpoint_id": str(endpoint_id.value), "limit": limit}
            )
            raise
    
    async def get_by_event(self, event_id: EventId) -> List[WebhookDelivery]:
        """Get webhook deliveries for a specific event."""
        try:
            query = WEBHOOK_DELIVERY_GET_BY_EVENT.format(schema=self._schema)
            rows = await self._db.fetch(query, event_id.value)
            return [self._row_to_delivery(row) for row in rows]
            
        except Exception as e:
            handle_delivery_error(
                "get_by_event", 
                None, 
                e, 
                {"schema": self._schema, "event_id": str(event_id.value)}
            )
            raise
    
    async def update(self, delivery: WebhookDelivery) -> WebhookDelivery:
        """Update webhook delivery."""
        try:
            query = WEBHOOK_DELIVERY_UPDATE.format(schema=self._schema)
            
            row = await self._db.fetchrow(
                query,
                delivery.id.value,
                delivery.status.value,
                delivery.attempt_count,
                delivery.next_retry_at,
                json.dumps(delivery.last_error) if delivery.last_error else None,
                delivery.delivered_at,
                delivery.updated_at,
            )
            
            if row:
                return self._row_to_delivery(row)
            
            raise EntityNotFoundError("WebhookDelivery", str(delivery.id.value))
            
        except Exception as e:
            handle_delivery_error("update", delivery.id, e, {"schema": self._schema})
            raise
    
    async def get_delivery_stats(self, endpoint_id: WebhookEndpointId, 
                                days: int = 7) -> Dict[str, Any]:
        """Get delivery statistics for an endpoint."""
        try:
            query = WEBHOOK_DELIVERY_GET_STATS.format(schema=self._schema)
            
            # Calculate date range
            end_date = datetime.now(timezone.utc)
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            start_date = start_date - timedelta(days=days - 1)
            
            rows = await self._db.fetch(query, endpoint_id.value, start_date, end_date)
            
            # Process results into statistics
            stats = {
                "total_deliveries": 0,
                "successful_deliveries": 0,
                "failed_deliveries": 0,
                "pending_deliveries": 0,
                "success_rate": 0.0,
                "average_attempts": 0.0,
                "daily_breakdown": []
            }
            
            total_attempts = 0
            for row in rows:
                stats["total_deliveries"] += row["delivery_count"]
                
                if row["status"] == DeliveryStatus.SUCCESS.value:
                    stats["successful_deliveries"] += row["delivery_count"]
                elif row["status"] == DeliveryStatus.FAILED.value:
                    stats["failed_deliveries"] += row["delivery_count"]
                elif row["status"] in [DeliveryStatus.PENDING.value, DeliveryStatus.RETRYING.value]:
                    stats["pending_deliveries"] += row["delivery_count"]
                
                total_attempts += row["total_attempts"] or 0
                
                stats["daily_breakdown"].append({
                    "date": row["delivery_date"].strftime("%Y-%m-%d") if row["delivery_date"] else None,
                    "status": row["status"],
                    "count": row["delivery_count"],
                    "avg_attempts": row["avg_attempts"] or 0
                })
            
            # Calculate success rate
            if stats["total_deliveries"] > 0:
                stats["success_rate"] = stats["successful_deliveries"] / stats["total_deliveries"]
                stats["average_attempts"] = total_attempts / stats["total_deliveries"]
            
            return stats
            
        except Exception as e:
            handle_delivery_error(
                "get_delivery_stats", 
                None, 
                e, 
                {"schema": self._schema, "endpoint_id": str(endpoint_id.value), "days": days}
            )
            raise
    
    def _row_to_delivery(self, row) -> WebhookDelivery:
        """Convert database row (single attempt) to WebhookDelivery aggregate entity."""
        # This method handles a single row - for full aggregate, use get_by_id which loads all attempts
        attempt = self._row_to_attempt(row)
        
        # Determine overall status from this attempt
        overall_status = attempt.delivery_status
        
        # Create delivery aggregate with this single attempt
        return WebhookDelivery(
            id=WebhookDeliveryId(row["id"]),
            webhook_endpoint_id=WebhookEndpointId(row["webhook_endpoint_id"]),
            webhook_event_id=EventId(row["webhook_event_id"]),
            current_attempt=row["attempt_number"],
            overall_status=overall_status,
            max_attempts=3,  # Default - should be loaded from endpoint config
            next_retry_at=row["next_retry_at"],
            max_attempts_reached=row["max_attempts_reached"],
            attempts=[attempt],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
    
    def _row_to_attempt(self, row) -> 'WebhookDeliveryAttempt':
        """Convert database row to WebhookDeliveryAttempt entity."""
        from ..entities.webhook_delivery import WebhookDeliveryAttempt, DeliveryStatus
        
        # Parse JSON fields
        request_headers = {}
        if row["request_headers"]:
            request_headers = json.loads(row["request_headers"])
        
        response_headers = None
        if row["response_headers"]:
            response_headers = json.loads(row["response_headers"])
        
        return WebhookDeliveryAttempt(
            attempt_number=row["attempt_number"],
            delivery_status=DeliveryStatus(row["delivery_status"]),
            request_url=row["request_url"],
            request_method=row["request_method"],
            request_headers=request_headers,
            request_body=row["request_body"],
            request_signature=row["request_signature"],
            response_status_code=row["response_status_code"],
            response_headers=response_headers,
            response_body=row["response_body"],
            response_time_ms=row["response_time_ms"],
            error_message=row["error_message"],
            error_code=row["error_code"],
            attempted_at=row["attempted_at"],
            completed_at=row["completed_at"],
        )