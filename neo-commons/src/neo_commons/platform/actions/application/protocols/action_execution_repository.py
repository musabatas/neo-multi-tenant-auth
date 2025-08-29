"""Action execution repository protocol for data persistence."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from ...domain.entities.action_execution import ActionExecution
from ...domain.entities.action import ActionStatus
from ...domain.value_objects.execution_id import ExecutionId
from ...domain.value_objects.action_id import ActionId
from ....events.domain.value_objects.event_id import EventId


class ActionExecutionRepositoryProtocol(ABC):
    """Protocol for action execution persistence operations."""
    
    @abstractmethod
    async def save(self, execution: ActionExecution, schema: str) -> ActionExecution:
        """
        Save an action execution to the specified schema.
        
        Args:
            execution: Action execution to save
            schema: Database schema name (admin, tenant_xxx, etc.)
            
        Returns:
            Saved execution with any database-generated fields
        """
        ...
    
    @abstractmethod
    async def get_by_id(self, execution_id: ExecutionId, schema: str) -> Optional[ActionExecution]:
        """
        Get action execution by ID from the specified schema.
        
        Args:
            execution_id: Execution ID to retrieve
            schema: Database schema name
            
        Returns:
            Action execution if found, None otherwise
        """
        ...
    
    @abstractmethod
    async def update(self, execution: ActionExecution, schema: str) -> ActionExecution:
        """
        Update an existing action execution in the specified schema.
        
        Args:
            execution: Execution with updated values
            schema: Database schema name
            
        Returns:
            Updated execution
        """
        ...
    
    @abstractmethod
    async def list_executions(
        self, 
        schema: str,
        limit: int = 50, 
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ActionExecution]:
        """
        List action executions from the specified schema with optional filtering.
        
        Args:
            schema: Database schema name
            limit: Maximum number of executions to return
            offset: Number of executions to skip
            filters: Optional filters (status, action_id, event_id, etc.)
            
        Returns:
            List of executions matching criteria
        """
        ...
    
    @abstractmethod
    async def get_executions_by_action(
        self, 
        action_id: ActionId, 
        schema: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[ActionExecution]:
        """
        Get executions for a specific action.
        
        Args:
            action_id: Action ID to get executions for
            schema: Database schema name
            limit: Maximum number of executions to return
            offset: Number of executions to skip
            
        Returns:
            List of executions for the action
        """
        ...
    
    @abstractmethod
    async def get_executions_by_event(
        self, 
        event_id: EventId, 
        schema: str
    ) -> List[ActionExecution]:
        """
        Get executions for a specific event.
        
        Args:
            event_id: Event ID to get executions for
            schema: Database schema name
            
        Returns:
            List of executions for the event
        """
        ...
    
    @abstractmethod
    async def get_executions_by_status(
        self, 
        status: ActionStatus, 
        schema: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[ActionExecution]:
        """
        Get executions by status.
        
        Args:
            status: Execution status to filter by
            schema: Database schema name
            limit: Maximum number of executions to return
            offset: Number of executions to skip
            
        Returns:
            List of executions with the specified status
        """
        ...
    
    @abstractmethod
    async def get_pending_executions(self, schema: str, limit: int = 100) -> List[ActionExecution]:
        """
        Get pending executions ready for processing.
        
        Args:
            schema: Database schema name
            limit: Maximum number of executions to return
            
        Returns:
            List of pending executions
        """
        ...
    
    @abstractmethod
    async def get_failed_executions(
        self, 
        schema: str,
        retry_eligible_only: bool = False,
        limit: int = 100
    ) -> List[ActionExecution]:
        """
        Get failed executions, optionally only those eligible for retry.
        
        Args:
            schema: Database schema name
            retry_eligible_only: If True, only return executions that can be retried
            limit: Maximum number of executions to return
            
        Returns:
            List of failed executions
        """
        ...
    
    @abstractmethod
    async def get_retry_executions(
        self, 
        parent_execution_id: ExecutionId, 
        schema: str
    ) -> List[ActionExecution]:
        """
        Get all retry executions for a parent execution.
        
        Args:
            parent_execution_id: Parent execution ID
            schema: Database schema name
            
        Returns:
            List of retry executions
        """
        ...
    
    @abstractmethod
    async def update_status(
        self, 
        execution_id: ExecutionId, 
        status: ActionStatus, 
        schema: str,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update execution status and related fields.
        
        Args:
            execution_id: Execution ID to update
            status: New status
            schema: Database schema name
            error_message: Error message if status is failed
            error_details: Error details if status is failed
            output_data: Output data if status is completed
            
        Returns:
            True if updated successfully, False if execution not found
        """
        ...
    
    @abstractmethod
    async def mark_as_started(
        self, 
        execution_id: ExecutionId, 
        worker_id: str,
        schema: str
    ) -> bool:
        """
        Mark execution as started by a worker.
        
        Args:
            execution_id: Execution ID to update
            worker_id: ID of the worker processing this execution
            schema: Database schema name
            
        Returns:
            True if updated successfully, False if execution not found
        """
        ...
    
    @abstractmethod
    async def mark_as_completed(
        self, 
        execution_id: ExecutionId, 
        output_data: Dict[str, Any],
        execution_duration_ms: int,
        schema: str
    ) -> bool:
        """
        Mark execution as completed successfully.
        
        Args:
            execution_id: Execution ID to update
            output_data: Output data from execution
            execution_duration_ms: Execution time in milliseconds
            schema: Database schema name
            
        Returns:
            True if updated successfully, False if execution not found
        """
        ...
    
    @abstractmethod
    async def mark_as_failed(
        self, 
        execution_id: ExecutionId, 
        error_message: str,
        error_details: Dict[str, Any],
        error_stack_trace: Optional[str],
        execution_duration_ms: Optional[int],
        schema: str
    ) -> bool:
        """
        Mark execution as failed.
        
        Args:
            execution_id: Execution ID to update
            error_message: Error message
            error_details: Error details
            error_stack_trace: Error stack trace
            execution_duration_ms: Execution time in milliseconds
            schema: Database schema name
            
        Returns:
            True if updated successfully, False if execution not found
        """
        ...
    
    @abstractmethod
    async def update_performance_metrics(
        self, 
        execution_id: ExecutionId,
        memory_usage_mb: Optional[int],
        cpu_time_ms: Optional[int],
        schema: str
    ) -> bool:
        """
        Update execution performance metrics.
        
        Args:
            execution_id: Execution ID to update
            memory_usage_mb: Memory usage in MB
            cpu_time_ms: CPU time in milliseconds
            schema: Database schema name
            
        Returns:
            True if updated successfully, False if execution not found
        """
        ...
    
    @abstractmethod
    async def get_execution_statistics(
        self, 
        schema: str,
        action_id: Optional[ActionId] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get execution statistics for actions.
        
        Args:
            schema: Database schema name
            action_id: Optional action ID to filter statistics
            start_date: Optional start date for time range
            end_date: Optional end date for time range
            
        Returns:
            Statistics dictionary with counts, averages, etc.
        """
        ...
    
    @abstractmethod
    async def cleanup_old_executions(
        self, 
        schema: str,
        older_than_days: int = 30,
        keep_failed: bool = True
    ) -> int:
        """
        Clean up old completed executions.
        
        Args:
            schema: Database schema name
            older_than_days: Delete executions older than this many days
            keep_failed: If True, keep failed executions for analysis
            
        Returns:
            Number of executions deleted
        """
        ...
    
    @abstractmethod
    async def count_executions(
        self, 
        schema: str, 
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count executions in the specified schema.
        
        Args:
            schema: Database schema name
            filters: Optional filters
            
        Returns:
            Number of executions matching criteria
        """
        ...