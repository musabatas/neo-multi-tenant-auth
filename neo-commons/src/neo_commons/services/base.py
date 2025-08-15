"""
Base service pattern for business logic operations.

Generic service classes that provide common business logic patterns
for all platform services in the NeoMultiTenant ecosystem.
"""

from typing import Any, TypeVar, Generic
from abc import ABC
import logging

# Use generic exceptions from neo-commons for platform-wide consistency
from neo_commons.exceptions.base import (
    ValidationError,
    NotFoundError,
    ConflictError
)
from neo_commons.models.pagination import PaginationParams, PaginationMetadata, PaginationHelper

T = TypeVar('T')

logger = logging.getLogger(__name__)


class BaseService(ABC, Generic[T]):
    """
    Base service class providing common business logic patterns.
    
    This class implements common patterns for:
    - Pagination using neo-commons utilities
    - Error handling and logging
    - Response formatting
    """
    
    def create_pagination_metadata(
        self,
        page: int,
        page_size: int,
        total_count: int
    ) -> PaginationMetadata:
        """Create pagination metadata from query results.
        
        Args:
            page: Current page number
            page_size: Items per page
            total_count: Total number of items
            
        Returns:
            PaginationMetadata object
        """
        return PaginationHelper.create_metadata(page, page_size, total_count)
    
    def validate_pagination_params(
        self,
        page: int,
        page_size: int,
        max_page_size: int = 100
    ) -> PaginationParams:
        """Validate and create pagination parameters.
        
        Args:
            page: Requested page number
            page_size: Requested page size
            max_page_size: Maximum allowed page size
            
        Returns:
            Validated PaginationParams
            
        Raises:
            ValidationError: If parameters are invalid
        """
        try:
            PaginationHelper.validate_params(page, page_size, max_page_size)
            return PaginationParams(page=page, page_size=page_size)
        except Exception as e:
            # Use generic neo-commons ValidationError
            raise ValidationError(
                message=str(e),
                errors=[{
                    "field": "pagination",
                    "value": f"page={page}, page_size={page_size}",
                    "requirement": f"page >= 1, 1 <= page_size <= {max_page_size}"
                }]
            )
    
    def handle_not_found(
        self,
        resource_type: str,
        resource_id: str
    ) -> None:
        """Raise a standardized not found exception.
        
        Args:
            resource_type: Type of resource (e.g., "User", "Organization")
            resource_id: ID of the resource
            
        Raises:
            NotFoundError: 404 not found error
        """
        raise NotFoundError(
            resource=resource_type,
            identifier=resource_id
        )
    
    def handle_conflict(
        self,
        resource_type: str,
        conflict_field: str,
        conflict_value: Any
    ) -> None:
        """Raise a standardized conflict exception.
        
        Args:
            resource_type: Type of resource
            conflict_field: Field causing conflict
            conflict_value: Value causing conflict
            
        Raises:
            ConflictError: 409 conflict error
        """
        raise ConflictError(
            message=f"{resource_type} with {conflict_field} '{conflict_value}' already exists",
            conflicting_field=conflict_field,
            conflicting_value=conflict_value
        )
    
    def handle_validation_error(
        self,
        field: str,
        value: Any,
        requirement: str
    ) -> None:
        """Raise a standardized validation exception.
        
        Args:
            field: Field that failed validation
            value: Invalid value
            requirement: What the requirement is
            
        Raises:
            ValidationError: 400 validation error
        """
        raise ValidationError(
            message=f"Invalid {field}: '{value}'. {requirement}",
            errors=[{
                "field": field,
                "value": str(value),
                "requirement": requirement
            }]
        )