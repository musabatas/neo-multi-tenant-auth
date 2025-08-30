"""List actions query."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from ...domain.entities.action import Action
from ...domain.value_objects.action_type import ActionType
from ..protocols.action_repository import ActionRepositoryProtocol


@dataclass
class ListActionsRequest:
    """Request to list actions with filters."""
    
    limit: int = 50
    offset: int = 0
    action_type: Optional[str] = None
    is_active: Optional[bool] = None
    is_healthy: Optional[bool] = None
    owner_team: Optional[str] = None
    event_pattern: Optional[str] = None


class ListActionsQuery:
    """Query to list actions with filtering and pagination."""
    
    def __init__(self, action_repository: ActionRepositoryProtocol):
        self.action_repository = action_repository
    
    async def execute(self, request: ListActionsRequest, schema: str) -> List[Action]:
        """
        List actions with filtering.
        
        Args:
            request: List request with filters
            schema: Database schema name (admin, tenant_xxx, etc.)
            
        Returns:
            List of actions matching criteria
        """
        filters = {}
        
        if request.action_type:
            filters["action_type"] = request.action_type
        
        if request.is_active is not None:
            filters["is_active"] = request.is_active
        
        if request.is_healthy is not None:
            filters["is_healthy"] = request.is_healthy
        
        if request.owner_team:
            filters["owner_team"] = request.owner_team
        
        return await self.action_repository.list_actions(
            schema=schema,
            limit=request.limit,
            offset=request.offset,
            filters=filters if filters else None
        )
    
    async def find_by_event_pattern(self, event_type: str, schema: str) -> List[Action]:
        """
        Find actions that match an event pattern.
        
        Args:
            event_type: Event type to match against
            schema: Database schema name (admin, tenant_xxx, etc.)
            
        Returns:
            List of actions that match the event pattern
        """
        return await self.action_repository.find_by_event_pattern(event_type, schema)
    
    async def find_by_type(self, action_type: ActionType, schema: str) -> List[Action]:
        """
        Find actions by action type.
        
        Args:
            action_type: Action type to filter by
            schema: Database schema name (admin, tenant_xxx, etc.)
            
        Returns:
            List of actions of the specified type
        """
        return await self.action_repository.find_by_type(action_type, schema)
    
    async def find_active_actions(self, schema: str) -> List[Action]:
        """
        Find all active actions.
        
        Args:
            schema: Database schema name (admin, tenant_xxx, etc.)
            
        Returns:
            List of all active actions
        """
        return await self.action_repository.find_active_actions(schema)
    
    async def find_healthy_actions(self, schema: str) -> List[Action]:
        """
        Find all healthy actions.
        
        Args:
            schema: Database schema name (admin, tenant_xxx, etc.)
            
        Returns:
            List of all healthy actions
        """
        return await self.action_repository.find_healthy_actions(schema)
    
    async def count_actions(self, filters: Optional[Dict[str, Any]], schema: str) -> int:
        """
        Count actions matching filters.
        
        Args:
            filters: Optional filters to apply
            schema: Database schema name (admin, tenant_xxx, etc.)
            
        Returns:
            Number of actions matching criteria
        """
        return await self.action_repository.count_actions(schema, filters)