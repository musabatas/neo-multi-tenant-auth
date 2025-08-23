"""Database feature for neo-commons.

Feature-First architecture for database operations:
- entities/: Database domain objects, connections, and protocols
- services/: Database business logic and orchestration
- repositories/: Database access patterns and query execution
"""

# Core database protocols and entities
from .entities.protocols import ConnectionManager, DatabaseRepository
from .entities.connection import DatabaseConnection
from .entities.config import DatabaseSettings

# Database service orchestration
from .services.database_service import DatabaseService

__all__ = [
    # Core protocols and entities
    "ConnectionManager",
    "DatabaseRepository", 
    "DatabaseConnection",
    
    # Configuration
    "DatabaseSettings",
    
    # Services
    "DatabaseService",
]