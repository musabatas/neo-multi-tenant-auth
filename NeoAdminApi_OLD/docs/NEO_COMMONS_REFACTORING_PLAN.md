# Neo-Commons Integration Refactoring Plan

## Current Architecture Problems

### 1. User ID Resolution Issues
**Problem**: User ID resolution (Keycloak → Platform) is scattered across multiple components
- `NeoAdminPermissionChecker._resolve_user_id()` 
- `PermissionService._resolve_user_id()`
- Similar logic in auth service

**Impact**: 
- Violates DRY principle
- Inconsistent resolution strategies
- Performance overhead from repeated database lookups

### 2. Database Query Issues
**Problem**: Permission queries have incorrect assumptions
- Trying to use `priority` column that doesn't exist in user permission tables
- Complex UNION queries that could be simplified
- Missing proper indexes usage

**Impact**:
- Runtime SQL errors
- Poor query performance
- Maintenance complexity

### 3. Incorrect Separation of Concerns
**Problem**: Business logic mixed between neo-commons and NeoAdminApi
- Permission checking logic split across libraries
- Cache management duplicated
- Authentication flow fragmented

**Impact**:
- Unclear responsibility boundaries
- Difficult to test
- Hard to maintain consistency

### 4. Cache Management Chaos
**Problem**: Multiple cache managers and inconsistent key patterns
- CacheManager created multiple times
- No centralized cache key management
- No proper invalidation strategy

**Impact**:
- Memory overhead
- Cache inconsistency risks
- Performance degradation

## Proposed Architecture

### Layer 1: Neo-Commons (Pure Library)
**Responsibilities**:
- JWT validation (Keycloak integration)
- Token introspection
- Basic auth protocols
- Cache abstractions
- Base repository patterns

**What it should NOT do**:
- Database queries (leave to implementations)
- User ID resolution (application concern)
- Business-specific permission logic

### Layer 2: NeoAdminApi Auth Module
**Responsibilities**:
- User ID resolution (single source of truth)
- Database queries for permissions
- Platform-specific business logic
- Cache key management
- FastAPI dependency integration

### Layer 3: Service Layer
**Responsibilities**:
- Business operations
- Transaction management
- Cross-feature coordination

## Refactoring Steps

### Phase 1: Centralize User ID Resolution

#### Step 1.1: Create UserIdentityResolver
```python
# src/features/auth/services/user_identity_resolver.py
class UserIdentityResolver:
    """Single source of truth for user identity resolution."""
    
    def __init__(self, auth_repo: AuthRepository):
        self.auth_repo = auth_repo
        self._cache = {}  # Simple in-memory cache
    
    async def resolve_to_platform_id(self, user_id: str) -> str:
        """Resolve any user ID to platform user ID."""
        # Check cache first
        if user_id in self._cache:
            return self._cache[user_id]
        
        # Try as platform ID
        try:
            user = await self.auth_repo.get_user_by_id(user_id)
            self._cache[user_id] = user['id']
            return user['id']
        except:
            pass
        
        # Try as Keycloak ID
        try:
            user = await self.auth_repo.get_user_by_external_id(
                provider="keycloak",
                external_id=user_id
            )
            platform_id = user['id']
            self._cache[user_id] = platform_id
            self._cache[platform_id] = platform_id
            return platform_id
        except:
            raise NotFoundError(f"User {user_id} not found")
```

#### Step 1.2: Update All Services to Use Resolver
- Inject UserIdentityResolver into services
- Remove all `_resolve_user_id()` methods
- Use centralized resolver

### Phase 2: Fix Permission Repository

#### Step 2.1: Correct SQL Queries
```python
# Fix platform direct permissions query
SELECT 
    p.id,
    p.code as name,
    p.resource,
    p.action,
    p.scope_level,
    p.description,
    p.is_dangerous,
    p.requires_mfa,
    p.requires_approval,
    p.permissions_config,
    (p.deleted_at IS NULL) as is_active,
    'platform_direct' as source_type,
    'Direct Assignment' as source_name,
    100 as priority  -- Fixed: constant value instead of up.priority
FROM admin.platform_user_permissions up
JOIN admin.platform_permissions p ON p.id = up.permission_id
WHERE up.user_id = $1
    AND up.is_active = true
    AND up.is_granted = true  -- Added: check is_granted
    AND p.deleted_at IS NULL
    AND (up.expires_at IS NULL OR up.expires_at > CURRENT_TIMESTAMP)
```

#### Step 2.2: Optimize Query Performance
- Use CTEs more efficiently
- Add proper index hints
- Consider materialized views for complex permission aggregations

### Phase 3: Simplify Neo-Commons

#### Step 3.1: Remove Business Logic
- Move permission checking to NeoAdminApi
- Keep only protocol definitions in neo-commons
- Remove database-specific code

#### Step 3.2: Clean Protocol Definitions
```python
# neo_commons/auth/core/protocols.py
@runtime_checkable
class TokenValidatorProtocol(Protocol):
    """Pure token validation protocol."""
    async def validate_token(self, token: str, realm: str) -> Dict[str, Any]:
        """Validate JWT and return claims."""
        ...

@runtime_checkable  
class PermissionCheckerProtocol(Protocol):
    """Permission checking protocol."""
    async def check_permission(
        self, 
        user_id: str, 
        permissions: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if user has required permissions."""
        ...
```

