# NeoMultiTenant Platform

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/FastAPI-0.115+-green.svg" alt="FastAPI Version">
  <img src="https://img.shields.io/badge/PostgreSQL-17+-blue.svg" alt="PostgreSQL Version">
  <img src="https://img.shields.io/badge/Redis-7+-red.svg" alt="Redis Version">
  <img src="https://img.shields.io/badge/Keycloak-26+-orange.svg" alt="Keycloak Version">
  <img src="https://img.shields.io/badge/License-Proprietary-lightgrey.svg" alt="License">
</p>

**Ultra-Advanced Multi-Tenant, Multi-Region, Multi-Database Enterprise Platform**

A robust, enterprise-grade multi-tenant platform designed for ultra-scalability, high performance, and advanced security. Built with modern async Python, PostgreSQL, Redis, and Keycloak integration, supporting schema-based and database-based multi-tenancy with comprehensive RBAC (Role-Based Access Control) system but actually work like permission based access control including custom permissions per user.

## 🌟 Key Features

### Multi-Tenancy & Scalability
- **Multi-Tenant Architecture**: Complete data isolation with schema-based or database-based tenancy
- **Multi-Region Support**: Global deployment with geo-distributed databases
- **📊 Multi-Database Strategy**: Supports multiple PostgreSQL instances with intelligent routing
- **⚡ Ultra-High Performance**: Sub-millisecond permission checks with intelligent caching
- **🔄 Dynamic Tenant Provisioning**: Automatic tenant schema creation and management

### Authentication & Security
- **External Authentication**: Keycloak integration with multi-realm support
- **🛡️ Advanced RBAC**: Hierarchical role-based access control with fine-grained permissions
- **🔒 Enterprise Security**: JWT validation, OAuth2, MFA support, audit logging
- **🏛️ Multi-Realm Support**: Admin and tenant-specific realm configurations
- **📝 Comprehensive Audit**: Tamper-proof audit logs with integrity validation

### Technology Stack
- **🐍 Python 3.13+**: Modern async/await patterns with FastAPI
- **🚀 FastAPI**: High-performance async web framework
- **🐘 PostgreSQL 17+**: Advanced database with JSONB, full-text search, and UUIDv7
- **⚡ Redis 7+**: High-performance caching with automatic invalidation
- **🔑 Keycloak 26+**: Enterprise identity and access management
- **🐳 Docker**: Containerized deployment with infrastructure automation

## 🏗️ Architecture Overview

### Project Structure

```
NeoMultiTenant/
├── NeoInfrastructure/             # Infrastructure & database management
│   ├── docker/                    # Docker compose files
│   │   ├── postgres/              # PostgreSQL init scripts (US/EU regions)
│   │   └── keycloak/              # Keycloak themes and providers
│   ├── migrations/                # Database migration system
│   │   ├── api/                   # Deployment API service
│   │   ├── flyway/                # SQL migration files
│   │   │   ├── admin/             # Admin DB migrations (V1001-V1010)
│   │   │   ├── platform/          # Platform common (V0001)
│   │   │   └── regional/          # Region-specific migrations
│   │   ├── orchestrator/          # Migration engines
│   │   └── seeds/                 # Initial data seeding
│   ├── scripts/                   # Infrastructure automation
│   ├── deploy.sh                  # Main deployment script
│   ├── stop.sh                    # Stop all services
│   └── reset.sh                   # Reset infrastructure
├── NeoAdmin/                      # Admin dashboard (React/Next.js)
├── NeoAdminApi/                   # Admin API service (FastAPI)
├── NeoTenantAdmin/                # Tenant admin interface (React/Next.js)
├── NeoTenantApi/                  # Tenant API service (FastAPI)
├── NeoTenantFrontend/             # Tenant frontend (React/Next.js)
├── NeoMarketingFrontend/          # Marketing website (React/Next.js)
├── deploy.dev.sh                  # Master deployment script
├── README.md                      # Project documentation
└── CLAUDE.md                      # AI assistant guidelines
```

### Service Architecture

The platform is designed as a microservices architecture with clear separation of concerns:

#### **Core Services**

**🏗️ NeoInfrastructure**
- Enterprise-grade Flyway database migrations with Python orchestration
- Multi-region PostgreSQL setup (e.g. US East, EU West)
- Global database for platform administration.
- Regional database provisioning for tenant deployments.
- Keycloak configuration, themes, and SSL management
- Infrastructure automation and deployment scripts

**NeoAdminApi**
- Platform administration API
- Tenant management and provisioning
- User and organization management
- Subscription and billing operations
- System monitoring and health checks

**NeoTenantApi**
- Tenant-specific business logic API
- User authentication and authorization
- RBAC and permission management
- Tenant data operations
- Integration endpoints

#### **Frontend Services**

**👑 NeoAdmin**
- Platform administration dashboard
- Super admin interface
- Tenant management UI
- System monitoring and analytics
- Billing and subscription management

**NeoTenantAdmin**
- Tenant administrator interface
- User and role management
- Tenant settings and configuration
- Team and organization management

**NeoTenantFrontend**
- End-user application interface
- Tenant-specific user experience
- Permission-based UI rendering
- Real-time features and notifications

**🌐 NeoMarketingFrontend**
- Public marketing website
- Landing pages and documentation
- Pricing and feature information
- Lead generation and signup flows

#### **Deployment Strategies**

**Development Mode:**
```bash
# All services together (infrastructure + migrations)
./deploy.dev.sh

# Or deploy with seed data
cd NeoInfrastructure
./deploy.sh --seed

# Individual service deployment
# See "Option 2: Individual Service Development" section below
```

**Production Mode:**
```bash
# Orchestrated deployment
TODO: Add production deployment scripts. 
- AWS, K8s, Coolify, Hetzner, etc.
```

