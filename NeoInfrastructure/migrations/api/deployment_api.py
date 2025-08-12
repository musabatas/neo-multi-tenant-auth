#!/usr/bin/env python3
"""
NeoMultiTenant Deployment & Migration API
RESTful API for managing infrastructure deployment and database migrations
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import asyncpg
import subprocess
import os
import uuid
import logging
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our migration managers
import sys
sys.path.append('/app/orchestrator')
sys.path.append('/app/api')
from enhanced_migration_manager import EnhancedMigrationManager, DatabaseConnection
from dynamic_migration_engine import DynamicMigrationEngine
from startup_migrations import run_startup_migrations
from keycloak_provisioner import (
    build_default_provisioner_from_env,
    KeycloakProvisioner,
)


# ============== MODELS ==============

class DeploymentStatus(str, Enum):
    """Deployment status enum"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class MigrationScope(str, Enum):
    """Migration scope enum"""
    ALL = "all"
    ADMIN = "admin"
    REGIONAL = "regional"
    TENANT = "tenant"
    SINGLE = "single"


class ServiceType(str, Enum):
    """Service type enum"""
    POSTGRES = "postgres"
    REDIS = "redis"
    KEYCLOAK = "keycloak"
    MIGRATION = "migration"


class ServiceHealth(BaseModel):
    """Service health status"""
    service: str
    status: str
    healthy: bool
    message: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None


class DeploymentRequest(BaseModel):
    """Deployment request model"""
    services: List[ServiceType] = Field(default_factory=lambda: [ServiceType.POSTGRES, ServiceType.REDIS])
    regions: List[str] = Field(default_factory=lambda: ["us-east", "eu-west"])
    skip_migrations: bool = False
    dry_run: bool = False
    force: bool = False


class MigrationRequest(BaseModel):
    """Migration request model"""
    scope: MigrationScope = MigrationScope.ALL
    database: Optional[str] = None
    schema: Optional[str] = None
    batch_size: int = Field(default=10, ge=1, le=50)
    dry_run: bool = False
    skip_validation: bool = False


class MigrationSchedule(BaseModel):
    """Migration schedule model"""
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    scope: MigrationScope
    cron_expression: Optional[str] = None
    run_at: Optional[datetime] = None
    enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TenantMigrationRequest(BaseModel):
    """Tenant-specific migration request"""
    tenant_id: str
    tenant_slug: str
    database: str
    schema: str
    create_schema: bool = True


class RollbackRequest(BaseModel):
    """Rollback request model"""
    database: str
    schema: str = "public"
    target_version: str
    dry_run: bool = False


class DeploymentResponse(BaseModel):
    """Deployment response model"""
    deployment_id: str
    status: DeploymentStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    services_deployed: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MigrationResponse(BaseModel):
    """Migration response model"""
    migration_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    databases_migrated: int = 0
    schemas_migrated: int = 0
    errors: List[str] = Field(default_factory=list)
    progress: Optional[Dict[str, Any]] = None
    batch_id: Optional[str] = None


# ============== GLOBAL STATE ==============

class GlobalState:
    """Global application state"""
    def __init__(self):
        self.admin_pool: Optional[asyncpg.Pool] = None
        self.migration_manager: Optional[EnhancedMigrationManager] = None
        self.dynamic_engine: Optional[DynamicMigrationEngine] = None
        self.active_deployments: Dict[str, DeploymentResponse] = {}
        self.active_migrations: Dict[str, MigrationResponse] = {}
        self.keycloak_provisioner: Optional[KeycloakProvisioner] = None


state = GlobalState()


# ============== HELPER FUNCTIONS ==============

async def init_db_connection(conn):
    """Initialize database connection with encryption key"""
    encryption_key = os.getenv('APP_ENCRYPTION_KEY', 'default-dev-key-change-in-production')
    # Set the encryption key as a session parameter
    await conn.execute(f"SET app.encryption_key = '{encryption_key}'")

