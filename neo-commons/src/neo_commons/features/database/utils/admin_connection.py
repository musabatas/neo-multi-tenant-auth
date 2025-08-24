"""Admin database connection utilities to eliminate duplicate connection logic."""

import os
import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime

from .connection_factory import ConnectionFactory
from .queries import CONNECTION_REGISTRY_LOAD, CONNECTION_REGISTRY_BY_NAME
from .error_handling import database_error_handler, DatabaseOperationContext

if TYPE_CHECKING:
    from ..entities.database_connection import DatabaseConnection

logger = logging.getLogger(__name__)


class AdminConnectionUtils:
    """Utilities for admin database connection operations."""
    
    @staticmethod
    def get_admin_database_url() -> Optional[str]:
        """Get admin database URL from environment.
        
        Returns:
            Admin database URL or None if not configured
        """
        return os.getenv("ADMIN_DATABASE_URL")
    
    @staticmethod
    @database_error_handler("load database connections from admin")
    async def load_database_connections(
        exclude_admin: bool = True,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """Load all database connections from admin database.
        
        Args:
            exclude_admin: Whether to exclude the admin connection itself
            include_inactive: Whether to include inactive connections
            
        Returns:
            List of database connection records
            
        Raises:
            DatabaseError: If admin database is not available or query fails
        """
        admin_db_url = AdminConnectionUtils.get_admin_database_url()
        if not admin_db_url:
            raise ValueError("ADMIN_DATABASE_URL not configured")
        
        async with DatabaseOperationContext(
            "load_database_connections",
            connection_name="admin",
            track_timing=True
        ) as ctx:
            
            conn = await ConnectionFactory.create_connection_from_url(
                admin_db_url,
                connection_name="admin_load_connections"
            )
            
            try:
                # Build query based on parameters
                query = CONNECTION_REGISTRY_LOAD
                conditions = []
                
                if exclude_admin:
                    conditions.append("connection_name != 'admin'")
                
                if not include_inactive:
                    # is_active = true is already in CONNECTION_REGISTRY_LOAD
                    pass
                else:
                    # Override the is_active = true condition
                    query = query.replace("WHERE is_active = true", "WHERE")
                
                if conditions:
                    query += " AND " + " AND ".join(conditions)
                
                ctx.add_context("query_conditions", conditions)
                
                rows = await conn.fetch(query)
                results = [dict(row) for row in rows]
                
                ctx.add_context("connections_loaded", len(results))
                logger.info(f"Loaded {len(results)} database connections from admin database")
                
                return results
                
            finally:
                await conn.close()
    
    @staticmethod
    @database_error_handler("load specific database connection from admin")
    async def load_database_connection_by_name(connection_name: str) -> Optional[Dict[str, Any]]:
        """Load a specific database connection by name from admin database.
        
        Args:
            connection_name: Name of the connection to load
            
        Returns:
            Database connection record or None if not found
        """
        admin_db_url = AdminConnectionUtils.get_admin_database_url()
        if not admin_db_url:
            raise ValueError("ADMIN_DATABASE_URL not configured")
        
        async with DatabaseOperationContext(
            "load_database_connection_by_name",
            connection_name="admin",
            track_timing=True
        ) as ctx:
            
            ctx.add_context("target_connection", connection_name)
            
            conn = await ConnectionFactory.create_connection_from_url(
                admin_db_url,
                connection_name="admin_load_by_name"
            )
            
            try:
                row = await conn.fetchrow(CONNECTION_REGISTRY_BY_NAME, connection_name)
                
                if row:
                    result = dict(row)
                    logger.debug(f"Found connection '{connection_name}' in admin database")
                    return result
                else:
                    logger.warning(f"Connection '{connection_name}' not found in admin database")
                    return None
                    
            finally:
                await conn.close()
    
    @staticmethod
    @database_error_handler("test admin database connectivity")
    async def test_admin_database_connection() -> Dict[str, Any]:
        """Test admin database connectivity and return connection info.
        
        Returns:
            Dictionary with connection test results and database info
        """
        admin_db_url = AdminConnectionUtils.get_admin_database_url()
        if not admin_db_url:
            return {
                "success": False,
                "error": "ADMIN_DATABASE_URL not configured",
                "timestamp": datetime.utcnow()
            }
        
        start_time = datetime.utcnow()
        
        try:
            conn = await ConnectionFactory.create_connection_from_url(
                admin_db_url,
                connection_name="admin_test"
            )
            
            try:
                # Get database info
                info_query = """
                    SELECT 
                        current_database() as database_name,
                        current_user as current_user,
                        version() as database_version,
                        inet_server_addr() as server_address,
                        inet_server_port() as server_port
                """
                
                row = await conn.fetchrow(info_query)
                db_info = dict(row) if row else {}
                
                # Test admin schema access
                schema_test = await conn.fetchval(
                    "SELECT COUNT(*) FROM admin.database_connections WHERE deleted_at IS NULL"
                )
                
                end_time = datetime.utcnow()
                
                result = {
                    "success": True,
                    "connection_time_ms": (end_time - start_time).total_seconds() * 1000,
                    "database_info": db_info,
                    "admin_connections_count": schema_test,
                    "timestamp": start_time
                }
                
                logger.info(f"Admin database connection test successful in {result['connection_time_ms']:.2f}ms")
                return result
                
            finally:
                await conn.close()
                
        except Exception as e:
            end_time = datetime.utcnow()
            result = {
                "success": False,
                "connection_time_ms": (end_time - start_time).total_seconds() * 1000,
                "error": str(e),
                "timestamp": start_time
            }
            
            logger.error(f"Admin database connection test failed: {e}")
            return result
    
    @staticmethod
    @database_error_handler("execute admin database query")
    async def execute_admin_query(
        query: str,
        *args: Any,
        fetch_method: str = "fetch"
    ) -> Any:
        """Execute a query on the admin database.
        
        Args:
            query: SQL query to execute
            args: Query parameters
            fetch_method: Method to use ('fetch', 'fetchrow', 'fetchval', 'execute')
            
        Returns:
            Query results based on fetch_method
        """
        admin_db_url = AdminConnectionUtils.get_admin_database_url()
        if not admin_db_url:
            raise ValueError("ADMIN_DATABASE_URL not configured")
        
        async with DatabaseOperationContext(
            f"execute_admin_query_{fetch_method}",
            connection_name="admin",
            track_timing=True
        ) as ctx:
            
            ctx.add_context("query_preview", query[:100] + "..." if len(query) > 100 else query)
            ctx.add_context("param_count", len(args))
            
            conn = await ConnectionFactory.create_connection_from_url(
                admin_db_url,
                connection_name="admin_query"
            )
            
            try:
                if fetch_method == "fetch":
                    result = await conn.fetch(query, *args)
                    return [dict(row) for row in result]
                elif fetch_method == "fetchrow":
                    row = await conn.fetchrow(query, *args)
                    return dict(row) if row else None
                elif fetch_method == "fetchval":
                    return await conn.fetchval(query, *args)
                elif fetch_method == "execute":
                    return await conn.execute(query, *args)
                else:
                    raise ValueError(f"Invalid fetch_method: {fetch_method}")
                    
            finally:
                await conn.close()
    
    @staticmethod
    def build_connection_from_row(row_data: Dict[str, Any]) -> "DatabaseConnection":
        """Build a DatabaseConnection object from database row data.
        
        Args:
            row_data: Dictionary containing database connection fields
            
        Returns:
            DatabaseConnection instance
        """
        # Import here to avoid circular imports
        from ..entities.database_connection import DatabaseConnection
        
        return DatabaseConnection(
            id=row_data["id"],
            connection_name=row_data["connection_name"],
            connection_type=row_data["connection_type"],
            region_id=row_data["region_id"],
            host=row_data["host"],
            port=row_data["port"],
            database_name=row_data["database_name"],
            username=row_data["username"],
            encrypted_password=row_data["encrypted_password"],
            ssl_mode=row_data["ssl_mode"],
            connection_options=row_data.get("connection_options", {}),  # Default empty dict if field missing
            is_active=row_data["is_active"],
            is_healthy=row_data["is_healthy"],
            pool_min_size=row_data["pool_min_size"],
            pool_max_size=row_data["pool_max_size"],
            pool_timeout_seconds=row_data["pool_timeout_seconds"],
            pool_recycle_seconds=row_data["pool_recycle_seconds"],
            pool_pre_ping=row_data["pool_pre_ping"],
            consecutive_failures=row_data.get("consecutive_failures", 0),
            max_consecutive_failures=row_data.get("max_consecutive_failures", 5),
            last_health_check=row_data.get("last_health_check"),
            metadata=row_data.get("metadata", {}),
            tags=row_data.get("tags", []),
            created_at=row_data.get("created_at"),
            updated_at=row_data.get("updated_at"),
            deleted_at=row_data.get("deleted_at")
        )