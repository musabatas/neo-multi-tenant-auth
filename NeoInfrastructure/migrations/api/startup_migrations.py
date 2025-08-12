#!/usr/bin/env python3
"""
Startup Migrations - Automatically apply admin database migrations on API startup
"""

import asyncio
import asyncpg
import subprocess
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class StartupMigrationRunner:
    """Runs admin database migrations on API startup"""
    
    def __init__(self):
        self.admin_host = os.getenv('POSTGRES_US_HOST', 'neo-postgres-us-east')
        self.admin_port = int(os.getenv('POSTGRES_US_PORT', '5432'))
        self.admin_db = 'neofast_admin'
        self.username = os.getenv('POSTGRES_USER', 'postgres')
        self.password = os.getenv('POSTGRES_PASSWORD', 'postgres')
        
    async def run_admin_migrations(self):
        """Run admin database migrations on startup using Flyway configs"""
        logger.info("Starting admin database migrations...")
        
        try:
            # First ensure database exists
            await self._ensure_admin_database()
            
            # Run migrations using Flyway configuration files
            await self._run_migration_from_config('platform-common', 'Platform Common Schema')
            await self._run_migration_from_config('admin-schema', 'Admin Schema')
            
            logger.info("✅ Admin database migrations completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to run admin migrations: {e}")
            return False
    
    async def _ensure_admin_database(self):
        """Ensure admin database exists"""
        try:
            # Connect to default postgres database
            conn = await asyncpg.connect(
                host=self.admin_host,
                port=self.admin_port,
                database='postgres',
                user=self.username,
                password=self.password
            )
            
            # Check if admin database exists
            exists = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM pg_database 
                    WHERE datname = $1
                )
            """, self.admin_db)
            
            if not exists:
                logger.info(f"Creating admin database: {self.admin_db}")
                await conn.execute(f'CREATE DATABASE {self.admin_db}')
            
            await conn.close()
            
        except Exception as e:
            logger.error(f"Error ensuring admin database: {e}")
            raise
    
    async def _run_migration_from_config(self, config_name: str, description: str):
        """Run migrations using Flyway configuration file"""
        logger.info(f"Running {description} using {config_name}.conf...")
        
        cmd = [
            'flyway',
            f'-configFiles=/app/flyway/conf/{config_name}.conf',
            'migrate'
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd='/app'
            )
            
            if result.returncode == 0:
                logger.info(f"✅ {description} migrations applied successfully")
                # Log successful migrations
                if 'Successfully applied' in result.stdout:
                    for line in result.stdout.split('\n'):
                        if 'Successfully applied' in line or 'Current version' in line:
                            logger.info(f"  {line.strip()}")
            else:
                logger.warning(f"⚠️ {description} migrations completed with warnings")
                if result.stderr:
                    logger.error(f"Flyway stderr: {result.stderr[:500]}")
                    
        except subprocess.TimeoutExpired:
            logger.error(f"Migration timeout for {description}")
            raise
        except Exception as e:
            logger.error(f"Failed to run {description} migrations: {e}")
            raise
    
    
    async def verify_admin_schema(self) -> bool:
        """Verify admin schema is properly set up"""
        try:
            conn = await asyncpg.connect(
                host=self.admin_host,
                port=self.admin_port,
                database=self.admin_db,
                user=self.username,
                password=self.password
            )
            
            # Check if critical tables exist
            critical_tables = [
                ('admin', 'database_connections'),
                ('admin', 'regions'),
                ('admin', 'migration_locks'),
                ('admin', 'migration_batches')
            ]
            
            for schema, table in critical_tables:
                exists = await conn.fetchval("""
                    SELECT EXISTS(
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = $1 AND table_name = $2
                    )
                """, schema, table)
                
                if not exists:
                    logger.error(f"Missing critical table: {schema}.{table}")
                    await conn.close()
                    return False
            
            # Get migration count from each schema's own history table
            try:
                admin_count = await conn.fetchval("""
                    SELECT COUNT(*) FROM admin.flyway_schema_history 
                    WHERE success = true
                """)
                logger.info(f"Admin schema has {admin_count} migrations")
            except:
                logger.info("Admin schema history table not found (will be created on first migration)")
            
            try:
                platform_count = await conn.fetchval("""
                    SELECT COUNT(*) FROM platform_common.flyway_schema_history 
                    WHERE success = true
                """)
                logger.info(f"Platform common has {platform_count} migrations")
            except:
                logger.info("Platform common history table not found (will be created on first migration)")
            
            await conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify admin schema: {e}")
            return False


async def run_startup_migrations():
    """Main function to run on API startup"""
    runner = StartupMigrationRunner()
    
    # Run migrations
    success = await runner.run_admin_migrations()
    
    if success:
        # Verify setup
        verified = await runner.verify_admin_schema()
        if verified:
            logger.info("🎉 Admin database fully initialized and verified")
            return True
        else:
            logger.error("Admin database verification failed")
            return False
    else:
        logger.error("Admin database migration failed")
        return False


if __name__ == "__main__":
    # For testing
    asyncio.run(run_startup_migrations())