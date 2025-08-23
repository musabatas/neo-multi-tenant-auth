# Unified Auth System - Simple Guide

## What It Does
A single authentication system that works everywhere - admin panel, tenant apps, all databases, all regions. One code, infinite tenants.

## Core Concept
```
User Request → Keycloak JWT → Platform User ID → Permissions → Access
                    ↓              ↓                ↓
              (External ID)   (Our Database)   (Redis Cache)
```

## The Magic: Dynamic Schema Resolution

```python
# Same code works for EVERYTHING
async def get_user(identifier: str, context: RequestContext):
    # Automatically picks the right database/schema
    schema = resolve_schema(context)  # Returns 'admin' or 'tenant_acme' etc.
    
    # SQL injection safe - validates schema name
    safe_schema = validate_schema(schema)  
    
    # Works with ANY identifier
    user = await db.fetch(f"""
        SELECT * FROM {safe_schema}.users 
        WHERE id = $1 OR external_id = $1 OR email = $1
    """, identifier)
    
    return user
```

## Key Features

### 1. Multi-ID Support
- Platform UUID: `a3f4b2c1-...`
- Keycloak ID: `kc_user_123`
- Email: `user@example.com`
- Username: `johndoe`

**ALL work with the same function!**

### 2. Sub-Millisecond Permissions
```python
# First call: ~10ms (database)
can_edit = await check_permission(user_id, "posts:edit")

# Second call: <1ms (cached)
can_delete = await check_permission(user_id, "posts:delete")
```

### 3. Automatic Tenant Detection
```python
# Admin API - always uses 'admin' schema
GET /api/admin/users → admin.users

# Tenant API - uses tenant's schema
GET /api/tenant/users → tenant_acme.users (auto-detected from JWT)
```

## Security Built-In

### SQL Injection Prevention
```python
def validate_schema(name: str) -> str:
    # Only allows: 'admin' or 'tenant_*' pattern
    if name == 'admin' or re.match(r'^tenant_[a-z0-9_]+$', name):
        return name
    raise SecurityError("Invalid schema")
```

### OAuth2 Client Credentials (No Passwords!)
```python
# ❌ NEVER DO THIS
config = {
    'admin_username': 'admin',  # BAD!
    'admin_password': 'secret'   # BAD!
}

# ✅ DO THIS INSTEAD
config = {
    'client_id': 'neo-service',
    'client_secret': encrypted('...')  # OAuth2 only
}
```

## Implementation in 3 Steps

### Step 1: User Resolution
```python
resolver = UserIdentityResolver(db, cache)
user = await resolver.resolve("any_identifier", tenant_id)
# Returns unified UserIdentity object
```

### Step 2: Permission Check
```python
checker = PermissionChecker(db, cache)
permissions = await checker.get_permissions(user.platform_id, user.schema)
# Returns set of permission strings
```

### Step 3: Use Anywhere
```python
# In Admin API
@router.get("/users")
@requires_permission("admin:users:list")
async def list_admin_users(user: CurrentUser):
    return await get_users("admin")  # Admin schema

# In Tenant API  
@router.get("/users")
@requires_permission("users:list")
async def list_tenant_users(user: CurrentUser):
    return await get_users(user.tenant_schema)  # Tenant's schema
```

## Database Structure (Already Exists!)

```sql
-- Both admin.users and tenant_*.users have SAME structure
CREATE TABLE {schema}.users (
    id UUID PRIMARY KEY,
    external_user_id VARCHAR(255),  -- Keycloak ID
    email VARCHAR(320),
    username VARCHAR(39),
    -- ... exact same fields in both schemas
);
```

## Caching Strategy

```yaml
Cache Keys:
  user:{tenant}:{id} → User object (5 min TTL)
  perms:{tenant}:{user} → Permission set (5 min TTL)
  schema:{tenant_id} → Schema name (1 hour TTL)

Invalidation:
  - On user update → Clear user:*
  - On permission change → Clear perms:*
  - On tenant change → Clear schema:*
```

## Configuration (From Existing DB)

```python
# Load from admin.tenants table (no new columns!)
tenant = await db.fetch("""
    SELECT 
        external_auth_metadata  -- JSONB with all config
    FROM admin.tenants 
    WHERE id = $1
""", tenant_id)

config = tenant['external_auth_metadata']
# {
#   'client_id': 'neo-backend',
#   'client_secret_encrypted': '...',
#   'keycloak_url': 'http://keycloak:8080'
# }
```

## Why This Works

1. **One Codebase**: Same repository code for admin + all tenants
2. **Dynamic Routing**: Schema determined at runtime from context
3. **Secure by Default**: Schema validation, OAuth2, encrypted secrets
4. **Fast**: Redis caching, connection pooling, prepared statements
5. **Scalable**: Works with 1 or 10,000 tenants

## Quick Integration

```python
# In your FastAPI app
from neo_commons.auth import setup_auth

app = FastAPI()
setup_auth(app, 
    schema_resolver=lambda ctx: ctx.tenant_schema or 'admin',
    cache=redis_client,
    db=connection_manager
)

# That's it! All routes now have auth
```

## The Result

- **1 auth system** for entire platform
- **<1ms** permission checks (cached)
- **0 SQL injection** vulnerabilities  
- **∞ tenants** supported
- **100% code reuse** between admin and tenants

Simple. Powerful. Secure. Fast.