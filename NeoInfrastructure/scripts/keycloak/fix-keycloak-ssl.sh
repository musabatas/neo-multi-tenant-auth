#!/bin/bash
# Fix Keycloak SSL requirement for development
# This script uses Keycloak CLI inside the container to disable SSL
# Based on OLD_PROJECT implementation

set -e

echo "Configuring Keycloak for development (disabling SSL requirements)..."
echo "⏳ Waiting for Keycloak to fully initialize..."
sleep 30  # Give Keycloak sufficient time to be fully ready

# Get the project root directory (two levels up from scripts/keycloak/)
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

# Disable SSL requirement using Keycloak admin CLI
echo "Authenticating with Keycloak admin..."
docker-compose -f docker/docker-compose.infrastructure.yml exec -T keycloak /opt/keycloak/bin/kcadm.sh config credentials \
    --server http://localhost:8080 \
    --realm master \
    --user admin \
    --password admin

# Set SSL requirement to NONE for master realm (uppercase as expected by Keycloak)
echo "Updating master realm to disable SSL..."
docker-compose -f docker/docker-compose.infrastructure.yml exec -T keycloak /opt/keycloak/bin/kcadm.sh update realms/master \
    -s sslRequired=NONE \
    -s enabled=true

echo "✅ Keycloak SSL requirements disabled for development"
echo ""
echo "🌐 Keycloak should now be accessible at:"
echo "   - Admin Console: http://localhost:8080/admin"
echo "   - Master Realm: http://localhost:8080/realms/master"