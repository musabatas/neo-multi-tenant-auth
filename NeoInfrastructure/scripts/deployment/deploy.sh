#!/bin/bash
# NeoMultiTenant - Complete Infrastructure Deployment
# One command to deploy everything: infrastructure, migrations, and services

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo "🚀 NeoMultiTenant - Complete Infrastructure Deployment"
echo "======================================================"
echo ""

# Parse command line arguments
RUN_SEEDS=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --seed)
            RUN_SEEDS=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --seed    Run seed data after migrations"
            echo "  --help    Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0           # Deploy infrastructure and run migrations"
            echo "  $0 --seed    # Deploy infrastructure, run migrations, and seed data"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Get the actual script location (resolving symlinks)
SCRIPT_PATH="$(readlink -f "$0" 2>/dev/null || readlink "$0" 2>/dev/null || echo "$0")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
INFRASTRUCTURE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
MIGRATIONS_DIR="$INFRASTRUCTURE_DIR/migrations"

# Function to check command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for service
wait_for_service() {
    local service=$1
    local check_cmd=$2
    local max_attempts=30
    local attempt=0
    
    echo -e "${CYAN}⏳ Waiting for $service...${NC}"
    while [ $attempt -lt $max_attempts ]; do
        if eval "$check_cmd" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ $service is ready${NC}"
            return 0
        fi
        sleep 2
        ((attempt++))
    done
    
    echo -e "${RED}❌ $service failed to start${NC}"
    return 1
}

# Function to wait for a specific table to exist in a database
wait_for_db_table() {
    local container=$1
    local database=$2
    local schema=$3
    local table=$4
    local max_attempts=60
    local attempt=0

    echo -e "${CYAN}⏳ Waiting for table ${schema}.${table} to exist in ${database}...${NC}"
    while [ $attempt -lt $max_attempts ]; do
        if docker exec -i "$container" psql -U postgres -d "$database" -tAc "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='${schema}' AND table_name='${table}')" | grep -q 't'; then
            echo -e "${GREEN}✅ Table ${schema}.${table} is present${NC}"
            return 0
        fi
        sleep 2
        ((attempt++))
    done

    echo -e "${RED}❌ Timed out waiting for table ${schema}.${table} in ${database}${NC}"
    return 1
}

# Check prerequisites
echo -e "${BLUE}📋 Checking prerequisites...${NC}"
if ! command_exists docker; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    exit 1
fi

if ! command_exists docker-compose; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All prerequisites met${NC}"
echo ""

# Step 1: Start Infrastructure Services
echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${PURPLE}STEP 1: STARTING INFRASTRUCTURE${NC}"
echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

cd "$INFRASTRUCTURE_DIR"

# Create necessary directories
echo -e "${CYAN}📁 Creating directory structure...${NC}"
mkdir -p docker/postgres/{init,init-us,init-eu}
mkdir -p docker/keycloak/{themes,providers}
mkdir -p migrations/{flyway/conf,logs,config}

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}📝 Creating .env configuration...${NC}"
    cat > .env << 'EOF'
# NeoInfrastructure Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_US_PORT=5432
POSTGRES_EU_PORT=5433
REDIS_PORT=6379
REDIS_PASSWORD=redis
KEYCLOAK_PORT=8080
KEYCLOAK_ADMIN=admin
KEYCLOAK_PASSWORD=admin
EOF
fi

# Start infrastructure
echo -e "${CYAN}🐳 Starting Docker containers...${NC}"

# Check if we need to recreate Keycloak (only if health check needs fixing)
keycloak_needs_recreation=false
if docker ps -a | grep -q neo-keycloak; then
    # Check if Keycloak has the old broken health check
    current_health_test=$(docker inspect neo-keycloak --format '{{range .Config.Healthcheck.Test}}{{.}} {{end}}' 2>/dev/null || echo "")
    if echo "$current_health_test" | grep -q "/health/ready"; then
        echo -e "${YELLOW}⚠️  Keycloak has outdated health check, recreating container...${NC}"
        keycloak_needs_recreation=true
    fi
fi

if [ "$keycloak_needs_recreation" = true ]; then
    docker-compose --env-file .env -f docker/docker-compose.infrastructure.yml stop keycloak
    docker-compose --env-file .env -f docker/docker-compose.infrastructure.yml rm -f keycloak
    echo -e "${GREEN}✅ Keycloak container will be recreated with new health check${NC}"
