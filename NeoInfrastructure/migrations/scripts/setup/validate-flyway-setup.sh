#!/bin/bash
# Validate Flyway Setup and Configuration
set -e

echo "🧪 Validating Flyway Setup"
echo "=========================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

MIGRATIONS_DIR="/Users/musabatas/Workspaces/NeoMultiTenant/NeoInfrastructure/migrations"

# Function to check file exists
check_file() {
    local file=$1
    local description=$2
    
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ $description${NC}"
        return 0
    else
        echo -e "${RED}❌ $description - NOT FOUND${NC}"
        return 1
    fi
}

# Function to check directory exists
check_dir() {
    local dir=$1
    local description=$2
    
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✅ $description${NC}"
        return 0
    else
        echo -e "${RED}❌ $description - NOT FOUND${NC}"
        return 1
    fi
}

echo -e "${BLUE}1. Checking Directory Structure...${NC}"
check_dir "$MIGRATIONS_DIR" "Migrations directory"
check_dir "$MIGRATIONS_DIR/flyway" "Flyway directory"
# Config directory no longer needed - using dynamic configuration
check_dir "$MIGRATIONS_DIR/flyway/global" "Global migrations directory"
check_dir "$MIGRATIONS_DIR/flyway/regional" "Regional migrations directory"

echo ""
echo -e "${BLUE}2. Checking Configuration Files...${NC}"
check_file "$MIGRATIONS_DIR/Dockerfile" "Dockerfile"
check_file "$MIGRATIONS_DIR/docker-compose.migrations.yml" "Docker Compose file"
check_file "$MIGRATIONS_DIR/orchestrator/dynamic_migration_engine.py" "Dynamic migration engine"
check_file "$MIGRATIONS_DIR/orchestrator/encryption.py" "Encryption module"
echo -e "${GREEN}✅ Using dynamic configuration - no static config files needed${NC}"

echo ""
echo -e "${BLUE}3. Checking Migration Files...${NC}"
check_file "$MIGRATIONS_DIR/flyway/global/V001__platform_common_schema.sql" "V001 migration"
check_file "$MIGRATIONS_DIR/flyway/global/V008__admin_migration_management.sql" "V008 migration"

echo ""
echo -e "${BLUE}4. Building Docker Image...${NC}"
cd "$MIGRATIONS_DIR"
if docker build -t neo-migrations-test . > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Docker image built successfully${NC}"
else
    echo -e "${RED}❌ Docker image build failed${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}5. Testing Flyway Installation...${NC}"
if docker run --rm neo-migrations-test flyway --version 2>/dev/null | grep -q "Flyway"; then
    VERSION=$(docker run --rm neo-migrations-test flyway --version 2>/dev/null | head -1)
    echo -e "${GREEN}✅ Flyway installed: $VERSION${NC}"
else
    echo -e "${RED}❌ Flyway not properly installed${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}6. Checking Dynamic Migration Engine...${NC}"
if docker run --rm -v "$MIGRATIONS_DIR/orchestrator:/app/orchestrator:ro" neo-migrations-test \
    test -f "/app/orchestrator/dynamic_migration_engine.py" 2>/dev/null; then
    echo -e "${GREEN}✅ Dynamic migration engine accessible in container${NC}"
else
    echo -e "${RED}❌ Dynamic migration engine NOT accessible in container${NC}"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ FLYWAY SETUP VALIDATION COMPLETE!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Deploy infrastructure: ./deploy.sh"
echo "2. Run dynamic migrations: ./run-dynamic-migrations.sh"
echo "3. Check migration status: curl http://localhost:8000/api/v1/migrations/dynamic/status"