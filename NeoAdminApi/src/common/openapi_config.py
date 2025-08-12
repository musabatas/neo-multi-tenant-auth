"""
OpenAPI schema customization and configuration.
"""
from typing import Dict, Any, List
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def create_openapi_schema(app: FastAPI) -> Dict[str, Any]:
    """Create customized OpenAPI schema with tag groups.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        Customized OpenAPI schema dictionary
    """
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add x-tagGroups for nested tag organization in Scalar
    openapi_schema["x-tagGroups"] = get_tag_groups()
    
    return openapi_schema


def get_tag_groups() -> List[Dict[str, Any]]:
    """Get tag groups for API documentation organization.
    
    Returns:
        List of tag group configurations
    """
    return [
        {
            "name": "Authentication & Authorization",
            "tags": ["Authentication", "Permissions", "Roles"]
        },
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


def configure_openapi(app: FastAPI) -> None:
    """Configure OpenAPI schema for the application.
    
    Args:
        app: FastAPI application instance
    """
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        app.openapi_schema = create_openapi_schema(app)
        return app.openapi_schema
    
    app.openapi = custom_openapi