"""Infrastructure protocols for neo-commons.

This module defines protocols for infrastructure-level contracts and interfaces.
"""

from .infrastructure import (
    InfrastructureProtocol,
    DatabaseConnectionProtocol,
    CacheProtocol,
    AuthenticationProviderProtocol,
    RepositoryProtocol,
    ServiceProtocol,
    HealthCheckProtocol,
    MetricsCollectorProtocol
)

__all__ = [
    "InfrastructureProtocol",
    "DatabaseConnectionProtocol",
    "CacheProtocol", 
    "AuthenticationProviderProtocol",
    "RepositoryProtocol",
    "ServiceProtocol",
    "HealthCheckProtocol",
    "MetricsCollectorProtocol",
]