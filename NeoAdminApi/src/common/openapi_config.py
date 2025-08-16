"""
OpenAPI schema customization and configuration for NeoAdminApi.

This module now uses the generic OpenAPI configuration from neo-commons
while providing service-specific tag groups for the Admin API.
"""
from typing import Dict, Any, List
from fastapi import FastAPI

# Import generic OpenAPI configuration from neo-commons
from neo_commons.api.openapi import (
    configure_openapi as neo_configure_openapi,
    merge_tag_groups,
    COMMON_TAG_GROUPS
)


def get_admin_tag_groups() -> List[Dict[str, Any]]:
    """Get Admin API specific tag groups for documentation organization.
    
    Returns:
        List of tag group configurations specific to Admin API
    """
    # Start with common groups and add Admin-specific ones
    base_groups = [
        COMMON_TAG_GROUPS["auth"],
        COMMON_TAG_GROUPS["system"],
        COMMON_TAG_GROUPS["debug"]
    ]
    
    admin_specific_groups = [
        {
            "name": "User Management",
            "tags": ["Platform Users", "User Profile", "User Settings"]
        },
        {
            "name": "Organization Management",
            "tags": ["Organizations", "Organization Settings", "Organization Members"]
        },
        {
            "name": "Tenant Management",
            "tags": ["Tenants", "Tenant Settings", "Tenant Users"]
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
            "name": "Billing & Subscriptions",
            "tags": ["Billing", "Subscriptions", "Invoices", "Payment Methods"]
        },
        {
            "name": "Analytics & Reports",
            "tags": ["Analytics", "Reports", "Metrics"]
        },
        {
            "name": "System",
            "tags": ["Health", "Configuration", "Migrations", "Monitoring"]
        }
    ]
    
    return merge_tag_groups(base_groups, admin_specific_groups)


def configure_openapi(app: FastAPI) -> None:
    """Configure OpenAPI schema for the Admin API application.
    
    This wrapper uses neo-commons OpenAPI configuration with Admin-specific tag groups.
    
    Args:
        app: FastAPI application instance
    """
    # Use neo-commons configuration with Admin-specific tag groups
    neo_configure_openapi(app, tag_groups=get_admin_tag_groups())


# For backward compatibility, expose the old function names
def create_openapi_schema(app: FastAPI) -> Dict[str, Any]:
    """Legacy function for backward compatibility.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        Customized OpenAPI schema dictionary
    """
    from neo_commons.api.openapi import create_openapi_schema as neo_create_schema
    return neo_create_schema(app, tag_groups=get_admin_tag_groups())


def get_tag_groups() -> List[Dict[str, Any]]:
    """Legacy function for backward compatibility.
    
    Returns:
        List of tag group configurations
    """
    return get_admin_tag_groups()