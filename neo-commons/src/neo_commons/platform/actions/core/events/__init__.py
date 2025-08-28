"""Action events for platform actions infrastructure.

This module contains event classes for action-related operations
following maximum separation architecture.
"""

from .action_executed import ActionExecuted
from .action_failed import ActionFailed

__all__ = [
    "ActionExecuted",
    "ActionFailed",
]