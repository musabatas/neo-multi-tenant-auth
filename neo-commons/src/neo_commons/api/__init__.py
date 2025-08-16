"""
API utilities for FastAPI applications.

This module provides common API components that can be used across
all services in the NeoMultiTenant platform.
"""

from .exception_handlers import ExceptionHandlerRegistry, register_exception_handlers
from .openapi import (
    configure_openapi,
    create_openapi_schema,
    get_default_tag_groups,
    merge_tag_groups,
    COMMON_TAG_GROUPS
)
from .endpoints import (
    register_health_endpoints,
    register_debug_endpoints,
)

__all__ = [
    # Exception handling
    "ExceptionHandlerRegistry",
    "register_exception_handlers",
    # OpenAPI configuration
    "configure_openapi",
    "create_openapi_schema",
    "get_default_tag_groups",
    "merge_tag_groups",
    "COMMON_TAG_GROUPS",
    # Common endpoints
    "register_health_endpoints",
    "register_debug_endpoints",
]