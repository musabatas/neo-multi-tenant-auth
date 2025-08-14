"""
NeoCommons - Shared utilities for NeoMultiTenant microservices

This package provides common utilities, authentication, database connections,
caching, and other shared components used across NeoMultiTenant API services.
"""

__version__ = "1.0.0"
__author__ = "NeoFast Team"
__email__ = "team@neofast.com"

# Core imports for convenience
from .exceptions.base import NeoAdminException
from .models.base import BaseModel
from .utils.datetime import utc_now, format_iso8601

# Configuration management
from .config import (
    BaseConfigProtocol,
    BaseNeoConfig,
    AdminConfig,
    TenantConfig,
    TestingConfig,
    get_config,
    get_admin_config,
    get_tenant_config,
    get_testing_config,
    create_config_for_environment,
    validate_config_or_exit
)

__all__ = [
    "__version__",
    "NeoAdminException", 
    "BaseModel",
    "utc_now",
    "format_iso8601",
    # Configuration
    "BaseConfigProtocol",
    "BaseNeoConfig",
    "AdminConfig", 
    "TenantConfig",
    "TestingConfig",
    "get_config",
    "get_admin_config",
    "get_tenant_config",
    "get_testing_config",
    "create_config_for_environment",
    "validate_config_or_exit"
]