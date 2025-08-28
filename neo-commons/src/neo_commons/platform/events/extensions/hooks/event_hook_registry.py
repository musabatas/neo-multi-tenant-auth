"""
Event hook registry for managing lifecycle hooks.

ONLY handles hook registration, execution, and lifecycle management.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

from ....core.value_objects import EventId, TenantId, EventType


class HookStage(Enum):
    """Event processing hook stages."""
    PRE_VALIDATION = "pre_validation"
    POST_VALIDATION = "post_validation" 
    PRE_PROCESSING = "pre_processing"
    POST_PROCESSING = "post_processing"
    PRE_ACTION = "pre_action"
    POST_ACTION = "post_action"
    ON_SUCCESS = "on_success"
    ON_ERROR = "on_error"
    ON_RETRY = "on_retry"


class HookPriority(Enum):
    """Hook execution priorities."""
    HIGHEST = 0
    HIGH = 100
    NORMAL = 500
    LOW = 900
    LOWEST = 1000


@dataclass
class HookContext:
    """Context passed to hooks during execution."""
    event_id: EventId
    tenant_id: TenantId
    event_type: EventType
    event_data: Dict[str, Any]
    stage: HookStage
    metadata: Dict[str, Any]
    processing_start_time: float
    current_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id.value,
            "tenant_id": self.tenant_id.value,
            "event_type": self.event_type.value,
            "event_data": self.event_data,
            "stage": self.stage.value,
            "metadata": self.metadata,
            "processing_start_time": self.processing_start_time,
            "current_time": self.current_time,
        }


@dataclass
class HookResult:
    """Result from hook execution."""
    success: bool = True
    continue_processing: bool = True
    modified_data: Optional[Dict[str, Any]] = None
    additional_metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "continue_processing": self.continue_processing,
            "modified_data": self.modified_data,
            "additional_metadata": self.additional_metadata,
            "error_message": self.error_message,
        }


@dataclass
class RegisteredHook:
    """Registered hook information."""
    name: str
    hook_function: Callable[[HookContext], Awaitable[HookResult]]
    stage: HookStage
    priority: HookPriority
    event_types: List[str]  # Empty list means all event types
    enabled: bool = True
    
    def matches_event_type(self, event_type: str) -> bool:
        """Check if hook matches event type."""
        if not self.event_types:
            return True  # Empty list means all event types
        return event_type in self.event_types


class EventHookRegistry:
    """
    Registry for managing event processing hooks.
    
    Provides registration, execution, and lifecycle management of hooks.
    """
    
    def __init__(self):
        self._hooks: Dict[HookStage, List[RegisteredHook]] = defaultdict(list)
        self._hook_stats: Dict[str, Dict[str, Any]] = {}
        self._logger = logging.getLogger(__name__)
        
    def register_hook(
        self,
        name: str,
        hook_function: Callable[[HookContext], Awaitable[HookResult]],
        stage: HookStage,
        priority: HookPriority = HookPriority.NORMAL,
        event_types: Optional[List[str]] = None
    ) -> None:
        """
        Register a hook for a specific stage.
        
        Args:
            name: Unique hook name
            hook_function: Async function to execute
            stage: Processing stage to attach to
            priority: Execution priority
            event_types: List of event types (None means all)
        """
        # Check for duplicate names
        existing_hook = self._find_hook_by_name(name)
        if existing_hook:
            self._logger.warning(f"Hook '{name}' already registered, replacing")
            self.unregister_hook(name)
            
        hook = RegisteredHook(
            name=name,
            hook_function=hook_function,
            stage=stage,
            priority=priority,
            event_types=event_types or [],
            enabled=True
        )
        
        self._hooks[stage].append(hook)
        self._sort_hooks_by_priority(stage)
        
        # Initialize stats
        self._hook_stats[name] = {
            "executions": 0,
            "successes": 0,
            "failures": 0,
            "total_time_ms": 0.0,
            "average_time_ms": 0.0,
        }
        
        self._logger.info(f"Registered hook '{name}' for stage {stage.value}")
        
    def unregister_hook(self, name: str) -> bool:
        """
        Unregister a hook by name.
        
        Args:
            name: Hook name to remove
            
        Returns:
            True if hook was found and removed
        """
        for stage, hooks in self._hooks.items():
            for i, hook in enumerate(hooks):
                if hook.name == name:
                    removed_hook = hooks.pop(i)
                    self._logger.info(f"Unregistered hook '{name}' from stage {stage.value}")
                    
                    # Clean up stats
                    if name in self._hook_stats:
                        del self._hook_stats[name]
                        
                    return True
                    
        return False
        
    def enable_hook(self, name: str) -> bool:
        """
        Enable a hook by name.
        
        Args:
            name: Hook name to enable
            
        Returns:
            True if hook was found and enabled
        """
        hook = self._find_hook_by_name(name)
        if hook:
            hook.enabled = True
            self._logger.info(f"Enabled hook '{name}'")
            return True
        return False
        
    def disable_hook(self, name: str) -> bool:
        """
        Disable a hook by name.
        
        Args:
            name: Hook name to disable
            
        Returns:
            True if hook was found and disabled
        """
        hook = self._find_hook_by_name(name)
        if hook:
            hook.enabled = False
            self._logger.info(f"Disabled hook '{name}'")
            return True
        return False
        
    async def execute_hooks(
        self,
        context: HookContext,
        timeout_seconds: float = 30.0
    ) -> List[HookResult]:
        """
        Execute all hooks for a specific stage.
        
        Args:
            context: Hook execution context
            timeout_seconds: Maximum execution time
            
        Returns:
            List of hook results
        """
        stage = context.stage
        applicable_hooks = [
            hook for hook in self._hooks[stage]
            if hook.enabled and hook.matches_event_type(context.event_type.value)
        ]
        
        if not applicable_hooks:
            return []
            
        self._logger.debug(f"Executing {len(applicable_hooks)} hooks for stage {stage.value}")
        
        results = []
        for hook in applicable_hooks:
            try:
                start_time = asyncio.get_event_loop().time()
                
                # Execute hook with timeout
                result = await asyncio.wait_for(
                    hook.hook_function(context),
                    timeout=timeout_seconds
                )
                
                execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
                
                # Update statistics
                self._update_hook_stats(hook.name, True, execution_time)
                
                results.append(result)
                
                # If hook says to stop processing, break early
                if not result.continue_processing:
                    self._logger.info(f"Hook '{hook.name}' requested processing stop")
                    break
                    
            except asyncio.TimeoutError:
                error_msg = f"Hook '{hook.name}' timed out after {timeout_seconds}s"
                self._logger.error(error_msg)
                self._update_hook_stats(hook.name, False, timeout_seconds * 1000)
                
                results.append(HookResult(
                    success=False,
                    continue_processing=True,  # Continue despite timeout
                    error_message=error_msg
                ))
                
            except Exception as e:
                error_msg = f"Hook '{hook.name}' failed: {str(e)}"
                self._logger.error(error_msg, exc_info=True)
                self._update_hook_stats(hook.name, False, 0)
                
                results.append(HookResult(
                    success=False,
                    continue_processing=True,  # Continue despite error
                    error_message=error_msg
                ))
                
        return results
        
    def get_hook_stats(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get hook execution statistics.
        
        Args:
            name: Specific hook name, or None for all hooks
            
        Returns:
            Hook statistics
        """
        if name:
            return self._hook_stats.get(name, {})
        return dict(self._hook_stats)
        
    def list_hooks(self, stage: Optional[HookStage] = None) -> List[Dict[str, Any]]:
        """
        List registered hooks.
        
        Args:
            stage: Specific stage, or None for all stages
            
        Returns:
            List of hook information
        """
        hooks = []
        
        stages_to_check = [stage] if stage else list(HookStage)
        
        for check_stage in stages_to_check:
            for hook in self._hooks[check_stage]:
                hooks.append({
                    "name": hook.name,
                    "stage": hook.stage.value,
                    "priority": hook.priority.value,
                    "event_types": hook.event_types,
                    "enabled": hook.enabled,
                })
                
        return hooks
        
    def clear_hooks(self, stage: Optional[HookStage] = None) -> int:
        """
        Clear hooks from specific stage or all stages.
        
        Args:
            stage: Specific stage to clear, or None for all
            
        Returns:
            Number of hooks cleared
        """
        cleared_count = 0
        
        if stage:
            cleared_count = len(self._hooks[stage])
            self._hooks[stage].clear()
            self._logger.info(f"Cleared {cleared_count} hooks from stage {stage.value}")
        else:
            for stage_hooks in self._hooks.values():
                cleared_count += len(stage_hooks)
                stage_hooks.clear()
            self._hook_stats.clear()
            self._logger.info(f"Cleared all {cleared_count} hooks")
            
        return cleared_count
        
    def _find_hook_by_name(self, name: str) -> Optional[RegisteredHook]:
        """Find a hook by name across all stages."""
        for hooks in self._hooks.values():
            for hook in hooks:
                if hook.name == name:
                    return hook
        return None
        
    def _sort_hooks_by_priority(self, stage: HookStage) -> None:
        """Sort hooks in a stage by priority."""
        self._hooks[stage].sort(key=lambda h: h.priority.value)
        
    def _update_hook_stats(self, name: str, success: bool, execution_time_ms: float) -> None:
        """Update hook execution statistics."""
        if name not in self._hook_stats:
            return
            
        stats = self._hook_stats[name]
        stats["executions"] += 1
        
        if success:
            stats["successes"] += 1
        else:
            stats["failures"] += 1
            
        stats["total_time_ms"] += execution_time_ms
        stats["average_time_ms"] = stats["total_time_ms"] / stats["executions"]