### Infrastructure Architecture (NeoInfrastructure)

The NeoInfrastructure module provides enterprise-grade infrastructure management with automated provisioning and multi-region support:

#### **Database Structure**

```
┌─ US East Region (Primary)                    ┌─ EU West Region (GDPR)
│  ├─ neofast_admin (Global)                   │  ├─ neofast_shared_eu
│  │  ├─ admin schema (50+ tables)             │  │  ├─ platform_common schema
│  │  ├─ platform_common schema                │  │  └─ tenant_template schema  
│  │  └─ keycloak schema                       │  └─ neofast_analytics_eu
│  ├─ neofast_shared_us                        │     ├─ platform_common schema
│  │  ├─ platform_common schema                │     └─ analytics schema
│  │  └─ tenant_template schema                │
│  └─ neofast_analytics_us                     │
│     ├─ platform_common schema                │
│     └─ analytics schema                      │
```

#### **Migration System**

**Enterprise Flyway Configuration:**
```bash
NeoInfrastructure/migrations/
├── flyway/conf/                # Region-specific configurations
│   ├── admin-complete.conf     # Admin database config
│   ├── admin-schema.conf       # Admin schema only
│   ├── platform-common.conf    # Platform common schema
│   ├── tenant-template-schema.conf  # Tenant template
│   └── analytics-schema.conf   # Analytics schema
├── flyway/admin/               # Admin database migrations
│   ├── V1001__admin_schema_types.sql
│   ├── V1002__admin_identity_access.sql
│   ├── V1003__admin_organization_tenant.sql
│   ├── V1004__admin_subscription_billing.sql
│   ├── V1005__admin_user_roles_tenant_mgmt.sql
│   ├── V1006__admin_monitoring_security.sql
│   ├── V1007__admin_migration_management.sql
│   ├── V1008__add_batch_error_and_dynamic_columns.sql
│   ├── V1009__add_migration_rollback_tracking.sql
│   └── V1010__populate_database_registry.sql
├── flyway/platform/            # Platform-wide common schemas
│   └── V0001__platform_common_schema.sql
└── flyway/regional/            # Region-specific migrations
    ├── shared/V2001__tenant_template_schema.sql
    └── analytics/V3001__analytics_base_schema.sql
```

**One-Command Deployment:**
```bash
cd NeoInfrastructure
./deploy.sh           # Deploy infrastructure + run migrations
./deploy.sh --seed    # Deploy + seed initial data
```

**Deployment API:**
The Deployment API (port 8000) automatically runs migrations on startup and provides endpoints for migration management.

#### **Regional Database Initialization**

**US Region Databases:**
```sql
-- Auto-created during container startup
neofast_admin         # Platform administration (Global)
neofast_shared_us     # Tenant templates (US region)  
neofast_analytics_us  # Analytics and reporting (US)
```

**EU Region Databases:**
```sql
-- GDPR-compliant databases
neofast_shared_eu     # Tenant templates (EU region)
neofast_analytics_eu  # Analytics and reporting (EU)
```

#### **Infrastructure Scripts**

**Quick Start Scripts:**
```bash
./deploy.sh           # Deploy infrastructure + migrations
./stop.sh             # Stop all services
./reset.sh            # Reset and rebuild everything
./reset.sh --clean-data --force  # Full cleanup without prompts

# Keycloak utilities
./scripts/keycloak/fix-keycloak-ssl.sh       # Fix Keycloak SSL issues
./scripts/keycloak/keycloak-disable-ssl.sh   # Disable SSL for development
```

**Migration Scripts:**
```bash
cd migrations
docker-compose -f docker-compose.api.yml up -d  # Start migration API
./scripts/deploy-with-flyway.sh                 # Manual Flyway deployment
./scripts/clean-migration.sh                    # Clean migration artifacts
```

#### **Keycloak Configuration**

**Multi-Realm Setup:**
- `NeoAdmin` - Platform administration realm
- `tenant-{slug}` - Dynamic tenant-specific realms
- Custom themes and providers in `/keycloak/themes/`
- SSL configuration and certificate management

### Database Architecture

#### Schema Design
The platform uses a sophisticated multi-schema PostgreSQL architecture:

**Platform Schemas:**
- `platform_common`: Shared functions, types, and utilities
- `admin`: Platform administration and tenant management
- `tenant_template`: Template schema for new tenants

**Multi-Tenancy Strategies:**
1. **Schema-based**: Each tenant gets its own PostgreSQL schema
2. **Database-based**: Each tenant gets its own database
3. **Hybrid**: Mix of both based on tenant tier and requirements

#### Core Tables Structure

**Admin Schema (Platform Management):**
```sql
-- Platform Identity & Access Management
admin.platform_users             # Platform administrators and users
admin.platform_permissions       # System-wide permissions
admin.platform_roles             # Platform roles (system, platform, tenant levels)
admin.role_permissions           # Role-permission junction table
admin.platform_user_roles        # User-role assignments
admin.platform_user_permissions  # Direct user permissions override

-- Organization & Tenant Management  
admin.organizations               # Customer organizations
admin.regions                    # Geographic deployment regions
admin.database_connections       # Database connection registry
admin.tenants                    # Tenant instances with region assignment
admin.tenant_contacts            # Tenant contact information
admin.tenant_quotas              # Tenant resource quotas
admin.tenant_settings            # Tenant configuration settings
admin.tenant_access_grants       # Cross-tenant access permissions

-- Subscription & Billing
admin.subscription_plans          # Available subscription plans
admin.plan_quotas                # Plan feature quotas and limits
admin.tenant_subscriptions       # Active tenant subscriptions
admin.subscription_addons        # Subscription add-ons
admin.invoices                   # Billing invoices
admin.invoice_line_items         # Invoice line item details
admin.payment_transactions       # Payment processing records
admin.billing_alerts            # Billing notifications and alerts

-- Infrastructure & Monitoring
admin.system_alerts             # System monitoring alerts
admin.api_rate_limits           # API rate limiting configuration
```

