"""
Public API for neo-commons - Stable interface for consumers.

This module provides the primary public interface that consuming services
should use for common operations. The internal module organization may change,
but this interface remains stable across versions.

Quick Start:
    # Authentication and authorization
    from neo_commons.public import CheckPermission, get_current_user
    
    @router.get("/users")
    async def list_users(
        current_user = Depends(CheckPermission(["users:list"]))
    ):
        return await user_service.list_users()
    
    # Caching
    from neo_commons.public import CacheClient
    
    cache = CacheClient.create_redis_cache()
    await cache.set("key", "value", ttl=300)
    
    # Database operations
    from neo_commons.public import get_database_connection
    
    db = await get_database_connection("tenant-123")
    
    # Utilities
    from neo_commons.public import generate_uuid_v7, utc_now
    
    user_id = generate_uuid_v7()
    timestamp = utc_now()

Upgrade Path:
    To migrate from direct module imports to the public API:
    
    OLD: from neo_commons.auth.dependencies import CheckPermission
    NEW: from neo_commons.public import CheckPermission
    
    OLD: from neo_commons.cache.client import CacheClient  
    NEW: from neo_commons.public import CacheClient
    
    OLD: from neo_commons.utils.uuid import generate_uuid_v7
    NEW: from neo_commons.public import generate_uuid_v7
"""

# ============ Core Domain Exports ============
# New core domain concepts
from .core import (
    # Entities
    User,
    Tenant,
    Organization,
    
    # Value Objects
    UserId,
    TenantId,
    OrganizationId,
    PermissionCode,
    create_user_id,
    create_tenant_id,
    create_organization_id,
    create_permission_code,
    
    # Contracts
    DomainEventProtocol,
    EntityProtocol,
    ValueObjectProtocol,
    AggregateRootProtocol,
)

# ============ Authentication & Authorization ============
# Essential auth exports for everyday use
from .auth.fastapi import (
    CheckPermission,
    CurrentUser,
    TokenData,
)

from .auth.fastapi import (
    RequirePermission,
)

from .auth.identity import (
    DefaultUserIdentityResolver,
)

# Legacy imports that may still be needed
from .auth.sessions import (
    DefaultGuestAuthService,
)

# Create convenient aliases
require_permission = RequirePermission
GuestOrAuthenticated = DefaultGuestAuthService  # This will need proper implementation
GuestSessionInfo = dict  # Placeholder - this was likely a dict type

# ============ Caching ============
# Core caching functionality
from .cache import (
    CacheManager,
    CacheConfig,
    TenantAwareCacheService,
)

# ============ Database ============
# Database connection and utilities
from .database import (
    get_database_connection,
)

# ============ Models & Responses ============
# Standard response models
from .models.base import (
    APIResponse,
    PaginatedResponse,
    PaginationParams,
    BaseSchema,
    TimestampMixin,
    UUIDMixin,
)

# ============ Utilities ============
# Essential utilities
from .utils.uuid import generate_uuid_v7
from .utils.datetime import utc_now
from .utils.encryption import encrypt_data, decrypt_data

# ============ Exceptions ============
# Common exceptions
from .exceptions.base import (
    NeoException,
    ValidationError,
    NotFoundError,
    ConflictError,
    UnauthorizedError,
    ForbiddenError,
)

__all__ = [
    # ============ Core Domain ============
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
    
    # ============ Authentication & Authorization ============
    "CheckPermission",
    "CurrentUser", 
    "TokenData",
    "GuestOrAuthenticated",
    "GuestSessionInfo",
    "require_permission",
    "RequirePermission",
    "DefaultUserIdentityResolver",
    
    # ============ Caching ============
    "CacheManager",
    "CacheConfig",
    "TenantAwareCacheService",
    
    # ============ Database ============
    "get_database_connection",
    
    # ============ Models & Responses ============
    "APIResponse",
    "PaginatedResponse", 
    "PaginationParams",
    "BaseSchema",
    "TimestampMixin",
    "UUIDMixin",
    
    # ============ Utilities ============
    "generate_uuid_v7",
    "utc_now",
    "encrypt_data",
    "decrypt_data",
    
    # ============ Exceptions ============
    "NeoException",
    "ValidationError",
    "NotFoundError",
    "ConflictError", 
    "UnauthorizedError",
    "ForbiddenError",
]