# ============== LIFECYCLE ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager"""
    # Startup
    logger.info("Starting Deployment API...")
    
    # Run admin database migrations first
    logger.info("Running admin database migrations...")
    migration_success = await run_startup_migrations()
    if not migration_success:
        logger.error("Failed to run admin migrations - API may not function correctly")
    else:
        logger.info("✅ Admin database migrations completed")
    
    # Initialize database pool
    state.admin_pool = await asyncpg.create_pool(
        host=os.getenv('POSTGRES_US_HOST', 'neo-postgres-us-east'),
        port=int(os.getenv('POSTGRES_US_PORT', '5432')),
        database='neofast_admin',
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', 'postgres'),
        min_size=5,
        max_size=20,
        init=init_db_connection
    )
    
    # Initialize migration manager
    state.migration_manager = EnhancedMigrationManager()
    await state.migration_manager.initialize()
    
    # Initialize dynamic migration engine
    state.dynamic_engine = DynamicMigrationEngine()
    await state.dynamic_engine.initialize()
    
    # Using our own encryption system for passwords
    logger.info("✅ Using built-in encryption system for database passwords")
    
    # Initialize Keycloak provisioner and kick off post-migration provisioning
    try:
        state.keycloak_provisioner = build_default_provisioner_from_env()
        asyncio.create_task(provision_missing_tenants())
        logger.info("🔑 Keycloak provisioner initialized; provisioning task scheduled")
    except Exception as e:
        logger.error(f"Failed to initialize Keycloak provisioner: {e}")

    logger.info("Deployment API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Deployment API...")
    
    if state.admin_pool:
        await state.admin_pool.close()
    
    if state.migration_manager:
        await state.migration_manager.cleanup()
    
    if state.dynamic_engine:
        await state.dynamic_engine.cleanup()
    
    
    logger.info("Deployment API shutdown complete")


# ============== APPLICATION ==============

