"""Action exceptions for platform actions infrastructure.

This module contains exception classes for action-related operations
following maximum separation architecture.
"""

from .action_execution_failed import ActionExecutionFailed
from .invalid_action_configuration import InvalidActionConfiguration

__all__ = [
    "ActionExecutionFailed",
    "InvalidActionConfiguration",
]