**Tenant Template Schema (Regional Databases):**
```sql
-- User Management
tenant_template.users             # Tenant users with external auth integration
tenant_template.teams             # Hierarchical team organization
tenant_template.team_members      # Team membership with roles

-- RBAC System
tenant_template.permissions       # Tenant-specific permissions
tenant_template.roles            # Tenant roles with scope levels
tenant_template.role_permissions  # Role-permission assignments
tenant_template.user_roles        # User-role assignments
tenant_template.user_permissions  # Direct user permission overrides

-- Tenant Management
tenant_template.settings          # Tenant configuration and preferences  
tenant_template.invitations       # User invitations and onboarding
```

### Authentication Flow

#### Keycloak Integration Patterns

**Multi-Realm Mode (Enterprise)**
```
Keycloak
├── NeoAdmin (realm for Neo Platform)
├── tenant-acme (realm for ACME Corp)
├── tenant-globex (realm for Globex Inc)
├── tenant-initech (realm for Initech Ltd)
```

#### Authentication Flow Sequence
1. **Frontend** → Obtains JWT from Keycloak (tenant-specific realm)
2. **API Request** → JWT sent in Authorization header
3. **FastAPI Middleware** → Validates JWT with realm's public key
4. **User Sync** → User upserted to PostgreSQL with tenant context
5. **Permission Cache** → User permissions cached in Redis
6. **Authorization** → Permissions checked against PostgreSQL/Redis

## 🚀 Quick Start Guide

### Prerequisites

- **Python 3.13+**
- **PostgreSQL 17+** 
- **Redis 7+**
- **Keycloak 26+**
- **Docker & Docker Compose**

### Option 1: Full Development Environment (All Services)

1. **Clone the repository**
```bash
git clone <repository-url>
cd NeoMultiTenant
```

2. **Deploy the complete platform**
```bash
# This single command:
# - Creates necessary directories and .env file
# - Starts PostgreSQL, Redis, Keycloak containers
# - Deploys the Migration API
# - Runs all database migrations automatically
./deploy.dev.sh

# Or deploy with initial seed data
cd NeoInfrastructure
./deploy.sh --seed
```

3. **Verify deployment**
```bash
# Check service health
curl http://localhost:8000/health

# View migration status
curl http://localhost:8000/api/v1/migrations/status
```

### Option 2: Individual Service Development

**Start Infrastructure Only:**
```bash
cd NeoInfrastructure
docker-compose -f docker/docker-compose.infrastructure.yml up -d

# Then start the deployment API (which runs migrations automatically)
cd migrations
docker-compose -f docker-compose.api.yml up -d
```

**Run Individual Services:**
```bash
# Admin API (Port 8001)
cd NeoAdminApi
docker-compose up -d
# or locally: uvicorn src.main:app --reload --port 8001

# Tenant API (Port 8002)  
cd NeoTenantApi
docker-compose up -d
# or locally: uvicorn src.main:app --reload --port 8002

# Admin Dashboard (Port 3001)
cd NeoAdmin
npm run dev
# or: docker-compose up -d

# Tenant Admin (Port 3002)
cd NeoTenantAdmin
npm run dev
# or: docker-compose up -d

# Tenant Frontend (Port 3003)
cd NeoTenantFrontend
npm run dev
# or: docker-compose up -d

# Marketing Site (Port 3000)
cd NeoMarketingFrontend
npm run dev
# or: docker-compose up -d
```

### Access Points

**API Services:**
- **Deployment API**: http://localhost:8000/docs (Migration management)
- **Admin API**: http://localhost:8001/docs (Platform management) 
- **Tenant API**: http://localhost:8002/docs (Tenant operations)

**Frontend Applications:**
- **Marketing Site**: http://localhost:3000 (Public website)
- **Admin Dashboard**: http://localhost:3001 (Platform administration)
- **Tenant Admin**: http://localhost:3002 (Tenant management)
- **Tenant Frontend**: http://localhost:3003 (End-user application)

**Infrastructure Services:**
- **Keycloak Admin**: http://localhost:8080 (admin/admin)
- **pgAdmin**: http://localhost:5050 (admin@example.com/admin)
- **RedisInsight**: http://localhost:5601 (Note: changed to avoid port conflict)

## Configuration

### Environment Variables

**Application Settings:**
```bash
# Platform
PROJECT_NAME="NeoMultiTenant"
ENVIRONMENT="development"  # development, staging, production
DEBUG=true
LOG_LEVEL="INFO"

# Service Ports
ADMIN_API_PORT=8001        # NeoAdminApi
TENANT_API_PORT=8002       # NeoTenantApi
ADMIN_UI_PORT=3001         # NeoAdmin
TENANT_ADMIN_PORT=3002     # NeoTenantAdmin
TENANT_UI_PORT=3003        # NeoTenantFrontend
MARKETING_PORT=3000        # NeoMarketingFrontend

# Security
SECRET_KEY="your-super-secret-key-change-in-production"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Database Configuration:**
```bash
# Admin Database (Platform Management) - Only database needed in .env
ADMIN_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/neofast_admin"
ADMIN_DATABASE_POOL_SIZE=20

