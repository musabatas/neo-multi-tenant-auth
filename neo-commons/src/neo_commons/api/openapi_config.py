"""
Enhanced OpenAPI schema customization and configuration for neo-commons.
Provides flexible OpenAPI configuration without tight coupling to application specifics.
"""
import logging
from typing import Dict, Any, List, Optional, Protocol, runtime_checkable, Callable
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

# Import from split modules
from .tag_providers import (
    TagGroupProviderProtocol,
    DefaultTagGroupProvider,
    AdminTagGroupProvider,
    TenantTagGroupProvider,
    create_admin_openapi_config,
    create_tenant_openapi_config,
    create_default_openapi_config
)
from .schema_enhancers import (
    enhance_schema_with_security,
    enhance_schema_with_examples,
    enhance_schema_with_tenant_security,
    enhance_schema_with_admin_security,
    enhance_schema_with_cors_info,
    enhance_schema_with_rate_limiting_info
)

logger = logging.getLogger(__name__)


@runtime_checkable
class ApplicationInfoProtocol(Protocol):
    """Protocol for application information."""
    
    @property
    def title(self) -> str:
        """Application title."""
        ...
    
    @property
    def version(self) -> str:
        """Application version."""
        ...
    
    @property
    def description(self) -> Optional[str]:
        """Application description."""
        ...


class DefaultApplicationInfo:
    """Default implementation of application information."""
    
    def __init__(
        self,
        title: str = "Neo API",
        version: str = "1.0.0",
        description: Optional[str] = None
    ):
        self._title = title
        self._version = version
        self._description = description
    
    @property
    def title(self) -> str:
        return self._title
    
    @property
    def version(self) -> str:
        return self._version
    
    @property
    def description(self) -> Optional[str]:
        return self._description


def create_openapi_schema(
    app: FastAPI,
    app_info: Optional[ApplicationInfoProtocol] = None,
    tag_group_provider: Optional[TagGroupProviderProtocol] = None,
    schema_customizer: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Create customized OpenAPI schema with flexible configuration.
    
    Args:
        app: FastAPI application instance
        app_info: Application information provider
        tag_group_provider: Tag group provider for organization
        schema_customizer: Optional function to further customize the schema
        
    Returns:
        Customized OpenAPI schema dictionary
    """
    # Use app info or defaults
    if app_info:
        title = app_info.title
        version = app_info.version
        description = app_info.description
    else:
        title = getattr(app, 'title', 'Neo API')
        version = getattr(app, 'version', '1.0.0')
        description = getattr(app, 'description', None)
    
    # Create base OpenAPI schema
    openapi_schema = get_openapi(
        title=title,
        version=version,
        description=description,
        routes=app.routes,
    )
    
    # Add tag groups if provider is available
    if tag_group_provider:
        try:
            tag_groups = tag_group_provider.get_tag_groups()
            if tag_groups:
                openapi_schema["x-tagGroups"] = tag_groups
                logger.debug(f"Added {len(tag_groups)} tag groups to OpenAPI schema")
        except Exception as e:
            logger.warning(f"Failed to add tag groups: {e}")
    
    # Apply custom schema modifications
    if schema_customizer:
        try:
            openapi_schema = schema_customizer(openapi_schema)
            logger.debug("Applied custom schema modifications")
        except Exception as e:
            logger.warning(f"Failed to apply custom schema modifications: {e}")
    
    # Add common extensions
    openapi_schema.setdefault("x-logo", {
        "url": "/static/logo.png",
        "altText": title
    })
    
    return openapi_schema


def configure_openapi(
    app: FastAPI,
    app_info: Optional[ApplicationInfoProtocol] = None,
    tag_group_provider: Optional[TagGroupProviderProtocol] = None,
    schema_customizer: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
) -> None:
    """
    Configure OpenAPI schema for the FastAPI application.
    
    Args:
        app: FastAPI application instance
        app_info: Application information provider
        tag_group_provider: Tag group provider for organization
        schema_customizer: Optional function to further customize the schema
    """
    def custom_openapi():
        """Custom OpenAPI generator function."""
        if app.openapi_schema:
            return app.openapi_schema
        
        app.openapi_schema = create_openapi_schema(
            app=app,
            app_info=app_info,
            tag_group_provider=tag_group_provider,
            schema_customizer=schema_customizer
        )
        return app.openapi_schema
    
    # Replace the default OpenAPI generator
    app.openapi = custom_openapi
    logger.info(f"Configured custom OpenAPI schema for {getattr(app, 'title', 'application')}")


# Re-export functions from split modules for backward compatibility
__all__ = [
    # Protocols
    "ApplicationInfoProtocol",
    "TagGroupProviderProtocol",
    # Classes
    "DefaultApplicationInfo",
    "DefaultTagGroupProvider",
    "AdminTagGroupProvider",
    "TenantTagGroupProvider",
    # Core functions
    "create_openapi_schema",
    "configure_openapi",
    # Factory functions
    "create_admin_openapi_config",
    "create_tenant_openapi_config",
    "create_default_openapi_config",
    # Schema enhancers
    "enhance_schema_with_security",
    "enhance_schema_with_examples",
    "enhance_schema_with_tenant_security",
    "enhance_schema_with_admin_security",
    "enhance_schema_with_cors_info",
    "enhance_schema_with_rate_limiting_info"
]