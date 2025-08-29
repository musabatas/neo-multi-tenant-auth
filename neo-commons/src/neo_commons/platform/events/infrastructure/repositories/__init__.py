"""Event repository implementations.

This module contains concrete implementations of event repositories
following the Maximum Separation Architecture principle.
"""

from .asyncpg_event_repository import AsyncPGEventRepository

__all__ = [
    "AsyncPGEventRepository",
]