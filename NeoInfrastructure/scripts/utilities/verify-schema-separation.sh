#!/bin/bash
# Verify schema separation in migration history

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Schema Migration History Verification${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Function to check migration history
check_history() {
    local database=$1
    local schema=$2
    local expected_migrations=$3
    
    echo -e "${CYAN}Checking $schema.flyway_schema_history in $database:${NC}"
    
    # Check if table exists
    exists=$(docker exec neo-postgres-us-east psql -U postgres -d $database -t -c "
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = '$schema' 
            AND table_name = 'flyway_schema_history'
        );
    " | tr -d ' ')
    
    if [ "$exists" = "t" ]; then
        echo -e "${GREEN}✅ History table exists${NC}"
        
        # Show migrations
        echo -e "${YELLOW}Migrations:${NC}"
        docker exec neo-postgres-us-east psql -U postgres -d $database -c "
            SELECT version, description, success 
            FROM $schema.flyway_schema_history 
            WHERE version IS NOT NULL
            ORDER BY installed_rank;
        "
        
        # Count migrations
        count=$(docker exec neo-postgres-us-east psql -U postgres -d $database -t -c "
            SELECT COUNT(*) 
            FROM $schema.flyway_schema_history 
            WHERE version IS NOT NULL;
        " | tr -d ' ')
        
        echo -e "Total migrations: $count (expected: $expected_migrations)"
        
        if [ "$count" -eq "$expected_migrations" ]; then
            echo -e "${GREEN}✅ Correct number of migrations${NC}"
        else
            echo -e "${RED}❌ Incorrect number of migrations${NC}"
        fi
    else
        echo -e "${RED}❌ History table does not exist${NC}"
    fi
    
    echo ""
}

# Check admin database
echo -e "${BLUE}1. Admin Database (neofast_admin)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

check_history "neofast_admin" "platform_common" 1  # V0001
check_history "neofast_admin" "admin" 8            # V1001-V1008

# Show all history tables
echo -e "${BLUE}2. All Migration History Tables${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

docker exec neo-postgres-us-east psql -U postgres -d neofast_admin -c "
    SELECT 
        n.nspname as schema,
        c.relname as table_name,
        pg_size_pretty(pg_total_relation_size(c.oid)) as size
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = 'flyway_schema_history'
    ORDER BY n.nspname;
"

# Check for cross-schema pollution
echo -e "\n${BLUE}3. Cross-Schema Pollution Check${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

echo -e "${CYAN}Checking if admin history contains platform_common migrations:${NC}"
pollution=$(docker exec neo-postgres-us-east psql -U postgres -d neofast_admin -t -c "
    SELECT COUNT(*) 
    FROM admin.flyway_schema_history 
    WHERE version = '0001';
" | tr -d ' ')

if [ "$pollution" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Admin history contains platform_common migrations${NC}"
    echo -e "This suggests migrations were run with combined config instead of separate configs"
else
    echo -e "${GREEN}✅ No cross-schema pollution detected${NC}"
fi

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Verification Complete${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"