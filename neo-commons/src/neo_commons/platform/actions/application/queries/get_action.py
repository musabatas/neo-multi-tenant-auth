"""Get action query."""

from typing import Optional

from ...domain.entities.action import Action
from ...domain.value_objects.action_id import ActionId
from ..protocols.action_repository import ActionRepositoryProtocol


class GetActionQuery:
    """Query to get a single action by ID or name."""
    
    def __init__(self, action_repository: ActionRepositoryProtocol):
        self.action_repository = action_repository
    
    async def by_id(self, action_id: ActionId, schema: str) -> Optional[Action]:
        """
        Get action by ID.
        
        Args:
            action_id: Action ID to retrieve
            schema: Database schema name (admin, tenant_xxx, etc.)
            
        Returns:
            Action if found, None otherwise
        """
        return await self.action_repository.get_by_id(action_id, schema)
    
    async def by_name(self, name: str, schema: str) -> Optional[Action]:
        """
        Get action by name.
        
        Args:
            name: Action name to retrieve
            schema: Database schema name (admin, tenant_xxx, etc.)
            
        Returns:
            Action if found, None otherwise
        """
        return await self.action_repository.get_by_name(name, schema)