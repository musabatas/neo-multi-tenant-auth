# Database Schema Analysis for Neo-Commons

## Executive Summary

After comprehensive analysis of the NeoMultiTenant database architecture, we've discovered that the `admin` schema and `tenant_template` schema (which serves as a blueprint for creating individual tenant schemas) have **IDENTICAL** table structures for all authentication and authorization tables. This perfect alignment enables neo-commons to implement a single, unified repository pattern with runtime schema switching across the admin schema and any number of dynamically-created tenant schemas (e.g., `tenant_acme`, `tenant_bigcorp`, etc.).

## Key Discoveries

### 1. Template-Based Multi-Tenant Architecture
The investigation revealed that:
- `admin` schema contains platform-wide management tables
- `tenant_template` schema serves as a blueprint for creating individual tenant schemas
- Each tenant gets their own schema (e.g., `tenant_acme`, `tenant_bigcorp`) created from the template
- All tenant schemas will have identical table structures for:
  - `users` - User identity and profile management
  - `permissions` - Permission definitions
  - `roles` - Role definitions with permission mappings
  - `role_permissions` - Many-to-many role-permission relationships
  - `user_roles` - User role assignments with flexible scoping
  - `user_permissions` - Direct permission grants to users
  - `teams` - Team/group organization
  - `team_members` - Team membership tracking

### 2. Built-in External Authentication Support
Both schemas include native support for external authentication providers:
```sql
-- From both admin.users and tenant_template.users
external_user_id VARCHAR(255) NOT NULL,
external_auth_provider platform_common.auth_provider NOT NULL DEFAULT 'keycloak',
external_auth_metadata JSONB DEFAULT '{}'
```

### 3. Flexible Permission Scoping
Both schemas implement the same flexible scoping system:
```sql
-- From user_roles and user_permissions in both schemas
scope_type VARCHAR(20) DEFAULT 'global',  -- or 'tenant' in tenant_template
scope_id UUID,  -- nullable for global scope
```

## Database Structure Analysis

### Common Platform Types (platform_common schema)

```sql
-- Shared enums used across all schemas
auth_provider: 'keycloak', 'auth0', 'cognito', 'okta', 'custom'
role_level: 'owner', 'admin', 'manager', 'member', 'viewer', 'guest', 'platform'
user_status: 'active', 'inactive', 'suspended', 'pending', 'deleted'
permission_scope: 'global', 'tenant', 'team', 'resource', 'platform'
team_types: 'working_group', 'project_team', 'department', 'committee', 'community'
```

### Users Table (Identical Structure)

| Field | Type | Description | Present In |
|-------|------|-------------|------------|
| id | UUID | Primary key (uuid_generate_v7) | Both |
| email | VARCHAR(320) | Unique email with validation | Both |
| username | VARCHAR(39) | Optional unique username | Both |
| external_user_id | VARCHAR(255) | Keycloak/external ID | Both |
| external_auth_provider | auth_provider | Provider type | Both |
| external_auth_metadata | JSONB | Provider-specific data | Both |
| status | user_status | User status enum | Both |
| is_system_user | BOOLEAN | System/service account flag | Both |
| manager_id | UUID | Self-reference for hierarchy | Both |
| metadata | JSONB | Extensible user metadata | Both |

### Permissions Table (Identical Structure)

| Field | Type | Description | Present In |
|-------|------|-------------|------------|
| id | INTEGER | Identity primary key | Both |
| code | VARCHAR(100) | Unique permission code | Both |
| resource | VARCHAR(50) | Resource being protected | Both |
| action | VARCHAR(50) | Action being permitted | Both |
| scope_level | permission_scope | Permission scope enum | Both |
| is_dangerous | BOOLEAN | High-risk operation flag | Both |
| requires_mfa | BOOLEAN | MFA requirement flag | Both |
| permission_config | JSONB | Additional configuration | Both |

### Dynamic Database Connections (admin schema only)

