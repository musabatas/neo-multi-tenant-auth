"""Infrastructure package for neo-commons.

Core infrastructure components that serve all features and services:
- configuration/: Configuration management system
- middleware/: FastAPI middleware for cross-cutting concerns
- fastapi/: FastAPI application factory and configuration
- protocols/: Infrastructure contracts and interfaces
- database/: Low-level database utilities
"""

# Configuration infrastructure
from .configuration import *
# Middleware infrastructure
from . import middleware
# FastAPI infrastructure
from . import fastapi
# Protocol definitions
from .protocols import InfrastructureProtocol

__all__ = [
    # Configuration
    "ConfigKey",
    "ConfigValue", 
    "ConfigSchema",
    "ConfigGroup",
    "ConfigScope",
    "ConfigType", 
    "ConfigSource",
    "ConfigurationProvider",
    "ConfigurationRepository",
    "ConfigurationCache",
    "ConfigurationValidator",
    "ConfigSourceProtocol",
    "ConfigurationWatcher",
    "ConfigurationExporter", 
    "ConfigurationAuditor",
    "ConfigurationManager",
    "ConfigurationService",
    "AsyncPGConfigurationRepository",
    
    # Middleware
    "middleware",
    
    # FastAPI
    "fastapi",
    
    # Protocols
    "InfrastructureProtocol",
]