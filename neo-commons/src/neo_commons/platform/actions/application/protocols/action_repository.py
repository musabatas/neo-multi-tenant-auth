"""Action repository protocol for data persistence."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from ...domain.entities.action import Action, ActionStatus
from ...domain.value_objects.action_id import ActionId
from ...domain.value_objects.action_type import ActionType


class ActionRepositoryProtocol(ABC):
    """Protocol for action persistence operations."""
    
    @abstractmethod
    async def save(self, action: Action, schema: str) -> Action:
        """
        Save an action to the specified schema.
        
        Args:
            action: Action to save
            schema: Database schema name (admin, tenant_xxx, etc.)
            
        Returns:
            Saved action with any database-generated fields
        """
        ...
    
    @abstractmethod
    async def get_by_id(self, action_id: ActionId, schema: str) -> Optional[Action]:
        """
        Get action by ID from the specified schema.
        
        Args:
            action_id: Action ID to retrieve
            schema: Database schema name
            
        Returns:
            Action if found, None otherwise
        """
        ...
    
    @abstractmethod
    async def get_by_name(self, name: str, schema: str) -> Optional[Action]:
        """
        Get action by name from the specified schema.
        
        Args:
            name: Action name to retrieve
            schema: Database schema name
            
        Returns:
            Action if found, None otherwise
        """
        ...
    
    @abstractmethod
    async def list_actions(
        self, 
        schema: str,
        limit: int = 50, 
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Action]:
        """
        List actions from the specified schema with optional filtering.
        
        Args:
            schema: Database schema name
            limit: Maximum number of actions to return
            offset: Number of actions to skip
            filters: Optional filters (action_type, is_active, is_healthy, etc.)
            
        Returns:
            List of actions matching criteria
        """
        ...
    
    @abstractmethod
    async def update(self, action: Action, schema: str) -> Action:
        """
        Update an existing action in the specified schema.
        
        Args:
            action: Action with updated values
            schema: Database schema name
            
        Returns:
            Updated action
        """
        ...
    
    @abstractmethod
    async def delete(self, action_id: ActionId, schema: str) -> bool:
        """
        Delete action by ID from the specified schema.
        
        Args:
            action_id: Action ID to delete
            schema: Database schema name
            
        Returns:
            True if action was deleted, False if not found
        """
        ...
    
    @abstractmethod
    async def find_by_event_pattern(self, event_type: str, schema: str) -> List[Action]:
        """
        Find actions that match an event type pattern.
        
        Args:
            event_type: Event type to match against action patterns
            schema: Database schema name
            
        Returns:
            List of actions with matching event patterns
        """
        ...
    
    @abstractmethod
    async def find_by_type(self, action_type: ActionType, schema: str) -> List[Action]:
        """
        Find actions by action type.
        
        Args:
            action_type: Action type to filter by
            schema: Database schema name
            
        Returns:
            List of actions with matching action type
        """
        ...
    
    @abstractmethod
    async def find_active_actions(self, schema: str) -> List[Action]:
        """
        Find all active actions in the specified schema.
        
        Args:
            schema: Database schema name
            
        Returns:
            List of active actions
        """
        ...
    
    @abstractmethod
    async def find_healthy_actions(self, schema: str) -> List[Action]:
        """
        Find all healthy actions in the specified schema.
        
        Args:
            schema: Database schema name
            
        Returns:
            List of healthy actions
        """
        ...
    
    @abstractmethod
    async def update_health_status(
        self, 
        action_id: ActionId, 
        is_healthy: bool,
        error_message: Optional[str],
        schema: str
    ) -> bool:
        """
        Update action health status.
        
        Args:
            action_id: Action ID to update
            is_healthy: Health status
            error_message: Error message if unhealthy
            schema: Database schema name
            
        Returns:
            True if updated successfully, False if action not found
        """
        ...
    
    @abstractmethod
    async def update_statistics(
        self, 
        action_id: ActionId,
        execution_time_ms: int,
        success: bool,
        schema: str
    ) -> bool:
        """
        Update action execution statistics.
        
        Args:
            action_id: Action ID to update
            execution_time_ms: Execution time in milliseconds
            success: Whether execution was successful
            schema: Database schema name
            
        Returns:
            True if updated successfully, False if action not found
        """
        ...
    
    @abstractmethod
    async def get_action_statistics(
        self, 
        action_id: ActionId, 
        schema: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get action execution statistics.
        
        Args:
            action_id: Action ID to get statistics for
            schema: Database schema name
            
        Returns:
            Statistics dictionary if found, None otherwise
        """
        ...
    
    @abstractmethod
    async def count_actions(self, schema: str, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count actions in the specified schema.
        
        Args:
            schema: Database schema name
            filters: Optional filters
            
        Returns:
            Number of actions matching criteria
        """
        ...