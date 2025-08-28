"""Time-based cache invalidator.

ONLY time-based invalidation functionality - handles scheduled invalidation,
TTL management, and time-based cache cleanup operations.

Following maximum separation architecture - one file = one purpose.
"""

import asyncio
from typing import Dict, List, Optional, Set, Callable, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
import uuid

from ...core.entities.cache_namespace import CacheNamespace
from ...core.value_objects.cache_key import CacheKey
from ...core.protocols.cache_repository import CacheRepository


@dataclass
class ScheduledInvalidation:
    """Scheduled invalidation entry.
    
    Represents a cache invalidation scheduled for future execution.
    """
    schedule_id: str
    key: CacheKey
    namespace: CacheNamespace
    scheduled_time: datetime
    reason: Optional[str] = None
    is_recurring: bool = False
    recurrence_interval: Optional[timedelta] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def is_due(self) -> bool:
        """Check if invalidation is due for execution."""
        return datetime.now(timezone.utc) >= self.scheduled_time
    
    @property
    def time_until_execution(self) -> timedelta:
        """Get time remaining until execution."""
        return self.scheduled_time - datetime.now(timezone.utc)


class TimeInvalidator:
    """Time-based cache invalidator.
    
    Handles scheduled cache invalidation with support for:
    - Delayed invalidation
    - Recurring invalidation patterns
    - Bulk time-based operations
    - TTL-based cleanup
    """
    
    def __init__(self, cache_repository: CacheRepository):
        """Initialize with cache repository.
        
        Args:
            cache_repository: Cache repository for operations
        """
        self._cache_repository = cache_repository
        self._scheduled_invalidations: Dict[str, ScheduledInvalidation] = {}
        self._background_task: Optional[asyncio.Task] = None
        self._running = False
        self._check_interval = timedelta(seconds=1)  # Check every second
    
    async def start_scheduler(self) -> None:
        """Start the background scheduler task."""
        if not self._running:
            self._running = True
            self._background_task = asyncio.create_task(self._scheduler_loop())
    
    async def stop_scheduler(self) -> None:
        """Stop the background scheduler task."""
        self._running = False
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            self._background_task = None
    
    async def schedule_invalidation(
        self,
        key: CacheKey,
        namespace: CacheNamespace,
        delay_seconds: int,
        reason: Optional[str] = None,
        is_recurring: bool = False,
        recurrence_interval: Optional[timedelta] = None
    ) -> str:
        """Schedule key invalidation after delay.
        
        Args:
            key: Cache key to invalidate
            namespace: Namespace containing the key
            delay_seconds: Delay before invalidation
            reason: Optional reason for invalidation
            is_recurring: Whether to repeat the invalidation
            recurrence_interval: Interval for recurring invalidation
            
        Returns:
            Schedule ID for management
        """
        schedule_id = str(uuid.uuid4())
        scheduled_time = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        
        invalidation = ScheduledInvalidation(
            schedule_id=schedule_id,
            key=key,
            namespace=namespace,
            scheduled_time=scheduled_time,
            reason=reason,
            is_recurring=is_recurring,
            recurrence_interval=recurrence_interval
        )
        
        self._scheduled_invalidations[schedule_id] = invalidation
        
        # Start scheduler if not running
        if not self._running:
            await self.start_scheduler()
        
        return schedule_id
    
    async def cancel_scheduled_invalidation(self, schedule_id: str) -> bool:
        """Cancel scheduled invalidation.
        
        Args:
            schedule_id: ID of scheduled invalidation
            
        Returns:
            True if cancellation was successful
        """
        if schedule_id in self._scheduled_invalidations:
            del self._scheduled_invalidations[schedule_id]
            return True
        return False
    
    async def list_scheduled_invalidations(
        self,
        namespace: Optional[CacheNamespace] = None
    ) -> List[Dict[str, Any]]:
        """List pending scheduled invalidations.
        
        Args:
            namespace: Optional namespace filter
            
        Returns:
            List of scheduled invalidation details
        """
        invalidations = []
        
        for invalidation in self._scheduled_invalidations.values():
            if namespace is None or invalidation.namespace.name == namespace.name:
                invalidations.append({
                    "schedule_id": invalidation.schedule_id,
                    "key": invalidation.key.value,
                    "namespace": invalidation.namespace.name,
                    "scheduled_time": invalidation.scheduled_time.isoformat(),
                    "time_until_execution": max(
                        invalidation.time_until_execution.total_seconds(), 0
                    ),
                    "reason": invalidation.reason,
                    "is_recurring": invalidation.is_recurring,
                    "recurrence_interval": (
                        invalidation.recurrence_interval.total_seconds() 
                        if invalidation.recurrence_interval else None
                    ),
                    "created_at": invalidation.created_at.isoformat(),
                    "is_due": invalidation.is_due
                })
        
        return sorted(invalidations, key=lambda x: x["scheduled_time"])
    
    async def schedule_recurring_invalidation(
        self,
        key: CacheKey,
        namespace: CacheNamespace,
        interval: timedelta,
        reason: Optional[str] = None,
        start_delay: Optional[timedelta] = None
    ) -> str:
        """Schedule recurring invalidation.
        
        Args:
            key: Cache key to invalidate
            namespace: Namespace containing the key
            interval: Recurrence interval
            reason: Optional reason for invalidation
            start_delay: Optional delay before first execution
            
        Returns:
            Schedule ID for management
        """
        delay = start_delay or interval
        return await self.schedule_invalidation(
            key=key,
            namespace=namespace,
            delay_seconds=int(delay.total_seconds()),
            reason=reason,
            is_recurring=True,
            recurrence_interval=interval
        )
    
    async def invalidate_expired_entries(
        self,
        namespace: Optional[CacheNamespace] = None
    ) -> int:
        """Invalidate expired cache entries.
        
        Args:
            namespace: Optional namespace filter
            
        Returns:
            Number of entries invalidated
        """
        # This is a placeholder - actual implementation would depend on
        # the cache repository supporting TTL queries
        # For now, we rely on the cache repository's built-in TTL handling
        return 0
    
    async def cleanup_old_schedules(self, older_than: timedelta) -> int:
        """Clean up old completed schedules.
        
        Args:
            older_than: Remove schedules older than this
            
        Returns:
            Number of schedules removed
        """
        cutoff_time = datetime.now(timezone.utc) - older_than
        to_remove = []
        
        for schedule_id, invalidation in self._scheduled_invalidations.items():
            # Remove completed non-recurring schedules older than cutoff
            if (not invalidation.is_recurring and 
                invalidation.scheduled_time < cutoff_time and
                invalidation.created_at < cutoff_time):
                to_remove.append(schedule_id)
        
        for schedule_id in to_remove:
            del self._scheduled_invalidations[schedule_id]
        
        return len(to_remove)
    
    async def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics.
        
        Returns:
            Dictionary with scheduler statistics
        """
        now = datetime.now(timezone.utc)
        total_schedules = len(self._scheduled_invalidations)
        due_schedules = sum(1 for inv in self._scheduled_invalidations.values() if inv.is_due)
        recurring_schedules = sum(1 for inv in self._scheduled_invalidations.values() if inv.is_recurring)
        
        # Get next execution time
        next_execution = None
        if self._scheduled_invalidations:
            next_inv = min(
                self._scheduled_invalidations.values(),
                key=lambda x: x.scheduled_time
            )
            next_execution = next_inv.scheduled_time.isoformat()
        
        return {
            "is_running": self._running,
            "total_scheduled": total_schedules,
            "due_for_execution": due_schedules,
            "recurring_schedules": recurring_schedules,
            "next_execution": next_execution,
            "check_interval_seconds": self._check_interval.total_seconds(),
            "current_time": now.isoformat()
        }
    
    async def _scheduler_loop(self) -> None:
        """Background scheduler loop."""
        while self._running:
            try:
                await self._process_due_invalidations()
                await asyncio.sleep(self._check_interval.total_seconds())
            except asyncio.CancelledError:
                break
            except Exception:
                # Log error and continue
                await asyncio.sleep(self._check_interval.total_seconds())
    
    async def _process_due_invalidations(self) -> None:
        """Process invalidations that are due for execution."""
        due_invalidations = []
        
        for invalidation in self._scheduled_invalidations.values():
            if invalidation.is_due:
                due_invalidations.append(invalidation)
        
        for invalidation in due_invalidations:
            try:
                # Execute invalidation
                await self._cache_repository.delete_entry(
                    invalidation.key, 
                    invalidation.namespace
                )
                
                # Handle recurring invalidations
                if invalidation.is_recurring and invalidation.recurrence_interval:
                    # Schedule next occurrence
                    invalidation.scheduled_time += invalidation.recurrence_interval
                else:
                    # Remove completed non-recurring invalidation
                    del self._scheduled_invalidations[invalidation.schedule_id]
                    
            except Exception:
                # Log error but continue processing other invalidations
                continue
    
    async def force_execute_schedule(self, schedule_id: str) -> bool:
        """Force immediate execution of scheduled invalidation.
        
        Args:
            schedule_id: ID of scheduled invalidation
            
        Returns:
            True if execution was successful
        """
        if schedule_id not in self._scheduled_invalidations:
            return False
        
        invalidation = self._scheduled_invalidations[schedule_id]
        
        try:
            await self._cache_repository.delete_entry(
                invalidation.key,
                invalidation.namespace
            )
            
            # Remove or reschedule based on recurrence
            if invalidation.is_recurring and invalidation.recurrence_interval:
                invalidation.scheduled_time = (
                    datetime.now(timezone.utc) + invalidation.recurrence_interval
                )
            else:
                del self._scheduled_invalidations[schedule_id]
            
            return True
            
        except Exception:
            return False
    
    def set_check_interval(self, interval: timedelta) -> None:
        """Set scheduler check interval.
        
        Args:
            interval: New check interval
        """
        self._check_interval = interval


def create_time_invalidator(cache_repository: CacheRepository) -> TimeInvalidator:
    """Factory function to create time invalidator.
    
    Args:
        cache_repository: Cache repository for operations
        
    Returns:
        Configured time invalidator instance
    """
    return TimeInvalidator(cache_repository)