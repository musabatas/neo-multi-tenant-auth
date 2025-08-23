"""Auth feature adapters.

Contains adapters for external services like Keycloak.
"""

from .keycloak_admin import KeycloakAdminAdapter
from .keycloak_openid import KeycloakOpenIDAdapter

__all__ = [
    "KeycloakAdminAdapter",
    "KeycloakOpenIDAdapter",
]