"""
Wildcard Permission Matcher for Neo-Commons

Provides intelligent pattern matching for permission strings including
wildcard support and resource-action decomposition.
"""
import re
from typing import Set, List, Optional, Dict
from loguru import logger

from .protocols import WildcardMatcherProtocol


class DefaultWildcardMatcher:
    """
    Default implementation of wildcard permission matching.
    
    Supports patterns like:
    - Exact matches: "users:read" matches "users:read"
    - Wildcard actions: "users:*" matches "users:read", "users:write", etc.
    - Wildcard resources: "*:read" matches "users:read", "tenants:read", etc.
    - Full wildcards: "*:*" matches any permission
    """
    
    def __init__(self):
        """Initialize the wildcard matcher."""
        self.permission_pattern = re.compile(r'^([^:]+):([^:]+)$')
        logger.debug("Initialized DefaultWildcardMatcher")
    
    def matches_permission(
        self,
        required_permission: str,
        granted_permission: str
    ) -> bool:
        """
        Check if granted permission matches required permission.
        
        Args:
            required_permission: Permission being checked (e.g., "users:read")
            granted_permission: Permission that was granted (e.g., "users:*")
            
        Returns:
            True if granted permission satisfies required permission
        """
        # Exact match
        if required_permission == granted_permission:
            return True
        
        # Parse both permissions
        req_resource, req_action = self._parse_permission(required_permission)
        granted_resource, granted_action = self._parse_permission(granted_permission)
        
        if not all([req_resource, req_action, granted_resource, granted_action]):
            return False
        
        # Check resource match (exact or wildcard)
        resource_match = (
            granted_resource == "*" or 
            granted_resource == req_resource
        )
        
        # Check action match (exact or wildcard)
        action_match = (
            granted_action == "*" or 
            granted_action == req_action
        )
        
        result = resource_match and action_match
        
        if result:
            logger.debug(
                f"Permission match: '{granted_permission}' satisfies '{required_permission}'"
            )
        
        return result
    
    def expand_wildcard_permissions(
        self,
        permissions: List[str]
    ) -> Set[str]:
        """
        Expand wildcard permissions to include all variations.
        
        This method primarily validates and normalizes permissions.
        True expansion would require knowledge of all possible resources/actions.
        
        Args:
            permissions: List of permission strings (may include wildcards)
            
        Returns:
            Set of normalized permission strings
        """
        expanded = set()
        
        for permission in permissions:
            # Validate permission format
            if self._is_valid_permission(permission):
                expanded.add(permission)
            else:
                logger.warning(f"Invalid permission format: {permission}")
        
        return expanded
    
    def get_resource_from_permission(
        self,
        permission: str
    ) -> Optional[str]:
        """
        Extract resource name from permission string.
        
        Args:
            permission: Permission string (e.g., "users:read")
            
        Returns:
            Resource name (e.g., "users") or None if invalid format
        """
        resource, _ = self._parse_permission(permission)
        return resource
    
    def get_action_from_permission(
        self,
        permission: str
    ) -> Optional[str]:
        """
        Extract action from permission string.
        
        Args:
            permission: Permission string (e.g., "users:read")
            
        Returns:
            Action name (e.g., "read") or None if invalid format
        """
        _, action = self._parse_permission(permission)
        return action
    
    def check_permissions_list(
        self,
        required_permissions: List[str],
        granted_permissions: List[str],
        require_all: bool = True
    ) -> bool:
        """
        Check if granted permissions satisfy required permissions.
        
        Args:
            required_permissions: List of permissions being checked
            granted_permissions: List of permissions that were granted
            require_all: If True, all required permissions must be satisfied
            
        Returns:
            True if permissions are satisfied based on require_all flag
        """
        if not required_permissions:
            return True
        
        satisfied_count = 0
        
        for required in required_permissions:
            satisfied = False
            
            for granted in granted_permissions:
                if self.matches_permission(required, granted):
                    satisfied = True
                    satisfied_count += 1
                    break
            
            # If require_all=True and any permission fails, return False
            if require_all and not satisfied:
                return False
            
            # If require_all=False and any permission succeeds, we can continue
            # (but we need to check all to get accurate satisfied_count)
        
        # If require_all=False, return True if at least one permission was satisfied
        if not require_all:
            return satisfied_count > 0
        
        # If require_all=True, we reach here only if all were satisfied
        return True
    
    def group_permissions_by_resource(
        self,
        permissions: List[str]
    ) -> Dict[str, Set[str]]:
        """
        Group permissions by resource.
        
        Args:
            permissions: List of permission strings
            
        Returns:
            Dict mapping resource to set of actions
        """
        grouped = {}
        
        for permission in permissions:
            resource, action = self._parse_permission(permission)
            if resource and action:
                if resource not in grouped:
                    grouped[resource] = set()
                grouped[resource].add(action)
        
        return grouped
    
    def has_wildcard_permission(
        self,
        permissions: List[str],
        resource: str,
        action: Optional[str] = None
    ) -> bool:
        """
        Check if permissions list contains a wildcard that would grant access.
        
        Args:
            permissions: List of granted permissions
            resource: Resource to check access for
            action: Optional specific action to check
            
        Returns:
            True if any wildcard permission grants access
        """
        # Check for full wildcard
        if "*:*" in permissions:
            return True
        
        # Check for resource wildcard
        if f"{resource}:*" in permissions:
            return True
        
        # Check for action wildcard if specific action provided
        if action and f"*:{action}" in permissions:
            return True
        
        return False
    
    def get_effective_permissions(
        self,
        granted_permissions: List[str],
        all_possible_permissions: List[str]
    ) -> Set[str]:
        """
        Get all effective permissions based on granted permissions with wildcards.
        
        Args:
            granted_permissions: List of granted permissions (may include wildcards)
            all_possible_permissions: List of all possible permission strings
            
        Returns:
            Set of all effective permissions the user has
        """
        effective = set()
        
        for possible in all_possible_permissions:
            for granted in granted_permissions:
                if self.matches_permission(possible, granted):
                    effective.add(possible)
                    break
        
        return effective
    
    def normalize_permission(self, permission: str) -> Optional[str]:
        """
        Normalize permission string format.
        
        Args:
            permission: Permission string to normalize
            
        Returns:
            Normalized permission string or None if invalid
        """
        resource, action = self._parse_permission(permission)
        if resource and action:
            return f"{resource}:{action}"
        return None
    
    def is_wildcard_permission(self, permission: str) -> bool:
        """
        Check if permission contains wildcards.
        
        Args:
            permission: Permission string to check
            
        Returns:
            True if permission contains wildcards
        """
        return "*" in permission
    
    def _parse_permission(self, permission: str) -> tuple[Optional[str], Optional[str]]:
        """
        Parse permission string into resource and action components.
        
        Args:
            permission: Permission string (e.g., "users:read")
            
        Returns:
            Tuple of (resource, action) or (None, None) if invalid
        """
        if not permission or not isinstance(permission, str):
            return None, None
        
        match = self.permission_pattern.match(permission)
        if not match:
            return None, None
        
        return match.group(1), match.group(2)
    
    def _is_valid_permission(self, permission: str) -> bool:
        """
        Check if permission string has valid format.
        
        Args:
            permission: Permission string to validate
            
        Returns:
            True if permission has valid format
        """
        resource, action = self._parse_permission(permission)
        return resource is not None and action is not None


# Factory function for dependency injection
def create_wildcard_matcher() -> DefaultWildcardMatcher:
    """
    Create a wildcard matcher instance.
    
    Returns:
        Configured DefaultWildcardMatcher instance
    """
    return DefaultWildcardMatcher()


__all__ = [
    "DefaultWildcardMatcher",
    "create_wildcard_matcher",
]