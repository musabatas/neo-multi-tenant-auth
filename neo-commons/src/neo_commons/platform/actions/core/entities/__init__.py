"""Action core entities exports.

ONLY handles action domain entities with maximum separation.
"""

from .action import Action
from .action_execution import ActionExecution

__all__ = [
    "Action",
    "ActionExecution",
]