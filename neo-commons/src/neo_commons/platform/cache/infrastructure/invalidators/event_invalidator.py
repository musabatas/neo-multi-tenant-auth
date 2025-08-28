"""Event-based cache invalidator.

ONLY event-based invalidation functionality - handles automatic cache
invalidation triggered by domain events and external system events.

Following maximum separation architecture - one file = one purpose.
"""

import asyncio
from typing import Dict, List, Optional, Set, Callable, Any, Union
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
import uuid
import re
import fnmatch

from ...core.entities.cache_namespace import CacheNamespace
from ...core.value_objects.cache_key import CacheKey
from ...core.value_objects.invalidation_pattern import InvalidationPattern
from ...core.protocols.cache_repository import CacheRepository


class TriggerStatus(Enum):
    """Event trigger status."""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


@dataclass
class EventTrigger:
    """Event-driven invalidation trigger.
    
    Represents a trigger that invalidates cache patterns when specific events occur.
    """
    trigger_id: str
    event_type: str
    pattern: InvalidationPattern
    namespace: Optional[CacheNamespace]
    status: TriggerStatus = TriggerStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    description: Optional[str] = None
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_active(self) -> bool:
        """Check if trigger is active."""
        return self.status == TriggerStatus.ACTIVE
    
    def matches_event_data(self, event_data: Dict[str, Any]) -> bool:
        """Check if event data matches trigger conditions.
        
        Args:
            event_data: Event data to check
            
        Returns:
            True if event matches conditions
        """
        if not self.conditions:
            return True
        
        for key, expected_value in self.conditions.items():
            if key not in event_data:
                return False
            
            actual_value = event_data[key]
            
            # Support different comparison types
            if isinstance(expected_value, dict):
                if "$eq" in expected_value:
                    if actual_value != expected_value["$eq"]:
                        return False
                elif "$in" in expected_value:
                    if actual_value not in expected_value["$in"]:
                        return False
                elif "$regex" in expected_value:
                    if not re.match(expected_value["$regex"], str(actual_value)):
                        return False
            else:
                # Simple equality check
                if actual_value != expected_value:
                    return False
        
        return True


