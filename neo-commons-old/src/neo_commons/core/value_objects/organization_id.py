"""
Organization ID value object for type-safe organization identification.

Provides a type-safe wrapper around string-based organization identifiers with
UUIDv7 generation for time-ordered, globally unique organization IDs.
"""

import uuid
from typing import NewType

# Type-safe organization ID based on string
OrganizationId = NewType('OrganizationId', str)


def create_organization_id() -> OrganizationId:
    """
    Generate a new organization ID using UUIDv7 for time-ordered uniqueness.
    
    UUIDv7 provides:
    - Timestamp-based ordering for better database performance
    - Global uniqueness across distributed systems
    - Sortable IDs that maintain creation order
    
    Returns:
        OrganizationId: A new unique organization identifier
        
    Example:
        >>> org_id = create_organization_id()
        >>> isinstance(org_id, str)
        True
        >>> len(str(org_id))
        36
    """
    return OrganizationId(str(uuid.uuid7()))


def validate_organization_id(organization_id: str) -> OrganizationId:
    """
    Validate and convert a string to an OrganizationId.
    
    Args:
        organization_id: String representation of an organization ID
        
    Returns:
        OrganizationId: Validated organization ID
        
    Raises:
        ValueError: If the organization_id is not a valid UUID format
        
    Example:
        >>> org_id = validate_organization_id("01234567-89ab-cdef-0123-456789abcdef")
        >>> isinstance(org_id, str)
        True
    """
    try:
        # Validate UUID format
        uuid.UUID(organization_id)
        return OrganizationId(organization_id)
    except ValueError as e:
        raise ValueError(f"Invalid organization ID format: {organization_id}") from e


def is_valid_organization_id(organization_id: str) -> bool:
    """
    Check if a string is a valid organization ID format.
    
    Args:
        organization_id: String to validate
        
    Returns:
        bool: True if valid UUID format, False otherwise
        
    Example:
        >>> is_valid_organization_id("01234567-89ab-cdef-0123-456789abcdef")
        True
        >>> is_valid_organization_id("invalid-id")
        False
    """
    try:
        uuid.UUID(organization_id)
        return True
    except ValueError:
        return False