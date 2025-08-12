#!/usr/bin/env python3
"""
Dynamic Migration Engine - Fully Programmatic Database Migration Management
Handles migrations dynamically based on database_connections table
"""

import asyncio
import asyncpg
import os
import subprocess
import json
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel

# Import encryption module
from encryption import decrypt_password, is_encrypted
# Import dependency resolver
from migration_dependency_resolver import MigrationDependencyResolver, SchemaMigration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
console = Console()


class DatabaseType(Enum):
    """Database types that determine migration sets"""
    ADMIN = "admin"
    SHARED = "shared"
    ANALYTICS = "analytics"
    TENANT = "tenant"


class MigrationSet(Enum):
    """Migration sets for different database types"""
    ADMIN = "admin"  # V002-V008 admin schema migrations
    PLATFORM_COMMON = "platform_common"  # V001 platform_common only
    REGIONAL_SHARED = "regional_shared"  # V101 tenant_template
    REGIONAL_ANALYTICS = "regional_analytics"  # V101 analytics


@dataclass
class MigrationConfig:
    """Migration configuration for a specific database/schema combination"""
    database_id: str
    database_name: str
    host: str
    port: int
    username: str
    password: str
    region: str
    database_type: DatabaseType
    schemas_to_migrate: List[str]
    migration_sets: List[MigrationSet]
    placeholders: Dict[str, str] = field(default_factory=dict)


@dataclass
class MigrationPlan:
    """Complete migration plan for all databases"""
    admin_config: Optional[MigrationConfig] = None
    regional_configs: List[MigrationConfig] = field(default_factory=list)
    tenant_configs: List[MigrationConfig] = field(default_factory=list)
    total_operations: int = 0
    rollback_on_failure: bool = True
    completed_migrations: List[Tuple[MigrationConfig, str]] = field(default_factory=list)


