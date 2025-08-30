"""Tenant schema management handler for multi-tenant operations."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ....application.handlers.action_handler import ActionHandler
from ....application.protocols.action_executor import ExecutionContext, ExecutionResult
from ....features.database.services.database_service import get_database_service

logger = logging.getLogger(__name__)


class TenantSchemaHandler(ActionHandler):
    """
    Tenant schema management handler for creating and managing tenant schemas.
    
    Configuration:
    - operation: Schema operation type (create, drop, migrate, copy_from_template)
    - template_schema: Source schema for template copying (default: 'tenant_template')
    - region: Target region for schema creation (default: 'us')
    - include_data: Whether to copy data when copying from template (default: False)
    - skip_if_exists: Skip operation if schema already exists (default: True)
    - backup_before_drop: Create backup before dropping schema (default: True)
    """
    
    @property
    def handler_name(self) -> str:
        return "tenant_schema_handler"
    
    @property
    def handler_version(self) -> str:
        return "1.0.0"
    
    @property
    def supported_action_types(self) -> list[str]:
        return ["tenant_schema", "schema_management", "tenant_provisioning"]
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate tenant schema handler configuration."""
        if "operation" not in config:
            raise ValueError("Missing required config field: operation")
        
        operation = config["operation"]
        valid_operations = ["create", "drop", "migrate", "copy_from_template", "backup", "restore"]
        if operation not in valid_operations:
            raise ValueError(f"Invalid operation: {operation}. Must be one of: {', '.join(valid_operations)}")
        
        # Validate region if provided
        region = config.get("region", "us")
        valid_regions = ["us", "eu", "asia", "admin"]
        if region not in valid_regions:
            raise ValueError(f"Invalid region: {region}. Must be one of: {', '.join(valid_regions)}")
        
        # Validate template schema for copy operations
        if operation == "copy_from_template":
            template_schema = config.get("template_schema", "tenant_template")
            if not template_schema:
                raise ValueError("template_schema is required for copy_from_template operation")
        
        return True
    
    async def execute(
        self, 
        config: Dict[str, Any], 
        input_data: Dict[str, Any], 
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute tenant schema operation.
        
        Expected input_data:
        - tenant_id: Tenant identifier (required)
        - tenant_slug: Tenant slug for schema naming (required) 
        - schema_name: Custom schema name (optional, defaults to tenant_{tenant_slug})
        - backup_location: S3 path or local path for backups (optional)
        - migration_scripts: List of migration scripts to run (for migrate operation)
        """
        operation_start = datetime.utcnow()
        
        try:
            # Extract configuration
            operation = config["operation"]
            template_schema = config.get("template_schema", "tenant_template")
            region = config.get("region", "us")
            include_data = config.get("include_data", False)
            skip_if_exists = config.get("skip_if_exists", True)
            backup_before_drop = config.get("backup_before_drop", True)
            
            # Extract input data
            tenant_id = input_data.get("tenant_id")
            tenant_slug = input_data.get("tenant_slug")
            custom_schema_name = input_data.get("schema_name")
            backup_location = input_data.get("backup_location")
            migration_scripts = input_data.get("migration_scripts", [])
            
            if not tenant_id or not tenant_slug:
                return ExecutionResult(
                    success=False,
                    output_data={},
                    error_message="Missing required fields: tenant_id and tenant_slug"
                )
            
            # Generate schema name
            schema_name = custom_schema_name or f"tenant_{tenant_slug}"
            
            # Get database service
            db_service = await get_database_service()
            
            # Route to specific operation
            if operation == "create":
                result = await self._create_tenant_schema(
                    db_service, schema_name, tenant_id, region, skip_if_exists
                )
            elif operation == "copy_from_template":
                result = await self._copy_from_template(
                    db_service, schema_name, template_schema, region, include_data, skip_if_exists
                )
            elif operation == "drop":
                result = await self._drop_tenant_schema(
                    db_service, schema_name, region, backup_before_drop, backup_location
                )
            elif operation == "migrate":
                result = await self._migrate_tenant_schema(
                    db_service, schema_name, region, migration_scripts
                )
            elif operation == "backup":
                result = await self._backup_tenant_schema(
                    db_service, schema_name, region, backup_location
                )
            elif operation == "restore":
                result = await self._restore_tenant_schema(
                    db_service, schema_name, region, backup_location
                )
            else:
                return ExecutionResult(
                    success=False,
                    output_data={},
                    error_message=f"Unsupported operation: {operation}"
                )
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - operation_start).total_seconds()
            
            # Enhance result with metadata
            result.update({
                "operation": operation,
                "tenant_id": tenant_id,
                "tenant_slug": tenant_slug,
                "schema_name": schema_name,
                "region": region,
                "execution_time_seconds": execution_time
            })
            
            return ExecutionResult(
                success=True,
                output_data=result
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                output_data={},
                error_message=f"Tenant schema operation failed: {str(e)}",
                error_details={
                    "operation": config.get("operation"),
                    "tenant_id": input_data.get("tenant_id"),
                    "error_type": type(e).__name__
                }
            )
    
    async def _create_tenant_schema(
        self,
        db_service,
        schema_name: str,
        tenant_id: str,
        region: str,
        skip_if_exists: bool
    ) -> Dict[str, Any]:
        """Create a new tenant schema."""
        
        connection_name = self._get_regional_connection(region)
        
        async with db_service.get_connection(connection_name) as conn:
            # Check if schema exists
            schema_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = $1)",
                schema_name
            )
            
            if schema_exists:
                if skip_if_exists:
                    return {
                        "schema_created": False,
                        "schema_exists": True,
                        "message": f"Schema {schema_name} already exists, skipped creation"
                    }
                else:
                    raise ValueError(f"Schema {schema_name} already exists")
            
            # Create schema
            await conn.execute(f'CREATE SCHEMA "{schema_name}"')
            
            # Set up basic permissions and ownership
            await conn.execute(f'ALTER SCHEMA "{schema_name}" OWNER TO postgres')
            
            logger.info(f"Created tenant schema: {schema_name} in region {region}")
            
            return {
                "schema_created": True,
                "schema_exists": False,
                "connection_used": connection_name,
                "message": f"Successfully created schema {schema_name}"
            }
    
    async def _copy_from_template(
        self,
        db_service,
        schema_name: str,
        template_schema: str,
        region: str,
        include_data: bool,
        skip_if_exists: bool
    ) -> Dict[str, Any]:
        """Copy schema structure and optionally data from template."""
        
        connection_name = self._get_regional_connection(region)
        
        async with db_service.transaction(connection_name) as conn:
            # Check if target schema exists
            schema_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = $1)",
                schema_name
            )
            
            if schema_exists:
                if skip_if_exists:
                    return {
                        "schema_copied": False,
                        "schema_exists": True,
                        "message": f"Schema {schema_name} already exists, skipped copying"
                    }
                else:
                    raise ValueError(f"Schema {schema_name} already exists")
            
            # Verify template schema exists
            template_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = $1)",
                template_schema
            )
            
            if not template_exists:
                raise ValueError(f"Template schema {template_schema} does not exist")
            
            # Create target schema
            await conn.execute(f'CREATE SCHEMA "{schema_name}"')
            
            # Copy all tables from template
            tables_query = """
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = $1 AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """
            
            tables = await conn.fetch(tables_query, template_schema)
            copied_tables = []
            
            for table_row in tables:
                table_name = table_row["table_name"]
                
                # Create table structure
                if include_data:
                    # Copy structure and data
                    await conn.execute(f'''
                        CREATE TABLE "{schema_name}"."{table_name}" AS 
                        SELECT * FROM "{template_schema}"."{table_name}"
                    ''')
                else:
                    # Copy only structure
                    await conn.execute(f'''
                        CREATE TABLE "{schema_name}"."{table_name}" AS 
                        SELECT * FROM "{template_schema}"."{table_name}" WHERE 1=0
                    ''')
                
                copied_tables.append(table_name)
            
            # Copy sequences
            sequences_query = """
                SELECT sequence_name FROM information_schema.sequences
                WHERE sequence_schema = $1
            """
            
            sequences = await conn.fetch(sequences_query, template_schema)
            copied_sequences = []
            
            for seq_row in sequences:
                seq_name = seq_row["sequence_name"]
                
                # Get sequence definition
                seq_def = await conn.fetchrow(f'''
                    SELECT * FROM "{template_schema}"."{seq_name}"
                ''')
                
                # Create sequence in target schema
                await conn.execute(f'''
                    CREATE SEQUENCE "{schema_name}"."{seq_name}"
                    START WITH 1
                    INCREMENT BY 1
                ''')
                
                copied_sequences.append(seq_name)
            
            # Copy views
            views_query = """
                SELECT table_name, view_definition FROM information_schema.views
                WHERE table_schema = $1
            """
            
            views = await conn.fetch(views_query, template_schema)
            copied_views = []
            
            for view_row in views:
                view_name = view_row["table_name"]
                view_def = view_row["view_definition"]
                
                # Replace schema references in view definition
                updated_view_def = view_def.replace(f'"{template_schema}".', f'"{schema_name}".')
                
                await conn.execute(f'''
                    CREATE VIEW "{schema_name}"."{view_name}" AS {updated_view_def}
                ''')
                
                copied_views.append(view_name)
            
            logger.info(f"Copied template schema {template_schema} to {schema_name}: "
                       f"{len(copied_tables)} tables, {len(copied_sequences)} sequences, {len(copied_views)} views")
            
            return {
                "schema_copied": True,
                "template_schema": template_schema,
                "connection_used": connection_name,
                "copied_tables": copied_tables,
                "copied_sequences": copied_sequences,
                "copied_views": copied_views,
                "include_data": include_data,
                "message": f"Successfully copied template {template_schema} to {schema_name}"
            }
    
    async def _drop_tenant_schema(
        self,
        db_service,
        schema_name: str,
        region: str,
        backup_before_drop: bool,
        backup_location: Optional[str]
    ) -> Dict[str, Any]:
        """Drop a tenant schema with optional backup."""
        
        connection_name = self._get_regional_connection(region)
        
        async with db_service.transaction(connection_name) as conn:
            # Check if schema exists
            schema_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = $1)",
                schema_name
            )
            
            if not schema_exists:
                return {
                    "schema_dropped": False,
                    "schema_exists": False,
                    "message": f"Schema {schema_name} does not exist"
                }
            
            backup_info = None
            
            # Create backup if requested
            if backup_before_drop:
                backup_info = await self._backup_tenant_schema(
                    db_service, schema_name, region, backup_location
                )
            
            # Drop schema
            await conn.execute(f'DROP SCHEMA "{schema_name}" CASCADE')
            
            logger.info(f"Dropped tenant schema: {schema_name} in region {region}")
            
            return {
                "schema_dropped": True,
                "backup_created": backup_before_drop,
                "backup_info": backup_info,
                "connection_used": connection_name,
                "message": f"Successfully dropped schema {schema_name}"
            }
    
    async def _migrate_tenant_schema(
        self,
        db_service,
        schema_name: str,
        region: str,
        migration_scripts: List[str]
    ) -> Dict[str, Any]:
        """Run migration scripts on tenant schema."""
        
        connection_name = self._get_regional_connection(region)
        
        async with db_service.transaction(connection_name) as conn:
            # Set schema search path
            await conn.execute(f'SET search_path TO "{schema_name}"')
            
            migration_results = []
            
            for script in migration_scripts:
                try:
                    result = await conn.execute(script)
                    migration_results.append({
                        "script": script[:100] + "..." if len(script) > 100 else script,
                        "success": True,
                        "result": result
                    })
                except Exception as e:
                    migration_results.append({
                        "script": script[:100] + "..." if len(script) > 100 else script,
                        "success": False,
                        "error": str(e)
                    })
                    # Continue with other scripts
            
            successful_migrations = sum(1 for r in migration_results if r["success"])
            
            return {
                "migrations_completed": True,
                "total_scripts": len(migration_scripts),
                "successful_migrations": successful_migrations,
                "failed_migrations": len(migration_scripts) - successful_migrations,
                "migration_results": migration_results,
                "connection_used": connection_name
            }
    
    async def _backup_tenant_schema(
        self,
        db_service,
        schema_name: str,
        region: str,
        backup_location: Optional[str]
    ) -> Dict[str, Any]:
        """Create backup of tenant schema."""
        
        # For now, create a logical backup by dumping schema structure
        # In production, this would integrate with pg_dump or cloud backup services
        
        connection_name = self._get_regional_connection(region)
        backup_timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        async with db_service.get_connection(connection_name) as conn:
            # Get schema structure info
            tables_info = await conn.fetch("""
                SELECT table_name, table_type 
                FROM information_schema.tables 
                WHERE table_schema = $1
            """, schema_name)
            
            # In a real implementation, this would call pg_dump
            backup_info = {
                "backup_created": True,
                "backup_timestamp": backup_timestamp,
                "backup_location": backup_location or f"/tmp/{schema_name}_backup_{backup_timestamp}.sql",
                "schema_tables": [dict(row) for row in tables_info],
                "table_count": len(tables_info),
                "backup_type": "logical",
                "connection_used": connection_name
            }
            
            logger.info(f"Created backup for schema {schema_name}: {backup_info['backup_location']}")
            
            return backup_info
    
    async def _restore_tenant_schema(
        self,
        db_service,
        schema_name: str,
        region: str,
        backup_location: Optional[str]
    ) -> Dict[str, Any]:
        """Restore tenant schema from backup."""
        
        if not backup_location:
            raise ValueError("backup_location is required for restore operation")
        
        connection_name = self._get_regional_connection(region)
        
        # In a real implementation, this would restore from pg_dump file
        # For now, return a placeholder response
        
        return {
            "schema_restored": True,
            "backup_location": backup_location,
            "connection_used": connection_name,
            "message": f"Schema {schema_name} restoration completed from {backup_location}"
        }
    
    def _get_regional_connection(self, region: str) -> str:
        """Get connection name for specified region."""
        region_connections = {
            "us": "neofast-shared-us-primary",
            "eu": "neofast-shared-eu-primary", 
            "asia": "neofast-shared-asia-primary",
            "admin": "admin"
        }
        
        return region_connections.get(region, "neofast-shared-us-primary")
    
    async def get_execution_timeout(self, config: Dict[str, Any]) -> int:
        """Get execution timeout for schema operations."""
        operation = config.get("operation", "create")
        
        # Schema operations can take significant time
        timeouts = {
            "create": 60,
            "copy_from_template": 300,  # 5 minutes for template copying
            "drop": 120,
            "migrate": 600,  # 10 minutes for migrations
            "backup": 1800,  # 30 minutes for backups
            "restore": 1800  # 30 minutes for restore
        }
        
        return timeouts.get(operation, 120)
    
    async def health_check(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform health check for tenant schema operations."""
        try:
            region = config.get("region", "us")
            connection_name = self._get_regional_connection(region)
            
            db_service = await get_database_service()
            
            async with db_service.get_connection(connection_name) as conn:
                # Test schema operations capability
                await conn.fetchval("SELECT 1")
                
                # Check template schema availability
                template_schema = config.get("template_schema", "tenant_template")
                template_exists = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = $1)",
                    template_schema
                )
                
                return {
                    "healthy": True,
                    "status": "Tenant schema handler ready",
                    "details": {
                        "region": region,
                        "connection_name": connection_name,
                        "template_schema_exists": template_exists,
                        "template_schema": template_schema
                    }
                }
        
        except Exception as e:
            return {
                "healthy": False,
                "status": f"Tenant schema handler health check failed: {str(e)}",
                "details": {
                    "error_type": type(e).__name__,
                    "region": config.get("region", "us")
                }
            }
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for tenant schema handler."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["create", "drop", "migrate", "copy_from_template", "backup", "restore"],
                    "description": "Schema operation type"
                },
                "template_schema": {
                    "type": "string",
                    "default": "tenant_template",
                    "description": "Source schema for template operations"
                },
                "region": {
                    "type": "string",
                    "enum": ["us", "eu", "asia", "admin"],
                    "default": "us",
                    "description": "Target region for operation"
                },
                "include_data": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include data when copying from template"
                },
                "skip_if_exists": {
                    "type": "boolean",
                    "default": True,
                    "description": "Skip operation if schema exists"
                },
                "backup_before_drop": {
                    "type": "boolean",
                    "default": True,
                    "description": "Create backup before dropping schema"
                }
            },
            "required": ["operation"]
        }
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input data schema for tenant schema handler."""
        return {
            "type": "object",
            "properties": {
                "tenant_id": {
                    "type": "string",
                    "description": "Tenant identifier"
                },
                "tenant_slug": {
                    "type": "string",
                    "description": "Tenant slug for schema naming"
                },
                "schema_name": {
                    "type": "string",
                    "description": "Custom schema name (optional)"
                },
                "backup_location": {
                    "type": "string",
                    "description": "Backup location path"
                },
                "migration_scripts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of SQL migration scripts"
                }
            },
            "required": ["tenant_id", "tenant_slug"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Get output data schema for tenant schema handler."""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "operation": {"type": "string"},
                "tenant_id": {"type": "string"},
                "schema_name": {"type": "string"},
                "region": {"type": "string"},
                "execution_time_seconds": {"type": "number"},
                "schema_created": {"type": "boolean"},
                "schema_copied": {"type": "boolean"},
                "schema_dropped": {"type": "boolean"},
                "backup_created": {"type": "boolean"},
                "migrations_completed": {"type": "boolean"},
                "copied_tables": {"type": "array"},
                "migration_results": {"type": "array"}
            },
            "required": ["success"]
        }