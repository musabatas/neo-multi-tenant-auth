"""Action executor protocol for action execution."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

from ...domain.entities.action import Action
from ...domain.entities.action_execution import ActionExecution
from ....events.domain.entities.event import Event


@dataclass
class ExecutionContext:
    """Context information for action execution."""
    schema: str
    event: Event
    tenant_id: Optional[str] = None
    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    worker_id: Optional[str] = None
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None


@dataclass
class ExecutionResult:
    """Result of action execution."""
    success: bool
    output_data: Dict[str, Any]
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[int] = None
    memory_usage_mb: Optional[int] = None
    cpu_time_ms: Optional[int] = None


class ActionExecutorProtocol(ABC):
    """Protocol for action execution."""
    
    @abstractmethod
    async def execute(
        self, 
        action: Action, 
        context: ExecutionContext,
        input_data: Dict[str, Any]
    ) -> ExecutionResult:
        """
        Execute an action with given context and input data.
        
        Args:
            action: Action to execute
            context: Execution context with event and schema info
            input_data: Input data for the action
            
        Returns:
            Execution result with success status and output/error data
            
        Raises:
            ActionExecutionError: If execution fails critically
        """
        ...
    
    @abstractmethod
    async def validate_action(self, action: Action) -> bool:
        """
        Validate if this executor can handle the action.
        
        Args:
            action: Action to validate
            
        Returns:
            True if executor can handle this action, False otherwise
        """
        ...
    
    @abstractmethod
    async def get_execution_timeout(self, action: Action) -> int:
        """
        Get the execution timeout for an action in seconds.
        
        Args:
            action: Action to get timeout for
            
        Returns:
            Timeout in seconds
        """
        ...
    
    @abstractmethod
    async def prepare_execution(
        self, 
        action: Action, 
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Prepare execution environment for the action.
        
        Args:
            action: Action to prepare for
            context: Execution context
            
        Returns:
            Preparation metadata (connection info, temporary resources, etc.)
        """
        ...
    
    @abstractmethod
    async def cleanup_execution(
        self, 
        action: Action, 
        context: ExecutionContext,
        preparation_metadata: Dict[str, Any]
    ) -> None:
        """
        Clean up after action execution.
        
        Args:
            action: Action that was executed
            context: Execution context
            preparation_metadata: Metadata from prepare_execution
        """
        ...
    
    @abstractmethod
    def get_supported_action_types(self) -> list[str]:
        """
        Get list of action types this executor supports.
        
        Returns:
            List of supported action type strings
        """
        ...