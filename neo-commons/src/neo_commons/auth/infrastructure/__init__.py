"""
Authorization infrastructure layer - External concerns and implementations.

This layer implements domain protocols with external systems:
- Database repositories (AsyncPG)
- Cache implementations (Redis)
- Keycloak integration
- External services
"""

from .repositories.permission_repository import PermissionRepository
from .repositories.role_repository import RoleRepository
from .repositories.access_control_repository import AccessControlRepository
from .repositories.session_repository import SessionRepository

from .cache.redis_permission_cache import RedisPermissionCache
from .cache.redis_auth_cache import RedisAuthCache

from .external.keycloak_token_validator import KeycloakTokenValidator

__all__ = [
    # Repositories
    "PermissionRepository",
    "RoleRepository",
    "AccessControlRepository", 
    "SessionRepository",
    
    # Cache implementations
    "RedisPermissionCache",
    "RedisAuthCache",
    
    # External integrations
    "KeycloakTokenValidator"
]