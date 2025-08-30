"""Authentication infrastructure layer.

External system integrations, repositories, adapters, and factories following maximum separation.
Each component handles exactly one external system concern.
"""

from .adapters import (
    KeycloakAdminAdapter,
    KeycloakOpenIDAdapter, 
    PublicKeyCacheAdapter,
    RedisCacheAdapter,
)
from .repositories import (
    DatabaseUserRepository,
    KeycloakTokenRepository,
    MemoryTokenCache,
    RedisSessionRepository,
)
from .factories import (
    CacheFactory,
    KeycloakClientFactory,
    SessionManagerFactory,
    TokenValidatorFactory,
)