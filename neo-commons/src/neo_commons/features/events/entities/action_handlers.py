"""
Event Action Handler Protocol and Base Implementations

This module defines the protocol for event action handlers and provides
base implementations for common handler functionality.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Protocol, runtime_checkable
from dataclasses import dataclass
from enum import Enum

from ....core.value_objects.identifiers import ActionId, ActionExecutionId
from .event_action import EventAction, ExecutionMode, HandlerResult


class HandlerStatus(str, Enum):
    """Status of a handler."""
    REGISTERED = "registered"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass(frozen=True)
class ExecutionContext:
    """Context for action execution."""
    execution_id: ActionExecutionId
    action_id: ActionId
    event_type: str
    event_data: Dict[str, Any]
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    execution_metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.execution_metadata is None:
            object.__setattr__(self, 'execution_metadata', {})


@runtime_checkable
class EventActionHandler(Protocol):
    """Protocol for event action handlers."""
    
    @property
    def handler_type(self) -> str:
        """Type identifier for this handler."""
        ...
    
    @property
    def status(self) -> HandlerStatus:
        """Current status of the handler."""
        ...
    
    def can_handle(self, action: EventAction) -> bool:
        """Check if this handler can process the given action."""
        ...
    
    async def execute(
        self, 
        action: EventAction, 
        context: ExecutionContext
    ) -> HandlerResult:
        """Execute the action with given context."""
        ...
    
    async def validate_configuration(self, configuration: Dict[str, Any]) -> List[str]:
        """Validate action configuration. Returns list of validation errors."""
        ...
    
    async def get_default_configuration(self) -> Dict[str, Any]:
        """Get default configuration for this handler type."""
        ...


@runtime_checkable
class AsyncEventActionHandler(EventActionHandler, Protocol):
    """Protocol for asynchronous event action handlers."""
    
    async def execute_async(
        self, 
        action: EventAction, 
        context: ExecutionContext
    ) -> ActionExecutionId:
        """Execute action asynchronously and return execution ID for tracking."""
        ...
    
    async def get_execution_status(self, execution_id: ActionExecutionId) -> HandlerResult:
        """Get the status of an async execution."""
        ...


class BaseEventActionHandler(ABC):
    """Base class for event action handlers."""
    
    def __init__(self, handler_type: str):
        self._handler_type = handler_type
        self._status = HandlerStatus.REGISTERED
    
    @property
    def handler_type(self) -> str:
        """Type identifier for this handler."""
        return self._handler_type
    
    @property
    def status(self) -> HandlerStatus:
        """Current status of the handler."""
        return self._status
    
    def can_handle(self, action: EventAction) -> bool:
        """Check if this handler can process the given action."""
        return (
            action.handler_type == self.handler_type and 
            self.status == HandlerStatus.REGISTERED
        )
    
    @abstractmethod
    async def execute(
        self, 
        action: EventAction, 
        context: ExecutionContext
    ) -> HandlerResult:
        """Execute the action with given context."""
        pass
    
    async def validate_configuration(self, configuration: Dict[str, Any]) -> List[str]:
        """Validate action configuration. Override in subclasses."""
        return []
    
    async def get_default_configuration(self) -> Dict[str, Any]:
        """Get default configuration for this handler type."""
        return {}
    
    def _set_status(self, status: HandlerStatus):
        """Set handler status (for internal use)."""
        self._status = status
    
    def _validate_required_fields(
        self, 
        configuration: Dict[str, Any], 
        required_fields: List[str]
    ) -> List[str]:
        """Helper method to validate required configuration fields."""
        errors = []
        for field in required_fields:
            if field not in configuration:
                errors.append(f"Missing required field: {field}")
            elif configuration[field] is None or configuration[field] == "":
                errors.append(f"Field cannot be empty: {field}")
        return errors
    
    def _create_success_result(
        self, 
        message: str = "Action executed successfully",
        metadata: Optional[Dict[str, Any]] = None
    ) -> HandlerResult:
        """Create a successful result."""
        return HandlerResult(
            success=True,
            message=message,
            metadata=metadata or {}
        )
    
    def _create_error_result(
        self, 
        error: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> HandlerResult:
        """Create an error result."""
        return HandlerResult(
            success=False,
            error=error,
            metadata=metadata or {}
        )


class BaseAsyncEventActionHandler(BaseEventActionHandler):
    """Base class for asynchronous event action handlers."""
    
    def __init__(self, handler_type: str):
        super().__init__(handler_type)
        self._executions: Dict[str, HandlerResult] = {}
    
    async def execute_async(
        self, 
        action: EventAction, 
        context: ExecutionContext
    ) -> ActionExecutionId:
        """Execute action asynchronously and return execution ID for tracking."""
        # Store initial pending status
        self._executions[str(context.execution_id)] = HandlerResult(
            success=None,  # Pending
            message="Execution in progress"
        )
        
        try:
            # Execute the action
            result = await self.execute(action, context)
            self._executions[str(context.execution_id)] = result
            return context.execution_id
        except Exception as e:
            error_result = HandlerResult(
                success=False,
                error=f"Async execution failed: {str(e)}"
            )
            self._executions[str(context.execution_id)] = error_result
            return context.execution_id
    
    async def get_execution_status(self, execution_id: ActionExecutionId) -> HandlerResult:
        """Get the status of an async execution."""
        execution_key = str(execution_id)
        if execution_key not in self._executions:
            return HandlerResult(
                success=False,
                error="Execution not found"
            )
        
        return self._executions[execution_key]


@runtime_checkable
class HandlerRegistry(Protocol):
    """Protocol for handler registry."""
    
    async def register_handler(self, handler: EventActionHandler) -> bool:
        """Register a new handler."""
        ...
    
    async def unregister_handler(self, handler_type: str) -> bool:
        """Unregister a handler by type."""
        ...
    
    async def get_handler(self, handler_type: str) -> Optional[EventActionHandler]:
        """Get a handler by type."""
        ...
    
    async def list_handlers(self) -> List[EventActionHandler]:
        """List all registered handlers."""
        ...
    
    async def get_supported_types(self) -> List[str]:
        """Get list of supported handler types."""
        ...


class SimpleHandlerRegistry:
    """Simple in-memory handler registry implementation."""
    
    def __init__(self):
        self._handlers: Dict[str, EventActionHandler] = {}
    
    async def register_handler(self, handler: EventActionHandler) -> bool:
        """Register a new handler."""
        try:
            self._handlers[handler.handler_type] = handler
            return True
        except Exception:
            return False
    
    async def unregister_handler(self, handler_type: str) -> bool:
        """Unregister a handler by type."""
        try:
            if handler_type in self._handlers:
                del self._handlers[handler_type]
                return True
            return False
        except Exception:
            return False
    
    async def get_handler(self, handler_type: str) -> Optional[EventActionHandler]:
        """Get a handler by type."""
        return self._handlers.get(handler_type)
    
    async def list_handlers(self) -> List[EventActionHandler]:
        """List all registered handlers."""
        return list(self._handlers.values())
    
    async def get_supported_types(self) -> List[str]:
        """Get list of supported handler types."""
        return list(self._handlers.keys())