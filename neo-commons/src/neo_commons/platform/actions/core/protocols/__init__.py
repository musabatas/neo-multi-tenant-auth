"""Action protocols for platform actions infrastructure.

This module contains protocol contracts for action-related operations
following maximum separation architecture and dependency injection patterns.
"""

from .action_executor import ActionExecutor
from .action_repository import ActionRepository

__all__ = [
    "ActionExecutor",
    "ActionRepository",
]