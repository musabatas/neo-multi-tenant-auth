"""Platform actions application handlers.

Application layer handlers for action lifecycle events and notifications.
Each handler focuses on single responsibility following maximum separation architecture.

Handlers:
- action_executed_handler.py: ONLY post-execution action processing
- action_failed_handler.py: ONLY failed action processing and recovery

Pure application layer - no infrastructure concerns.
"""

from .action_executed_handler import (
    ActionExecutedHandler,
    ActionExecutedHandlerResult,
    ResultAnalysisType,
    create_action_executed_handler
)

from .action_failed_handler import (
    ActionFailedHandler,
    ActionFailedHandlerResult,
    FailureAnalysisType,
    FailureSeverity,
    create_action_failed_handler
)

__all__ = [
    # Action Executed Handler
    "ActionExecutedHandler",
    "ActionExecutedHandlerResult",
    "ResultAnalysisType",
    "create_action_executed_handler",
    
    # Action Failed Handler
    "ActionFailedHandler",
    "ActionFailedHandlerResult",
    "FailureAnalysisType",
    "FailureSeverity",
    "create_action_failed_handler",
]