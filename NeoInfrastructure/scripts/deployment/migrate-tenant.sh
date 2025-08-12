#!/bin/bash
# NeoMultiTenant - Migrate Individual Tenant Schema
# This script creates and migrates a schema for a specific tenant

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Default values
API_URL="http://localhost:8000"
DRY_RUN=false

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS] --tenant-id <id> --tenant-slug <slug> --database <db> --schema <schema>"
    echo ""
    echo "Required arguments:"
    echo "  --tenant-id <id>        Tenant ID (e.g., 123e4567-e89b-12d3-a456-426614174000)"
    echo "  --tenant-slug <slug>    Tenant slug (e.g., acme-corp)"
    echo "  --database <db>         Target database (e.g., neofast_shared_us)"
    echo "  --schema <schema>       Schema name (e.g., tenant_acme_corp)"
    echo ""
    echo "Optional arguments:"
    echo "  --api-url <url>         API URL (default: http://localhost:8000)"
    echo "  --dry-run              Show what would be done without executing"
    echo "  --no-create-schema     Skip schema creation (use existing schema)"
    echo "  --help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --tenant-id 123e4567 --tenant-slug acme-corp --database neofast_shared_us --schema tenant_acme_corp"
    echo "  $0 --tenant-id 123e4567 --tenant-slug acme-corp --database neofast_shared_us --schema tenant_acme_corp --dry-run"
    exit 1
}

# Parse command line arguments
TENANT_ID=""
TENANT_SLUG=""
DATABASE=""
SCHEMA=""
CREATE_SCHEMA=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --tenant-id)
            TENANT_ID="$2"
            shift 2
            ;;
        --tenant-slug)
            TENANT_SLUG="$2"
            shift 2
            ;;
        --database)
            DATABASE="$2"
            shift 2
            ;;
        --schema)
            SCHEMA="$2"
            shift 2
            ;;
        --api-url)
            API_URL="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --no-create-schema)
            CREATE_SCHEMA=false
            shift
            ;;
        --help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate required arguments
if [ -z "$TENANT_ID" ] || [ -z "$TENANT_SLUG" ] || [ -z "$DATABASE" ] || [ -z "$SCHEMA" ]; then
    echo -e "${RED}❌ Missing required arguments${NC}"
    usage
fi

echo "🚀 NeoMultiTenant - Tenant Migration"
echo "===================================="
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "  Tenant ID:      $TENANT_ID"
echo "  Tenant Slug:    $TENANT_SLUG"
echo "  Database:       $DATABASE"
echo "  Schema:         $SCHEMA"
echo "  Create Schema:  $CREATE_SCHEMA"
echo "  API URL:        $API_URL"
echo "  Dry Run:        $DRY_RUN"
echo ""

# Check if API is running
echo -e "${CYAN}🔍 Checking API health...${NC}"
if ! curl -s "$API_URL/health" > /dev/null 2>&1; then
    echo -e "${RED}❌ Deployment API is not running at $API_URL${NC}"
    echo "   Please run: ./deploy.sh first"
    exit 1
fi
echo -e "${GREEN}✅ API is healthy${NC}"
echo ""

# Check current schema version (if exists)
echo -e "${CYAN}📊 Checking current schema status...${NC}"
version_response=$(curl -s "$API_URL/api/v1/tenants/$TENANT_ID/version?database=$DATABASE&schema=$SCHEMA")
current_version=$(echo "$version_response" | python3 -c "import json, sys; data = json.load(sys.stdin); print(data.get('current_version', 'N/A'))" 2>/dev/null || echo "N/A")
pending_migrations=$(echo "$version_response" | python3 -c "import json, sys; data = json.load(sys.stdin); print(data.get('pending_migrations', 0))" 2>/dev/null || echo "0")

if [ "$current_version" != "N/A" ] && [ "$current_version" != "null" ]; then
    echo -e "  Current Version: ${GREEN}$current_version${NC}"
    echo -e "  Pending Migrations: ${YELLOW}$pending_migrations${NC}"
else
    echo -e "  Schema Status: ${YELLOW}Not yet created${NC}"
fi
echo ""

# Prepare migration request
REQUEST_BODY=$(cat <<EOF
{
    "tenant_id": "$TENANT_ID",
    "tenant_slug": "$TENANT_SLUG",
    "database": "$DATABASE",
    "schema": "$SCHEMA",
    "create_schema": $CREATE_SCHEMA
}
EOF
)

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}🔍 DRY RUN MODE - Showing request that would be sent:${NC}"
    echo "$REQUEST_BODY" | python3 -m json.tool
    echo ""
    echo -e "${YELLOW}No changes will be made.${NC}"
    exit 0
fi

# Trigger tenant migration
echo -e "${CYAN}🔄 Triggering tenant migration...${NC}"
response=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$REQUEST_BODY" \
    "$API_URL/api/v1/tenants/$TENANT_ID/migrate")

migration_id=$(echo "$response" | python3 -c "import json, sys; print(json.load(sys.stdin).get('migration_id', ''))" 2>/dev/null || echo "")

if [ -z "$migration_id" ]; then
    echo -e "${RED}❌ Failed to start migration${NC}"
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
    status_response=$(curl -s "$API_URL/api/v1/migrations/$migration_id")
    status=$(echo "$status_response" | python3 -c "import json, sys; print(json.load(sys.stdin).get('status', ''))" 2>/dev/null || echo "unknown")
    
    case "$status" in
        "completed")
            echo -e "\n${GREEN}✅ Migration completed successfully!${NC}"
            break
            ;;
        "failed")
            echo -e "\n${RED}❌ Migration failed${NC}"
            echo "$status_response" | python3 -m json.tool
            exit 1
            ;;
        "in_progress")
            echo -n "."
            sleep 2
            ((attempt++))
            ;;
        *)
            echo -e "\n${YELLOW}⚠️  Unknown status: $status${NC}"
            sleep 2
            ((attempt++))
            ;;
    esac
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "\n${RED}❌ Migration timeout${NC}"
    exit 1
fi

# Show final schema version
echo ""
echo -e "${CYAN}📊 Final schema status:${NC}"
final_version=$(curl -s "$API_URL/api/v1/tenants/$TENANT_ID/version?database=$DATABASE&schema=$SCHEMA")
echo "$final_version" | python3 -m json.tool

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 Tenant migration complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Tenant '$TENANT_SLUG' schema '$SCHEMA' has been created and migrated in database '$DATABASE'"