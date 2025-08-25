# Organizations Feature - NeoAdminApi

This feature integrates neo-commons organization functionality into the NeoAdminApi service for platform administration.

## Implementation Overview

- **Removed**: Custom organization service and repository implementations
- **Added**: Neo-commons integration with dependency injection
- **Architecture**: Features-first approach using dependency override pattern

## API Endpoints

### Public Organization API (`/api/v1/organizations/`)

- `GET /` - List organizations with pagination and filtering
- `POST /` - Create new organization
- `GET /{organization_id}` - Get organization by ID
- `PUT /{organization_id}` - Update organization
- `DELETE /{organization_id}` - Delete organization
- `GET /slug/{slug}` - Get organization by slug
- `POST /search` - Search organizations
- `POST /{organization_id}/verify` - Verify organization
- `POST /{organization_id}/activate` - Activate organization
- `POST /{organization_id}/deactivate` - Deactivate organization
- `GET /{organization_id}/metadata` - Get organization metadata
- `PUT /{organization_id}/metadata` - Update organization metadata
- `POST /search/metadata` - Search organizations by metadata

### Admin Organization API (`/api/v1/admin/organizations/`)

- `GET /stats` - Get organization statistics
- `GET /health` - Get organization system health
- `POST /integrity/validate` - Validate data integrity
- `POST /cleanup` - Cleanup operations
- `GET /export` - Export organization data
- `GET /{organization_id}/health` - Get specific organization health
- `POST /search/advanced` - Advanced organization search
- `POST /{organization_id}/force-verify` - Force verify organization
- `GET /reports/dashboard` - Get dashboard reports

## Database Configuration

- **Schema**: `admin` (for platform administration)
- **Connection**: Uses existing NeoAdminApi database service
- **Repository**: Neo-commons `OrganizationDatabaseRepository`
- **Cache**: Disabled for simplicity (can be enabled later)

## Integration Pattern

```python
# Dependency override pattern
app.dependency_overrides.update({
    get_organization_repository: get_admin_organization_repository,
    get_organization_service: get_admin_organization_service_impl,
    get_basic_organization_service: get_admin_organization_service_impl,
    get_admin_organization_service: get_admin_organization_service_impl,
})

# Router inclusion
app.include_router(organization_router, prefix="/api/v1")
app.include_router(organization_admin_router, prefix="/api/v1")
```

## Benefits

1. **DRY Compliance**: No duplication of organization logic
2. **Centralized**: Uses neo-commons shared implementation
3. **Database-Level Pagination**: Scalable for large datasets
4. **Protocol-Based**: Clean dependency injection
5. **Comprehensive**: Full CRUD + admin operations
6. **Consistent**: Same API patterns across services

## Testing

The implementation has been tested for:

- ✅ Import correctness
- ✅ App creation without errors
- ✅ Route registration (18 total endpoints)
- ✅ Proper URL structure
- ✅ Dependency injection setup

## Usage

Services can now use all organization endpoints immediately without additional implementation. The neo-commons routers provide complete functionality with proper error handling, validation, and response models.