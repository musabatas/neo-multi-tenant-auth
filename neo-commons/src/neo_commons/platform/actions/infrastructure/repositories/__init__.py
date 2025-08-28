"""Action repository implementations for platform actions infrastructure.

This module contains concrete implementations of the ActionRepository protocol
following maximum separation architecture patterns.
"""

from .asyncpg_action_repository import AsyncpgActionRepository, create_asyncpg_action_repository

__all__ = [
    "AsyncpgActionRepository",
    "create_asyncpg_action_repository",
]