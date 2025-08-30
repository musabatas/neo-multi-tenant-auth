"""Action dependencies for dependency injection."""

from fastapi import Depends
from typing import Callable

from ...application.commands.create_action import CreateActionCommand
from ...application.commands.execute_action import ExecuteActionCommand
from ...application.queries.get_action import GetActionQuery
from ...application.queries.list_actions import ListActionsQuery
from ...application.protocols.action_repository import ActionRepositoryProtocol
from ...application.protocols.action_execution_repository import ActionExecutionRepositoryProtocol
from ...application.protocols.event_action_subscription_repository import EventActionSubscriptionRepositoryProtocol
from ...application.protocols.action_executor import ActionExecutorProtocol
from ...infrastructure.repositories.asyncpg_action_repository import AsyncPGActionRepository
from ...infrastructure.repositories.asyncpg_action_execution_repository import AsyncPGActionExecutionRepository
from ...infrastructure.repositories.asyncpg_event_action_subscription_repository import AsyncPGEventActionSubscriptionRepository
from ...infrastructure.executors.default_action_executor import DefaultActionExecutor


# Repository Dependencies
def get_action_repository() -> ActionRepositoryProtocol:
    """Get action repository instance."""
    # TODO: In a real implementation, this would be configured through dependency injection container
    return AsyncPGActionRepository()


def get_action_execution_repository() -> ActionExecutionRepositoryProtocol:
    """Get action execution repository instance."""
    # TODO: In a real implementation, this would be configured through dependency injection container
    return AsyncPGActionExecutionRepository()


def get_event_action_subscription_repository() -> EventActionSubscriptionRepositoryProtocol:
    """Get event action subscription repository instance."""
    # TODO: In a real implementation, this would be configured through dependency injection container
    return AsyncPGEventActionSubscriptionRepository()


def get_action_executor() -> ActionExecutorProtocol:
    """Get action executor instance."""
    # TODO: In a real implementation, this would be configured through dependency injection container
    return DefaultActionExecutor()


# Command Dependencies
def get_create_action_command(
    action_repository: ActionRepositoryProtocol = Depends(get_action_repository)
) -> CreateActionCommand:
    """Get create action command instance."""
    return CreateActionCommand(action_repository)


def get_execute_action_command(
    action_repository: ActionRepositoryProtocol = Depends(get_action_repository),
    execution_repository: ActionExecutionRepositoryProtocol = Depends(get_action_execution_repository),
    action_executor: ActionExecutorProtocol = Depends(get_action_executor)
) -> ExecuteActionCommand:
    """Get execute action command instance."""
    return ExecuteActionCommand(
        action_repository=action_repository,
        execution_repository=execution_repository,
        action_executor=action_executor
    )


# Query Dependencies
def get_get_action_query(
    action_repository: ActionRepositoryProtocol = Depends(get_action_repository)
) -> GetActionQuery:
    """Get action query instance."""
    return GetActionQuery(action_repository)


def get_list_actions_query(
    action_repository: ActionRepositoryProtocol = Depends(get_action_repository)
) -> ListActionsQuery:
    """Get list actions query instance."""
    return ListActionsQuery(action_repository)


# Service Dependencies (Convenience wrappers)
def get_action_service(
    action_repository: ActionRepositoryProtocol = Depends(get_action_repository)
):
    """Get action service containing commands and queries."""
    # This returns a simple object with all action-related operations
    class ActionService:
        def __init__(self, repository: ActionRepositoryProtocol):
            self.create_action = CreateActionCommand(repository)
            self.get_action = GetActionQuery(repository)
            self.list_actions = ListActionsQuery(repository)
    
    return ActionService(action_repository)


def get_action_execution_service(
    action_repository: ActionRepositoryProtocol = Depends(get_action_repository),
    execution_repository: ActionExecutionRepositoryProtocol = Depends(get_action_execution_repository),
    action_executor: ActionExecutorProtocol = Depends(get_action_executor)
):
    """Get action execution service."""
    class ActionExecutionService:
        def __init__(self, action_repo, execution_repo, executor):
            self.execute_action = ExecuteActionCommand(
                action_repository=action_repo,
                execution_repository=execution_repo,
                action_executor=executor
            )
    
    return ActionExecutionService(action_repository, execution_repository, action_executor)


def get_event_matcher_service(
    subscription_repository: EventActionSubscriptionRepositoryProtocol = Depends(get_event_action_subscription_repository),
    action_repository: ActionRepositoryProtocol = Depends(get_action_repository)
):
    """Get event matcher service for finding actions based on events."""
    class EventMatcherService:
        def __init__(self, sub_repo, action_repo):
            self.subscription_repository = sub_repo
            self.action_repository = action_repo
        
        async def find_matching_actions(
            self, 
            event_type: str, 
            schema: str,
            tenant_id: str = None,
            organization_id: str = None,
            source_service: str = None
        ):
            """Find actions that match an event."""
            # Get subscriptions matching the event
            subscriptions = await self.subscription_repository.find_matching_subscriptions(
                event_type=event_type,
                schema=schema,
                tenant_id=tenant_id,
                organization_id=organization_id,
                source_service=source_service
            )
            
            # Get the corresponding actions
            actions = []
            for subscription in subscriptions:
                action = await self.action_repository.get(subscription.action_id, schema)
                if action and action.is_active and action.is_healthy:
                    actions.append(action)
            
            # Sort by priority (higher priority first)
            return sorted(actions, key=lambda a: a.priority, reverse=True)
    
    return EventMatcherService(subscription_repository, action_repository)


def get_action_metrics_service():
    """Get action metrics service."""
    # TODO: Implement when metrics functionality is created
    class ActionMetricsService:
        def __init__(self):
            pass
        
        async def get_action_metrics(self, action_id, schema):
            raise NotImplementedError("Metrics service not yet implemented")
    
    return ActionMetricsService()


# Schema Resolution Dependencies
def get_tenant_schema_resolver() -> Callable[[str], str]:
    """Get tenant schema resolver function."""
    def resolve_schema(tenant_id: str) -> str:
        """Resolve tenant schema name from tenant ID."""
        # TODO: In a real implementation, this would query the database to get tenant schema
        # For now, assume schema follows pattern: tenant_{tenant_slug}
        return f"tenant_{tenant_id}"
    
    return resolve_schema


def get_admin_schema() -> str:
    """Get admin schema name."""
    return "admin"