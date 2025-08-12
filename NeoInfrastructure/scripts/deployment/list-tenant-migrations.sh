#!/bin/bash
# NeoMultiTenant - List Tenant Migration Status
# This script shows all tenants and their schema migration status

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
ADMIN_DB_HOST="${POSTGRES_US_HOST:-neo-postgres-us-east}"
ADMIN_DB_PORT="${POSTGRES_US_PORT:-5432}"
ADMIN_DB_NAME="neofast_admin"
ADMIN_DB_USER="${POSTGRES_USER:-postgres}"
ADMIN_DB_PASS="${POSTGRES_PASSWORD:-postgres}"

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Optional arguments:"
    echo "  --api-url <url>    API URL (default: http://localhost:8000)"
    echo "  --region <region>  Filter by region (us-east-1, eu-west-1)"
    echo "  --help             Show this help message"
    echo ""
    exit 1
}

# Parse command line arguments
REGION_FILTER=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --api-url)
            API_URL="$2"
            shift 2
            ;;
        --region)
            REGION_FILTER="$2"
            shift 2
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

echo "🚀 NeoMultiTenant - Tenant Migration Status"
echo "=========================================="
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

# Query tenants from admin database
echo -e "${CYAN}📊 Fetching tenant information...${NC}"

QUERY="
SELECT 
    t.id as tenant_id,
    t.slug as tenant_slug,
    t.name as tenant_name,
    t.status as tenant_status,
    ts.database_name,
    ts.schema_name,
    ts.region_code,
    ts.status as schema_status,
    ts.created_at
FROM admin.tenants t
LEFT JOIN admin.tenant_schemas ts ON t.id = ts.tenant_id
WHERE 1=1
"

if [ -n "$REGION_FILTER" ]; then
    QUERY="$QUERY AND ts.region_code = '$REGION_FILTER'"
fi

QUERY="$QUERY ORDER BY t.created_at DESC, ts.region_code"

# Execute query
export PGPASSWORD="$ADMIN_DB_PASS"
TENANTS=$(psql -h "$ADMIN_DB_HOST" -p "$ADMIN_DB_PORT" -U "$ADMIN_DB_USER" -d "$ADMIN_DB_NAME" -t -A -F"|" -c "$QUERY" 2>/dev/null || echo "")

if [ -z "$TENANTS" ]; then
    echo -e "${YELLOW}No tenants found${NC}"
    echo ""
    echo "Note: This script queries the admin.tenants table."
    echo "Make sure you have created tenants in the system."
    exit 0
fi

echo -e "${GREEN}✅ Found tenants${NC}"
echo ""

# Display tenant information
echo -e "${BLUE}Tenant Schema Status:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
printf "%-36s %-20s %-10s %-25s %-20s %-10s\n" "Tenant ID" "Slug" "Status" "Database" "Schema" "Region"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Process each tenant
while IFS='|' read -r tenant_id tenant_slug tenant_name tenant_status database_name schema_name region_code schema_status created_at; do
    if [ -n "$tenant_id" ]; then
        # Check migration status if schema exists
        if [ -n "$schema_name" ] && [ -n "$database_name" ]; then
            # Get current version from API
            version_response=$(curl -s "$API_URL/api/v1/tenants/$tenant_id/version?database=$database_name&schema=$schema_name" 2>/dev/null || echo "{}")
            current_version=$(echo "$version_response" | python3 -c "import json, sys; data = json.load(sys.stdin); print(data.get('current_version', 'N/A'))" 2>/dev/null || echo "N/A")
            
            if [ "$current_version" != "N/A" ] && [ "$current_version" != "null" ]; then
                version_status="${GREEN}v$current_version${NC}"
            else
                version_status="${YELLOW}Not migrated${NC}"
            fi
        else
            database_name="${YELLOW}Not assigned${NC}"
            schema_name="${YELLOW}Not created${NC}"
            region_code="${YELLOW}-${NC}"
            version_status=""
        fi
        
        # Color code tenant status
        case "$tenant_status" in
            "active")
                status_color="${GREEN}$tenant_status${NC}"
                ;;
            "suspended")
                status_color="${YELLOW}$tenant_status${NC}"
                ;;
            *)
                status_color="${RED}$tenant_status${NC}"
                ;;
        esac
        
        printf "%-36s %-20s %-10b %-25s %-20s %-10s %-15b\n" \
            "$tenant_id" "$tenant_slug" "$status_color" "$database_name" "$schema_name" "$region_code" "$version_status"
    fi
done <<< "$TENANTS"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Show migration commands
echo ""
echo -e "${BLUE}To migrate a tenant schema:${NC}"
echo "  ./migrate-tenant.sh --tenant-id <id> --tenant-slug <slug> --database <db> --schema <schema>"
echo ""
echo -e "${BLUE}To run all pending migrations:${NC}"
echo "  ./run-dynamic-migrations.sh"
echo ""