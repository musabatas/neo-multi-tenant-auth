# Neo-Commons Feature Development Principles

## Architecture Overview

The neo-commons library follows a **Feature-First + Clean Core** architecture with protocol-based dependency injection. This document outlines the key principles, patterns, and implementation details based on the organizations feature analysis.

## Core Architecture Patterns

### 1. Feature-First Organization

```
features/
├── {feature_name}/
│   ├── entities/          # Domain objects and protocols
│   ├── services/          # Business logic orchestration
│   ├── repositories/      # Data access implementations  
│   ├── models/            # API request/response models
│   ├── routers/           # FastAPI route handlers
│   └── utils/             # Feature-specific utilities
```

**Key Principles:**
- Each feature is self-contained with clear boundaries
- Features communicate through well-defined protocols
- Business logic stays within feature boundaries
- Cross-cutting concerns handled by infrastructure

### 2. Clean Core Integration

**Core Responsibilities (Minimal):**
- Value objects (OrganizationId, UserId, etc.)
- Domain exceptions (EntityNotFoundError, ValidationError)
- Shared contracts (RequestContext, common protocols)

**Feature Responsibilities:**
- Domain entities with business logic
- Service orchestration and workflows
- Repository patterns for data access
- API models and routing

### 3. Protocol-Based Dependency Injection

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class OrganizationRepository(Protocol):
    async def save(self, organization: Organization) -> Organization: ...
    async def find_by_id(self, id: OrganizationId) -> Optional[Organization]: ...
    # ... other methods
```

**Benefits:**
- Flexible implementation swapping
- Enhanced testability with mocks
- Clear contract definitions
- Loose coupling between layers

## Entity Design Patterns

### Domain Entity Structure

```python
@dataclass
class Organization:
    # Core identifiers
    id: OrganizationId
    name: str
    slug: str
    
    # Optional business fields
    legal_name: Optional[str] = None
    tax_id: Optional[str] = None
    
    # Extensibility
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Audit fields
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None
```

**Key Features:**
- **Immutable by Design**: Use `@dataclass` with validation in `__post_init__`
- **Rich Domain Methods**: Business logic methods like `verify()`, `soft_delete()`, `update_address()`
- **Extensible Metadata**: JSONB-like metadata field for custom attributes
- **Audit Trail**: Standard timestamp fields for tracking changes
- **Soft Delete Support**: `deleted_at` field with `is_deleted` property

### Entity Validation Patterns

```python
def __post_init__(self):
    """Post-initialization validation."""
    from ..utils.validation import OrganizationValidationRules
    
    # Centralized validation
    OrganizationValidationRules.validate_slug(self.slug)
    OrganizationValidationRules.validate_display_name(self.name)
```

**Validation Strategy:**
- Validation logic in dedicated utils modules
- Entity validation in `__post_init__` for data integrity
- Service-level validation for complex business rules
- Repository validation for database constraints

## Service Layer Patterns

### Service Architecture

```python
class OrganizationService:
    def __init__(
        self,
        repository: OrganizationRepository,
        cache: Optional[OrganizationCache] = None,
        config_resolver: Optional[OrganizationConfigResolver] = None,
        notification_service: Optional[OrganizationNotificationService] = None,
        validation_service: Optional[OrganizationValidationService] = None
    ):
```

**Key Patterns:**
- **Dependency Injection**: Protocol-based dependencies
- **Optional Services**: Non-critical services are optional
- **Single Responsibility**: Each service handles one domain
- **Error Handling**: Comprehensive error handling with logging

### Business Logic Orchestration

```python
@organization_error_handler("create organization")
@log_organization_operation("create organization", include_timing=True)
async def create_organization(self, name: str, slug: Optional[str] = None, **kwargs) -> Organization:
    # 1. Validation
    if not slug:
        slug = OrganizationValidationRules.name_to_slug(name)
    
    # 2. Business rules
    existing = await self.get_by_slug(slug)
    if existing:
        raise EntityAlreadyExistsError("Organization", f"slug:{slug}")
    
    # 3. Entity creation
    organization = Organization(id=org_id, name=name, slug=slug, **kwargs)
    
    # 4. Persistence
    saved = await self._repository.save(organization)
    
    # 5. Side effects (cache, notifications)
    if self._cache:
        await self._cache.set(saved)
    if self._notification_service:
        await self._notification_service.notify_organization_created(saved)
    
    return saved
```

**Service Method Structure:**
1. Input validation and transformation
2. Business rule enforcement
3. Entity creation/modification
4. Repository operations
5. Side effects (caching, notifications, logging)

## Repository Layer Patterns

### Repository Architecture

```python
class OrganizationDatabaseRepository(PaginatedRepositoryMixin[Organization]):
    def __init__(self, database_repository: DatabaseRepository, schema: str):
        self._db = database_repository
        self._schema = schema
        self._table = f"{schema}.organizations"
```

**Key Design Principles:**
- **Infrastructure Reuse**: Leverages existing `DatabaseRepository` service
- **Schema Flexibility**: Schema name passed as parameter (not hardcoded)
- **Mixin Integration**: Uses `PaginatedRepositoryMixin` for standardized pagination
- **Protocol Compliance**: Implements repository protocols for dependency injection

### Performance Optimization Strategies

#### Light vs Full Data Queries

```python
# Light data - 9 essential fields for listing
async def find_active_light(self, limit: int = 20, offset: int = 0) -> List[Organization]:
    query = ORGANIZATION_LIST_LIGHT.format(schema=self._schema)
    # Returns: id, name, slug, industry, country_code, is_active, verified_at, created_at, updated_at

# Full data - 20+ fields for detailed views  
async def find_active_full(self, limit: int = 20, offset: int = 0) -> List[Organization]:
    query = ORGANIZATION_LIST_FULL.format(schema=self._schema)
    # Returns: All fields including metadata, address, branding, etc.
```

**Usage Patterns:**
- **Light Mode**: Use for listing, search results, dropdowns
- **Full Mode**: Use for detail views, edit forms, admin panels
- **Performance Gain**: Light queries reduce memory usage by ~60%

#### Admin Query Patterns

```python
async def search_full_admin(
    self, 
    query: str = None, 
    filters: Optional[Dict[str, Any]] = None,
    include_deleted: bool = False,  # Key admin feature
    limit: int = 20,
    offset: int = 0
) -> List[Organization]:
```

**Admin-Specific Features:**
- **Include Deleted**: `include_deleted` parameter for soft-deleted records
- **Extended Filters**: More comprehensive filter options
- **Audit Support**: Full data access for compliance/audit needs

### Database Integration Patterns

```python
# Query with performance monitoring
async with monitor_query_performance("INSERT", "organization_create",
                                    organization_id=str(organization.id.value),
                                    schema=self._schema):
    result = await self._db.execute_query(query, params)

# Async JSON serialization for performance
brand_colors_json = await serialize_brand_colors_async(organization.brand_colors)
metadata_json = await serialize_metadata_async(organization.metadata)
```

**Performance Features:**
- **Query Monitoring**: Built-in performance tracking
- **Async JSON**: Non-blocking JSON serialization for large objects
- **Connection Reuse**: Leverages existing database connection pool
- **Error Context**: Rich error context with schema and operation info

## Caching Layer Patterns

### Cache Architecture

```python
class OrganizationCacheAdapter:
    def __init__(self, cache_service: Cache, key_prefix: str = "org"):
        self._cache = cache_service
        self._key_prefix = key_prefix
        self._default_ttl = 3600  # 1 hour default
```

**Key Features:**
- **Dual Key Storage**: Cache by both ID and slug for flexible access
- **TTL Management**: Configurable Time-To-Live for cache entries
- **Pattern-Based Keys**: Consistent key naming with prefixes
- **Performance Monitoring**: Cache hit/miss tracking

### Cache Strategy Patterns

```python
async def set(self, organization: Organization, ttl: Optional[int] = None) -> bool:
    # Cache by ID
    id_key = self._make_id_key(organization.id)
    id_result = await self._cache.set(id_key, serialized_data, ttl)
    
    # Cache by slug  
    slug_key = self._make_slug_key(organization.slug)
    slug_result = await self._cache.set(slug_key, serialized_data, ttl)
    
    return id_result and slug_result
