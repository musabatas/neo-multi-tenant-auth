"""
NeoCommons - Shared utilities for NeoMultiTenant microservices

This package provides common utilities, authentication, database connections,
caching, and other shared components used across NeoMultiTenant API services.
"""

# Import version from single source of truth
from .__version__ import __version__
__author__ = "NeoFast Team"
__email__ = "team@neofast.com"

__all__ = [
    "__version__",
]

# Conditional imports to avoid dependency issues during installation
def _import_optional_modules():
    """Import modules that have external dependencies only when accessed."""
    try:
        # Core imports for convenience
        from .exceptions.base import NeoCommonsException
        from .models.base import BaseModel
        from .utils.datetime import utc_now, format_iso8601

        # Authorization system
        from .auth import (
            Permission,
            Role,
            UserContext,
            TenantContext,
            PermissionService,
            PermissionRepository,
            get_current_user,
            require_permission,
            permission_required,
            PermissionError
        )

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

        # Update __all__ with successful imports
        global __all__
        __all__ = [
            "__version__",
            "NeoCommonsException", 
            "BaseModel",
            "utc_now",
            "format_iso8601",
            # Authorization
            "Permission",
            "Role",
            "UserContext",
            "TenantContext", 
            "PermissionService",
            "PermissionRepository",
            "get_current_user",
            "require_permission",
            "permission_required",
            "PermissionError",
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

        # Add to globals for easy access
        globals().update({
            'NeoCommonsException': NeoCommonsException,
            'BaseModel': BaseModel,
            'utc_now': utc_now,
            'format_iso8601': format_iso8601,
            'Permission': Permission,
            'Role': Role,
            'UserContext': UserContext,
            'TenantContext': TenantContext,
            'PermissionService': PermissionService,
            'PermissionRepository': PermissionRepository,
            'get_current_user': get_current_user,
            'require_permission': require_permission,
            'permission_required': permission_required,
            'PermissionError': PermissionError,
            'BaseConfigProtocol': BaseConfigProtocol,
            'BaseNeoConfig': BaseNeoConfig,
            'AdminConfig': AdminConfig,
            'TenantConfig': TenantConfig,
            'TestingConfig': TestingConfig,
            'get_config': get_config,
            'get_admin_config': get_admin_config,
            'get_tenant_config': get_tenant_config,
            'get_testing_config': get_testing_config,
            'create_config_for_environment': create_config_for_environment,
            'validate_config_or_exit': validate_config_or_exit,
        })

    except ImportError:
        # During installation, dependencies might not be available yet
        pass

# Only import optional modules if we're not in setup mode
import sys
if 'setuptools' not in sys.modules:
    _import_optional_modules()