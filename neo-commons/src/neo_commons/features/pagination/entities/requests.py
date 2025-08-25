"""Pagination request entities and enums."""

from dataclasses import dataclass, field
from typing import Optional, List, Any, Dict, Union
from enum import Enum


class SortOrder(str, Enum):
    """Sort order enumeration."""
    ASC = "asc"
    DESC = "desc"
    
    def to_sql(self) -> str:
        """Convert to SQL ORDER BY clause."""
        return "ASC" if self == SortOrder.ASC else "DESC"


@dataclass(frozen=True)
class SortField:
    """Sort field specification with validation."""
    
    field: str
    order: SortOrder = SortOrder.ASC
    nulls_last: bool = True
    
    def to_sql(self) -> str:
        """Convert to SQL ORDER BY clause fragment."""
        nulls_clause = "NULLS LAST" if self.nulls_last else "NULLS FIRST"
        return f"{self.field} {self.order.to_sql()} {nulls_clause}"
    
    def __post_init__(self):
        """Validate field name for SQL injection prevention."""
        if not self.field or not self.field.replace("_", "").replace(".", "").isalnum():
            raise ValueError(f"Invalid field name: {self.field}")


@dataclass(frozen=True)  
class PaginationRequest:
    """Base pagination request."""
    
    sort_fields: List[SortField] = field(default_factory=lambda: [SortField("id")])
    filters: Optional[Dict[str, Any]] = field(default_factory=dict)
    search_query: Optional[str] = None
    
    def get_order_by_sql(self) -> str:
        """Get SQL ORDER BY clause."""
        if not self.sort_fields:
            return "ORDER BY id ASC NULLS LAST"
        
        clauses = [sort_field.to_sql() for sort_field in self.sort_fields]
        return f"ORDER BY {', '.join(clauses)}"


@dataclass(frozen=True)
class OffsetPaginationRequest(PaginationRequest):
    """Offset-based pagination request (traditional page/limit)."""
    
    page: int = 1
    per_page: int = 50
    
    def __post_init__(self):
        """Validate pagination parameters."""
        if self.page < 1:
            raise ValueError("Page must be >= 1")
        if self.per_page < 1 or self.per_page > 1000:
            raise ValueError("Per page must be between 1 and 1000")
    
    @property
    def offset(self) -> int:
        """Calculate offset from page and per_page."""
        return (self.page - 1) * self.per_page
    
    @property  
    def limit(self) -> int:
        """Get limit (alias for per_page)."""
        return self.per_page


@dataclass(frozen=True)
class CursorPaginationRequest(PaginationRequest):
    """Cursor-based pagination request (for large datasets)."""
    
    limit: int = 50
    cursor_after: Optional[str] = None
    cursor_before: Optional[str] = None
    
    def __post_init__(self):
        """Validate cursor pagination parameters.""" 
        if self.limit < 1 or self.limit > 1000:
            raise ValueError("Limit must be between 1 and 1000")
        if self.cursor_after and self.cursor_before:
            raise ValueError("Cannot specify both cursor_after and cursor_before")


# Type aliases for convenience
OffsetPagination = OffsetPaginationRequest
CursorPagination = CursorPaginationRequest