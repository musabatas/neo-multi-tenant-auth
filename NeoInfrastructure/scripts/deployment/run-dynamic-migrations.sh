#!/bin/bash
# NeoMultiTenant - Run Dynamic Migrations via API
# This script triggers migrations for all databases using connection info from admin.database_connections
#
# Usage:
#   ./run-dynamic-migrations.sh [options]
#
# Options:
#   --dry-run              Show migration plan without executing
#   --database <name>      Filter to specific database (coming soon)
#   --schema <name>        Filter to specific schema (coming soon)
#   --force                Skip confirmation prompts (coming soon)
#   --help                 Show this help message

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo "🚀 NeoMultiTenant - Dynamic Database Migrations"
echo "==============================================="
echo ""

# Check if API is running
echo -e "${CYAN}🔍 Checking API health...${NC}"
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${RED}❌ Deployment API is not running${NC}"
    echo "   Please run: ./deploy.sh first"
    exit 1
fi
echo -e "${GREEN}✅ API is healthy${NC}"
echo ""

# Show current migration status
echo -e "${CYAN}📊 Current migration status:${NC}"
curl -s http://localhost:8000/api/v1/migrations/dynamic/status | python3 -m json.tool 2>/dev/null || {
    echo -e "${YELLOW}⚠️  Could not fetch current status${NC}"
}
echo ""

# Parse command line arguments
DRY_RUN=false
DATABASE_FILTER=""
SCHEMA_FILTER=""
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --database)
            DATABASE_FILTER="$2"
            shift 2
            echo -e "${YELLOW}⚠️  Database filtering not yet implemented${NC}"
            ;;
        --schema)
            SCHEMA_FILTER="$2"
            shift 2
            echo -e "${YELLOW}⚠️  Schema filtering not yet implemented${NC}"
            ;;
        --force)
            FORCE=true
            shift
            echo -e "${YELLOW}⚠️  Force mode not yet implemented${NC}"
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --dry-run              Show migration plan without executing"
            echo "  --database <name>      Filter to specific database (coming soon)"
            echo "  --schema <name>        Filter to specific schema (coming soon)"
            echo "  --force                Skip confirmation prompts (coming soon)"
            echo "  --help                 Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Option to run dry-run first
if [ "$DRY_RUN" = "true" ]; then
    echo -e "${YELLOW}🔍 Running in DRY-RUN mode${NC}"
    echo ""
    
    echo -e "${CYAN}📋 Fetching migration plan...${NC}"
    response=$(curl -s -X POST "http://localhost:8000/api/v1/migrations/dynamic?dry_run=true")
    echo "$response" | python3 -m json.tool
    
    echo ""
    echo -e "${YELLOW}This was a dry run. To execute migrations, run without --dry-run flag${NC}"
    exit 0
fi

# Trigger dynamic migrations
echo -e "${CYAN}🔄 Triggering dynamic migrations for all regional databases...${NC}"
echo ""

response=$(curl -s -X POST http://localhost:8000/api/v1/migrations/dynamic)
migration_id=$(echo "$response" | python3 -c "import json, sys; print(json.load(sys.stdin).get('migration_id', ''))")

if [ -z "$migration_id" ]; then
    echo -e "${RED}❌ Failed to start migrations${NC}"
    echo "$response" | python3 -m json.tool
    exit 1
fi

echo -e "${GREEN}✅ Migration started with ID: $migration_id${NC}"
echo ""

# Poll for status
echo -e "${CYAN}⏳ Monitoring migration progress...${NC}"

max_attempts=60  # 5 minutes max
attempt=0

while [ $attempt -lt $max_attempts ]; do
    status_response=$(curl -s "http://localhost:8000/api/v1/migrations/$migration_id")
    status=$(echo "$status_response" | python3 -c "import json, sys; print(json.load(sys.stdin).get('status', ''))" 2>/dev/null || echo "unknown")
    
    # Extract progress information
    progress=$(echo "$status_response" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    p = data.get('progress', {})
    if p:
        print(f\"Phase: {p.get('current_phase', 'unknown')} | Databases: {p.get('completed_databases', 0)}/{p.get('total_databases', 0)} | Schemas: {p.get('completed_schemas', 0)}/{p.get('total_schemas', 0)}\")
except: pass" 2>/dev/null)
    
    case "$status" in
        "completed")
            echo -e "\n${GREEN}✅ Migrations completed successfully!${NC}"
            echo -e "${CYAN}Final status:${NC}"
            echo "$status_response" | python3 -m json.tool 2>/dev/null || echo "$status_response"
            break
            ;;
        "failed")
            echo -e "\n${RED}❌ Migrations failed${NC}"
            echo -e "${RED}Error details:${NC}"
            echo "$status_response" | python3 -m json.tool 2>/dev/null || echo "$status_response"
            exit 1
            ;;
        "in_progress")
            if [ -n "$progress" ]; then
                echo -ne "\r${CYAN}⏳ $progress${NC}                    "
            else
                echo -n "."
            fi
            sleep 5
            ((attempt++))
            ;;
        *)
            echo -e "\n${YELLOW}⚠️  Unknown status: $status${NC}"
            echo "$status_response" | python3 -m json.tool 2>/dev/null || echo "$status_response"
            sleep 5
            ((attempt++))
            ;;
    esac
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "\n${RED}❌ Migration timeout${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}📊 Final migration status:${NC}"
curl -s http://localhost:8000/api/v1/migrations/dynamic/status | python3 -m json.tool 2>/dev/null || {
    echo -e "${YELLOW}⚠️  Could not fetch final status${NC}"
}

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 Dynamic migrations complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "All regional databases have been migrated using connection info from admin.database_connections"