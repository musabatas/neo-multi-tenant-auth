"""Shared domain concerns for neo-commons.

This module contains cross-cutting entities, protocols, and value objects
that are used across multiple domains.
"""

# Import shared entities - only what's actually in shared
from .context import RequestContext

# Note: Organization and Tenant entities have moved to features/
# Import them directly from features when needed to avoid circular dependencies

# Import shared value objects
from ..value_objects.identifiers import (
    UserId,
    TenantId,
    OrganizationId,
    PermissionCode,
    RoleCode,
    DatabaseConnectionId,
    RegionId
)

# Import shared protocols
from .domain import (
    TenantContextProtocol,
    UserIdentityProtocol,
    PermissionCheckerProtocol,
    UserResolverProtocol,
    SchemaResolverProtocol
)
from .application import (
    ConfigurationProtocol,
    EventPublisherProtocol,
    EventHandlerProtocol,
    ValidationProtocol,
    EncryptionProtocol
)

__all__ = [
    # Entities
    "RequestContext",
    
    # Value Objects
    "UserId",
    "TenantId", 
    "OrganizationId",
    "PermissionCode",
    "RoleCode",
    "DatabaseConnectionId",
    "RegionId",
    
    # Protocols
    "TenantContextProtocol",
    "UserIdentityProtocol", 
    "PermissionCheckerProtocol",
    "UserResolverProtocol",
    "SchemaResolverProtocol",
    "ConfigurationProtocol",
    "EventPublisherProtocol",
    "EventHandlerProtocol",
    "ValidationProtocol",
    "EncryptionProtocol",
]