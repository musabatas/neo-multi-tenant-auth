"""
Auth Decorators Module

Permission decorators for endpoint protection and metadata collection with:
- Declarative permission requirements for endpoints
- OpenAPI documentation integration
- Permission metadata extraction for discovery
- Runtime validation support via dependency injection
- Multi-scope permission support (platform/tenant/user)
"""

from .permissions import RequirePermission, require_permission, PermissionMetadata

__all__ = [
    "RequirePermission",
    "require_permission", 
    "PermissionMetadata"
]