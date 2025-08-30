"""Base ActionHandler class for all action implementations."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from ..protocols.action_executor import ExecutionContext, ExecutionResult


class ActionHandler(ABC):
    """
    Abstract base class for all action handlers.
    
    This class provides the basic interface that all action handlers must implement.
    Each handler is responsible for executing a specific type of action (email, SMS, webhook, etc.).
    """
    
    @property
    @abstractmethod
    def handler_name(self) -> str:
        """Return the unique name of this handler."""
        pass
    
    @property
    @abstractmethod
    def handler_version(self) -> str:
        """Return the version of this handler."""
        pass
    
    @property
    @abstractmethod
    def supported_action_types(self) -> list[str]:
        """Return the list of action types this handler supports."""
        pass
    
    @abstractmethod
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate the configuration for this handler.
        
        Args:
            config: Handler-specific configuration
            
        Returns:
            True if configuration is valid, False otherwise
            
        Raises:
            ValueError: If configuration is invalid with specific error message
        """
        pass
    
    @abstractmethod
    async def execute(
        self, 
        config: Dict[str, Any], 
        input_data: Dict[str, Any], 
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute the action with given configuration and input data.
        
        Args:
            config: Handler-specific configuration (from Action.config)
            input_data: Input data for the action (from Event.event_data)
            context: Execution context with schema, event, tenant info
            
        Returns:
            ExecutionResult with success status and output data
            
        Raises:
            Exception: Any execution errors will be caught by the executor
        """
        pass
    
    @abstractmethod
    async def get_execution_timeout(self, config: Dict[str, Any]) -> int:
        """
        Get the execution timeout for this handler in seconds.
        
        Args:
            config: Handler-specific configuration
            
        Returns:
            Timeout in seconds
        """
        pass
    
    async def prepare_execution(
        self, 
        config: Dict[str, Any], 
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Prepare execution environment for the action.
        
        This method is called before execute() and can be used to:
        - Set up connections
        - Validate prerequisites  
        - Prepare temporary resources
        
        Args:
            config: Handler-specific configuration
            context: Execution context
            
        Returns:
            Preparation metadata (connections, temporary resources, etc.)
        """
        return {}
    
    async def cleanup_execution(
        self, 
        config: Dict[str, Any], 
        context: ExecutionContext,
        preparation_metadata: Dict[str, Any]
    ) -> None:
        """
        Clean up after action execution.
        
        This method is called after execute() (whether successful or not) and can be used to:
        - Close connections
        - Clean up temporary resources
        - Perform final logging
        
        Args:
            config: Handler-specific configuration
            context: Execution context
            preparation_metadata: Metadata from prepare_execution()
        """
        pass
    
    async def health_check(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform health check for this handler.
        
        Args:
            config: Handler-specific configuration
            
        Returns:
            Health status dictionary with:
            - healthy: bool
            - status: str (description)
            - details: Dict[str, Any] (additional details)
        """
        return {
            "healthy": True,
            "status": "Handler is operational",
            "details": {}
        }
    
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get the JSON schema for this handler's configuration.
        
        Returns:
            JSON schema dictionary describing required/optional config fields
        """
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    def get_input_schema(self) -> Dict[str, Any]:
        """
        Get the JSON schema for this handler's input data.
        
        Returns:
            JSON schema dictionary describing expected input data format
        """
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """
        Get the JSON schema for this handler's output data.
        
        Returns:
            JSON schema dictionary describing output data format
        """
        return {
            "type": "object", 
            "properties": {
                "success": {"type": "boolean"},
                "message": {"type": "string"}
            },
            "required": ["success"]
        }
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name={self.handler_name}, version={self.handler_version})"
    
    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}(name={self.handler_name!r}, "
                f"version={self.handler_version!r}, "
                f"action_types={self.supported_action_types!r})")