"""Action dependencies."""

from .action_dependencies import (
    get_action_repository,
    get_action_execution_repository,
    get_event_action_subscription_repository,
    get_action_executor,
    get_create_action_command,
    get_execute_action_command,
    get_get_action_query,
    get_list_actions_query,
    get_action_service,
    get_action_execution_service,
    get_event_matcher_service,
    get_action_metrics_service,
    get_tenant_schema_resolver,
    get_admin_schema,
)

__all__ = [
    # Repository Dependencies
    "get_action_repository",
    "get_action_execution_repository",
    "get_event_action_subscription_repository",
    "get_action_executor",
    
    # Command Dependencies
    "get_create_action_command",
    "get_execute_action_command",
    
    # Query Dependencies
    "get_get_action_query",
    "get_list_actions_query",
    
    # Service Dependencies
    "get_action_service",
    "get_action_execution_service",
    "get_event_matcher_service",
    "get_action_metrics_service",
    
    # Schema Dependencies
    "get_tenant_schema_resolver",
    "get_admin_schema",
]