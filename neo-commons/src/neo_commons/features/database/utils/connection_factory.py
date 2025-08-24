"""Asyncpg connection factory to eliminate duplicate connection logic."""

import asyncio
import logging
from typing import Optional, Dict, Any, Union, TYPE_CHECKING
from datetime import datetime
import asyncpg

if TYPE_CHECKING:
    from ..entities.database_connection import DatabaseConnection

logger = logging.getLogger(__name__)


class ConnectionFactory:
    """Factory for creating asyncpg connections with standard error handling."""
    
    @staticmethod
    async def create_connection(
        connection: "DatabaseConnection", 
        timeout: Optional[int] = None
    ) -> asyncpg.Connection:
        """Create a single asyncpg connection from DatabaseConnection.
        
        Args:
            connection: Database connection configuration
            timeout: Connection timeout in seconds (overrides connection config)
            
        Returns:
            asyncpg.Connection instance
            
        Raises:
            ConnectionError: If connection fails
        """
        try:
            return await asyncio.wait_for(
                asyncpg.connect(
                    host=connection.host,
                    port=connection.port,
                    database=connection.database_name,
                    user=connection.username,
                    password=connection.encrypted_password,
                    ssl=connection.ssl_mode,
                    **(connection.connection_options or {})
                ),
                timeout=timeout or connection.pool_timeout_seconds
            )
        except Exception as e:
            logger.error(f"Failed to create connection to {connection.connection_name}: {e}")
            raise ConnectionError(f"Connection failed: {e}") from e
    
    @staticmethod 
    async def create_connection_from_url(
        url: str,
        timeout: Optional[int] = None,
        connection_name: str = "unknown"
    ) -> asyncpg.Connection:
        """Create a connection from a database URL.
        
        Args:
            url: Database connection URL
            timeout: Connection timeout in seconds (default: 10)
            connection_name: Name for logging context
            
        Returns:
            asyncpg.Connection instance
            
        Raises:
            ConnectionError: If connection fails
        """
        try:
            return await asyncio.wait_for(
                asyncpg.connect(url),
                timeout=timeout or 10
            )
        except Exception as e:
            logger.error(f"Failed to create connection from URL for {connection_name}: {e}")
            raise ConnectionError(f"Connection failed for {connection_name}: {e}") from e
    
    @staticmethod
    async def create_connection_with_params(
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        ssl: Optional[str] = None,
        timeout: Optional[int] = None,
        connection_name: str = "unknown",
        **kwargs: Any
    ) -> asyncpg.Connection:
        """Create connection with individual parameters.
        
        Args:
            host: Database host
            port: Database port 
            database: Database name
            user: Username
            password: Password
            ssl: SSL mode (optional)
            timeout: Connection timeout in seconds (default: 10)
            connection_name: Name for logging context
            **kwargs: Additional connection parameters
            
        Returns:
            asyncpg.Connection instance
            
        Raises:
            ConnectionError: If connection fails
        """
        try:
            return await asyncio.wait_for(
                asyncpg.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=user,
                    password=password,
                    ssl=ssl,
                    **kwargs
                ),
                timeout=timeout or 10
            )
        except Exception as e:
            logger.error(f"Failed to create connection with params for {connection_name}: {e}")
            raise ConnectionError(f"Connection failed for {connection_name}: {e}") from e
    
    @staticmethod
    async def test_connection(
        connection: Union["DatabaseConnection", str],
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Test connection and return result with metrics.
        
        Args:
            connection: DatabaseConnection instance or URL string
            timeout: Connection timeout in seconds
            
        Returns:
            Dict with connection test results
        """
        start_time = datetime.utcnow()
        result = {
            "success": False,
            "connection_time_ms": 0,
            "error": None,
            "timestamp": start_time
        }
        
        try:
            # Check if it's a DatabaseConnection by checking for connection_name attribute
            if hasattr(connection, 'connection_name'):
                conn = await ConnectionFactory.create_connection(connection, timeout)
                connection_name = connection.connection_name
            else:  # URL string
                conn = await ConnectionFactory.create_connection_from_url(connection, timeout)
                connection_name = "url_connection"
            
            await conn.close()
            
            end_time = datetime.utcnow()
            result.update({
                "success": True,
                "connection_time_ms": (end_time - start_time).total_seconds() * 1000,
                "connection_name": connection_name
            })
            
        except Exception as e:
            end_time = datetime.utcnow()
            result.update({
                "success": False,
                "connection_time_ms": (end_time - start_time).total_seconds() * 1000,
                "error": str(e)
            })
        
        return result
    
    @staticmethod
    async def create_connection_pool(
        connection: "DatabaseConnection"
    ) -> asyncpg.Pool:
        """Create an asyncpg connection pool.
        
        Args:
            connection: Database connection configuration
            
        Returns:
            asyncpg.Pool instance
            
        Raises:
            ConnectionError: If pool creation fails
        """
        try:
            return await asyncpg.create_pool(
                host=connection.host,
                port=connection.port,
                database=connection.database_name,
                user=connection.username,
                password=connection.encrypted_password,
                ssl=connection.ssl_mode,
                min_size=connection.pool_min_size,
                max_size=connection.pool_max_size,
                timeout=connection.pool_timeout_seconds,
                max_inactive_connection_lifetime=connection.pool_recycle_seconds,
                **(connection.connection_options or {})
            )
        except Exception as e:
            logger.error(f"Failed to create pool for {connection.connection_name}: {e}")
            raise ConnectionError(f"Pool creation failed: {e}") from e