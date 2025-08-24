"""Database connection entities for neo-commons."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime

from ....core.value_objects.identifiers import DatabaseConnectionId, RegionId
from ....config.constants import ConnectionType, HealthStatus
from ..utils.validation import (
    validate_pool_configuration,
    validate_connection_basic_fields,
    validate_connection_timeouts
)


@dataclass
class DatabaseConnection:
    """Database connection entity representing a connection configuration."""
    
    # Core Identity
    id: DatabaseConnectionId
    region_id: RegionId
    connection_name: str
    connection_type: ConnectionType
    
    # Connection Details
    host: str
    port: int = 5432
    database_name: str = ""
    ssl_mode: str = "require"
    username: str = "postgres"
    encrypted_password: Optional[str] = None
    connection_options: Dict[str, Any] = field(default_factory=dict)
    
    # Pool Configuration
    pool_min_size: int = 5
    pool_max_size: int = 20
    pool_timeout_seconds: int = 30
    pool_recycle_seconds: int = 3600
    pool_pre_ping: bool = True
    
    # Health and Status
    is_active: bool = True
    is_healthy: bool = True
    last_health_check: Optional[datetime] = None
    consecutive_failures: int = 0
    max_consecutive_failures: int = 3
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate the database connection after initialization."""
        # Use shared validation utilities
        validate_connection_basic_fields(self.connection_name, self.host, self.database_name)
        validate_pool_configuration(
            self.pool_min_size, 
            self.pool_max_size, 
            self.pool_timeout_seconds,
            self.connection_name
        )
        validate_connection_timeouts(
            self.pool_timeout_seconds,
            self.pool_recycle_seconds, 
            self.connection_name
        )
        
        # Connection-specific validations
        if self.consecutive_failures < 0:
            raise ValueError("consecutive_failures must be >= 0")
        if self.max_consecutive_failures <= 0:
            raise ValueError("max_consecutive_failures must be > 0")
    
    @property
    def is_deleted(self) -> bool:
        """Check if the connection is soft-deleted."""
        return self.deleted_at is not None
    
    @property
    def is_available(self) -> bool:
        """Check if the connection is available for use."""
        return self.is_active and self.is_healthy and not self.is_deleted
    
    @property
    def health_status(self) -> HealthStatus:
        """Get the current health status."""
        if not self.is_active or self.is_deleted:
            return HealthStatus.UNHEALTHY
        
        if not self.is_healthy:
            return HealthStatus.UNHEALTHY
        
        if self.consecutive_failures > 0:
            if self.consecutive_failures >= self.max_consecutive_failures // 2:
                return HealthStatus.DEGRADED
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    @property
    def safe_dsn(self) -> str:
        """Get DSN without password for logging."""
        return (
            f"postgresql://{self.username}@"
            f"{self.host}:{self.port}/{self.database_name}"
            f"?sslmode={self.ssl_mode}"
        )
    
    def increment_failure_count(self) -> None:
        """Increment the consecutive failure count."""
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.max_consecutive_failures:
            self.is_healthy = False
    
    def reset_failure_count(self) -> None:
        """Reset the consecutive failure count and mark as healthy."""
        self.consecutive_failures = 0
        self.is_healthy = True
    
    def mark_unhealthy(self, reason: Optional[str] = None) -> None:
        """Mark the connection as unhealthy."""
        self.is_healthy = False
        if reason and "health_check_failures" not in self.metadata:
            self.metadata["health_check_failures"] = []
        if reason:
            self.metadata["health_check_failures"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "reason": reason
            })
    
    def mark_healthy(self) -> None:
        """Mark the connection as healthy and reset failure count."""
        self.is_healthy = True
        self.consecutive_failures = 0
        self.last_health_check = datetime.utcnow()
        # Keep failure history but clear the active indicator
        if "health_check_failures" in self.metadata:
            self.metadata["last_health_recovery"] = datetime.utcnow().isoformat()
    
    def deactivate(self, reason: Optional[str] = None) -> None:
        """Deactivate the connection."""
        self.is_active = False
        if reason:
            self.metadata["deactivation_reason"] = reason
            self.metadata["deactivated_at"] = datetime.utcnow().isoformat()
    
    def activate(self) -> None:
        """Activate the connection."""
        self.is_active = True
        if "deactivation_reason" in self.metadata:
            self.metadata["reactivated_at"] = datetime.utcnow().isoformat()
    
    def soft_delete(self, reason: Optional[str] = None) -> None:
        """Soft delete the connection."""
        self.deleted_at = datetime.utcnow()
        self.is_active = False
        if reason:
            self.metadata["deletion_reason"] = reason
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the connection."""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the connection."""
        if tag in self.tags:
            self.tags.remove(tag)
    
    def has_tag(self, tag: str) -> bool:
        """Check if the connection has a specific tag."""
        return tag in self.tags
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id.value,
            "region_id": self.region_id.value,
            "connection_name": self.connection_name,
            "connection_type": self.connection_type.value,
            "host": self.host,
            "port": self.port,
            "database_name": self.database_name,
            "ssl_mode": self.ssl_mode,
            "username": self.username,
            "connection_options": self.connection_options,
            "pool_min_size": self.pool_min_size,
            "pool_max_size": self.pool_max_size,
            "pool_timeout_seconds": self.pool_timeout_seconds,
            "pool_recycle_seconds": self.pool_recycle_seconds,
            "pool_pre_ping": self.pool_pre_ping,
            "is_active": self.is_active,
            "is_healthy": self.is_healthy,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "consecutive_failures": self.consecutive_failures,
            "max_consecutive_failures": self.max_consecutive_failures,
            "metadata": self.metadata,
            "tags": self.tags,
            "health_status": self.health_status.value,
            "is_available": self.is_available,
            "safe_dsn": self.safe_dsn,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }
    
    @classmethod
    def from_url(cls, connection_name: str, database_url: str, region_id: str = "admin") -> "DatabaseConnection":
        """Create DatabaseConnection from a database URL.
        
        Args:
            connection_name: Name for this connection
            database_url: PostgreSQL URL like postgresql://user:pass@host:port/db
            region_id: Region identifier
            
        Returns:
            DatabaseConnection instance
        """
        import re
        from datetime import datetime, timezone
        from urllib.parse import urlparse
        
        # Parse the database URL
        parsed = urlparse(database_url)
        
        if parsed.scheme not in ('postgresql', 'postgres'):
            raise ValueError(f"Unsupported database scheme: {parsed.scheme}")
        
        # Extract connection details
        host = parsed.hostname or 'localhost'
        port = parsed.port or 5432
        database_name = parsed.path.lstrip('/') if parsed.path else 'postgres'
        username = parsed.username or 'postgres'
        password = parsed.password or ''
        
        # Parse query parameters for SSL mode
        from urllib.parse import parse_qs
        query_params = parse_qs(parsed.query) if parsed.query else {}
        ssl_mode = query_params.get('sslmode', ['prefer'])[0]  # Default to 'prefer' if not specified
        
        # Generate a unique ID using UUIDv7
        from ....utils.uuid import generate_uuid7
        connection_id = DatabaseConnectionId(generate_uuid7())
        
        return cls(
            id=connection_id,
            region_id=RegionId(region_id),
            connection_name=connection_name,
            connection_type=ConnectionType.PRIMARY,
            host=host,
            port=port,
            database_name=database_name,
            ssl_mode=ssl_mode,  # Parsed from URL or default to 'prefer'
            username=username,
            encrypted_password=password,  # TODO: Should be encrypted in production
            connection_options={},  # Default empty connection options for URL-based connections
            pool_min_size=5,
            pool_max_size=20,
            pool_timeout_seconds=30,
            pool_recycle_seconds=3600,
            pool_pre_ping=True,
            is_active=True,
            is_healthy=True,
            last_health_check=None,
            consecutive_failures=0,
            max_consecutive_failures=3,
            metadata={"source": "environment", "auto_created": True},
            tags=["admin", "environment"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            deleted_at=None,
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatabaseConnection":
        """Create from dictionary representation."""
        # Parse datetime fields
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        
        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
        
        deleted_at = None
        if data.get("deleted_at"):
            deleted_at = datetime.fromisoformat(data["deleted_at"].replace("Z", "+00:00"))
        
        last_health_check = None
        if data.get("last_health_check"):
            last_health_check = datetime.fromisoformat(data["last_health_check"].replace("Z", "+00:00"))
        
        return cls(
            id=DatabaseConnectionId(data["id"]),
            region_id=RegionId(data["region_id"]),
            connection_name=data["connection_name"],
            connection_type=ConnectionType(data["connection_type"]),
            host=data["host"],
            port=data.get("port", 5432),
            database_name=data.get("database_name", ""),
            ssl_mode=data.get("ssl_mode", "require"),
            username=data.get("username", "postgres"),
            encrypted_password=data.get("encrypted_password"),
            connection_options=data.get("connection_options", {}),
            pool_min_size=data.get("pool_min_size", 5),
            pool_max_size=data.get("pool_max_size", 20),
            pool_timeout_seconds=data.get("pool_timeout_seconds", 30),
            pool_recycle_seconds=data.get("pool_recycle_seconds", 3600),
            pool_pre_ping=data.get("pool_pre_ping", True),
            is_active=data.get("is_active", True),
            is_healthy=data.get("is_healthy", True),
            last_health_check=last_health_check,
            consecutive_failures=data.get("consecutive_failures", 0),
            max_consecutive_failures=data.get("max_consecutive_failures", 3),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
            created_at=created_at,
            updated_at=updated_at,
            deleted_at=deleted_at,
        )