"""
User ID value object for type-safe user identification.

Provides a type-safe wrapper around string-based user identifiers with
UUIDv7 generation for time-ordered, globally unique user IDs.
"""

import uuid
from typing import NewType

# Type-safe user ID based on string
UserId = NewType('UserId', str)


def create_user_id() -> UserId:
    """
    Generate a new user ID using UUIDv7 for time-ordered uniqueness.
    
    UUIDv7 provides:
    - Timestamp-based ordering for better database performance
    - Global uniqueness across distributed systems
    - Sortable IDs that maintain creation order
    
    Returns:
        UserId: A new unique user identifier
        
    Example:
        >>> user_id = create_user_id()
        >>> isinstance(user_id, str)
        True
        >>> len(str(user_id))
        36
    """
    return UserId(str(uuid.uuid7()))


def validate_user_id(user_id: str) -> UserId:
    """
    Validate and convert a string to a UserId.
    
    Args:
        user_id: String representation of a user ID
        
    Returns:
        UserId: Validated user ID
        
    Raises:
        ValueError: If the user_id is not a valid UUID format
        
    Example:
        >>> user_id = validate_user_id("01234567-89ab-cdef-0123-456789abcdef")
        >>> isinstance(user_id, str)
        True
    """
    try:
        # Validate UUID format
        uuid.UUID(user_id)
        return UserId(user_id)
    except ValueError as e:
        raise ValueError(f"Invalid user ID format: {user_id}") from e


def is_valid_user_id(user_id: str) -> bool:
    """
    Check if a string is a valid user ID format.
    
    Args:
        user_id: String to validate
        
    Returns:
        bool: True if valid UUID format, False otherwise
        
    Example:
        >>> is_valid_user_id("01234567-89ab-cdef-0123-456789abcdef")
        True
        >>> is_valid_user_id("invalid-id")
        False
    """
    try:
        uuid.UUID(user_id)
        return True
    except ValueError:
        return False