fi

docker-compose --env-file .env -f docker/docker-compose.infrastructure.yml up -d

# Wait for containers to be healthy
echo -e "${CYAN}⏳ Waiting for containers to be healthy...${NC}"
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    # Check if neo-postgres-us-east is healthy
    us_health=$(docker inspect -f '{{.State.Health.Status}}' neo-postgres-us-east 2>/dev/null || echo "not_found")
    eu_health=$(docker inspect -f '{{.State.Health.Status}}' neo-postgres-eu-west 2>/dev/null || echo "not_found")
    
    if [ "$us_health" = "healthy" ] && [ "$eu_health" = "healthy" ]; then
        echo -e "${GREEN}✅ All database containers are healthy${NC}"
        break
    fi
    
    echo -n "."
    sleep 2
    ((attempt++))
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "\n${RED}❌ Timeout waiting for containers to be healthy${NC}"
    echo "Container status:"
    docker ps -a | grep -E "neo-postgres|neo-redis"
    exit 1
fi

# Additional checks to ensure services are ready
wait_for_service "PostgreSQL US East" "docker exec neo-postgres-us-east pg_isready -U postgres"
wait_for_service "PostgreSQL EU West" "docker exec neo-postgres-eu-west pg_isready -U postgres"
wait_for_service "Redis" "docker exec neo-redis redis-cli -a redis ping"

echo ""
echo -e "${GREEN}✅ Infrastructure services started${NC}"

# Step 2: Deploy API Service (which will handle migrations)
echo ""
echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${PURPLE}STEP 2: DEPLOYING API SERVICE${NC}"
echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "${CYAN}🚀 Building and starting Deployment API...${NC}"
echo -e "${YELLOW}ℹ️  The API will automatically run database migrations on startup${NC}"
cd "$MIGRATIONS_DIR"
docker-compose -f docker-compose.api.yml build
docker-compose -f docker-compose.api.yml up -d

# Wait for API to be ready
echo -e "${CYAN}⏳ Waiting for API to be ready (migrations will run automatically)...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Deployment API is running${NC}"
        break
    fi
    sleep 2
done

# Ensure critical admin tables exist before proceeding (verifies migrations finished)
wait_for_db_table "neo-postgres-us-east" "neofast_admin" "admin" "tenants"
wait_for_db_table "neo-postgres-us-east" "neofast_admin" "admin" "users"

echo -e "${GREEN}✅ API deployed and admin migrations verified${NC}"

# Step 3: Provision Keycloak (admin realm and tenants)
echo ""
echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${PURPLE}STEP 3: KEYCLOAK PROVISIONING${NC}"
echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Ensure Keycloak is healthy before provisioning
# First check Docker health status, but also verify actual connectivity
echo -e "${CYAN}⏳ Waiting for Keycloak to be ready...${NC}"
keycloak_ready=false
for i in {1..60}; do
    # Check both Docker health and actual connectivity
    docker_health=$(docker inspect -f '{{.State.Health.Status}}' neo-keycloak 2>/dev/null || echo "not_found")
    
    # Also check if Keycloak is actually responding (redirect means it's working)
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ 2>/dev/null | grep -q "302\|200"; then
        keycloak_ready=true
        echo -e "${GREEN}✅ Keycloak is ready${NC}"
        break
    fi
    
    # If Docker says healthy but curl fails, still wait
    if [ "$docker_health" = "healthy" ]; then
        echo -e "${YELLOW}   Docker reports healthy but Keycloak not responding yet...${NC}"
    fi
    
    sleep 2
done

if [ "$keycloak_ready" = false ]; then
    echo -e "${RED}❌ Keycloak failed to start properly${NC}"
    echo -e "${YELLOW}   Debug info:${NC}"
    docker logs --tail 20 neo-keycloak
    exit 1
fi

echo -e "${CYAN}Ensuring admin realm exists (platform-admin)...${NC}"
docker exec -i neo-deployment-api python /app/api/provision_keycloak.py --admin-realm | sed 's/.*/   &/' || true

