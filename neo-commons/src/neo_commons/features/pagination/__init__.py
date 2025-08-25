"""Perfect pagination implementation for neo-commons.

This module provides a comprehensive pagination system with:
- Offset-based pagination (traditional page/limit)
- Cursor-based pagination (for large datasets)
- Performance metadata and monitoring
- Repository and service mixins for easy integration
- Protocol-based design for flexibility
"""

# Core entities
from .entities import (
    # Requests
    OffsetPaginationRequest,
    CursorPaginationRequest,
    SortField,
    SortOrder,
    PaginationRequest,
    
    # Responses  
    OffsetPaginationResponse,
    CursorPaginationResponse,
    PaginationResponse,
    PaginationMetadata,
    
    # Type aliases
    OffsetPagination,
    CursorPagination
)

# Protocols
from .protocols import (
    PaginatedRepository,
    CursorPaginatedRepository, 
    HybridPaginatedRepository,
    PaginatedService,
    CursorPaginatedService
)

# Mixins
from .mixins import (
    PaginatedRepositoryMixin,
    CursorPaginatedRepositoryMixin
)

__all__ = [
    # Entities - Requests
    "OffsetPaginationRequest",
    "CursorPaginationRequest", 
    "SortField",
    "SortOrder",
    "PaginationRequest",
    
    # Entities - Responses
    "OffsetPaginationResponse",
    "CursorPaginationResponse",
    "PaginationResponse", 
    "PaginationMetadata",
    
    # Type aliases
    "OffsetPagination",
    "CursorPagination",
    
    # Protocols
    "PaginatedRepository",
    "CursorPaginatedRepository",
    "HybridPaginatedRepository", 
    "PaginatedService",
    "CursorPaginatedService",
    
    # Mixins
    "PaginatedRepositoryMixin",
    "CursorPaginatedRepositoryMixin"
]