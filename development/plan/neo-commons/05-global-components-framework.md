# Global Components Framework

## Executive Summary

The Global Components Framework provides a comprehensive suite of ready-to-use, configurable, and overrideable components that can be shared across all NeoMultiTenant services. This framework ensures consistency, reduces code duplication, and accelerates development while maintaining flexibility for service-specific customization.

## Core Design Principles

### 1. **Zero Configuration, Full Customization**
- Components work out-of-the-box with sensible defaults
- Every aspect can be overridden for specific needs
- Configuration cascades: Global � Service � Request level

### 2. **Protocol-Based Extensibility**
- All components defined as protocols (interfaces)
- Multiple implementations available
- Easy to swap or extend implementations

### 3. **Performance First**
- Async-first design throughout
- Built-in caching where appropriate
- Lazy loading and initialization

### 4. **Type Safety**
- Full type hints and runtime validation
- Pydantic models for all configurations
- Protocol definitions for contracts

## Component Categories

```
neo-commons/
    components/
    |-- config/              # Configuration management
    |-- middleware/          # FastAPI middleware stack
    |-- dependencies/        # Dependency injection
    |-- models/             # Shared data models
    |-- repositories/       # Data access patterns
    |-- services/           # Business logic components
    |-- utils/              # Utility functions
    |-- validators/         # Input validation
    |-- serializers/        # Data serialization
    |-- exceptions/         # Exception handling
```

## 1. Configuration Management

### Base Configuration System

```python
from pydantic import BaseSettings, Field
from typing import Optional, Dict, Any
from functools import lru_cache

class GlobalConfig(BaseSettings):
    """Global configuration with environment variable support"""
    
    # Application
    app_name: str = Field("neo-commons", env="APP_NAME")
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    
    # Database
    admin_database_url: str = Field(..., env="ADMIN_DATABASE_URL")
    db_pool_min: int = Field(5, env="DB_POOL_MIN")
    db_pool_max: int = Field(20, env="DB_POOL_MAX")
    
    # Redis
    redis_url: str = Field("redis://localhost:6379", env="REDIS_URL")
    redis_password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    
    # Keycloak
    keycloak_url: str = Field("http://localhost:8080", env="KEYCLOAK_URL")
    keycloak_realm: str = Field("master", env="KEYCLOAK_REALM")
    
    # Security
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    encryption_key: str = Field(..., env="ENCRYPTION_KEY")
    
    # Performance
    cache_ttl: int = Field(300, env="CACHE_TTL")
    request_timeout: int = Field(30, env="REQUEST_TIMEOUT")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

class ServiceConfig(GlobalConfig):
    """Service-specific configuration that extends global"""
    
    service_name: str
    service_version: str = "1.0.0"
    service_port: int = 8000
    
    # Service-specific overrides
    custom_settings: Dict[str, Any] = {}
    
    def merge_with_global(self, global_config: GlobalConfig):
        """Merge service config with global config"""
        for field_name, field_value in global_config.__dict__.items():
            if not hasattr(self, field_name) or getattr(self, field_name) is None:
                setattr(self, field_name, field_value)
        return self

@lru_cache()
def get_config() -> GlobalConfig:
    """Get cached configuration instance"""
    return GlobalConfig()

# Usage in services
class NeoAdminApiConfig(ServiceConfig):
    service_name: str = "NeoAdminApi"
    service_port: int = 8001
    default_schema: str = "admin"
    
class NeoTenantApiConfig(ServiceConfig):
    service_name: str = "NeoTenantApi"
    service_port: int = 8002
    default_schema: str = None  # Resolved per request
```

### Dynamic Configuration Provider