# All other databases are managed through admin.database_connections table
# Including:
# - Regional shared databases (neofast_shared_us, neofast_shared_eu)
# - Analytics databases (neofast_analytics_us, neofast_analytics_eu)
# - Tenant-specific databases (dynamically created)
# - Replica databases (for read scaling)
# - Backup databases (for disaster recovery)
```

**Redis Configuration:**
```bash
REDIS_URL="redis://localhost:6379/0"
REDIS_MAX_CONNECTIONS=50
REDIS_PASSWORD="redis"
```

**Keycloak Configuration:**
```bash
# Multi-Realm Mode (Default)
KEYCLOAK_URL="http://localhost:8080"
KEYCLOAK_REALM="NeoAdmin"        # Admin platform realm
KEYCLOAK_REALM_PATTERN="{schema-name}"  # Dynamic realm per tenant use {schema-name} which cannot be changed.
KEYCLOAK_MASTER_REALM="master"
KEYCLOAK_ADMIN="admin"
KEYCLOAK_PASSWORD="admin"

# Service-specific clients
ADMIN_API_CLIENT_ID="NeoAdminApi"
TENANT_API_CLIENT_ID="NeoTenantApi"
ADMIN_UI_CLIENT_ID="NeoAdmin-ui"
TENANT_UI_CLIENT_ID="neo-tenant-ui"
```

### Multi-Tenancy Configuration

**Tenant Provisioning:**
```bash
# Tenancy Strategy (configured per tenant in admin.tenants table)
MULTI_TENANT_MODE=true
DEFAULT_REGION="us-east-1"          # Default region for new tenants
DEFAULT_DEPLOYMENT_TYPE="schema"    # Default: schema, database, dedicated

# Automatic Provisioning
AUTO_PROVISION_TENANTS=true
TENANT_SCHEMA_TEMPLATE="tenant_template"

# Database assignment is managed through admin.database_connections
# Tenants are assigned databases based on:
# - Region preference (GDPR compliance, latency)
# - Deployment type (schema, database, dedicated)
# - Resource requirements (plan tier, expected load)
# - Database capacity and health status
```

## 🗄️ Database Management

### Dynamic Migration Management

The platform uses a **programmatic migration system** that extends Flyway with dynamic tracking and orchestration capabilities for managing migrations across thousands of tenant schemas.

#### **Migration Architecture**

**Multi-Level Migration Tracking:**
1. **Global Migrations** - Admin database and platform-wide changes
2. **Regional Migrations** - Region-specific shared databases  
3. **Template Migrations** - Tenant template schema updates
4. **Tenant Migrations** - Individual tenant schema migrations

**Migration Tracking System:**
```sql
-- Flyway tracks migrations per database/schema in flyway_schema_history table
-- Extended with custom tracking for multi-tenant management:

-- Query pending migrations for all tenant schemas
SELECT 
    t.slug as tenant,
    t.schema_name,
    dc.database_name,
    fsh.version,
    fsh.installed_on,
    fsh.success
FROM admin.tenants t
JOIN admin.database_connections dc ON t.database_connection_id = dc.id
LEFT JOIN {database}.{schema}.flyway_schema_history fsh 
    ON fsh.installed_by IS NOT NULL
WHERE t.status = 'active'
ORDER BY t.slug, fsh.installed_rank;
```

#### **Programmatic Migration Execution**

**Python Migration Orchestrator:**
```python
# NeoInfrastructure Migration Manager
class MigrationManager:
    async def apply_migrations(self):
        """Apply migrations dynamically across all databases and schemas"""
        
        # 1. Apply admin database migrations (auto on deployment)
        await self.migrate_admin_database()
        
        # 2. Apply regional database migrations
        for region in await self.get_active_regions():
            await self.migrate_regional_databases(region)
        
        # 3. Apply tenant schema migrations
        for tenant in await self.get_active_tenants():
            await self.migrate_tenant_schema(tenant)
    
    async def migrate_tenant_schema(self, tenant):
        """Migrate individual tenant schema with tracking"""
        
        # Get tenant's database connection
        db_conn = await self.get_database_connection(tenant.database_connection_id)
        
        # Check current migration version
        current_version = await self.get_schema_version(db_conn, tenant.schema_name)
        
        # Apply pending migrations
        pending = await self.get_pending_migrations(current_version, 'tenant')
        for migration in pending:
            await self.apply_migration(db_conn, tenant.schema_name, migration)
            await self.update_migration_status(tenant.id, migration)
```

**Migration API Endpoints:**
```python
# NeoAdminApi Migration Endpoints
@router.post("/api/v1/admin/migrations/apply")
async def apply_migrations(scope: str = "all"):
    """Apply pending migrations programmatically"""
    manager = MigrationManager()
    
    if scope == "admin":
        return await manager.migrate_admin_database()
    elif scope == "regional":
        return await manager.migrate_all_regional_databases()
    elif scope == "tenants":
        return await manager.migrate_all_tenant_schemas()
    else:  # all
        return await manager.apply_migrations()

@router.get("/api/v1/admin/migrations/status")
async def get_migration_status():
    """Get migration status across all databases and schemas"""
    return {
        "admin": await get_admin_migration_status(),
        "regional": await get_regional_migration_status(),
        "tenants": await get_tenant_migration_status()
    }

@router.post("/api/v1/admin/tenants/{tenant_id}/migrate")
async def migrate_tenant(tenant_id: UUID):
    """Apply migrations to specific tenant schema"""
    tenant = await get_tenant(tenant_id)
    return await MigrationManager().migrate_tenant_schema(tenant)
```

#### **Automatic Migration Triggers**

**Event-Driven Migrations:**
```python
# Automatically apply migrations on specific events

# 1. New tenant provisioning
async def provision_tenant(tenant_data):
    tenant = await create_tenant(tenant_data)
    await create_tenant_schema(tenant)
    await apply_tenant_template_migrations(tenant)
    return tenant

# 2. Region activation
async def activate_region(region_id):
    region = await enable_region(region_id)
    await apply_regional_migrations(region)
    return region

# 3. Database connection activation
async def activate_database_connection(database_connection_id):
    database_connection = await enable_database_connection(database_connection_id)
    await apply_database_connection_migrations(database_connection)
    return database_connection

