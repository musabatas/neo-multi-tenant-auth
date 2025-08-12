# NeoInfrastructure Scripts

This directory contains all operational scripts for managing the NeoInfrastructure.

## Directory Structure

```
scripts/
├── deployment/     # Core deployment and lifecycle management
├── testing/        # Test scripts and validation tools
├── utilities/      # Helper scripts and tools
├── keycloak/       # Keycloak-specific scripts
└── README.md       # This file
```

## Deployment Scripts (`deployment/`)

Main scripts for deploying and managing the infrastructure:

- **`deploy.sh`** - Main deployment script that sets up everything (infrastructure, migrations, API)
  - Use `--seed` flag to also populate initial data
- **`stop.sh`** - Gracefully stops all services including migrations API
- **`reset.sh`** - Resets infrastructure with options for data/image cleanup
- **`start-api.sh`** - Starts the deployment API service
- **`run-dynamic-migrations.sh`** - Runs dynamic database migrations
- **`run-seeds.sh`** - Runs seed data independently (populates regions and database connections)

## Testing Scripts (`testing/`)

Scripts for testing various components:

- **`test-infrastructure.sh`** - Tests all infrastructure services
- **`test-schema-migration.sh`** - Tests database schema migrations
- **`test-flyway.sh`** - Tests Flyway migration system
- **`test_encryption.py`** - Tests password encryption functionality
- **`test_encryption_integration.sh`** - Integration tests for encryption
- **`test-dependency-resolver.py`** - Tests migration dependency resolution

## Utility Scripts (`utilities/`)

Helper scripts for various operations:

- **`health-check.sh`** - Comprehensive health check for all services
- **`verify-schema-separation.sh`** - Verifies schema isolation
- **`encrypt_password.py`** - Encrypts passwords for database storage
- **`update_database_passwords.py`** - Updates database passwords in admin table
- **`fix-pgcrypto.sh`** - Fixes pgcrypto extension issues

## Keycloak Scripts (`keycloak/`)

Keycloak-specific configuration scripts:

- **`fix-keycloak-ssl.sh`** - Configures Keycloak SSL settings for development
- **`keycloak-disable-ssl.sh`** - Disables SSL requirement for development

## Quick Start

The main entry points are available as symlinks in the project root:

```bash
# Deploy everything
./deploy.sh

# Stop all services
./stop.sh

# Reset infrastructure (with prompts)
./reset.sh

# Reset with data cleanup
./reset.sh --clean-data --force
```

## Migration Scripts

Migration-specific scripts are located in `migrations/scripts/`:

- **`clean-migration.sh`** - Cleans migration history
- **`deploy-with-flyway.sh`** - Deploys using Flyway
- **`run-with-infrastructure.sh`** - Runs migrations with infrastructure
- **`setup/install-flyway.sh`** - Installs Flyway
- **`setup/validate-flyway-setup.sh`** - Validates Flyway configuration