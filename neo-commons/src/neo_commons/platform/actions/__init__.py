"""Platform Actions Module.

Enterprise-grade action execution system with configurable triggers, 
handlers, and comprehensive execution tracking. Supports webhook delivery, 
email notifications, function execution, and custom handlers.

This module provides:
- Action domain entities with lifecycle management
- Value objects for configuration and results
- Execution tracking with performance metrics
- Flexible trigger conditions and priorities
- Multiple execution modes (sync, async, queued)
- Comprehensive error handling and retry logic

Pure platform infrastructure - used by all business features.
"""

from .core import (
    # Entities
    Action,
    ActionExecution,
    
    # Value Objects - Identifiers
    ActionId,
    ActionExecutionId,
    
    # Value Objects - Configuration
    ActionCondition,
    ActionPriority,
    ActionStatus,
    ExecutionMode,
    HandlerType,
    
    # Value Objects - Results
    ActionResult,
    ActionResultStatus,
)

__all__ = [
    # Entities
    "Action",
    "ActionExecution",
    
    # Value Objects - Identifiers
    "ActionId",
    "ActionExecutionId",
    
    # Value Objects - Configuration
    "ActionCondition",
    "ActionPriority",
    "ActionStatus",
    "ExecutionMode",
    "HandlerType",
    
    # Value Objects - Results
    "ActionResult",
    "ActionResultStatus",
]