# 4. Scheduled migration batches
@scheduled_task(cron="0 2 * * *")  # 2 AM daily
async def apply_pending_migrations():
    await MigrationManager().apply_migrations()
```

#### **Migration Monitoring & Safety**

**Migration Health Checks:**
```sql
-- Monitor migration status across all schemas
CREATE OR REPLACE VIEW admin.migration_health AS
SELECT 
    'admin' as scope,
    COUNT(*) as total_schemas,
    SUM(CASE WHEN latest_migration = expected_version THEN 1 ELSE 0 END) as up_to_date,
    SUM(CASE WHEN latest_migration < expected_version THEN 1 ELSE 0 END) as pending
FROM (
    SELECT schema_name, MAX(version) as latest_migration
    FROM flyway_schema_history
    GROUP BY schema_name
) schema_versions;

-- Alert on migration failures
SELECT 
    t.slug,
    t.schema_name,
    fsh.version,
    fsh.error_message,
    fsh.installed_on
FROM admin.tenants t
JOIN flyway_schema_history fsh ON fsh.success = false
WHERE fsh.installed_on > NOW() - INTERVAL '24 hours';
```

**Migration Safety Features:**
1. **Locking Mechanism** - Prevent concurrent migrations on same schema
2. **Rollback Support** - Track and revert failed migrations
3. **Dry Run Mode** - Test migrations without applying
4. **Batch Processing** - Migrate tenants in controlled batches
5. **Health Monitoring** - Track migration success/failure rates

#### **CLI Migration Tools**

```bash
# NeoInfrastructure Migration CLI
cd NeoInfrastructure/migrations

# Apply all pending migrations
./migrate.py apply --scope all

# Check migration status
./migrate.py status --detailed

# Migrate specific tenant
./migrate.py tenant --slug acme-corp

# Migrate with safety checks
./migrate.py apply --dry-run --batch-size 10

# Rollback last migration
./migrate.py rollback --scope tenant --version V001
```

### Multi-Region Database Setup

**Regional Configuration:**
- **US Region**: Primary databases for North American tenants
- **EU Region**: GDPR-compliant databases for European tenants
- **Analytics**: Separate analytics databases for reporting

**Centralized Database Registry:**
All databases are managed through the `admin.database_connections` table with connection pooling and health monitoring:

```sql
-- Database connections are automatically populated during deployment
SELECT 
    dc.connection_name,
    dc.connection_type,
    dc.host || ':' || dc.port || '/' || dc.database_name as connection_url,
    r.code as region,
    dc.is_active,
    dc.is_healthy,
    dc.pool_min_size,
    dc.pool_max_size
FROM admin.database_connections dc
JOIN admin.regions r ON dc.region_id = r.id
WHERE dc.is_active = true;

-- Example results:
-- neofast-admin-primary    | primary   | neo-postgres-us-east:5432/neofast_admin        | us-east-1
-- neofast-shared-us-primary| primary   | neo-postgres-us-east:5432/neofast_shared_us    | us-east-1  
-- neofast-analytics-us     | analytics | neo-postgres-us-east:5432/neofast_analytics_us | us-east-1
-- neofast-shared-eu-primary| primary   | neo-postgres-eu-west:5432/neofast_shared_eu    | eu-west-1
-- neofast-analytics-eu     | analytics | neo-postgres-eu-west:5432/neofast_analytics_eu | eu-west-1
```

**Connection Types:**
- `primary` - Main operational databases
- `replica` - Read replicas for scaling  
- `analytics` - Analytics and reporting databases
- `backup` - Backup and disaster recovery databases

**Dynamic Database Management:**
```sql
-- Services query database connections by type and region
SELECT * FROM admin.database_connections 
WHERE connection_type = 'primary' 
AND region_id = (SELECT id FROM admin.regions WHERE code = 'us-east-1')
AND is_active = true AND is_healthy = true;

-- Tenants are assigned databases based on region and deployment type
SELECT t.slug, t.deployment_type, dc.connection_name, dc.host, dc.database_name
FROM admin.tenants t
JOIN admin.database_connections dc ON t.database_connection_id = dc.id
WHERE t.status = 'active';
```

### Centralized Database Management

The platform uses a **centralized database management system** where only the admin database connection is configured in environment variables. All other databases are dynamically managed through the `admin.database_connections` table.

#### **Architecture Benefits:**

1. **Scalability**: Add new databases/regions without service restarts
2. **Security**: Database credentials managed centrally and securely  
3. **Health Monitoring**: Automatic health checks and failover
4. **Connection Pooling**: Optimized connection management per database
5. **Multi-Region Support**: Intelligent database routing by region

#### **Database Connection Management:**

**Environment Configuration (Minimal):**
```bash
# Only admin database needed in .env
ADMIN_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/neofast_admin"

# All other connections managed via admin.database_connections table
```

**Service Connection Logic:**
```python
# Services fetch database connections dynamically
async def get_database_connection(connection_type: str, region_code: str = None):
    """Get database connection from registry"""
    query = """
    SELECT dc.* FROM admin.database_connections dc
    JOIN admin.regions r ON dc.region_id = r.id  
    WHERE dc.connection_type = $1 
    AND dc.is_active = true 
    AND dc.is_healthy = true
    AND ($2 IS NULL OR r.code = $2)
    ORDER BY dc.consecutive_failures ASC
    LIMIT 1
    """
    return await admin_db.fetch_one(query, connection_type, region_code)

# Example usage
tenant_db = await get_database_connection('primary', 'us-east-1')
analytics_db = await get_database_connection('analytics', 'eu-west-1') 
```

**Health Monitoring:**
```sql
-- Automatic health checks update connection status
UPDATE admin.database_connections 
SET 
    is_healthy = $1,
    last_health_check = NOW(),
    consecutive_failures = CASE WHEN $1 THEN 0 ELSE consecutive_failures + 1 END
