"""
Protocol interfaces for model components.

Protocol-based interfaces for base models, pagination, and response handling
to ensure maximum flexibility across different platform services.
"""
from typing import Protocol, Any, Dict, List, Optional, TypeVar, Generic
from pydantic import BaseModel


T = TypeVar('T')


class BaseModelProtocol(Protocol):
    """Protocol for base model operations."""
    
    def model_dump(
        self, 
        *, 
        include: Optional[set] = None,
        exclude: Optional[set] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False
    ) -> Dict[str, Any]:
        """Serialize model to dictionary."""
        ...
    
    def model_dump_json(
        self,
        *,
        include: Optional[set] = None,
        exclude: Optional[set] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False
    ) -> str:
        """Serialize model to JSON string."""
        ...
    
    @classmethod
    def model_validate(cls, obj: Any) -> "BaseModelProtocol":
        """Validate and create model instance from data."""
        ...


class APIResponseProtocol(Protocol[T]):
    """Protocol for standardized API response format."""
    
    success: bool
    data: Optional[T]
    message: str
    errors: List[str]
    metadata: Dict[str, Any]
    
    @classmethod
    def success_response(
        cls,
        data: Optional[T] = None,
        message: str = "Success",
        metadata: Optional[Dict[str, Any]] = None
    ) -> "APIResponseProtocol[T]":
        """Create successful response."""
        ...
    
    @classmethod
    def error_response(
        cls,
        message: str,
        errors: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "APIResponseProtocol[T]":
        """Create error response."""
        ...


class PaginationProtocol(Protocol):
    """Protocol for pagination metadata and parameters."""
    
    page: int
    page_size: int
    total_pages: int
    total_items: int
    has_next: bool
    has_previous: bool
    
    @classmethod
    def create(
        cls,
        page: int,
        page_size: int,
        total_items: int
    ) -> "PaginationProtocol":
        """Create pagination metadata from parameters."""
        ...


class PaginatedResponseProtocol(Protocol[T]):
    """Protocol for paginated response data."""
    
    items: List[T]
    pagination: PaginationProtocol
    
    @classmethod
    def create(
        cls,
        items: List[T],
        page: int,
        page_size: int,
        total_items: int
    ) -> "PaginatedResponseProtocol[T]":
        """Create paginated response with metadata."""
        ...


class FilterableModelProtocol(Protocol):
    """Protocol for models that support filtering operations."""
    
    @classmethod
    def get_filterable_fields(cls) -> List[str]:
        """Get list of fields that can be used for filtering."""
        ...
    
    @classmethod
    def get_sortable_fields(cls) -> List[str]:
        """Get list of fields that can be used for sorting."""
        ...
    
    @classmethod
    def validate_filter_field(cls, field: str) -> bool:
        """Validate if field can be used for filtering."""
        ...
    
    @classmethod
    def validate_sort_field(cls, field: str) -> bool:
        """Validate if field can be used for sorting."""
        ...