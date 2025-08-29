"""Action dispatcher protocol for event routing to actions."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from uuid import UUID

from ...domain.entities.action import Action
from ...domain.entities.action_execution import ActionExecution
from ...domain.entities.event_action_subscription import EventActionSubscription
from ....events.domain.entities.event import Event


class ActionDispatcherProtocol(ABC):
    """Protocol for dispatching events to matching actions."""
    
    @abstractmethod
    async def dispatch_event(
        self, 
        event: Event, 
        schema: str
    ) -> List[ActionExecution]:
        """
        Dispatch an event to all matching actions.
        
        Args:
            event: Event to dispatch
            schema: Database schema name
            
        Returns:
            List of action executions created for the event
        """
        ...
    
    @abstractmethod
    async def find_matching_actions(
        self, 
        event: Event, 
        schema: str
    ) -> List[Action]:
        """
        Find actions that match an event.
        
        Args:
            event: Event to find actions for
            schema: Database schema name
            
        Returns:
            List of matching actions, sorted by priority
        """
        ...
    
    @abstractmethod
    async def find_matching_subscriptions(
        self, 
        event: Event, 
        schema: str
    ) -> List[EventActionSubscription]:
        """
        Find subscriptions that match an event.
        
        Args:
            event: Event to find subscriptions for
            schema: Database schema name
            
        Returns:
            List of matching subscriptions, sorted by priority
        """
        ...
    
    @abstractmethod
    async def execute_actions_for_event(
        self, 
        event: Event, 
        actions: List[Action],
        schema: str,
        parallel: bool = True
    ) -> List[ActionExecution]:
        """
        Execute a list of actions for an event.
        
        Args:
            event: Event that triggered the actions
            actions: List of actions to execute
            schema: Database schema name
            parallel: Whether to execute actions in parallel
            
        Returns:
            List of action executions
        """
        ...
    
    @abstractmethod
    async def schedule_action_execution(
        self, 
        action: Action, 
        event: Event,
        schema: str,
        delay_seconds: Optional[int] = None
    ) -> ActionExecution:
        """
        Schedule an action execution for later processing.
        
        Args:
            action: Action to schedule
            event: Event that triggered the action
            schema: Database schema name
            delay_seconds: Optional delay before execution
            
        Returns:
            Scheduled action execution
        """
        ...
    
    @abstractmethod
    async def retry_failed_execution(
        self, 
        failed_execution: ActionExecution,
        schema: str
    ) -> Optional[ActionExecution]:
        """
        Retry a failed action execution.
        
        Args:
            failed_execution: Failed execution to retry
            schema: Database schema name
            
        Returns:
            New retry execution if eligible, None if max retries exceeded
        """
        ...
    
    @abstractmethod
    async def cancel_execution(
        self, 
        execution_id: str,
        schema: str
    ) -> bool:
        """
        Cancel a pending or running action execution.
        
        Args:
            execution_id: Execution ID to cancel
            schema: Database schema name
            
        Returns:
            True if cancelled successfully, False if not found or already completed
        """
        ...
    
    @abstractmethod
    async def get_execution_status(
        self, 
        execution_id: str,
        schema: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get status information for an execution.
        
        Args:
            execution_id: Execution ID to check
            schema: Database schema name
            
        Returns:
            Status dictionary if found, None otherwise
        """
        ...
    
    @abstractmethod
    async def get_pending_executions(
        self, 
        schema: str,
        limit: int = 100
    ) -> List[ActionExecution]:
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
    async def process_execution_queue(
        self, 
        schema: str,
        worker_id: str,
        max_concurrent: int = 5
    ) -> List[ActionExecution]:
        """
        Process the execution queue for a schema.
        
        Args:
            schema: Database schema name
            worker_id: ID of the worker processing executions
            max_concurrent: Maximum concurrent executions
            
        Returns:
            List of executions processed
        """
        ...
    
    @abstractmethod
    async def monitor_executions(
        self, 
        schema: str,
        timeout_seconds: int = 300
    ) -> Dict[str, Any]:
        """
        Monitor running executions and handle timeouts.
        
        Args:
            schema: Database schema name
            timeout_seconds: Timeout threshold in seconds
            
        Returns:
            Monitoring report with timeout/completion statistics
        """
        ...