```python
from typing import Protocol, Any
import json

class ConfigProvider(Protocol):
    """Protocol for configuration providers"""
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        ...
    
    async def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        ...
    
    async def refresh(self) -> None:
        """Refresh configuration from source"""
        ...

class DatabaseConfigProvider:
    """Load configuration from database"""
    
    def __init__(self, connection_manager):
        self._conn_manager = connection_manager
        self._cache = {}
        self._last_refresh = None
    
    async def get(self, key: str, default: Any = None) -> Any:
        if key not in self._cache:
            await self.refresh()
        return self._cache.get(key, default)
    
    async def refresh(self):
        query = """
        SELECT key, value, value_type 
        FROM admin.configurations 
        WHERE is_active = true
        """
        pool = await self._conn_manager.get_connection("admin-primary")
        async with pool.acquire() as conn:
            rows = await conn.fetch(query)
            for row in rows:
                self._cache[row['key']] = self._deserialize(
                    row['value'], 
                    row['value_type']
                )
    
    def _deserialize(self, value: str, value_type: str) -> Any:
        if value_type == 'json':
            return json.loads(value)
        elif value_type == 'int':
            return int(value)
        elif value_type == 'bool':
            return value.lower() in ('true', '1', 'yes')
        return value

class FeatureFlagProvider:
    """Feature flag management"""
    
    async def is_enabled(self, flag: str, context: dict = None) -> bool:
        """Check if feature flag is enabled"""
        # Check global flags
        global_flag = await self._check_global_flag(flag)
        if global_flag is not None:
            return global_flag
        
        # Check tenant-specific flags
        if context and context.get('tenant_id'):
            tenant_flag = await self._check_tenant_flag(flag, context['tenant_id'])
            if tenant_flag is not None:
                return tenant_flag
        
        # Check user-specific flags
        if context and context.get('user_id'):
            user_flag = await self._check_user_flag(flag, context['user_id'])
            if user_flag is not None:
                return user_flag
        
        return False  # Default to disabled
```

## 2. Middleware Stack

### Base Middleware System

```python
from fastapi import FastAPI, Request, Response
from typing import Callable, List, Optional
import time
import uuid

class BaseMiddleware:
    """Base class for all middleware"""
    
    def __init__(self, app: FastAPI):
        self.app = app
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        # Pre-processing
        request = await self.process_request(request)
        
        # Call next middleware or route
        response = await call_next(request)
        
        # Post-processing
        response = await self.process_response(request, response)
        
        return response
    
    async def process_request(self, request: Request) -> Request:
        """Override for request processing"""
        return request
    
    async def process_response(self, request: Request, response: Response) -> Response:
        """Override for response processing"""
        return response

class RequestIdMiddleware(BaseMiddleware):
    """Add unique request ID to all requests"""
    
    async def process_request(self, request: Request) -> Request:
        request.state.request_id = str(uuid.uuid4())
        return request
    
    async def process_response(self, request: Request, response: Response) -> Response:
        response.headers["X-Request-ID"] = request.state.request_id
        return response

class TimingMiddleware(BaseMiddleware):
    """Track request timing"""
    
    async def process_request(self, request: Request) -> Request:
        request.state.start_time = time.time()
        return request
    
    async def process_response(self, request: Request, response: Response) -> Response:
        duration = time.time() - request.state.start_time
        response.headers["X-Response-Time"] = f"{duration:.3f}"
        return response

class TenantContextMiddleware(BaseMiddleware):
    """Extract and validate tenant context"""
    
    async def process_request(self, request: Request) -> Request:
        # Extract from header
        tenant_id = request.headers.get("X-Tenant-ID")
        
        # Or extract from JWT
        if not tenant_id and hasattr(request.state, "user"):
            tenant_id = request.state.user.get("tenant_id")
        
        # Or extract from subdomain
        if not tenant_id:
            host = request.headers.get("host", "")
            if ".neo-platform.com" in host:
                tenant_slug = host.split(".")[0]
                tenant_id = await self._resolve_tenant_id(tenant_slug)
        
        request.state.tenant_id = tenant_id
        return request
    
    async def _resolve_tenant_id(self, slug: str) -> Optional[str]:
        # Resolve tenant ID from slug
        cache_key = f"tenant:slug:{slug}"
        cached = await redis.get(cache_key)
        if cached:
            return cached
        
        query = "SELECT id FROM admin.tenants WHERE slug = $1 AND status = 'active'"
        result = await db.fetchval(query, slug)
        if result:
            await redis.set(cache_key, result, ttl=3600)
        return result

class RateLimitMiddleware(BaseMiddleware):
    """Rate limiting per tenant/user"""
    
    def __init__(self, app: FastAPI, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
    
    async def process_request(self, request: Request) -> Request:
        # Get identifier (tenant or user)
        identifier = request.state.tenant_id or request.state.get("user_id", "anonymous")
        
        # Check rate limit
        key = f"rate_limit:{identifier}:{int(time.time() / 60)}"
        count = await redis.incr(key)
        
        if count == 1:
            await redis.expire(key, 60)
        
        if count > self.requests_per_minute:
            raise HTTPException(429, "Rate limit exceeded")
        
        return request

def register_middleware(app: FastAPI, config: ServiceConfig):
    """Register middleware stack with configuration"""
    
    # Order matters! First registered = outermost
    middleware_stack = [
        RequestIdMiddleware,
        TimingMiddleware,
        TenantContextMiddleware,
    ]
    
    # Add rate limiting in production
    if config.environment == "production":
        middleware_stack.append(RateLimitMiddleware)
    
    for middleware_class in middleware_stack:
        app.add_middleware(middleware_class)
    
    return app
```

