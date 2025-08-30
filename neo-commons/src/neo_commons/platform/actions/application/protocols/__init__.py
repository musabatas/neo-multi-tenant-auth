"""Actions application protocols."""

from .action_repository import ActionRepositoryProtocol
from .action_execution_repository import ActionExecutionRepositoryProtocol
from .event_action_subscription_repository import EventActionSubscriptionRepositoryProtocol
from .action_executor import ActionExecutorProtocol, ExecutionContext, ExecutionResult
from .action_dispatcher import ActionDispatcherProtocol

__all__ = [
    # Repository Protocols
    "ActionRepositoryProtocol",
    "ActionExecutionRepositoryProtocol",
    "EventActionSubscriptionRepositoryProtocol",
    
    # Execution Protocols
    "ActionExecutorProtocol", 
    "ExecutionContext",
    "ExecutionResult",
    
    # Dispatcher Protocols
    "ActionDispatcherProtocol",
]