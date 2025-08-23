"""Infrastructure protocols for neo-commons.

This module defines protocols for infrastructure-level contracts and interfaces.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from abc import abstractmethod
import asyncpg


@runtime_checkable
class InfrastructureProtocol(Protocol):
    """Base protocol for all infrastructure components."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the infrastructure component."""
        ...
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup resources."""
        ...


@runtime_checkable
class DatabaseConnectionProtocol(Protocol):
    """Protocol for database connection managers."""
    
    @abstractmethod
    async def get_connection(self, connection_name: str) -> asyncpg.Pool:
        """Get database connection pool by name."""
        ...
    
    @abstractmethod
    async def get_connection_for_tenant(self, tenant_id: str) -> asyncpg.Pool:
        """Get database connection pool for specific tenant."""
        ...
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize connection manager."""
        ...
    
    @abstractmethod
    async def close(self) -> None:
        """Close all connections."""
        ...


@runtime_checkable
class CacheProtocol(Protocol):
    """Protocol for cache implementations."""
    
    @abstractmethod
    async def get(self, key: str, tenant_id: Optional[str] = None) -> Optional[Any]:
        """Get value from cache."""
        ...
    
    @abstractmethod
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: int, 
        tenant_id: Optional[str] = None
    ) -> None:
        """Set value in cache with TTL."""
        ...
    
    @abstractmethod
    async def delete(self, key: str, tenant_id: Optional[str] = None) -> None:
        """Delete value from cache."""
        ...
    
    @abstractmethod
    async def invalidate_pattern(
        self, 
        pattern: str, 
        tenant_id: Optional[str] = None
    ) -> None:
        """Invalidate cache keys matching pattern."""
        ...


@runtime_checkable
class AuthenticationProviderProtocol(Protocol):
    """Protocol for authentication providers (Keycloak, etc.)."""
    
    @abstractmethod
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token and return claims."""
        ...
    
    @abstractmethod
    async def get_public_key(self, realm: str) -> str:
        """Get public key for token validation."""
        ...
    
    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> Dict[str, str]:
        """Refresh access token."""
        ...


@runtime_checkable
class RepositoryProtocol(Protocol):
    """Base protocol for repository implementations."""
    
    @abstractmethod
    async def get_by_id(self, id: str, schema: str) -> Optional[Dict[str, Any]]:
        """Get entity by ID."""
        ...
    
    @abstractmethod
    async def create(self, data: Dict[str, Any], schema: str) -> Dict[str, Any]:
        """Create new entity."""
        ...
    
    @abstractmethod
    async def update(
        self, 
        id: str, 
        data: Dict[str, Any], 
        schema: str
    ) -> Optional[Dict[str, Any]]:
        """Update entity."""
        ...
    
    @abstractmethod
    async def delete(self, id: str, schema: str) -> bool:
        """Delete entity."""
        ...
    
    @abstractmethod
    async def list(
        self, 
        filters: Optional[Dict[str, Any]] = None,
        schema: str = "admin",
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List entities with filtering and pagination."""
        ...


@runtime_checkable
class ServiceProtocol(Protocol):
    """Base protocol for service implementations."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize service."""
        ...
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup service resources."""
        ...


@runtime_checkable
class HealthCheckProtocol(Protocol):
    """Protocol for health check implementations."""
    
    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """Perform health check and return status."""
        ...
    
    @abstractmethod
    async def check_readiness(self) -> Dict[str, Any]:
        """Check if service is ready to accept requests."""
        ...


@runtime_checkable
class MetricsCollectorProtocol(Protocol):
    """Protocol for metrics collection."""
    
    @abstractmethod
    def increment_counter(
        self, 
        name: str, 
        value: float = 1.0, 
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment counter metric."""
        ...
    
    @abstractmethod
    def record_histogram(
        self, 
        name: str, 
        value: float, 
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record histogram value."""
        ...
    
    @abstractmethod
    def set_gauge(
        self, 
        name: str, 
        value: float, 
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Set gauge value."""
        ...