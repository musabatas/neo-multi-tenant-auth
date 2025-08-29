"""File management repository implementations.

Data persistence layer implementing file repository protocols using
various storage backends (PostgreSQL, Redis caching, etc.).

Following maximum separation architecture - one file = one purpose.
"""

from .asyncpg_file_repository import AsyncpgFileRepository

__all__ = [
    "AsyncpgFileRepository",
]