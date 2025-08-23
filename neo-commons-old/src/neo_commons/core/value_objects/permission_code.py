"""
Permission code value object for type-safe permission identification.

Provides a type-safe wrapper around string-based permission codes with
validation for the standard format: resource.action.scope
"""

import re
from typing import NewType

# Type-safe permission code based on string
PermissionCode = NewType('PermissionCode', str)

# Permission code format: resource.action.scope
# Examples: users.read.own, admin.write.tenant, reports.delete.all
PERMISSION_CODE_PATTERN = re.compile(r'^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$')


def create_permission_code(resource: str, action: str, scope: str) -> PermissionCode:
    """
    Create a new permission code from resource, action, and scope.
    
    Args:
        resource: The resource being accessed (e.g., 'users', 'reports')
        action: The action being performed (e.g., 'read', 'write', 'delete')
        scope: The scope of access (e.g., 'own', 'team', 'tenant', 'all')
        
    Returns:
        PermissionCode: A validated permission code
        
    Raises:
        ValueError: If any component is invalid
        
    Example:
        >>> perm = create_permission_code("users", "read", "own")
        >>> str(perm)
        'users.read.own'
    """
    # Validate individual components
    if not _is_valid_component(resource):
        raise ValueError(f"Invalid resource component: {resource}")
    if not _is_valid_component(action):
        raise ValueError(f"Invalid action component: {action}")
    if not _is_valid_component(scope):
        raise ValueError(f"Invalid scope component: {scope}")
    
    permission_code = f"{resource}.{action}.{scope}"
    return PermissionCode(permission_code)


def validate_permission_code(permission_code: str) -> PermissionCode:
    """
    Validate and convert a string to a PermissionCode.
    
    Args:
        permission_code: String representation of a permission code
        
    Returns:
        PermissionCode: Validated permission code
        
    Raises:
        ValueError: If the permission_code doesn't match the required format
        
    Example:
        >>> perm = validate_permission_code("users.read.own")
        >>> isinstance(perm, str)
        True
    """
    if not is_valid_permission_code(permission_code):
        raise ValueError(
            f"Invalid permission code format: {permission_code}. "
            f"Expected format: resource.action.scope (e.g., 'users.read.own')"
        )
    
    return PermissionCode(permission_code)


def is_valid_permission_code(permission_code: str) -> bool:
    """
    Check if a string is a valid permission code format.
    
    Permission codes must follow the pattern: resource.action.scope
    where each component contains only lowercase letters, numbers, and underscores,
    and starts with a letter.
    
    Args:
        permission_code: String to validate
        
    Returns:
        bool: True if valid permission code format, False otherwise
        
    Example:
        >>> is_valid_permission_code("users.read.own")
        True
        >>> is_valid_permission_code("Users.Read.Own")  # uppercase not allowed
        False
        >>> is_valid_permission_code("users.read")  # missing scope
        False
    """
    return bool(PERMISSION_CODE_PATTERN.match(permission_code))


def parse_permission_code(permission_code: PermissionCode) -> tuple[str, str, str]:
    """
    Parse a permission code into its resource, action, and scope components.
    
    Args:
        permission_code: Valid permission code to parse
        
    Returns:
        tuple[str, str, str]: (resource, action, scope)
        
    Example:
        >>> resource, action, scope = parse_permission_code(PermissionCode("users.read.own"))
        >>> (resource, action, scope)
        ('users', 'read', 'own')
    """
    parts = permission_code.split('.')
    return parts[0], parts[1], parts[2]


def _is_valid_component(component: str) -> bool:
    """
    Validate an individual component of a permission code.
    
    Components must:
    - Start with a letter
    - Contain only lowercase letters, numbers, and underscores
    - Be at least 1 character long
    """
    return bool(re.match(r'^[a-z][a-z0-9_]*$', component))