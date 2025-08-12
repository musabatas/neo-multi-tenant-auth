#!/usr/bin/env python3
"""
Enhanced Migration Manager - Dynamic Database Management
Handles migrations across thousands of schemas with proper tracking
"""

import asyncio
import asyncpg
import os
import subprocess
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import logging
from pathlib import Path
from dataclasses import dataclass, field
from encryption import decrypt_password

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.live import Live

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
console = Console()


@dataclass
class DatabaseConnection:
    """Database connection configuration"""
    id: str
    name: str
    host: str
    port: int
    database: str
    username: str
    password: str
    region: str
    connection_type: str
    is_active: bool = True
    is_healthy: bool = True
    schemas: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MigrationStatus:
    """Migration status for a database/schema"""
    database: str
    schema: str
    current_version: str
    pending_migrations: List[str]
    last_migration_date: Optional[datetime]
    status: str  # 'up-to-date', 'pending', 'failed'
    error_message: Optional[str] = None


class MigrationLock:
    """Distributed lock for migrations"""
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        
    async def acquire(self, resource_key: str, worker_id: str, timeout_seconds: int = 600) -> bool:
        """Acquire a migration lock"""
        async with self.pool.acquire() as conn:
            try:
                expires_at = datetime.utcnow() + timedelta(seconds=timeout_seconds)
                await conn.execute("""
                    INSERT INTO admin.migration_locks (resource_key, locked_by, expires_at)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (resource_key) DO NOTHING
                """, resource_key, worker_id, expires_at)
                
                # Check if we got the lock
                result = await conn.fetchval("""
                    SELECT locked_by FROM admin.migration_locks 
                    WHERE resource_key = $1 AND locked_by = $2
                """, resource_key, worker_id)
                
                return result == worker_id
            except Exception as e:
                logger.error(f"Failed to acquire lock: {e}")
                return False
    
    async def release(self, resource_key: str, worker_id: str) -> bool:
        """Release a migration lock"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute("""
                    DELETE FROM admin.migration_locks 
                    WHERE resource_key = $1 AND locked_by = $2
                """, resource_key, worker_id)
                return True
            except Exception as e:
                logger.error(f"Failed to release lock: {e}")
                return False
    
    async def cleanup_expired(self) -> int:
        """Clean up expired locks"""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM admin.migration_locks 
                WHERE expires_at < NOW()
            """)
            return int(result.split()[-1])


