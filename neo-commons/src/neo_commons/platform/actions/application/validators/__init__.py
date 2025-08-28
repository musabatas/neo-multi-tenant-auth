"""Action validators for platform actions infrastructure.

This module provides validation operations for actions following maximum separation architecture.
Each validator handles specific validation responsibilities for action integrity and business rules.
"""

from .action_validator import (
    ActionValidationResult,
    ActionValidator
)

__all__ = [
    "ActionValidationResult",
    "ActionValidator"
]