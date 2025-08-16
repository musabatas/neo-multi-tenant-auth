"""
Base service pattern for business logic operations.

Service wrapper that imports from neo-commons and provides NeoAdminApi-specific
service patterns while maintaining backward compatibility.
"""

from typing import TypeVar, Generic

# Import base service class from neo-commons
from neo_commons.services.base import BaseService as NeoBaseService

# Import service-specific exceptions for compatibility
from src.common.exceptions.base import NeoAdminException

T = TypeVar('T')


class BaseService(NeoBaseService[T], Generic[T]):
    """
    Service wrapper for NeoAdminApi that extends neo-commons BaseService.
    
    Provides additional service-specific patterns while maintaining
    full compatibility with existing NeoAdminApi code.
    """
    
    def validate_pagination_params(
        self,
        page: int,
        page_size: int,
        max_page_size: int = 100
    ):
        """Override to convert ValidationError to NeoAdminException for service compatibility."""
        try:
            return super().validate_pagination_params(page, page_size, max_page_size)
        except Exception as e:
            # Convert neo-commons ValidationError to NeoAdminException for service compatibility
            raise NeoAdminException(
                status_code=400,
                error_code="PAGINATION_VALIDATION_ERROR",
                message=str(e)
            )