"""Pagination entities for requests, responses, and metadata."""

from .requests import (
    PaginationRequest,
    OffsetPaginationRequest,
    CursorPaginationRequest,
    SortField,
    SortOrder,
    # Type aliases
    OffsetPagination,
    CursorPagination
)

from .responses import (
    PaginationResponse,
    OffsetPaginationResponse,
    CursorPaginationResponse,
    PaginationMetadata
)

__all__ = [
    # Requests
    "PaginationRequest",
    "OffsetPaginationRequest", 
    "CursorPaginationRequest",
    "SortField",
    "SortOrder",
    
    # Type aliases
    "OffsetPagination",
    "CursorPagination",
    
    # Responses
    "PaginationResponse",
    "OffsetPaginationResponse",
    "CursorPaginationResponse",
    "PaginationMetadata"
]