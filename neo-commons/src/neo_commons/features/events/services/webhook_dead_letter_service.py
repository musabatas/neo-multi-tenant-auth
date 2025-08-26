"""Dead Letter Queue service for permanently failed webhook deliveries.

Handles webhook deliveries that have exhausted all retry attempts or encountered
permanent failures. Provides archival, analysis, and recovery mechanisms for
failed deliveries to prevent data loss and enable forensic analysis.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID

from ....core.value_objects import WebhookDeliveryId, WebhookEndpointId, EventId
from ....features.database.entities.protocols import DatabaseRepository
from ..entities.webhook_delivery import WebhookDelivery, DeliveryStatus
from ..entities.domain_event import DomainEvent
from ..entities.protocols import WebhookDeliveryRepository, EventRepository
from ..utils.error_handling import handle_delivery_error
from .webhook_config_service import get_webhook_config


logger = logging.getLogger(__name__)


class DeadLetterReason(Enum):
    """Reasons for delivery being sent to dead letter queue."""
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"
    CIRCUIT_BREAKER_PERMANENT = "circuit_breaker_permanent"  
    ENDPOINT_DISABLED = "endpoint_disabled"
    ENDPOINT_DELETED = "endpoint_deleted"
    PERMANENT_ERROR = "permanent_error"  # 400-level HTTP errors
    SECURITY_VIOLATION = "security_violation"
    CONFIGURATION_ERROR = "configuration_error"
    MANUAL_INTERVENTION = "manual_intervention"


class DeadLetterAction(Enum):
    """Actions that can be taken on dead letter deliveries."""
    ARCHIVE = "archive"
    DELETE = "delete"
    RETRY_MANUAL = "retry_manual"
    REDIRECT = "redirect"  # Redirect to different endpoint
    TRANSFORM = "transform"  # Transform payload and retry


@dataclass
class DeadLetterEntry:
    """Entry in the dead letter queue with comprehensive context."""
    
    # Core identifiers
    delivery_id: WebhookDeliveryId
    event_id: EventId
    endpoint_id: WebhookEndpointId
    
    # Dead letter context
    reason: DeadLetterReason
    original_delivery: Optional[WebhookDelivery] = None
    original_event: Optional[DomainEvent] = None
    
    # Failure analysis
    failure_summary: str = ""
    error_details: Dict[str, Any] = field(default_factory=dict)
    retry_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    
    # Processing status
    is_processed: bool = False
    action_taken: Optional[DeadLetterAction] = None
    action_result: Optional[str] = None
    
    # Recovery attempts
    recovery_attempts: int = 0
    last_recovery_attempt: Optional[datetime] = None
    
    def mark_processed(self, action: DeadLetterAction, result: str) -> None:
        """Mark the dead letter entry as processed."""
        self.is_processed = True
        self.action_taken = action
        self.action_result = result
        self.processed_at = datetime.now(timezone.utc)
    
    def add_recovery_attempt(self, result: str) -> None:
        """Record a recovery attempt."""
        self.recovery_attempts += 1
        self.last_recovery_attempt = datetime.now(timezone.utc)
        self.error_details["recovery_attempts"] = self.error_details.get("recovery_attempts", [])
        self.error_details["recovery_attempts"].append({
            "attempt": self.recovery_attempts,
            "timestamp": self.last_recovery_attempt.isoformat(),
            "result": result
        })


@dataclass
class DeadLetterStats:
    """Statistics for dead letter queue operations."""
    
    total_entries: int = 0
    entries_by_reason: Dict[DeadLetterReason, int] = field(default_factory=dict)
    entries_by_endpoint: Dict[str, int] = field(default_factory=dict)
    
    # Processing statistics
    processed_entries: int = 0
    pending_entries: int = 0
    expired_entries: int = 0
    
    # Action statistics
    archived_entries: int = 0
    deleted_entries: int = 0
    recovered_entries: int = 0
    redirected_entries: int = 0
    
    # Time-based metrics
    avg_time_to_dlq_hours: Optional[float] = None
    oldest_unprocessed_entry: Optional[datetime] = None
    dlq_growth_rate_per_hour: float = 0.0
    
    def get_recovery_rate(self) -> float:
        """Calculate recovery rate percentage."""
        if self.total_entries == 0:
            return 0.0
        return (self.recovered_entries / self.total_entries) * 100


class WebhookDeadLetterService:
    """Service for managing webhook delivery dead letter queue."""
    
    def __init__(
        self,
        delivery_repository: WebhookDeliveryRepository,
        event_repository: EventRepository,
        database_repository: DatabaseRepository,
        schema: str
    ):
        """Initialize dead letter service.
        
        Args:
            delivery_repository: Webhook delivery repository
            event_repository: Domain event repository
            database_repository: Database repository for raw queries
            schema: Database schema name
        """
        self._delivery_repo = delivery_repository
        self._event_repo = event_repository
        self._db = database_repository
        self._schema = schema
        
        # Get configuration
        self._config = get_webhook_config()
        
        # Dead letter queue settings
        self._default_retention_days = 30
        self._max_recovery_attempts = 3
        self._batch_processing_size = 100
        
        # In-memory dead letter queue for immediate processing
        self._dlq_queue: List[DeadLetterEntry] = []
        self._processing_lock = asyncio.Lock()
        
    async def add_to_dead_letter_queue(
        self,
        delivery: WebhookDelivery,
        reason: DeadLetterReason,
        error_details: Optional[Dict[str, Any]] = None
    ) -> DeadLetterEntry:
        """Add a failed delivery to the dead letter queue.
        
        Args:
            delivery: Failed webhook delivery
            reason: Reason for dead letter queue placement
            error_details: Additional error context
            
        Returns:
            Created dead letter entry
        """
        try:
            logger.warning(
                f"Adding delivery {delivery.id} to dead letter queue: {reason.value}",
                extra={
                    "delivery_id": str(delivery.id.value),
                    "endpoint_id": str(delivery.endpoint_id.value),
                    "reason": reason.value
                }
            )
            
            # Get original event for context
            original_event = None
            try:
                original_event = await self._event_repo.get_by_id(delivery.event_id)
            except Exception as e:
                logger.error(f"Failed to get original event {delivery.event_id}: {e}")
            
            # Create dead letter entry
            dlq_entry = DeadLetterEntry(
                delivery_id=delivery.id,
                event_id=delivery.event_id,
                endpoint_id=delivery.endpoint_id,
                reason=reason,
                original_delivery=delivery,
                original_event=original_event,
                failure_summary=self._generate_failure_summary(delivery, reason),
                error_details=error_details or {},
                retry_history=self._extract_retry_history(delivery),
                expires_at=datetime.now(timezone.utc) + timedelta(days=self._default_retention_days)
            )
            
            # Store in persistent storage
            await self._store_dead_letter_entry(dlq_entry)
            
            # Add to in-memory queue for processing
            async with self._processing_lock:
                self._dlq_queue.append(dlq_entry)
            
            # Update delivery status to indicate DLQ placement
            delivery.status = DeliveryStatus.FAILED
            delivery.failure_reason = f"Moved to dead letter queue: {reason.value}"
            delivery.updated_at = datetime.now(timezone.utc)
            await self._delivery_repo.update(delivery)
            
            logger.info(f"Successfully added delivery {delivery.id} to dead letter queue")
            return dlq_entry
            
        except Exception as e:
            logger.error(f"Failed to add delivery {delivery.id} to dead letter queue: {e}")
            handle_delivery_error("add_to_dead_letter_queue", delivery.id, e, {
                "reason": reason.value,
                "error_details": error_details
            })
            raise
    
    async def process_dead_letter_queue(self, batch_size: Optional[int] = None) -> Dict[str, Any]:
        """Process entries in the dead letter queue.
        
        Args:
            batch_size: Number of entries to process (default: configured batch size)
            
        Returns:
            Processing statistics and results
        """
        if batch_size is None:
            batch_size = self._batch_processing_size
        
        logger.info(f"Processing dead letter queue with batch size {batch_size}")
        
        try:
            processing_stats = {
                "processed_count": 0,
                "archived_count": 0,
                "deleted_count": 0,
                "recovery_attempts": 0,
                "errors": []
            }
            
            # Get unprocessed entries from persistent storage
            unprocessed_entries = await self._get_unprocessed_entries(batch_size)
            
            if not unprocessed_entries:
                logger.debug("No unprocessed dead letter entries found")
                return processing_stats
            
            logger.info(f"Processing {len(unprocessed_entries)} dead letter entries")
            
            for entry in unprocessed_entries:
                try:
                    action = await self._determine_processing_action(entry)
                    result = await self._execute_processing_action(entry, action)
                    
                    entry.mark_processed(action, result)
                    await self._update_dead_letter_entry(entry)
                    
                    processing_stats["processed_count"] += 1
                    
                    if action == DeadLetterAction.ARCHIVE:
                        processing_stats["archived_count"] += 1
                    elif action == DeadLetterAction.DELETE:
                        processing_stats["deleted_count"] += 1
                    elif action in [DeadLetterAction.RETRY_MANUAL, DeadLetterAction.REDIRECT]:
                        processing_stats["recovery_attempts"] += 1
                    
                    logger.debug(f"Processed dead letter entry {entry.delivery_id}: {action.value}")
                    
                except Exception as entry_error:
                    error_msg = f"Failed to process dead letter entry {entry.delivery_id}: {entry_error}"
                    logger.error(error_msg)
                    processing_stats["errors"].append(error_msg)
                    continue
            
            logger.info(
                f"Dead letter queue processing complete: {processing_stats['processed_count']} entries processed, "
                f"{processing_stats['archived_count']} archived, {processing_stats['deleted_count']} deleted"
            )
            
            return processing_stats
            
        except Exception as e:
            logger.error(f"Error processing dead letter queue: {e}")
            raise
    
    async def get_dead_letter_stats(self) -> DeadLetterStats:
        """Get comprehensive dead letter queue statistics.
        
        Returns:
            Complete statistics for dead letter queue operations
        """
        try:
            logger.debug("Generating dead letter queue statistics")
            
            stats = DeadLetterStats()
            
            # Get basic counts
            total_query = f"""
            SELECT 
                COUNT(*) as total_entries,
                COUNT(CASE WHEN is_processed = false THEN 1 END) as pending_entries,
                COUNT(CASE WHEN is_processed = true THEN 1 END) as processed_entries,
                COUNT(CASE WHEN expires_at < NOW() THEN 1 END) as expired_entries
            FROM {self._schema}.webhook_dead_letter_queue
            """
            
            row = await self._db.fetchrow(total_query)
            if row:
                stats.total_entries = row["total_entries"] or 0
                stats.pending_entries = row["pending_entries"] or 0
                stats.processed_entries = row["processed_entries"] or 0
                stats.expired_entries = row["expired_entries"] or 0
            
            # Get entries by reason
            reason_query = f"""
            SELECT reason, COUNT(*) as count
            FROM {self._schema}.webhook_dead_letter_queue
            GROUP BY reason
            """
            
            reason_rows = await self._db.fetchall(reason_query)
            for row in reason_rows:
                try:
                    reason = DeadLetterReason(row["reason"])
                    stats.entries_by_reason[reason] = row["count"]
                except ValueError:
                    # Handle unknown reason values
                    logger.warning(f"Unknown dead letter reason: {row['reason']}")
            
            # Get entries by endpoint
            endpoint_query = f"""
            SELECT endpoint_id, COUNT(*) as count
            FROM {self._schema}.webhook_dead_letter_queue
            GROUP BY endpoint_id
            ORDER BY count DESC
            LIMIT 20
            """
            
            endpoint_rows = await self._db.fetchall(endpoint_query)
            for row in endpoint_rows:
                stats.entries_by_endpoint[str(row["endpoint_id"])] = row["count"]
            
            # Get action statistics
            action_query = f"""
            SELECT 
                COUNT(CASE WHEN action_taken = 'archive' THEN 1 END) as archived_entries,
                COUNT(CASE WHEN action_taken = 'delete' THEN 1 END) as deleted_entries,
                COUNT(CASE WHEN action_taken IN ('retry_manual', 'redirect') THEN 1 END) as recovered_entries
            FROM {self._schema}.webhook_dead_letter_queue
            WHERE is_processed = true
            """
            
            action_row = await self._db.fetchrow(action_query)
            if action_row:
                stats.archived_entries = action_row["archived_entries"] or 0
                stats.deleted_entries = action_row["deleted_entries"] or 0
                stats.recovered_entries = action_row["recovered_entries"] or 0
            
            # Get time-based metrics
            time_metrics_query = f"""
            SELECT 
                AVG(EXTRACT(EPOCH FROM (created_at - '1970-01-01'::timestamp))/3600) as avg_time_to_dlq_hours,
                MIN(created_at) FILTER (WHERE is_processed = false) as oldest_unprocessed_entry
            FROM {self._schema}.webhook_dead_letter_queue
            """
            
            time_row = await self._db.fetchrow(time_metrics_query)
            if time_row:
                stats.avg_time_to_dlq_hours = float(time_row["avg_time_to_dlq_hours"]) if time_row["avg_time_to_dlq_hours"] else None
                stats.oldest_unprocessed_entry = time_row["oldest_unprocessed_entry"]
            
            # Calculate growth rate (entries in last hour)
            growth_query = f"""
            SELECT COUNT(*) as recent_entries
            FROM {self._schema}.webhook_dead_letter_queue
            WHERE created_at >= NOW() - INTERVAL '1 hour'
            """
            
            growth_row = await self._db.fetchrow(growth_query)
            if growth_row:
                stats.dlq_growth_rate_per_hour = float(growth_row["recent_entries"] or 0)
            
            logger.debug(f"Dead letter statistics generated: {stats.total_entries} total entries")
            return stats
            
        except Exception as e:
            logger.error(f"Error generating dead letter queue statistics: {e}")
            return DeadLetterStats()
    
    async def retry_dead_letter_entry(
        self,
        delivery_id: WebhookDeliveryId,
        new_endpoint_id: Optional[WebhookEndpointId] = None
    ) -> bool:
        """Manually retry a dead letter entry.
        
        Args:
            delivery_id: ID of the delivery to retry
            new_endpoint_id: Optional new endpoint to deliver to
            
        Returns:
            True if retry was successful
        """
        try:
            # Get dead letter entry
            entry = await self._get_dead_letter_entry(delivery_id)
            if not entry:
                logger.error(f"Dead letter entry not found for delivery {delivery_id}")
                return False
            
            if entry.recovery_attempts >= self._max_recovery_attempts:
                logger.warning(f"Max recovery attempts reached for delivery {delivery_id}")
                return False
            
            # Prepare for retry
            original_delivery = entry.original_delivery
            if not original_delivery:
                logger.error(f"Original delivery not found for dead letter entry {delivery_id}")
                return False
            
            # Update endpoint if provided
            if new_endpoint_id:
                original_delivery.endpoint_id = new_endpoint_id
                logger.info(f"Redirecting delivery {delivery_id} to new endpoint {new_endpoint_id}")
            
            # Reset delivery status for retry
            original_delivery.status = DeliveryStatus.PENDING
            original_delivery.attempt_count = 0
            original_delivery.failure_reason = None
            original_delivery.next_retry_at = datetime.now(timezone.utc)
            original_delivery.updated_at = datetime.now(timezone.utc)
            
            # Save updated delivery
            await self._delivery_repo.update(original_delivery)
            
            # Update dead letter entry
            entry.add_recovery_attempt("Manual retry initiated")
            await self._update_dead_letter_entry(entry)
            
            logger.info(f"Successfully initiated retry for dead letter delivery {delivery_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error retrying dead letter entry {delivery_id}: {e}")
            return False
    
    async def cleanup_expired_entries(self) -> int:
        """Clean up expired dead letter entries.
        
        Returns:
            Number of entries cleaned up
        """
        try:
            logger.info("Cleaning up expired dead letter entries")
            
            cleanup_query = f"""
            DELETE FROM {self._schema}.webhook_dead_letter_queue
            WHERE expires_at < NOW()
            """
            
            result = await self._db.execute(cleanup_query)
            cleanup_count = result.split()[-1] if result else 0  # Extract row count from result
            
            logger.info(f"Cleaned up {cleanup_count} expired dead letter entries")
            return int(cleanup_count) if isinstance(cleanup_count, str) and cleanup_count.isdigit() else 0
            
        except Exception as e:
            logger.error(f"Error cleaning up expired dead letter entries: {e}")
            return 0
    
    # Helper methods for dead letter operations
    
    def _generate_failure_summary(self, delivery: WebhookDelivery, reason: DeadLetterReason) -> str:
        """Generate human-readable failure summary."""
        summaries = {
            DeadLetterReason.MAX_RETRIES_EXCEEDED: f"Delivery failed after {delivery.attempt_count} attempts",
            DeadLetterReason.CIRCUIT_BREAKER_PERMANENT: "Circuit breaker permanently blocked delivery",
            DeadLetterReason.ENDPOINT_DISABLED: "Target endpoint was disabled",
            DeadLetterReason.ENDPOINT_DELETED: "Target endpoint was deleted",
            DeadLetterReason.PERMANENT_ERROR: "Received permanent error response (4xx)",
            DeadLetterReason.SECURITY_VIOLATION: "Security violation detected",
            DeadLetterReason.CONFIGURATION_ERROR: "Configuration error prevented delivery",
            DeadLetterReason.MANUAL_INTERVENTION: "Manually moved to dead letter queue"
        }
        
        return summaries.get(reason, f"Delivery failed due to {reason.value}")
    
    def _extract_retry_history(self, delivery: WebhookDelivery) -> List[Dict[str, Any]]:
        """Extract retry history from delivery attempts."""
        history = []
        
        for attempt in delivery.attempts:
            history.append({
                "attempt_number": attempt.attempt_number,
                "attempted_at": attempt.attempted_at.isoformat(),
                "status": attempt.delivery_status.value,
                "response_code": attempt.response_status_code,
                "response_time_ms": attempt.response_time_ms,
                "error_message": attempt.error_message
            })
        
        return history
    
    async def _store_dead_letter_entry(self, entry: DeadLetterEntry) -> None:
        """Store dead letter entry in persistent storage."""
        insert_query = f"""
        INSERT INTO {self._schema}.webhook_dead_letter_queue (
            delivery_id, event_id, endpoint_id, reason, failure_summary,
            error_details, retry_history, created_at, expires_at,
            is_processed, recovery_attempts
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """
        
        await self._db.execute(
            insert_query,
            entry.delivery_id.value,
            entry.event_id.value, 
            entry.endpoint_id.value,
            entry.reason.value,
            entry.failure_summary,
            entry.error_details,
            entry.retry_history,
            entry.created_at,
            entry.expires_at,
            entry.is_processed,
            entry.recovery_attempts
        )
    
    async def _determine_processing_action(self, entry: DeadLetterEntry) -> DeadLetterAction:
        """Determine what action to take for a dead letter entry."""
        # Default action based on reason
        action_map = {
            DeadLetterReason.MAX_RETRIES_EXCEEDED: DeadLetterAction.ARCHIVE,
            DeadLetterReason.CIRCUIT_BREAKER_PERMANENT: DeadLetterAction.ARCHIVE,
            DeadLetterReason.ENDPOINT_DISABLED: DeadLetterAction.ARCHIVE,
            DeadLetterReason.ENDPOINT_DELETED: DeadLetterAction.DELETE,
            DeadLetterReason.PERMANENT_ERROR: DeadLetterAction.DELETE,
            DeadLetterReason.SECURITY_VIOLATION: DeadLetterAction.DELETE,
            DeadLetterReason.CONFIGURATION_ERROR: DeadLetterAction.RETRY_MANUAL,
            DeadLetterReason.MANUAL_INTERVENTION: DeadLetterAction.ARCHIVE
        }
        
        return action_map.get(entry.reason, DeadLetterAction.ARCHIVE)
    
    async def _execute_processing_action(self, entry: DeadLetterEntry, action: DeadLetterAction) -> str:
        """Execute the determined processing action."""
        if action == DeadLetterAction.ARCHIVE:
            return "Entry archived for long-term retention"
        elif action == DeadLetterAction.DELETE:
            return "Entry marked for deletion"
        elif action == DeadLetterAction.RETRY_MANUAL:
            return "Entry flagged for manual retry review"
        elif action == DeadLetterAction.REDIRECT:
            return "Entry prepared for endpoint redirection"
        else:
            return f"Action {action.value} executed"
    
    async def _get_unprocessed_entries(self, limit: int) -> List[DeadLetterEntry]:
        """Get unprocessed dead letter entries from persistent storage."""
        query = f"""
        SELECT delivery_id, event_id, endpoint_id, reason, failure_summary,
               error_details, retry_history, created_at, expires_at,
               is_processed, action_taken, action_result, recovery_attempts,
               last_recovery_attempt, processed_at
        FROM {self._schema}.webhook_dead_letter_queue
        WHERE is_processed = false AND expires_at > NOW()
        ORDER BY created_at ASC
        LIMIT $1
        """
        
        rows = await self._db.fetchall(query, limit)
        entries = []
        
        for row in rows:
            try:
                entry = DeadLetterEntry(
                    delivery_id=WebhookDeliveryId(value=row["delivery_id"]),
                    event_id=EventId(value=row["event_id"]),
                    endpoint_id=WebhookEndpointId(value=row["endpoint_id"]),
                    reason=DeadLetterReason(row["reason"]),
                    failure_summary=row["failure_summary"] or "",
                    error_details=row["error_details"] or {},
                    retry_history=row["retry_history"] or [],
                    created_at=row["created_at"],
                    expires_at=row["expires_at"],
                    is_processed=row["is_processed"] or False,
                    recovery_attempts=row["recovery_attempts"] or 0,
                    last_recovery_attempt=row["last_recovery_attempt"],
                    processed_at=row["processed_at"]
                )
                
                if row["action_taken"]:
                    entry.action_taken = DeadLetterAction(row["action_taken"])
                if row["action_result"]:
                    entry.action_result = row["action_result"]
                
                entries.append(entry)
                
            except Exception as e:
                logger.error(f"Error parsing dead letter entry: {e}")
                continue
        
        return entries
    
    async def _get_dead_letter_entry(self, delivery_id: WebhookDeliveryId) -> Optional[DeadLetterEntry]:
        """Get a specific dead letter entry by delivery ID."""
        query = f"""
        SELECT delivery_id, event_id, endpoint_id, reason, failure_summary,
               error_details, retry_history, created_at, expires_at,
               is_processed, action_taken, action_result, recovery_attempts,
               last_recovery_attempt, processed_at
        FROM {self._schema}.webhook_dead_letter_queue
        WHERE delivery_id = $1
        """
        
        row = await self._db.fetchrow(query, delivery_id.value)
        if not row:
            return None
        
        try:
            entry = DeadLetterEntry(
                delivery_id=WebhookDeliveryId(value=row["delivery_id"]),
                event_id=EventId(value=row["event_id"]),
                endpoint_id=WebhookEndpointId(value=row["endpoint_id"]),
                reason=DeadLetterReason(row["reason"]),
                failure_summary=row["failure_summary"] or "",
                error_details=row["error_details"] or {},
                retry_history=row["retry_history"] or [],
                created_at=row["created_at"],
                expires_at=row["expires_at"],
                is_processed=row["is_processed"] or False,
                recovery_attempts=row["recovery_attempts"] or 0,
                last_recovery_attempt=row["last_recovery_attempt"],
                processed_at=row["processed_at"]
            )
            
            if row["action_taken"]:
                entry.action_taken = DeadLetterAction(row["action_taken"])
            if row["action_result"]:
                entry.action_result = row["action_result"]
            
            # Try to load original delivery and event
            try:
                entry.original_delivery = await self._delivery_repo.get_by_id(delivery_id)
                entry.original_event = await self._event_repo.get_by_id(entry.event_id)
            except Exception as load_error:
                logger.warning(f"Could not load original delivery/event for {delivery_id}: {load_error}")
            
            return entry
            
        except Exception as e:
            logger.error(f"Error parsing dead letter entry {delivery_id}: {e}")
            return None
    
    async def _update_dead_letter_entry(self, entry: DeadLetterEntry) -> None:
        """Update a dead letter entry in persistent storage."""
        update_query = f"""
        UPDATE {self._schema}.webhook_dead_letter_queue
        SET is_processed = $1, action_taken = $2, action_result = $3,
            recovery_attempts = $4, last_recovery_attempt = $5, 
            processed_at = $6, error_details = $7
        WHERE delivery_id = $8
        """
        
        await self._db.execute(
            update_query,
            entry.is_processed,
            entry.action_taken.value if entry.action_taken else None,
            entry.action_result,
            entry.recovery_attempts,
            entry.last_recovery_attempt,
            entry.processed_at,
            entry.error_details,
            entry.delivery_id.value
        )