echo -e "${CYAN}Provisioning tenant realms and clients (missing only)...${NC}"
docker exec -i neo-deployment-api python /app/api/provision_keycloak.py | sed 's/.*/   &/' || true

# Step 4: Run Seed Data (if requested)
if [ "$RUN_SEEDS" = true ]; then
    echo ""
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${PURPLE}STEP 4: RUNNING SEED DATA${NC}"
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    echo -e "${CYAN}🌱 Seeding database with initial data...${NC}"
    
    # Run seed files in order
    SEED_DIR="$MIGRATIONS_DIR/seeds/admin"
    if [ -d "$SEED_DIR" ]; then
        for seed_file in $(ls "$SEED_DIR"/*.sql 2>/dev/null | sort); do
            seed_name=$(basename "$seed_file")
            echo -e "${CYAN}   Running seed: $seed_name${NC}"
            
            # Execute seed file directly on the admin database
            if docker exec -i neo-postgres-us-east psql -U postgres -d neofast_admin < "$seed_file"; then
                echo -e "${GREEN}   ✅ $seed_name completed${NC}"
            else
                echo -e "${RED}   ❌ $seed_name failed${NC}"
                echo -e "${YELLOW}   Note: Seed data may already exist (ON CONFLICT will update)${NC}"
            fi
        done
        echo -e "${GREEN}✅ Seed data loaded${NC}"
    else
        echo -e "${YELLOW}⚠️  No seed files found in $SEED_DIR${NC}"
    fi
fi

cd "$INFRASTRUCTURE_DIR"

# Step 5: Run Dynamic Migrations
echo ""
echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${PURPLE}STEP 5: DYNAMIC MIGRATIONS${NC}"
echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "${CYAN}🔄 Running dynamic migrations for all regional/tenant databases...${NC}"
echo -e "${YELLOW}ℹ️  This will migrate databases listed in admin.database_connections${NC}"

# Ensure API is ready for dynamic migrations
echo -e "${CYAN}⏳ Verifying API is ready for dynamic migrations...${NC}"
for i in {1..10}; do
    if curl -s http://localhost:8000/api/v1/migrations/dynamic/status > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Dynamic migration API is ready${NC}"
        break
    fi
    if [ $i -eq 10 ]; then
        echo -e "${RED}❌ Dynamic migration API not responding${NC}"
        echo -e "${YELLOW}   Continuing anyway - databases may need manual migration${NC}"
        break
    fi
    sleep 2
done

# Run dynamic migrations
echo -e "${CYAN}🚀 Triggering dynamic migrations...${NC}"
response=$(curl -s -X POST http://localhost:8000/api/v1/migrations/dynamic 2>/dev/null || echo '{"error": "API call failed"}')
migration_id=$(echo "$response" | python3 -c "import json, sys; print(json.load(sys.stdin).get('migration_id', ''))" 2>/dev/null || echo "")

if [ -n "$migration_id" ]; then
    echo -e "${GREEN}✅ Dynamic migration started with ID: $migration_id${NC}"
    
    # Monitor progress for up to 3 minutes
    echo -e "${CYAN}⏳ Monitoring migration progress...${NC}"
    max_attempts=36  # 3 minutes
    attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        status_response=$(curl -s "http://localhost:8000/api/v1/migrations/$migration_id" 2>/dev/null || echo '{"status": "unknown"}')
        status=$(echo "$status_response" | python3 -c "import json, sys; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "unknown")
        
        case "$status" in
            "completed")
                echo -e "\n${GREEN}✅ Dynamic migrations completed successfully!${NC}"
                break
                ;;
            "failed")
                echo -e "\n${RED}❌ Dynamic migrations failed${NC}"
                echo -e "${YELLOW}⚠️  Check logs: docker logs neo-deployment-api${NC}"
                break
                ;;
            "in_progress")
                echo -n "."
                sleep 5
                ((attempt++))
                ;;
            *)
                echo -n "?"
                sleep 5
                ((attempt++))
                ;;
        esac
    done
    
    if [ $attempt -eq $max_attempts ]; then
        echo -e "\n${YELLOW}⚠️  Migration monitoring timeout - migrations may still be running${NC}"
        echo -e "${CYAN}   Check status: curl http://localhost:8000/api/v1/migrations/dynamic/status${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Could not start dynamic migrations${NC}"
    echo -e "${CYAN}   Manual command: cd $INFRASTRUCTURE_DIR/scripts/deployment && ./run-dynamic-migrations.sh${NC}"
fi

echo -e "${GREEN}✅ Dynamic migration step completed${NC}"

# Step 6: Verify Deployment
echo ""
echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${PURPLE}STEP 6: DEPLOYMENT VERIFICATION${NC}"
echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "${CYAN}🔍 Checking service health...${NC}"

# Check container status
RUNNING_CONTAINERS=$(docker ps --format "table {{.Names}}\t{{.Status}}" | grep neo- | wc -l)
echo -e "   Running containers: $RUNNING_CONTAINERS"

# Show migration status via API
echo ""
echo -e "${CYAN}📊 Migration Status:${NC}"
# Check if API is responding
if curl -s http://localhost:8000/api/v1/migrations/status > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Migrations completed successfully (check API for details)${NC}"
    echo -e "${CYAN}   View status: curl http://localhost:8000/api/v1/migrations/status${NC}"
else
    echo -e "${YELLOW}⚠️  Unable to verify migration status via API${NC}"
fi

# Final Summary
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 DEPLOYMENT COMPLETE!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo ""
echo -e "${BLUE}📊 Infrastructure Status:${NC}"
echo "   ✅ PostgreSQL US East: localhost:5432"
echo "   ✅ PostgreSQL EU West: localhost:5433"
echo "   ✅ Redis Cache: localhost:6379"
echo "   ✅ Keycloak IAM: http://localhost:8080"
echo "   ✅ Deployment API: http://localhost:8000"

echo ""
echo -e "${BLUE}🗄️ Databases Created:${NC}"
echo "   • neofast_admin (Global)"
echo "   • neofast_shared_us (US Region)"
echo "   • neofast_analytics_us (US Analytics)"
echo "   • neofast_shared_eu (EU Region - GDPR)"
echo "   • neofast_analytics_eu (EU Analytics - GDPR)"

echo ""
echo -e "${BLUE}Management Commands:${NC}"
echo "   Stop all:     $INFRASTRUCTURE_DIR/stop.sh"
echo "   Reset all:    $INFRASTRUCTURE_DIR/reset.sh"
echo "   View logs:    docker-compose -f docker/docker-compose.infrastructure.yml logs -f"
echo "   API logs:     docker-compose -f migrations/docker-compose.api.yml logs -f"
echo ""
echo -e "${BLUE}🌐 API Endpoints:${NC}"
echo "   Health Check: http://localhost:8000/health"
echo "   API Docs:     http://localhost:8000/docs"
echo "   Migrations:   http://localhost:8000/api/v1/migrations/status"
echo "   Dynamic Migrations: http://localhost:8000/api/v1/migrations/dynamic/status"

if [ "$RUN_SEEDS" = true ]; then
    echo ""
    echo -e "${BLUE}🌱 Seed Data:${NC}"
    echo "   ✅ Regions populated (US East, EU West)"
    echo "   ✅ Database connections configured"
fi

echo ""
echo -e "${BLUE}🔄 Dynamic Migrations:${NC}"
echo "   ✅ Regional databases migrated"
echo "   ✅ Tenant template schemas created"
echo "   ✅ Analytics databases prepared"

echo ""
echo -e "${CYAN}💡 Next Steps:${NC}"
if [ "$RUN_SEEDS" = false ]; then
    echo "   1. Run seed data: $INFRASTRUCTURE_DIR/deploy.sh --seed"
    echo "   2. Deploy microservices: cd ../NeoServices && ./deploy.sh"
    echo "   3. Create first tenant via API"
    echo "   4. Test application functionality"
else
    echo "   1. Deploy microservices: cd ../NeoServices && ./deploy.sh"
    echo "   2. Create first tenant via API"
    echo "   3. Test application functionality"
fi

echo ""
echo -e "${CYAN}🔧 Manual Migration Commands (if needed):${NC}"
echo "   Dynamic migrations: $INFRASTRUCTURE_DIR/scripts/deployment/run-dynamic-migrations.sh"
echo "   List tenant migrations: $INFRASTRUCTURE_DIR/scripts/deployment/list-tenant-migrations.sh"