class DynamicMigrationEngine:
    """Dynamic migration engine that reads configuration from database"""
    
    def __init__(self):
        self.admin_pool: Optional[asyncpg.Pool] = None
        self.migration_base_path = Path("/app/flyway")
        # We don't need to list individual files - Flyway will discover them automatically
        # based on the locations we provide in the config
        
    async def initialize(self):
        """Initialize connection to admin database"""
        # Check if APP_ENCRYPTION_KEY is available
        if os.getenv('APP_ENCRYPTION_KEY'):
            console.print("[green]✅ Encryption key found, passwords will be decrypted[/green]")
        else:
            console.print("[yellow]⚠️  APP_ENCRYPTION_KEY not set, using plaintext passwords[/yellow]")
        
        self.admin_pool = await asyncpg.create_pool(
            host=os.getenv('POSTGRES_US_HOST', 'neo-postgres-us-east'),
            port=int(os.getenv('POSTGRES_US_PORT', '5432')),
            database='neofast_admin',
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD', 'postgres'),
            min_size=2,
            max_size=10
        )
        console.print("[green]✅ Migration engine initialized[/green]")
    
    async def get_migration_plan(self) -> MigrationPlan:
        """Build complete migration plan from database_connections table"""
        plan = MigrationPlan()
        
        async with self.admin_pool.acquire() as conn:
            # Get all active database connections
            rows = await conn.fetch("""
                SELECT 
                    id, connection_name, host, port, database_name,
                    username, encrypted_password, region_id, connection_type
                FROM admin.database_connections 
                WHERE is_active = true AND is_healthy = true
                ORDER BY connection_type, region_id
            """)
            
            for row in rows:
                config = await self._build_migration_config(row)
                
                if config.database_type == DatabaseType.ADMIN:
                    # Skip admin database for dynamic migrations
                    continue
                elif config.database_type in [DatabaseType.SHARED, DatabaseType.ANALYTICS]:
                    plan.regional_configs.append(config)
                elif config.database_type == DatabaseType.TENANT:
                    plan.tenant_configs.append(config)
            
            # Calculate total operations
            if plan.admin_config:
                plan.total_operations += len(plan.admin_config.schemas_to_migrate)
            for config in plan.regional_configs:
                plan.total_operations += len(config.schemas_to_migrate)
            for config in plan.tenant_configs:
                plan.total_operations += len(config.schemas_to_migrate)
        
        return plan
    
    async def _build_migration_config(self, row: asyncpg.Record) -> MigrationConfig:
        """Build migration configuration for a database"""
        # Determine database type from connection_type
        connection_type = row['connection_type'].lower()
        
        if 'admin' in connection_type or row['database_name'] == 'neofast_admin':
            db_type = DatabaseType.ADMIN
            # Order matters: platform_common must be migrated before admin
            schemas = ['platform_common', 'admin']
            migration_sets = [MigrationSet.PLATFORM_COMMON, MigrationSet.ADMIN]
        elif 'shared' in row['database_name']:
            # Check database name for shared databases
            db_type = DatabaseType.SHARED
            schemas = ['platform_common', 'tenant_template']
            migration_sets = [MigrationSet.PLATFORM_COMMON, MigrationSet.REGIONAL_SHARED]
        elif 'analytics' in connection_type or 'analytics' in row['database_name']:
            db_type = DatabaseType.ANALYTICS
            schemas = ['platform_common', 'analytics']
            migration_sets = [MigrationSet.PLATFORM_COMMON, MigrationSet.REGIONAL_ANALYTICS]
        else:
            db_type = DatabaseType.TENANT
            schemas = ['public']  # Or specific tenant schema
            migration_sets = [MigrationSet.REGIONAL_SHARED]
        
        # Determine region and GDPR compliance
        region_name = await self._get_region_name(row['region_id'])
        is_gdpr = 'eu' in region_name.lower()
        
        # Get and decrypt password if needed
        password = await self._get_password(row)
        
        return MigrationConfig(
            database_id=row['id'],
            database_name=row['database_name'],
            host=row['host'],
            port=row['port'],
            username=row['username'] or 'postgres',
            password=password,
            region=region_name,
            database_type=db_type,
            schemas_to_migrate=schemas,
            migration_sets=migration_sets,
            placeholders={
                'region': region_name,
                'gdpr': str(is_gdpr).lower()
            }
        )
    
    async def _get_password(self, row: asyncpg.Record) -> str:
        """Get password - decrypt if encrypted, otherwise return as-is"""
        # First check for encrypted_password column
        encrypted_password = row.get('encrypted_password')
        
        if encrypted_password and encrypted_password.strip():
            # We have an encrypted password, decrypt it
            try:
                decrypted = decrypt_password(encrypted_password)
                logger.info(f"Decrypted password for connection {row['id']}")
                return decrypted
            except Exception as e:
                logger.warning(f"Failed to decrypt password for connection {row['id']}: {e}")
                # Fallback to plaintext password or environment variable
        
        # Check for plaintext password column (legacy support)
        password = row.get('password')
        if password:
            return password
        
        # Fallback to environment variable
        logger.info(f"Using environment password for connection {row.get('connection_name', 'unknown')}")
        return os.getenv('POSTGRES_PASSWORD', 'postgres')
    
    async def _get_region_name(self, region_id: str) -> str:
        """Get region name from region_id"""
        async with self.admin_pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT name FROM admin.regions 
                WHERE id = $1
            """, region_id)
            return result or 'unknown'
    
    async def execute_migration_plan(self, plan: MigrationPlan, dry_run: bool = False, batch_id: Optional[str] = None) -> Optional[str]:
        """Execute the complete migration plan with batch tracking. Returns batch_id if created."""
        console.print(Panel.fit("🚀 Executing Dynamic Migration Plan", style="bold blue"))
        
        # Create migration batch if not provided
        if not batch_id and not dry_run:
            batch_id = await self._create_migration_batch(plan)
            logger.info(f"Created migration batch: {batch_id}")
        
        try:
            # Phase 1: Admin database (SKIPPED - admin migrations handled separately)
            if plan.admin_config:
                console.print("\n[bold]Phase 1: Admin Database[/bold]")
                console.print("  [yellow]⚠️ Skipping admin database - migrations handled separately[/yellow]")
            
            # Phase 2: Regional databases
            if plan.regional_configs:
                console.print("\n[bold]Phase 2: Regional Databases[/bold]")
                for config in plan.regional_configs:
                    success = await self._migrate_database(config, dry_run, batch_id, plan)
                    if not success and plan.rollback_on_failure:
                        raise Exception(f"Regional database migration failed: {config.database_name}")
            
            # Phase 3: Tenant databases
            if plan.tenant_configs:
                console.print("\n[bold]Phase 3: Tenant Databases[/bold]")
                with Progress() as progress:
                    task = progress.add_task(
                        "[cyan]Migrating tenants...", 
                        total=len(plan.tenant_configs)
                    )
                    for config in plan.tenant_configs:
                        success = await self._migrate_database(config, dry_run, batch_id, plan)
                        if not success and plan.rollback_on_failure:
                            raise Exception(f"Tenant database migration failed: {config.database_name}")
                        progress.update(task, advance=1)
            
            # Mark batch as completed
            if batch_id and not dry_run:
                await self._complete_migration_batch(batch_id, "completed")
            
            console.print("\n[bold green]✅ Migration plan executed successfully![/bold green]")
            return batch_id
            
        except Exception as e:
            console.print(f"\n[bold red]❌ Migration failed: {e}[/bold red]")
            
            # Rollback if enabled
            if plan.rollback_on_failure and plan.completed_migrations and not dry_run:
                console.print("\n[bold yellow]🔄 Rolling back completed migrations...[/bold yellow]")
                await self._rollback_migrations(plan.completed_migrations)
            
            # Mark batch as failed
            if batch_id and not dry_run:
                await self._complete_migration_batch(batch_id, "failed", str(e))
            raise
    
    async def _migrate_database(self, config: MigrationConfig, dry_run: bool = False, batch_id: Optional[str] = None, plan: Optional[MigrationPlan] = None) -> bool:
        """Migrate a specific database with its migration sets"""
        console.print(f"\n[cyan]Migrating {config.database_name} ({config.database_type.value})[/cyan]")
        
        # Pre-flight check: Test database connectivity
        if not await self._test_database_connection(config):
            console.print(f"  [red]❌ Failed to connect to {config.database_name}[/red]")
            if batch_id and not dry_run:
                await self._record_migration_failure(batch_id, config, "pre-flight", "Database connection failed")
            return False
        
        # Get migration order using dependency resolver
        ordered_migrations = MigrationDependencyResolver.get_migration_order(config.schemas_to_migrate)
        
        console.print(f"  [blue]Migration order: {' → '.join([m.schema_name for m in ordered_migrations])}[/blue]")
        
        for migration in ordered_migrations:
            # Validate migration files exist
            if not dry_run and not await self._validate_migration_files(migration.migration_location):
                console.print(f"  [red]❌ Migration files not found for {migration.schema_name}[/red]")
                if batch_id:
                    await self._record_migration_failure(batch_id, config, migration.schema_name, "Migration files not found")
                return False
            
            # Build Flyway configuration dynamically
            flyway_config = MigrationDependencyResolver.build_flyway_config(
                database_url=f"jdbc:postgresql://{config.host}:{config.port}/{config.database_name}",
                username=config.username,
                password=config.password,
                schema_name=migration.schema_name,
                migration_location=migration.migration_location
            )
            
            # Add any placeholders
            if config.placeholders:
                for key, value in config.placeholders.items():
                    flyway_config += f"flyway.placeholders.{key}={value}\n"
            
            # Write temporary config file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
                f.write(flyway_config)
                temp_config_path = f.name
            
            try:
                # Run Flyway migration
                cmd = [
                    'flyway',
                    '-configFiles=' + temp_config_path,
                    'migrate' if not dry_run else 'info'
                ]
                
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=60
                )
                
                if result.returncode == 0:
                    console.print(f"  [green]✅ {migration.schema_name} schema migrated → {migration.schema_name}.flyway_schema_history[/green]")
                    if batch_id and not dry_run:
                        await self._record_migration_success(batch_id, config, migration.schema_name, result.stdout)
                    # Track successful migration for potential rollback
                    if plan and not dry_run:
                        plan.completed_migrations.append((config, migration.schema_name))
                else:
                    console.print(f"  [red]❌ {migration.schema_name} schema failed[/red]")
                    if result.stderr:
                        console.print(f"  [red]{result.stderr[:200]}[/red]")
                    if batch_id and not dry_run:
                        await self._record_migration_failure(batch_id, config, migration.schema_name, result.stderr)
                    # Don't continue if a dependency fails
                    return False
                    
            except subprocess.TimeoutExpired:
                console.print(f"  [red]⏱️ Migration timeout for {migration.schema_name}[/red]")
                if batch_id and not dry_run:
                    await self._record_migration_failure(batch_id, config, migration.schema_name, "Migration timeout")
                return False
            except Exception as e:
                console.print(f"  [red]❌ Unexpected error for {migration.schema_name}: {e}[/red]")
                if batch_id and not dry_run:
                    await self._record_migration_failure(batch_id, config, migration.schema_name, str(e))
                return False
            finally:
                # Clean up temp config
                if os.path.exists(temp_config_path):
                    os.unlink(temp_config_path)
        
        # All migrations completed successfully
        return True
    
    # Method removed - now using MigrationDependencyResolver.build_flyway_config()
    
    async def _create_migration_batch(self, plan: MigrationPlan) -> str:
        """Create a new migration batch record"""
        async with self.admin_pool.acquire() as conn:
            batch_id = await conn.fetchval("""
                INSERT INTO admin.migration_batches (
                    batch_name,
                    batch_type,
                    scope,
                    total_targets,
                    total_databases,
                    total_schemas,
                    status,
                    executed_by,
                    execution_mode,
                    metadata
                ) VALUES (
                    $1,
                    'dynamic',
                    'regional',
                    $2,
                    $3,
                    $4,
                    'running',
                    $5,
                    'auto',
                    $6
                ) RETURNING id
            """, 
            f"Dynamic Migration - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
            len(plan.regional_configs) + len(plan.tenant_configs),
            len(plan.regional_configs) + len(plan.tenant_configs),
            plan.total_operations,
            'deployment-api',
            json.dumps({
                'regional_databases': [c.database_name for c in plan.regional_configs],
                'tenant_databases': [c.database_name for c in plan.tenant_configs]
            })
            )
            return str(batch_id)
    
    async def _complete_migration_batch(self, batch_id: str, status: str, error: Optional[str] = None):
        """Mark a migration batch as completed or failed"""
        async with self.admin_pool.acquire() as conn:
            if error:
                await conn.execute("""
                    UPDATE admin.migration_batches
                    SET status = $2,
                        completed_at = CURRENT_TIMESTAMP,
                        error_message = $3
                    WHERE id = $1
                """, batch_id, status, error)
            else:
                await conn.execute("""
                    UPDATE admin.migration_batches
                    SET status = $2,
                        completed_at = CURRENT_TIMESTAMP,
                        successful_count = (
                            SELECT COUNT(*) FROM admin.migration_batch_details
                            WHERE batch_id = $1 AND status = 'success'
                        ),
                        failed_count = (
                            SELECT COUNT(*) FROM admin.migration_batch_details
                            WHERE batch_id = $1 AND status = 'failed'
                        )
                    WHERE id = $1
                """, batch_id, status)
    
    async def _record_migration_success(self, batch_id: str, config: MigrationConfig, schema: str, output: Optional[str] = None):
        """Record successful migration in batch details"""
        async with self.admin_pool.acquire() as conn:
            # Extract migration count from output if available
            migrations_applied = 0
            if output:
                for line in output.split('\n'):
                    if 'Successfully applied' in line:
                        # Try to extract number of migrations
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'applied' and i > 0:
                                try:
                                    migrations_applied = int(parts[i-1])
                                except:
                                    pass
            
            await conn.execute("""
                INSERT INTO admin.migration_batch_details (
                    batch_id,
                    target_database,
                    target_schema,
                    target_type,
                    status,
                    database_connection_id,
                    database_name,
                    schema_name,
                    migrations_applied,
                    execution_time_ms,
                    metadata
                ) VALUES (
                    $1, $2, $3, 'schema', 'success', $4, $5, $6, $7,
                    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - 
                        (SELECT started_at FROM admin.migration_batches WHERE id = $1)
                    )) * 1000,
                    $8
                )
            """, 
            batch_id, config.database_name, schema, config.database_id, 
            config.database_name, schema, migrations_applied,
            json.dumps({'region': config.region, 'database_type': config.database_type.value})
            )
            logger.info(f"Recorded successful migration for {config.database_name}.{schema}")
    
    async def _record_migration_failure(self, batch_id: str, config: MigrationConfig, schema: str, error: Optional[str] = None):
        """Record failed migration in batch details"""
        async with self.admin_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO admin.migration_batch_details (
                    batch_id,
                    target_database,
                    target_schema,
                    target_type,
                    status,
                    error_message,
                    database_connection_id,
                    database_name,
                    schema_name,
                    execution_time_ms,
                    metadata
                ) VALUES (
                    $1, $2, $3, 'schema', 'failed', $4, $5, $6, $7,
                    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - 
                        (SELECT started_at FROM admin.migration_batches WHERE id = $1)
                    )) * 1000,
                    $8
                )
            """, 
            batch_id, config.database_name, schema,
            error[:1000] if error else 'Unknown error',
            config.database_id, config.database_name, schema,
            json.dumps({'region': config.region, 'database_type': config.database_type.value})
            )
            logger.error(f"Recorded failed migration for {config.database_name}.{schema}")
    
    async def _test_database_connection(self, config: MigrationConfig) -> bool:
        """Test database connection before attempting migration"""
        try:
            pool = await asyncpg.create_pool(
                host=config.host,
                port=config.port,
                database=config.database_name,
                user=config.username,
                password=config.password,
                min_size=1,
                max_size=1,
                command_timeout=5
            )
            
            async with pool.acquire() as conn:
                # Simple connectivity test
                version = await conn.fetchval("SELECT version()")
                logger.info(f"Connected to {config.database_name}: {version[:50]}...")
                
            await pool.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to {config.database_name}: {e}")
            return False
    
    async def _validate_migration_files(self, migration_location: str) -> bool:
        """Validate migration files exist and are readable"""
        migration_path = Path(f"/app/flyway/{migration_location}")
        
        if not migration_path.exists():
            logger.error(f"Migration path does not exist: {migration_path}")
            return False
        
        sql_files = list(migration_path.glob("*.sql"))
        if not sql_files:
            logger.error(f"No SQL files found in: {migration_path}")
            return False
        
        logger.info(f"Found {len(sql_files)} migration files in {migration_path}")
        return True
    
    async def get_migration_status(self) -> Table:
        """Get current migration status for all databases"""
        table = Table(title="Dynamic Migration Status")
        table.add_column("Database", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Schema", style="yellow")
        table.add_column("Current Version", style="green")
        table.add_column("Status", style="blue")
        
        plan = await self.get_migration_plan()
        
        # Check all databases
        all_configs = []
        if plan.admin_config:
            all_configs.append(plan.admin_config)
        all_configs.extend(plan.regional_configs)
        all_configs.extend(plan.tenant_configs)
        
        for config in all_configs:
            for schema in config.schemas_to_migrate:
                version = await self._get_current_version(config, schema)
                status = "✅ Up to date" if version else "⚠️ Not migrated"
                table.add_row(
                    config.database_name,
                    config.database_type.value,
                    schema,
                    version or "None",
                    status
                )
        
        return table
    
    async def _get_current_version(self, config: MigrationConfig, schema: str) -> Optional[str]:
        """Get current migration version for a schema"""
        try:
            pool = await asyncpg.create_pool(
                host=config.host,
                port=config.port,
                database=config.database_name,
                user=config.username,
                password=config.password,
                min_size=1,
                max_size=2
            )
            
            async with pool.acquire() as conn:
                # Check if schema exists
                schema_exists = await conn.fetchval("""
                    SELECT EXISTS(
                        SELECT 1 FROM information_schema.schemata 
                        WHERE schema_name = $1
                    )
                """, schema)
                
                if not schema_exists:
                    return None
                
                # Check if flyway table exists
                table_exists = await conn.fetchval("""
                    SELECT EXISTS(
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = $1 
                        AND table_name = 'flyway_schema_history'
                    )
                """, schema)
                
                if not table_exists:
                    return None
                
                # Get latest version
                version = await conn.fetchval(f"""
                    SELECT MAX(version) 
                    FROM {schema}.flyway_schema_history 
                    WHERE success = true
                """)
                
                return version
                
        except Exception as e:
            logger.error(f"Error checking version for {config.database_name}.{schema}: {e}")
            return None
        finally:
            if 'pool' in locals():
                await pool.close()
    
    async def _rollback_migrations(self, completed_migrations: List[Tuple[MigrationConfig, str]]):
        """Rollback completed migrations in reverse order"""
        # Rollback in reverse order
        for config, schema_name in reversed(completed_migrations):
            console.print(f"  [yellow]↩️ Rolling back {config.database_name}.{schema_name}[/yellow]")
            
            try:
                # Get current version to determine rollback target
                current_version = await self._get_current_version(config, schema_name)
                if not current_version:
                    console.print(f"    [blue]ℹ️ No migrations to rollback for {schema_name}[/blue]")
                    continue
                
                # For now, we'll just log the rollback since Flyway's undo requires Teams Edition
                # In production, you would implement proper rollback logic based on your needs
                console.print(f"    [yellow]⚠️ Rollback would revert from version {current_version}[/yellow]")
                console.print(f"    [yellow]   (Actual rollback requires Flyway Teams Edition)[/yellow]")
                
                # Record the rollback attempt
                async with self.admin_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO admin.migration_rollbacks (
                            database_id,
                            database_name,
                            schema_name,
                            from_version,
                            rollback_reason,
                            status
                        ) VALUES ($1, $2, $3, $4, $5, $6)
                    """, config.database_id, config.database_name, schema_name,
                        current_version, "Migration failure in batch", "logged_only")
                
            except Exception as e:
                console.print(f"    [red]❌ Failed to rollback {schema_name}: {e}[/red]")
                logger.error(f"Rollback failed for {config.database_name}.{schema_name}: {e}")
    
    async def cleanup(self):
        """Clean up resources"""
        if self.admin_pool:
            await self.admin_pool.close()


@click.group()
def cli():
    """Dynamic Migration Engine CLI"""
    pass


@cli.command()
@click.option('--dry-run', is_flag=True, help='Show migration plan without executing')
def migrate(dry_run):
    """Execute dynamic migration plan"""
    async def run():
        engine = DynamicMigrationEngine()
        await engine.initialize()
        
        # Get migration plan
        plan = await engine.get_migration_plan()
        
        # Show plan summary
        console.print("\n[bold]Migration Plan Summary:[/bold]")
        if plan.admin_config:
            console.print(f"  • Admin database: {plan.admin_config.database_name}")
        console.print(f"  • Regional databases: {len(plan.regional_configs)}")
        console.print(f"  • Tenant databases: {len(plan.tenant_configs)}")
        console.print(f"  • Total operations: {plan.total_operations}")
        
        if not dry_run:
            # Execute plan
            await engine.execute_migration_plan(plan, dry_run=False)
        else:
            console.print("\n[yellow]Dry run mode - no migrations executed[/yellow]")
        
        await engine.cleanup()
    
    asyncio.run(run())


@cli.command()
def status():
    """Show migration status for all databases"""
    async def run():
        engine = DynamicMigrationEngine()
        await engine.initialize()
        
        table = await engine.get_migration_status()
        console.print(table)
        
        await engine.cleanup()
    
    asyncio.run(run())


@cli.command()
@click.argument('database')
@click.argument('schema')
def check(database, schema):
    """Check migration status for specific database/schema"""
    async def run():
        engine = DynamicMigrationEngine()
        await engine.initialize()
        
        # Find the database configuration
        plan = await engine.get_migration_plan()
        config = None
        
        all_configs = []
        if plan.admin_config:
            all_configs.append(plan.admin_config)
        all_configs.extend(plan.regional_configs)
        all_configs.extend(plan.tenant_configs)
        
        for c in all_configs:
            if c.database_name == database:
                config = c
                break
        
        if config:
            version = await engine._get_current_version(config, schema)
            if version:
                console.print(f"[green]Current version: {version}[/green]")
            else:
                console.print(f"[yellow]Schema not migrated or doesn't exist[/yellow]")
        else:
            console.print(f"[red]Database {database} not found[/red]")
        
        await engine.cleanup()
    
    asyncio.run(run())


if __name__ == '__main__':
    cli()