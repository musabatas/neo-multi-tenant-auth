"""Database configuration for neo-commons."""

from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, SecretStr, validator
from pydantic_settings import BaseSettings
from enum import Enum

from ....config.constants import ConnectionType


class DatabaseSettings(BaseSettings):
    """Global database settings."""
    
    # Default connection (usually admin database)
    default_host: str = Field(default="localhost", description="Default database host")
    default_port: int = Field(default=5432, description="Default database port")
    default_database: str = Field(default="neofast_admin", description="Default database name")
    default_username: str = Field(default="postgres", description="Default database username")
    default_password: SecretStr = Field(default="postgres", description="Default database password")
    default_ssl_mode: str = Field(default="prefer", description="Default SSL mode")
    
    # Connection pool settings
    pool_min_size: int = Field(default=5, ge=0, description="Minimum pool size")
    pool_max_size: int = Field(default=20, ge=1, description="Maximum pool size")
    pool_timeout_seconds: int = Field(default=30, ge=1, description="Pool timeout in seconds")
    pool_recycle_seconds: int = Field(default=3600, ge=60, description="Pool recycle time")
    pool_pre_ping: bool = Field(default=True, description="Enable pool pre-ping")
    
    # Health monitoring
    health_check_interval_seconds: int = Field(default=30, ge=10, description="Health check interval")
    max_consecutive_failures: int = Field(default=3, ge=1, description="Max failures before marking unhealthy")
    connection_timeout_seconds: int = Field(default=10, ge=1, description="Connection timeout")
    
    # Performance settings
    enable_query_logging: bool = Field(default=False, description="Enable query logging")
    query_timeout_seconds: int = Field(default=60, ge=1, description="Query timeout")
    max_query_log_length: int = Field(default=1000, ge=100, description="Max logged query length")
    
    # Schema settings
    default_admin_schema: str = Field(default="admin", description="Default admin schema")
    tenant_schema_prefix: str = Field(default="tenant_", description="Tenant schema prefix")
    
    @validator('pool_max_size')
    def validate_pool_max_size(cls, v, values):
        """Ensure max pool size is greater than min pool size."""
        if 'pool_min_size' in values and v < values['pool_min_size']:
            raise ValueError('pool_max_size must be greater than or equal to pool_min_size')
        return v
    
    class Config:
        env_prefix = "NEO_DB_"
        case_sensitive = False


@dataclass(frozen=True)
class DatabaseConnectionConfig:
    """Configuration for a database connection."""
    
    # Connection identity
    connection_id: str
    connection_name: str
    connection_type: ConnectionType
    
    # Connection details
    host: str
    port: int = 5432
    database_name: str = ""
    username: str = "postgres"
    password: str = ""
    ssl_mode: str = "prefer"
    
    # Pool configuration
    pool_min_size: int = 5
    pool_max_size: int = 20
    pool_timeout_seconds: int = 30
    pool_recycle_seconds: int = 3600
    pool_pre_ping: bool = True
    
    # Health and monitoring
    is_active: bool = True
    is_healthy: bool = True
    max_consecutive_failures: int = 3
    
    # Optional metadata
    region_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.pool_min_size < 0:
            raise ValueError("pool_min_size must be >= 0")
        if self.pool_max_size < self.pool_min_size:
            raise ValueError("pool_max_size must be >= pool_min_size")
        if self.pool_timeout_seconds <= 0:
            raise ValueError("pool_timeout_seconds must be > 0")
        if not self.connection_name:
            raise ValueError("connection_name cannot be empty")
        if not self.host:
            raise ValueError("host cannot be empty")
    
    @property
    def dsn(self) -> str:
        """Build PostgreSQL DSN string."""
        password_part = f":{self.password}" if self.password else ""
        return (
            f"postgresql://{self.username}{password_part}@"
            f"{self.host}:{self.port}/{self.database_name}"
            f"?sslmode={self.ssl_mode}"
        )
    
    @property
    def safe_dsn(self) -> str:
        """Build PostgreSQL DSN string without password for logging."""
        return (
            f"postgresql://{self.username}@"
            f"{self.host}:{self.port}/{self.database_name}"
            f"?sslmode={self.ssl_mode}"
        )
    
    def to_asyncpg_kwargs(self) -> Dict[str, Any]:
        """Convert to asyncpg connection arguments."""
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database_name,
            "user": self.username,
            "password": self.password,
            "ssl": self.ssl_mode,
            "min_size": self.pool_min_size,
            "max_size": self.pool_max_size,
            "timeout": self.pool_timeout_seconds,
            "max_inactive_connection_lifetime": self.pool_recycle_seconds,
        }


