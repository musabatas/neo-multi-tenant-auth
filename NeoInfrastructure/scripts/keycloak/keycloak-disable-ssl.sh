#!/bin/bash
# Standalone script to disable Keycloak SSL
# Use this if Keycloak is already running but SSL needs to be disabled

set -e

echo "🔧 Disabling Keycloak SSL requirements..."

# Get the project root directory (one level up from scripts/)
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# Check if Keycloak container is running
if ! docker-compose -f docker/docker-compose.infrastructure.yml ps keycloak | grep -q "Up"; then
    echo "❌ Keycloak container is not running"
    echo "💡 Start infrastructure first: ./scripts/start-infrastructure.sh"
    exit 1
fi

# Use the dedicated SSL fix script
if [ -f "$PROJECT_ROOT/scripts/fix-keycloak-ssl.sh" ]; then
    "$PROJECT_ROOT/scripts/fix-keycloak-ssl.sh"
else
    echo "❌ SSL fix script not found at: $PROJECT_ROOT/scripts/fix-keycloak-ssl.sh"
    exit 1
fi