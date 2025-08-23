# Unified Authentication System

## Executive Summary
A single, powerful authentication system that seamlessly works across admin schema and all dynamically-created tenant schemas (tenant_acme, tenant_bigcorp, etc.). Provides sub-millisecond permission checking, automatic Keycloak-to-platform user ID mapping, and intelligent caching.

## Core Architecture

```
+----------------------------------------------------------+
|                   External Layer (Keycloak)              |
|  - JWT Token Validation                                  |
|  - Realm-per-tenant isolation                           |
|  - OAuth2 Client Credentials                            |
+----------------------------------------------------------+
                           ↓
+----------------------------------------------------------+
|              User ID Resolution Layer                    |
|  - Keycloak ID → Platform ID mapping                    |
|  - Multi-identifier support (UUID/email/username)       |
|  - Automatic user synchronization                       |
+----------------------------------------------------------+
                           ↓
+----------------------------------------------------------+
|            Permission Resolution Layer                   |
|  - Role-based permissions                               |
|  - Direct user permissions                              |
|  - Team-based permissions                               |
|  - Scope-aware (global/team/tenant)                     |
+----------------------------------------------------------+
                           ↓
+----------------------------------------------------------+
|                 Caching Layer (Redis)                    |
|  - Sub-millisecond permission checks                    |
|  - Tenant-isolated caching                              |
|  - Event-driven invalidation                            |
+----------------------------------------------------------+
```

## Key Components

### 1. User Identity Resolution

```python
from dataclasses import dataclass
from typing import Optional, Set
import re

@dataclass
class UserIdentity:
    """Unified user identity across platform"""
    platform_id: str           # Internal platform UUID
    external_id: str           # Keycloak/external provider ID
    email: str                 
    username: Optional[str]    
    first_name: Optional[str]  
    last_name: Optional[str]   
    display_name: Optional[str]
    tenant_id: Optional[str]   # Current tenant context
    schema_name: str           # Resolved schema (admin or tenant_*)
    auth_provider: str         # keycloak, auth0, etc.
    permissions: Set[str]      # Cached permissions
    roles: Set[str]           # Cached roles
    metadata: dict            # Additional custom metadata

class UserIdentityResolver:
    """Resolves user identity from multiple sources"""
    
    def _validate_schema_name(self, schema_name: str) -> str:
        """Validate schema name to prevent SQL injection"""
        if schema_name == 'admin' or re.match(r'^tenant_[a-z0-9_]+$', schema_name):
            return schema_name
        raise ValueError(f"Invalid schema name: {schema_name}")
    
    async def resolve_user(self, identifier: str, tenant_id: Optional[str] = None):
        # Check cache first
        cache_key = f"user:{tenant_id or 'admin'}:{identifier}"
        cached = await self.cache.get(cache_key)
        if cached:
            return UserIdentity(**json.loads(cached))
        
        # Determine and validate schema
        schema_name = await self._resolve_schema(tenant_id)
        safe_schema = self._validate_schema_name(schema_name)
        
        # Multi-field lookup (safe after validation)
        query = f"""
        SELECT * FROM {safe_schema}.users
        WHERE (id::text = $1 OR external_user_id = $1 
               OR email = $1 OR username = $1)
        AND deleted_at IS NULL AND status = 'active'
        """
        
        user = await self.db.fetchrow(query, identifier)
        if user:
            identity = self._map_to_identity(user, tenant_id)
            await self.cache.set(cache_key, identity, ttl=300)
            return identity
        return None
```

### 2. Permission System

