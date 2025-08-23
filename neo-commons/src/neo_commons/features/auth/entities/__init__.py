"""Auth feature entities.

Contains domain objects and protocol interfaces for authentication.
"""

from .auth_context import AuthContext
from .jwt_token import JWTToken
from .keycloak_config import KeycloakConfig
from .protocols import (
    JWTValidatorProtocol,
    KeycloakClientProtocol,
    RealmManagerProtocol,
    UserMapperProtocol,
)
from .realm import Realm

__all__ = [
    # Domain entities
    "AuthContext",
    "JWTToken",
    "KeycloakConfig", 
    "Realm",
    # Protocols
    "JWTValidatorProtocol",
    "KeycloakClientProtocol",
    "RealmManagerProtocol",
    "UserMapperProtocol",
]