## 3. Dependency Injection System

### Core Dependencies

```python
from fastapi import Depends, Header, HTTPException
from typing import Optional, Protocol

class DatabaseDependency:
    """Provides database connection based on context"""
    
    def __init__(self, connection_manager):
        self._manager = connection_manager
    
    async def __call__(self, 
                       request: Request,
                       x_tenant_id: Optional[str] = Header(None)) -> Pool:
        # Determine connection based on context
        if x_tenant_id:
            return await self._manager.get_connection_for_tenant(x_tenant_id)
        elif request.url.path.startswith("/admin"):
            return await self._manager.get_connection("admin-primary")
        else:
            raise HTTPException(400, "Unable to determine database context")

class CacheDependency:
    """Provides cache connection with tenant isolation"""
    
    def __init__(self, redis_client):
        self._redis = redis_client
    
    def __call__(self, request: Request) -> TenantAwareCache:
        tenant_id = getattr(request.state, "tenant_id", None)
        return TenantAwareCache(self._redis, tenant_id)

class CurrentUser:
    """Provides current authenticated user"""
    
    async def __call__(self,
                       request: Request,
                       token: str = Depends(oauth2_scheme)) -> UserIdentity:
        # Validate JWT
        payload = await validate_jwt(token)
        
        # Resolve user identity
        resolver = UserIdentityResolver()
        user = await resolver.resolve_user(
            payload['sub'],
            request.state.tenant_id
        )
        
        if not user:
            raise HTTPException(401, "User not found")
        
        # Store in request state
        request.state.user = user
        return user

class RequirePermissions:
    """Check required permissions"""
    
    def __init__(self, permissions: List[str], require_all: bool = False):
        self.permissions = permissions
        self.require_all = require_all
    
    async def __call__(self,
                       request: Request,
                       user: UserIdentity = Depends(CurrentUser())):
        checker = PermissionChecker()
        
        for permission in self.permissions:
            has_perm = await checker.check_permission(
                user.platform_id,
                permission,
                {'tenant_id': user.tenant_id, 'schema': user.schema_name}
            )
            
            if self.require_all and not has_perm:
                raise HTTPException(403, f"Missing permission: {permission}")
            elif not self.require_all and has_perm:
                return user  # At least one permission satisfied
        
        if not self.require_all:
            raise HTTPException(403, "Insufficient permissions")
        
        return user

# Usage
@router.get("/users")
async def list_users(
    db: Pool = Depends(DatabaseDependency()),
    cache: Cache = Depends(CacheDependency()),
    user: UserIdentity = Depends(RequirePermissions(["users:list"]))
):
    # All dependencies automatically injected
    return await UserService(db, cache).list_users(user.schema_name)
```

## 4. Shared Data Models

### Base Models