app = FastAPI(
    title="NeoMultiTenant Deployment API",
    description="API for managing infrastructure deployment and database migrations",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== HEALTH ENDPOINTS ==============

@app.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@app.get("/health/services", response_model=List[ServiceHealth])
async def check_services_health():
    """Check health of all services"""
    services = []
    
    # Check PostgreSQL US East
    try:
        async with state.admin_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
            services.append(ServiceHealth(
                service="postgres-us-east",
                status="running",
                healthy=True,
                message="Database is responsive"
            ))
    except Exception as e:
        services.append(ServiceHealth(
            service="postgres-us-east",
            status="error",
            healthy=False,
            message=str(e)
        ))
    
    # Check Redis
    try:
        result = subprocess.run(
            ["docker", "exec", "neo-redis", "redis-cli", "-a", "redis", "ping"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            services.append(ServiceHealth(
                service="redis",
                status="running",
                healthy=True,
                message="Redis is responsive"
            ))
        else:
            services.append(ServiceHealth(
                service="redis",
                status="error",
                healthy=False,
                message="Redis not responding"
            ))
    except Exception as e:
        services.append(ServiceHealth(
            service="redis",
            status="error",
            healthy=False,
            message=str(e)
        ))
    
    # Check Keycloak
    try:
        import requests
        response = requests.get("http://neo-keycloak:8080/health/ready", timeout=5)
        if response.status_code == 200:
            services.append(ServiceHealth(
                service="keycloak",
                status="running",
                healthy=True,
                message="Keycloak is ready"
            ))
        else:
            services.append(ServiceHealth(
                service="keycloak",
                status="starting",
                healthy=False,
                message="Keycloak is starting up"
            ))
    except Exception:
        services.append(ServiceHealth(
            service="keycloak",
            status="error",
            healthy=False,
            message="Cannot connect to Keycloak"
        ))
    
    return services


# ============== DEPLOYMENT ENDPOINTS ==============

@app.post("/api/v1/deploy", response_model=DeploymentResponse)
async def deploy_infrastructure(
    request: DeploymentRequest,
    background_tasks: BackgroundTasks
):
    """Deploy infrastructure services"""
    deployment_id = str(uuid.uuid4())
    
    deployment = DeploymentResponse(
        deployment_id=deployment_id,
        status=DeploymentStatus.PENDING,
        started_at=datetime.utcnow()
    )
    
    state.active_deployments[deployment_id] = deployment
    
    # Start deployment in background
    background_tasks.add_task(
        execute_deployment,
        deployment_id,
        request
    )
    
    return deployment


@app.get("/api/v1/deploy/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment_status(deployment_id: str):
    """Get deployment status"""
    if deployment_id not in state.active_deployments:
        raise HTTPException(
            status_code=404,
            detail=f"Deployment {deployment_id} not found"
        )
    
    return state.active_deployments[deployment_id]


@app.get("/api/v1/deployments", response_model=List[DeploymentResponse])
async def list_deployments(
    status: Optional[DeploymentStatus] = None,
    limit: int = Query(default=10, ge=1, le=100)
):
    """List all deployments"""
    deployments = list(state.active_deployments.values())
    
    if status:
        deployments = [d for d in deployments if d.status == status]
    
    # Sort by started_at descending
    deployments.sort(key=lambda x: x.started_at, reverse=True)
    
    return deployments[:limit]


@app.delete("/api/v1/deploy/{deployment_id}")
async def stop_deployment(deployment_id: str):
    """Stop a deployment"""
    if deployment_id not in state.active_deployments:
        raise HTTPException(
            status_code=404,
            detail=f"Deployment {deployment_id} not found"
        )
    
    deployment = state.active_deployments[deployment_id]
    
    if deployment.status == DeploymentStatus.IN_PROGRESS:
        # TODO: Implement actual deployment cancellation
        deployment.status = DeploymentStatus.FAILED
        deployment.errors.append("Deployment cancelled by user")
    
    return {"message": f"Deployment {deployment_id} stopped"}


# ============== MIGRATION ENDPOINTS ==============

@app.post("/api/v1/migrations/dynamic", response_model=MigrationResponse)
async def run_dynamic_migrations(
    background_tasks: BackgroundTasks,
    dry_run: bool = Query(default=False, description="Show plan without executing")
):
    """Run dynamic migrations for all databases from database_connections table"""
    migration_id = str(uuid.uuid4())
    
    migration = MigrationResponse(
        migration_id=migration_id,
        status="in_progress" if not dry_run else "dry_run",
        started_at=datetime.utcnow()
    )
    
    state.active_migrations[migration_id] = migration
    
    async def execute_dynamic_migrations():
        try:
            # Get migration plan
            plan = await state.dynamic_engine.get_migration_plan()
            
            # Update migration with plan info
            total_databases = len(plan.regional_configs) + len(plan.tenant_configs)
            if plan.admin_config:
                total_databases += 1
            
            migration.progress = {
                "total_databases": total_databases,
                "total_schemas": plan.total_operations,
                "admin_database": plan.admin_config.database_name if plan.admin_config else None,
                "regional_databases": len(plan.regional_configs),
                "tenant_databases": len(plan.tenant_configs),
                "completed_databases": 0,
                "completed_schemas": 0,
                "current_phase": "initializing"
            }
            
            # Execute the plan (batch_id will be created by the engine)
            batch_id = await state.dynamic_engine.execute_migration_plan(plan, dry_run=dry_run)
            
            # Update migration with batch_id
            if batch_id:
                migration.batch_id = batch_id
            
            # Get final stats from batch
            if not dry_run and batch_id:
                async with state.admin_pool.acquire() as conn:
                    batch_stats = await conn.fetchrow("""
                        SELECT successful_count, failed_count, completed_at
                        FROM admin.migration_batches
                        WHERE id = $1
                    """, batch_id)
                    
                    if batch_stats:
                        migration.schemas_migrated = batch_stats['successful_count'] or 0
                        migration.progress['completed_schemas'] = batch_stats['successful_count'] or 0
                        migration.progress['failed_schemas'] = batch_stats['failed_count'] or 0
            
            migration.status = "completed"
            migration.completed_at = datetime.utcnow()
            migration.progress['current_phase'] = "completed"
            # After migrations, provision any pending tenants
            if state.keycloak_provisioner is not None and not dry_run:
                asyncio.create_task(provision_missing_tenants())
            
        except Exception as e:
            logger.error(f"Dynamic migration failed: {e}")
            migration.status = "failed"
            migration.errors.append(str(e))
            migration.completed_at = datetime.utcnow()
            if migration.progress:
                migration.progress['current_phase'] = "failed"
    
    if not dry_run:
        background_tasks.add_task(execute_dynamic_migrations)
    else:
        # For dry run, execute immediately
        await execute_dynamic_migrations()
    
    return migration


@app.get("/api/v1/migrations/dynamic/status", response_model=Dict[str, Any])
async def get_dynamic_migration_status():
    """Get dynamic migration status for all databases"""
    try:
        # Get migration plan to show summary
        plan = await state.dynamic_engine.get_migration_plan()
        
        # Get current status for each database
        status_data = []
        
        all_configs = []
        if plan.admin_config:
            all_configs.append(plan.admin_config)
        all_configs.extend(plan.regional_configs)
        all_configs.extend(plan.tenant_configs)
        
        for config in all_configs:
            for schema in config.schemas_to_migrate:
                version = await state.dynamic_engine._get_current_version(config, schema)
                status_data.append({
                    "database": config.database_name,
                    "type": config.database_type.value,
                    "schema": schema,
                    "current_version": version or "Not migrated",
                    "region": config.region
                })
        
        return {
            "total_databases": len(all_configs),
            "admin_database": plan.admin_config.database_name if plan.admin_config else None,
            "regional_databases": len(plan.regional_configs),
            "tenant_databases": len(plan.tenant_configs),
            "status_details": status_data
        }
        
    except Exception as e:
        logger.error(f"Failed to get dynamic migration status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get migration status: {str(e)}"
        )


# ============== ORIGINAL MIGRATION ENDPOINTS ==============

@app.post("/api/v1/migrations/apply", response_model=MigrationResponse)
async def apply_migrations(
    request: MigrationRequest,
    background_tasks: BackgroundTasks
):
    """Apply database migrations"""
    migration_id = str(uuid.uuid4())
    
    migration = MigrationResponse(
        migration_id=migration_id,
        status="pending",
        started_at=datetime.utcnow()
    )
    
    state.active_migrations[migration_id] = migration
    
    # Start migration in background
    background_tasks.add_task(
        execute_migration,
        migration_id,
        request
    )
    
    return migration


@app.get("/api/v1/migrations/status", response_model=Dict[str, Any])
async def get_migration_dashboard():
    """Get migration status dashboard"""
    async with state.admin_pool.acquire() as conn:
        # Get migration statistics
        total_databases = await conn.fetchval("""
            SELECT COUNT(DISTINCT database_name) 
            FROM admin.database_connections 
            WHERE is_active = true
        """)
        
        # Get recent migrations
        recent_migrations = await conn.fetch("""
            SELECT target_database, target_schema, status, completed_at
            FROM admin.migration_batch_details
            ORDER BY completed_at DESC
            LIMIT 10
        """)
        
        # Get pending migrations count
        # This would need to check Flyway schema history vs available migrations
        pending_count = 0  # TODO: Implement actual pending check
        
        return {
            "total_databases": total_databases or 0,
            "pending_migrations": pending_count,
            "recent_migrations": [dict(row) for row in recent_migrations] if recent_migrations else [],
            "active_migrations": len([m for m in state.active_migrations.values() if m.status == "in_progress"])
        }


@app.get("/api/v1/migrations/status/{database}/{schema}")
async def get_specific_migration_status(
    database: str,
    schema: str = "public"
):
    """Get migration status for specific database/schema"""
    # Find the connection
    connection = None
    for conn in state.migration_manager.connections.values():
        if conn.database == database:
            connection = conn
            break
    
    if not connection:
        raise HTTPException(
            status_code=404,
            detail=f"Database {database} not found"
        )
    
    status = await state.migration_manager.get_migration_status(connection, schema)
    
    return {
        "database": status.database,
        "schema": status.schema,
        "current_version": status.current_version,
        "pending_migrations": status.pending_migrations,
        "last_migration_date": status.last_migration_date.isoformat() if status.last_migration_date else None,
        "status": status.status,
        "error_message": status.error_message
    }


@app.post("/api/v1/migrations/schedule", response_model=MigrationSchedule)
async def schedule_migration(schedule: MigrationSchedule):
    """Schedule a migration window"""
    async with state.admin_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO admin.migration_schedules 
            (id, name, scope, cron_expression, run_at, enabled, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, schedule.id, schedule.name, schedule.scope, 
            schedule.cron_expression, schedule.run_at, 
            schedule.enabled, schedule.metadata)
    
    return schedule


@app.delete("/api/v1/migrations/locks/{key}")
async def clear_migration_lock(key: str):
    """Clear a stuck migration lock"""
    async with state.admin_pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM admin.migration_locks 
            WHERE resource_key = $1
        """, key)
    
    return {"message": f"Lock {key} cleared"}


@app.get("/api/v1/migrations/{migration_id}")
async def get_migration_by_id(migration_id: str):
    """Get migration status by ID"""
    if migration_id not in state.active_migrations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Migration {migration_id} not found"
        )
    
    migration = state.active_migrations[migration_id]
    return {
        "migration_id": migration.migration_id,
        "status": migration.status,
        "databases_migrated": migration.databases_migrated,
        "schemas_migrated": migration.schemas_migrated,
        "started_at": migration.started_at,
        "completed_at": migration.completed_at,
        "errors": migration.errors,
        "progress": migration.progress,
        "batch_id": migration.batch_id
    }


@app.post("/api/v1/migrations/rollback", response_model=Dict[str, Any])
async def rollback_migration(request: RollbackRequest):
    """Rollback migration to specific version"""
    # Build Flyway rollback command
    cmd = [
        'flyway',
        'undo',
        f'-url=jdbc:postgresql://neo-postgres-us-east:5432/{request.database}',
        f'-schemas={request.schema}',
        f'-target={request.target_version}'
    ]
    
    if request.dry_run:
        cmd.append('-dryRunOutput=/tmp/rollback.sql')
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            return {
                "status": "success",
                "message": f"Rolled back to version {request.target_version}",
                "dry_run": request.dry_run
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Rollback failed: {result.stderr}"
            )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500,
            detail="Rollback operation timed out"
        )


# ============== TENANT ENDPOINTS ==============

@app.post("/api/v1/tenants/{tenant_id}/migrate")
async def migrate_tenant(
    tenant_id: str,
    request: TenantMigrationRequest,
    background_tasks: BackgroundTasks
):
    """Migrate a specific tenant schema"""
    # Find the connection
    connection = None
    for conn in state.migration_manager.connections.values():
        if conn.database == request.database:
            connection = conn
            break
    
    if not connection:
        raise HTTPException(
            status_code=404,
            detail=f"Database {request.database} not found"
        )
    
    # Create schema if needed
    if request.create_schema:
        async with state.admin_pool.acquire() as conn:
            await conn.execute(f"""
                CREATE SCHEMA IF NOT EXISTS {request.schema}
            """)
    
    # Run migration in background
    migration_id = str(uuid.uuid4())
    
    migration = MigrationResponse(
        migration_id=migration_id,
        status="in_progress",
        started_at=datetime.utcnow()
    )
    
    state.active_migrations[migration_id] = migration
    
    background_tasks.add_task(
        migrate_single_tenant,
        migration_id,
        connection,
        request.schema
    )
    # Schedule Keycloak provisioning for this tenant
    if state.keycloak_provisioner is not None:
        background_tasks.add_task(provision_tenant_by_id, tenant_id)
    
    return migration


@app.get("/api/v1/tenants/{tenant_id}/version")
async def get_tenant_schema_version(
    tenant_id: str,
    database: str = Query(...),
    schema: str = Query(...)
):
    """Get current schema version for a tenant"""
    # Find the connection
    connection = None
    for conn in state.migration_manager.connections.values():
        if conn.database == database:
            connection = conn
            break
    
    if not connection:
        raise HTTPException(
            status_code=404,
            detail=f"Database {database} not found"
        )
    
    status = await state.migration_manager.get_migration_status(connection, schema)
    
    return {
        "tenant_id": tenant_id,
        "database": database,
        "schema": schema,
        "current_version": status.current_version,
        "pending_migrations": len(status.pending_migrations),
        "status": status.status
    }


# ============== KEYCLOAK PROVISIONING ==============

async def provision_missing_tenants() -> None:
    """Provision Keycloak realms/clients for tenants missing credentials."""
    if state.admin_pool is None or state.keycloak_provisioner is None:
        logger.warning("Provisioning skipped: admin_pool or keycloak_provisioner not ready")
        return

    try:
        async with state.admin_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, slug, external_auth_realm, external_auth_metadata
                FROM admin.tenants
                WHERE external_auth_provider = 'keycloak'
                  AND (
                        external_auth_realm IS NULL OR external_auth_realm = ''
                        OR (external_auth_metadata ->> 'client_secret') IS NULL
                      )
                """
            )

            if not rows:
                logger.info("No tenants require Keycloak provisioning")
                return

            for row in rows:
                tenant_id: str = row["id"]
                tenant_slug: str = row["slug"]
                realm: str = f"tenant-{tenant_slug}"

                try:
                    ensured_realm, client_id, client_secret = await state.keycloak_provisioner.ensure_realm_and_client(realm)

                    await conn.execute(
                        """
                        UPDATE admin.tenants
                        SET external_auth_realm = $2,
                            external_auth_metadata = COALESCE(external_auth_metadata, '{}'::jsonb)
                                || jsonb_build_object(
                                    'realm', $2,
                                    'client_id', $3,
                                    'client_secret', $4
                                   ),
                            updated_at = NOW()
                        WHERE id = $1
                        """,
                        tenant_id,
                        ensured_realm,
                        client_id,
                        client_secret,
                    )

                    logger.info(
                        f"Provisioned Keycloak for tenant {tenant_slug}: realm={ensured_realm}, client_id={client_id}"
                    )
                except Exception as e:
                    logger.error(f"Failed to provision Keycloak for tenant {tenant_slug}: {e}")

    except Exception as outer:
        logger.error(f"Provisioning task encountered an error: {outer}")


@app.post("/api/v1/tenants/{tenant_id}/provision-auth", response_model=Dict[str, Any])
async def provision_tenant_auth(tenant_id: str) -> Dict[str, Any]:
    """Provision Keycloak realm/client for a single tenant and store credentials."""
    if state.admin_pool is None or state.keycloak_provisioner is None:
        raise HTTPException(status_code=500, detail="Service not ready")

    async with state.admin_pool.acquire() as conn:
        tenant = await conn.fetchrow(
            """
            SELECT id, slug FROM admin.tenants
            WHERE id = $1 AND external_auth_provider = 'keycloak'
            """,
            tenant_id,
        )
        if tenant is None:
            raise HTTPException(status_code=404, detail="Tenant not found or not using Keycloak")

        tenant_slug: str = tenant["slug"]
        realm: str = f"tenant-{tenant_slug}"

        try:
            ensured_realm, client_id, client_secret = await state.keycloak_provisioner.ensure_realm_and_client(realm)

            await conn.execute(
                """
                UPDATE admin.tenants
                SET external_auth_realm = $2,
                    external_auth_metadata = COALESCE(external_auth_metadata, '{}'::jsonb)
                        || jsonb_build_object(
                            'realm', $2,
                            'client_id', $3,
                            'client_secret', $4
                           ),
                    updated_at = NOW()
                WHERE id = $1
                """,
                tenant_id,
                ensured_realm,
                client_id,
                client_secret,
            )

            return {
                "tenant_id": tenant_id,
                "realm": ensured_realm,
                "client_id": client_id,
                "stored": True,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Provisioning failed: {e}")


async def provision_tenant_by_id(tenant_id: str) -> None:
    """Helper to provision a single tenant by id without HTTP context."""
    if state.admin_pool is None or state.keycloak_provisioner is None:
        return
    async with state.admin_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, slug FROM admin.tenants
            WHERE id = $1 AND external_auth_provider = 'keycloak'
            """,
            tenant_id,
        )
        if row is None:
            return
        tenant_slug: str = row["slug"]
        realm: str = f"tenant-{tenant_slug}"
        ensured_realm, client_id, client_secret = await state.keycloak_provisioner.ensure_realm_and_client(realm)
        await conn.execute(
            """
            UPDATE admin.tenants
            SET external_auth_realm = $2,
                external_auth_metadata = COALESCE(external_auth_metadata, '{}'::jsonb)
                    || jsonb_build_object(
                        'realm', $2,
                        'client_id', $3,
                        'client_secret', $4
                       ),
                updated_at = NOW()
            WHERE id = $1
            """,
            tenant_id,
            ensured_realm,
            client_id,
            client_secret,
        )


# ============== BACKGROUND TASKS ==============

async def execute_deployment(deployment_id: str, request: DeploymentRequest):
    """Execute deployment in background"""
    deployment = state.active_deployments[deployment_id]
    deployment.status = DeploymentStatus.IN_PROGRESS
    
    try:
        # Run deployment script
        cmd = ["/app/scripts/deploy-with-flyway.sh"]
        
        if request.dry_run:
            cmd.append("--dry-run")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            deployment.status = DeploymentStatus.COMPLETED
            deployment.services_deployed = request.services
        else:
            deployment.status = DeploymentStatus.FAILED
            deployment.errors.append(result.stderr)
    
    except subprocess.TimeoutExpired:
        deployment.status = DeploymentStatus.FAILED
        deployment.errors.append("Deployment timed out")
    
    except Exception as e:
        deployment.status = DeploymentStatus.FAILED
        deployment.errors.append(str(e))
    
    finally:
        deployment.completed_at = datetime.utcnow()


async def execute_migration(migration_id: str, request: MigrationRequest):
    """Execute migration in background"""
    migration = state.active_migrations[migration_id]
    migration.status = "in_progress"
    
    try:
        if request.scope == MigrationScope.ALL:
            await state.migration_manager.migrate_all(request.batch_size)
            migration.status = "completed"
        
        elif request.scope == MigrationScope.SINGLE:
            if not request.database or not request.schema:
                raise ValueError("Database and schema required for single migration")
            
            # Find connection
            connection = None
            for conn in state.migration_manager.connections.values():
                if conn.database == request.database:
                    connection = conn
                    break
            
            if connection:
                success = await state.migration_manager.migrate_database(connection, request.schema)
                migration.status = "completed" if success else "failed"
                migration.databases_migrated = 1 if success else 0
                migration.schemas_migrated = 1 if success else 0
        
        else:
            # Handle other scopes
            migration.status = "completed"
    
    except Exception as e:
        migration.status = "failed"
        migration.errors.append(str(e))
    
    finally:
        migration.completed_at = datetime.utcnow()


async def migrate_single_tenant(migration_id: str, connection: DatabaseConnection, schema: str):
    """Migrate a single tenant schema"""
    migration = state.active_migrations[migration_id]
    
    try:
        success = await state.migration_manager.migrate_database(connection, schema)
        
        if success:
            migration.status = "completed"
            migration.schemas_migrated = 1
        else:
            migration.status = "failed"
    
    except Exception as e:
        migration.status = "failed"
        migration.errors.append(str(e))
    
    finally:
        migration.completed_at = datetime.utcnow()


# ============== MAIN ==============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )