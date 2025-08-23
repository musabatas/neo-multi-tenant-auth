"""
Simple PermissionRepository wrapper using neo-commons base implementation.
"""
from neo_commons.auth.repositories import BasePermissionRepository
from src.common.database.connection_provider import neo_admin_connection_provider


class PermissionRepository(BasePermissionRepository):
    """
    NeoAdminApi PermissionRepository using neo-commons base implementation.
    
    Inherits all functionality from BasePermissionRepository with NeoAdminApi configuration.
    """
    
    def __init__(self):
        """Initialize with NeoAdminApi database configuration."""
        super().__init__(
            connection_provider=neo_admin_connection_provider,
            schema_name="admin"
        )