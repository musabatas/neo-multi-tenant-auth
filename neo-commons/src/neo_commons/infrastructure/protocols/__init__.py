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

from .factory import (
    RuntimeProtocolFactory,
    ProtocolImplementation,
    AdaptationStrategy,
    ProtocolRegistrar,
    get_protocol_factory,
    set_protocol_factory,
    create_protocol,
    register_implementation,
    protocol_implementation
)

__all__ = [
    # Infrastructure protocols
    "InfrastructureProtocol",
    "DatabaseConnectionProtocol",
    "CacheProtocol", 
    "AuthenticationProviderProtocol",
    "RepositoryProtocol",
    "ServiceProtocol",
    "HealthCheckProtocol",
    "MetricsCollectorProtocol",
    
    # Protocol factory
    "RuntimeProtocolFactory",
    "ProtocolImplementation",
    "AdaptationStrategy",
    "ProtocolRegistrar",
    "get_protocol_factory",
    "set_protocol_factory", 
    "create_protocol",
    "register_implementation",
    "protocol_implementation",
]