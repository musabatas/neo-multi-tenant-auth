"""
Core domain module for neo-commons.

This module provides the foundational domain concepts shared across all
neo-commons modules, including entities, value objects, and cross-cutting
contracts that define the platform's core business rules.

Features:
- Immutable domain entities (User, Tenant, Organization)
- Type-safe value objects with validation
- Cross-module protocol contracts
- Platform-wide constants and types

Example Usage:
    from neo_commons.core.entities import User
    from neo_commons.core.value_objects import UserId, create_user_id
    
    user_id = create_user_id()
    user = User(
        id=user_id,
        tenant_id=TenantId("tenant-123"),
        email="user@example.com"
    )
"""

# Core entities
from .entities import (
    User,
    Tenant,
    Organization,
)

# Core value objects
from .value_objects import (
    UserId,
    TenantId,
    OrganizationId,
    PermissionCode,
    create_user_id,
    create_tenant_id,
    create_organization_id,
    create_permission_code,
)

# Cross-cutting contracts
from .contracts import (
    DomainEventProtocol,
    EntityProtocol,
    ValueObjectProtocol,
    AggregateRootProtocol,
)

__all__ = [
    # Entities
    "User",
    "Tenant", 
    "Organization",
    
    # Value Objects
    "UserId",
    "TenantId",
    "OrganizationId", 
    "PermissionCode",
    "create_user_id",
    "create_tenant_id",
    "create_organization_id",
    "create_permission_code",
    
    # Contracts
    "DomainEventProtocol",
    "EntityProtocol",
    "ValueObjectProtocol",
    "AggregateRootProtocol",
]