"""Database entities - domain objects, protocols, and configuration."""

# Core protocols
from .protocols import (
    ConnectionManager,
    ConnectionPool,
    SchemaResolver,
    ConnectionHealthChecker,
    ConnectionRegistry,
    FailoverManager,
    ConnectionLoadBalancer,
    DatabaseRepository,
    DatabaseConnectionRepository
)

# Domain entities
from .database_connection import DatabaseConnection

# Configuration
from .config import (
    DatabaseSettings,
    DatabaseConnectionConfig,
    SchemaConfig
)

__all__ = [
    # Entities
    "DatabaseConnection",
    
    # Protocols
    "ConnectionManager",
    "ConnectionPool", 
    "SchemaResolver",
    "ConnectionHealthChecker",
    "ConnectionRegistry",
    "FailoverManager",
    "ConnectionLoadBalancer",
    "DatabaseRepository",
    "DatabaseConnectionRepository",
    
    # Configuration
    "DatabaseSettings",
    "DatabaseConnectionConfig",
    "SchemaConfig",
]