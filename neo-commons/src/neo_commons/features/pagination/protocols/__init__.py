"""Pagination protocols for repositories and services."""

from .repository import (
    PaginatedRepository,
    CursorPaginatedRepository,
    HybridPaginatedRepository
)

from .service import (
    PaginatedService,
    CursorPaginatedService
)

__all__ = [
    "PaginatedRepository",
    "CursorPaginatedRepository", 
    "HybridPaginatedRepository",
    "PaginatedService",
    "CursorPaginatedService"
]