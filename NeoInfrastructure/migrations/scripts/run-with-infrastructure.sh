#!/bin/bash
# Run NeoMigrations with NeoInfrastructure
set -e

echo "🚀 Starting NeoMigrations with Infrastructure Integration"

# Check if infrastructure is running
if ! docker network ls | grep -q neo-infrastructure; then
    echo "Creating neo-infrastructure network..."
    docker network create neo-infrastructure
fi

# Check if infrastructure containers are running
if ! docker ps | grep -q neo-postgres-us-east; then
    echo "⚠️  NeoInfrastructure not running. Starting it first..."
    
    if [ -d "../NeoInfrastructure" ]; then
        cd ../NeoInfrastructure
        echo "🏗️  Starting infrastructure services..."
        ./scripts/deployment/deploy.sh
        cd - > /dev/null
        
        echo "⏳ Waiting for databases to be ready..."
        sleep 10
    else
        echo "❌ NeoInfrastructure directory not found"
        echo "💡 Please start infrastructure manually first"
        exit 1
    fi
fi

echo "🔄 Running database migrations..."

# Option 1: Run migrations in existing network
docker-compose -f docker-compose.migrations.yml run --rm neo-migrations python orchestrator/migration_manager.py migrate

# Option 2: Alternative - run with both compose files
# docker-compose -f ../NeoInfrastructure/docker/docker-compose.infrastructure.yml \
#                -f docker-compose.migrations.yml \
#                run --rm neo-migrations python orchestrator/migration_manager.py migrate

echo "✅ Migrations completed!"
echo ""
echo "🌐 Access your services:"
echo "   📊 PostgreSQL US: localhost:5432"
echo "   🇪🇺 PostgreSQL EU: localhost:5433" 
echo "   🔴 Redis: localhost:6379"
echo "   Keycloak: http://localhost:8080"