"""
NeoAdminApi Connection Provider for neo-commons BaseRepository.

This module provides a ConnectionProvider implementation that allows neo-commons 
repositories to use NeoAdminApi's database connection instead of trying to create
their own DatabaseManager instance.
"""

from typing import Optional
from neo_commons.repositories.protocols import ConnectionProvider
from .connection import get_database


class NeoAdminConnectionProvider:
    """Connection provider that uses NeoAdminApi's database connection."""
    
    async def get_connection(self, context: Optional[str] = None):
        """
        Get database connection using NeoAdminApi's get_database function.
        
        Args:
            context: Optional context (ignored for admin database)
            
        Returns:
            Database connection from NeoAdminApi
        """
        return get_database()
    
    async def health_check(self) -> bool:
        """Check if connection is healthy."""
        try:
            db = get_database()
            await db.fetchval("SELECT 1")
            return True
        except Exception:
            return False


# Global instance to be used by repositories
neo_admin_connection_provider = NeoAdminConnectionProvider()