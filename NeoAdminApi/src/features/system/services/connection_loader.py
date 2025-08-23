"""Database connection loader service.

This service loads database connections from the admin.database_connections table
and registers them with the neo-commons connection registry.
"""

import logging
from typing import List, Dict, Any, Optional
import asyncpg

from neo_commons.features.database.entities.database_connection import DatabaseConnection
from neo_commons.features.database.entities.protocols import ConnectionRegistry
from neo_commons.core.value_objects import DatabaseConnectionId, RegionId
from neo_commons.utils.uuid import generate_uuid7
from neo_commons.utils.encryption import decrypt_password, is_encrypted

logger = logging.getLogger(__name__)


class DatabaseConnectionLoader:
    """Service for loading database connections from admin.database_connections table."""
    
    def __init__(self, admin_database_url: str, connection_registry: ConnectionRegistry):
        self.admin_database_url = admin_database_url
        self.connection_registry = connection_registry
    
    async def load_all_connections(self) -> List[DatabaseConnection]:
        """Load all active database connections from admin.database_connections table."""
        try:
            # Connect to admin database
            conn = await asyncpg.connect(self.admin_database_url)
            
            try:
                # Query all active database connections
                query = """
                    SELECT 
                        id,
                        region_id,
                        connection_name,
                        connection_type,
                        host,
                        port,
                        database_name,
                        ssl_mode,
                        username,
                        encrypted_password,
                        pool_min_size,
                        pool_max_size,
                        pool_timeout_seconds,
                        pool_recycle_seconds,
                        pool_pre_ping,
                        is_active,
                        is_healthy,
                        last_health_check,
                        consecutive_failures,
                        max_consecutive_failures,
                        metadata,
                        tags,
                        created_at,
                        updated_at
                    FROM admin.database_connections 
                    WHERE deleted_at IS NULL AND is_active = true
                    ORDER BY connection_name
                """
                
                rows = await conn.fetch(query)
                connections = []
                
                for row in rows:
                    try:
                        connection = self._row_to_connection(row)
                        connections.append(connection)
                        logger.info(f"Loaded connection: {connection.connection_name}")
                        
                    except Exception as e:
                        logger.error(f"Failed to convert row to connection: {e}")
                        continue
                
                logger.info(f"Loaded {len(connections)} database connections from admin.database_connections")
                return connections
                
            finally:
                await conn.close()
                
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
            # Load connections from database
            connections = await self.load_all_connections()
            
            # Register with neo-commons
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
            logger.error(f"Failed to load and register connections: {e}")
            return {
                "status": "error",
                "error": str(e),
                "loaded_count": 0,
                "registered_count": 0,
                "failed_count": 0
            }
    
    def _row_to_connection(self, row) -> DatabaseConnection:
        """Convert a database row to a DatabaseConnection entity."""
        from neo_commons.features.database.entities.database_connection import ConnectionType
        from datetime import datetime, timezone
        
        # Map string connection type to enum
        connection_type_mapping = {
            "primary": ConnectionType.PRIMARY,
            "replica": ConnectionType.REPLICA,
            "analytics": ConnectionType.ANALYTICS,
            "backup": ConnectionType.BACKUP
        }
        
        connection_type = connection_type_mapping.get(
            row["connection_type"], 
            ConnectionType.PRIMARY
        )
        
        # Decrypt password if it's encrypted
        password = row["encrypted_password"] or ""
        if password and is_encrypted(password):
            try:
                password = decrypt_password(password)
                logger.debug(f"Successfully decrypted password for connection: {row['connection_name']}")
            except Exception as e:
                logger.error(f"Failed to decrypt password for connection {row['connection_name']}: {e}")
                # Keep encrypted password - connection will fail health checks but will be registered
        
        # Create DatabaseConnection entity
        connection = DatabaseConnection(
            id=DatabaseConnectionId(str(row["id"])),
            region_id=RegionId(str(row["region_id"])),
            connection_name=row["connection_name"],
            connection_type=connection_type,
            host=row["host"],
            port=row["port"] or 5432,
            database_name=row["database_name"],
            ssl_mode=row["ssl_mode"] or "prefer",
            username=row["username"] or "postgres",
            encrypted_password=password,
            pool_min_size=row["pool_min_size"] or 5,
            pool_max_size=row["pool_max_size"] or 20,
            pool_timeout_seconds=row["pool_timeout_seconds"] or 30,
            pool_recycle_seconds=row["pool_recycle_seconds"] or 3600,
            pool_pre_ping=row["pool_pre_ping"] if row["pool_pre_ping"] is not None else True,
            is_active=row["is_active"] if row["is_active"] is not None else True,
            is_healthy=row["is_healthy"] if row["is_healthy"] is not None else True,
            last_health_check=row["last_health_check"],
            consecutive_failures=row["consecutive_failures"] or 0,
            max_consecutive_failures=row["max_consecutive_failures"] or 3,
            metadata=row["metadata"] or {},
            tags=row["tags"] or [],
            created_at=row["created_at"] or datetime.now(timezone.utc),
            updated_at=row["updated_at"] or datetime.now(timezone.utc),
            deleted_at=row.get("deleted_at")
        )
        
        return connection