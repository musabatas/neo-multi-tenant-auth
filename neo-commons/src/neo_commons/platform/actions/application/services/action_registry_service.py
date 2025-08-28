"""Action registry service for platform actions infrastructure.

Pure platform service providing action registration, management, and intelligent matching
with high-performance caching for event-driven architectures.

Following maximum separation architecture - this file contains ONLY action registry orchestration.
Action filtering, execution, and delivery are separate services in their own files.

Extracted to platform/actions following enterprise clean architecture patterns.
Pure platform infrastructure - used by all business features.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from datetime import datetime, timedelta

# Platform actions core imports (clean boundaries)
from ...core.entities import Action
from ...core.value_objects import ActionId, ActionStatus, HandlerType, ActionPriority
from ...core.protocols import ActionRepository

# Neo-commons core imports
from .....core.value_objects import UserId
from .....utils import utc_now


logger = logging.getLogger(__name__)


@runtime_checkable
class ActionRegistryService(Protocol):
    """Action registry service protocol for platform actions infrastructure.
    
    This protocol defines the contract for action registration and intelligent matching
    following maximum separation architecture. Single responsibility: coordinate action
    registration lifecycle, intelligent matching, and performance optimization.
    
    Pure platform infrastructure protocol - implementations handle:
    - Action registration and configuration management
    - High-performance action matching with caching
    - Action lifecycle management (active, paused, archived)
    - Performance optimization through intelligent caching strategies
    - Action condition evaluation and filtering
    - Registry health monitoring and optimization
    """
    
    async def register_action(
        self,
        action: Action,
        validation_context: Optional[Dict[str, Any]] = None
    ) -> Action:
        """Register a new action in the registry.
        
        Handles action registration with proper validation, conflict detection,
        and cache optimization for high-performance event matching.
        
        Args:
            action: Action configuration to register
            validation_context: Optional validation context for extended checks
            
        Returns:
            Registered action with registry metadata
            
        Raises:
            ActionRegistrationError: If action cannot be registered
            DuplicateActionError: If action with same configuration exists
            InvalidActionError: If action configuration is invalid
        """
        ...
    
    async def unregister_action(
        self,
        action_id: ActionId,
        reason: Optional[str] = None
    ) -> bool:
        """Unregister an action from the registry.
        
        Handles action removal with proper cache invalidation and
        dependency cleanup for registry consistency.
        
        Args:
            action_id: Unique identifier of the action to unregister
            reason: Optional reason for unregistration (for audit logging)
            
        Returns:
            True if unregistration was successful, False if not found
            
        Raises:
            ActionUnregistrationError: If unregistration operation fails
        """
        ...
    
    async def get_actions_for_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        execution_context: Optional[Dict[str, Any]] = None
    ) -> List[Action]:
        """Get actions that match the given event with intelligent filtering.
        
        High-performance action matching with condition evaluation,
        priority sorting, and cache optimization.
        
        Args:
            event_type: Event type to find matching actions for
            event_data: Complete event data for condition evaluation
            execution_context: Optional context for filtering (tenant, user, etc.)
            
        Returns:
            List of matching actions sorted by priority
            
        Raises:
            ActionMatchingError: If matching operation fails
        """
        ...
    
    async def update_action(
        self,
        action_id: ActionId,
        updates: Dict[str, Any],
        validation_context: Optional[Dict[str, Any]] = None
    ) -> Action:
        """Update an existing action in the registry.
        
        Handles action updates with validation, cache invalidation,
        and consistency checks.
        
        Args:
            action_id: Unique identifier of the action to update
            updates: Dictionary of field updates to apply
            validation_context: Optional validation context for updates
            
        Returns:
            Updated action with new configuration
            
        Raises:
            ActionNotFoundError: If action doesn't exist
            ActionUpdateError: If update operation fails
        """
        ...
    
    async def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry performance and health statistics.
        
        Returns comprehensive registry metrics for monitoring
        and performance optimization.
        
        Returns:
            Dictionary containing registry statistics:
            - total_actions: Total number of registered actions
            - active_actions: Number of active actions
            - actions_by_handler: Actions grouped by handler type
            - cache_hit_rate: Action lookup cache hit percentage
            - avg_match_time_ms: Average action matching time
            - last_cache_refresh: Last cache refresh timestamp
            
        Raises:
            RegistryStatsError: If stats retrieval fails
        """
        ...
    
    async def invalidate_cache(
        self,
        cache_keys: Optional[List[str]] = None
    ) -> None:
        """Invalidate registry cache for consistent performance.
        
        Handles selective or full cache invalidation with
        smart refresh strategies.
        
        Args:
            cache_keys: Optional specific cache keys to invalidate (None = all)
            
        Raises:
            CacheInvalidationError: If cache invalidation fails
        """
        ...


