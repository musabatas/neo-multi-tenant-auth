"""Database connection registry implementation."""

import logging
from typing import Dict, Optional, List, Set
from datetime import datetime
import asyncio

from ..entities.database_protocols import ConnectionRegistry, ConnectionManager
from ..entities.database_connection import DatabaseConnection
from ....core.value_objects.identifiers import DatabaseConnectionId, RegionId
from ....config.constants import ConnectionType, HealthStatus
from ....core.exceptions.database import (
    ConnectionNotFoundError,
    EntityAlreadyExistsError,
    DatabaseConfigurationError
)
from ...tenants.services.tenant_cache import TenantCache

logger = logging.getLogger(__name__)


class InMemoryConnectionRegistry(ConnectionRegistry):
    """In-memory implementation of ConnectionRegistry."""
    
    def __init__(self, cache: Optional[TenantCache] = None):
        self._connections: Dict[str, DatabaseConnection] = {}  # connection_id -> connection
        self._name_index: Dict[str, str] = {}  # connection_name -> connection_id
        self._type_index: Dict[ConnectionType, Set[str]] = {}  # type -> set of connection_ids
        self._region_index: Dict[str, Set[str]] = {}  # region_id -> set of connection_ids
        self._lock = asyncio.Lock()
        self._cache = cache
    
    async def initialize(self) -> None:
        """Initialize the connection registry."""
        # For in-memory registry, initialization is complete during construction
        pass
    
    async def register_connection(self, connection: DatabaseConnection) -> None:
        """Register a new database connection."""
        async with self._lock:
            connection_id = str(connection.id)
            
            # Check if connection already exists
            if connection_id in self._connections:
                raise EntityAlreadyExistsError("DatabaseConnection", connection_id)
            
            # Check if name is already taken
            if connection.connection_name in self._name_index:
                existing_id = self._name_index[connection.connection_name]
                if existing_id != connection_id:
                    raise EntityAlreadyExistsError(
                        "DatabaseConnection", 
                        f"name '{connection.connection_name}'"
                    )
            
            # Register the connection
            self._connections[connection_id] = connection
            self._name_index[connection.connection_name] = connection_id
            
            # Update type index
            if connection.connection_type not in self._type_index:
                self._type_index[connection.connection_type] = set()
            self._type_index[connection.connection_type].add(connection_id)
            
            # Update region index
            region_id = str(connection.region_id)
            if region_id not in self._region_index:
                self._region_index[region_id] = set()
            self._region_index[region_id].add(connection_id)
            
            # Cache the connection info
            if self._cache:
                cache_key = f"db:connection:{connection.connection_name}"
                await self._cache.set(cache_key, connection_id, ttl=1800)  # 30 minutes
            
            logger.info(f"Registered connection: {connection.connection_name} ({connection_id})")
    
    async def get_connection(self, connection_id: DatabaseConnectionId) -> Optional[DatabaseConnection]:
        """Get a connection by ID."""
        async with self._lock:
            connection_id_str = str(connection_id)
            connection = self._connections.get(connection_id_str)
            
            if connection and not connection.is_deleted:
                return connection
            
            return None
    
    async def get_connection_by_name(self, connection_name: str) -> Optional[DatabaseConnection]:
        """Get a connection by name."""
        async with self._lock:
            # Check cache first
            if self._cache:
                cache_key = f"db:connection:{connection_name}"
                cached_id = await self._cache.get(cache_key)
                if cached_id and cached_id in self._connections:
                    connection = self._connections[cached_id]
                    if not connection.is_deleted:
                        return connection
            
            # Check name index
            connection_id = self._name_index.get(connection_name)
            if connection_id and connection_id in self._connections:
                connection = self._connections[connection_id]
                if not connection.is_deleted:
                    return connection
            
            return None
    
    async def list_connections(self,
                              connection_type: Optional[ConnectionType] = None,
                              region_id: Optional[RegionId] = None,
                              active_only: bool = True) -> List[DatabaseConnection]:
        """List connections with optional filtering."""
        async with self._lock:
            connections = []
            
            # Start with all connections or filter by type
            if connection_type:
                connection_ids = self._type_index.get(connection_type, set())
            else:
                connection_ids = set(self._connections.keys())
            
            # Filter by region if specified
            if region_id:
                region_connections = self._region_index.get(str(region_id), set())
                connection_ids = connection_ids.intersection(region_connections)
            
            # Build result list
            for connection_id in connection_ids:
                connection = self._connections.get(connection_id)
                if connection:
                    # Apply filters
                    if connection.is_deleted:
                        continue
                    
                    if active_only and not connection.is_active:
                        continue
                    
                    connections.append(connection)
            
            # Sort by connection name for consistent ordering
            connections.sort(key=lambda c: c.connection_name)
            return connections
    
    async def update_connection(self, connection: DatabaseConnection) -> None:
        """Update an existing connection."""
        async with self._lock:
            connection_id = str(connection.id)
            
            if connection_id not in self._connections:
                raise ConnectionNotFoundError(connection.connection_name)
            
            old_connection = self._connections[connection_id]
            
            # Update name index if name changed
            if old_connection.connection_name != connection.connection_name:
                # Remove old name mapping
                self._name_index.pop(old_connection.connection_name, None)
                
                # Check if new name is available
                if connection.connection_name in self._name_index:
                    existing_id = self._name_index[connection.connection_name]
                    if existing_id != connection_id:
                        raise EntityAlreadyExistsError(
                            "DatabaseConnection", 
                            f"name '{connection.connection_name}'"
                        )
                
                # Add new name mapping
                self._name_index[connection.connection_name] = connection_id
            
            # Update type index if type changed
            if old_connection.connection_type != connection.connection_type:
                # Remove from old type set
                old_type_set = self._type_index.get(old_connection.connection_type, set())
                old_type_set.discard(connection_id)
                
                # Add to new type set
                if connection.connection_type not in self._type_index:
                    self._type_index[connection.connection_type] = set()
                self._type_index[connection.connection_type].add(connection_id)
            
            # Update region index if region changed
            old_region_id = str(old_connection.region_id)
            new_region_id = str(connection.region_id)
            
            if old_region_id != new_region_id:
                # Remove from old region set
                old_region_set = self._region_index.get(old_region_id, set())
                old_region_set.discard(connection_id)
                
                # Add to new region set
                if new_region_id not in self._region_index:
                    self._region_index[new_region_id] = set()
                self._region_index[new_region_id].add(connection_id)
            
            # Update the connection
            connection.updated_at = datetime.utcnow()
            self._connections[connection_id] = connection
            
            # Update cache
            if self._cache:
                cache_key = f"db:connection:{connection.connection_name}"
                await self._cache.set(cache_key, connection_id, ttl=1800)
                
                # Invalidate old name if it changed
                if old_connection.connection_name != connection.connection_name:
                    old_cache_key = f"db:connection:{old_connection.connection_name}"
                    await self._cache.delete(old_cache_key)
            
            logger.info(f"Updated connection: {connection.connection_name} ({connection_id})")
    
    async def remove_connection(self, connection_id: DatabaseConnectionId) -> None:
        """Remove a connection from the registry."""
        async with self._lock:
            connection_id_str = str(connection_id)
            
            if connection_id_str not in self._connections:
                raise ConnectionNotFoundError(str(connection_id))
            
            connection = self._connections[connection_id_str]
            
            # Remove from all indexes
            self._name_index.pop(connection.connection_name, None)
            
            # Remove from type index
            type_set = self._type_index.get(connection.connection_type, set())
            type_set.discard(connection_id_str)
            
            # Remove from region index
            region_id = str(connection.region_id)
            region_set = self._region_index.get(region_id, set())
            region_set.discard(connection_id_str)
            
            # Remove the connection
            del self._connections[connection_id_str]
            
            # Remove from cache
            if self._cache:
                cache_key = f"db:connection:{connection.connection_name}"
                await self._cache.delete(cache_key)
            
            logger.info(f"Removed connection: {connection.connection_name} ({connection_id_str})")
    
    async def get_healthy_connections(self, 
                                    connection_type: Optional[ConnectionType] = None,
                                    region_id: Optional[RegionId] = None) -> List[DatabaseConnection]:
        """Get all healthy connections."""
        connections = await self.list_connections(connection_type, region_id, active_only=True)
        
        # Filter to only healthy connections
        healthy_connections = [
            conn for conn in connections 
            if conn.is_healthy and conn.health_status == HealthStatus.HEALTHY
        ]
        
        return healthy_connections
    
    async def get_connections_by_region(self, region_id: RegionId) -> List[DatabaseConnection]:
        """Get all connections in a specific region."""
        return await self.list_connections(region_id=region_id, active_only=False)
    
    async def get_connections_by_type(self, connection_type: ConnectionType) -> List[DatabaseConnection]:
        """Get all connections of a specific type."""
        return await self.list_connections(connection_type=connection_type, active_only=False)
    
    async def get_primary_connections(self) -> List[DatabaseConnection]:
        """Get all primary connections."""
        return await self.get_connections_by_type(ConnectionType.PRIMARY)
    
    async def get_replica_connections(self) -> List[DatabaseConnection]:
        """Get all replica connections.""" 
        return await self.get_connections_by_type(ConnectionType.REPLICA)
    
    async def get_analytics_connections(self) -> List[DatabaseConnection]:
        """Get all analytics connections."""
        return await self.get_connections_by_type(ConnectionType.ANALYTICS)
    
    async def update_health_status(self, 
                                  connection_id: DatabaseConnectionId,
                                  is_healthy: bool,
                                  consecutive_failures: int = 0) -> None:
        """Update health status for a connection."""
        async with self._lock:
            connection = await self.get_connection(connection_id)
            if connection:
                connection.is_healthy = is_healthy
                connection.consecutive_failures = consecutive_failures
                connection.last_health_check = datetime.utcnow()
                
                if is_healthy:
                    connection.reset_failure_count()
                else:
                    connection.mark_unhealthy("Health check failed")
                
                # Update in registry
                await self.update_connection(connection)
    
    async def get_registry_stats(self) -> Dict[str, int]:
        """Get statistics about the connection registry."""
        async with self._lock:
            total_connections = len(self._connections)
            active_connections = sum(1 for c in self._connections.values() if c.is_active)
            healthy_connections = sum(1 for c in self._connections.values() if c.is_healthy)
            
            type_counts = {}
            for conn_type in ConnectionType:
                type_counts[conn_type.value] = len(self._type_index.get(conn_type, set()))
            
            return {
                "total_connections": total_connections,
                "active_connections": active_connections,
                "healthy_connections": healthy_connections,
                "deleted_connections": total_connections - active_connections,
                **type_counts
            }
    
    async def clear_registry(self) -> None:
        """Clear all connections from the registry (for testing)."""
        async with self._lock:
            self._connections.clear()
            self._name_index.clear()
            self._type_index.clear()
            self._region_index.clear()
            
            if self._cache:
                await self._cache.delete_pattern("db:connection:*")
            
            logger.warning("Cleared all connections from registry")
    
    async def get_all_connections(self) -> List[DatabaseConnection]:
        """Get all registered connections."""
        async with self._lock:
            return list(self._connections.values())
    
    async def list_connections(self, active_only: bool = False) -> List[DatabaseConnection]:
        """List connections with optional filtering by active status."""
        async with self._lock:
            if active_only:
                return [conn for conn in self._connections.values() if conn.is_active]
            return list(self._connections.values())