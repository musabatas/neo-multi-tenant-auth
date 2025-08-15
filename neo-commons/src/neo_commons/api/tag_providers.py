"""
Tag group providers for OpenAPI documentation organization.
Provides flexible tag grouping without tight coupling to application specifics.
"""
import logging
from typing import Dict, Any, List, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class TagGroupProviderProtocol(Protocol):
    """Protocol for tag group providers."""
    
    def get_tag_groups(self) -> List[Dict[str, Any]]:
        """Get tag groups for API documentation organization."""
        ...


class DefaultTagGroupProvider:
    """Default tag group provider with common API organization patterns."""
    
    def __init__(self, custom_tag_groups: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize with optional custom tag groups.
        
        Args:
            custom_tag_groups: Custom tag groups to use instead of defaults
        """
        self._custom_tag_groups = custom_tag_groups
    
    def get_tag_groups(self) -> List[Dict[str, Any]]:
        """Get tag groups for API documentation organization."""
        if self._custom_tag_groups:
            return self._custom_tag_groups
        
        return self._get_default_tag_groups()
    
    def _get_default_tag_groups(self) -> List[Dict[str, Any]]:
        """Get default tag groups for common API patterns."""
        return [
            {
                "name": "Authentication & Authorization",
                "tags": ["Authentication", "Permissions", "Roles", "Sessions"]
            },
            {
                "name": "User Management",
                "tags": ["Users", "User Profile", "User Settings", "User Preferences"]
            },
            {
                "name": "Organization Management", 
                "tags": ["Organizations", "Organization Settings", "Organization Members"]
            },
            {
                "name": "Infrastructure",
                "tags": ["Health", "Configuration", "Database", "Cache"]
            },
            {
                "name": "Reference Data",
                "tags": ["Countries", "Currencies", "Languages", "Timezones"]
            },
            {
                "name": "System",
                "tags": ["Health", "Configuration", "Monitoring", "Metrics"]
            },
            {
                "name": "Development",
                "tags": ["Debug", "Test", "Development", "Root"]
            }
        ]


class AdminTagGroupProvider(DefaultTagGroupProvider):
    """Tag group provider for admin/platform APIs."""
    
    def _get_default_tag_groups(self) -> List[Dict[str, Any]]:
        """Get tag groups optimized for admin/platform APIs."""
        return [
            {
                "name": "Authentication & Authorization",
                "tags": ["Authentication", "Permissions", "Roles", "Sessions"]
            },
            {
                "name": "User Management",
                "tags": ["Users", "User Profile", "User Settings"]
            },
            {
                "name": "Organization Management",
                "tags": ["Organizations", "Organization Settings", "Organization Members"]
            },
            {
                "name": "Client Management", 
                "tags": ["Clients", "Client Settings", "Client Users"]
            },
            {
                "name": "Infrastructure",
                "tags": ["Regions", "Database Connections", "Health"]
            },
            {
                "name": "Reference Data",
                "tags": ["Currencies", "Countries", "Languages"]
            },
            {
                "name": "💳 Billing & Subscriptions",
                "tags": ["Billing", "Subscriptions", "Invoices", "Payment Methods"]
            },
            {
                "name": "📊 Analytics & Reports",
                "tags": ["Analytics", "Reports", "Metrics"]
            },
            {
                "name": "System",
                "tags": ["Health", "Configuration", "Migrations", "Monitoring"]
            },
            {
                "name": "Debug",
                "tags": ["Debug", "Test", "Root"]
            }
        ]


class TenantTagGroupProvider(DefaultTagGroupProvider):
    """Tag group provider for tenant-specific APIs."""
    
    def _get_default_tag_groups(self) -> List[Dict[str, Any]]:
        """Get tag groups optimized for tenant APIs."""
        return [
            {
                "name": "Authentication & Authorization",
                "tags": ["Authentication", "Permissions", "Roles", "Sessions"]
            },
            {
                "name": "User Management",
                "tags": ["Users", "User Profile", "Teams", "Invitations"]
            },
            {
                "name": "Workspace Management",
                "tags": ["Workspaces", "Projects", "Boards", "Documents"]
            },
            {
                "name": "Content Management",
                "tags": ["Content", "Files", "Media", "Templates"]
            },
            {
                "name": "Communication",
                "tags": ["Messages", "Notifications", "Comments", "Activities"]
            },
            {
                "name": "Reports & Analytics", 
                "tags": ["Reports", "Analytics", "Dashboards", "Metrics"]
            },
            {
                "name": "System",
                "tags": ["Health", "Settings", "Preferences"]
            },
            {
                "name": "Development",
                "tags": ["Debug", "Test", "Root"]
            }
        ]


def create_admin_openapi_config(
    custom_tag_groups: Optional[List[Dict[str, Any]]] = None
) -> TagGroupProviderProtocol:
    """
    Create OpenAPI configuration optimized for admin/platform APIs.
    
    Args:
        custom_tag_groups: Custom tag groups to override defaults
        
    Returns:
        Configured tag group provider for admin APIs
    """
    return AdminTagGroupProvider(custom_tag_groups=custom_tag_groups)


def create_tenant_openapi_config(
    custom_tag_groups: Optional[List[Dict[str, Any]]] = None
) -> TagGroupProviderProtocol:
    """
    Create OpenAPI configuration optimized for tenant APIs.
    
    Args:
        custom_tag_groups: Custom tag groups to override defaults
        
    Returns:
        Configured tag group provider for tenant APIs
    """
    return TenantTagGroupProvider(custom_tag_groups=custom_tag_groups)


def create_default_openapi_config(
    custom_tag_groups: Optional[List[Dict[str, Any]]] = None
) -> TagGroupProviderProtocol:
    """
    Create default OpenAPI configuration for general APIs.
    
    Args:
        custom_tag_groups: Custom tag groups to override defaults
        
    Returns:
        Configured tag group provider with defaults
    """
    return DefaultTagGroupProvider(custom_tag_groups=custom_tag_groups)