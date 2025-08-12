#!/bin/bash
# NeoMultiTenant - Master Deployment Script
# One command to deploy the entire enterprise platform

# Get the absolute path of the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 NeoMultiTenant Master Deployment"
echo "Deploying complete enterprise platform..."
echo ""

# Run the complete deployment
exec "$SCRIPT_DIR/NeoInfrastructure/deploy.sh"
