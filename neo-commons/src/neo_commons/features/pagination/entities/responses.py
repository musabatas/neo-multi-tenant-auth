"""Pagination response entities and metadata."""

from dataclasses import dataclass, field
from typing import Generic, TypeVar, List, Optional, Dict, Any
from datetime import datetime

T = TypeVar('T')


@dataclass(frozen=True)
class PaginationMetadata:
    """Pagination metadata for performance tracking."""
    
    query_duration_ms: Optional[float] = None
    count_duration_ms: Optional[float] = None
    total_duration_ms: Optional[float] = None
    index_used: Optional[str] = None
    estimated_total: bool = False
    cache_hit: bool = False
    
    @classmethod
    def create_performance_metadata(
        cls,
        query_start: datetime,
        query_end: datetime,
        count_start: Optional[datetime] = None,
        count_end: Optional[datetime] = None,
        **kwargs
    ) -> 'PaginationMetadata':
        """Create metadata with calculated durations."""
        query_duration = (query_end - query_start).total_seconds() * 1000
        
        count_duration = None
        if count_start and count_end:
            count_duration = (count_end - count_start).total_seconds() * 1000
        
        total_duration = query_duration
        if count_duration:
            total_duration += count_duration
            
        return cls(
            query_duration_ms=query_duration,
            count_duration_ms=count_duration,
            total_duration_ms=total_duration,
            **kwargs
        )


class PaginationResponse(Generic[T]):
    """Base pagination response with common methods."""
    
    @property
    def count(self) -> int:
        """Get number of items in current page."""
        return len(self.items)
    
    @property
    def has_items(self) -> bool:
        """Check if response has any items."""
        return len(self.items) > 0


@dataclass(frozen=True) 
class OffsetPaginationResponse(PaginationResponse[T]):
    """Offset-based pagination response with page info."""
    
    items: List[T]
    total: int
    page: int
    per_page: int
    metadata: Optional[PaginationMetadata] = None
    
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.per_page == 0:
            return 0
        return (self.total + self.per_page - 1) // self.per_page
    
    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.total_pages
    
    @property
    def has_prev(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1
    
    @property
    def next_page(self) -> Optional[int]:
        """Get next page number."""
        return self.page + 1 if self.has_next else None
    
    @property
    def prev_page(self) -> Optional[int]:
        """Get previous page number."""
        return self.page - 1 if self.has_prev else None
    
    @property
    def offset(self) -> int:
        """Get current offset."""
        return (self.page - 1) * self.per_page
    
    @property
    def page_info(self) -> Dict[str, Any]:
        """Get comprehensive page information."""
        return {
            "current_page": self.page,
            "per_page": self.per_page,
            "total_items": self.total,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
            "next_page": self.next_page,
            "prev_page": self.prev_page,
            "offset": self.offset,
            "items_on_page": self.count
        }


@dataclass(frozen=True)
class CursorPaginationResponse(PaginationResponse[T]):
    """Cursor-based pagination response for large datasets."""
    
    items: List[T]
    next_cursor: Optional[str] = None
    prev_cursor: Optional[str] = None  
    has_more: bool = False
    estimated_total: Optional[int] = None
    metadata: Optional[PaginationMetadata] = None
    
    @property
    def has_next(self) -> bool:
        """Check if there are more items."""
        return self.has_more and self.next_cursor is not None
    
    @property
    def has_prev(self) -> bool:
        """Check if there are previous items."""
        return self.prev_cursor is not None
    
    @property
    def cursor_info(self) -> Dict[str, Any]:
        """Get cursor pagination information."""
        return {
            "items_count": self.count,
            "has_next": self.has_next,
            "has_prev": self.has_prev, 
            "next_cursor": self.next_cursor,
            "prev_cursor": self.prev_cursor,
            "estimated_total": self.estimated_total
        }