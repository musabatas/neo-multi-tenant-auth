"""
Neo-Commons Authorization Module.

Complete authorization system focused on roles, permissions, and access control.
Authentication is handled externally by Keycloak.

Architecture:
    - Domain: Core business entities and rules
    - Application: Business logic and workflows  
    - Infrastructure: Database, cache, and external integrations
    - Interfaces: FastAPI dependencies, decorators, and middleware

Key Features:
    - Sub-millisecond permission checks with Redis caching
    - Multi-level RBAC (Platform vs Tenant scoped)
    - Clean Architecture with protocol-based dependency injection
    - Keycloak token validation and session management
    - FastAPI integration with decorators and dependencies

Usage:
    # FastAPI Dependencies
    from neo_commons.auth import get_current_user, require_permission
    
    # Decorators
    from neo_commons.auth import permission_required, role_required
    
    # Services (via DI)
    from neo_commons.auth import PermissionService, RoleService
    
    # Domain Entities
    from neo_commons.auth import Permission, Role, UserContext
"""

# Domain layer - Core business entities and rules
from .domain.entities.permission import Permission, PermissionScope, PermissionGroup
from .domain.entities.role import Role, RoleLevel, RoleAssignment
from .domain.entities.access_control import AccessControlEntry, AccessLevel
from .domain.entities.session import Session, SessionContext, SessionStatus

from .domain.value_objects.permission_check import PermissionCheck, PermissionResult
from .domain.value_objects.user_context import UserContext, UserType
from .domain.value_objects.tenant_context import TenantContext

# Application layer - Business logic and services
from .application.services.permission_service import PermissionService
from .application.services.role_service import RoleService
from .application.services.access_control_service import AccessControlService  
from .application.services.token_validation_service import TokenValidationService

# Infrastructure layer - External implementations
from .infrastructure.repositories.permission_repository import PermissionRepository
from .infrastructure.repositories.role_repository import RoleRepository
from .infrastructure.repositories.access_control_repository import AccessControlRepository
from .infrastructure.repositories.session_repository import SessionRepository
from .infrastructure.cache.redis_permission_cache import RedisPermissionCache
from .infrastructure.cache.redis_auth_cache import RedisAuthCache
from .infrastructure.external.keycloak_token_validator import KeycloakTokenValidator

# Interfaces layer - FastAPI integration
from .interfaces.dependencies.auth_dependencies import (
    get_current_user,
    get_user_context,
    get_tenant_context,
    require_permission,
    require_any_permission,
    require_all_permissions,
    get_permission_service,
    get_role_service
)

from .interfaces.decorators.permission_decorators import (
    permission_required,
    role_required,
    superadmin_required,
    tenant_access_required,
    PermissionError
)

# Protocols for dependency injection
from .domain.protocols.repository_protocols import (
    PermissionRepositoryProtocol,
    RoleRepositoryProtocol,
    AccessControlRepositoryProtocol,
    SessionRepositoryProtocol
)

from .domain.protocols.service_protocols import (
    PermissionServiceProtocol,
    RoleServiceProtocol,
    AccessControlServiceProtocol,
    TokenValidationServiceProtocol
)

from .domain.protocols.cache_protocols import (
    AuthCacheProtocol,
    PermissionCacheProtocol
)

__all__ = [
    # Domain Entities
    "Permission",
    "PermissionScope",
    "PermissionGroup",
    "Role", 
    "RoleLevel",
    "RoleAssignment",
    "AccessControlEntry",
    "AccessLevel",
    "Session",
    "SessionContext", 
    "SessionStatus",
    
    # Value Objects
    "PermissionCheck",
    "PermissionResult",
    "UserContext",
    "UserType",
    "TenantContext",
    
    # Application Services
    "PermissionService",
    "RoleService",
    "AccessControlService",
    "TokenValidationService",
    
    # Infrastructure
    "PermissionRepository",
    "RoleRepository",
    "AccessControlRepository",
    "SessionRepository", 
    "RedisPermissionCache",
    "RedisAuthCache",
    "KeycloakTokenValidator",
    
    # FastAPI Dependencies
    "get_current_user",
    "get_user_context",
    "get_tenant_context", 
    "require_permission",
    "require_any_permission",
    "require_all_permissions",
    "get_permission_service",
    "get_role_service",
    
    # Decorators
    "permission_required",
    "role_required",
    "superadmin_required",
    "tenant_access_required",
    "PermissionError",
    
    # Protocols
    "PermissionRepositoryProtocol",
    "RoleRepositoryProtocol", 
    "AccessControlRepositoryProtocol",
    "SessionRepositoryProtocol",
    "PermissionServiceProtocol",
    "RoleServiceProtocol",
    "AccessControlServiceProtocol", 
    "TokenValidationServiceProtocol",
    "AuthCacheProtocol",
    "PermissionCacheProtocol"
]

# Version and metadata
__version__ = "1.0.0"
__author__ = "NeoMultiTenant Team"
__description__ = "Authorization module with sub-millisecond permission checks"