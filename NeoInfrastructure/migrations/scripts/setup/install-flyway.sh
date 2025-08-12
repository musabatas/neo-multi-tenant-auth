#!/bin/bash
# Install real Flyway in the container
set -e

FLYWAY_VERSION=${FLYWAY_VERSION:-10.21.0}
FLYWAY_URL="https://download.flywaydb.org/flyway-commandline-${FLYWAY_VERSION}-linux-x64.tar.gz"

echo "🔄 Installing Flyway ${FLYWAY_VERSION}..."

# Try to download Flyway
if curl -fsSL "$FLYWAY_URL" | tar -xz -C /opt; then
    echo "✅ Flyway downloaded successfully"
    
    # Move and setup Flyway
    sudo mv /opt/flyway-${FLYWAY_VERSION} /opt/flyway
    sudo chmod +x /opt/flyway/flyway
    sudo rm -f /usr/local/bin/flyway  # Remove mock
    sudo ln -s /opt/flyway/flyway /usr/local/bin/flyway
    
    echo "✅ Flyway installation completed"
    flyway -version
else
    echo "❌ Failed to download Flyway - keeping mock version"
    echo "💡 You can run migrations manually with SQL files"
fi