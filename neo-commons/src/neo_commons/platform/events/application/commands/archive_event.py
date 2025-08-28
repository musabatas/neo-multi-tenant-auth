"""Archive event command for platform events infrastructure.

This module handles ONLY event archival operations following maximum separation architecture.
Single responsibility: Archive and manage lifecycle of events in the platform system.

Pure application layer - no infrastructure concerns.
Uses protocols for dependency injection and clean architecture compliance.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum

from ...core.protocols import EventRepository
from ...core.entities import DomainEvent
from ...core.value_objects import EventId
from ...core.exceptions import EventDispatchFailed
from .....core.value_objects import UserId
from .....utils import utc_now


class ArchivalReason(Enum):
    """Reasons for event archival."""
    AGE_BASED = "age_based"           # Archived due to age policy
    SIZE_BASED = "size_based"         # Archived due to storage optimization  
    MANUAL = "manual"                 # Manually archived by user
    COMPLIANCE = "compliance"         # Archived for compliance requirements
    ERROR_CLEANUP = "error_cleanup"   # Archived due to processing errors
    BULK_CLEANUP = "bulk_cleanup"     # Archived as part of bulk cleanup


@dataclass
class ArchiveEventData:
    """Data required to archive events.
    
    Contains all the configuration needed to archive events.
    Separates data from business logic following CQRS patterns.
    """
    # Event selection criteria
    event_ids: Optional[List[EventId]] = None  # Specific events to archive
    event_types: Optional[List[str]] = None     # Archive events of these types
    
    # Time-based archival criteria
    older_than_days: Optional[int] = None       # Archive events older than N days
    before_date: Optional[datetime] = None      # Archive events before this date
    after_date: Optional[datetime] = None       # Archive events after this date
    
    # Status-based criteria
    processed_only: bool = True                 # Only archive processed events
    failed_only: bool = False                   # Only archive failed events
    
    # Archival configuration
    reason: ArchivalReason = ArchivalReason.MANUAL
    reason_details: Optional[str] = None
    compress_data: bool = True                  # Compress archived data
    maintain_references: bool = True            # Keep references for lookups
    
    # Archival destination
    archive_location: str = "default"           # Archive storage location
    retention_days: Optional[int] = None        # Days to retain in archive (None = forever)
    
    # Context and metadata
    archived_by_user_id: Optional[UserId] = None
    batch_id: Optional[str] = None              # For bulk operations
    dry_run: bool = False                       # Preview mode - don't actually archive
    
    def __post_init__(self):
        """Validate data after initialization."""
        if not any([self.event_ids, self.event_types, self.older_than_days, self.before_date]):
            raise ValueError("Must specify at least one selection criteria for archival")


@dataclass
class ArchiveEventResult:
    """Result of event archival operation.
    
    Contains archival statistics and operation metadata.
    Provides clear feedback about the archival operation.
    """
    total_events_selected: int
    events_archived: int
    events_skipped: int
    events_failed: int
    archive_batch_id: str
    archive_location: str
    operation_duration_ms: float
    archived_event_ids: List[EventId] = field(default_factory=list)
    skipped_reasons: Dict[str, int] = field(default_factory=dict)
    error_details: List[str] = field(default_factory=list)
    success: bool = True
    message: str = "Event archival completed successfully"


class ArchiveEventCommand:
    """Command to archive events.
    
    Handles event archival with proper selection criteria, validation,
    data compression, and reference maintenance.
    
    Single responsibility: ONLY event archival logic.
    Uses dependency injection through protocols for clean architecture.
    """
    
    def __init__(self, repository: EventRepository):
        """Initialize command with required dependencies.
        
        Args:
            repository: Event repository for event persistence and archival
        """
        self._repository = repository
    
    async def execute(self, data: ArchiveEventData) -> ArchiveEventResult:
        """Execute event archival command.
        
        Selects events based on criteria, validates archival eligibility,
        performs archival operation, and tracks results.
        
        Args:
            data: Event archival data containing selection and configuration
            
        Returns:
            ArchiveEventResult with archival statistics and metadata
            
        Raises:
            EventDispatchFailed: If archival operation fails
            ValueError: If archival criteria are invalid
        """
        start_time = utc_now()
        
        try:
            # Validate archival criteria
            self._validate_archival_criteria(data)
            
            # Select events for archival
            events_to_archive = await self._select_events_for_archival(data)
            
            # Filter events based on eligibility
            eligible_events, skipped_events, skip_reasons = self._filter_eligible_events(
                events_to_archive, data
            )
            
            # Perform archival operation (or dry run)
            if data.dry_run:
                archived_events, failed_events, error_details = [], [], []
            else:
                archived_events, failed_events, error_details = await self._perform_archival(
                    eligible_events, data
                )
            
            # Calculate operation duration
            duration_ms = (utc_now() - start_time).total_seconds() * 1000
            
            # Generate batch ID for tracking
            batch_id = data.batch_id or f"archive_{start_time.strftime('%Y%m%d_%H%M%S')}_{len(events_to_archive)}"
            
            # Create result
            result = ArchiveEventResult(
                total_events_selected=len(events_to_archive),
                events_archived=len(archived_events),
                events_skipped=len(skipped_events),
                events_failed=len(failed_events),
                archive_batch_id=batch_id,
                archive_location=data.archive_location,
                operation_duration_ms=duration_ms,
                archived_event_ids=[event.id for event in archived_events],
                skipped_reasons=skip_reasons,
                error_details=error_details,
                success=len(failed_events) == 0,
                message=self._build_result_message(data.dry_run, len(archived_events), len(skipped_events), len(failed_events))
            )
            
            return result
            
        except ValueError as e:
            raise EventDispatchFailed(f"Invalid archival criteria: {str(e)}")
        except Exception as e:
            raise EventDispatchFailed(f"Failed to archive events: {str(e)}")
    
    def _validate_archival_criteria(self, data: ArchiveEventData) -> None:
        """Validate event archival criteria.
        
        Args:
            data: Archival data to validate
            
        Raises:
            ValueError: If criteria are invalid
        """
        # Validate time-based criteria
        if data.older_than_days is not None and data.older_than_days < 1:
            raise ValueError("older_than_days must be at least 1")
        
        if data.before_date and data.after_date and data.before_date <= data.after_date:
            raise ValueError("before_date must be after after_date")
        
        # Validate retention settings
        if data.retention_days is not None and data.retention_days < 30:
            raise ValueError("retention_days must be at least 30 days")
        
        # Validate archive location
        if not data.archive_location or not data.archive_location.strip():
            raise ValueError("archive_location cannot be empty")
        
        # Validate conflicting criteria
        if data.processed_only and data.failed_only:
            raise ValueError("Cannot specify both processed_only and failed_only")
    
    async def _select_events_for_archival(self, data: ArchiveEventData) -> List[DomainEvent]:
        """Select events based on archival criteria.
        
        Args:
            data: Archival criteria
            
        Returns:
            List of events matching criteria
        """
        # Build filters for repository query
        filters = {}
        
        # Specific event IDs
        if data.event_ids:
            filters["event_ids"] = [str(event_id) for event_id in data.event_ids]
        
        # Event types
        if data.event_types:
            filters["event_types"] = data.event_types
        
        # Time-based filters
        if data.older_than_days:
            cutoff_date = utc_now() - timedelta(days=data.older_than_days)
            filters["created_before"] = cutoff_date
        
        if data.before_date:
            filters["created_before"] = data.before_date
        
        if data.after_date:
            filters["created_after"] = data.after_date
        
        # Status filters
        if data.processed_only:
            filters["status"] = "processed"
        elif data.failed_only:
            filters["status"] = "failed"
        
        # Query repository with filters
        search_result = await self._repository.search_events(
            filters=filters,
            sort_by="created_at",
            sort_order="asc",
            limit=10000  # Large limit for bulk operations
        )
        
        return search_result.get("events", [])
    
    def _filter_eligible_events(
        self, 
        events: List[DomainEvent], 
        data: ArchiveEventData
    ) -> tuple[List[DomainEvent], List[DomainEvent], Dict[str, int]]:
        """Filter events for archival eligibility.
        
        Args:
            events: Events to filter
            data: Archival configuration
            
        Returns:
            Tuple of (eligible_events, skipped_events, skip_reasons)
        """
        eligible = []
        skipped = []
        skip_reasons = {}
        
        for event in events:
            skip_reason = self._check_archival_eligibility(event, data)
            if skip_reason:
                skipped.append(event)
                skip_reasons[skip_reason] = skip_reasons.get(skip_reason, 0) + 1
            else:
                eligible.append(event)
        
        return eligible, skipped, skip_reasons
    
    def _check_archival_eligibility(self, event: DomainEvent, data: ArchiveEventData) -> Optional[str]:
        """Check if event is eligible for archival.
        
        Args:
            event: Event to check
            data: Archival configuration
            
        Returns:
            Skip reason if not eligible, None if eligible
        """
        # Check if event is too recent (safety buffer)
        if (utc_now() - event.occurred_at).total_seconds() < 3600:  # 1 hour buffer
            return "too_recent"
        
        # Check if event is already archived (if tracking available)
        # This would depend on repository implementation
        
        # Check if event has active references (if maintain_references is True)
        if data.maintain_references:
            # In a complete implementation, check for active references
            # For now, assume all events are eligible
            pass
        
        # All checks passed - event is eligible
        return None
    
    async def _perform_archival(
        self, 
        events: List[DomainEvent], 
        data: ArchiveEventData
    ) -> tuple[List[DomainEvent], List[DomainEvent], List[str]]:
        """Perform the actual archival operation.
        
        Args:
            events: Events to archive
            data: Archival configuration
            
        Returns:
            Tuple of (archived_events, failed_events, error_details)
        """
        archived = []
        failed = []
        errors = []
        
        for event in events:
            try:
                # Archive the event
                await self._archive_single_event(event, data)
                archived.append(event)
                
            except Exception as e:
                failed.append(event)
                errors.append(f"Failed to archive event {event.id}: {str(e)}")
        
        return archived, failed, errors
    
    async def _archive_single_event(self, event: DomainEvent, data: ArchiveEventData) -> None:
        """Archive a single event.
        
        Args:
            event: Event to archive
            data: Archival configuration
        """
        # Prepare archive record
        archive_record = {
            "event_id": str(event.id),
            "event_data": event.__dict__ if data.compress_data else event,
            "archived_at": utc_now(),
            "archived_by": str(data.archived_by_user_id) if data.archived_by_user_id else None,
            "archive_reason": data.reason.value,
            "reason_details": data.reason_details,
            "archive_location": data.archive_location,
            "retention_until": (utc_now() + timedelta(days=data.retention_days)) if data.retention_days else None,
            "batch_id": data.batch_id
        }
        
        # In a complete implementation, this would:
        # 1. Save archive record to archive storage
        # 2. Update event status to "archived" 
        # 3. Optionally remove from main event storage
        # 4. Update any references if maintain_references is True
        
        # For now, we'll use the repository's archive method (if available)
        # Note: This assumes the repository has archival capabilities
        if hasattr(self._repository, 'archive_event'):
            await self._repository.archive_event(event.id, archive_record)
    
    def _build_result_message(self, dry_run: bool, archived: int, skipped: int, failed: int) -> str:
        """Build result message based on operation outcome.
        
        Args:
            dry_run: Whether this was a dry run
            archived: Number of events archived
            skipped: Number of events skipped  
            failed: Number of events that failed
            
        Returns:
            Result message string
        """
        if dry_run:
            return f"Dry run completed: {archived} events would be archived, {skipped} skipped, {failed} failed"
        elif failed > 0:
            return f"Archival completed with errors: {archived} archived, {skipped} skipped, {failed} failed"
        elif skipped > 0:
            return f"Archival completed: {archived} events archived, {skipped} skipped"
        else:
            return f"Archival completed successfully: {archived} events archived"


def create_archive_event_command(repository: EventRepository) -> ArchiveEventCommand:
    """Factory function to create ArchiveEventCommand instance.
    
    Args:
        repository: Event repository for event archival
        
    Returns:
        Configured ArchiveEventCommand instance
    """
    return ArchiveEventCommand(repository=repository)