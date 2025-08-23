#!/bin/bash
# NeoInfrastructure Health Check & Monitoring

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo "🏥 NeoInfrastructure Health Check"
echo "=================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment
if [ -f ".env" ]; then
    source .env
fi

# Function to check service health
check_service() {
    local service=$1
    local check_cmd=$2
    
    if eval "$check_cmd" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ $service: Healthy${NC}"
        return 0
    else
        echo -e "${RED}❌ $service: Unhealthy${NC}"
        return 1
    fi
}

# Function to check database
check_database() {
    local host=$1
    local port=$2
    local db=$3
    local description=$4
    
    if PGPASSWORD=postgres psql -h localhost -p $port -U postgres -d $db -c "SELECT 1" >/dev/null 2>&1; then
        # Get table count
        table_count=$(PGPASSWORD=postgres psql -h localhost -p $port -U postgres -d $db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema')" 2>/dev/null | xargs)
        echo -e "${GREEN}✅ $description: Connected (${table_count} tables)${NC}"
    else
        echo -e "${RED}❌ $description: Cannot connect${NC}"
    fi
}

# Check Docker
echo -e "${BLUE}1. Docker Services${NC}"
echo "-------------------"

# Check containers
RUNNING=$(docker ps --filter "name=neo-" --format "{{.Names}}" | wc -l)
TOTAL=$(docker ps -a --filter "name=neo-" --format "{{.Names}}" | wc -l)

echo -e "   Containers: ${RUNNING}/${TOTAL} running"

if [ "$RUNNING" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  No services running. Run ./deploy.sh to start${NC}"
    exit 1
fi

# List running containers
docker ps --filter "name=neo-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | while read line; do
    echo "   $line"
done

echo ""
echo -e "${BLUE}2. Database Services${NC}"
echo "--------------------"

# Check PostgreSQL US East
check_database "localhost" "${POSTGRES_US_PORT:-5432}" "postgres" "PostgreSQL US East"
check_database "localhost" "${POSTGRES_US_PORT:-5432}" "neofast_admin" "  └─ Admin DB"
check_database "localhost" "${POSTGRES_US_PORT:-5432}" "neofast_shared_us" "  └─ Shared US DB"
check_database "localhost" "${POSTGRES_US_PORT:-5432}" "neofast_analytics_us" "  └─ Analytics US DB"

# Check PostgreSQL EU West
check_database "localhost" "${POSTGRES_EU_PORT:-5433}" "postgres" "PostgreSQL EU West"
check_database "localhost" "${POSTGRES_EU_PORT:-5433}" "neofast_shared_eu" "  └─ Shared EU DB"
check_database "localhost" "${POSTGRES_EU_PORT:-5433}" "neofast_analytics_eu" "  └─ Analytics EU DB"

echo ""
echo -e "${BLUE}3. Cache Services${NC}"
echo "-----------------"

# Check Redis
if docker exec neo-redis redis-cli -a redis ping >/dev/null 2>&1; then
    keys=$(docker exec neo-redis redis-cli -a redis DBSIZE 2>/dev/null | cut -d' ' -f2)
    echo -e "${GREEN}✅ Redis: Connected (${keys} keys)${NC}"
else
    echo -e "${RED}❌ Redis: Cannot connect${NC}"
fi

echo ""
echo -e "${BLUE}4. Identity Services${NC}"
echo "--------------------"

# Check Keycloak
if curl -s http://localhost:${KEYCLOAK_PORT:-8080}/health/ready >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Keycloak: Ready${NC}"
    echo "     └─ Admin: http://localhost:${KEYCLOAK_PORT:-8080}/admin (admin/admin)"
else
    echo -e "${YELLOW}⚠️  Keycloak: Starting up...${NC}"
fi

echo ""
echo -e "${BLUE}5. Migration Status${NC}"
echo "-------------------"

# Check Flyway schema history
if PGPASSWORD=postgres psql -h localhost -p ${POSTGRES_US_PORT:-5432} -U postgres -d neofast_admin -c "SELECT COUNT(*) FROM flyway_schema_history" >/dev/null 2>&1; then
    migration_count=$(PGPASSWORD=postgres psql -h localhost -p ${POSTGRES_US_PORT:-5432} -U postgres -d neofast_admin -t -c "SELECT COUNT(*) FROM flyway_schema_history" 2>/dev/null | xargs)
    echo -e "${GREEN}✅ Migrations: ${migration_count} applied${NC}"
else
    echo -e "${YELLOW}⚠️  Migrations: No history table found${NC}"
fi

echo ""
echo -e "${BLUE}6. Resource Usage${NC}"
echo "-----------------"

# Get Docker stats
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep neo- || true

echo ""
echo -e "${BLUE}7. Network Connectivity${NC}"
echo "-----------------------"

# Check network
if docker network ls | grep NeoInfrastructure >/dev/null 2>&1; then
    container_count=$(docker network inspect NeoInfrastructure -f '{{len .Containers}}' 2>/dev/null || echo "0")
    echo -e "${GREEN}✅ Network 'NeoInfrastructure': ${container_count} containers${NC}"
else
    echo -e "${RED}❌ Network 'NeoInfrastructure' not found${NC}"
fi

# Summary
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

HEALTH_SCORE=0
TOTAL_CHECKS=7

# Calculate health score
[ "$RUNNING" -gt 0 ] && ((HEALTH_SCORE++))
docker exec neo-postgres-us-east pg_isready >/dev/null 2>&1 && ((HEALTH_SCORE++))
docker exec neo-postgres-eu-west pg_isready >/dev/null 2>&1 && ((HEALTH_SCORE++))
docker exec neo-redis redis-cli -a redis ping >/dev/null 2>&1 && ((HEALTH_SCORE++))
curl -s http://localhost:${KEYCLOAK_PORT:-8080}/health >/dev/null 2>&1 && ((HEALTH_SCORE++))
docker network ls | grep NeoInfrastructure >/dev/null 2>&1 && ((HEALTH_SCORE++))
[ -f "migrations/Dockerfile" ] && ((HEALTH_SCORE++))

PERCENTAGE=$((HEALTH_SCORE * 100 / TOTAL_CHECKS))

if [ "$PERCENTAGE" -ge 90 ]; then
    echo -e "${GREEN}🎉 System Health: EXCELLENT (${PERCENTAGE}%)${NC}"
elif [ "$PERCENTAGE" -ge 70 ]; then
    echo -e "${YELLOW}⚠️  System Health: GOOD (${PERCENTAGE}%)${NC}"
else
    echo -e "${RED}❌ System Health: POOR (${PERCENTAGE}%)${NC}"
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"