```python
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

class TimestampMixin(BaseModel):
    """Mixin for timestamp fields"""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

class AuditMixin(TimestampMixin):
    """Mixin for audit fields"""
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    deleted_by: Optional[UUID] = None

class BaseEntity(AuditMixin):
    """Base for all entities"""
    id: UUID = Field(default_factory=uuid7)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }

# Shared domain models
class User(BaseEntity):
    """User model shared across services"""
    email: str = Field(..., max_length=320)
    username: Optional[str] = Field(None, max_length=39)
    external_user_id: str
    external_auth_provider: str = "keycloak"
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    status: str = "active"
    is_system_user: bool = False
    
    @validator('email')
    def validate_email(cls, v):
        # Email validation logic
        return v.lower()

class Permission(BaseModel):
    """Permission model"""
    code: str = Field(..., max_length=100)
    resource: str = Field(..., max_length=50)
    action: str = Field(..., max_length=50)
    scope_level: str = "tenant"
    is_dangerous: bool = False
    requires_mfa: bool = False
    
    @property
    def full_code(self) -> str:
        return f"{self.resource}:{self.action}"

class Role(BaseEntity):
    """Role model"""
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=150)
    role_level: str
    is_system: bool = False
    is_default: bool = False
    permissions: List[Permission] = []

# Request/Response models
class PaginationParams(BaseModel):
    """Standard pagination parameters"""
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: str = Field("asc", regex="^(asc|desc)$")

class PaginatedResponse(BaseModel):
    """Standard paginated response"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages
    
    @property
    def has_previous(self) -> bool:
        return self.page > 1

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

## 5. Repository Pattern

### Base Repository

```python
from typing import Protocol, TypeVar, Generic, Optional, List
from abc import ABC, abstractmethod

T = TypeVar('T', bound=BaseEntity)

class Repository(Protocol[T]):
    """Repository protocol"""
    
    async def get(self, id: UUID) -> Optional[T]:
        ...
    
    async def list(self, filters: dict = None, pagination: PaginationParams = None) -> List[T]:
        ...
    
    async def create(self, entity: T) -> T:
        ...
    
    async def update(self, id: UUID, updates: dict) -> Optional[T]:
        ...
    
    async def delete(self, id: UUID) -> bool:
        ...

class BaseRepository(Generic[T], ABC):
    """Base repository implementation"""
    
    def __init__(self, 
                 connection_manager: DynamicConnectionManager,
                 schema_resolver: SchemaResolver,
                 cache: Optional[Cache] = None):
        self._conn_manager = connection_manager
        self._schema_resolver = schema_resolver
        self._cache = cache
        self._table_name = self._get_table_name()
    
    @abstractmethod
    def _get_table_name(self) -> str:
        """Return table name for this repository"""
        pass
    
    @abstractmethod
    def _entity_from_row(self, row: dict) -> T:
        """Convert database row to entity"""
        pass
    
    async def get(self, id: UUID, context: RequestContext) -> Optional[T]:
        # Check cache
        if self._cache:
            cache_key = f"{self._table_name}:{context.tenant_id}:{id}"
            cached = await self._cache.get(cache_key)
            if cached:
                return self._entity_from_row(cached)
        
        # Get from database
        schema = await self._schema_resolver.resolve_schema(context)
        query = f"""
        SELECT * FROM {schema}.{self._table_name}
        WHERE id = $1 AND deleted_at IS NULL
        """
        
        pool = await self._get_connection(context)
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, id)
            
        if row:
            entity = self._entity_from_row(dict(row))
            # Cache result
            if self._cache:
                await self._cache.set(cache_key, dict(row), ttl=300)
            return entity
        
        return None
    
    async def list(self, 
                   context: RequestContext,
                   filters: dict = None,
                   pagination: PaginationParams = None) -> PaginatedResponse:
        schema = await self._schema_resolver.resolve_schema(context)
        
        # Build query
        where_clauses = ["deleted_at IS NULL"]
        params = []
        param_count = 0
        
        if filters:
            for key, value in filters.items():
                param_count += 1
                where_clauses.append(f"{key} = ${param_count}")
                params.append(value)
        
        where_sql = " AND ".join(where_clauses)
        
        # Count query
        count_query = f"""
        SELECT COUNT(*) FROM {schema}.{self._table_name}
        WHERE {where_sql}
        """
        
        # Data query
        pagination = pagination or PaginationParams()
        offset = (pagination.page - 1) * pagination.page_size
        
        data_query = f"""
        SELECT * FROM {schema}.{self._table_name}
        WHERE {where_sql}
        ORDER BY {pagination.sort_by or 'created_at'} {pagination.sort_order}
        LIMIT {pagination.page_size} OFFSET {offset}
        """
        
        pool = await self._get_connection(context)
        async with pool.acquire() as conn:
            # Execute both queries
            total = await conn.fetchval(count_query, *params)
            rows = await conn.fetch(data_query, *params)
        
        items = [self._entity_from_row(dict(row)) for row in rows]
        
        return PaginatedResponse(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=(total + pagination.page_size - 1) // pagination.page_size
        )

