"""Schema resolution implementation for neo-commons."""

import re
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from ..entities.database_protocols import SchemaResolver, ConnectionManager
from ....core.exceptions.database import (
    SchemaNotFoundError,
    InvalidSchemaError,
    SchemaResolutionError,
)
from ....config.constants import DatabaseSchemas
from ...tenants.services.tenant_cache import TenantCache

logger = logging.getLogger(__name__)


@dataclass
class SchemaInfo:
    """Information about a resolved schema."""
    schema_name: str
    schema_type: str  # 'admin', 'tenant', 'platform_common'
    tenant_id: Optional[str] = None
    tenant_slug: Optional[str] = None
    connection_name: str = "default"
    is_cached: bool = False


class DatabaseSchemaResolver(SchemaResolver):
    """Implementation of SchemaResolver for database schema resolution."""
    
    # Schema name validation patterns
    VALID_SCHEMA_PATTERN = re.compile(r'^[a-z][a-z0-9_]*$')
    TENANT_SCHEMA_PATTERN = re.compile(r'^tenant_[a-z0-9][a-z0-9_-]*[a-z0-9]$')
    
    # Security whitelist of allowed schema prefixes
    ALLOWED_SCHEMA_PREFIXES = {
        'admin',
        'tenant_',
        'platform_common',
    }
    
    def __init__(self, 
                 connection_manager: ConnectionManager,
                 cache: Optional[TenantCache] = None,
                 admin_connection_name: str = "admin-primary"):
        self._connection_manager = connection_manager
        self._cache = cache
        self._admin_connection_name = admin_connection_name
        
        # Default schema mappings
        self._default_schemas = {
            'admin': DatabaseSchemas.ADMIN,
            'platform_common': DatabaseSchemas.PLATFORM_COMMON,
        }
    
    async def resolve_schema(self, 
                           tenant_id: Optional[str] = None,
                           context_type: str = "admin") -> str:
        """Resolve the correct schema name based on context."""
        try:
            if context_type == "admin":
                return await self.get_admin_schema()
            elif context_type == "platform_common":
                return await self.get_platform_schema()
            elif context_type == "tenant" and tenant_id:
                return await self.get_tenant_schema(tenant_id)
            else:
                raise SchemaResolutionError(
                    f"Cannot resolve schema for context_type='{context_type}', "
                    f"tenant_id='{tenant_id}'"
                )
        except Exception as e:
            logger.error(f"Schema resolution failed: {e}")
            raise SchemaResolutionError(f"Schema resolution failed: {e}")
    
    async def get_tenant_schema(self, tenant_id: str) -> str:
        """Get the specific schema name for a tenant."""
        if not tenant_id:
            raise ValueError("tenant_id cannot be empty")
        
        # Check cache first
        if self._cache:
            cached_schema = await self._cache.get_tenant_schema(tenant_id)
            if cached_schema:
                logger.debug(f"Schema for tenant {tenant_id} found in cache: {cached_schema}")
                return cached_schema
        
        # Query database for tenant schema
        try:
            query = """
                SELECT schema_name, slug, name
                FROM admin.tenants 
                WHERE id = $1 AND status = 'active' AND deleted_at IS NULL
            """
            
            result = await self._connection_manager.execute_fetchrow(
                self._admin_connection_name, 
                query, 
                tenant_id
            )
            
            if not result:
                raise SchemaNotFoundError(f"Active tenant with ID '{tenant_id}' not found")
            
            schema_name = result['schema_name']
            
            # Validate the schema name
            if not await self.validate_schema_name(schema_name):
                raise InvalidSchemaError(
                    schema_name, 
                    "Schema name failed security validation"
                )
            
            # Cache the result
            if self._cache:
                await self._cache.set_tenant_schema(tenant_id, schema_name)
            
            logger.info(f"Resolved schema for tenant {tenant_id}: {schema_name}")
            return schema_name
            
        except Exception as e:
            if isinstance(e, (SchemaNotFoundError, InvalidSchemaError)):
                raise
            logger.error(f"Database error resolving tenant schema for {tenant_id}: {e}")
            raise SchemaResolutionError(f"Failed to resolve tenant schema: {e}")
    
    async def validate_schema_name(self, schema_name: str) -> bool:
        """Validate that a schema name is safe to use."""
        if not schema_name:
            return False
        
        # Check basic pattern
        if not self.VALID_SCHEMA_PATTERN.match(schema_name):
            logger.warning(f"Schema name '{schema_name}' failed pattern validation")
            return False
        
        # Check against allowed prefixes
        allowed = any(
            schema_name.startswith(prefix) for prefix in self.ALLOWED_SCHEMA_PREFIXES
        )
        
        if not allowed:
            logger.warning(f"Schema name '{schema_name}' not in allowed prefixes")
            return False
        
        # Additional validation for tenant schemas
        if schema_name.startswith('tenant_'):
            if not self.TENANT_SCHEMA_PATTERN.match(schema_name):
                logger.warning(f"Tenant schema name '{schema_name}' failed tenant pattern validation")
                return False
        
        # Check length limits
        if len(schema_name) > 63:  # PostgreSQL limit
            logger.warning(f"Schema name '{schema_name}' exceeds length limit")
            return False
        
        return True
    
    async def get_admin_schema(self) -> str:
        """Get the admin schema name."""
        return self._default_schemas['admin']
    
    async def get_platform_schema(self) -> str:
        """Get the platform common schema name."""
        return self._default_schemas['platform_common']
    
    async def get_schema_info(self, 
                             tenant_id: Optional[str] = None,
                             context_type: str = "admin") -> SchemaInfo:
        """Get detailed information about a resolved schema."""
        schema_name = await self.resolve_schema(tenant_id, context_type)
        
        if context_type == "admin":
            return SchemaInfo(
                schema_name=schema_name,
                schema_type="admin",
                connection_name=self._admin_connection_name
            )
        elif context_type == "platform_common":
            return SchemaInfo(
                schema_name=schema_name,
                schema_type="platform_common",
                connection_name=self._admin_connection_name
            )
        elif context_type == "tenant" and tenant_id:
            # Get additional tenant info if needed
            tenant_info = await self._get_tenant_info(tenant_id)
            
            return SchemaInfo(
                schema_name=schema_name,
                schema_type="tenant",
                tenant_id=tenant_id,
                tenant_slug=tenant_info.get('slug'),
                connection_name=tenant_info.get('connection_name', 'shared-primary'),
                is_cached=self._cache is not None
            )
        else:
            raise SchemaResolutionError(f"Cannot get schema info for context: {context_type}")
    
    async def _get_tenant_info(self, tenant_id: str) -> Dict[str, Any]:
        """Get additional tenant information."""
        try:
            query = """
                SELECT 
                    t.slug,
                    t.name,
                    dc.connection_name
                FROM admin.tenants t
                LEFT JOIN admin.database_connections dc ON t.database_connection_id = dc.id
                WHERE t.id = $1 AND t.status = 'active' AND t.deleted_at IS NULL
            """
            
            result = await self._connection_manager.execute_fetchrow(
                self._admin_connection_name, 
                query, 
                tenant_id
            )
            
            return dict(result) if result else {}
            
        except Exception as e:
            logger.warning(f"Failed to get tenant info for {tenant_id}: {e}")
            return {}
    
    async def list_tenant_schemas(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all active tenant schemas."""
        try:
            query = """
                SELECT 
                    id as tenant_id,
                    slug,
                    name,
                    schema_name,
                    status,
                    created_at
                FROM admin.tenants
                WHERE status = 'active' AND deleted_at IS NULL
                ORDER BY created_at DESC
                LIMIT $1
            """
            
            results = await self._connection_manager.execute_query(
                self._admin_connection_name, 
                query, 
                limit
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to list tenant schemas: {e}")
            return []
    
    async def schema_exists(self, schema_name: str, connection_name: Optional[str] = None) -> bool:
        """Check if a schema exists in the database."""
        if not await self.validate_schema_name(schema_name):
            return False
        
        conn_name = connection_name or self._admin_connection_name
        
        try:
            query = """
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.schemata 
                    WHERE schema_name = $1
                )
            """
            
            result = await self._connection_manager.execute_fetchval(
                conn_name,
                query,
                schema_name
            )
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error checking schema existence for '{schema_name}': {e}")
            return False
    
    async def invalidate_tenant_cache(self, tenant_id: str) -> None:
        """Invalidate cached tenant schema information."""
        if self._cache:
            await self._cache.invalidate_tenant_schema(tenant_id)
            logger.info(f"Invalidated cache for tenant {tenant_id}")
    
    async def get_schema_for_query(self, query: str, schema_name: str) -> str:
        """Prepare a query with the correct schema name."""
        # Validate schema name before use
        if not await self.validate_schema_name(schema_name):
            raise InvalidSchemaError(schema_name, "Failed validation for query preparation")
        
        # Replace {schema_name} placeholder in query
        if '{schema_name}' in query:
            return query.format(schema_name=schema_name)
        
        return query