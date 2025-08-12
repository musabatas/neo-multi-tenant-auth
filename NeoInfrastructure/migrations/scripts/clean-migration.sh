#!/bin/bash
# Clean migration script demonstrating proper schema separation

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Clean Schema-Separated Migration Demo${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Database connection details
DB_HOST="${POSTGRES_US_HOST:-neo-postgres-us-east}"
DB_PORT="${POSTGRES_US_PORT:-5432}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_PASSWORD="${POSTGRES_PASSWORD:-postgres}"

# Function to run migration for a specific schema
migrate_schema() {
    local database=$1
    local schema=$2
    local location=$3
    local description=$4
    
    echo -e "${CYAN}🔄 Migrating $database.$schema - $description${NC}"
    
    # Create temporary config
    cat > /tmp/flyway-$schema.conf << EOF
flyway.url=jdbc:postgresql://$DB_HOST:$DB_PORT/$database
flyway.user=$DB_USER
flyway.password=$DB_PASSWORD
flyway.schemas=$schema
flyway.defaultSchema=$schema
flyway.table=flyway_schema_history
flyway.locations=filesystem:/app/flyway/$location
flyway.baselineOnMigrate=true
flyway.validateOnMigrate=false
flyway.cleanDisabled=true
flyway.mixed=true
flyway.outOfOrder=true
EOF

    # Run migration
    flyway -configFiles=/tmp/flyway-$schema.conf migrate
    
    echo -e "${GREEN}✅ $schema migration complete → $schema.flyway_schema_history${NC}\n"
    
    # Clean up
    rm -f /tmp/flyway-$schema.conf
}

# Migrate admin database
echo -e "${YELLOW}1. Admin Database (neofast_admin)${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Order matters: platform_common first (dependency)
migrate_schema "neofast_admin" "platform_common" "platform" "Shared functions and types"
migrate_schema "neofast_admin" "admin" "admin" "Admin tables and data"

# Show results
echo -e "${BLUE}Migration Results:${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d neofast_admin << EOF
-- Show history tables
SELECT 
    n.nspname as schema,
    COUNT(*) as migrations
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN (
    SELECT schemaname, COUNT(*) as count
    FROM (
        SELECT 'platform_common' as schemaname, version FROM platform_common.flyway_schema_history WHERE version IS NOT NULL
        UNION ALL
        SELECT 'admin' as schemaname, version FROM admin.flyway_schema_history WHERE version IS NOT NULL
    ) t
    GROUP BY schemaname
) counts ON counts.schemaname = n.nspname
WHERE c.relname = 'flyway_schema_history'
GROUP BY n.nspname
ORDER BY n.nspname;
EOF

echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Clean Migration Complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "\nEach schema now has its own migration history:"
echo -e "• platform_common.flyway_schema_history - Platform migrations only"
echo -e "• admin.flyway_schema_history - Admin migrations only"