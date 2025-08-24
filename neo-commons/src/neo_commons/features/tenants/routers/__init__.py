"""Tenant routers - core API endpoints for tenant management."""

from .tenant_router import tenant_router
from .dependencies import TenantDependencies

__all__ = [
    "tenant_router",
    "TenantDependencies",
]