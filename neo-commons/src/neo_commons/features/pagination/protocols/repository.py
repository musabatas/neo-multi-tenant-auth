"""Repository protocols for pagination support."""

from typing import Protocol, runtime_checkable, TypeVar, List, Tuple, Optional
from ..entities import (
    OffsetPaginationRequest,
    OffsetPaginationResponse, 
    CursorPaginationRequest,
    CursorPaginationResponse
)

T = TypeVar('T')


@runtime_checkable
class PaginatedRepository(Protocol[T]):
    """Protocol for repositories that support offset-based pagination."""
    
    async def find_paginated(
        self, 
        pagination: OffsetPaginationRequest
    ) -> OffsetPaginationResponse[T]:
        """Find items with offset-based pagination.
        
        Args:
            pagination: Pagination request with page, per_page, sorts, and filters
            
        Returns:
            Paginated response with items, total count, and page information
        """
        ...
    
    async def count_filtered(self, pagination: OffsetPaginationRequest) -> int:
        """Count total items matching pagination filters.
        
        Args:
            pagination: Pagination request with filters and search query
            
        Returns:
            Total count of matching items
        """
        ...


@runtime_checkable  
class CursorPaginatedRepository(Protocol[T]):
    """Protocol for repositories that support cursor-based pagination."""
    
    async def find_cursor_paginated(
        self,
        pagination: CursorPaginationRequest
    ) -> CursorPaginationResponse[T]:
        """Find items with cursor-based pagination.
        
        Args:
            pagination: Cursor pagination request with limit, cursors, sorts, and filters
            
        Returns:
            Cursor paginated response with items and cursor information
        """
        ...
    
    async def estimate_total(self, pagination: CursorPaginationRequest) -> Optional[int]:
        """Get estimated total count for cursor pagination.
        
        Args:
            pagination: Cursor pagination request with filters
            
        Returns:
            Estimated total count, or None if not available
        """
        ...


@runtime_checkable
class HybridPaginatedRepository(PaginatedRepository[T], CursorPaginatedRepository[T], Protocol):
    """Protocol for repositories supporting both pagination types."""
    pass