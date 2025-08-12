# NeoInfrastructure

Multi-region development infrastructure and database migration service for the NeoMultiTenant platform.

## 📁 Directory Structure

```
NeoInfrastructure/
├── docker/                    # Docker compose files and init scripts
│   ├── docker-compose.infrastructure.yml
│   ├── postgres/             # PostgreSQL initialization scripts
│   └── keycloak/             # Keycloak themes and providers
├── migrations/               # Database migration system
│   ├── flyway/              # Flyway migration files
│   ├── orchestrator/        # Python migration orchestration
│   ├── api/                 # Migration API service
│   └── scripts/             # Migration-specific scripts
├── scripts/                  # All operational scripts (organized)
│   ├── deployment/          # Deploy, stop, reset scripts
│   ├── testing/             # Test scripts
│   ├── utilities/           # Helper scripts
│   └── keycloak/            # Keycloak configuration
├── docs/                     # Additional documentation
├── deploy.sh -> scripts/deployment/deploy.sh    # Symlink
├── stop.sh -> scripts/deployment/stop.sh        # Symlink
└── reset.sh -> scripts/deployment/reset.sh      # Symlink
```

## 🏗️ Architecture

- **Multi-Region Setup**: US East (primary) + EU West (GDPR compliant)
- **PostgreSQL**: 2 separate instances for regional data isolation
- **Redis**: Shared cache and session store
- **Keycloak**: Centralized authentication (SSL disabled for dev)
- **Database Migrations**: Enterprise-grade Flyway + Python orchestration

### **Database Structure**
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

### **Schema Breakdown**
- **`admin`**: Platform administration (users, organizations, tenants, billing, regions, monitoring)
- **`platform_common`**: Shared utilities, functions, and types used across all databases
- **`tenant_template`**: Template for tenant-specific data (users, roles, teams, settings)
- **`analytics`**: Event tracking, usage metrics, performance monitoring
- **`keycloak`**: Authentication and authorization data

## 🚀 Quick Start

### **Complete Deployment (Infrastructure + Migrations)**
```bash
# Deploy infrastructure and run migrations
./deploy.sh

# Deploy infrastructure, run migrations, and seed data
./deploy.sh --seed

# Stop all services
./stop.sh

# Reset infrastructure (with prompts)
./reset.sh

# Reset with data cleanup (no prompts)
./reset.sh --clean-data --force

# Run seed data separately (after deployment)
./scripts/deployment/run-seeds.sh
```

### **Infrastructure Management**
```bash
# All main scripts are available as symlinks in the root:
./deploy.sh  # Deploy everything
./stop.sh    # Stop all services
./reset.sh   # Reset infrastructure

# Or use scripts directly:
./scripts/deployment/deploy.sh
./scripts/deployment/stop.sh
./scripts/deployment/reset.sh

# Run specific migrations
./scripts/deployment/run-dynamic-migrations.sh

# Health check
./scripts/utilities/health-check.sh
```

📋 New Workflow

  1. Run ./deploy.sh to bootstrap infrastructure and admin database
  2. Run ./run-dynamic-migrations.sh to migrate all regional databases
  3. Check status with curl http://localhost:8000/api/v1/migrations/dynamic/status

### **Migrations Only**
```bash
cd migrations

# Build the migration service
docker-compose -f docker-compose.migrations.yml build

# Run all migrations
docker-compose -f docker-compose.migrations.yml run --rm neo-migrations migrate

# Run only admin migrations
docker-compose -f docker-compose.migrations.yml run --rm neo-migrations admin

# Run only regional migrations  
docker-compose -f docker-compose.migrations.yml run --rm neo-migrations regional

# Show migration info
docker-compose -f docker-compose.migrations.yml run --rm neo-migrations info
```

## 📊 Services

| Service | URL | Credentials | Purpose |
|---------|-----|-------------|---------|
| PostgreSQL US | `localhost:5432` | `postgres/postgres` | US region databases |
| PostgreSQL EU | `localhost:5433` | `postgres/postgres` | EU region databases |
| Redis | `localhost:6379` | password: `redis` | Cache & sessions |
| Keycloak | `http://localhost:8080` | `admin/admin` | Authentication |
| pgAdmin | `http://localhost:5050` | `admin@neo.local/admin` | DB management |
| RedisInsight | `http://localhost:8001` | - | Redis management |

## 🗄️ Databases

