"""
Simple permission sync manager for NeoAdminApi.

Uses neo-commons PermissionSyncManager with NeoAdminApi-specific configuration.
"""
from typing import Dict, Any

from neo_commons.auth.manager import PermissionSyncManager
from neo_commons.repositories.base import DefaultSchemaProvider
from src.common.database.connection import get_database

class NeoAdminPermissionSyncManager:
    """Simple wrapper around neo-commons PermissionSyncManager."""
    
    def __init__(self):
        """Initialize with NeoAdminApi configuration."""
        self.manager = PermissionSyncManager(
            connection_provider=get_database(),
            schema_provider=DefaultSchemaProvider(admin_schema="admin")
        )
    
    async def sync_permissions(
        self,
        app,
        dry_run: bool = False,
        force_update: bool = False
    ) -> Dict[str, Any]:
        """Sync permissions using neo-commons manager."""
        return await self.manager.sync_permissions(
            app=app,
            dry_run=dry_run,
            force_update=force_update
        )