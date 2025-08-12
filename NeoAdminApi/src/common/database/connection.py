"""
Database connection management using asyncpg.
"""
import asyncio
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
import asyncpg
from asyncpg import Pool, Connection, Record
from loguru import logger

from src.common.config.settings import settings


class DatabaseManager:
    """Manages database connections and pools."""
    
    def __init__(self):
        self.pool: Optional[Pool] = None
        self.dsn = str(settings.admin_database_url).replace("+asyncpg", "")
        
    async def create_pool(self) -> Pool:
        """Create and return a connection pool."""
        if self.pool is None:
            logger.info(f"Creating database pool with size {settings.db_pool_size}")
            self.pool = await asyncpg.create_pool(
                self.dsn,
                min_size=10,
                max_size=settings.db_pool_size,
                max_inactive_connection_lifetime=settings.db_pool_recycle,
                command_timeout=settings.db_pool_timeout,
                server_settings={
                    'application_name': settings.app_name,
                    'jit': 'on'
                }
            )
            logger.info("Database pool created successfully")
        return self.pool
    
    async def close_pool(self):
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Database pool closed")
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool."""
        if not self.pool:
            await self.create_pool()
        
        async with self.pool.acquire() as connection:
            yield connection
    
    @asynccontextmanager
    async def transaction(self):
        """Create a transaction context."""
        async with self.acquire() as connection:
            async with connection.transaction():
                yield connection
    
    async def execute(self, query: str, *args, timeout: float = None) -> str:
        """Execute a query without returning results."""
        async with self.acquire() as connection:
            return await connection.execute(query, *args, timeout=timeout)
    
    async def executemany(self, query: str, args: List[tuple], timeout: float = None) -> str:
        """Execute a query multiple times with different arguments."""
        async with self.acquire() as connection:
            return await connection.executemany(query, args, timeout=timeout)
    
    async def fetch(self, query: str, *args, timeout: float = None) -> List[Record]:
        """Fetch multiple rows."""
        # Track database operation for metadata
        try:
            from src.common.utils.metadata import MetadataCollector
            MetadataCollector.increment_db_queries()
        except ImportError:
            pass
        
        async with self.acquire() as connection:
            return await connection.fetch(query, *args, timeout=timeout)
    
    async def fetchrow(self, query: str, *args, timeout: float = None) -> Optional[Record]:
        """Fetch a single row."""
        # Track database operation for metadata
        try:
            from src.common.utils.metadata import MetadataCollector
            MetadataCollector.increment_db_queries()
        except ImportError:
            pass
        
        async with self.acquire() as connection:
            return await connection.fetchrow(query, *args, timeout=timeout)
    
    async def fetchval(self, query: str, *args, column: int = 0, timeout: float = None) -> Any:
        """Fetch a single value."""
        # Track database operation for metadata
        try:
            from src.common.utils.metadata import MetadataCollector
            MetadataCollector.increment_db_queries()
        except ImportError:
            pass
        
        async with self.acquire() as connection:
            return await connection.fetchval(query, *args, column=column, timeout=timeout)
    
    async def health_check(self) -> bool:
        """Check database health."""
        try:
            async with self.acquire() as connection:
                result = await connection.fetchval("SELECT 1")
                return result == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


class DynamicDatabaseManager:
    """Manages dynamic database connections for multi-region support."""
    
    def __init__(self):
        self.pools: Dict[str, Pool] = {}
        self.connections_cache: Dict[str, Dict[str, Any]] = {}
        self.last_refresh: Optional[float] = None
        
    async def load_database_connections(self) -> Dict[str, Dict[str, Any]]:
        """Load database connections from admin.database_connections table."""
        db = get_database()
        
        query = """
            SELECT 
                dc.id as connection_id,
                dc.connection_name,
                dc.connection_type,
                dc.host,
                dc.port,
                dc.database_name,
                dc.username,
                dc.encrypted_password as password,
                dc.ssl_mode,
                dc.pool_max_size as max_connections,
                dc.is_active,
                false as is_read_only,
                1 as priority,
                r.code as region_code,
                r.name as region_name
            FROM admin.database_connections dc
            LEFT JOIN admin.regions r ON dc.region_id = r.id
            WHERE dc.is_active = true
            ORDER BY dc.connection_name
        """
        
        rows = await db.fetch(query)
        
        connections = {}
        for row in rows:
            connection_id = str(row['connection_id'])
            connections[connection_id] = {
                'connection_id': connection_id,
                'connection_name': row['connection_name'],
                'connection_type': row['connection_type'],
                'host': row['host'],
                'port': row['port'],
                'database_name': row['database_name'],
                'username': row['username'],
                'password': row['password'],
                'ssl_mode': row['ssl_mode'] or 'prefer',
                'max_connections': row['max_connections'] or 20,
                'is_read_only': row['is_read_only'],
                'priority': row['priority'],
                'region_code': row['region_code'],
                'region_name': row['region_name'],
                'dsn': self._build_dsn(row)
            }
        
        self.connections_cache = connections
        return connections
    
    def _build_dsn(self, connection_info: Record) -> str:
        """Build DSN from connection information."""
        ssl_param = f"?sslmode={connection_info['ssl_mode']}" if connection_info['ssl_mode'] else ""
        return (
            f"postgresql://{connection_info['username']}:{connection_info['password']}"
            f"@{connection_info['host']}:{connection_info['port']}"
            f"/{connection_info['database_name']}{ssl_param}"
        )
    
    async def get_pool(self, connection_id: str) -> Pool:
        """Get or create a connection pool for a specific database."""
        if connection_id not in self.pools:
            if connection_id not in self.connections_cache:
                await self.load_database_connections()
            
            if connection_id not in self.connections_cache:
                raise ValueError(f"Database connection {connection_id} not found")
            
            conn_info = self.connections_cache[connection_id]
            logger.info(f"Creating pool for {conn_info['connection_name']} ({conn_info['region_code']})")
            
            self.pools[connection_id] = await asyncpg.create_pool(
                conn_info['dsn'],
                min_size=5,
                max_size=conn_info['max_connections'],
                server_settings={
                    'application_name': f"{settings.app_name}-{conn_info['region_code']}",
                    'jit': 'on'
                }
            )
        
        return self.pools[connection_id]
    
    async def get_regional_pool(self, region_code: str, connection_type: str = 'shared') -> Pool:
        """Get a connection pool for a specific region and type."""
        for conn_id, conn_info in self.connections_cache.items():
            if (conn_info['region_code'] == region_code and 
                conn_info['connection_type'] == connection_type):
                return await self.get_pool(conn_id)
        
        # Refresh cache and try again
        await self.load_database_connections()
        
        for conn_id, conn_info in self.connections_cache.items():
            if (conn_info['region_code'] == region_code and 
                conn_info['connection_type'] == connection_type):
                return await self.get_pool(conn_id)
        
        raise ValueError(f"No {connection_type} database found for region {region_code}")
    
    async def close_all_pools(self):
        """Close all connection pools."""
        for connection_id, pool in self.pools.items():
            await pool.close()
            logger.info(f"Closed pool for connection {connection_id}")
        self.pools.clear()
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all database connections."""
        results = {}
        
        for conn_id, conn_info in self.connections_cache.items():
            try:
                pool = await self.get_pool(conn_id)
                async with pool.acquire() as connection:
                    result = await connection.fetchval("SELECT 1")
                    results[conn_info['connection_name']] = (result == 1)
            except Exception as e:
                logger.error(f"Health check failed for {conn_info['connection_name']}: {e}")
                results[conn_info['connection_name']] = False
        
        return results


# Global instances
_database_manager: Optional[DatabaseManager] = None
_dynamic_database_manager: Optional[DynamicDatabaseManager] = None


def get_database() -> DatabaseManager:
    """Get the global database manager instance."""
    global _database_manager
    if _database_manager is None:
        _database_manager = DatabaseManager()
    return _database_manager


def get_dynamic_database() -> DynamicDatabaseManager:
    """Get the global dynamic database manager instance."""
    global _dynamic_database_manager
    if _dynamic_database_manager is None:
        _dynamic_database_manager = DynamicDatabaseManager()
    return _dynamic_database_manager


async def init_database():
    """Initialize database connections."""
    logger.info("Initializing database connections...")
    
    # Initialize main admin database
    db = get_database()
    await db.create_pool()
    
    # Initialize dynamic database connections
    dynamic_db = get_dynamic_database()
    await dynamic_db.load_database_connections()
    
    logger.info("Database initialization complete")


async def close_database():
    """Close all database connections."""
    logger.info("Closing database connections...")
    
    db = get_database()
    await db.close_pool()
    
    dynamic_db = get_dynamic_database()
    await dynamic_db.close_all_pools()
    
    logger.info("All database connections closed")