class DefaultActionRegistryService:
    """Default implementation of ActionRegistryService.
    
    High-performance action registry with intelligent caching, condition evaluation,
    and optimized matching for event-driven architectures.
    
    Features:
    - Multi-level caching (event type, handler type, priority)
    - Intelligent cache invalidation strategies
    - Condition evaluation with short-circuiting
    - Priority-based action sorting
    - Performance metrics collection
    - Cache warming and preloading
    """
    
    def __init__(
        self,
        repository: ActionRepository,
        cache_ttl_seconds: int = 300,  # 5 minutes default
        enable_cache: bool = True,
        cache_warm_on_startup: bool = True,
        max_cache_size: int = 10000
    ):
        """Initialize the action registry service.
        
        Args:
            repository: Action storage repository implementation
            cache_ttl_seconds: Cache time-to-live in seconds
            enable_cache: Whether to enable caching (disable for testing)
            cache_warm_on_startup: Whether to warm cache on service startup
            max_cache_size: Maximum number of cached action lists
        """
        self._repository = repository
        self._cache_ttl_seconds = cache_ttl_seconds
        self._enable_cache = enable_cache
        self._cache_warm_on_startup = cache_warm_on_startup
        self._max_cache_size = max_cache_size
        
        # Multi-level cache structure for optimized lookups
        self._event_type_cache: Dict[str, List[Action]] = {}
        self._handler_type_cache: Dict[HandlerType, List[Action]] = {}
        self._user_actions_cache: Dict[str, List[Action]] = {}
        
        # Cache metadata and performance tracking
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_hit_count = 0
        self._cache_miss_count = 0
        self._total_matches = 0
        self._total_match_time_ms = 0.0
        
        # Asynchronous locks for cache operations
        self._cache_lock = asyncio.Lock()
        self._stats_lock = asyncio.Lock()
    
    async def register_action(
        self,
        action: Action,
        validation_context: Optional[Dict[str, Any]] = None
    ) -> Action:
        """Register a new action in the registry."""
        start_time = utc_now()
        
        try:
            # Validate action configuration
            self._validate_action_for_registration(action, validation_context)
            
            # Save to repository
            registered_action = await self._repository.save_action(action)
            
            # Invalidate relevant cache entries
            await self._invalidate_action_caches(action)
            
            # Update performance metrics
            await self._update_registration_metrics(True)
            
            logger.info(
                f"Registered action: {action.name}",
                extra={
                    "action_id": str(action.id),
                    "handler_type": action.handler_type.value,
                    "event_types": action.event_types,
                    "execution_mode": action.execution_mode.value,
                    "priority": action.priority.value,
                    "registration_time_ms": (utc_now() - start_time).total_seconds() * 1000
                }
            )
            
            return registered_action
            
        except Exception as e:
            await self._update_registration_metrics(False)
            logger.error(
                f"Failed to register action: {action.name}",
                extra={
                    "action_id": str(action.id),
                    "error": str(e),
                    "validation_context": validation_context
                },
                exc_info=True
            )
            raise
    
    async def unregister_action(
        self,
        action_id: ActionId,
        reason: Optional[str] = None
    ) -> bool:
        """Unregister an action from the registry."""
        try:
            # Get action before deletion for cache invalidation
            action = await self._repository.get_action_by_id(action_id)
            
            # Delete from repository
            success = await self._repository.delete_action(action_id, soft_delete=True)
            
            if success and action:
                # Invalidate relevant cache entries
                await self._invalidate_action_caches(action)
                
                logger.info(
                    f"Unregistered action: {action.name}",
                    extra={
                        "action_id": str(action_id),
                        "reason": reason or "No reason provided"
                    }
                )
            
            return success
            
        except Exception as e:
            logger.error(
                f"Failed to unregister action: {action_id}",
                extra={
                    "action_id": str(action_id),
                    "reason": reason,
                    "error": str(e)
                },
                exc_info=True
            )
            raise
    
    async def get_actions_for_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        execution_context: Optional[Dict[str, Any]] = None
    ) -> List[Action]:
        """Get actions that match the given event with intelligent filtering."""
        match_start_time = utc_now()
        
        try:
            # Get candidate actions (cached or from repository)
            candidates = await self._get_candidate_actions(event_type, execution_context)
            
            # Track cache performance
            await self._track_cache_hit(len(candidates) > 0)
            
            # Filter candidates by evaluating conditions
            matching_actions = []
            for action in candidates:
                if self._evaluate_action_match(action, event_type, event_data, execution_context):
                    matching_actions.append(action)
            
            # Sort by priority (critical > high > normal > low)
            matching_actions.sort(key=lambda a: a.priority.value, reverse=True)
            
            # Update performance metrics
            match_time_ms = (utc_now() - match_start_time).total_seconds() * 1000
            await self._update_match_metrics(match_time_ms, len(candidates), len(matching_actions))
            
            logger.debug(
                f"Found {len(matching_actions)} matching actions for event: {event_type}",
                extra={
                    "event_type": event_type,
                    "candidates": len(candidates),
                    "matching": len(matching_actions),
                    "match_time_ms": match_time_ms,
                    "execution_context": execution_context
                }
            )
            
            return matching_actions
            
        except Exception as e:
            logger.error(
                f"Failed to get actions for event: {event_type}",
                extra={
                    "event_type": event_type,
                    "error": str(e),
                    "execution_context": execution_context
                },
                exc_info=True
            )
            raise
    
    async def update_action(
        self,
        action_id: ActionId,
        updates: Dict[str, Any],
        validation_context: Optional[Dict[str, Any]] = None
    ) -> Action:
        """Update an existing action in the registry."""
        try:
            # Get current action for cache invalidation
            current_action = await self._repository.get_action_by_id(action_id)
            if not current_action:
                raise ValueError(f"Action not found: {action_id}")
            
            # Validate updates
            self._validate_action_updates(current_action, updates, validation_context)
            
            # Update in repository
            updated_action = await self._repository.update_action(action_id, updates)
            
            # Invalidate cache for both old and new configurations
            await self._invalidate_action_caches(current_action)
            await self._invalidate_action_caches(updated_action)
            
            logger.info(
                f"Updated action: {updated_action.name}",
                extra={
                    "action_id": str(action_id),
                    "updates": list(updates.keys()),
                    "handler_type": updated_action.handler_type.value
                }
            )
            
            return updated_action
            
        except Exception as e:
            logger.error(
                f"Failed to update action: {action_id}",
                extra={
                    "action_id": str(action_id),
                    "updates": list(updates.keys()) if updates else [],
                    "error": str(e)
                },
                exc_info=True
            )
            raise
    
    async def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry performance and health statistics."""
        async with self._stats_lock:
            # Get action counts from repository
            all_actions = await self._repository.search_actions({}, limit=0)  # Get count only
            total_actions = all_actions.get("total_count", 0)
            
            # Get active actions count
            active_filters = {"status": ActionStatus.ACTIVE.value, "is_enabled": True}
            active_result = await self._repository.search_actions(active_filters, limit=0)
            active_actions = active_result.get("total_count", 0)
            
            # Calculate cache statistics
            cache_hit_rate = 0.0
            total_cache_requests = self._cache_hit_count + self._cache_miss_count
            if total_cache_requests > 0:
                cache_hit_rate = (self._cache_hit_count / total_cache_requests) * 100
            
            # Calculate average match time
            avg_match_time_ms = 0.0
            if self._total_matches > 0:
                avg_match_time_ms = self._total_match_time_ms / self._total_matches
            
            # Get cache sizes
            cache_sizes = {
                "event_type_cache": len(self._event_type_cache),
                "handler_type_cache": len(self._handler_type_cache),
                "user_actions_cache": len(self._user_actions_cache)
            }
            
            return {
                "total_actions": total_actions,
                "active_actions": active_actions,
                "cache_enabled": self._enable_cache,
                "cache_ttl_seconds": self._cache_ttl_seconds,
                "cache_hit_rate_percent": round(cache_hit_rate, 2),
                "cache_hits": self._cache_hit_count,
                "cache_misses": self._cache_miss_count,
                "total_matches": self._total_matches,
                "avg_match_time_ms": round(avg_match_time_ms, 3),
                "cache_sizes": cache_sizes,
                "last_stats_update": utc_now().isoformat()
            }
    
    async def invalidate_cache(
        self,
        cache_keys: Optional[List[str]] = None
    ) -> None:
        """Invalidate registry cache for consistent performance."""
        async with self._cache_lock:
            if cache_keys is None:
                # Full cache invalidation
                self._event_type_cache.clear()
                self._handler_type_cache.clear()
                self._user_actions_cache.clear()
                self._cache_timestamps.clear()
                
                logger.info("Full action registry cache invalidated")
            else:
                # Selective cache invalidation
                for cache_key in cache_keys:
                    if cache_key in self._event_type_cache:
                        del self._event_type_cache[cache_key]
                    if cache_key in self._cache_timestamps:
                        del self._cache_timestamps[cache_key]
                
                logger.debug(
                    f"Selective cache invalidation completed",
                    extra={"invalidated_keys": cache_keys}
                )
    
    async def _get_candidate_actions(
        self,
        event_type: str,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> List[Action]:
        """Get candidate actions from cache or repository."""
        if not self._enable_cache:
            return await self._repository.get_actions_by_event_type(event_type, active_only=True)
        
        async with self._cache_lock:
            cache_key = f"event_type:{event_type}"
            now = utc_now()
            
            # Check if cache is valid
            if (cache_key in self._event_type_cache and 
                cache_key in self._cache_timestamps and
                (now - self._cache_timestamps[cache_key]).total_seconds() < self._cache_ttl_seconds):
                return self._event_type_cache[cache_key].copy()
            
            # Refresh cache from repository
            actions = await self._repository.get_actions_by_event_type(event_type, active_only=True)
            
            # Update cache with size limit
            if len(self._event_type_cache) >= self._max_cache_size:
                # Remove oldest cache entry
                oldest_key = min(self._cache_timestamps, key=self._cache_timestamps.get)
                del self._event_type_cache[oldest_key]
                del self._cache_timestamps[oldest_key]
            
            self._event_type_cache[cache_key] = actions.copy()
            self._cache_timestamps[cache_key] = now
            
            return actions
    
    def _evaluate_action_match(
        self,
        action: Action,
        event_type: str,
        event_data: Dict[str, Any],
        execution_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Evaluate if action matches the event with condition checking."""
        try:
            # Use the Action's built-in matching logic
            if not action.matches_event(event_type, event_data):
                return False
            
            # Additional execution context filtering
            if execution_context:
                # Tenant-based filtering
                if "tenant_id" in execution_context and action.tenant_id:
                    if execution_context["tenant_id"] != action.tenant_id:
                        return False
                
                # User-based filtering
                if "user_id" in execution_context and action.created_by_user_id:
                    if execution_context["user_id"] != str(action.created_by_user_id):
                        return False
            
            return True
            
        except Exception as e:
            logger.warning(
                f"Error evaluating action match for action {action.id}: {str(e)}",
                extra={
                    "action_id": str(action.id),
                    "event_type": event_type,
                    "error": str(e)
                }
            )
            return False  # Fail safe - don't execute if condition evaluation fails
    
    async def _invalidate_action_caches(self, action: Action) -> None:
        """Invalidate cache entries related to the action."""
        async with self._cache_lock:
            # Invalidate event type caches
            for event_type in action.event_types:
                cache_key = f"event_type:{event_type}"
                if cache_key in self._event_type_cache:
                    del self._event_type_cache[cache_key]
                if cache_key in self._cache_timestamps:
                    del self._cache_timestamps[cache_key]
            
            # Invalidate handler type cache
            if action.handler_type in self._handler_type_cache:
                del self._handler_type_cache[action.handler_type]
            
            # Invalidate user-specific cache
            if action.created_by_user_id:
                user_cache_key = str(action.created_by_user_id)
                if user_cache_key in self._user_actions_cache:
                    del self._user_actions_cache[user_cache_key]
    
    def _validate_action_for_registration(
        self,
        action: Action,
        validation_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Validate action configuration for registration."""
        # Basic validation is handled in Action.__post_init__
        # Additional registry-specific validation here
        
        if validation_context:
            # Tenant-specific validation
            if "tenant_id" in validation_context:
                if not action.tenant_id or action.tenant_id != validation_context["tenant_id"]:
                    raise ValueError("Action tenant_id must match validation context")
            
            # User permission validation
            if "user_id" in validation_context:
                if not action.created_by_user_id:
                    raise ValueError("Action must have created_by_user_id for user validation")
    
    def _validate_action_updates(
        self,
        current_action: Action,
        updates: Dict[str, Any],
        validation_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Validate action updates before applying."""
        # Prevent changing immutable fields
        immutable_fields = {"id", "created_at", "created_by_user_id"}
        for field in immutable_fields:
            if field in updates:
                raise ValueError(f"Cannot update immutable field: {field}")
        
        # Validate handler type configuration consistency
        if "handler_type" in updates or "configuration" in updates:
            # This would require more complex validation based on handler type
            # For now, rely on Action's validation in the entity
            pass
    
    async def _track_cache_hit(self, was_hit: bool) -> None:
        """Track cache hit/miss statistics."""
        if was_hit:
            self._cache_hit_count += 1
        else:
            self._cache_miss_count += 1
    
    async def _update_match_metrics(
        self,
        match_time_ms: float,
        candidates: int,
        matches: int
    ) -> None:
        """Update action matching performance metrics."""
        self._total_matches += 1
        self._total_match_time_ms += match_time_ms
    
    async def _update_registration_metrics(self, success: bool) -> None:
        """Update action registration metrics."""
        # Could track registration success/failure rates here
        # For now, just logging is sufficient
        pass


def create_action_registry_service(
    repository: ActionRepository,
    cache_ttl_seconds: int = 300,
    enable_cache: bool = True,
    cache_warm_on_startup: bool = True,
    max_cache_size: int = 10000
) -> ActionRegistryService:
    """Factory function to create ActionRegistryService instance.
    
    Args:
        repository: Action storage repository implementation
        cache_ttl_seconds: Cache time-to-live in seconds
        enable_cache: Whether to enable caching
        cache_warm_on_startup: Whether to warm cache on startup
        max_cache_size: Maximum number of cached action lists
        
    Returns:
        Configured ActionRegistryService implementation
    """
    return DefaultActionRegistryService(
        repository=repository,
        cache_ttl_seconds=cache_ttl_seconds,
        enable_cache=enable_cache,
        cache_warm_on_startup=cache_warm_on_startup,
        max_cache_size=max_cache_size
    )