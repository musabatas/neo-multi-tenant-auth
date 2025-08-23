"""
Tenant ID value object for type-safe tenant identification.

Provides a type-safe wrapper around string-based tenant identifiers with
UUIDv7 generation for time-ordered, globally unique tenant IDs.
"""

import uuid
from typing import NewType

# Type-safe tenant ID based on string
TenantId = NewType('TenantId', str)


def create_tenant_id() -> TenantId:
    """
    Generate a new tenant ID using UUIDv7 for time-ordered uniqueness.
    
    UUIDv7 provides:
    - Timestamp-based ordering for better database performance
    - Global uniqueness across distributed systems
    - Sortable IDs that maintain creation order
    
    Returns:
        TenantId: A new unique tenant identifier
        
    Example:
        >>> tenant_id = create_tenant_id()
        >>> isinstance(tenant_id, str)
        True
        >>> len(str(tenant_id))
        36
    """
    return TenantId(str(uuid.uuid7()))


def validate_tenant_id(tenant_id: str) -> TenantId:
    """
    Validate and convert a string to a TenantId.
    
    Args:
        tenant_id: String representation of a tenant ID
        
    Returns:
        TenantId: Validated tenant ID
        
    Raises:
        ValueError: If the tenant_id is not a valid UUID format
        
    Example:
        >>> tenant_id = validate_tenant_id("01234567-89ab-cdef-0123-456789abcdef")
        >>> isinstance(tenant_id, str)
        True
    """
    try:
        # Validate UUID format
        uuid.UUID(tenant_id)
        return TenantId(tenant_id)
    except ValueError as e:
        raise ValueError(f"Invalid tenant ID format: {tenant_id}") from e


def is_valid_tenant_id(tenant_id: str) -> bool:
    """
    Check if a string is a valid tenant ID format.
    
    Args:
        tenant_id: String to validate
        
    Returns:
        bool: True if valid UUID format, False otherwise
        
    Example:
        >>> is_valid_tenant_id("01234567-89ab-cdef-0123-456789abcdef")
        True
        >>> is_valid_tenant_id("invalid-id")
        False
    """
    try:
        uuid.UUID(tenant_id)
        return True
    except ValueError:
        return False