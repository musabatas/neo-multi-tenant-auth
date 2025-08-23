"""
Permission synchronization manager.

Enhanced with neo-commons protocol-based dependency injection for:
- Dynamic schema configuration via SchemaProvider protocol
- Database connection management via ConnectionProvider protocol
- Configurable permission registries
- Audit logging capabilities
"""
import json
from typing import Dict, Any, List, Optional, Set, Protocol, runtime_checkable
from loguru import logger
from datetime import datetime

from ..repositories.protocols import SchemaProvider, ConnectionProvider
from ..repositories.base import DefaultSchemaProvider
from ..utils.datetime import utc_now
from .utils.scanner import EndpointPermissionScanner
from .permissions.registry import PLATFORM_PERMISSIONS, TENANT_PERMISSIONS


@runtime_checkable
class PermissionRegistryProvider(Protocol):
    """Protocol for providing permission registries."""
    
    def get_platform_permissions(self) -> List[Dict[str, Any]]:
        """Get platform-level permissions."""
        ...
    
    def get_tenant_permissions(self) -> List[Dict[str, Any]]:
        """Get tenant-level permissions."""
        ...


class DefaultPermissionRegistryProvider:
    """Default permission registry provider using static definitions."""
    
    def get_platform_permissions(self) -> List[Dict[str, Any]]:
        """Get platform-level permissions."""
        return PLATFORM_PERMISSIONS
    
    def get_tenant_permissions(self) -> List[Dict[str, Any]]:
        """Get tenant-level permissions."""
        return TENANT_PERMISSIONS


