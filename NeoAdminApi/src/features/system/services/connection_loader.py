"""Database connection loader service.

This service loads database connections from the admin.database_connections table
and registers them with the neo-commons connection registry using centralized utilities.
"""

import logging
from typing import List, Dict, Any

from neo_commons.features.database.entities.database_connection import DatabaseConnection
from neo_commons.features.database.entities.protocols import ConnectionRegistry
from neo_commons.features.database.utils.admin_connection import AdminConnectionUtils

logger = logging.getLogger(__name__)


class DatabaseConnectionLoader:
    """Service for loading database connections from admin.database_connections table."""
    
    def __init__(self, connection_registry: ConnectionRegistry):
        self.connection_registry = connection_registry
    
    async def load_all_connections(self) -> List[DatabaseConnection]:
        """Load all active database connections from admin.database_connections table."""
        try:
            # Use neo-commons AdminConnectionUtils for centralized connection loading
            connection_data = await AdminConnectionUtils.load_database_connections(
                exclude_admin=False,  # Include admin connection
                include_inactive=False  # Only active connections
            )
            
            connections = []
            for row_data in connection_data:
                try:
                    # Use neo-commons utility to build connection from row data
                    connection = AdminConnectionUtils.build_connection_from_row(row_data)
                    connections.append(connection)
                    logger.info(f"Loaded connection: {connection.connection_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to convert row to connection: {e}")
                    continue
            
            logger.info(f"Loaded {len(connections)} database connections using neo-commons utilities")
            return connections
            
        except Exception as e:
            logger.error(f"Failed to load database connections: {e}")
            raise
    
    async def register_connections(self, connections: List[DatabaseConnection]) -> Dict[str, Any]:
        """Register loaded connections with the neo-commons connection registry."""
        results = {
            "registered": 0,
            "failed": 0,
            "errors": []
        }
        
        for connection in connections:
            try:
                await self.connection_registry.register_connection(connection)
                results["registered"] += 1
                logger.info(f"Registered connection: {connection.connection_name}")
                
            except Exception as e:
                results["failed"] += 1
                error_msg = f"Failed to register {connection.connection_name}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(error_msg)
        
        return results
    
    async def load_and_register_all(self) -> Dict[str, Any]:
        """Load all connections from database and register them with neo-commons."""
        try:
            # Load connections using neo-commons utilities
            connections = await self.load_all_connections()
            
            # Register with neo-commons connection registry
            registration_results = await self.register_connections(connections)
            
            return {
                "status": "success",
                "loaded_count": len(connections),
                "registered_count": registration_results["registered"],
                "failed_count": registration_results["failed"],
                "errors": registration_results["errors"],
                "connections": [
                    {
                        "name": conn.connection_name,
                        "type": conn.connection_type.value,
                        "host": conn.host,
                        "database": conn.database_name,
                        "is_active": conn.is_active,
                        "is_healthy": conn.is_healthy
                    }
                    for conn in connections
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to load and register connections using neo-commons: {e}")
            return {
                "status": "error",
                "error": str(e),
                "loaded_count": 0,
                "registered_count": 0,
                "failed_count": 0
            }
    
