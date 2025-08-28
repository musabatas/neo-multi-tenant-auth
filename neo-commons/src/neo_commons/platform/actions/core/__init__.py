"""Action core components for platform actions infrastructure.

This module contains the core domain components for actions including
entities, value objects, exceptions, and shared contracts.
"""

from .entities import Action, ActionExecution
from .value_objects import (
    ActionCondition,
    ActionExecutionId,
    ActionId,
    ActionPriority,
    ActionResult,
    ActionResultStatus,
    ActionStatus,
    ExecutionMode,
    HandlerType,
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