```sql
-- admin.database_connections table structure
CREATE TABLE admin.database_connections (
    id UUID PRIMARY KEY,
    region_id UUID REFERENCES admin.regions,
    connection_name VARCHAR(100) UNIQUE,
    connection_type admin.connection_type,  -- 'admin', 'shared', 'analytics', 'tenant'
    host VARCHAR(255),
    port INTEGER DEFAULT 5432,
    database_name VARCHAR(63),
    username VARCHAR(255),
    encrypted_password VARCHAR(256),
    -- Pool configuration
    pool_min_size INTEGER DEFAULT 5,
    pool_max_size INTEGER DEFAULT 20,
    pool_timeout_seconds INTEGER DEFAULT 30,
    -- Health monitoring
    is_active BOOLEAN DEFAULT true,
    is_healthy BOOLEAN DEFAULT true,
    last_health_check TIMESTAMPTZ,
    consecutive_failures INTEGER DEFAULT 0
);
```

## Unified Query Patterns

### 1. User Identity Resolution Pattern
```sql
-- Works in admin schema and ALL tenant schemas (tenant_acme, tenant_bigcorp, etc.)
SELECT 
    id, email, username, external_user_id, external_auth_provider,
    first_name, last_name, display_name, status, is_system_user
FROM {schema_name}.users 
WHERE (
    id = $1 
    OR external_user_id = $1 
    OR email = $1 
    OR username = $1
) AND deleted_at IS NULL;

-- Examples:
-- Admin context: FROM admin.users
-- Tenant context: FROM tenant_acme.users, FROM tenant_bigcorp.users, etc.
```

### 2. Permission Resolution Pattern
```sql
-- Unified permission check across both schemas
WITH user_permissions AS (
    -- Direct permissions
    SELECT p.code, up.scope_type, up.scope_id
    FROM {schema_name}.user_permissions up
    JOIN {schema_name}.permissions p ON up.permission_id = p.id
    WHERE up.user_id = $1 
      AND up.is_active = true 
      AND up.is_granted = true
      AND (up.expires_at IS NULL OR up.expires_at > NOW())
    
    UNION ALL
    
    -- Role-based permissions
    SELECT p.code, ur.scope_type, ur.scope_id
    FROM {schema_name}.user_roles ur
    JOIN {schema_name}.role_permissions rp ON ur.role_id = rp.role_id
    JOIN {schema_name}.permissions p ON rp.permission_id = p.id
    WHERE ur.user_id = $1 
      AND ur.is_active = true
      AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
    
    UNION ALL
    
    -- Team-based permissions (if scope_type = 'team')
    SELECT p.code, 'team' as scope_type, tm.team_id as scope_id
    FROM {schema_name}.team_members tm
    JOIN {schema_name}.teams t ON tm.team_id = t.id
    JOIN {schema_name}.user_roles ur ON ur.scope_id = t.id
    JOIN {schema_name}.role_permissions rp ON ur.role_id = rp.role_id
    JOIN {schema_name}.permissions p ON rp.permission_id = p.id
    WHERE tm.user_id = $1 
      AND tm.status = 'active'
      AND t.is_active = true
      AND ur.scope_type = 'team'
)
SELECT DISTINCT code, scope_type, scope_id 
FROM user_permissions
WHERE code = $2 
  AND (
    scope_type = 'global' 
    OR (scope_type = $3 AND scope_id = $4)
  );
```

### 3. User Role Assignment Pattern
```sql
-- Get all roles for a user with scoping
SELECT 
    r.code, r.name, r.role_level,
    ur.scope_type, ur.scope_id,
    ur.expires_at, ur.is_active
FROM {schema_name}.user_roles ur
JOIN {schema_name}.roles r ON ur.role_id = r.id
WHERE ur.user_id = $1
  AND ur.is_active = true
  AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
ORDER BY r.priority DESC;
```

## Schema Detection Strategy

