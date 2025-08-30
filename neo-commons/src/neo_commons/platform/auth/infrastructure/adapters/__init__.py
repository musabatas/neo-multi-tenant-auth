"""Authentication infrastructure adapters.

External system adapters following maximum separation principle.
Each adapter handles exactly one external system integration.
"""

from .keycloak_openid_adapter import KeycloakOpenIDAdapter
from .keycloak_admin_adapter import KeycloakAdminAdapter
from .public_key_cache_adapter import PublicKeyCacheAdapter
from .redis_cache_adapter import RedisCacheAdapter

__all__ = [
    "KeycloakOpenIDAdapter",
    "KeycloakAdminAdapter", 
    "PublicKeyCacheAdapter",
    "RedisCacheAdapter",
]