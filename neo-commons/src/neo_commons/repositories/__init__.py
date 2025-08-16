"""
Repository patterns for data access layer.

This module provides base repository classes and patterns that can be used
across all platform services with dynamic schema configuration.
"""

from .base import BaseRepository
from .protocols import (
    RepositoryProtocol,
    SchemaProvider,
    ConnectionProvider,
    CacheableRepositoryProtocol,
    AuditableRepositoryProtocol,
    TenantAwareRepositoryProtocol
)

__all__ = [
    "BaseRepository",
    # Protocol interfaces
    "RepositoryProtocol", 
    "SchemaProvider",
    "ConnectionProvider",
    "CacheableRepositoryProtocol",
    "AuditableRepositoryProtocol",
    "TenantAwareRepositoryProtocol"
]