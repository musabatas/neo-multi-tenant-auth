"""Get webhook logs query for platform events infrastructure.

This module handles ONLY webhook log retrieval operations following maximum separation architecture.
Single responsibility: Query and retrieve webhook delivery logs from neo_commons.platform system.

Pure application layer - no infrastructure concerns.
Uses protocols for dependency injection and clean architecture compliance.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum

from ....actions.core.protocols import ActionRepository  # For webhook delivery logs (webhooks are actions)
from ...core.entities import WebhookDelivery
from ...core.value_objects import WebhookDeliveryId, WebhookEndpointId, EventId, DeliveryStatus
from ...core.exceptions import EventDispatchFailed
from .....core.value_objects import UserId
from .....utils import utc_now


class LogLevel(Enum):
    """Log level filtering options."""
    ALL = "all"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    RETRY = "retry"


@dataclass
class GetWebhookLogsData:
    """Data required to query webhook logs.
    
    Contains all the filtering and pagination options for webhook log retrieval.
    Separates query parameters from business logic following CQRS patterns.
    """
    # Filtering criteria
    webhook_endpoint_id: Optional[WebhookEndpointId] = None
    event_id: Optional[EventId] = None
    event_types: Optional[List[str]] = None
    delivery_status: Optional[DeliveryStatus] = None
    log_level: LogLevel = LogLevel.ALL
    
    # Time range filtering
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    last_hours: Optional[int] = None         # Get logs from last N hours
    last_days: Optional[int] = None          # Get logs from last N days
    
    # Response filtering
    http_status_codes: Optional[List[int]] = None
    response_time_min_ms: Optional[int] = None
    response_time_max_ms: Optional[int] = None
    
    # Context filtering
    tenant_id: Optional[str] = None
    user_id: Optional[UserId] = None
    
    # Pagination and sorting
    limit: int = 100
    offset: int = 0
    sort_by: str = "attempted_at"
    sort_order: str = "desc"  # desc or asc
    
    # Additional options
    include_headers: bool = False             # Include request/response headers
    include_payload: bool = False             # Include request payload
    include_response_body: bool = False       # Include response body
    include_retry_history: bool = True        # Include retry attempts
    
    def __post_init__(self):
        """Validate query parameters after initialization."""
        # Set time range based on last_hours or last_days
        if self.last_hours:
            self.start_date = utc_now() - timedelta(hours=self.last_hours)
            self.end_date = utc_now()
        elif self.last_days:
            self.start_date = utc_now() - timedelta(days=self.last_days)
            self.end_date = utc_now()
        
        # Validate time range
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        
        # Validate pagination
        if self.limit < 1 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        
        if self.offset < 0:
            raise ValueError("offset must be non-negative")
        
        # Validate sort options
        if self.sort_by not in ["attempted_at", "completed_at", "response_time_ms", "http_status"]:
            raise ValueError("Invalid sort_by field")
        
        if self.sort_order not in ["asc", "desc"]:
            raise ValueError("sort_order must be 'asc' or 'desc'")


@dataclass
class WebhookLogEntry:
    """Single webhook log entry for response."""
    delivery_id: WebhookDeliveryId
    webhook_endpoint_id: WebhookEndpointId
    event_id: EventId
    event_type: str
    
    # Delivery details
    delivery_status: DeliveryStatus
    http_status: Optional[int]
    response_time_ms: Optional[int]
    
    # Timestamps
    attempted_at: datetime
    completed_at: Optional[datetime]
    
    # Request details
    request_url: str
    request_method: str
    request_headers: Optional[Dict[str, Any]] = None
    request_payload: Optional[Dict[str, Any]] = None
    
    # Response details
    response_headers: Optional[Dict[str, Any]] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    
    # Retry information
    attempt_number: int = 1
    max_attempts: int = 3
    next_retry_at: Optional[datetime] = None
    
    # Context
    tenant_id: Optional[str] = None
    correlation_id: Optional[str] = None


@dataclass
class GetWebhookLogsResult:
    """Result of webhook logs query.
    
    Contains the retrieved webhook logs and query metadata.
    Provides comprehensive information about webhook delivery history.
    """
    logs: List[WebhookLogEntry]
    total_count: int
    has_more: bool
    next_offset: Optional[int]
    
    # Query metadata
    query_duration_ms: float
    filters_applied: Dict[str, Any]
    
    # Summary statistics
    success_count: int
    error_count: int
    retry_count: int
    avg_response_time_ms: Optional[float]
    
    success: bool = True
    message: str = "Webhook logs retrieved successfully"


class GetWebhookLogsQuery:
    """Query to retrieve webhook logs.
    
    Handles webhook log retrieval with advanced filtering, pagination,
    and performance optimization for monitoring and debugging.
    
    Single responsibility: ONLY webhook log retrieval logic.
    Uses dependency injection through protocols for clean architecture.
    """
    
    def __init__(self, repository: ActionRepository):
        """Initialize query with required dependencies.
        
        Args:
            repository: Action repository for webhook delivery log access
        """
        self._repository = repository
    
    async def execute(self, data: GetWebhookLogsData) -> GetWebhookLogsResult:
        """Execute webhook logs query.
        
        Retrieves webhook delivery logs based on filtering criteria,
        applies pagination, and returns formatted results with statistics.
        
        Args:
            data: Query parameters for webhook log retrieval
            
        Returns:
            GetWebhookLogsResult with logs and metadata
            
        Raises:
            EventDispatchFailed: If query operation fails
            ValueError: If query parameters are invalid
        """
        start_time = utc_now()
        
        try:
            # Build repository filters
            filters = self._build_repository_filters(data)
            
            # Execute query with pagination
            logs_result = await self._query_webhook_logs(data, filters)
            
            # Convert to response format
            log_entries = self._convert_to_log_entries(logs_result, data)
            
            # Calculate statistics
            stats = self._calculate_statistics(log_entries)
            
            # Calculate query duration
            duration_ms = (utc_now() - start_time).total_seconds() * 1000
            
            # Determine pagination info
            has_more = len(log_entries) == data.limit
            next_offset = data.offset + len(log_entries) if has_more else None
            
            # Create result
            result = GetWebhookLogsResult(
                logs=log_entries,
                total_count=stats["total_count"],
                has_more=has_more,
                next_offset=next_offset,
                query_duration_ms=duration_ms,
                filters_applied=self._get_applied_filters(data),
                success_count=stats["success_count"],
                error_count=stats["error_count"],
                retry_count=stats["retry_count"],
                avg_response_time_ms=stats["avg_response_time_ms"],
                success=True,
                message=f"Retrieved {len(log_entries)} webhook log entries"
            )
            
            return result
            
        except ValueError as e:
            raise EventDispatchFailed(f"Invalid webhook logs query: {str(e)}")
        except Exception as e:
            raise EventDispatchFailed(f"Failed to retrieve webhook logs: {str(e)}")
    
    def _build_repository_filters(self, data: GetWebhookLogsData) -> Dict[str, Any]:
        """Build repository-specific filters from query data.
        
        Args:
            data: Query parameters
            
        Returns:
            Dictionary of repository filters
        """
        filters = {}
        
        # ID-based filtering
        if data.webhook_endpoint_id:
            filters["webhook_endpoint_id"] = str(data.webhook_endpoint_id)
        
        if data.event_id:
            filters["event_id"] = str(data.event_id)
        
        if data.event_types:
            filters["event_types"] = data.event_types
        
        # Status filtering
        if data.delivery_status:
            filters["delivery_status"] = data.delivery_status.value
        
        # Time range filtering
        if data.start_date:
            filters["attempted_after"] = data.start_date
        
        if data.end_date:
            filters["attempted_before"] = data.end_date
        
        # Response filtering
        if data.http_status_codes:
            filters["http_status_codes"] = data.http_status_codes
        
        if data.response_time_min_ms:
            filters["response_time_min_ms"] = data.response_time_min_ms
        
        if data.response_time_max_ms:
            filters["response_time_max_ms"] = data.response_time_max_ms
        
        # Context filtering
        if data.tenant_id:
            filters["tenant_id"] = data.tenant_id
        
        if data.user_id:
            filters["user_id"] = str(data.user_id)
        
        # Log level filtering
        if data.log_level != LogLevel.ALL:
            filters["log_level"] = data.log_level.value
        
        return filters
    
    async def _query_webhook_logs(self, data: GetWebhookLogsData, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Query webhook delivery logs from repository.
        
        Args:
            data: Query parameters
            filters: Repository filters
            
        Returns:
            Repository query result
        """
        # Note: In a complete implementation, this would use a specialized
        # WebhookDeliveryRepository. For now, using ActionRepository as placeholder.
        
        # Use the repository's search method (assuming it supports webhook delivery queries)
        result = await self._repository.search_webhook_deliveries(
            filters=filters,
            sort_by=data.sort_by,
            sort_order=data.sort_order,
            limit=data.limit,
            offset=data.offset
        )
        
        return result
    
    def _convert_to_log_entries(self, logs_result: Dict[str, Any], data: GetWebhookLogsData) -> List[WebhookLogEntry]:
        """Convert repository results to WebhookLogEntry objects.
        
        Args:
            logs_result: Raw repository result
            data: Query parameters for inclusion options
            
        Returns:
            List of formatted webhook log entries
        """
        deliveries = logs_result.get("deliveries", [])
        log_entries = []
        
        for delivery in deliveries:
            # Create log entry with conditional field inclusion
            log_entry = WebhookLogEntry(
                delivery_id=delivery.id,
                webhook_endpoint_id=delivery.webhook_endpoint_id,
                event_id=delivery.event_id,
                event_type=delivery.event_type or "unknown",
                delivery_status=delivery.delivery_status,
                http_status=delivery.http_status_code,
                response_time_ms=delivery.response_time_ms,
                attempted_at=delivery.attempted_at,
                completed_at=delivery.completed_at,
                request_url=delivery.endpoint_url,
                request_method=delivery.http_method or "POST",
                attempt_number=delivery.attempt_number or 1,
                max_attempts=delivery.max_attempts or 3,
                next_retry_at=delivery.next_retry_at,
                tenant_id=getattr(delivery, "tenant_id", None),
                correlation_id=str(delivery.id),  # Use delivery ID as correlation
                error_message=delivery.error_message
            )
            
            # Include optional fields based on query parameters
            if data.include_headers:
                log_entry.request_headers = getattr(delivery, "request_headers", {})
                log_entry.response_headers = getattr(delivery, "response_headers", {})
            
            if data.include_payload:
                log_entry.request_payload = getattr(delivery, "request_payload", {})
            
            if data.include_response_body:
                log_entry.response_body = getattr(delivery, "response_body", None)
            
            log_entries.append(log_entry)
        
        return log_entries
    
    def _calculate_statistics(self, log_entries: List[WebhookLogEntry]) -> Dict[str, Any]:
        """Calculate summary statistics for the log entries.
        
        Args:
            log_entries: List of webhook log entries
            
        Returns:
            Dictionary of statistics
        """
        if not log_entries:
            return {
                "total_count": 0,
                "success_count": 0,
                "error_count": 0,
                "retry_count": 0,
                "avg_response_time_ms": None
            }
        
        success_count = sum(1 for entry in log_entries if entry.delivery_status == DeliveryStatus.SUCCESS)
        error_count = sum(1 for entry in log_entries 
                         if entry.delivery_status in [DeliveryStatus.FAILED, DeliveryStatus.TIMEOUT])
        retry_count = sum(1 for entry in log_entries if entry.delivery_status == DeliveryStatus.RETRYING)
        
        # Calculate average response time (excluding None values)
        response_times = [entry.response_time_ms for entry in log_entries 
                         if entry.response_time_ms is not None]
        avg_response_time_ms = sum(response_times) / len(response_times) if response_times else None
        
        return {
            "total_count": len(log_entries),
            "success_count": success_count,
            "error_count": error_count,
            "retry_count": retry_count,
            "avg_response_time_ms": avg_response_time_ms
        }
    
    def _get_applied_filters(self, data: GetWebhookLogsData) -> Dict[str, Any]:
        """Get summary of applied filters for result metadata.
        
        Args:
            data: Query parameters
            
        Returns:
            Dictionary of applied filters
        """
        applied = {}
        
        if data.webhook_endpoint_id:
            applied["webhook_endpoint_id"] = str(data.webhook_endpoint_id)
        
        if data.event_id:
            applied["event_id"] = str(data.event_id)
        
        if data.event_types:
            applied["event_types"] = data.event_types
        
        if data.delivery_status:
            applied["delivery_status"] = data.delivery_status.value
        
        if data.log_level != LogLevel.ALL:
            applied["log_level"] = data.log_level.value
        
        if data.start_date:
            applied["start_date"] = data.start_date.isoformat()
        
        if data.end_date:
            applied["end_date"] = data.end_date.isoformat()
        
        if data.tenant_id:
            applied["tenant_id"] = data.tenant_id
        
        applied["limit"] = data.limit
        applied["offset"] = data.offset
        applied["sort_by"] = data.sort_by
        applied["sort_order"] = data.sort_order
        
        return applied


def create_get_webhook_logs_query(repository: ActionRepository) -> GetWebhookLogsQuery:
    """Factory function to create GetWebhookLogsQuery instance.
    
    Args:
        repository: Action repository for webhook delivery log access
        
    Returns:
        Configured GetWebhookLogsQuery instance
    """
    return GetWebhookLogsQuery(repository=repository)