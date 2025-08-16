"""
Database connection management using asyncpg.

Service wrapper that imports from neo-commons and provides NeoAdminApi-specific
database functionality while maintaining backward compatibility.
"""
from typing import Optional, Dict, Any

# Import from neo-commons
from neo_commons.database.connection import (
    DatabaseManager as NeoDatabaseManager,
    DynamicDatabaseManager as NeoDynamicDatabaseManager,
    DatabaseConfig,
    SchemaConfig
)

# Import service-specific settings
from src.common.config.settings import settings


class AdminDatabaseConfig:
    """Service-specific database configuration for NeoAdminApi implementing DatabaseConfig protocol."""
    
    @property
    def database_url(self) -> str:
        return str(settings.admin_database_url)
    
    @property
    def app_name(self) -> str:
        return settings.app_name
    
    @property
    def db_pool_size(self) -> int:
        return settings.db_pool_size
    
    @property
    def db_pool_recycle(self) -> int:
        return settings.db_pool_recycle
    
    @property
    def db_pool_timeout(self) -> int:
        return settings.db_pool_timeout


class AdminSchemaConfig:
    """Service-specific schema configuration for NeoAdminApi."""
    
    @property
    def admin_schema(self) -> str:
        return "admin"
    
    @property
    def shared_schema(self) -> str:
        return "platform_common"


class DatabaseManager(NeoDatabaseManager):
    """
    Service wrapper for NeoAdminApi that extends neo-commons DatabaseManager.
    
    Provides NeoAdminApi-specific database functionality while maintaining
    full compatibility with existing code.
    """
    
    def __init__(self):
        # Initialize with service-specific configuration
        config = AdminDatabaseConfig()
        super().__init__(config)
    
    async def fetch(self, query: str, *args, timeout: float = None):
        """Fetch multiple rows with metadata tracking."""
        # Track database operation for NeoAdminApi metadata
        try:
            from src.common.utils.metadata import MetadataCollector
            MetadataCollector.increment_db_queries()
        except ImportError:
            pass
        
        # Use neo-commons implementation
        return await super().fetch(query, *args, timeout=timeout)
    
    async def fetchrow(self, query: str, *args, timeout: float = None):
        """Fetch a single row with metadata tracking."""
        # Track database operation for NeoAdminApi metadata
        try:
            from src.common.utils.metadata import MetadataCollector
            MetadataCollector.increment_db_queries()
        except ImportError:
            pass
        
        # Use neo-commons implementation
        return await super().fetchrow(query, *args, timeout=timeout)
    
    async def fetchval(self, query: str, *args, column: int = 0, timeout: float = None):
        """Fetch a single value with metadata tracking."""
        # Track database operation for NeoAdminApi metadata
        try:
            from src.common.utils.metadata import MetadataCollector
            MetadataCollector.increment_db_queries()
        except ImportError:
            pass
        
        # Use neo-commons implementation
        return await super().fetchval(query, *args, column=column, timeout=timeout)


class DynamicDatabaseManager(NeoDynamicDatabaseManager):
    """
    Service wrapper for NeoAdminApi that extends neo-commons DynamicDatabaseManager.
    
    Provides NeoAdminApi-specific functionality with proper schema configuration.
    """
    
    def __init__(self):
        # Create admin database manager and schema config
        admin_db = DatabaseManager()
        schema_config = AdminSchemaConfig()
        super().__init__(admin_db, schema_config)


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
    from loguru import logger
    
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
    from loguru import logger
    
    logger.info("Closing database connections...")
    
    db = get_database()
    await db.close_pool()
    
    dynamic_db = get_dynamic_database()
    await dynamic_db.close_all_pools()
    
    logger.info("All database connections closed")