class EventInvalidator:
    """Event-based cache invalidator.
    
    Handles automatic cache invalidation triggered by events with support for:
    - Event pattern matching
    - Conditional triggering
    - Batch event processing
    - Event trigger management
    """
    
    def __init__(self, cache_repository: CacheRepository):
        """Initialize with cache repository.
        
        Args:
            cache_repository: Cache repository for operations
        """
        self._cache_repository = cache_repository
        self._triggers: Dict[str, EventTrigger] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._background_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start_event_processor(self) -> None:
        """Start the background event processor."""
        if not self._running:
            self._running = True
            self._background_task = asyncio.create_task(self._process_events())
    
    async def stop_event_processor(self) -> None:
        """Stop the background event processor."""
        self._running = False
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            self._background_task = None
    
    async def register_event_trigger(
        self,
        event_type: str,
        pattern: InvalidationPattern,
        namespace: Optional[CacheNamespace] = None,
        conditions: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None
    ) -> str:
        """Register event-driven invalidation trigger.
        
        Args:
            event_type: Type of event that triggers invalidation
            pattern: Pattern of keys to invalidate
            namespace: Optional namespace limit
            conditions: Optional event data conditions
            description: Optional description of the trigger
            
        Returns:
            Trigger ID for management
        """
        trigger_id = str(uuid.uuid4())
        
        trigger = EventTrigger(
            trigger_id=trigger_id,
            event_type=event_type,
            pattern=pattern,
            namespace=namespace,
            conditions=conditions or {},
            description=description
        )
        
        self._triggers[trigger_id] = trigger
        
        # Start processor if not running
        if not self._running:
            await self.start_event_processor()
        
        return trigger_id
    
    async def unregister_event_trigger(self, trigger_id: str) -> bool:
        """Unregister event-driven invalidation trigger.
        
        Args:
            trigger_id: ID of trigger to remove
            
        Returns:
            True if trigger was removed successfully
        """
        if trigger_id in self._triggers:
            del self._triggers[trigger_id]
            return True
        return False
    
    async def pause_trigger(self, trigger_id: str) -> bool:
        """Pause an event trigger.
        
        Args:
            trigger_id: ID of trigger to pause
            
        Returns:
            True if trigger was paused successfully
        """
        if trigger_id in self._triggers:
            self._triggers[trigger_id].status = TriggerStatus.PAUSED
            return True
        return False
    
    async def resume_trigger(self, trigger_id: str) -> bool:
        """Resume a paused event trigger.
        
        Args:
            trigger_id: ID of trigger to resume
            
        Returns:
            True if trigger was resumed successfully
        """
        if trigger_id in self._triggers:
            self._triggers[trigger_id].status = TriggerStatus.ACTIVE
            return True
        return False
    
    async def trigger_event_invalidation(
        self,
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None
    ) -> int:
        """Trigger invalidation based on event.
        
        Args:
            event_type: Type of event occurring
            event_data: Optional event data for context
            
        Returns:
            Number of keys invalidated
        """
        if not self._running:
            await self.start_event_processor()
        
        # Queue event for processing
        await self._event_queue.put({
            "event_type": event_type,
            "event_data": event_data or {},
            "timestamp": datetime.now(timezone.utc)
        })
        
        # For synchronous processing, we'd process immediately
        # For now, return 0 as actual count will be processed asynchronously
        return 0
    
    async def process_event_immediately(
        self,
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None
    ) -> int:
        """Process event immediately and return invalidation count.
        
        Args:
            event_type: Type of event occurring
            event_data: Optional event data for context
            
        Returns:
            Number of keys invalidated
        """
        event_data = event_data or {}
        total_invalidated = 0
        
        # Find matching triggers
        matching_triggers = self._find_matching_triggers(event_type, event_data)
        
        for trigger in matching_triggers:
            try:
                invalidated = await self._execute_trigger(trigger, event_data)
                total_invalidated += invalidated
            except Exception:
                # Continue with other triggers even if one fails
                continue
        
        return total_invalidated
    
    async def list_event_triggers(
        self,
        event_type: Optional[str] = None,
        namespace: Optional[CacheNamespace] = None,
        status: Optional[TriggerStatus] = None
    ) -> List[Dict[str, Any]]:
        """List registered event triggers.
        
        Args:
            event_type: Optional event type filter
            namespace: Optional namespace filter
            status: Optional status filter
            
        Returns:
            List of trigger details
        """
        triggers = []
        
        for trigger in self._triggers.values():
            # Apply filters
            if event_type and trigger.event_type != event_type:
                continue
            if namespace and trigger.namespace and trigger.namespace.name != namespace.name:
                continue
            if status and trigger.status != status:
                continue
            
            triggers.append({
                "trigger_id": trigger.trigger_id,
                "event_type": trigger.event_type,
                "pattern": {
                    "pattern": trigger.pattern.pattern,
                    "pattern_type": trigger.pattern.pattern_type
                },
                "namespace": trigger.namespace.name if trigger.namespace else None,
                "status": trigger.status.value,
                "description": trigger.description,
                "conditions": trigger.conditions,
                "created_at": trigger.created_at.isoformat(),
                "last_triggered": trigger.last_triggered.isoformat() if trigger.last_triggered else None,
                "trigger_count": trigger.trigger_count,
                "is_active": trigger.is_active
            })
        
        return sorted(triggers, key=lambda x: x["created_at"])
    
    async def get_trigger_statistics(self, trigger_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific trigger.
        
        Args:
            trigger_id: ID of trigger to get stats for
            
        Returns:
            Trigger statistics or None if not found
        """
        if trigger_id not in self._triggers:
            return None
        
        trigger = self._triggers[trigger_id]
        
        return {
            "trigger_id": trigger_id,
            "event_type": trigger.event_type,
            "status": trigger.status.value,
            "trigger_count": trigger.trigger_count,
            "created_at": trigger.created_at.isoformat(),
            "last_triggered": trigger.last_triggered.isoformat() if trigger.last_triggered else None,
            "average_triggers_per_day": self._calculate_average_triggers_per_day(trigger),
            "pattern_complexity": self._assess_pattern_complexity(trigger.pattern),
            "condition_complexity": len(trigger.conditions)
        }
    
    async def get_event_processor_stats(self) -> Dict[str, Any]:
        """Get event processor statistics.
        
        Returns:
            Event processor statistics
        """
        active_triggers = sum(1 for t in self._triggers.values() if t.is_active)
        total_triggers = len(self._triggers)
        total_trigger_count = sum(t.trigger_count for t in self._triggers.values())
        
        event_types = set(t.event_type for t in self._triggers.values())
        namespaces = set(
            t.namespace.name for t in self._triggers.values() 
            if t.namespace
        )
        
        return {
            "is_running": self._running,
            "total_triggers": total_triggers,
            "active_triggers": active_triggers,
            "paused_triggers": total_triggers - active_triggers,
            "total_trigger_executions": total_trigger_count,
            "unique_event_types": len(event_types),
            "unique_namespaces": len(namespaces),
            "queue_size": self._event_queue.qsize(),
            "current_time": datetime.now(timezone.utc).isoformat()
        }
    
    def _find_matching_triggers(
        self, 
        event_type: str, 
        event_data: Dict[str, Any]
    ) -> List[EventTrigger]:
        """Find triggers that match the event.
        
        Args:
            event_type: Type of event
            event_data: Event data
            
        Returns:
            List of matching triggers
        """
        matching_triggers = []
        
        for trigger in self._triggers.values():
            if (trigger.is_active and 
                trigger.event_type == event_type and
                trigger.matches_event_data(event_data)):
                matching_triggers.append(trigger)
        
        return matching_triggers
    
    async def _execute_trigger(
        self, 
        trigger: EventTrigger, 
        event_data: Dict[str, Any]
    ) -> int:
        """Execute a trigger and invalidate matching keys.
        
        Args:
            trigger: Trigger to execute
            event_data: Event data for context
            
        Returns:
            Number of keys invalidated
        """
        # Update trigger statistics
        trigger.last_triggered = datetime.now(timezone.utc)
        trigger.trigger_count += 1
        
        # Get all keys and find matches
        all_keys = await self._get_all_cache_keys(trigger.namespace)
        matching_keys = []
        
        for key in all_keys:
            if self._key_matches_pattern(key, trigger.pattern):
                matching_keys.append(key)
        
        # Invalidate matching keys
        invalidated_count = 0
        for key in matching_keys:
            try:
                success = await self._cache_repository.delete_entry(
                    key, 
                    trigger.namespace or CacheNamespace("default")
                )
                if success:
                    invalidated_count += 1
            except Exception:
                continue
        
        return invalidated_count
    
    async def _process_events(self) -> None:
        """Background event processing loop."""
        while self._running:
            try:
                # Wait for events with timeout
                event = await asyncio.wait_for(
                    self._event_queue.get(), 
                    timeout=1.0
                )
                
                await self.process_event_immediately(
                    event["event_type"],
                    event["event_data"]
                )
                
            except asyncio.TimeoutError:
                continue  # No events, continue waiting
            except asyncio.CancelledError:
                break
            except Exception:
                # Log error and continue
                continue
    
    async def _get_all_cache_keys(self, namespace: Optional[CacheNamespace] = None) -> List[CacheKey]:
        """Get all cache keys for pattern matching.
        
        Args:
            namespace: Optional namespace filter
            
        Returns:
            List of cache keys
        """
        try:
            if hasattr(self._cache_repository, 'list_keys'):
                return await self._cache_repository.list_keys(namespace)
            return []
        except Exception:
            return []
    
    def _key_matches_pattern(self, key: CacheKey, pattern: InvalidationPattern) -> bool:
        """Check if key matches pattern.
        
        Args:
            key: Cache key to check
            pattern: Pattern to match
            
        Returns:
            True if key matches pattern
        """
        key_str = key.value
        pattern_str = pattern.pattern
        
        if pattern.pattern_type == "literal":
            return key_str == pattern_str
        elif pattern.pattern_type == "wildcard":
            return fnmatch.fnmatch(key_str, pattern_str)
        elif pattern.pattern_type == "regex":
            try:
                return bool(re.match(pattern_str, key_str))
            except re.error:
                return False
        else:
            return key_str == pattern_str
    
    def _calculate_average_triggers_per_day(self, trigger: EventTrigger) -> float:
        """Calculate average triggers per day for a trigger.
        
        Args:
            trigger: Trigger to analyze
            
        Returns:
            Average triggers per day
        """
        if trigger.trigger_count == 0:
            return 0.0
        
        days_active = (datetime.now(timezone.utc) - trigger.created_at).days
        if days_active == 0:
            days_active = 1  # At least 1 day for calculation
        
        return trigger.trigger_count / days_active
    
    def _assess_pattern_complexity(self, pattern: InvalidationPattern) -> str:
        """Assess pattern complexity level.
        
        Args:
            pattern: Pattern to assess
            
        Returns:
            Complexity level (simple, medium, complex)
        """
        pattern_str = pattern.pattern
        
        if pattern.pattern_type == "literal":
            return "simple"
        elif pattern.pattern_type == "wildcard":
            if pattern_str.count("*") + pattern_str.count("?") <= 2:
                return "simple"
            else:
                return "medium"
        elif pattern.pattern_type == "regex":
            # Simple heuristic for regex complexity
            special_chars = len([c for c in pattern_str if c in r"[]{}()|+*?^$\\"])
            if special_chars <= 3:
                return "medium"
            else:
                return "complex"
        
        return "simple"


def create_event_invalidator(cache_repository: CacheRepository) -> EventInvalidator:
    """Factory function to create event invalidator.
    
    Args:
        cache_repository: Cache repository for operations
        
    Returns:
        Configured event invalidator instance
    """
    return EventInvalidator(cache_repository)