### Phase 4: Centralize Cache Management

#### Step 4.1: Create CacheKeyManager
```python
# src/common/cache/keys.py
class CacheKeyManager:
    """Centralized cache key management."""
    
    PLATFORM_USER = "platform:user:{user_id}"
    PLATFORM_PERMISSIONS = "platform:perms:{user_id}"
    TENANT_PERMISSIONS = "tenant:{tenant_id}:perms:{user_id}"
    SESSION = "session:{session_id}"
    USER_IDENTITY = "identity:{any_id}"
    
    @staticmethod
    def get_platform_user_key(user_id: str) -> str:
        return CacheKeyManager.PLATFORM_USER.format(user_id=user_id)
    
    @staticmethod
    def get_permission_key(user_id: str, tenant_id: Optional[str] = None) -> str:
        if tenant_id:
            return CacheKeyManager.TENANT_PERMISSIONS.format(
                tenant_id=tenant_id,
                user_id=user_id
            )
        return CacheKeyManager.PLATFORM_PERMISSIONS.format(user_id=user_id)
```

#### Step 4.2: Single Cache Manager Instance
```python
# src/common/cache/__init__.py
_cache_manager = None

def get_cache_manager():
    """Get singleton cache manager."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
```

### Phase 5: Clean Dependency Injection

#### Step 5.1: Simplify CheckPermission
```python
# src/features/auth/dependencies.py
class CheckPermission:
    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions
        self.identity_resolver = None  # Lazy init
        self.permission_service = None  # Lazy init
    
    async def __call__(self, request: Request, token: str = Depends(oauth2_scheme)):
        # Initialize services if needed
        if not self.identity_resolver:
            self.identity_resolver = UserIdentityResolver(AuthRepository())
        if not self.permission_service:
            self.permission_service = PermissionService()
        
        # Validate token
        token_data = await validate_token(token)
        
        # Resolve to platform ID once
        platform_user_id = await self.identity_resolver.resolve_to_platform_id(
            token_data.get("sub")
        )
        
        # Check permissions
        has_permission = await self.permission_service.check_permissions(
            platform_user_id,
            self.required_permissions
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Return user data with platform ID
        return {
            **token_data,
            "id": platform_user_id,  # Always platform ID
            "keycloak_id": token_data.get("sub")  # Original Keycloak ID
        }
```

## Implementation Priority

### Week 1: Foundation
1. ✅ Implement UserIdentityResolver
2. ✅ Fix permission repository queries
3. ✅ Create CacheKeyManager

### Week 2: Integration
4. ⏳ Update all services to use resolver
5. ⏳ Implement singleton cache manager
6. ⏳ Update CheckPermission dependency

### Week 3: Cleanup
7. ⏳ Remove duplicate code
8. ⏳ Simplify neo-commons
9. ⏳ Update tests

### Week 4: Optimization
10. ⏳ Add caching strategies
11. ⏳ Performance testing
12. ⏳ Documentation

## Benefits of Refactoring

### 1. **Clear Separation of Concerns**
- Neo-commons: Pure library functions
- NeoAdminApi: Business logic
- Services: Operations

### 2. **DRY Principle Adherence**
- Single user ID resolution point
- Centralized cache management
- Reusable permission checking

### 3. **Performance Improvements**
- Reduced database queries
- Efficient caching
- Optimized SQL queries

### 4. **Maintainability**
- Clear responsibility boundaries
- Easier testing
- Consistent patterns

### 5. **Scalability**
- Ready for multi-region
- Tenant isolation
- Cache efficiency

## Testing Strategy

### Unit Tests
- UserIdentityResolver with mocked repository
- CacheKeyManager key generation
- Permission service with mocked data

### Integration Tests
- Full auth flow with real database
- Cache invalidation scenarios
- Permission checking edge cases

### Performance Tests
- User ID resolution caching
- Permission query optimization
- Cache hit rates

## Migration Path

### Step 1: Add New Components (Non-Breaking)
- Add UserIdentityResolver alongside existing code
- Add CacheKeyManager without removing old keys
- Keep existing functionality working

### Step 2: Gradual Migration
- Update one service at a time
- Run both old and new code
- Monitor for issues

### Step 3: Cleanup
- Remove old code
- Update documentation
- Final testing

## Success Metrics

1. **Code Quality**
   - 0 duplicated user ID resolution logic
   - Single cache manager instance
   - Clear separation between libraries

2. **Performance**
   - <1ms user ID resolution (cached)
   - <5ms permission checking (cached)
   - >90% cache hit rate

3. **Maintainability**
   - 50% reduction in auth-related code
   - Clear documentation
   - Comprehensive test coverage

## Risk Mitigation

### Risk 1: Breaking Existing Functionality
**Mitigation**: Gradual migration with feature flags

### Risk 2: Performance Regression
**Mitigation**: Benchmark before and after each change

### Risk 3: Cache Inconsistency
**Mitigation**: Clear invalidation strategy and monitoring

## Conclusion

This refactoring will transform the current fragmented authentication system into a clean, maintainable, and performant architecture that properly separates concerns between neo-commons and NeoAdminApi while adhering to DRY principles and the actual database structure.