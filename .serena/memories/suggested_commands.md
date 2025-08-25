# Essential Development Commands

## Infrastructure Management
```bash
# Deploy complete infrastructure with migrations
cd NeoInfrastructure
./deploy.sh                    # Deploy infrastructure + run migrations
./deploy.sh --seed            # Deploy + seed initial data

# Alternative deployment from root
./deploy.dev.sh               # Master deployment script

# Infrastructure control
./stop.sh                     # Stop all services
./reset.sh                    # Reset and rebuild everything
```

## Database Operations
```bash
# Check migration status
curl http://localhost:8000/api/v1/migrations/status

# Apply migrations
curl -X POST http://localhost:8000/api/v1/migrations/apply

# View Flyway migration history
docker exec neo-postgres-us-east psql -U postgres -d neofast_admin -c "SELECT * FROM flyway_schema_history ORDER BY installed_rank;"
```

## Development Workflow
```bash
# Start only infrastructure
cd NeoInfrastructure
./scripts/start-infrastructure.sh

# Health checks
./scripts/utilities/health-check.sh
./scripts/utilities/verify-schema-separation.sh

# Check container logs
docker logs neo-deployment-api -f
docker logs neo-postgres-us-east -f
```

## Testing
```bash
# Infrastructure tests
cd NeoInfrastructure
pytest migrations/tests/

# API tests
cd NeoAdminApi
pytest tests/

# Frontend tests
cd NeoAdmin
npm test
npm run test:e2e
```

## Service Ports
- Deployment API: 8000
- Admin API: 8001  
- Tenant API: 8002
- Marketing Site: 3000
- Admin Dashboard: 3001
- Tenant Admin: 3002
- Tenant Frontend: 3003
- PostgreSQL US: 5432
- PostgreSQL EU: 5433
- Redis: 6379
- Keycloak: 8080