WHERE id = $2;

-- Disable unhealthy connections
UPDATE admin.database_connections 
SET is_active = false 
WHERE consecutive_failures >= max_consecutive_failures;
```

#### **Tenant Database Assignment:**

**Schema-based Tenancy:**
```sql
-- Tenant uses existing shared database with unique schema
INSERT INTO admin.tenants (slug, schema_name, database_connection_id, deployment_type)
VALUES ('acme', 'tenant_acme', 
    (SELECT id FROM admin.database_connections WHERE connection_name = 'neofast-shared-us-primary'),
    'schema');
```

**Database-based Tenancy:**
```sql
-- Tenant gets dedicated database
INSERT INTO admin.database_connections (connection_name, connection_type, host, database_name, region_id)
VALUES ('tenant-acme-primary', 'primary', 'neo-postgres-us-east', 'tenant_acme', 
    (SELECT id FROM admin.regions WHERE code = 'us-east-1'));

INSERT INTO admin.tenants (slug, database_connection_id, deployment_type)
VALUES ('acme', (SELECT id FROM admin.database_connections WHERE connection_name = 'tenant-acme-primary'), 'database');
```

## Security & Authentication

### Keycloak Setup

**1. Single Realm Configuration:**
```bash
# Create realm
./scripts/setup-keycloak.sh

# Configure client
Client ID: neofast-api
Access Type: confidential
Standard Flow: enabled
Direct Access Grants: enabled
```

**2. Multi-Realm Configuration:**
For enterprise multi-tenancy, each tenant gets its own realm:
```bash
# Tenant realm naming pattern
tenant-{slug}  # e.g., tenant-acme, tenant-globex

# Automatic realm creation
POST /api/v1/admin/tenants
{
  "name": "ACME Corporation",
  "slug": "acme",
  "create_keycloak_realm": true
}
```

### RBAC System

**Permission Structure:**
```
resource.action.scope
├── users.read.own      # Read own user data
├── users.write.team    # Modify team members
├── users.delete.tenant # Delete any user in tenant
└── admin.*.*          # All admin permissions
```

**Role Hierarchy:**
```
System Roles:
├── system_admin       # Platform super admin
├── tenant_admin       # Tenant administrator
├── user_manager       # User management
└── viewer            # Read-only access

Custom Roles:
├── project_manager    # Project-specific permissions
├── team_lead         # Team leadership permissions
└── developer         # Development permissions
```

### Permission Caching Strategy

**Redis Cache Structure:**
```
# User permissions
tenant:{tenant_id}:user:{user_id}:permissions
  └── Set of permission codes: ["users.read.own", "posts.write.team"]

# Role permissions  
tenant:{tenant_id}:role:{role_id}:permissions
  └── Set of permission codes from role

# Permission check cache
tenant:{tenant_id}:check:{user_id}:{permission}:{resource_id}
  └── Boolean result with TTL
```

**Cache Invalidation:**
- User permissions: 5 minutes TTL
- Role permissions: 1 hour TTL  
- Permission checks: 1 minute TTL
- Automatic invalidation on permission/role changes

## 🚀 API Documentation

### API Versioning

The platform supports flexible API versioning:

**Prefix-based (default):**
```
/api/v1/users
/api/v1/tenants
/api/v2/advanced-features
```

**Header-based:**
```bash
curl -H "Accept: application/vnd.api+json;version=1" /users
```

### Core Endpoints

#### **NeoAdminApi** (Port 8001) - Platform Management

**System & Health:**
```
GET  /health                     # Service health check
GET  /metrics                    # Prometheus metrics
GET  /docs                       # OpenAPI documentation
```

**Platform Administration:**
```
GET    /api/v1/admin/tenants           # List all tenants
POST   /api/v1/admin/tenants           # Create new tenant
GET    /api/v1/admin/tenants/{id}      # Get tenant details
PUT    /api/v1/admin/tenants/{id}      # Update tenant
DELETE /api/v1/admin/tenants/{id}      # Delete tenant

GET    /api/v1/admin/organizations     # List organizations
POST   /api/v1/admin/organizations     # Create organization
GET    /api/v1/admin/users             # List platform users
POST   /api/v1/admin/users             # Create platform user
```

**Billing & Subscriptions:**
```
GET    /api/v1/admin/subscriptions     # List subscriptions
POST   /api/v1/admin/subscriptions     # Create subscription
GET    /api/v1/admin/invoices          # List invoices
POST   /api/v1/admin/usage             # Record usage metrics
```

#### **NeoTenantApi** (Port 8002) - Tenant Operations

**Authentication & Users:**
```
POST /api/v1/auth/login               # Tenant user login
GET  /api/v1/auth/me                  # Current user profile
POST /api/v1/auth/refresh             # Refresh token
POST /api/v1/auth/logout              # Logout

