"""
Service layer patterns for the NeoMultiTenant platform.

This module provides generic service classes and patterns
that can be used across all platform services.
"""

from .base import BaseService

from .protocols import (
    BaseServiceProtocol,
    CRUDServiceProtocol,
    FilterableServiceProtocol,
    CacheableServiceProtocol,
    AuditableServiceProtocol,
    TenantAwareServiceProtocol,
    BatchServiceProtocol
)

__all__ = [
    "BaseService",
    # Protocol interfaces
    "BaseServiceProtocol",
    "CRUDServiceProtocol",
    "FilterableServiceProtocol",
    "CacheableServiceProtocol",
    "AuditableServiceProtocol",
    "TenantAwareServiceProtocol",
    "BatchServiceProtocol"
]