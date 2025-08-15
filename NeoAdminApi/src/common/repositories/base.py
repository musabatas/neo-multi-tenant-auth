"""
Base repository pattern for database operations.

MIGRATED TO NEO-COMMONS: Now using neo-commons BaseRepository with NeoAdminApi-specific extensions.
Import compatibility maintained - all existing imports continue to work.
"""

from typing import Optional, List, Dict, Any, TypeVar, Generic
from abc import ABC, abstractmethod
import logging

from src.common.database.connection import DatabaseManager, get_database
from src.common.models.pagination import PaginationParams

# NEO-COMMONS IMPORT: Use neo-commons BaseRepository as foundation
from neo_commons.repositories.base import BaseRepository as NeoCommonsBaseRepository

T = TypeVar('T')
logger = logging.getLogger(__name__)


class BaseRepository(NeoCommonsBaseRepository[T]):
    """
    NeoAdminApi base repository extending neo-commons BaseRepository.
    
    Maintains backward compatibility while leveraging neo-commons infrastructure.
    Adds NeoAdminApi-specific functionality like automatic database connection management.
    """
    
    def __init__(self, table_name: str, schema: str = "admin"):
        """Initialize NeoAdminApi repository with automatic database connection.
        
        Args:
            table_name: The database table name
            schema: The database schema (default: admin)
        """
        # Initialize neo-commons BaseRepository with NeoAdminApi database manager
        db_manager = get_database()
        super().__init__(table_name, schema, db_manager)
    
    # All methods are inherited from neo-commons BaseRepository
    # The neo-commons version includes additional features like:
    # - Enhanced dependency injection support
    # - Additional WHERE clause operators (__gt, __lt, __ne)
    # - include_deleted parameter for all methods
    # - exists() method for checking record existence
    # - restore() method for undeleting records
    # - Better error handling with database manager validation


# Re-export the class for backward compatibility
__all__ = [
    "BaseRepository",
]