### US East Region (Port 5432)
- `neofast_admin` - Platform administration
- `neofast_shared_us` - Shared tenant data (US)
- `neofast_analytics_us` - Analytics data (US)

### EU West Region (Port 5433)  
- `neofast_shared_eu` - Shared tenant data (EU, GDPR compliant)
- `neofast_analytics_eu` - Analytics data (EU, GDPR compliant)

## 📂 Migration Structure

```
migrations/
├── flyway/
│   ├── global/                     # Admin database migrations (US only)
│   │   ├── V001__platform_common_schema.sql
│   │   ├── V002__admin_schema_types.sql
│   │   ├── V003__admin_identity_access.sql
│   │   ├── V004__admin_organization_tenant.sql
│   │   ├── V005__admin_subscription_billing.sql
│   │   ├── V006__admin_user_roles_tenant_mgmt.sql
│   │   └── V007__admin_monitoring_security.sql
│   │
│   ├── regional/                   # Regional database migrations
│   │   ├── shared/                 # Tenant data databases
│   │   │   └── V001__tenant_template_schema.sql
│   │   └── analytics/              # Analytics databases
│   │       └── V001__analytics_base_schema.sql
│   │
│   └── config/                     # Flyway configurations
│       ├── us-admin.conf           # US admin database
│       ├── us-shared.conf          # US shared database
│       ├── us-analytics.conf       # US analytics database
│       ├── eu-shared.conf          # EU shared database
│       └── eu-analytics.conf       # EU analytics database
│
├── orchestrator/                   # Python migration orchestration
├── scripts/                        # Migration scripts
├── Dockerfile                      # Migration service container
├── docker-compose.migrations.yml   # Migration service compose
└── requirements.txt                # Python dependencies
```

## Configuration

Environment variables are automatically created in `.env` file on first run.

Key configurations:
- `POSTGRES_US_PORT=5432` - US region PostgreSQL port
- `POSTGRES_EU_PORT=5433` - EU region PostgreSQL port  
- `KEYCLOAK_PORT=8080` - Keycloak HTTP port
- `REDIS_PORT=6379` - Redis port

### **Migration Environment Variables**
```bash
# Database Connections
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_US_HOST=neo-postgres-us-east
POSTGRES_EU_HOST=neo-postgres-eu-west
```

## 🛠️ Development Tools

Start with development tools:
```bash
cd NeoInfrastructure
docker-compose -f docker/docker-compose.infrastructure.yml --profile tools up -d
```

## Scripts

### start-infrastructure.sh
- Creates `.env` with defaults if missing
- Starts all infrastructure services
- Waits for health checks
- Disables Keycloak SSL for development
- Shows service status and URLs

### reset-infrastructure.sh
- `--clean-data` - Remove all data volumes
- `--clean-images` - Remove Docker images  
- `--force` - Skip confirmation prompts

## 📁 Directory Structure

```
NeoInfrastructure/
├── docker/
│   ├── docker-compose.infrastructure.yml  # Main compose file
│   ├── postgres/
│   │   ├── init/           # Common PostgreSQL init scripts
│   │   ├── init-us/        # US region specific scripts
│   │   └── init-eu/        # EU region specific scripts
│   └── keycloak/
│       ├── themes/         # Custom Keycloak themes
│       └── providers/      # Custom Keycloak providers
├── migrations/              # Database migration service
│   ├── flyway/             # Migration files and configs
│   ├── orchestrator/       # Python migration orchestration
│   ├── scripts/            # Migration scripts
│   ├── Dockerfile          # Migration service container
│   ├── docker-compose.migrations.yml
│   └── requirements.txt
├── scripts/
│   ├── start-infrastructure.sh   # Start services
│   └── reset-infrastructure.sh   # Reset/cleanup services
└── .env                    # Environment configuration
```

## Multi-Region Features

- **Data Residency**: EU region for GDPR compliance
- **Regional Isolation**: Separate databases per region
- **Flexible Deployment**: Schema, database, or dedicated options
- **Health Monitoring**: Built-in health checks for all services
- **Automatic Failover**: Ready for connection failover logic

## Security Notes

- SSL is disabled in Keycloak for development
- Default passwords should be changed for production
- All services run on localhost only
- No external network exposure by default

## 📝 Next Steps

1. Start the infrastructure: `./scripts/start-infrastructure.sh`
2. Verify all services are healthy
3. Set up application-specific schemas and migrations
4. Configure Keycloak realms for different services
5. Implement region selection logic in applications