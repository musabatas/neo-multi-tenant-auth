"""Actions API components."""

from .models import (
    # Requests
    CreateActionRequest,
    ExecuteActionRequest,
    UpdateActionRequest,
    
    # Responses
    ActionResponse,
    ActionListResponse,
    ExecutionResponse,
    ActionMetricsResponse,
)

from .routers import (
    admin_actions_router,
    tenant_actions_router,
    internal_actions_router,
)

from .dependencies import (
    # Repository Dependencies
    get_action_repository,
    get_action_execution_repository,
    get_event_action_subscription_repository,
    get_action_executor,
    
    # Command Dependencies
    get_create_action_command,
    get_execute_action_command,
    
    # Query Dependencies
    get_get_action_query,
    get_list_actions_query,
    
    # Service Dependencies
    get_action_service,
    get_action_execution_service,
    get_event_matcher_service,
    get_action_metrics_service,
    
    # Schema Dependencies
    get_tenant_schema_resolver,
    get_admin_schema,
)

__all__ = [
    # Models - Requests
    "CreateActionRequest",
    "ExecuteActionRequest",
    "UpdateActionRequest",
    
    # Models - Responses
    "ActionResponse",
    "ActionListResponse",
    "ExecutionResponse",
    "ActionMetricsResponse",
    
    # Routers
    "admin_actions_router",
    "tenant_actions_router",
    "internal_actions_router",
    
    # Dependencies - Repositories
    "get_action_repository",
    "get_action_execution_repository",
    "get_event_action_subscription_repository",
    "get_action_executor",
    
    # Dependencies - Commands
    "get_create_action_command",
    "get_execute_action_command",
    
    # Dependencies - Queries
    "get_get_action_query",
    "get_list_actions_query",
    
    # Dependencies - Services
    "get_action_service",
    "get_action_execution_service",
    "get_event_matcher_service",
    "get_action_metrics_service",
    
    # Dependencies - Schema
    "get_tenant_schema_resolver",
    "get_admin_schema",
]