class EnhancedMigrationManager:
    """Enhanced migration manager with dynamic database connections"""
    
    def __init__(self):
        self.admin_pool: Optional[asyncpg.Pool] = None
        self.connections: Dict[str, DatabaseConnection] = {}
        self.lock_manager: Optional[MigrationLock] = None
        self.worker_id = f"worker-{os.getpid()}"
        
    async def initialize(self):
        """Initialize the migration manager"""
        # Connect to admin database
        self.admin_pool = await asyncpg.create_pool(
            host=os.getenv('POSTGRES_US_HOST', 'neo-postgres-us-east'),
            port=int(os.getenv('POSTGRES_US_PORT', '5432')),
            database='neofast_admin',
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD', 'postgres'),
            min_size=5,
            max_size=20
        )
        
        self.lock_manager = MigrationLock(self.admin_pool)
        await self.load_database_connections()
        
        console.print("[green]✅ Migration manager initialized[/green]")
    
    async def load_database_connections(self):
        """Load database connections from admin.database_connections"""
        async with self.admin_pool.acquire() as conn:
            # Check if table exists
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'admin' 
                    AND table_name = 'database_connections'
                )
            """)
            
            if not table_exists:
                console.print("[yellow]⚠️  database_connections table not found, using defaults[/yellow]")
                self._load_default_connections()
                return
            
            rows = await conn.fetch("""
                SELECT * FROM admin.database_connections 
                WHERE is_active = true AND is_healthy = true
                ORDER BY connection_type, region_id, connection_name
            """)
            
            for row in rows:
                # Decrypt password if encrypted
                password = 'postgres'  # Default
                encrypted_password = row.get('encrypted_password')
                if encrypted_password:
                    try:
                        password = decrypt_password(encrypted_password)
                    except Exception as e:
                        logger.warning(f"Failed to decrypt password for {row['connection_name']}: {e}")
                        password = os.getenv('POSTGRES_PASSWORD', 'postgres')
                
                connection = DatabaseConnection(
                    id=row['id'],
                    name=row['connection_name'],
                    host=row['host'],
                    port=row['port'],
                    database=row['database_name'],
                    username=row.get('username', 'postgres'),  # Default to postgres
                    password=password,
                    region=row['region_id'],
                    connection_type=row['connection_type'],
                    is_active=row['is_active'],
                    is_healthy=row['is_healthy'],
                    schemas=row.get('schemas', []),
                    metadata=row.get('metadata', {})
                )
                self.connections[connection.id] = connection
    
    def _load_default_connections(self):
        """Load default connections for development"""
        self.connections = {
            'admin-us': DatabaseConnection(
                id='admin-us',
                name='Admin Database',
                host='neo-postgres-us-east',
                port=5432,
                database='neofast_admin',
                username='postgres',
                password='postgres',
                region='us-east',
                connection_type='admin',
                schemas=['admin', 'platform_common']
            ),
            'shared-us': DatabaseConnection(
                id='shared-us',
                name='US Shared Database',
                host='neo-postgres-us-east',
                port=5432,
                database='neofast_shared_us',
                username='postgres',
                password='postgres',
                region='us-east',
                connection_type='shared',
                schemas=['platform_common', 'tenant_template']
            ),
            'shared-eu': DatabaseConnection(
                id='shared-eu',
                name='EU Shared Database',
                host='neo-postgres-eu-west',
                port=5432,
                database='neofast_shared_eu',
                username='postgres',
                password='postgres',
                region='eu-west',
                connection_type='shared',
                schemas=['platform_common', 'tenant_template']
            ),
            'analytics-us': DatabaseConnection(
                id='analytics-us',
                name='US Analytics Database',
                host='neo-postgres-us-east',
                port=5432,
                database='neofast_analytics_us',
                username='postgres',
                password='postgres',
                region='us-east',
                connection_type='analytics',
                schemas=['platform_common', 'analytics']
            ),
            'analytics-eu': DatabaseConnection(
                id='analytics-eu',
                name='EU Analytics Database',
                host='neo-postgres-eu-west',
                port=5432,
                database='neofast_analytics_eu',
                username='postgres',
                password='postgres',
                region='eu-west',
                connection_type='analytics',
                schemas=['platform_common', 'analytics']
            )
        }
    
    async def get_migration_status(self, connection: DatabaseConnection, schema: str = 'public') -> MigrationStatus:
        """Get migration status for a database/schema"""
        try:
            # Build Flyway command to check status
            cmd = self._build_flyway_command(connection, schema, 'info')
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Parse Flyway output
            pending = []
            current_version = 'None'
            last_date = None
            
            for line in result.stdout.split('\n'):
                if '| Pending' in line:
                    parts = line.split('|')
                    if len(parts) > 2:
                        pending.append(parts[2].strip())
                elif '| Success' in line:
                    parts = line.split('|')
                    if len(parts) > 2:
                        current_version = parts[2].strip()
                        if len(parts) > 5:
                            try:
                                last_date = datetime.strptime(parts[5].strip(), '%Y-%m-%d %H:%M:%S')
                            except:
                                pass
            
            status = 'up-to-date' if not pending else 'pending'
            
            return MigrationStatus(
                database=connection.database,
                schema=schema,
                current_version=current_version,
                pending_migrations=pending,
                last_migration_date=last_date,
                status=status
            )
        except subprocess.TimeoutExpired:
            return MigrationStatus(
                database=connection.database,
                schema=schema,
                current_version='Unknown',
                pending_migrations=[],
                last_migration_date=None,
                status='failed',
                error_message='Timeout checking status'
            )
        except Exception as e:
            return MigrationStatus(
                database=connection.database,
                schema=schema,
                current_version='Unknown',
                pending_migrations=[],
                last_migration_date=None,
                status='failed',
                error_message=str(e)
            )
    
    def _build_flyway_command(self, connection: DatabaseConnection, schema: str, operation: str) -> List[str]:
        """Build Flyway command with dynamic parameters"""
        locations = self._get_migration_locations(connection.connection_type)
        
        return [
            'flyway',
            operation,
            f'-url=jdbc:postgresql://{connection.host}:{connection.port}/{connection.database}',
            f'-user={connection.username}',
            f'-password={connection.password}',
            f'-schemas={schema}',
            f'-locations={",".join(locations)}',
            '-baselineOnMigrate=true',
            '-validateOnMigrate=true',
            '-mixed=true'
        ]
    
    def _get_migration_locations(self, connection_type: str) -> List[str]:
        """Get migration file locations based on connection type"""
        base_path = '/app/flyway'
        
        if connection_type == 'admin':
            return [f'filesystem:{base_path}/global']
        elif connection_type == 'shared':
            return [
                f'filesystem:{base_path}/global',
                f'filesystem:{base_path}/regional/shared'
            ]
        elif connection_type == 'analytics':
            return [
                f'filesystem:{base_path}/global',
                f'filesystem:{base_path}/regional/analytics'
            ]
        elif connection_type == 'tenant':
            return [
                f'filesystem:{base_path}/global',
                f'filesystem:{base_path}/tenant'
            ]
        else:
            return [f'filesystem:{base_path}/global']
    
    async def migrate_database(self, connection: DatabaseConnection, schema: str = 'public') -> bool:
        """Run migration for a specific database/schema"""
        resource_key = f"{connection.database}:{schema}"
        
        # Acquire lock
        if not await self.lock_manager.acquire(resource_key, self.worker_id):
            console.print(f"[yellow]⏳ Waiting for lock on {resource_key}[/yellow]")
            return False
        
        try:
            console.print(f"[cyan]🔄 Migrating {connection.name} ({schema})[/cyan]")
            
            # Run Flyway migration
            cmd = self._build_flyway_command(connection, schema, 'migrate')
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                console.print(f"[green]✅ {connection.name} ({schema}) migrated successfully[/green]")
                await self._record_migration_success(connection, schema)
                return True
            else:
                console.print(f"[red]❌ Migration failed for {connection.name} ({schema})[/red]")
                console.print(f"[red]{result.stderr}[/red]")
                await self._record_migration_failure(connection, schema, result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            console.print(f"[red]⏱️ Migration timeout for {connection.name} ({schema})[/red]")
            return False
        finally:
            # Release lock
            await self.lock_manager.release(resource_key, self.worker_id)
    
    async def _record_migration_success(self, connection: DatabaseConnection, schema: str):
        """Record successful migration in tracking table"""
        async with self.admin_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO admin.migration_batch_details 
                (batch_id, target_database, target_schema, target_type, status, started_at, completed_at)
                VALUES ($1, $2, $3, 'schema', 'completed', NOW(), NOW())
                ON CONFLICT DO NOTHING
            """, self.worker_id, connection.database, schema)
    
    async def _record_migration_failure(self, connection: DatabaseConnection, schema: str, error: str):
        """Record failed migration in tracking table"""
        async with self.admin_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO admin.migration_batch_details 
                (batch_id, target_database, target_schema, target_type, status, error_message, started_at)
                VALUES ($1, $2, $3, 'schema', 'failed', $4, NOW())
                ON CONFLICT DO NOTHING
            """, self.worker_id, connection.database, schema, error[:500])
    
    async def migrate_all(self, batch_size: int = 10):
        """Migrate all databases and schemas"""
        console.print(Panel.fit("🚀 Starting Complete Migration", style="bold blue"))
        
        # Clean up expired locks
        expired = await self.lock_manager.cleanup_expired()
        if expired > 0:
            console.print(f"[yellow]🧹 Cleaned up {expired} expired locks[/yellow]")
        
        # Phase 1: Admin database
        console.print("\n[bold]Phase 1: Admin Database[/bold]")
        admin_conn = self.connections.get('admin-us')
        if admin_conn:
            await self.migrate_database(admin_conn, 'admin')
            await self.migrate_database(admin_conn, 'platform_common')
        
        # Phase 2: Regional databases
        console.print("\n[bold]Phase 2: Regional Databases[/bold]")
        for conn_id, connection in self.connections.items():
            if connection.connection_type in ['shared', 'analytics']:
                for schema in connection.schemas:
                    await self.migrate_database(connection, schema)
        
        # Phase 3: Tenant schemas (batched)
        console.print("\n[bold]Phase 3: Tenant Schemas[/bold]")
        tenant_schemas = await self._get_tenant_schemas()
        
        if tenant_schemas:
            with Progress() as progress:
                task = progress.add_task("[cyan]Migrating tenants...", total=len(tenant_schemas))
                
                for i in range(0, len(tenant_schemas), batch_size):
                    batch = tenant_schemas[i:i+batch_size]
                    await self._migrate_tenant_batch(batch)
                    progress.update(task, advance=len(batch))
        
        console.print("\n[bold green]✅ All migrations complete![/bold green]")
    
    async def _get_tenant_schemas(self) -> List[Tuple[str, str]]:
        """Get list of tenant schemas from database"""
        tenant_schemas = []
        
        async with self.admin_pool.acquire() as conn:
            # Check if tenants table exists
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'admin' 
                    AND table_name = 'tenants'
                )
            """)
            
            if table_exists:
                rows = await conn.fetch("""
                    SELECT database_name, schema_name 
                    FROM admin.tenants 
                    WHERE is_active = true
                    ORDER BY created_at
                """)
                
                for row in rows:
                    tenant_schemas.append((row['database_name'], row['schema_name']))
        
        return tenant_schemas
    
    async def _migrate_tenant_batch(self, batch: List[Tuple[str, str]]):
        """Migrate a batch of tenant schemas in parallel"""
        tasks = []
        for database, schema in batch:
            # Find the appropriate connection
            for connection in self.connections.values():
                if connection.database == database:
                    tasks.append(self.migrate_database(connection, schema))
                    break
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def show_status(self):
        """Show migration status dashboard"""
        console.print(Panel.fit("📊 Migration Status Dashboard", style="bold blue"))
        
        table = Table(title="Database Migration Status")
        table.add_column("Database", style="cyan")
        table.add_column("Schema", style="magenta")
        table.add_column("Current Version", style="green")
        table.add_column("Pending", style="yellow")
        table.add_column("Status", style="blue")
        
        for connection in self.connections.values():
            for schema in connection.schemas:
                status = await self.get_migration_status(connection, schema)
                
                status_emoji = "✅" if status.status == 'up-to-date' else "⚠️"
                pending_count = len(status.pending_migrations)
                
                table.add_row(
                    connection.name,
                    schema,
                    status.current_version,
                    str(pending_count),
                    f"{status_emoji} {status.status}"
                )
        
        console.print(table)
    
    async def cleanup(self):
        """Clean up resources"""
        if self.admin_pool:
            await self.admin_pool.close()


@click.group()
def cli():
    """Enhanced Migration Manager CLI"""
    pass


@cli.command()
@click.option('--batch-size', default=10, help='Number of schemas to migrate in parallel')
def migrate(batch_size):
    """Run all migrations"""
    async def run():
        manager = EnhancedMigrationManager()
        await manager.initialize()
        await manager.migrate_all(batch_size)
        await manager.cleanup()
    
    asyncio.run(run())


@cli.command()
def status():
    """Show migration status"""
    async def run():
        manager = EnhancedMigrationManager()
        await manager.initialize()
        await manager.show_status()
        await manager.cleanup()
    
    asyncio.run(run())


@cli.command()
@click.argument('database')
@click.argument('schema')
def migrate_single(database, schema):
    """Migrate a single database/schema"""
    async def run():
        manager = EnhancedMigrationManager()
        await manager.initialize()
        
        # Find the connection
        connection = None
        for conn in manager.connections.values():
            if conn.database == database:
                connection = conn
                break
        
        if connection:
            await manager.migrate_database(connection, schema)
        else:
            console.print(f"[red]Database {database} not found[/red]")
        
        await manager.cleanup()
    
    asyncio.run(run())


if __name__ == '__main__':
    cli()