GET    /api/v1/users                  # List tenant users
POST   /api/v1/users                  # Create user
GET    /api/v1/users/{id}            # Get user details
PUT    /api/v1/users/{id}            # Update user
DELETE /api/v1/users/{id}            # Delete user
```

**RBAC & Permissions:**
```
GET    /api/v1/roles                  # List roles
POST   /api/v1/roles                  # Create role
GET    /api/v1/permissions            # List permissions
POST   /api/v1/users/{id}/roles       # Assign role to user
GET    /api/v1/users/{id}/permissions # Get user permissions
```

**Teams & Organizations:**
```
GET    /api/v1/teams                  # List teams
POST   /api/v1/teams                  # Create team
GET    /api/v1/teams/{id}/members     # List team members
POST   /api/v1/teams/{id}/members     # Add team member
```

### Response Format

**Standard Success Response:**
```json
{
  "success": true,
  "data": {
    "id": "01234567-89ab-cdef-0123-456789abcdef",
    "name": "John Doe",
    "email": "john@example.com"
  },
  "meta": {
    "timestamp": "2025-01-31T12:00:00Z",
    "version": "v1"
  }
}
```

**Paginated Response:**
```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "pages": 5,
    "has_next": true,
    "has_previous": false
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "email",
      "issue": "Invalid email format"
    }
  },
  "meta": {
    "timestamp": "2025-01-31T12:00:00Z",
    "request_id": "req_123456789"
  }
}
```

## 🧪 Testing

### Test Structure
```
tests/
├── unit/              # Unit tests (mocked dependencies)
├── integration/       # Integration tests (real services)
├── e2e/              # End-to-end tests
├── load/             # Load testing
└── fixtures/         # Test data and utilities
```

### Running Tests

Each service has its own test suite:

**Admin API Tests:**
```bash
cd NeoAdminApi
pytest tests/unit/ -v
pytest tests/integration/ -v --cov=src
```

**Tenant API Tests:**
```bash
cd NeoTenantApi
pytest tests/unit/ -v
pytest tests/integration/ -v --cov=src
```

**Frontend Tests:**
```bash
# Admin Dashboard
cd NeoAdmin
npm test
npm run test:e2e

# Tenant Frontend
cd NeoTenantFrontend
npm test
npm run test:e2e
```

**Infrastructure Tests:**
```bash
# Start test infrastructure
cd NeoInfrastructure
./scripts/start-infrastructure.sh

# Run database migration tests
cd migrations
python -m pytest tests/
```

**Load Testing:**
```bash
# API load testing
cd tests/load
locust -f admin_api_load.py --host=http://localhost:8001
locust -f tenant_api_load.py --host=http://localhost:8002
```

## 📊 Monitoring & Observability

### Structured Logging

**Log Format:**
```json
{
  "timestamp": "2025-01-31T12:00:00Z",
  "level": "INFO",
  "logger": "src.core.auth",
  "message": "User authentication successful",
  "context": {
    "tenant_id": "tenant_123",
    "user_id": "user_456",
    "request_id": "req_789",
    "ip_address": "192.168.1.1"
  },
  "performance": {
    "duration_ms": 15,
    "cache_hit": true
  }
}
```

### Metrics Collection

**Prometheus Metrics:**
```
# Permission check metrics
permission_checks_total{tenant, permission, result}
permission_check_duration_seconds{tenant, permission}

# API metrics  
http_requests_total{method, endpoint, status}
http_request_duration_seconds{method, endpoint}

# Cache metrics
cache_operations_total{operation, result}
cache_hit_ratio{cache_type}

# Database metrics
db_connections_active{pool}
db_query_duration_seconds{query_type}
```

### Health Monitoring

**Health Check Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-31T12:00:00Z",
  "version": "0.1.0",
  "services": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5,
      "connections": 15
    },
    "redis": {
      "status": "healthy", 
      "response_time_ms": 2,
      "memory_usage_mb": 128
    },
    "keycloak": {
      "status": "healthy",
      "response_time_ms": 50
    }
  }
}
```

## 🚦 Performance Optimization

### Performance Targets

- **Permission checks**: < 1ms (with cache)
- **API response time**: < 100ms (p95)
- **Database queries**: < 10ms (simple), < 50ms (complex)
- **Cache hit rate**: > 90% for permissions
- **Concurrent users**: 10,000+
- **Requests per second**: 1,000+ per instance

### Optimization Strategies

**1. Database Optimization:**
```sql
-- JSONB indexes for permissions
CREATE INDEX idx_user_permissions_jsonb ON users USING gin(permissions);

-- Partial indexes for active users
CREATE INDEX idx_active_users ON users(tenant_id) WHERE status = 'active';

-- UUIDv7 for time-ordered UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

**2. Redis Caching:**
```python
# Permission caching with automatic invalidation
@cache_with_invalidation(
    key_pattern="tenant:{tenant_id}:user:{user_id}:permissions",
    ttl=300,  # 5 minutes
    invalidate_on=["user_permissions_changed", "user_roles_changed"]
)
async def get_user_permissions(tenant_id: str, user_id: str):
    return await permission_repository.get_user_permissions(user_id)
```

**3. Connection Pooling:**
```python
# AsyncPG connection pool
DATABASE_POOL_CONFIG = {
    "min_size": 10,
    "max_size": 20,
    "max_queries": 50000,
    "max_inactive_connection_lifetime": 300
}
```

## 🔄 Development Workflow

### Git Workflow

**Branch Strategy:**
```
main                 # Production-ready code
├── develop         # Integration branch
├── feat/user-mgmt  # Feature branches
├── fix/auth-bug    # Bug fixes
└── release/v1.1    # Release branches
```

**Commit Convention:**
```
feat: implement user authentication endpoint
fix: resolve Redis cache invalidation issue  
refactor: optimize permission check queries
docs: update API documentation
test: add integration tests for auth flow
chore: update dependencies
```

### Feature Development Process

**1. Create Feature Branch:**
```bash
git checkout -b feat/feature-name-JIRA-XXX
```

**2. Feature Module Structure:**
```bash
mkdir -p src/features/[feature]/{models,repositories,services,routers,caches}
```

**3. Implementation Order:**
- **Models**: Pydantic models for validation
- **Repository**: Database operations with asyncpg
- **Service**: Business logic and orchestration  
- **Cache**: Redis caching strategies
- **Router**: FastAPI endpoints
- **Tests**: Comprehensive test suite

**4. Quality Checks:**
```bash
# Format and lint
black . && ruff check . && mypy .

# Run tests
pytest --cov=src

