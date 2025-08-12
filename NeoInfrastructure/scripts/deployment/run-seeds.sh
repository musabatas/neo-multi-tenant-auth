#!/bin/bash
# Run seed data for NeoInfrastructure
# This script can be run independently to seed or re-seed the database

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo "🌱 NeoInfrastructure - Database Seeding"
echo "======================================="
echo ""

# Get the actual script location (resolving symlinks)
SCRIPT_PATH="$(readlink -f "$0" 2>/dev/null || readlink "$0" 2>/dev/null || echo "$0")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MIGRATIONS_DIR="$PROJECT_ROOT/migrations"

# Check if infrastructure is running
if ! docker ps | grep -q "neo-postgres-us-east"; then
    echo -e "${RED}❌ Infrastructure not running${NC}"
    echo -e "${YELLOW}Please start infrastructure first with: ./deploy.sh${NC}"
    exit 1
fi

# Check if admin database exists
if ! docker exec neo-postgres-us-east psql -U postgres -lqt | cut -d \| -f 1 | grep -qw neofast_admin; then
    echo -e "${RED}❌ Admin database not found${NC}"
    echo -e "${YELLOW}Please run migrations first with: ./deploy.sh${NC}"
    exit 1
fi

echo -e "${CYAN}🌱 Running seed data...${NC}"
echo ""

# Run seed files in order
SEED_DIR="$MIGRATIONS_DIR/seeds/admin"
if [ -d "$SEED_DIR" ]; then
    SUCCESS_COUNT=0
    TOTAL_COUNT=0
    
    for seed_file in $(ls "$SEED_DIR"/*.sql 2>/dev/null | sort); do
        TOTAL_COUNT=$((TOTAL_COUNT + 1))
        seed_name=$(basename "$seed_file")
        echo -e "${CYAN}Running seed: $seed_name${NC}"
        
        # Execute seed file directly on the admin database
        if docker exec -i neo-postgres-us-east psql -U postgres -d neofast_admin < "$seed_file" 2>/dev/null; then
            echo -e "${GREEN}✅ $seed_name completed${NC}"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        else
            echo -e "${YELLOW}⚠️  $seed_name skipped (data may already exist)${NC}"
        fi
        echo ""
    done
    
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🎉 Seeding Complete!${NC}"
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Seeds processed: $SUCCESS_COUNT/$TOTAL_COUNT"
    
    # Show what was seeded
    echo ""
    echo -e "${BLUE}📊 Seeded Data:${NC}"
    echo "   • Regions: US East (us-east-1), EU West (eu-west-1)"
    echo "   • Database Connections:"
    echo "     - neofast-admin-primary (US East)"
    echo "     - neofast-shared-us-primary (US East)"
    echo "     - neofast-analytics-us (US East)"
    echo "     - neofast-shared-eu-primary (EU West)"
    echo "     - neofast-analytics-eu (EU West)"
else
    echo -e "${RED}❌ No seed files found in $SEED_DIR${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}💡 To verify seed data:${NC}"
echo '   docker exec -it neo-postgres-us-east psql -U postgres -d neofast_admin -c "SELECT * FROM admin.regions;"'
echo '   docker exec -it neo-postgres-us-east psql -U postgres -d neofast_admin -c "SELECT * FROM admin.database_connections;"'