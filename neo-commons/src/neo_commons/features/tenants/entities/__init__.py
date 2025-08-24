"""Tenant entities - domain objects, protocols, and business logic."""

from .tenant import Tenant
from .protocols import (
    TenantRepository,
    TenantCache,
    TenantConfigResolver
)

__all__ = [
    # Domain entities
    "Tenant",
    
    # Protocols
    "TenantRepository",
    "TenantCache", 
    "TenantConfigResolver",
]