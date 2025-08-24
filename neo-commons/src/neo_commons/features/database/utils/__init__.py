"""Database utility modules."""

from .validation import (
    validate_pool_configuration,
    validate_connection_basic_fields,
    validate_connection_timeouts,
)
from .queries import (
    BASIC_HEALTH_CHECK,
    SCHEMA_EXISTENCE_CHECK,
    DATABASE_ACTIVITY_STATS,
    DATABASE_DETAILED_ACTIVITY,
    HEALTH_CHECK_QUERIES,
    CONNECTION_REGISTRY_LOAD,
    CONNECTION_REGISTRY_BY_NAME,
    TENANT_SCHEMA_EXISTS,
    TENANT_SCHEMA_LIST,
)
from .connection_factory import ConnectionFactory
from .error_handling import (
    database_error_handler,
    log_database_operation,
    DatabaseOperationContext,
    format_database_error,
    handle_connection_error,
    handle_query_error,
    handle_health_check_error,
)
from .admin_connection import AdminConnectionUtils

__all__ = [
    "validate_pool_configuration",
    "validate_connection_basic_fields", 
    "validate_connection_timeouts",
    "BASIC_HEALTH_CHECK",
    "SCHEMA_EXISTENCE_CHECK", 
    "DATABASE_ACTIVITY_STATS",
    "DATABASE_DETAILED_ACTIVITY",
    "HEALTH_CHECK_QUERIES",
    "CONNECTION_REGISTRY_LOAD",
    "CONNECTION_REGISTRY_BY_NAME",
    "TENANT_SCHEMA_EXISTS",
    "TENANT_SCHEMA_LIST",
    "ConnectionFactory",
    "database_error_handler",
    "log_database_operation",
    "DatabaseOperationContext",
    "format_database_error",
    "handle_connection_error",
    "handle_query_error",
    "handle_health_check_error",
    "AdminConnectionUtils",
]