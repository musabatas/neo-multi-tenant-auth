#!/bin/bash
# NeoInfrastructure - Reset Development Infrastructure
# Stops services and optionally cleans up data

set -e

echo "🔄 NeoInfrastructure Reset Utility"
echo "=================================="

# Get the actual script location (resolving symlinks)
SCRIPT_PATH="$(readlink -f "$0" 2>/dev/null || readlink "$0" 2>/dev/null || echo "$0")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Parse command line arguments
CLEAN_DATA=false
CLEAN_IMAGES=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --clean-data)
            CLEAN_DATA=true
            shift
            ;;
        --clean-images)
            CLEAN_IMAGES=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help)
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --clean-data    Remove all data volumes (PostgreSQL, Redis, Keycloak data)"
            echo "  --clean-images  Remove downloaded Docker images"
            echo "  --force         Skip confirmation prompts"
            echo "  --help          Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Stop services only"
            echo "  $0 --clean-data      # Stop services and remove data"
            echo "  $0 --clean-data --clean-images --force  # Full cleanup"
            echo ""
            exit 0
            ;;
        *)
            echo "❌ Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Confirmation before stopping services (unless --force is used)
if [ "$FORCE" = false ]; then
    echo "⚠️  This will stop all NeoInfrastructure services:"
    echo "   • PostgreSQL databases (US East & EU West)"
    echo "   • Redis cache"
    echo "   • Keycloak authentication"
    echo "   • Migration API service"
    echo "   • Any running migration containers"
    echo ""
    read -p "Are you sure you want to continue? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Reset cancelled"
        exit 0
    fi
fi

# Use the stop.sh script to stop all services including API
"$SCRIPT_DIR/stop.sh"

# Clean data volumes if requested
if [ "$CLEAN_DATA" = true ]; then
    echo ""
    echo "🗑️  Data cleanup requested..."
    
    if [ "$FORCE" = false ]; then
        echo "⚠️  This will permanently delete ALL infrastructure data:"
        echo "   • PostgreSQL US East data (all databases and schemas)"
        echo "   • PostgreSQL EU West data (all databases and schemas)"  
        echo "   • Redis cache data"
        echo "   • Keycloak configuration and realms"
        echo "   • pgAdmin settings"
        echo "   • RedisInsight configuration"
        echo ""
        read -p "Are you sure you want to continue? (y/N) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "❌ Data cleanup cancelled"
            exit 0
        fi
    fi
    
    echo "🗑️  Removing data volumes..."
    
    # Remove named volumes
    docker volume rm -f neo_postgres_us_east_data 2>/dev/null || true
    docker volume rm -f neo_postgres_eu_west_data 2>/dev/null || true
    docker volume rm -f neo_redis_data 2>/dev/null || true
    docker volume rm -f neo_keycloak_data 2>/dev/null || true
    docker volume rm -f neo_pgadmin_data 2>/dev/null || true
    docker volume rm -f neo_redisinsight_data 2>/dev/null || true
    
    echo "✅ Data volumes removed"
fi

# Clean Docker images if requested
if [ "$CLEAN_IMAGES" = true ]; then
    echo ""
    echo "🗑️  Image cleanup requested..."
    
    if [ "$FORCE" = false ]; then
        echo "⚠️  This will remove downloaded Docker images:"
        echo "   • PostgreSQL (supabase/postgres:17.4.1.032)"
        echo "   • Redis (redis:7-alpine)"
        echo "   • Keycloak (quay.io/keycloak/keycloak:26.3.2)"
        echo "   • pgAdmin (dpage/pgadmin4:latest)"
        echo "   • RedisInsight (redislabs/redisinsight:latest)"
        echo ""
        read -p "Remove these images? (y/N) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "❌ Image cleanup cancelled"
            exit 0
        fi
    fi
    
    echo "🗑️  Removing Docker images..."
    
    # Remove infrastructure images
    docker rmi -f supabase/postgres:17.4.1.032 2>/dev/null || true
    docker rmi -f redis:7-alpine 2>/dev/null || true
    docker rmi -f quay.io/keycloak/keycloak:26.3.2 2>/dev/null || true
    docker rmi -f dpage/pgadmin4:latest 2>/dev/null || true
    docker rmi -f redislabs/redisinsight:latest 2>/dev/null || true
    
    echo "✅ Docker images removed"
fi

# Clean up orphaned networks
echo ""
echo "🧹 Cleaning up orphaned networks..."
docker network rm neo-infrastructure 2>/dev/null || true

# Show final status
echo ""
echo "🎉 NeoInfrastructure reset complete!"
echo ""

if [ "$CLEAN_DATA" = true ]; then
    echo "📊 Data Status: ❌ All data removed (fresh start)"
else
    echo "📊 Data Status: ✅ Data preserved (quick restart)"
fi

if [ "$CLEAN_IMAGES" = true ]; then
    echo "🐳 Images Status: ❌ Images removed (will re-download on next start)"
else
    echo "🐳 Images Status: ✅ Images preserved (faster restart)"
fi

echo ""
echo "💡 To start infrastructure again:"
echo "   ./scripts/start-infrastructure.sh"
echo ""
echo "💡 Reset options:"
echo "   ./scripts/reset-infrastructure.sh --help"