@dataclass
class SchemaConfig:
    """Schema configuration for database operations."""
    
    # Schema identification
    schema_name: str
    schema_type: str  # 'admin', 'tenant', 'platform_common'
    
    # Schema metadata
    tenant_id: Optional[str] = None
    tenant_slug: Optional[str] = None
    is_template: bool = False
    
    # Database connection reference
    connection_name: str = "default"
    
    def __post_init__(self):
        """Validate schema configuration."""
        if not self.schema_name:
            raise ValueError("schema_name cannot be empty")
        if self.schema_type not in ("admin", "tenant", "platform_common"):
            raise ValueError(f"Invalid schema_type: {self.schema_type}")
        if self.schema_type == "tenant" and not self.tenant_id:
            raise ValueError("tenant_id required for tenant schemas")
    
    @property
    def is_admin_schema(self) -> bool:
        """Check if this is an admin schema."""
        return self.schema_type == "admin"
    
    @property
    def is_tenant_schema(self) -> bool:
        """Check if this is a tenant schema."""
        return self.schema_type == "tenant"
    
    @property
    def is_platform_schema(self) -> bool:
        """Check if this is a platform common schema."""
        return self.schema_type == "platform_common"


class ConnectionRegistry:
    """Registry for managing database connection configurations."""
    
    def __init__(self):
        self._connections: Dict[str, DatabaseConnectionConfig] = {}
        self._default_connection_name: Optional[str] = None
    
    def register_connection(self, config: DatabaseConnectionConfig) -> None:
        """Register a database connection configuration."""
        self._connections[config.connection_name] = config
        
        # Set as default if it's the first connection or if it's admin
        if (not self._default_connection_name or 
            config.connection_type == ConnectionType.PRIMARY):
            self._default_connection_name = config.connection_name
    
    def get_connection(self, connection_name: str) -> DatabaseConnectionConfig:
        """Get connection configuration by name."""
        if connection_name not in self._connections:
            raise ValueError(f"Connection '{connection_name}' not found")
        return self._connections[connection_name]
    
    def get_default_connection(self) -> DatabaseConnectionConfig:
        """Get the default connection configuration."""
        if not self._default_connection_name:
            raise ValueError("No default connection configured")
        return self._connections[self._default_connection_name]
    
    def list_connections(self, 
                        connection_type: Optional[ConnectionType] = None,
                        active_only: bool = True) -> List[DatabaseConnectionConfig]:
        """List all registered connections."""
        connections = list(self._connections.values())
        
        if connection_type:
            connections = [c for c in connections if c.connection_type == connection_type]
        
        if active_only:
            connections = [c for c in connections if c.is_active]
        
        return connections
    
    def remove_connection(self, connection_name: str) -> None:
        """Remove a connection from the registry."""
        if connection_name in self._connections:
            del self._connections[connection_name]
            
            # Update default if needed
            if self._default_connection_name == connection_name:
                remaining = list(self._connections.keys())
                self._default_connection_name = remaining[0] if remaining else None
    
    def clear(self) -> None:
        """Clear all connections from the registry."""
        self._connections.clear()
        self._default_connection_name = None
    
    @property
    def connection_count(self) -> int:
        """Get the number of registered connections."""
        return len(self._connections)


# Global connection registry instance
connection_registry = ConnectionRegistry()


def create_default_admin_connection(settings: DatabaseSettings) -> DatabaseConnectionConfig:
    """Create default admin connection from settings."""
    return DatabaseConnectionConfig(
        connection_id="default-admin",
        connection_name="admin-primary",
        connection_type=ConnectionType.PRIMARY,
        host=settings.default_host,
        port=settings.default_port,
        database_name=settings.default_database,
        username=settings.default_username,
        password=settings.default_password.get_secret_value(),
        ssl_mode=settings.default_ssl_mode,
        pool_min_size=settings.pool_min_size,
        pool_max_size=settings.pool_max_size,
        pool_timeout_seconds=settings.pool_timeout_seconds,
        pool_recycle_seconds=settings.pool_recycle_seconds,
        pool_pre_ping=settings.pool_pre_ping,
        max_consecutive_failures=settings.max_consecutive_failures,
        tags=["admin", "primary", "default"],
        metadata={"created_from": "default_settings"}
    )


def register_default_connections(settings: DatabaseSettings) -> None:
    """Register default database connections."""
    # Register the default admin connection
    admin_conn = create_default_admin_connection(settings)
    connection_registry.register_connection(admin_conn)