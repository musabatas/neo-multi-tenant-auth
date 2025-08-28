"""Action value objects for platform actions infrastructure.

This module contains immutable value objects that represent action concepts
with built-in validation and business logic.
"""

from .action_condition import ActionCondition
from .action_execution_id import ActionExecutionId
from .action_id import ActionId
from .action_priority import ActionPriority
from .action_result import ActionResult, ActionResultStatus
from .action_status import ActionStatus
from .execution_mode import ExecutionMode
from .handler_type import HandlerType

__all__ = [
    # Action identifiers
    "ActionId",
    "ActionExecutionId",
    
    # Action configuration
    "ActionCondition",
    "ActionPriority",
    "ActionStatus",
    "ExecutionMode",
    "HandlerType",
    
    # Action results
    "ActionResult",
    "ActionResultStatus",
]