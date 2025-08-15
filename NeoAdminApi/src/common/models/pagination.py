"""
Pagination models for API responses.

MIGRATED TO NEO-COMMONS: Now using neo-commons pagination models.
Import compatibility maintained - all existing imports continue to work.
"""

# NEO-COMMONS IMPORT: Use neo-commons pagination models directly
from neo_commons.models.pagination import (
    PaginationMetadata,
    PaginatedResponse,
    PaginationParams,
    CursorPaginationParams,
    CursorPaginatedResponse,
)

# Re-export for backward compatibility
__all__ = [
    "PaginationMetadata",
    "PaginatedResponse", 
    "PaginationParams",
    "CursorPaginationParams",
    "CursorPaginatedResponse",
]