"""Dependencies for event action management endpoints."""

from functools import lru_cache

from neo_commons.features.events.services.event_action_registry import EventActionRegistry
from neo_commons.features.events.services.action_execution_service import ActionExecutionService
from neo_commons.features.events.repositories.action_execution_repository import ActionExecutionRepository

from ...common.dependencies import get_database_service
from .services import AdminEventActionService


@lru_cache()
def get_action_registry() -> EventActionRegistry:
    """Get event action registry instance."""
    # This will be initialized with database service
    # For now, return a placeholder - needs proper initialization
    return None


@lru_cache()
def get_execution_service() -> ActionExecutionService:
    """Get action execution service instance.""" 
    # This will be initialized with proper dependencies
    return None


@lru_cache()
def get_execution_repository() -> ActionExecutionRepository:
    """Get action execution repository instance."""
    # This will be initialized with database service
    return None


async def get_admin_event_action_service() -> AdminEventActionService:
    """Get admin event action service with proper dependencies.
    
    Returns:
        Initialized AdminEventActionService
    """
    # Get database service
    database_service = await get_database_service()
    
    # Initialize neo-commons event services
    from neo_commons.features.events.repositories.event_action_repository import EventActionRepository
    from neo_commons.features.events.repositories.action_execution_repository import ActionExecutionRepository
    from neo_commons.features.events.services.event_action_registry import EventActionRegistry
    from neo_commons.features.events.services.action_execution_service import ActionExecutionService
    
    # Create repositories with database service
    action_repository = EventActionRepository(database_service, schema_name="admin")
    execution_repository = ActionExecutionRepository(database_service, schema_name="admin")
    
    # Create services
    action_registry = EventActionRegistry(action_repository)
    execution_service = ActionExecutionService(execution_repository)
    
    # Return admin service
    return AdminEventActionService(
        action_registry=action_registry,
        execution_service=execution_service,
        execution_repository=execution_repository
    )