```

**Cache Invalidation:**
- **Multi-Key Deletion**: Clear both ID and slug keys
- **User Cache Clearing**: Clear user-specific organization caches
- **Pattern Deletion**: Support for wildcard cache clearing

## Utility Modules Pattern

### Centralized Validation

```python
class OrganizationValidationRules:
    """Centralized validation rules for organization data."""
    
    SLUG_PATTERN = re.compile(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$')
    NAME_MIN_LENGTH = 2
    NAME_MAX_LENGTH = 100
    
    @staticmethod
    def validate_slug(slug: str) -> str:
        # Centralized validation logic
        if not OrganizationValidationRules.SLUG_PATTERN.match(slug):
            raise ValueError("Invalid slug format")
        return slug
```

**Benefits:**
- **DRY Principle**: Single source of truth for validation rules
- **Reusability**: Used across entities, services, and API layers
- **Consistency**: Ensures uniform validation across application
- **Testability**: Isolated validation logic for unit testing

### Error Handling Patterns

```python
@organization_error_handler("create organization")
@log_organization_operation("create organization", include_timing=True)
async def create_organization(self, name: str, **kwargs) -> Organization:
    # Method implementation with automatic error handling and logging
```

**Error Handling Features:**
- **Consistent Error Context**: Standardized error information
- **Operation Tracking**: Performance and timing metrics
- **Domain Exception Handling**: Special handling for business exceptions
- **Flexible Response**: Configurable re-raise vs. default return behavior

### Performance Monitoring

```python
async with monitor_query_performance("SELECT", "organization_find_by_id",
                                    organization_id=str(organization_id.value),
                                    schema=self._schema):
    result = await self._db.fetch_one(query, [str(organization_id.value)])
```

**Monitoring Features:**
- **Query Performance**: Automatic timing and metrics collection
- **Context Enrichment**: Rich metadata for operations
- **Non-intrusive**: Uses context managers for clean implementation
- **Aggregation Ready**: Structured data for analytics dashboards

## API Layer Patterns

### Request/Response Models

#### Model Architecture

```python
class CreateOrganizationRequest(BaseModel):
    name: str = Field(..., description="Organization display name")
    slug: Optional[str] = Field(None, description="Auto-generated if not provided")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @validator("name")
    def validate_name(cls, v):
        return OrganizationValidationRules.validate_display_name(v)
    
    class Config:
        extra = "allow"  # Service-specific extensions
        json_schema_extra = {"example": {...}}
```

**Model Design Principles:**
- **Field Validation**: Use Pydantic validators with centralized validation rules
- **Optional Fields**: Clear distinction between required and optional fields
- **Extensibility**: `extra = "allow"` for service-specific field additions
- **Documentation**: Comprehensive field descriptions and examples
- **Type Safety**: Proper type hints for IDE support and validation

#### Response Model Patterns

```python
class OrganizationResponse(BaseModel):
    id: str = Field(..., description="Organization ID")
    name: str = Field(..., description="Organization display name")
    # ... other fields
    
    @classmethod
    def from_entity(cls, organization) -> "OrganizationResponse":
        """Create response from organization entity."""
        return cls(
            id=str(organization.id.value),
            name=organization.name,
            # ... map all fields
        )
```

**Response Features:**
- **Entity Mapping**: `from_entity()` class method for entity-to-response conversion
- **Multiple Variants**: Light (9 fields) vs Full (20+ fields) response models
- **Consistent Structure**: Standard fields across all response models
- **Rich Examples**: JSON schema examples for API documentation

### Router Architecture

#### Router Configuration

```python
router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"],
    responses={
        404: {"description": "Organization not found"},
        409: {"description": "Organization already exists"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)
```

**Configuration Features:**
- **Consistent Prefixes**: Clear URL structure
- **OpenAPI Tags**: Logical grouping of endpoints
- **Standard Responses**: Common error responses defined centrally
- **Documentation**: Comprehensive response descriptions

#### Endpoint Patterns

```python
@router.post("/", response_model=OrganizationResponse, status_code=201)
async def create_organization(
    request: CreateOrganizationRequest,
    service: OrganizationService = Depends(get_organization_service)
) -> OrganizationResponse:
    try:
        # 1. Convert request to service parameters
        create_params = request.model_dump(exclude_unset=True)
        
        # 2. Call service layer
        organization = await service.create_organization(**create_params)
        
        # 3. Convert to response model
        return OrganizationResponse.from_entity(organization)
        
    except EntityAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create: {str(e)}")
```

**Endpoint Structure:**
1. **Request Parsing**: Pydantic models for automatic validation
2. **Service Delegation**: Business logic handled by service layer
3. **Response Mapping**: Entity-to-response conversion
4. **Error Handling**: Domain-specific exception mapping to HTTP status codes
5. **Documentation**: Comprehensive endpoint descriptions and response schemas

### Performance-Optimized Endpoints

#### Light vs Full Data Support

```python
@router.get("/", response_model=OrganizationListResponse)
async def list_organizations(
    light: bool = Query(True, description="Return light data or full data"),
    include_deleted: bool = Query(False, description="Admin-only feature"),
    service: OrganizationService = Depends(get_organization_service)
):
    if include_deleted:  # Admin endpoints
        if light:
            orgs = await service.get_active_organizations_light_admin(include_deleted, per_page, offset)
            return [OrganizationSummaryResponse.from_entity(org) for org in orgs]
        else:
            orgs = await service.get_active_organizations_full_admin(include_deleted, per_page, offset)
            return [OrganizationResponse.from_entity(org) for org in orgs]
    else:  # Regular endpoints
        if light:
            orgs = await service.get_active_organizations_light(per_page, offset)
            return [OrganizationSummaryResponse.from_entity(org) for org in orgs]
        else:
            orgs = await service.get_active_organizations_full(per_page, offset)
            return [OrganizationResponse.from_entity(org) for org in orgs]
```

**Performance Features:**
- **Query Optimization**: Light vs full data queries for different use cases
- **Admin Support**: `include_deleted` parameter for administrative access
- **Response Variants**: Different response models for different data loads
- **Database Efficiency**: Service methods optimized for query performance

#### Advanced Search Support

```python
@router.post("/search", response_model=OrganizationSearchResponse)
async def search_organizations(
    request: OrganizationSearchRequest,
    light: bool = Query(True, description="Return light or full data"),
    service: OrganizationService = Depends(get_organization_service)
):
    import time
    start_time = time.time()
    
    # Use optimized search methods
    if light:
        organizations = await service.search_organizations_light(
            query=request.query,
            filters=request.get_combined_filters(),
            limit=request.limit,
            offset=0
        )
        org_responses = [OrganizationSummaryResponse.from_entity(org) for org in organizations]
    else:
        organizations = await service.search_organizations_full(...)
        org_responses = [OrganizationResponse.from_entity(org) for org in organizations]
    
    # Performance tracking
    duration_ms = int((time.time() - start_time) * 1000)
    
    return OrganizationSearchResponse(
        organizations=org_responses,
        query=request.query,
        filters=request.filters or {},
        total=len(org_responses),
        took_ms=duration_ms
    )
```

**Search Features:**
- **POST for Complex Search**: Allows complex filter objects in request body
- **Combined Filters**: Merge direct parameters with filter objects
- **Performance Tracking**: Built-in search timing for monitoring
- **Response Metadata**: Include query details and performance metrics in response

### Metadata and Configuration Endpoints

```python
@router.put("/{organization_id}/metadata", response_model=OrganizationMetadataResponse)
async def update_organization_metadata(
    organization_id: str = Path(..., description="Organization ID"),
    request: OrganizationMetadataRequest = None,
    service: OrganizationService = Depends(get_organization_service)
):
    org_id = OrganizationId(organization_id)
    organization = await service.update_metadata(
        org_id,
        request.metadata,
        merge=request.merge  # Support both merge and replace operations
    )
    return OrganizationMetadataResponse(
        organization_id=organization_id,
        metadata=organization.metadata or {},
        updated_at=organization.updated_at
    )
```

**Metadata Features:**
- **JSONB Support**: Rich metadata operations with PostgreSQL JSONB
- **Merge vs Replace**: Flexible metadata update strategies
- **Search Integration**: Metadata-based search capabilities
- **Dot Notation**: Support for nested metadata access patterns

### Performance Monitoring Integration

```python
@router.get("/performance/stats", tags=["Performance"])
async def get_performance_stats(
    operation_name: Optional[str] = Query(None, description="Filter by operation")
) -> Dict[str, Any]:
    monitor = get_performance_monitor()
    stats = monitor.get_stats(operation_name)
    
    # Convert to serializable format with performance metrics
    serializable_stats = {}
    for name, stat in stats.items():
        serializable_stats[name] = {
            "avg_time_ms": round(stat.avg_time_ms, 3),
            "p95_time_ms": round(stat.p95_time_ms, 3),
            "success_rate": round(stat.success_rate, 2),
            "sub_ms_percentage": round(stat.sub_ms_percentage, 2)
        }
    
    return {"statistics": serializable_stats, "generated_at": datetime.now().isoformat()}
```

**Monitoring Features:**
- **Built-in Performance Endpoints**: Expose performance metrics via API
- **Operation Filtering**: Filter metrics by specific operations
- **Sub-millisecond Tracking**: Track operations meeting performance targets
- **Real-time Data**: Live performance statistics for monitoring dashboards

## Integration Patterns

### Pagination Integration

```python
# Using standardized pagination from neo-commons
from ....features.pagination.entities import OffsetPaginationRequest, OffsetPaginationResponse

# Service layer pagination
async def list_paginated(
    self,
    pagination: OffsetPaginationRequest
) -> OffsetPaginationResponse[Organization]:
    return await self._repository.find_paginated(pagination)

# Repository mixin usage
class OrganizationDatabaseRepository(PaginatedRepositoryMixin[Organization]):
    async def find_paginated(
        self,
        pagination: OffsetPaginationRequest
    ) -> OffsetPaginationResponse[Organization]:
        base_query = f"SELECT * FROM {{schema}}.organizations WHERE is_active = true"
        count_query = f"SELECT COUNT(*) FROM {{schema}}.organizations WHERE is_active = true"
        
        return await super().find_paginated(
            pagination=pagination,
            base_query=base_query,
            count_query=count_query
        )
```

**Pagination Features:**
- **Standardized Interface**: Common pagination patterns across features
- **Database-Level Pagination**: Efficient database queries with offset/limit
- **Flexible Sorting**: Multiple sort fields with direction support
- **Filter Integration**: Combine pagination with search filters
- **Metadata Rich**: Response includes total counts, page info, navigation flags

## Best Practices Summary

### Development Principles

1. **DRY (Don't Repeat Yourself)**
   - Centralized validation in utils modules
   - Reuse existing infrastructure services
   - Common patterns across entity/service/repository layers
   - Shared error handling decorators

2. **Protocol-Based Design**
   - Use `@runtime_checkable` protocols for dependency injection
   - Clear contract definitions between layers
   - Enhanced testability with protocol mocks
   - Flexible implementation swapping

3. **Performance-First Architecture**
   - Light vs full data query patterns
   - Async JSON serialization for large objects
   - Database-level pagination
   - Built-in performance monitoring

4. **Extensibility Support**
   - Metadata fields for custom attributes
   - `extra = "allow"` in Pydantic models
   - Optional service dependencies
   - Admin-specific endpoint variations

5. **Error Handling Standards**
   - Domain-specific exceptions
   - Consistent HTTP status code mapping
   - Rich error context with operation details
   - Graceful degradation patterns

### File Organization Standards

```
features/{feature_name}/
├── entities/              # Domain entities and protocols
│   ├── {entity}.py       # Main entity with business logic
│   ├── protocols.py      # Repository and service protocols
│   └── __init__.py       # Export public interfaces
├── services/              # Business logic orchestration
│   ├── {service}.py      # Service implementation
│   └── __init__.py       
├── repositories/          # Data access implementations
│   ├── {repo}.py         # Database repository
│   ├── {cache}.py        # Cache adapter
│   └── __init__.py
├── models/                # API request/response models
│   ├── requests.py       # Pydantic request models
│   ├── responses.py      # Pydantic response models
│   └── __init__.py
├── routers/               # FastAPI route handlers
│   ├── {router}.py       # Main router implementation
│   ├── admin_router.py   # Admin-specific endpoints (if needed)
│   ├── dependencies.py   # Router dependencies
│   └── __init__.py
└── utils/                 # Feature-specific utilities
    ├── validation.py     # Centralized validation rules
    ├── error_handling.py # Error handling decorators
    ├── performance_monitor.py  # Performance tracking
    ├── queries.py        # SQL query constants
    ├── json_async.py     # Async JSON operations
    └── __init__.py
```

### Key Implementation Guidelines

1. **Always check neo-commons first** before implementing new functionality
2. **Use existing infrastructure services** - database, cache, configuration
3. **Implement validation in centralized utils** for reusability
4. **Follow entity → service → repository → API layer pattern**
5. **Provide both light and full data access methods** for performance
6. **Use protocol-based dependency injection** for testability
7. **Include comprehensive error handling** with operation context
8. **Implement performance monitoring** for all database operations
9. **Support admin operations** with include_deleted patterns
10. **Follow OpenAPI documentation standards** with clear examples