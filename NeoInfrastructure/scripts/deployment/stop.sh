#!/bin/bash
# Stop NeoInfrastructure services gracefully

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo "🛑 Stopping NeoInfrastructure services..."
echo "========================================="

# Get the actual script location (resolving symlinks)
SCRIPT_PATH="$(readlink -f "$0" 2>/dev/null || readlink "$0" 2>/dev/null || echo "$0")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Stop API service (remove containers and networks)
if [ -f "migrations/docker-compose.api.yml" ]; then
    echo -e "${CYAN}🔄 Stopping and removing API service...${NC}"
    docker-compose -f migrations/docker-compose.api.yml down --remove-orphans 2>/dev/null || true
fi

# Stop migration services (remove containers and networks)
if [ -f "migrations/docker-compose.migrations.yml" ]; then
    echo -e "${CYAN}🔄 Stopping and removing migration services...${NC}"
    docker-compose -f migrations/docker-compose.migrations.yml down --remove-orphans 2>/dev/null || true
fi

# Stop infrastructure services (remove containers and networks)
if [ -f "docker/docker-compose.infrastructure.yml" ]; then
    echo -e "${CYAN}🔄 Stopping and removing infrastructure services...${NC}"
    docker-compose -f docker/docker-compose.infrastructure.yml down --remove-orphans
fi

echo -e "${GREEN}✅ All services stopped${NC}"

# Show remaining containers
REMAINING=$(docker ps --filter "name=neo-" --format "table {{.Names}}" | tail -n +2 | wc -l)
if [ "$REMAINING" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Some containers are still running:${NC}"
    docker ps --filter "name=neo-" --format "table {{.Names}}\t{{.Status}}"
fi