"""
Keycloak exception classes.

Custom exception types for Keycloak operations.
"""
from .realm_exceptions import (
    RealmManagerException,
    RealmNotConfiguredException,
    RealmCreationException
)

__all__ = [
    "RealmManagerException",
    "RealmNotConfiguredException",
    "RealmCreationException"
]