class PermissionSyncManager:
    """
    Protocol-based permission synchronization manager.
    
    Features:
    - Dynamic schema configuration via SchemaProvider protocol
    - Database operations via ConnectionProvider protocol
    - Configurable permission registries
    - Discovers permissions from endpoints
    - Syncs with database on startup with safe updates
    - Maintains comprehensive audit trail
    """
    
    def __init__(
        self,
        connection_provider: ConnectionProvider,
        schema_provider: Optional[SchemaProvider] = None,
        permission_registry: Optional[PermissionRegistryProvider] = None
    ):
        """
        Initialize permission sync manager with protocol-based dependencies.
        
        Args:
            connection_provider: Database connection provider
            schema_provider: Schema provider for dynamic configuration
            permission_registry: Permission registry provider
        """
        self.db = connection_provider
        self.schema_provider = schema_provider or DefaultSchemaProvider()
        self.permission_registry = permission_registry or DefaultPermissionRegistryProvider()
        self.scanner: Optional[EndpointPermissionScanner] = None
        self.sync_stats = {
            'added': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
    
    async def sync_permissions(
        self,
        app,
        dry_run: bool = False,
        force_update: bool = False
    ) -> Dict[str, Any]:
        """
        Synchronize permissions from code to database.
        
        Args:
            app: FastAPI application instance
            dry_run: If True, preview changes without applying
            force_update: If True, update existing permissions
            
        Returns:
            Sync results with statistics
        """
        logger.info("Starting permission synchronization...")
        
        # Reset statistics
        self.sync_stats = {
            'added': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        try:
            # Step 1: Discover permissions from endpoints
            self.scanner = EndpointPermissionScanner(app)
            discovered_permissions = self.scanner.scan()
            
            # Step 2: Add static permissions from registry
            static_permissions = self._get_static_permissions()
            
            # Merge discovered and static permissions
            all_permissions = {**static_permissions, **discovered_permissions}
            
            # Step 3: Get existing permissions from database
            existing_permissions = await self._get_existing_permissions()
            
            # Step 4: Sync each permission
            sync_results = []
            for code, permission_def in all_permissions.items():
                result = await self._sync_permission(
                    permission_def,
                    existing_permissions.get(code),
                    dry_run=dry_run,
                    force_update=force_update
                )
                sync_results.append(result)
            
            # Step 5: Generate report
            report = self._generate_sync_report(sync_results, dry_run)
            
            if not dry_run:
                logger.info(f"Permission sync completed: {self.sync_stats}")
                
                # Log to audit table if available
                await self._log_sync_audit(self.sync_stats)
            else:
                logger.info("Permission sync dry run completed (no changes applied)")
            
            return {
                'success': True,
                'stats': self.sync_stats,
                'results': sync_results,
                'report': report
            }
            
        except Exception as e:
            logger.error(f"Permission sync failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'stats': self.sync_stats
            }
    
    def _get_static_permissions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get static permissions from registry provider.
        
        Returns:
            Dictionary of permission definitions
        """
        permissions = {}
        
        # Add platform permissions from registry
        for perm in self.permission_registry.get_platform_permissions():
            # Convert PermissionDefinition to dict if needed
            perm_dict = perm.to_dict() if hasattr(perm, 'to_dict') else perm
            permissions[perm_dict['code']] = {
                **perm_dict,
                'scope_level': 'platform',
                'endpoints': []  # Static permissions may not have endpoints
            }
        
        # Add tenant permissions from registry
        for perm in self.permission_registry.get_tenant_permissions():
            # Convert PermissionDefinition to dict if needed
            perm_dict = perm.to_dict() if hasattr(perm, 'to_dict') else perm
            permissions[perm_dict['code']] = {
                **perm_dict,
                'scope_level': 'tenant',
                'endpoints': []
            }
        
        return permissions
    
    async def _get_existing_permissions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get existing permissions from database.
        
        Returns:
            Dictionary of code -> permission record
        """
        admin_schema = self.schema_provider.get_admin_schema()
        
        query = f"""
            SELECT 
                id,
                code,
                description,
                resource,
                action,
                scope_level,
                is_dangerous,
                requires_mfa,
                requires_approval,
                permissions_config,
                created_at,
                updated_at,
                deleted_at
            FROM {admin_schema}.platform_permissions
            WHERE deleted_at IS NULL
        """
        
        # Use connection provider for database operations
        if hasattr(self.db, 'fetch'):
            # Direct database manager
            results = await self.db.fetch(query)
        else:
            # Connection provider protocol
            async with self.db.get_connection() as conn:
                results = await conn.fetch(query)
        
        permissions = {}
        for row in results:
            permissions[row['code']] = dict(row)
        
        return permissions
    
    async def _sync_permission(
        self,
        permission_def: Dict[str, Any],
        existing: Optional[Dict[str, Any]],
        dry_run: bool,
        force_update: bool
    ) -> Dict[str, Any]:
        """
        Sync a single permission.
        
        Args:
            permission_def: Permission definition from code
            existing: Existing database record (if any)
            dry_run: Preview mode
            force_update: Force update existing
            
        Returns:
            Sync result for this permission
        """
        code = permission_def['code']
        
        # Prepare result
        result = {
            'code': code,
            'action': None,
            'status': 'pending',
            'details': {}
        }
        
        try:
            if not existing:
                # Permission doesn't exist - create it
                result['action'] = 'create'
                if not dry_run:
                    await self._create_permission(permission_def)
                    self.sync_stats['added'] += 1
                    result['status'] = 'success'
                else:
                    result['status'] = 'dry_run'
                    
            elif force_update or self._should_update(permission_def, existing):
                # Permission exists and needs update
                result['action'] = 'update'
                result['details']['changes'] = self._get_changes(permission_def, existing)
                
                if not dry_run:
                    await self._update_permission(permission_def, existing['id'])
                    self.sync_stats['updated'] += 1
                    result['status'] = 'success'
                else:
                    result['status'] = 'dry_run'
            else:
                # Permission exists and is up to date
                result['action'] = 'skip'
                result['status'] = 'skipped'
                self.sync_stats['skipped'] += 1
                
        except Exception as e:
            result['status'] = 'error'
            result['details']['error'] = str(e)
            self.sync_stats['errors'] += 1
            logger.error(f"Failed to sync permission {code}: {e}")
        
        return result
    
    def _should_update(self, new_def: Dict[str, Any], existing: Dict[str, Any]) -> bool:
        """
        Check if permission needs updating.
        
        Args:
            new_def: New permission definition
            existing: Existing database record
            
        Returns:
            True if update needed
        """
        # Check if key fields differ
        fields_to_check = [
            'description',
            'resource',
            'action',
            'scope_level',
            'is_dangerous',
            'requires_mfa',
            'requires_approval'
        ]
        
        for field in fields_to_check:
            if new_def.get(field) != existing.get(field):
                return True
        
        return False
    
    def _get_changes(self, new_def: Dict[str, Any], existing: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get changes between new and existing permission.
        
        Args:
            new_def: New permission definition
            existing: Existing database record
            
        Returns:
            Dictionary of changes
        """
        changes = {}
        
        fields_to_check = [
            'description',
            'resource',
            'action',
            'scope_level',
            'is_dangerous',
            'requires_mfa',
            'requires_approval'
        ]
        
        for field in fields_to_check:
            old_val = existing.get(field)
            new_val = new_def.get(field)
            if old_val != new_val:
                changes[field] = {
                    'old': old_val,
                    'new': new_val
                }
        
        return changes
    
    async def _create_permission(self, permission_def: Dict[str, Any]):
        """
        Create a new permission in database.
        
        Args:
            permission_def: Permission definition
        """
        admin_schema = self.schema_provider.get_admin_schema()
        
        query = f"""
            INSERT INTO {admin_schema}.platform_permissions (
                code,
                description,
                resource,
                action,
                scope_level,
                is_dangerous,
                requires_mfa,
                requires_approval,
                permissions_config,
                created_at,
                updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
            )
        """
        
        # Prepare config with endpoint information
        config = {
            'endpoints': permission_def.get('endpoints', []),
            'auto_discovered': len(permission_def.get('endpoints', [])) > 0
        }
        
        now = utc_now()
        
        # Use connection provider for database operations
        if hasattr(self.db, 'execute'):
            # Direct database manager
            await self.db.execute(
                query,
                permission_def['code'],
                permission_def['description'],
                permission_def['resource'],
                permission_def['action'],
                permission_def['scope_level'],
                permission_def.get('is_dangerous', False),
                permission_def.get('requires_mfa', False),
                permission_def.get('requires_approval', False),
                json.dumps(config),
                now,
                now
            )
        else:
            # Connection provider protocol
            async with self.db.get_connection() as conn:
                await conn.execute(
                    query,
                    permission_def['code'],
                    permission_def['description'],
                    permission_def['resource'],
                    permission_def['action'],
                    permission_def['scope_level'],
                    permission_def.get('is_dangerous', False),
                    permission_def.get('requires_mfa', False),
                    permission_def.get('requires_approval', False),
                    json.dumps(config),
                    now,
                    now
                )
        
        logger.info(f"Created permission: {permission_def['code']}")
    
    async def _update_permission(self, permission_def: Dict[str, Any], permission_id: int):
        """
        Update an existing permission.
        
        Args:
            permission_def: New permission definition
            permission_id: Database ID of permission
        """
        admin_schema = self.schema_provider.get_admin_schema()
        
        query = f"""
            UPDATE {admin_schema}.platform_permissions
            SET 
                description = $1,
                resource = $2,
                action = $3,
                scope_level = $4,
                is_dangerous = $5,
                requires_mfa = $6,
                requires_approval = $7,
                permissions_config = permissions_config || $8,
                updated_at = $9
            WHERE id = $10
        """
        
        # Prepare config update
        config_update = {
            'endpoints': permission_def.get('endpoints', []),
            'last_sync': utc_now().isoformat()
        }
        
        # Use connection provider for database operations
        if hasattr(self.db, 'execute'):
            # Direct database manager
            await self.db.execute(
                query,
                permission_def['description'],
                permission_def['resource'],
                permission_def['action'],
                permission_def['scope_level'],
                permission_def.get('is_dangerous', False),
                permission_def.get('requires_mfa', False),
                permission_def.get('requires_approval', False),
                json.dumps(config_update),
                utc_now(),
                permission_id
            )
        else:
            # Connection provider protocol
            async with self.db.get_connection() as conn:
                await conn.execute(
                    query,
                    permission_def['description'],
                    permission_def['resource'],
                    permission_def['action'],
                    permission_def['scope_level'],
                    permission_def.get('is_dangerous', False),
                    permission_def.get('requires_mfa', False),
                    permission_def.get('requires_approval', False),
                    json.dumps(config_update),
                    utc_now(),
                    permission_id
                )
        
        logger.info(f"Updated permission: {permission_def['code']}")
    
    async def _log_sync_audit(self, stats: Dict[str, int]):
        """
        Log sync operation to audit table.
        
        Args:
            stats: Sync statistics
        """
        # This would log to an audit table if available
        # For now, just log to logger
        logger.info(f"Permission sync audit: {stats}")
    
    def _generate_sync_report(self, results: List[Dict[str, Any]], dry_run: bool) -> str:
        """
        Generate a sync report.
        
        Args:
            results: List of sync results
            dry_run: Whether this was a dry run
            
        Returns:
            Formatted report
        """
        report = ["=" * 80]
        report.append(f"PERMISSION SYNC REPORT {'(DRY RUN)' if dry_run else ''}")
        report.append("=" * 80)
        
        # Statistics
        report.append(f"\nStatistics:")
        report.append(f"  Added: {self.sync_stats['added']}")
        report.append(f"  Updated: {self.sync_stats['updated']}")
        report.append(f"  Skipped: {self.sync_stats['skipped']}")
        report.append(f"  Errors: {self.sync_stats['errors']}")
        
        # Changes by action
        for action in ['create', 'update', 'error']:
            action_results = [r for r in results if r['action'] == action]
            if action_results:
                report.append(f"\n{action.upper()} Operations:")
                for result in action_results:
                    report.append(f"  - {result['code']}")
                    if result.get('details', {}).get('changes'):
                        for field, change in result['details']['changes'].items():
                            report.append(f"    {field}: {change['old']} → {change['new']}")
                    if result.get('details', {}).get('error'):
                        report.append(f"    ERROR: {result['details']['error']}")
        
        # Scanner report if available
        if self.scanner:
            report.append("\n" + self.scanner.get_endpoint_report())
        
        report.append("=" * 80)
        return '\n'.join(report)