# Concrete implementation
class UserRepository(BaseRepository[User]):
    def _get_table_name(self) -> str:
        return "users"
    
    def _entity_from_row(self, row: dict) -> User:
        return User(**row)
    
    async def find_by_email(self, email: str, context: RequestContext) -> Optional[User]:
        schema = await self._schema_resolver.resolve_schema(context)
        query = f"""
        SELECT * FROM {schema}.users
        WHERE email = $1 AND deleted_at IS NULL
        """
        
        pool = await self._get_connection(context)
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, email)
        
        return self._entity_from_row(dict(row)) if row else None
```

## 6. Service Layer

### Base Service Pattern

```python
class BaseService:
    """Base service with common functionality"""
    
    def __init__(self, repository: Repository, cache: Optional[Cache] = None):
        self._repository = repository
        self._cache = cache
        self._logger = logging.getLogger(self.__class__.__name__)
    
    async def get_by_id(self, id: UUID, context: RequestContext) -> Optional[BaseEntity]:
        """Get entity by ID with caching"""
        try:
            return await self._repository.get(id, context)
        except Exception as e:
            self._logger.error(f"Error getting entity {id}: {e}")
            raise ServiceError(f"Unable to retrieve entity: {e}")
    
    async def list(self,
                   context: RequestContext,
                   filters: dict = None,
                   pagination: PaginationParams = None) -> PaginatedResponse:
        """List entities with pagination"""
        try:
            return await self._repository.list(context, filters, pagination)
        except Exception as e:
            self._logger.error(f"Error listing entities: {e}")
            raise ServiceError(f"Unable to list entities: {e}")

class UserService(BaseService):
    """User management service"""
    
    def __init__(self, 
                 user_repository: UserRepository,
                 permission_checker: PermissionChecker,
                 cache: Optional[Cache] = None):
        super().__init__(user_repository, cache)
        self._permission_checker = permission_checker
    
    async def create_user(self, 
                         user_data: dict,
                         context: RequestContext,
                         created_by: UUID) -> User:
        """Create new user with validation"""
        # Validate permissions
        can_create = await self._permission_checker.check_permission(
            created_by,
            "users:create",
            context
        )
        if not can_create:
            raise PermissionDeniedError("Cannot create users")
        
        # Validate data
        user = User(**user_data)
        user.created_by = created_by
        
        # Check for duplicates
        existing = await self._repository.find_by_email(user.email, context)
        if existing:
            raise DuplicateEntityError(f"User with email {user.email} already exists")
        
        # Create user
        created = await self._repository.create(user, context)
        
        # Invalidate cache
        if self._cache:
            await self._cache.delete(f"users:list:{context.tenant_id}")
        
        # Publish event
        await self._publish_event("user.created", {
            "user_id": str(created.id),
            "tenant_id": context.tenant_id,
            "created_by": str(created_by)
        })
        
        return created
```

## 7. Utility Functions

### Common Utilities

```python
import hashlib
import secrets
from datetime import datetime, timezone
from typing import Any, Dict

