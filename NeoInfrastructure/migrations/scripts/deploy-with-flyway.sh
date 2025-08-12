#!/bin/bash
# NeoMultiTenant - Dynamic Migration Deployment
# Uses API-based dynamic configuration for migrations

set -e

echo "🚀 NeoMultiTenant - Dynamic Migration Deployment"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${YELLOW}This script has been replaced by the dynamic migration system.${NC}"
echo ""
echo -e "${CYAN}To run migrations, use:${NC}"
echo "   1. Admin database (bootstrap): Already done in deploy.sh"
echo "   2. All other databases: ./run-dynamic-migrations.sh"
echo ""
echo -e "${CYAN}To check migration status:${NC}"
echo "   curl http://localhost:8000/api/v1/migrations/dynamic/status | python3 -m json.tool"
echo ""
echo -e "${GREEN}The system now uses dynamic configuration from admin.database_connections table${NC}"
echo -e "${GREEN}No static Flyway config files are needed anymore!${NC}"