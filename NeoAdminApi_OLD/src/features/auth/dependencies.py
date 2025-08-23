"""
Neo-Commons Auth Dependencies for FastAPI routes.

Direct integration with neo-commons auth system without wrappers.
"""
from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from loguru import logger

# Import neo-commons directly - no wrappers needed
from neo_commons.auth import (
    CheckPermission,
    CurrentUser,
    create_reference_data_access,
    create_guest_session_info,
    create_guest_auth_service,
    create_auth_service,
    create_permission_cache_manager,
)
from neo_commons.cache import TenantAwareCacheService

from src.common.config.settings import settings
from src.common.exceptions.base import UnauthorizedError, ForbiddenError
from .implementations import NeoAdminAuthConfig

# Security scheme
security = HTTPBearer(
    description="JWT token from Keycloak",
    auto_error=False
)

# ============================================================================
# NEO-COMMONS CONFIGURATION
# ============================================================================

# Configure neo-commons with NeoAdminApi settings
def _configure_neo_commons():
    """Configure neo-commons with NeoAdminApi-specific settings."""
    from src.common.cache.client import get_cache
    from .services.permission_service import PermissionService
    
    # Create cache service for auth
    cache_manager = get_cache()
    cache_service = TenantAwareCacheService(cache_manager)
    
    # Create auth config
    auth_config = NeoAdminAuthConfig()
    
    # Create required services
    guest_service = create_guest_auth_service(cache_service=cache_service)
    permission_service = PermissionService()
    auth_service = create_auth_service(auth_config=auth_config)
    
    # Create reference data access dependency with all required parameters
    reference_data_access = create_reference_data_access(
        guest_service=guest_service,
        permission_checker=permission_service,
        token_validator=auth_service.token_validator,
        auth_config=auth_config
    )
    
    # Create guest session info dependency
    guest_session_info = create_guest_session_info(guest_service)
    
    return reference_data_access, guest_session_info

# Create configured dependencies
get_reference_data_access, get_guest_session_info = _configure_neo_commons()

# ============================================================================
# NEO-COMMONS DEPENDENCY ALIASES
# ============================================================================

# Use neo-commons dependencies directly with NeoAdminApi configuration
def get_current_user_dependency():
    """Get neo-commons CurrentUser dependency configured for NeoAdminApi."""
    auth_config = NeoAdminAuthConfig()
    auth_service = create_auth_service(auth_config=auth_config)
    return CurrentUser(
        token_validator=auth_service.token_validator,
        auth_config=auth_config
    )

def create_permission_dependency(permissions: List[str], any_of: bool = False):
    """Create neo-commons CheckPermission dependency with NeoAdminApi configuration."""
    from .services.permission_service import PermissionService
    auth_config = NeoAdminAuthConfig()
    auth_service = create_auth_service(auth_config=auth_config)
    permission_service = PermissionService()
    
    # Create the CheckPermission instance
    checker = CheckPermission(
        permission_checker=permission_service,
        token_validator=auth_service.token_validator,
        auth_config=auth_config,
        permissions=permissions,
        any_of=any_of
    )
    
    # Return the callable directly - FastAPI will handle dependency injection
    return checker

# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def require_permission(permission: str):
    """Convenience function for single permission check using neo-commons."""
    return create_permission_dependency([permission])

def require_any_permission(*permissions: str):
    """Convenience function for any-of permission check using neo-commons."""
    return create_permission_dependency(list(permissions), any_of=True)

def require_all_permissions(*permissions: str):
    """Convenience function for all-of permission check using neo-commons."""
    return create_permission_dependency(list(permissions), any_of=False)

# ============================================================================
# EXPORTS - Make functions available for import from other modules
# ============================================================================

__all__ = [
    # Neo-commons dependencies (configured for NeoAdminApi)
    "CheckPermission",
    "CurrentUser", 
    "security",
    
    # Guest authentication dependencies
    "get_reference_data_access",
    "get_guest_session_info",
    
    # Convenience functions (using neo-commons internally)
    "require_permission",
    "require_any_permission", 
    "require_all_permissions",
    
    # Dependency creation helpers
    "get_current_user_dependency",
    "create_permission_dependency",
]