# UUID v7 generation
def uuid7() -> UUID:
    """Generate time-ordered UUID v7"""
    # Implementation of UUID v7
    timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
    random_bits = secrets.randbits(74)
    
    # Combine timestamp and random
    uuid_int = (timestamp << 74) | random_bits
    
    # Set version and variant bits
    uuid_int = (uuid_int & ~(0xF << 76)) | (0x7 << 76)  # Version 7
    uuid_int = (uuid_int & ~(0x3 << 62)) | (0x2 << 62)  # Variant 10
    
    return UUID(int=uuid_int)

# String utilities
def slugify(text: str) -> str:
    """Convert text to slug"""
    import re
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')

def sanitize_html(html: str) -> str:
    """Sanitize HTML content"""
    import bleach
    allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li']
    allowed_attrs = {'a': ['href', 'title']}
    return bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs)

# Hashing utilities
def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    import bcrypt
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    import bcrypt
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# Date/Time utilities
def utc_now() -> datetime:
    """Get current UTC time"""
    return datetime.now(timezone.utc)

def format_datetime(dt: datetime, format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime to string"""
    return dt.strftime(format)

def parse_datetime(date_string: str) -> datetime:
    """Parse datetime from string"""
    from dateutil import parser
    return parser.parse(date_string)

# Validation utilities
def is_valid_email(email: str) -> bool:
    """Validate email format"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_phone(phone: str) -> bool:
    """Validate phone number"""
    import phonenumbers
    try:
        parsed = phonenumbers.parse(phone, None)
        return phonenumbers.is_valid_number(parsed)
    except:
        return False

# Async utilities
async def retry_async(func, max_attempts: int = 3, delay: float = 1.0):
    """Retry async function with exponential backoff"""
    import asyncio
    
    for attempt in range(max_attempts):
        try:
            return await func()
        except Exception as e:
            if attempt == max_attempts - 1:
                raise
            await asyncio.sleep(delay * (2 ** attempt))

# Cache utilities
class CacheDecorator:
    """Decorator for caching function results"""
    
    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self.cache = {}
    
    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            key = self._make_key(func.__name__, args, kwargs)
            
            # Check cache
            if key in self.cache:
                value, expiry = self.cache[key]
                if datetime.now() < expiry:
                    return value
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Cache result
            expiry = datetime.now() + timedelta(seconds=self.ttl)
            self.cache[key] = (result, expiry)
            
            return result
        
        return wrapper
    
    def _make_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        key_parts = [func_name]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return ":".join(key_parts)
```

## 8. Exception Handling

### Global Exception Handlers

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import traceback

class BaseError(Exception):
    """Base exception for all custom errors"""
    
    def __init__(self, message: str, code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}

class ValidationError(BaseError):
    """Validation error"""
    status_code = 400

class AuthenticationError(BaseError):
    """Authentication error"""
    status_code = 401

class PermissionDeniedError(BaseError):
    """Permission denied error"""
    status_code = 403

class NotFoundError(BaseError):
    """Resource not found error"""
    status_code = 404

class ConflictError(BaseError):
    """Resource conflict error"""
    status_code = 409

class ServiceError(BaseError):
    """Internal service error"""
    status_code = 500

def register_exception_handlers(app: FastAPI):
    """Register global exception handlers"""
    
    @app.exception_handler(BaseError)
    async def handle_base_error(request: Request, exc: BaseError):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=getattr(request.state, 'request_id', None)
            ).dict()
        )
    
    @app.exception_handler(ValidationError)
    async def handle_validation_error(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error="validation_error",
                message=str(exc),
                details=exc.errors() if hasattr(exc, 'errors') else {},
                request_id=getattr(request.state, 'request_id', None)
            ).dict()
        )
    
    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        # Log full traceback
        logger.error(f"Unexpected error: {traceback.format_exc()}")
        
        # Return generic error to client
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="internal_error",
                message="An unexpected error occurred",
                request_id=getattr(request.state, 'request_id', None)
            ).dict()
        )
```

## 9. Application Factory

### FastAPI Application Builder

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

class NeoCommonsApp:
    """Application factory for neo-commons"""
    
    def __init__(self, 
                 service_config: ServiceConfig,
                 connection_manager: Optional[DynamicConnectionManager] = None,
                 cache_client: Optional[Redis] = None):
        self.config = service_config
        self.connection_manager = connection_manager or self._create_connection_manager()
        self.cache = cache_client or self._create_cache_client()
        self.app: Optional[FastAPI] = None
    
    def _create_connection_manager(self) -> DynamicConnectionManager:
        """Create default connection manager"""
        return DynamicConnectionManager(
            admin_db_url=self.config.admin_database_url,
            encryption_key=self.config.encryption_key
        )
    
    def _create_cache_client(self) -> Redis:
        """Create default Redis client"""
        return Redis.from_url(
            self.config.redis_url,
            password=self.config.redis_password,
            decode_responses=True
        )
    
    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """Application lifespan management"""
        # Startup
        await self.connection_manager.initialize()
        await self.cache.ping()
        
        # Initialize background tasks
        asyncio.create_task(self._health_check_loop())
        
        yield
        
        # Shutdown
        await self.connection_manager.close_all()
        await self.cache.close()
    
    def create_app(self) -> FastAPI:
        """Create and configure FastAPI application"""
        
        self.app = FastAPI(
            title=self.config.service_name,
            version=self.config.service_version,
            lifespan=self.lifespan
        )
        
        # Register middleware
        self._register_middleware()
        
        # Register exception handlers
        register_exception_handlers(self.app)
        
        # Register dependencies
        self._register_dependencies()
        
        # Register routes
        self._register_routes()
        
        return self.app
    
    def _register_middleware(self):
        """Register middleware stack"""
        # CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Custom middleware
        register_middleware(self.app, self.config)
    
    def _register_dependencies(self):
        """Register dependency injection"""
        # Database
        self.app.dependency_overrides[get_db] = lambda: DatabaseDependency(
            self.connection_manager
        )
        
        # Cache
        self.app.dependency_overrides[get_cache] = lambda: CacheDependency(
            self.cache
        )
        
        # Current user
        self.app.dependency_overrides[get_current_user] = CurrentUser
    
    def _register_routes(self):
        """Register API routes"""
        # Health check
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "service": self.config.service_name}
        
        # Metrics
        @self.app.get("/metrics")
        async def metrics():
            return await self._collect_metrics()
    
    async def _health_check_loop(self):
        """Background health check"""
        while True:
            try:
                # Check database
                await self.connection_manager.health_check_all()
                
                # Check cache
                await self.cache.ping()
                
            except Exception as e:
                logger.error(f"Health check failed: {e}")
            
            await asyncio.sleep(30)

