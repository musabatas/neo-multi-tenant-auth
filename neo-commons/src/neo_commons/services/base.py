"""
Base service pattern for business logic operations.
"""

from typing import Optional, Dict, Any, TypeVar, Generic
from abc import ABC
import logging

from neo_commons.exceptions.base import NeoAdminException, NotFoundError, ConflictError, ValidationError
from neo_commons.models.pagination import PaginationParams, PaginationMetadata

T = TypeVar('T')

logger = logging.getLogger(__name__)


class BaseService(ABC, Generic[T]):
    """
    Base service class providing common business logic patterns.
    
    This class implements common patterns for:
    - Pagination metadata creation
    - Error handling and logging
    - Response formatting
    - Validation helpers
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
        return PaginationMetadata.create(page, page_size, total_count)
    
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
        if page < 1:
            raise ValidationError(
                message="Page number must be greater than 0",
                errors=[{
                    "field": "page",
                    "value": str(page),
                    "requirement": "Must be greater than 0"
                }]
            )
        
        if page_size < 1:
            raise ValidationError(
                message="Page size must be greater than 0",
                errors=[{
                    "field": "page_size",
                    "value": str(page_size),
                    "requirement": "Must be greater than 0"
                }]
            )
        
        if page_size > max_page_size:
            raise ValidationError(
                message=f"Page size cannot exceed {max_page_size}",
                errors=[{
                    "field": "page_size",
                    "value": str(page_size),
                    "requirement": f"Must be less than or equal to {max_page_size}"
                }]
            )
        
        return PaginationParams(page=page, page_size=page_size)
    
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
            conflicting_value=str(conflict_value)
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
    
    def validate_required_fields(
        self,
        data: Dict[str, Any],
        required_fields: list[str]
    ) -> None:
        """Validate that all required fields are present and not empty.
        
        Args:
            data: Data dictionary to validate
            required_fields: List of required field names
            
        Raises:
            ValidationError: If any required field is missing or empty
        """
        errors = []
        
        for field in required_fields:
            if field not in data:
                errors.append({
                    "field": field,
                    "value": None,
                    "requirement": "Field is required"
                })
            elif data[field] is None or (isinstance(data[field], str) and not data[field].strip()):
                errors.append({
                    "field": field,
                    "value": data.get(field),
                    "requirement": "Field cannot be empty"
                })
        
        if errors:
            raise ValidationError(
                message="Required field validation failed",
                errors=errors
            )
    
    def validate_field_lengths(
        self,
        data: Dict[str, Any],
        field_lengths: Dict[str, Dict[str, int]]
    ) -> None:
        """Validate field lengths against specified limits.
        
        Args:
            data: Data dictionary to validate
            field_lengths: Dictionary of field names to length constraints
                         Format: {"field_name": {"min": 1, "max": 100}}
            
        Raises:
            ValidationError: If any field violates length constraints
        """
        errors = []
        
        for field, constraints in field_lengths.items():
            if field not in data or data[field] is None:
                continue
                
            value = str(data[field])
            length = len(value)
            
            if "min" in constraints and length < constraints["min"]:
                errors.append({
                    "field": field,
                    "value": value,
                    "requirement": f"Must be at least {constraints['min']} characters"
                })
            
            if "max" in constraints and length > constraints["max"]:
                errors.append({
                    "field": field,
                    "value": value,
                    "requirement": f"Must be at most {constraints['max']} characters"
                })
        
        if errors:
            raise ValidationError(
                message="Field length validation failed",
                errors=errors
            )
    
    def validate_unique_constraint(
        self,
        exists_check_result: bool,
        field: str,
        value: Any,
        resource_type: str = "Resource"
    ) -> None:
        """Validate uniqueness constraint.
        
        Args:
            exists_check_result: Result from repository exists check
            field: Field name that should be unique
            value: Field value
            resource_type: Type of resource for error message
            
        Raises:
            ConflictError: If the constraint is violated
        """
        if exists_check_result:
            self.handle_conflict(resource_type, field, value)
    
    def sanitize_input(
        self,
        data: Dict[str, Any],
        allowed_fields: Optional[list[str]] = None,
        strip_strings: bool = True
    ) -> Dict[str, Any]:
        """Sanitize input data by removing unwanted fields and cleaning strings.
        
        Args:
            data: Input data to sanitize
            allowed_fields: List of allowed field names (if None, all are allowed)
            strip_strings: Whether to strip whitespace from string values
            
        Returns:
            Sanitized data dictionary
        """
        sanitized = {}
        
        for key, value in data.items():
            # Skip fields not in allowed list
            if allowed_fields and key not in allowed_fields:
                continue
            
            # Strip string values if requested
            if strip_strings and isinstance(value, str):
                value = value.strip()
            
            sanitized[key] = value
        
        return sanitized
    
    def log_operation(
        self,
        operation: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log service operation with structured data.
        
        Args:
            operation: Operation being performed (create, update, delete, etc.)
            resource_type: Type of resource being operated on
            resource_id: ID of the resource (if applicable)
            user_id: ID of the user performing the operation
            additional_data: Additional data to include in log
        """
        log_data = {
            "operation": operation,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "user_id": user_id
        }
        
        if additional_data:
            log_data.update(additional_data)
        
        logger.info(f"Service operation: {operation} on {resource_type}", extra=log_data)