"""
Base service pattern for business logic operations.

MIGRATED TO NEO-COMMONS: Now using neo-commons BaseService with additional validation helpers.
Import compatibility maintained - all existing imports continue to work.
"""

from typing import Optional, Dict, Any, TypeVar, Generic

# NEO-COMMONS IMPORT: Use neo-commons BaseService as foundation
from neo_commons.services.base import BaseService as NeoCommonsBaseService

T = TypeVar('T')


class BaseService(NeoCommonsBaseService[T]):
    """
    NeoAdminApi base service extending neo-commons BaseService.
    
    Maintains backward compatibility while leveraging neo-commons infrastructure.
    Adds all the enhanced features from neo-commons including:
    - Enhanced validation helpers (validate_required_fields, validate_field_lengths)
    - Input sanitization methods (sanitize_input)
    - Structured logging (log_operation)
    - Unique constraint validation (validate_unique_constraint)
    """
    
    # All methods are inherited from neo-commons BaseService
    # The neo-commons version includes additional features like:
    # - validate_required_fields() for comprehensive field validation
    # - validate_field_lengths() for length constraint validation
    # - sanitize_input() for cleaning and filtering input data
    # - validate_unique_constraint() for uniqueness validation
    # - log_operation() for structured service operation logging
    # - Enhanced error handling with proper ValidationError usage
    pass


# Re-export the class for backward compatibility
__all__ = [
    "BaseService",
]