# Security check
bandit -r src/
```

### Code Quality Standards

**File Limits:**
- Every file ≤ 400 lines
- Every function ≤ 50 lines
- Single responsibility principle

**Type Safety:**
```python
# Full type hints required
async def get_user(user_id: UUID, tenant_id: str) -> Optional[UserResponse]:
    return await user_repository.get_by_id(user_id)
```

**Error Handling:**
```python
# Specific exceptions, never bare except
try:
    result = await dangerous_operation()
except SpecificDatabaseError as e:
    logger.error("Database operation failed", extra={"error": str(e)})
    raise HTTPException(500, "Operation failed")
```

## 🚀 Deployment

### Production Deployment

**Full Platform Deployment:**
```bash
# Deploy all services
docker-compose -f docker-compose.prod.yml up -d

# Or deploy infrastructure first, then services
cd NeoInfrastructure
./scripts/start-infrastructure.sh
```

**Individual Service Deployment:**
```bash
# Deploy Admin API
cd NeoAdminApi
docker-compose -f docker-compose.prod.yml up -d

# Deploy Tenant API
cd NeoTenantApi
docker-compose -f docker-compose.prod.yml up -d

# Deploy Frontend Services
cd NeoAdmin && docker-compose -f docker-compose.prod.yml up -d
cd NeoTenantFrontend && docker-compose -f docker-compose.prod.yml up -d
```

**Environment Configuration:**
```bash
# Production settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
WORKERS=4

# Security
SECRET_KEY="production-secret-change-me"
ALLOWED_ORIGINS="https://app.example.com"

# Databases (with SSL)
ADMIN_DATABASE_URL="postgresql://user:pass@prod-db:5432/neo_admin?sslmode=require"
US_SHARED_DATABASE_URL="postgresql://user:pass@us-db:5432/neo_shared_us?sslmode=require"
EU_SHARED_DATABASE_URL="postgresql://user:pass@eu-db:5432/neo_shared_eu?sslmode=require"

# Redis (with password)
REDIS_URL="redis://:password@prod-redis:6379/0"

# Keycloak (HTTPS)
KEYCLOAK_URL="https://auth.example.com"
KEYCLOAK_REALM="NeoAdmin"
```

### Infrastructure Requirements

**Minimum Production Setup:**
- **Application**: 2+ instances (load balanced)
- **Database**: PostgreSQL 17+ with replication
- **Cache**: Redis cluster with persistence
- **Keycloak**: 2+ instances (clustered)
- **Load Balancer**: Nginx/HAProxy with SSL termination

**Recommended Production Setup:**
- **Application**: 4+ instances across multiple AZ
- **Database**: Master-replica with automatic failover
- **Cache**: Redis cluster with 3+ nodes
- **Keycloak**: Clustered setup with shared database
- **Monitoring**: Prometheus + Grafana + AlertManager

### Scaling Considerations

**Horizontal Scaling:**
- Stateless application design
- Database connection pooling
- Redis cluster mode
- Load balancer configuration

**Database Scaling:**
- Read replicas for analytics
- Partitioning for large tenants
- Connection pooling per service
- Query optimization

**Multi-Region Deployment:**
- Regional database instances
- CDN for static assets
- Geo-DNS routing
- Cross-region replication

## Troubleshooting

### Common Issues

**1. Database Connection Errors:**
```bash
# Check database connectivity
docker-compose ps postgres
docker-compose logs postgres

# Test connection
psql "postgresql://postgres:postgres@localhost:5432/neofast"
```

**2. Redis Connection Errors:**
```bash
# Check Redis status
docker-compose ps redis
redis-cli -h localhost -p 6379 ping
```

**3. Keycloak Authentication Issues:**
```bash
# Check Keycloak status
curl http://localhost:8080/health/ready

# Verify realm configuration
curl http://localhost:8080/realms/neofast-platform/.well-known/openid_configuration
```

**4. Permission Denied Errors:**
```bash
# Check user permissions in database
psql -c "SELECT * FROM admin.platform_user_permissions WHERE user_id = 'user-uuid';"

# Clear permission cache
redis-cli DEL "tenant:*:user:*:permissions"
```

### Debug Mode

**Enable Debug Logging:**
```bash
export LOG_LEVEL=DEBUG
export ENABLE_SQL_LOGGING=true
uvicorn src.main:app --reload --log-level debug
```

**Health Check Diagnostics:**
```bash
# Check all services
curl http://localhost:8000/health | jq

# Check specific service
curl http://localhost:8000/health | jq '.services.database'
```

## 📚 Additional Resources

### Documentation
- [API Documentation](http://localhost:8000/docs) - Interactive OpenAPI docs
- [Database Schema](./docs/database-schema.md) - Detailed schema documentation
- [Migration Guide](./docs/migrations.md) - Database migration procedures
- [Security Guide](./docs/security.md) - Security best practices

### Development Tools
- **Code Quality**: Black, Ruff, MyPy, Bandit
- **Testing**: Pytest, pytest-asyncio, pytest-cov
- **Database**: pgAdmin, PostgreSQL extensions
- **Caching**: RedisInsight, Redis CLI tools
- **API Testing**: FastAPI docs, Postman collections

### Contributing
1. Fork the repository
2. Create feature branch (`git checkout -b feat/amazing-feature`)
3. Follow code quality standards
4. Add comprehensive tests
5. Update documentation
6. Submit pull request

### Support & Community
- **Issues**: [GitHub Issues](https://github.com/organization/neomultitenant/issues)
- **Discussions**: [GitHub Discussions](https://github.com/organization/neomultitenant/discussions)
- **Documentation**: [Project Wiki](https://github.com/organization/neomultitenant/wiki)

---

## 📝 License

This project is proprietary software. All rights reserved.

**Copyright © 2025 NeoFast Team**

---

<p align="center">
  <strong>Built with ❤️ for enterprise-grade multi-tenancy</strong><br>
  <em>Ultra-scalable • Secure • High-performance</em>
</p>