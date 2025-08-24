"""Value objects module for neo-commons.

This module provides immutable value objects that encapsulate
business logic and provide type safety. Includes both basic and
advanced (configurable) validation options.
"""

from .identifiers import (
    # Basic value objects
    UserId,
    TenantId,
    OrganizationId,
    PermissionCode,
    RoleCode,
    DatabaseConnectionId,
    RegionId,
    RealmId,
    KeycloakUserId,
    TokenId,
    # Value objects framework
    ValueObject,
    ValidationRule,
    ValidationRuleBuilder,
    set_value_object_configuration,
    clear_value_object_cache,
    get_value_object_statistics,
    # Advanced identifier value objects
    AdvancedUserId,
    AdvancedTenantId,
    AdvancedOrganizationId,
    AdvancedPermissionCode,
    AdvancedRoleCode,
    AdvancedDatabaseConnectionId,
    AdvancedRegionId,
    AdvancedRealmId,
    AdvancedKeycloakUserId,
    AdvancedTokenId,
    # Backward compatibility aliases
    ConfigurableValueObject,
    ConfigurableUserId,
    ConfigurableTenantId,
    ConfigurableOrganizationId,
    ConfigurablePermissionCode,
    ConfigurableRoleCode,
    ConfigurableDatabaseConnectionId,
    ConfigurableRegionId,
    ConfigurableRealmId,
    ConfigurableKeycloakUserId,
    ConfigurableTokenId,
)

__all__ = [
    # Basic value objects
    "UserId",
    "TenantId", 
    "OrganizationId",
    "PermissionCode",
    "RoleCode",
    "DatabaseConnectionId",
    "RegionId",
    "RealmId",
    "KeycloakUserId", 
    "TokenId",
    # Value objects framework
    "ValueObject",
    "ValidationRule",
    "ValidationRuleBuilder",
    "set_value_object_configuration",
    "clear_value_object_cache",
    "get_value_object_statistics",
    # Advanced identifier value objects
    "AdvancedUserId",
    "AdvancedTenantId",
    "AdvancedOrganizationId",
    "AdvancedPermissionCode",
    "AdvancedRoleCode",
    "AdvancedDatabaseConnectionId",
    "AdvancedRegionId",
    "AdvancedRealmId",
    "AdvancedKeycloakUserId",
    "AdvancedTokenId",
    # Backward compatibility aliases
    "ConfigurableValueObject",
    "ConfigurableUserId",
    "ConfigurableTenantId",
    "ConfigurableOrganizationId",
    "ConfigurablePermissionCode",
    "ConfigurableRoleCode",
    "ConfigurableDatabaseConnectionId",
    "ConfigurableRegionId",
    "ConfigurableRealmId",
    "ConfigurableKeycloakUserId",
    "ConfigurableTokenId",
]