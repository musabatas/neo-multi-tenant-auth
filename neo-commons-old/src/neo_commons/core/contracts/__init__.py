"""
Cross-cutting contracts and protocols for the NeoMultiTenant platform.

This module defines the foundational protocols that establish contracts
between different modules and layers of the application. These protocols
enable dependency injection and ensure consistent behavior across the platform.

Protocol Categories:
- Domain protocols: Core business abstractions
- Event protocols: Domain event handling
- Integration protocols: Cross-module communication
"""

from .protocols import (
    DomainEventProtocol,
    EntityProtocol,
    ValueObjectProtocol,
    AggregateRootProtocol,
)

__all__ = [
    "DomainEventProtocol",
    "EntityProtocol",
    "ValueObjectProtocol", 
    "AggregateRootProtocol",
]