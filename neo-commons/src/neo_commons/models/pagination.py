"""
Pagination models for API responses.
"""

from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, Field

from .base import BaseSchema

T = TypeVar('T')


class PaginationMetadata(BaseSchema):
    """Metadata for paginated responses."""
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of items per page")
    total_pages: int = Field(description="Total number of pages")
    total_items: int = Field(description="Total number of items")
    has_next: bool = Field(description="Whether there is a next page")
    has_previous: bool = Field(description="Whether there is a previous page")
    
    @classmethod
    def create(cls, page: int, page_size: int, total_items: int) -> "PaginationMetadata":
        """Create pagination metadata from basic parameters."""
        total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 0
        
        return cls(
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            total_items=total_items,
            has_next=page < total_pages,
            has_previous=page > 1
        )


class PaginatedResponse(BaseSchema, Generic[T]):
    """Generic paginated response model."""
    items: List[T] = Field(description="List of items for current page")
    pagination: PaginationMetadata = Field(description="Pagination metadata")
    
    @classmethod
    def create(
        cls,
        items: List[T],
        page: int,
        page_size: int,
        total_items: int
    ) -> "PaginatedResponse[T]":
        """Create a paginated response with items and metadata."""
        pagination = PaginationMetadata.create(page, page_size, total_items)
        
        return cls(
            items=items,
            pagination=pagination
        )


class PaginationParams(BaseSchema):
    """Common pagination parameters."""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Get limit for database query."""
        return self.page_size


class CursorPaginationParams(BaseSchema):
    """Cursor-based pagination parameters for large datasets."""
    cursor: Optional[str] = Field(None, description="Cursor for next page")
    limit: int = Field(20, ge=1, le=100, description="Maximum items per page")
    
    
class CursorPaginatedResponse(BaseSchema, Generic[T]):
    """Cursor-based paginated response for large datasets."""
    items: List[T] = Field(description="List of items")
    next_cursor: Optional[str] = Field(None, description="Cursor for next page")
    has_more: bool = Field(description="Whether there are more items")
    
    @classmethod
    def create(
        cls,
        items: List[T],
        next_cursor: Optional[str] = None,
        has_more: bool = False
    ) -> "CursorPaginatedResponse[T]":
        """Create a cursor-based paginated response."""
        return cls(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more
        )