### Runtime Schema Resolution
```python
class SchemaResolver:
    """Resolves the correct schema based on tenant context"""
    
    @staticmethod
    async def get_tenant_schema(tenant_id: str) -> str:
        """Get the actual tenant schema name from tenant configuration"""
        # Query admin.tenants table to get the schema name
        query = """
        SELECT schema_name 
        FROM admin.tenants 
        WHERE id = $1 AND status = 'active'
        """
        result = await conn.fetchrow(query, tenant_id)
        
        if not result:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found or inactive")
        
        # Returns actual schema like 'tenant_acme', 'tenant_bigcorp', etc.
        return result['schema_name']
    
    @staticmethod
    async def resolve_schema_from_context(context: RequestContext) -> str:
        """Resolve schema based on request context"""
        if context.is_admin_request:
            return "admin"
        elif context.tenant_id:
            # Get actual tenant schema (e.g., 'tenant_acme')
            return await SchemaResolver.get_tenant_schema(context.tenant_id)
        else:
            raise SchemaResolutionError("Cannot determine schema from context")
```

### Service-Level Configuration
```python
# NeoAdminApi default configuration
class AdminApiConfig:
    DEFAULT_SCHEMA = "admin"
    DEFAULT_CONNECTION = "admin-primary"
    
# NeoTenantApi configuration  
class TenantApiConfig:
    # Schema is dynamically resolved based on tenant_id in request
    # Examples: tenant_acme, tenant_bigcorp, tenant_startup
    DEFAULT_CONNECTION = "shared-{region}"
    
    async def get_schema_for_request(self, tenant_id: str) -> str:
        """Dynamically resolve schema for tenant request"""
        return await SchemaResolver.get_tenant_schema(tenant_id)
```

## Repository Implementation Pattern

### Unified Base Repository
```python
class UnifiedAuthRepository:
    """Single repository working across admin and all tenant schemas"""
    
    def __init__(self, connection_manager: ConnectionManager, schema_resolver: SchemaResolver):
        self._connection_manager = connection_manager
        self._schema_resolver = schema_resolver
        # Pattern allows admin and any tenant schema (tenant_*)
        self._schema_whitelist = {'admin', 'tenant_*'}
    
    def _validate_schema(self, schema_name: str) -> None:
        """Validate schema name against whitelist to prevent SQL injection"""
        # Check if schema matches allowed patterns
        if not (schema_name == 'admin' or schema_name.startswith('tenant_')):
            raise SecurityError(f"Invalid schema name: {schema_name}")
        
        # Additional validation: schema name should only contain alphanumeric and underscore
        if not re.match(r'^[a-z][a-z0-9_]*$', schema_name):
            raise SecurityError(f"Schema name contains invalid characters: {schema_name}")
    
    async def get_user(self, user_id: str, tenant_id: Optional[str] = None) -> Optional[User]:
        """Get user from admin or tenant schema based on context"""
        # Resolve schema dynamically
        if tenant_id:
            schema_name = await self._schema_resolver.get_tenant_schema(tenant_id)
        else:
            schema_name = "admin"
        
        self._validate_schema(schema_name)
        
        query = f"""
        SELECT * FROM {schema_name}.users 
        WHERE id = $1 AND deleted_at IS NULL
        """
        
        async with self._connection_manager.get_connection() as conn:
            row = await conn.fetchrow(query, user_id)
            return User.from_row(row) if row else None
    
    async def check_permission(self, 
                              user_id: str, 
                              permission_code: str,
                              schema_name: str,
                              scope_type: str = None,
                              scope_id: str = None) -> bool:
        """Check permission in specified schema"""
        self._validate_schema(schema_name)
        
        # Use unified permission resolution query
        query = self._build_permission_query(schema_name)
        
        async with self._connection_manager.get_connection() as conn:
            result = await conn.fetchrow(
                query, 
                user_id, 
                permission_code, 
                scope_type or 'global',
                scope_id
            )
            return result['has_permission'] if result else False
```

## Key Implementation Requirements

### 1. Security Considerations
- **Schema Name Validation**: MUST validate schema names against whitelist
- **Prepared Statements**: Use parameterized queries for all user input
- **Connection Security**: Encrypt passwords in database_connections table
- **Audit Logging**: Log all cross-schema operations

