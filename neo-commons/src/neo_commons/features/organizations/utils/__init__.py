"""Organization utility modules for comprehensive functionality.

Provides validation, queries, error handling, factories, and admin utilities
following DRY principles and single responsibility patterns.
"""

# Validation utilities
from .validation import OrganizationValidationRules

# Query constants and builders
from .queries import (
    ORGANIZATION_QUERIES,
    ORGANIZATION_INSERT,
    ORGANIZATION_UPDATE,
    ORGANIZATION_DELETE_SOFT,
    ORGANIZATION_DELETE_HARD,
    ORGANIZATION_GET_BY_ID,
    ORGANIZATION_GET_BY_SLUG,
    ORGANIZATION_EXISTS_BY_ID,
    ORGANIZATION_EXISTS_BY_SLUG,
    ORGANIZATION_LIST_ALL,
    ORGANIZATION_LIST_PAGINATED,
    ORGANIZATION_COUNT_ALL,
    ORGANIZATION_SEARCH_BY_NAME,
    ORGANIZATION_SEARCH_ADVANCED,
    ORGANIZATION_SEARCH_BY_METADATA,
    ORGANIZATION_UPDATE_METADATA,
    ORGANIZATION_GET_METADATA,
    ORGANIZATION_STATS_BASIC,
    ORGANIZATION_STATS_BY_INDUSTRY,
    ORGANIZATION_STATS_BY_COUNTRY,
    ORGANIZATION_STATS_BY_COMPANY_SIZE,
    ORGANIZATION_HEALTH_CHECK,
    ORGANIZATION_VALIDATE_UNIQUE_SLUG,
    ORGANIZATION_VALIDATE_UNIQUE_NAME,
    ORGANIZATION_AUDIT_LOG,
    ORGANIZATION_AUDIT_HISTORY,
    build_organization_search_query,
    build_organization_stats_query,
)

# Error handling utilities
from .error_handling import (
    organization_error_handler,
    log_organization_operation,
    OrganizationOperationContext,
    format_organization_error,
    handle_organization_creation_error,
    handle_organization_retrieval_error,
    handle_organization_update_error,
    handle_organization_deletion_error,
    handle_organization_search_error,
    handle_organization_validation_error,
    handle_organization_stats_error,
)

# Factory patterns have been simplified - use direct entity construction instead
# from .factory import (
#     OrganizationFactory,
#     OrganizationTestFactory,
# )

# Admin integration utilities
from .admin_integration import (
    OrganizationAdminUtils,
)

__all__ = [
    # Validation
    "OrganizationValidationRules",
    
    # Query constants
    "ORGANIZATION_QUERIES",
    "ORGANIZATION_INSERT",
    "ORGANIZATION_UPDATE", 
    "ORGANIZATION_DELETE_SOFT",
    "ORGANIZATION_DELETE_HARD",
    "ORGANIZATION_GET_BY_ID",
    "ORGANIZATION_GET_BY_SLUG",
    "ORGANIZATION_EXISTS_BY_ID",
    "ORGANIZATION_EXISTS_BY_SLUG",
    "ORGANIZATION_LIST_ALL",
    "ORGANIZATION_LIST_PAGINATED",
    "ORGANIZATION_COUNT_ALL",
    "ORGANIZATION_SEARCH_BY_NAME",
    "ORGANIZATION_SEARCH_ADVANCED",
    "ORGANIZATION_SEARCH_BY_METADATA",
    "ORGANIZATION_UPDATE_METADATA",
    "ORGANIZATION_GET_METADATA",
    "ORGANIZATION_STATS_BASIC",
    "ORGANIZATION_STATS_BY_INDUSTRY",
    "ORGANIZATION_STATS_BY_COUNTRY",
    "ORGANIZATION_STATS_BY_COMPANY_SIZE",
    "ORGANIZATION_HEALTH_CHECK",
    "ORGANIZATION_VALIDATE_UNIQUE_SLUG",
    "ORGANIZATION_VALIDATE_UNIQUE_NAME",
    "ORGANIZATION_AUDIT_LOG",
    "ORGANIZATION_AUDIT_HISTORY",
    "build_organization_search_query",
    "build_organization_stats_query",
    
    # Error handling
    "organization_error_handler",
    "log_organization_operation",
    "OrganizationOperationContext",
    "format_organization_error",
    "handle_organization_creation_error",
    "handle_organization_retrieval_error",
    "handle_organization_update_error",
    "handle_organization_deletion_error",
    "handle_organization_search_error",
    "handle_organization_validation_error",
    "handle_organization_stats_error",
    
    # Factory utilities - simplified to direct entity construction
    # "OrganizationFactory",
    # "OrganizationTestFactory",
    
    # Admin utilities
    "OrganizationAdminUtils",
]