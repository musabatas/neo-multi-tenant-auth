# Keycloak Providers

Custom providers and extensions for NeoMultiTenant platform.

## Directory Structure

```
providers/
├── custom-user-storage/     # Custom user storage providers
├── multi-tenant-auth/       # Multi-tenant authentication logic
└── region-selector/         # Region-based authentication routing
```

## Provider Types

- **User Storage Providers**: Custom user database integration
- **Authentication Flows**: Multi-tenant login logic
- **Event Listeners**: Audit logging and analytics
- **Protocol Mappers**: Custom token claims

## Future Providers

- Regional user storage routing
- Tenant-aware authentication
- Advanced audit logging
- Custom protocol mappers for multi-region setup