```python
class PermissionChecker:
    """High-performance permission checking with caching"""
    
    async def check_permission(self, 
                              user_id: str,
                              permission: str,
                              scope: Optional[dict] = None) -> bool:
        # Cache check
        cache_key = f"perms:{user_id}:{scope.get('tenant_id') if scope else 'admin'}"
        cached_perms = await self.cache.get(cache_key)
        
        if cached_perms:
            permissions = set(json.loads(cached_perms))
        else:
            permissions = await self._load_permissions(user_id, scope)
            await self.cache.set(cache_key, list(permissions), ttl=300)
        
        return permission in permissions
    
    async def _load_permissions(self, user_id: str, scope: dict) -> Set[str]:
        """Load permissions from multiple sources"""
        permissions = set()
        schema = self._validate_schema_name(scope.get('schema', 'admin'))
        
        # 1. Role-based permissions
        role_query = f"""
        SELECT p.code FROM {schema}.permissions p
        JOIN {schema}.role_permissions rp ON p.id = rp.permission_id
        JOIN {schema}.user_roles ur ON rp.role_id = ur.role_id
        WHERE ur.user_id = $1 AND ur.is_active = true
        """
        
        # 2. Direct user permissions
        direct_query = f"""
        SELECT p.code FROM {schema}.permissions p
        JOIN {schema}.user_permissions up ON p.id = up.permission_id
        WHERE up.user_id = $1 AND up.is_granted = true
        """
        
        # 3. Team-based permissions (if applicable)
        team_query = f"""
        SELECT p.code FROM {schema}.permissions p
        JOIN {schema}.role_permissions rp ON p.id = rp.permission_id
        JOIN {schema}.team_members tm ON rp.role_id = tm.role_id
        WHERE tm.user_id = $1 AND tm.is_active = true
        """
        
        # Execute queries in parallel
        results = await asyncio.gather(
            self.db.fetch(role_query, user_id),
            self.db.fetch(direct_query, user_id),
            self.db.fetch(team_query, user_id)
        )
        
        for result_set in results:
            permissions.update(row['code'] for row in result_set)
        
        return permissions
```

### 3. Keycloak Integration

```python
@dataclass
class KeycloakConfig:
    """Configuration for a Keycloak realm/tenant"""
    tenant_id: str
    realm_name: str           
    client_id: str           
    client_secret: Optional[str]  # OAuth2 client credentials only
    keycloak_url: str        
    issuer: str              
    audience: Optional[str] = None
    scope: str = "openid profile email"
    service_account_enabled: bool = False
    admin_api_roles: Optional[List[str]] = None

class KeycloakAdminClient:
    """Secure admin operations using OAuth2 client credentials"""
    
    async def get_admin_token(self) -> str:
        """Get admin access token using client credentials flow"""
        if self._access_token and self._token_expires_at > datetime.now(timezone.utc):
            return self._access_token
        
        # OAuth2 client credentials flow (NO username/password!)
        token_url = f"{self.config.keycloak_url}/realms/{self.config.realm_name}/protocol/openid-connect/token"
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.config.client_id,
            'client_secret': self.config.client_secret,
            'scope': 'openid'
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(token_url, data=data)
                response.raise_for_status()
                
                token_data = response.json()
                self._access_token = token_data['access_token']
                expires_in = token_data.get('expires_in', 300)
                self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 30)
                
                return self._access_token
        except httpx.HTTPError as e:
            logger.error(f"Failed to get Keycloak admin token: {e}")
            raise KeycloakConnectionError(f"Unable to authenticate with Keycloak: {e}")
```

### 4. Dynamic Schema Resolution

```python
class SchemaResolver:
    """Determines which database schema to use based on context"""
    
    async def resolve_schema(self, context: RequestContext) -> str:
        # Admin API always uses admin schema
        if context.is_admin_api:
            return 'admin'
        
        # Extract tenant from JWT or request
        tenant_id = context.tenant_id
        if not tenant_id:
            raise TenantNotFoundError("No tenant context available")
        
        # Lookup tenant schema (cached)
        cache_key = f"schema:{tenant_id}"
        cached_schema = await self.cache.get(cache_key)
        if cached_schema:
            return cached_schema
        
        # Query from database
        query = """
        SELECT schema_name FROM admin.tenants 
        WHERE id = $1 AND status = 'active'
        """
        result = await self.db.fetchval(query, tenant_id)
        if not result:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")
        
        await self.cache.set(cache_key, result, ttl=3600)
        return result
```

### 5. FastAPI Integration

```python
from fastapi import Depends, HTTPException
from typing import Optional

class CheckPermission:
    """FastAPI dependency for permission checking"""
    
    def __init__(self, permissions: List[str], require_all: bool = False):
        self.permissions = permissions
        self.require_all = require_all
    
    async def __call__(self, 
                      request: Request,
                      token: str = Depends(oauth2_scheme)) -> dict:
        # Validate JWT
        payload = await validate_jwt(token)
        
        # Resolve user
        resolver = UserIdentityResolver(db, cache)
        user = await resolver.resolve_user(
            payload['sub'],
            payload.get('tenant_id')
        )
        
        if not user:
            raise HTTPException(401, "User not found")
        
        # Check permissions
        checker = PermissionChecker(db, cache)
        has_perms = []
        
        for permission in self.permissions:
            has_perm = await checker.check_permission(
                user.platform_id,
                permission,
                {'tenant_id': user.tenant_id, 'schema': user.schema_name}
            )
            has_perms.append(has_perm)
        
        # Validate based on requirement
        if self.require_all and not all(has_perms):
            raise HTTPException(403, "Insufficient permissions")
        elif not self.require_all and not any(has_perms):
            raise HTTPException(403, "Insufficient permissions")
        
        return user

# Usage in routes
@router.get("/users")
async def list_users(current_user: dict = Depends(CheckPermission(["users:list"]))):
    # Automatically uses correct schema based on user context
    return await user_service.list_users(current_user.schema_name)
```

