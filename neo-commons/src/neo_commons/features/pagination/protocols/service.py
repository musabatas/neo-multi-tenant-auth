"""Service protocols for pagination support."""

from typing import Protocol, runtime_checkable, TypeVar
from ..entities import (
    OffsetPaginationRequest,
    OffsetPaginationResponse,
    CursorPaginationRequest, 
    CursorPaginationResponse
)

T = TypeVar('T')


@runtime_checkable
class PaginatedService(Protocol[T]):
    """Protocol for services that support pagination."""
    
    async def list_paginated(
        self,
        pagination: OffsetPaginationRequest
    ) -> OffsetPaginationResponse[T]:
        """List items with offset-based pagination.
        
        Args:
            pagination: Pagination request
            
        Returns:
            Paginated response with business logic applied
        """
        ...
    
    async def search_paginated(
        self,
        pagination: OffsetPaginationRequest
    ) -> OffsetPaginationResponse[T]:
        """Search items with pagination.
        
        Args:
            pagination: Pagination request with search query
            
        Returns:
            Paginated search results
        """
        ...


@runtime_checkable
class CursorPaginatedService(Protocol[T]):
    """Protocol for services that support cursor-based pagination."""
    
    async def list_cursor_paginated(
        self,
        pagination: CursorPaginationRequest
    ) -> CursorPaginationResponse[T]:
        """List items with cursor-based pagination.
        
        Args:
            pagination: Cursor pagination request
            
        Returns:
            Cursor paginated response
        """
        ...