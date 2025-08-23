"""
OpenAPI schema customization and configuration for FastAPI applications.

This module provides reusable OpenAPI configuration utilities that can be used
across all Neo services for consistent API documentation.
"""
from typing import Dict, Any, List, Optional, Callable
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def create_openapi_schema(
    app: FastAPI,
    tag_groups: Optional[List[Dict[str, Any]]] = None,
    custom_processors: Optional[List[Callable[[Dict[str, Any]], Dict[str, Any]]]] = None
) -> Dict[str, Any]:
    """Create customized OpenAPI schema with optional tag groups.
    
    Args:
        app: FastAPI application instance
        tag_groups: Optional list of tag group configurations for nested documentation
        custom_processors: Optional list of functions to further process the schema
        
    Returns:
        Customized OpenAPI schema dictionary
    """
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add x-tagGroups for nested tag organization in Scalar if provided
    if tag_groups:
        openapi_schema["x-tagGroups"] = tag_groups
    
    # Apply any custom processors
    if custom_processors:
        for processor in custom_processors:
            openapi_schema = processor(openapi_schema)
    
    return openapi_schema


def configure_openapi(
    app: FastAPI,
    tag_groups: Optional[List[Dict[str, Any]]] = None,
    custom_processors: Optional[List[Callable[[Dict[str, Any]], Dict[str, Any]]]] = None
) -> None:
    """Configure OpenAPI schema for the application.
    
    This function sets up a custom OpenAPI schema generator for the FastAPI app,
    allowing for tag grouping and custom schema processing.
    
    Args:
        app: FastAPI application instance
        tag_groups: Optional list of tag group configurations
        custom_processors: Optional list of schema processing functions
    
    Example:
        ```python
        from fastapi import FastAPI
        from neo_commons.api.openapi import configure_openapi
        
        app = FastAPI(title="My Service")
        
        tag_groups = [
            {
                "name": "User Management",
                "tags": ["Users", "Profiles", "Settings"]
            },
            {
                "name": "System",
                "tags": ["Health", "Monitoring"]
            }
        ]
        
        configure_openapi(app, tag_groups=tag_groups)
        ```
    """
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        app.openapi_schema = create_openapi_schema(
            app, 
            tag_groups=tag_groups,
            custom_processors=custom_processors
        )
        return app.openapi_schema
    
    app.openapi = custom_openapi


# Common tag groups that can be reused across services
COMMON_TAG_GROUPS = {
    "auth": {
        "name": "Authentication & Authorization",
        "tags": ["Authentication", "Permissions", "Roles"]
    },
    "users": {
        "name": "User Management",
        "tags": ["Users", "User Profile", "User Settings"]
    },
    "system": {
        "name": "System",
        "tags": ["Health", "Configuration", "Monitoring"]
    },
    "debug": {
        "name": "Debug",
        "tags": ["Debug", "Test"]
    }
}


def get_default_tag_groups() -> List[Dict[str, Any]]:
    """Get a default set of tag groups for common API organization.
    
    Returns:
        List of default tag group configurations
    """
    return list(COMMON_TAG_GROUPS.values())


def merge_tag_groups(
    base_groups: List[Dict[str, Any]], 
    custom_groups: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Merge custom tag groups with base groups, avoiding duplicates.
    
    Args:
        base_groups: Base list of tag groups
        custom_groups: Custom tag groups to merge
        
    Returns:
        Merged list of tag groups with duplicates removed
    """
    # Create a dict keyed by group name for easy merging
    merged = {group["name"]: group for group in base_groups}
    
    for custom_group in custom_groups:
        name = custom_group["name"]
        if name in merged:
            # Merge tags, avoiding duplicates
            existing_tags = set(merged[name]["tags"])
            new_tags = set(custom_group["tags"])
            merged[name]["tags"] = list(existing_tags | new_tags)
        else:
            merged[name] = custom_group
    
    return list(merged.values())