## Configuration Storage

```python
# Load from existing admin.tenants table (no new columns needed!)
async def get_keycloak_config(tenant_id: str) -> dict:
    query = """
    SELECT 
        external_auth_realm,
        external_auth_metadata  -- JSONB with all config
    FROM admin.tenants 
    WHERE id = $1
    """
    
    tenant = await db.fetchrow(query, tenant_id)
    
    # Config stored in existing JSONB column
    auth_metadata = tenant['external_auth_metadata'] or {}
    
    return {
        'realm': tenant['external_auth_realm'],
        'client_id': auth_metadata.get('client_id'),
        'client_secret': await decrypt(auth_metadata.get('client_secret_encrypted')),
        'keycloak_url': auth_metadata.get('keycloak_url')
    }
```

## Security Features

### Encryption Helper
```python
import base64
from cryptography.fernet import Fernet

class EncryptionHelper:
    def __init__(self, encryption_key: str):
        key = base64.urlsafe_b64encode(encryption_key.encode()[:32].ljust(32, b'\0'))
        self._cipher = Fernet(key)
    
    async def encrypt(self, plaintext: str) -> str:
        return self._cipher.encrypt(plaintext.encode()).decode()
    
    async def decrypt(self, ciphertext: str) -> str:
        return self._cipher.decrypt(ciphertext.encode()).decode()
```

### Custom Exceptions
```python
class AuthenticationError(Exception): pass
class KeycloakConnectionError(AuthenticationError): pass
class TenantNotFoundError(AuthenticationError): pass
class PermissionDeniedError(AuthenticationError): pass
class InvalidSchemaError(AuthenticationError): pass
```

## Caching Strategy

```yaml
Cache Design:
  Keys:
    user:{tenant}:{id}: User object (5 min TTL)
    perms:{tenant}:{user}: Permission set (5 min TTL)  
    schema:{tenant_id}: Schema name (1 hour TTL)
    jwt:{jti}: JWT validation (until exp)
    
  Invalidation:
    User Update: Clear user:* for that user
    Permission Change: Clear perms:* for affected users
    Tenant Update: Clear schema:* for that tenant
    Role Change: Clear perms:* for users with that role
    
  Performance:
    L1 Cache: In-memory LRU (process-local)
    L2 Cache: Redis (distributed)
    Hit Rate Target: >90%
    Response Time: <1ms cached, <10ms uncached
```

## Database Requirements

```sql
-- Both admin and tenant_* schemas have IDENTICAL structure
-- This enables single codebase to work with all schemas

-- Users table (same in admin.users and tenant_*.users)
CREATE TABLE {schema}.users (
    id UUID PRIMARY KEY,
    external_user_id VARCHAR(255),  -- Keycloak ID
    external_auth_provider VARCHAR(50),
    email VARCHAR(320),
    username VARCHAR(39),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    status VARCHAR(20),
    metadata JSONB,
    created_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);

-- Permissions, roles, user_roles, user_permissions tables
-- All follow same structure in both schemas
```

## Implementation Checklist

- [ ] User identity resolution with multi-ID support
- [ ] Permission checking with caching
- [ ] Keycloak integration with OAuth2 client credentials
- [ ] Dynamic schema resolution
- [ ] FastAPI dependency injection
- [ ] Redis caching layer
- [ ] SQL injection prevention
- [ ] Encryption for sensitive data
- [ ] Comprehensive error handling
- [ ] Audit logging
- [ ] Performance monitoring
- [ ] Migration from existing system

## Performance Targets

- Permission check: <1ms with cache, <10ms without
- User resolution: <5ms with cache, <20ms without  
- Token validation: <2ms
- Cache hit rate: >90%
- Concurrent requests: 10,000/sec per instance

## Summary

This unified authentication system provides enterprise-grade security with:
- **One codebase** for all tenants and admin
- **Sub-millisecond** permission checks via caching
- **Zero SQL injection** risk with validation
- **OAuth2 security** without storing passwords
- **Infinite scalability** with dynamic schemas
- **100% code reuse** between admin and tenants

Simple to integrate, powerful to use, secure by default.