### 2. Performance Optimizations
- **Connection Pooling**: Maintain pools per database/schema combination
- **Query Caching**: Cache permission checks in Redis with tenant:user:permission keys
- **Prepared Statements**: Prepare frequently used queries
- **Index Utilization**: Ensure all lookup fields are properly indexed

### 3. Migration Path
- **Phase 1**: Create unified repository interfaces
- **Phase 2**: Implement schema detection and routing
- **Phase 3**: Add caching layer for performance
- **Phase 4**: Migrate existing repositories to unified pattern

## Schema Differences to Handle

### Admin-Only Tables
- `organizations` - Company/entity management
- `regions` - Geographic deployment regions  
- `database_connections` - Dynamic database configuration
- `tenants` - Tenant instance configuration
- `tenant_contacts` - Tenant contact management

### Tenant-Only Tables (in each tenant schema: tenant_acme, tenant_bigcorp, etc.)
- `invitations` - User invitation management
- `settings` - Tenant-specific configuration (if exists)
- All other tenant-specific business tables

### Default Value Differences
| Table | Field | Admin Default | Tenant Default |
|-------|-------|---------------|----------------|
| permissions | scope_level | 'platform' | 'tenant' |
| roles | scope_type | 'global' | 'tenant' |
| user_roles | scope_type | 'global' | 'tenant' |
| user_permissions | scope_type | 'global' | 'tenant' |

## Implementation Recommendations

### High Priority
1. **Unified Repository Base Class**: Implement single repository with dynamic schema support
2. **Schema Detection Strategy**: Auto-detect based on API context and connection type
3. **User ID Mapping Layer**: Support both platform and external IDs seamlessly

### Medium Priority
4. **Connection Pool Manager**: Dynamic pool creation for multi-region support
5. **Permission Caching**: Redis-based caching with sub-millisecond targets

### Low Priority
6. **Schema Migration Verification**: Automated testing to ensure schema synchronization

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Schema Drift | High | Automated tests comparing structures |
| SQL Injection | Critical | Schema name whitelist validation |
| Connection Exhaustion | Medium | Pool sizing and monitoring |
| Cache Coherency | Medium | TTL-based expiration and event-driven invalidation |
| Performance Degradation | High | Query optimization and proper indexing |

## Tenant Schema Creation Process

### Schema Creation from Template
```sql
-- When a new tenant is onboarded, create their schema from the template
CREATE SCHEMA tenant_acme;

-- Copy all table structures from tenant_template
-- This ensures all tenant schemas have identical structure
SELECT clone_schema('tenant_template', 'tenant_acme');

-- The admin.tenants table tracks the mapping
INSERT INTO admin.tenants (
    id, organization_id, slug, name, schema_name, 
    database_connection_id, status
) VALUES (
    uuid_generate_v7(), 
    $organization_id,
    'acme',
    'Acme Corporation', 
    'tenant_acme',  -- Actual schema name
    $connection_id,
    'active'
);
```

### Schema Name Resolution Flow
```
1. Request arrives with tenant_id (from JWT token or URL)
2. Query admin.tenants to get schema_name
3. Validate schema_name against security patterns
4. Use schema_name in all queries for that request
5. Cache tenant_id → schema_name mapping in Redis
```

## Conclusion

The template-based architecture where `tenant_template` serves as a blueprint for creating individual tenant schemas (like `tenant_acme`, `tenant_bigcorp`) provides an ideal foundation for neo-commons. By implementing a unified repository pattern with runtime schema resolution, we can achieve:

- **Single codebase** serving both admin and tenant contexts
- **Dynamic database connections** without code changes
- **Sub-millisecond performance** through intelligent caching
- **Seamless Keycloak integration** with automatic user ID mapping
- **Enterprise-grade security** with proper validation and isolation

This architecture dramatically simplifies our development effort while maintaining the flexibility required for true multi-tenant operations.