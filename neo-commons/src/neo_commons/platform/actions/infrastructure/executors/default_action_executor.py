"""Default action executor implementation."""

import asyncio
import importlib
import traceback
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from ...domain.entities.action import Action, ActionStatus
from ...domain.entities.action_execution import ActionExecution
from ...application.protocols.action_executor import ActionExecutorProtocol, ExecutionContext, ExecutionResult
from ...application.handlers.action_handler import ActionHandler


class ActionExecutionError(Exception):
    """Raised when action execution fails critically."""
    pass


class HandlerLoadError(Exception):
    """Raised when action handler cannot be loaded."""
    pass


class DefaultActionExecutor(ActionExecutorProtocol):
    """
    Default implementation of ActionExecutorProtocol.
    
    This executor loads action handlers dynamically by their class path,
    validates configurations, and executes actions with proper error handling.
    """
    
    def __init__(self):
        self._handler_cache: Dict[str, ActionHandler] = {}
        self._timeout_tasks: Dict[str, asyncio.Task] = {}
    
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
        start_time = datetime.now(timezone.utc)
        
        try:
            # Load and cache handler
            handler = await self._get_handler(action.handler_class)
            
            # Validate handler can handle this action
            if not await self.validate_action(action):
                raise ActionExecutionError(f"Handler {action.handler_class} cannot handle action type {action.action_type}")
            
            # Prepare execution environment
            preparation_metadata = await handler.prepare_execution(action.config, context)
            
            try:
                # Get execution timeout
                timeout_seconds = await handler.get_execution_timeout(action.config)
                
                # Execute with timeout
                execution_task = asyncio.create_task(
                    handler.execute(action.config, input_data, context)
                )
                
                # Store task for potential cancellation
                execution_id = str(context.event.id)
                self._timeout_tasks[execution_id] = execution_task
                
                try:
                    result = await asyncio.wait_for(execution_task, timeout=timeout_seconds)
                    
                    # Calculate execution time
                    end_time = datetime.now(timezone.utc)
                    execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
                    
                    # Ensure ExecutionResult format
                    if not isinstance(result, ExecutionResult):
                        # Handler returned raw dict, convert to ExecutionResult
                        result = ExecutionResult(
                            success=True,
                            output_data=result if isinstance(result, dict) else {"result": result},
                            execution_time_ms=execution_time_ms
                        )
                    else:
                        # Update execution time if not set
                        if result.execution_time_ms is None:
                            result.execution_time_ms = execution_time_ms
                    
                    return result
                    
                except asyncio.TimeoutError:
                    # Cancel the execution task
                    execution_task.cancel()
                    try:
                        await execution_task
                    except asyncio.CancelledError:
                        pass
                    
                    execution_time_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                    return ExecutionResult(
                        success=False,
                        output_data={},
                        error_message=f"Action execution timed out after {timeout_seconds} seconds",
                        error_details={"timeout_seconds": timeout_seconds},
                        execution_time_ms=execution_time_ms
                    )
                
                finally:
                    # Clean up timeout task
                    self._timeout_tasks.pop(execution_id, None)
            
            finally:
                # Always cleanup execution environment
                try:
                    await handler.cleanup_execution(action.config, context, preparation_metadata)
                except Exception as cleanup_error:
                    # Log cleanup errors but don't fail the execution
                    print(f"Warning: Cleanup failed for action {action.id}: {cleanup_error}")
        
        except Exception as e:
            execution_time_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            error_message = str(e)
            error_details = {
                "error_type": type(e).__name__,
                "handler_class": action.handler_class
            }
            
            # Add stack trace for debugging
            stack_trace = traceback.format_exc()
            
            return ExecutionResult(
                success=False,
                output_data={},
                error_message=error_message,
                error_details=error_details,
                execution_time_ms=execution_time_ms
            )
    
    async def validate_action(self, action: Action) -> bool:
        """
        Validate if this executor can handle the action.
        
        Args:
            action: Action to validate
            
        Returns:
            True if executor can handle this action, False otherwise
        """
        try:
            # Try to load the handler
            handler = await self._get_handler(action.handler_class)
            
            # Check if handler supports this action type
            if action.action_type.value not in handler.supported_action_types:
                return False
            
            # Validate handler configuration
            return await handler.validate_config(action.config)
            
        except Exception:
            return False
    
    async def get_execution_timeout(self, action: Action) -> int:
        """
        Get the execution timeout for an action in seconds.
        
        Args:
            action: Action to get timeout for
            
        Returns:
            Timeout in seconds
        """
        try:
            handler = await self._get_handler(action.handler_class)
            return await handler.get_execution_timeout(action.config)
        except Exception:
            # Fallback to action's timeout setting
            return action.timeout_seconds
    
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
        try:
            handler = await self._get_handler(action.handler_class)
            return await handler.prepare_execution(action.config, context)
        except Exception as e:
            return {"preparation_error": str(e)}
    
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
        try:
            handler = await self._get_handler(action.handler_class)
            await handler.cleanup_execution(action.config, context, preparation_metadata)
        except Exception as e:
            # Log cleanup errors but don't raise
            print(f"Warning: Cleanup failed for action {action.id}: {e}")
    
    def get_supported_action_types(self) -> list[str]:
        """
        Get list of action types this executor supports.
        
        Returns:
            List of supported action type strings
        """
        # This executor supports all action types through dynamic handler loading
        return [
            "email", "sms", "push_notification", "webhook", "slack_notification",
            "database_operation", "function_execution", "background_job", 
            "cache_invalidation", "security_scan", "external_api", "crm_sync",
            "analytics_tracking", "report_generation", "backup_operation"
        ]
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """
        Cancel a running execution.
        
        Args:
            execution_id: Execution ID to cancel
            
        Returns:
            True if cancelled, False if not found or already completed
        """
        task = self._timeout_tasks.get(execution_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            return True
        return False
    
    async def get_handler_health(self, handler_class: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get health status for a specific handler.
        
        Args:
            handler_class: Handler class path
            config: Handler configuration
            
        Returns:
            Health status dictionary
        """
        try:
            handler = await self._get_handler(handler_class)
            return await handler.health_check(config)
        except Exception as e:
            return {
                "healthy": False,
                "status": f"Handler load failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    # Private methods
    
    async def _get_handler(self, handler_class: str) -> ActionHandler:
        """
        Get handler instance, loading and caching if necessary.
        
        Args:
            handler_class: Full Python class path (e.g., 'handlers.email.SendGridEmailHandler')
            
        Returns:
            Handler instance
            
        Raises:
            HandlerLoadError: If handler cannot be loaded
        """
        if handler_class not in self._handler_cache:
            try:
                # Parse module and class name
                if '.' not in handler_class:
                    raise HandlerLoadError(f"Invalid handler class path: {handler_class}")
                
                module_path, class_name = handler_class.rsplit('.', 1)
                
                # Import the module
                module = importlib.import_module(module_path)
                
                # Get the handler class
                if not hasattr(module, class_name):
                    raise HandlerLoadError(f"Class {class_name} not found in module {module_path}")
                
                handler_cls = getattr(module, class_name)
                
                # Validate handler class
                if not issubclass(handler_cls, ActionHandler):
                    raise HandlerLoadError(f"Handler {handler_class} must inherit from ActionHandler")
                
                # Instantiate and cache
                self._handler_cache[handler_class] = handler_cls()
                
            except ImportError as e:
                raise HandlerLoadError(f"Failed to import handler module {handler_class}: {e}")
            except Exception as e:
                raise HandlerLoadError(f"Failed to load handler {handler_class}: {e}")
        
        return self._handler_cache[handler_class]