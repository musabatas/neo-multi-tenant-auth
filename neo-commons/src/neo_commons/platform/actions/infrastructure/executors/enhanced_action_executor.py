"""Enhanced action executor with registry, retry, and error handling."""

import traceback
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from ...application.protocols.action_executor import ActionExecutorProtocol, ExecutionContext, ExecutionResult
from ...domain.entities.action import Action
from ...domain.entities.action_execution import ActionExecution, ActionStatus
from ...domain.value_objects.execution_id import ExecutionId
from ..registries.handler_registry import get_handler_registry
from ..retry.retry_policy import RetryPolicy, RetryScheduler, ErrorClassifier


class EnhancedActionExecutor(ActionExecutorProtocol):
    """Enhanced action executor with full retry and error handling."""
    
    def __init__(self):
        self.handler_registry = get_handler_registry()
        self.retry_scheduler = RetryScheduler()
        self.error_classifier = ErrorClassifier()
    
    async def execute(
        self, 
        action: Action, 
        execution_context: ExecutionContext
    ) -> ExecutionResult:
        """Execute an action with comprehensive error handling and retry logic."""
        execution_id = ExecutionId.generate()
        
        # Create execution record
        execution = ActionExecution.create(
            execution_id=execution_id,
            action_id=action.id,
            event_id=execution_context.event_id,
            input_data=execution_context.input_data,
            attempt_number=1
        )
        
        try:
            # Execute the action
            result = await self._execute_with_timeout(action, execution_context, execution)
            
            # Mark as completed
            execution.complete(result.output_data if result else {})
            
            return ExecutionResult(
                execution_id=execution_id,
                success=True,
                output_data=execution.output_data,
                execution_time_ms=execution.execution_time_ms,
                error_message=None
            )
            
        except Exception as e:
            # Classify the error
            error_type = self.error_classifier.classify_error(e)
            error_message = str(e)
            stack_trace = traceback.format_exc()
            
            # Mark execution as failed
            execution.fail(error_message, {"stack_trace": stack_trace, "error_type": error_type})
            
            # Determine if retry should be attempted
            retry_policy = self._get_retry_policy(action)
            should_retry = retry_policy.should_retry(execution.attempt_number, error_type)
            
            if should_retry and execution.attempt_number <= retry_policy.max_retries:
                # Schedule retry
                await self._schedule_retry(action, execution_context, execution, retry_policy, e)
                
                return ExecutionResult(
                    execution_id=execution_id,
                    success=False,
                    output_data=None,
                    execution_time_ms=execution.execution_time_ms,
                    error_message=f"Failed, retry scheduled: {error_message}",
                    retry_scheduled=True
                )
            else:
                # No more retries
                return ExecutionResult(
                    execution_id=execution_id,
                    success=False,
                    output_data=None,
                    execution_time_ms=execution.execution_time_ms,
                    error_message=error_message,
                    retry_scheduled=False
                )
    
    async def _execute_with_timeout(
        self, 
        action: Action, 
        execution_context: ExecutionContext,
        execution: ActionExecution
    ) -> Optional[ExecutionResult]:
        """Execute action with timeout handling."""
        start_time = datetime.utcnow()
        
        try:
            # Load handler from registry
            handler = await self.handler_registry.get_handler(action.handler_class)
            
            # Execute with timeout
            timeout_seconds = action.timeout_seconds
            
            if timeout_seconds and timeout_seconds > 0:
                result = await asyncio.wait_for(
                    handler.execute(
                        config=action.config,
                        input_data=execution_context.input_data,
                        context=execution_context
                    ),
                    timeout=timeout_seconds
                )
            else:
                result = await handler.execute(
                    config=action.config,
                    input_data=execution_context.input_data,
                    context=execution_context
                )
            
            # Calculate execution time
            end_time = datetime.utcnow()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            execution.execution_time_ms = execution_time_ms
            
            return ExecutionResult(
                execution_id=execution.id,
                success=True,
                output_data=result if isinstance(result, dict) else {"result": result},
                execution_time_ms=execution_time_ms
            )
            
        except asyncio.TimeoutError:
            # Handle timeout specifically
            end_time = datetime.utcnow()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            execution.execution_time_ms = execution_time_ms
            
            raise TimeoutError(f"Action execution timed out after {timeout_seconds} seconds")
        
        except Exception as e:
            # Calculate execution time even for failures
            end_time = datetime.utcnow()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            execution.execution_time_ms = execution_time_ms
            raise e
    
    async def _schedule_retry(
        self,
        action: Action,
        execution_context: ExecutionContext,
        failed_execution: ActionExecution,
        retry_policy: RetryPolicy,
        original_error: Exception
    ):
        """Schedule a retry for a failed execution."""
        error_type = self.error_classifier.classify_error(original_error)
        
        # Create retry callback
        async def retry_callback():
            # Create new execution for retry
            retry_execution_context = ExecutionContext(
                event_id=execution_context.event_id,
                input_data=execution_context.input_data,
                context_data={
                    **execution_context.context_data,
                    "retry_attempt": failed_execution.attempt_number + 1,
                    "parent_execution_id": str(failed_execution.id.value)
                },
                schema=execution_context.schema,
                tenant_id=execution_context.tenant_id,
                organization_id=execution_context.organization_id
            )
            
            # Execute retry (this will create a new execution record)
            await self.execute(action, retry_execution_context)
        
        # Schedule the retry
        await self.retry_scheduler.schedule_retry(
            execution_id=str(failed_execution.id.value),
            retry_policy=retry_policy,
            attempt_number=failed_execution.attempt_number + 1,
            retry_callback=retry_callback,
            error_type=error_type
        )
    
    def _get_retry_policy(self, action: Action) -> RetryPolicy:
        """Get retry policy for an action."""
        if action.retry_policy:
            return RetryPolicy.from_dict(action.retry_policy)
        else:
            # Use default retry policy
            from ..retry.retry_policy import DEFAULT_RETRY_POLICIES
            return DEFAULT_RETRY_POLICIES["default"]
    
    async def validate_handler(self, handler_class_path: str) -> bool:
        """Validate if a handler can be loaded and executed."""
        validation_result = await self.handler_registry.validate_handler(handler_class_path)
        return validation_result.is_valid
    
    async def get_handler_info(self, handler_class_path: str) -> Optional[Dict[str, Any]]:
        """Get information about a handler."""
        validation_result = await self.handler_registry.validate_handler(handler_class_path)
        
        if validation_result.is_valid and validation_result.validation_details:
            return validation_result.validation_details
        
        return None
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get handler registry statistics."""
        return {
            **self.handler_registry.get_cache_stats(),
            "scheduled_retries": self.retry_scheduler.get_scheduled_count(),
            "scheduled_executions": self.retry_scheduler.get_scheduled_executions()
        }
    
    async def cancel_retry(self, execution_id: str) -> bool:
        """Cancel a scheduled retry."""
        return await self.retry_scheduler.cancel_retry(execution_id)
    
    async def shutdown(self):
        """Shutdown executor and cleanup resources."""
        await self.retry_scheduler.shutdown()
        self.handler_registry.clear_cache()