"""
Event Action Registry Service

Provides registration and management of event actions with caching
and intelligent matching for high-performance event processing.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta

from ..entities.protocols import EventActionRepository, EventActionRegistry
from ..entities.event_action import EventAction, ActionStatus
from ..entities.action_conditions import ActionCondition, FieldCondition, ConditionOperator
from ....core.value_objects.identifiers import ActionId

logger = logging.getLogger(__name__)


class EventActionRegistryService:
    """Service for managing event action registration and matching."""
    
    def __init__(
        self,
        repository: EventActionRepository,
        cache_ttl_seconds: int = 300,  # 5 minutes
        enable_cache: bool = True
    ):
        self._repository = repository
        self._cache_ttl_seconds = cache_ttl_seconds
        self._enable_cache = enable_cache
        
        # In-memory cache for fast lookups
        self._action_cache: Dict[str, List[EventAction]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._all_actions_cache: Optional[List[EventAction]] = None
        self._all_actions_cache_time: Optional[datetime] = None
        
        # Lock for cache operations
        self._cache_lock = asyncio.Lock()
    
    async def register_action(self, action: EventAction) -> None:
        """Register a new event action."""
        try:
            await self._repository.save(action)
            
            # Invalidate relevant caches
            await self._invalidate_cache()
            
            logger.info(
                f"Registered event action: {action.name} (ID: {action.id.value})",
                extra={
                    "action_id": str(action.id.value),
                    "handler_type": action.handler_type.value,
                    "event_types": action.event_types
                }
            )
        except Exception as e:
            logger.error(
                f"Failed to register event action: {action.name}",
                extra={
                    "action_id": str(action.id.value),
                    "error": str(e)
                }
            )
            raise
    
    async def unregister_action(self, action_id: ActionId) -> bool:
        """Unregister an event action."""
        try:
            success = await self._repository.delete(action_id)
            
            if success:
                # Invalidate relevant caches
                await self._invalidate_cache()
                
                logger.info(
                    f"Unregistered event action: {action_id.value}",
                    extra={"action_id": str(action_id.value)}
                )
            
            return success
        except Exception as e:
            logger.error(
                f"Failed to unregister event action: {action_id.value}",
                extra={
                    "action_id": str(action_id.value),
                    "error": str(e)
                }
            )
            raise
    
    async def get_actions_for_event(
        self, 
        event_type: str, 
        event_data: Dict[str, Any]
    ) -> List[EventAction]:
        """Get actions that match the given event with condition evaluation."""
        try:
            # Get candidate actions from repository or cache
            candidates = await self._get_candidate_actions(event_type, event_data)
            
            # Filter actions by evaluating conditions
            matching_actions = []
            for action in candidates:
                if await self._evaluate_action_conditions(action, event_data):
                    matching_actions.append(action)
            
            # Sort by priority (high to low)
            matching_actions.sort(key=lambda a: a.priority.value, reverse=True)
            
            logger.debug(
                f"Found {len(matching_actions)} matching actions for event: {event_type}",
                extra={
                    "event_type": event_type,
                    "candidates": len(candidates),
                    "matching": len(matching_actions)
                }
            )
            
            return matching_actions
            
        except Exception as e:
            logger.error(
                f"Failed to get actions for event: {event_type}",
                extra={
                    "event_type": event_type,
                    "error": str(e)
                }
            )
            raise
    
    async def reload_actions(self) -> None:
        """Reload actions from storage and clear cache."""
        await self._invalidate_cache()
        logger.info("Event action registry cache invalidated")
    
    async def get_action_by_id(self, action_id: ActionId) -> Optional[EventAction]:
        """Get a specific action by ID."""
        return await self._repository.get_by_id(action_id)
    
    async def update_action(self, action: EventAction) -> EventAction:
        """Update an existing action."""
        try:
            updated_action = await self._repository.update(action)
            
            # Invalidate relevant caches
            await self._invalidate_cache()
            
            logger.info(
                f"Updated event action: {action.name} (ID: {action.id.value})",
                extra={
                    "action_id": str(action.id.value),
                    "handler_type": action.handler_type.value
                }
            )
            
            return updated_action
        except Exception as e:
            logger.error(
                f"Failed to update event action: {action.name}",
                extra={
                    "action_id": str(action.id.value),
                    "error": str(e)
                }
            )
            raise
    
    async def get_actions_by_handler_type(self, handler_type: str) -> List[EventAction]:
        """Get actions by handler type."""
        return await self._repository.get_actions_by_handler_type(handler_type)
    
    async def get_active_actions(self) -> List[EventAction]:
        """Get all active actions."""
        if not self._enable_cache:
            return await self._repository.get_active_actions()
        
        async with self._cache_lock:
            now = datetime.utcnow()
            
            # Check if cache is valid
            if (self._all_actions_cache is not None and 
                self._all_actions_cache_time is not None and
                (now - self._all_actions_cache_time).total_seconds() < self._cache_ttl_seconds):
                return self._all_actions_cache.copy()
            
            # Refresh cache
            actions = await self._repository.get_active_actions()
            self._all_actions_cache = actions.copy()
            self._all_actions_cache_time = now
            
            return actions
    
    async def _get_candidate_actions(
        self, 
        event_type: str, 
        event_data: Dict[str, Any]
    ) -> List[EventAction]:
        """Get candidate actions from cache or repository."""
        if not self._enable_cache:
            return await self._repository.get_actions_for_event(
                event_type, 
                event_data.get("context_filters")
            )
        
        async with self._cache_lock:
            cache_key = f"event_type:{event_type}"
            now = datetime.utcnow()
            
            # Check if cache is valid
            if (cache_key in self._action_cache and 
                cache_key in self._cache_timestamps and
                (now - self._cache_timestamps[cache_key]).total_seconds() < self._cache_ttl_seconds):
                return self._action_cache[cache_key].copy()
            
            # Refresh cache
            actions = await self._repository.get_actions_for_event(
                event_type,
                event_data.get("context_filters")
            )
            
            self._action_cache[cache_key] = actions.copy()
            self._cache_timestamps[cache_key] = now
            
            return actions
    
    async def _evaluate_action_conditions(
        self, 
        action: EventAction, 
        event_data: Dict[str, Any]
    ) -> bool:
        """Evaluate if action conditions are satisfied by event data."""
        if not action.conditions:
            return True  # No conditions means action always matches
        
        try:
            for condition in action.conditions:
                if not await self._evaluate_condition(condition, event_data):
                    return False
            
            return True  # All conditions satisfied
            
        except Exception as e:
            logger.warning(
                f"Error evaluating conditions for action {action.id.value}: {str(e)}",
                extra={
                    "action_id": str(action.id.value),
                    "error": str(e)
                }
            )
            return False  # Default to not matching on error
    
    async def _evaluate_condition(
        self, 
        condition: ActionCondition, 
        event_data: Dict[str, Any]
    ) -> bool:
        """Evaluate a single condition."""
        if isinstance(condition, FieldCondition):
            return self._evaluate_field_condition(condition, event_data)
        
        # For composite conditions, would handle OR/AND logic here
        # For now, assume simple field conditions
        logger.warning(f"Unsupported condition type: {type(condition)}")
        return True
    
    def _evaluate_field_condition(
        self, 
        condition: FieldCondition, 
        event_data: Dict[str, Any]
    ) -> bool:
        """Evaluate a field-based condition."""
        try:
            # Extract field value from event data
            field_path = condition.field_path.split('.')
            value = event_data
            
            for path_part in field_path:
                if isinstance(value, dict) and path_part in value:
                    value = value[path_part]
                else:
                    # Field not found in event data
                    return False
            
            # Apply operator
            expected_value = condition.value
            
            if condition.operator == ConditionOperator.EQUALS:
                return value == expected_value
            elif condition.operator == ConditionOperator.NOT_EQUALS:
                return value != expected_value
            elif condition.operator == ConditionOperator.CONTAINS:
                return str(expected_value) in str(value)
            elif condition.operator == ConditionOperator.NOT_CONTAINS:
                return str(expected_value) not in str(value)
            elif condition.operator == ConditionOperator.GREATER_THAN:
                return self._safe_compare(value, expected_value, lambda a, b: a > b)
            elif condition.operator == ConditionOperator.LESS_THAN:
                return self._safe_compare(value, expected_value, lambda a, b: a < b)
            elif condition.operator == ConditionOperator.GREATER_THAN_OR_EQUAL:
                return self._safe_compare(value, expected_value, lambda a, b: a >= b)
            elif condition.operator == ConditionOperator.LESS_THAN_OR_EQUAL:
                return self._safe_compare(value, expected_value, lambda a, b: a <= b)
            elif condition.operator == ConditionOperator.IN:
                return value in expected_value if isinstance(expected_value, (list, tuple, set)) else False
            elif condition.operator == ConditionOperator.NOT_IN:
                return value not in expected_value if isinstance(expected_value, (list, tuple, set)) else True
            elif condition.operator == ConditionOperator.REGEX:
                import re
                pattern = str(expected_value)
                text = str(value)
                return bool(re.search(pattern, text))
            elif condition.operator == ConditionOperator.EXISTS:
                return True  # If we got here, the field exists
            elif condition.operator == ConditionOperator.NOT_EXISTS:
                return False  # If we got here, the field exists
            else:
                logger.warning(f"Unsupported operator: {condition.operator}")
                return False
                
        except Exception as e:
            logger.warning(
                f"Error evaluating field condition: {str(e)}",
                extra={
                    "field_path": condition.field_path,
                    "operator": condition.operator.value,
                    "error": str(e)
                }
            )
            return False
    
    def _safe_compare(self, a: Any, b: Any, comparator) -> bool:
        """Safely compare values with type conversion."""
        try:
            # Try direct comparison first
            return comparator(a, b)
        except TypeError:
            try:
                # Try converting to same type
                if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                    return comparator(float(a), float(b))
                elif isinstance(a, str) and isinstance(b, str):
                    return comparator(a, b)
                else:
                    # Convert both to strings for comparison
                    return comparator(str(a), str(b))
            except Exception:
                return False
    
    async def _invalidate_cache(self) -> None:
        """Invalidate all caches."""
        async with self._cache_lock:
            self._action_cache.clear()
            self._cache_timestamps.clear()
            self._all_actions_cache = None
            self._all_actions_cache_time = None
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        async with self._cache_lock:
            now = datetime.utcnow()
            valid_entries = 0
            
            for cache_key, timestamp in self._cache_timestamps.items():
                if (now - timestamp).total_seconds() < self._cache_ttl_seconds:
                    valid_entries += 1
            
            return {
                "enabled": self._enable_cache,
                "ttl_seconds": self._cache_ttl_seconds,
                "total_entries": len(self._action_cache),
                "valid_entries": valid_entries,
                "expired_entries": len(self._action_cache) - valid_entries,
                "all_actions_cached": self._all_actions_cache is not None,
                "all_actions_cache_age_seconds": (
                    (now - self._all_actions_cache_time).total_seconds()
                    if self._all_actions_cache_time else None
                )
            }