# Usage in service
from neo_commons import NeoCommonsApp, NeoAdminApiConfig

config = NeoAdminApiConfig()
neo_app = NeoCommonsApp(config)
app = neo_app.create_app()

# Add service-specific routes
from .routes import admin_router
app.include_router(admin_router, prefix="/api/admin")
```

## Implementation Strategy

### Phase 1: Core Infrastructure (Week 1)
- [ ] Configuration management system
- [ ] Base middleware implementation
- [ ] Dependency injection framework

### Phase 2: Data Layer (Week 2)
- [ ] Shared models and validators
- [ ] Repository pattern implementation
- [ ] Service layer abstraction

### Phase 3: Utilities & Helpers (Week 3)
- [ ] Common utility functions
- [ ] Exception handling framework
- [ ] Logging and monitoring

### Phase 4: Integration (Week 4)
- [ ] Application factory
- [ ] Service templates
- [ ] Documentation and examples

## Benefits

1. **Consistency**: All services use the same patterns and components
2. **Rapid Development**: Ready-to-use components accelerate development
3. **Maintainability**: Single source of truth for shared functionality
4. **Flexibility**: Everything can be overridden for specific needs
5. **Type Safety**: Full type hints and runtime validation
6. **Performance**: Built-in caching and optimization
7. **Security**: Centralized security controls and validation

## Conclusion

This Global Components Framework provides a comprehensive foundation for building enterprise-grade services. With ready-to-use components that can be easily customized, teams can focus on business logic rather than infrastructure, while maintaining consistency and quality across all services.