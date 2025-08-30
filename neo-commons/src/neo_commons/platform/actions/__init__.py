"""Actions platform module."""

# Domain exports
from .domain import (
    # Entities
    Action,
    ActionExecution,
    ActionStatus,
    EventActionSubscription,
    
    # Value Objects
    ActionId,
    ActionType,
    ExecutionId,
    SubscriptionId,
)

# Application exports
from .application import (
    # Repository Protocols
    ActionRepositoryProtocol,
    ActionExecutionRepositoryProtocol, 
    EventActionSubscriptionRepositoryProtocol,
    
    # Execution Protocols
    ActionExecutorProtocol,
    ExecutionContext,
    ExecutionResult,
    
    # Dispatcher Protocols
    ActionDispatcherProtocol,
    
    # Commands
    CreateActionCommand,
    CreateActionRequest,
    ExecuteActionCommand, 
    ExecuteActionRequest,
    
    # Queries
    GetActionQuery,
    ListActionsQuery,
    ListActionsRequest,
    
    # Validators
    ActionConfigValidator,
    ValidationResult,
    EventPatternValidator,
    PatternValidationResult, 
    HandlerClassValidator,
    HandlerValidationResult,
)

# Infrastructure exports
from .infrastructure import (
    # Repositories
    AsyncPGActionRepository,
    AsyncPGActionExecutionRepository,
    AsyncPGEventActionSubscriptionRepository,
    
    # Executors
    DefaultActionExecutor,
    EnhancedActionExecutor,
    
    # Email handlers
    SimpleEmailHandler,
    SendGridEmailHandler,
    TemplateEmailHandler,
    
    # Webhook handlers
    HTTPWebhookHandler,
    EnhancedWebhookHandler,
    
    # Database handlers
    SimpleDatabaseHandler,
    EnhancedDatabaseHandler,
    TenantSchemaHandler,
    
    # SMS handlers
    TwilioSMSHandler,
    AWSSNSSMSHandler,
    
    # Registries
    HandlerRegistry,
    
    # Retry System
    RetryPolicy,
    BackoffType,
)

# API exports
from .api import (
    # Models - Requests
    CreateActionRequest as APICreateActionRequest,
    ExecuteActionRequest as APIExecuteActionRequest,
    UpdateActionRequest,
    
    # Models - Responses
    ActionResponse,
    ActionListResponse,
    ExecutionResponse,
    ActionMetricsResponse,
    
    # Routers
    admin_actions_router,
    tenant_actions_router,
    internal_actions_router,
    
    # Dependencies
    get_action_service,
    get_action_execution_service,
    get_event_matcher_service,
    get_action_metrics_service,
    get_tenant_schema_resolver,
    get_admin_schema,
)

__all__ = [
    # Domain - Entities
    "Action",
    "ActionExecution",
    "ActionStatus",
    "EventActionSubscription",
    
    # Domain - Value Objects
    "ActionId",
    "ActionType",
    "ExecutionId",
    "SubscriptionId",
    
    # Application - Protocols
    "ActionRepositoryProtocol",
    "ActionExecutionRepositoryProtocol",
    "EventActionSubscriptionRepositoryProtocol",
    "ActionExecutorProtocol",
    "ExecutionContext",
    "ExecutionResult",
    "ActionDispatcherProtocol",
    
    # Application - Commands
    "CreateActionCommand",
    "CreateActionRequest",
    "ExecuteActionCommand",
    "ExecuteActionRequest",
    
    # Application - Queries
    "GetActionQuery",
    "ListActionsQuery",
    "ListActionsRequest",
    
    # Application - Validators
    "ActionConfigValidator",
    "ValidationResult",
    "EventPatternValidator",
    "PatternValidationResult",
    "HandlerClassValidator",
    "HandlerValidationResult",
    
    # Infrastructure - Repositories
    "AsyncPGActionRepository",
    "AsyncPGActionExecutionRepository",
    "AsyncPGEventActionSubscriptionRepository",
    
    # Infrastructure - Executors
    "DefaultActionExecutor",
    "EnhancedActionExecutor",
    
    # Infrastructure - Email Handlers
    "SimpleEmailHandler",
    "SendGridEmailHandler",
    "TemplateEmailHandler",
    
    # Infrastructure - Webhook Handlers
    "HTTPWebhookHandler",
    "EnhancedWebhookHandler",
    
    # Infrastructure - Database Handlers
    "SimpleDatabaseHandler",
    "EnhancedDatabaseHandler",
    "TenantSchemaHandler",
    
    # Infrastructure - SMS Handlers
    "TwilioSMSHandler",
    "AWSSNSSMSHandler",
    
    # Infrastructure - System Components
    "HandlerRegistry",
    "RetryPolicy",
    "BackoffType",
    
    # API - Models
    "APICreateActionRequest",
    "APIExecuteActionRequest",
    "UpdateActionRequest",
    "ActionResponse",
    "ActionListResponse",
    "ExecutionResponse",
    "ActionMetricsResponse",
    
    # API - Routers
    "admin_actions_router",
    "tenant_actions_router",
    "internal_actions_router",
    
    # API - Dependencies
    "get_action_service",
    "get_action_execution_service",
    "get_event_matcher_service",
    "get_action_metrics_service",
    "get_tenant_schema_resolver",
    "get_admin_schema",
]