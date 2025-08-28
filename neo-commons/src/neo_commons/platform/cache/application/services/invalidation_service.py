"""Cache invalidation orchestration service.

ONLY invalidation orchestration - manages cache invalidation operations
with pattern matching, dependency tracking, and event-driven triggers.

Following maximum separation architecture - one file = one purpose.
"""

import asyncio
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from weakref import WeakSet

from ...core.protocols.cache_repository import CacheRepository
from ...core.entities.cache_namespace import CacheNamespace
from ...core.value_objects.cache_key import CacheKey
from ...core.value_objects.invalidation_pattern import InvalidationPattern


class InvalidationStats:
    """Invalidation service statistics."""
    
    def __init__(self):
        self.total_invalidations = 0
        self.pattern_invalidations = 0
        self.dependency_invalidations = 0
        self.scheduled_invalidations = 0
        self.event_invalidations = 0
        self.total_keys_invalidated = 0
        self.average_keys_per_invalidation = 0.0
        self.last_invalidation_time = None
        self.error_count = 0


class ScheduledInvalidation:
    """Scheduled invalidation task."""
    
    def __init__(
        self,
        schedule_id: str,
        key: CacheKey,
        namespace: CacheNamespace,
        execute_at: float,
        reason: Optional[str] = None
    ):
        self.schedule_id = schedule_id
        self.key = key
        self.namespace = namespace
        self.execute_at = execute_at
        self.reason = reason
        self.created_at = time.time()
        self.is_cancelled = False


class EventTrigger:
    """Event-driven invalidation trigger."""
    
    def __init__(
        self,
        trigger_id: str,
        event_type: str,
        pattern: InvalidationPattern,
        namespace: Optional[CacheNamespace] = None
    ):
        self.trigger_id = trigger_id
        self.event_type = event_type
        self.pattern = pattern
        self.namespace = namespace
        self.created_at = time.time()
        self.trigger_count = 0
        self.last_triggered = None


