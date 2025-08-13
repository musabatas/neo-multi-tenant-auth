#!/bin/bash
# Start NeoMultiTenant Deployment API

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo "🚀 Starting NeoMultiTenant Deployment API"
echo "========================================"
echo ""

# Get the actual script location (resolving symlinks)
SCRIPT_PATH="$(readlink -f "$0" 2>/dev/null || readlink "$0" 2>/dev/null || echo "$0")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Check if infrastructure is running
if ! docker ps | grep -q "neo-postgres-us-east"; then
    echo -e "${YELLOW}⚠️  Infrastructure not running. Starting it first...${NC}"
    "$SCRIPT_DIR/deploy.sh"
fi

# Build API container
echo -e "${CYAN}🔨 Building API container...${NC}"
cd migrations
docker-compose -f docker-compose.api.yml build

# Start API
echo -e "${CYAN}🌐 Starting API service...${NC}"
docker-compose -f docker-compose.api.yml up -d

# Wait for API to be ready
echo -e "${CYAN}⏳ Waiting for API to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

# Check API health
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo -e "${GREEN}✅ API is running and healthy${NC}"
else
    echo -e "${YELLOW}⚠️  API may still be starting up${NC}"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 DEPLOYMENT API STARTED!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo ""
echo -e "${BLUE}📡 API Endpoints:${NC}"
echo "   • Health:     http://localhost:8000/health"
echo "   • Docs:       http://localhost:8000/docs"
echo "   • OpenAPI:    http://localhost:8000/openapi.json"

echo ""
echo -e "${BLUE}🎮 CLI Usage:${NC}"
echo "   cd migrations/api"
echo "   python cli_client.py --help"
echo ""
echo "   Examples:"
echo "   python cli_client.py health"
echo "   python cli_client.py deploy --watch"
echo "   python cli_client.py migrate --scope all"
echo "   python cli_client.py status"

echo ""
echo -e "${BLUE}Management:${NC}"
echo "   View logs:  docker logs -f neo-deployment-api"
echo "   Stop API:   docker-compose -f migrations/docker-compose.api.yml down"
echo "   Restart:    docker-compose -f migrations/docker-compose.api.yml restart"