class InvalidationServiceImpl:
    """Cache invalidation orchestration service implementation.
    
    Features:
    - Pattern-based invalidation with wildcard and regex support
    - Dependency tracking and cascade invalidation
    - Scheduled invalidation with delay support
    - Event-driven invalidation triggers
    - Performance monitoring and statistics
    - Distributed coordination support
    - Graceful error handling and recovery
    """
    
    def __init__(self, repository: CacheRepository):
        """Initialize invalidation service.
        
        Args:
            repository: Cache repository for storage operations
        """
        self._repository = repository
        self._stats = InvalidationStats()
        
        # Dependency tracking: source_key -> set of dependent keys
        self._dependencies: Dict[str, Set[str]] = defaultdict(set)
        
        # Scheduled invalidations
        self._scheduled_tasks: Dict[str, ScheduledInvalidation] = {}
        self._scheduler_running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        
        # Event triggers
        self._event_triggers: Dict[str, EventTrigger] = {}
        self._event_triggers_by_type: Dict[str, List[str]] = defaultdict(list)
        
        # Background task management
        self._background_tasks: WeakSet = WeakSet()
        self._is_running = True
        
        # Start background scheduler
        self._start_scheduler()
    
    def _start_scheduler(self):
        """Start background scheduler for timed invalidations."""
        if not self._scheduler_running:
            self._scheduler_running = True
            self._scheduler_task = asyncio.create_task(self._run_scheduler())
            self._background_tasks.add(self._scheduler_task)
    
    async def _run_scheduler(self):
        """Background scheduler loop."""
        while self._scheduler_running and self._is_running:
            try:
                current_time = time.time()
                
                # Find expired scheduled tasks
                expired_tasks = [
                    task for task in self._scheduled_tasks.values()
                    if not task.is_cancelled and task.execute_at <= current_time
                ]
                
                # Execute expired tasks
                for task in expired_tasks:
                    try:
                        await self.invalidate_key(
                            task.key, 
                            task.namespace, 
                            f"Scheduled: {task.reason or 'No reason'}"
                        )
                        self._stats.scheduled_invalidations += 1
                    except Exception:
                        self._stats.error_count += 1
                    finally:
                        # Remove completed task
                        if task.schedule_id in self._scheduled_tasks:
                            del self._scheduled_tasks[task.schedule_id]
                
                # Sleep for 1 second before next check
                await asyncio.sleep(1.0)
                
            except asyncio.CancelledError:
                break
            except Exception:
                self._stats.error_count += 1
                # Continue running despite errors
                await asyncio.sleep(1.0)
    
    def _get_full_key(self, key: CacheKey, namespace: CacheNamespace) -> str:
        """Get full cache key with namespace."""
        return namespace.get_full_key(key.value)
    
    async def invalidate_key(
        self, 
        key: CacheKey, 
        namespace: CacheNamespace,
        reason: Optional[str] = None
    ) -> bool:
        """Invalidate single cache key."""
        try:
            # Delete from repository
            success = await self._repository.delete(key, namespace)
            
            # Update statistics
            if success:
                self._stats.total_invalidations += 1
                self._stats.total_keys_invalidated += 1
                self._stats.last_invalidation_time = datetime.now(timezone.utc)
                self._update_averages()
            
            return success
            
        except Exception:
            self._stats.error_count += 1
            return False
    
    async def invalidate_keys(
        self, 
        keys: List[CacheKey], 
        namespace: CacheNamespace,
        reason: Optional[str] = None
    ) -> Dict[CacheKey, bool]:
        """Invalidate multiple cache keys."""
        try:
            results = await self._repository.delete_many(keys, namespace)
            
            # Update statistics
            successful_count = sum(1 for success in results.values() if success)
            if successful_count > 0:
                self._stats.total_invalidations += 1
                self._stats.total_keys_invalidated += successful_count
                self._stats.last_invalidation_time = datetime.now(timezone.utc)
                self._update_averages()
            
            return results
            
        except Exception:
            self._stats.error_count += 1
            return {key: False for key in keys}
    
    async def invalidate_pattern(
        self, 
        pattern: InvalidationPattern,
        namespace: Optional[CacheNamespace] = None,
        reason: Optional[str] = None
    ) -> int:
        """Invalidate keys matching pattern."""
        try:
            count = await self._repository.invalidate_pattern(pattern, namespace)
            
            # Update statistics
            if count > 0:
                self._stats.total_invalidations += 1
                self._stats.pattern_invalidations += 1
                self._stats.total_keys_invalidated += count
                self._stats.last_invalidation_time = datetime.now(timezone.utc)
                self._update_averages()
            
            return count
            
        except Exception:
            self._stats.error_count += 1
            return 0
    
    async def invalidate_namespace(
        self, 
        namespace: CacheNamespace,
        reason: Optional[str] = None
    ) -> int:
        """Invalidate entire namespace."""
        try:
            count = await self._repository.flush_namespace(namespace)
            
            # Update statistics
            if count > 0:
                self._stats.total_invalidations += 1
                self._stats.total_keys_invalidated += count
                self._stats.last_invalidation_time = datetime.now(timezone.utc)
                self._update_averages()
            
            return count
            
        except Exception:
            self._stats.error_count += 1
            return 0
    
    # Dependency-based invalidation
    async def add_dependency(
        self, 
        source_key: CacheKey, 
        dependent_key: CacheKey,
        namespace: CacheNamespace
    ) -> bool:
        """Add cache dependency relationship."""
        try:
            source_full_key = self._get_full_key(source_key, namespace)
            dependent_full_key = self._get_full_key(dependent_key, namespace)
            
            self._dependencies[source_full_key].add(dependent_full_key)
            return True
            
        except Exception:
            self._stats.error_count += 1
            return False
    
    async def remove_dependency(
        self, 
        source_key: CacheKey, 
        dependent_key: CacheKey,
        namespace: CacheNamespace
    ) -> bool:
        """Remove cache dependency relationship."""
        try:
            source_full_key = self._get_full_key(source_key, namespace)
            dependent_full_key = self._get_full_key(dependent_key, namespace)
            
            if source_full_key in self._dependencies:
                self._dependencies[source_full_key].discard(dependent_full_key)
                
                # Clean up empty dependency sets
                if not self._dependencies[source_full_key]:
                    del self._dependencies[source_full_key]
            
            return True
            
        except Exception:
            self._stats.error_count += 1
            return False
    
    async def get_dependencies(
        self, 
        key: CacheKey, 
        namespace: CacheNamespace
    ) -> List[CacheKey]:
        """Get all keys that depend on given key."""
        try:
            full_key = self._get_full_key(key, namespace)
            dependent_keys = self._dependencies.get(full_key, set())
            
            # Convert back to CacheKey objects
            result = []
            namespace_prefix = f"{namespace}:"
            
            for dep_key in dependent_keys:
                if dep_key.startswith(namespace_prefix):
                    key_value = dep_key[len(namespace_prefix):]
                    result.append(CacheKey(key_value))
            
            return result
            
        except Exception:
            self._stats.error_count += 1
            return []
    
    async def invalidate_with_dependencies(
        self, 
        key: CacheKey, 
        namespace: CacheNamespace,
        reason: Optional[str] = None
    ) -> int:
        """Invalidate key and all its dependencies."""
        invalidated_count = 0
        visited_keys = set()
        
        async def _recursive_invalidate(current_key: CacheKey, current_namespace: CacheNamespace):
            nonlocal invalidated_count, visited_keys
            
            full_key = self._get_full_key(current_key, current_namespace)
            if full_key in visited_keys:
                return  # Avoid infinite loops
            
            visited_keys.add(full_key)
            
            try:
                # Invalidate current key
                success = await self.invalidate_key(current_key, current_namespace, reason)
                if success:
                    invalidated_count += 1
                
                # Find and invalidate dependencies
                dependencies = await self.get_dependencies(current_key, current_namespace)
                for dep_key in dependencies:
                    await _recursive_invalidate(dep_key, current_namespace)
                    
            except Exception:
                self._stats.error_count += 1
        
        try:
            await _recursive_invalidate(key, namespace)
            
            # Update statistics
            if invalidated_count > 0:
                self._stats.dependency_invalidations += 1
                self._stats.last_invalidation_time = datetime.now(timezone.utc)
                self._update_averages()
            
            return invalidated_count
            
        except Exception:
            self._stats.error_count += 1
            return invalidated_count
    
    # Scheduled invalidation
    async def schedule_invalidation(
        self, 
        key: CacheKey, 
        namespace: CacheNamespace,
        delay_seconds: int,
        reason: Optional[str] = None
    ) -> str:
        """Schedule key invalidation after delay."""
        try:
            schedule_id = str(uuid.uuid4())
            execute_at = time.time() + delay_seconds
            
            scheduled_task = ScheduledInvalidation(
                schedule_id=schedule_id,
                key=key,
                namespace=namespace,
                execute_at=execute_at,
                reason=reason
            )
            
            self._scheduled_tasks[schedule_id] = scheduled_task
            
            return schedule_id
            
        except Exception:
            self._stats.error_count += 1
            return ""
    
    async def cancel_scheduled_invalidation(self, schedule_id: str) -> bool:
        """Cancel scheduled invalidation."""
        try:
            if schedule_id in self._scheduled_tasks:
                self._scheduled_tasks[schedule_id].is_cancelled = True
                return True
            return False
            
        except Exception:
            self._stats.error_count += 1
            return False
    
    async def list_scheduled_invalidations(
        self, 
        namespace: Optional[CacheNamespace] = None
    ) -> List[Dict[str, Any]]:
        """List pending scheduled invalidations."""
        try:
            result = []
            
            for task in self._scheduled_tasks.values():
                if task.is_cancelled:
                    continue
                
                if namespace and task.namespace.name != namespace.name:
                    continue
                
                result.append({
                    "schedule_id": task.schedule_id,
                    "key": task.key.value,
                    "namespace": task.namespace.name,
                    "execute_at": task.execute_at,
                    "reason": task.reason,
                    "created_at": task.created_at,
                    "seconds_remaining": max(0, task.execute_at - time.time())
                })
            
            return result
            
        except Exception:
            self._stats.error_count += 1
            return []
    
    # Event-driven invalidation
    async def register_event_trigger(
        self, 
        event_type: str,
        pattern: InvalidationPattern,
        namespace: Optional[CacheNamespace] = None
    ) -> str:
        """Register event-driven invalidation trigger."""
        try:
            trigger_id = str(uuid.uuid4())
            
            trigger = EventTrigger(
                trigger_id=trigger_id,
                event_type=event_type,
                pattern=pattern,
                namespace=namespace
            )
            
            self._event_triggers[trigger_id] = trigger
            self._event_triggers_by_type[event_type].append(trigger_id)
            
            return trigger_id
            
        except Exception:
            self._stats.error_count += 1
            return ""
    
    async def unregister_event_trigger(self, trigger_id: str) -> bool:
        """Unregister event-driven invalidation trigger."""
        try:
            if trigger_id not in self._event_triggers:
                return False
            
            trigger = self._event_triggers[trigger_id]
            
            # Remove from type mapping
            if trigger.event_type in self._event_triggers_by_type:
                try:
                    self._event_triggers_by_type[trigger.event_type].remove(trigger_id)
                    
                    # Clean up empty lists
                    if not self._event_triggers_by_type[trigger.event_type]:
                        del self._event_triggers_by_type[trigger.event_type]
                        
                except ValueError:
                    pass  # trigger_id not in list
            
            # Remove trigger
            del self._event_triggers[trigger_id]
            
            return True
            
        except Exception:
            self._stats.error_count += 1
            return False
    
    async def trigger_event_invalidation(
        self, 
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None
    ) -> int:
        """Trigger invalidation based on event."""
        total_invalidated = 0
        
        try:
            trigger_ids = self._event_triggers_by_type.get(event_type, [])
            
            for trigger_id in trigger_ids:
                if trigger_id not in self._event_triggers:
                    continue
                
                trigger = self._event_triggers[trigger_id]
                
                try:
                    # Invalidate based on pattern
                    count = await self.invalidate_pattern(
                        trigger.pattern,
                        trigger.namespace,
                        f"Event: {event_type}"
                    )
                    
                    total_invalidated += count
                    
                    # Update trigger statistics
                    trigger.trigger_count += 1
                    trigger.last_triggered = time.time()
                    
                except Exception:
                    self._stats.error_count += 1
                    continue
            
            # Update statistics
            if total_invalidated > 0:
                self._stats.event_invalidations += 1
                self._stats.last_invalidation_time = datetime.now(timezone.utc)
                self._update_averages()
            
            return total_invalidated
            
        except Exception:
            self._stats.error_count += 1
            return total_invalidated
    
    # Statistics and monitoring
    async def get_invalidation_stats(self) -> Dict[str, Any]:
        """Get invalidation statistics."""
        return {
            "total_invalidations": self._stats.total_invalidations,
            "pattern_invalidations": self._stats.pattern_invalidations,
            "dependency_invalidations": self._stats.dependency_invalidations,
            "scheduled_invalidations": self._stats.scheduled_invalidations,
            "event_invalidations": self._stats.event_invalidations,
            "total_keys_invalidated": self._stats.total_keys_invalidated,
            "average_keys_per_invalidation": self._stats.average_keys_per_invalidation,
            "last_invalidation_time": self._stats.last_invalidation_time.isoformat() if self._stats.last_invalidation_time else None,
            "error_count": self._stats.error_count,
            "active_dependencies": len(self._dependencies),
            "scheduled_tasks_pending": len([t for t in self._scheduled_tasks.values() if not t.is_cancelled]),
            "event_triggers_active": len(self._event_triggers)
        }
    
    async def get_dependency_graph(
        self, 
        namespace: Optional[CacheNamespace] = None
    ) -> Dict[str, List[str]]:
        """Get cache dependency graph."""
        result = {}
        
        try:
            namespace_prefix = f"{namespace}:" if namespace else None
            
            for source_key, dependent_keys in self._dependencies.items():
                # Filter by namespace if specified
                if namespace_prefix and not source_key.startswith(namespace_prefix):
                    continue
                
                # Convert to simplified key format
                if namespace_prefix and source_key.startswith(namespace_prefix):
                    simple_source_key = source_key[len(namespace_prefix):]
                else:
                    simple_source_key = source_key
                
                # Convert dependent keys
                simple_dependent_keys = []
                for dep_key in dependent_keys:
                    if namespace_prefix:
                        if dep_key.startswith(namespace_prefix):
                            simple_dependent_keys.append(dep_key[len(namespace_prefix):])
                    else:
                        simple_dependent_keys.append(dep_key)
                
                if simple_dependent_keys:
                    result[simple_source_key] = simple_dependent_keys
            
            return result
            
        except Exception:
            self._stats.error_count += 1
            return {}
    
    async def health_check(self) -> bool:
        """Check invalidation service health."""
        try:
            # Check if scheduler is running
            if not self._scheduler_running:
                return False
            
            # Check repository health
            repository_healthy = await self._repository.ping()
            if not repository_healthy:
                return False
            
            return True
            
        except Exception:
            return False
    
    def _update_averages(self):
        """Update average statistics."""
        if self._stats.total_invalidations > 0:
            self._stats.average_keys_per_invalidation = (
                self._stats.total_keys_invalidated / self._stats.total_invalidations
            )
    
    async def shutdown(self):
        """Shutdown invalidation service gracefully."""
        self._is_running = False
        self._scheduler_running = False
        
        # Cancel scheduler task
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all background tasks
        for task in list(self._background_tasks):
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
    
    def __del__(self):
        """Cleanup on deletion."""
        if hasattr(self, '_is_running') and self._is_running:
            # Note: Cannot call async shutdown from __del__
            # This is a best-effort cleanup
            self._is_running = False
            self._scheduler_running = False


# Factory function for dependency injection
def create_invalidation_service(repository: CacheRepository) -> InvalidationServiceImpl:
    """Create invalidation service with repository dependency.
    
    Args:
        repository: Cache repository for storage operations
        
    Returns:
        Configured invalidation service
    """
    return InvalidationServiceImpl(repository)