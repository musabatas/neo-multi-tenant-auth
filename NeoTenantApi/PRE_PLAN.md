# NeoTenantApi Development Plan

## Overview

NeoTenantApi is the tenant-specific API service that handles all business logic and operations within individual tenant contexts. It provides secure, isolated access to tenant data while supporting comprehensive RBAC with custom permissions per user.

## Tech Stack

### Core Technologies
- **Language**: Python 3.13+
- **Framework**: FastAPI (latest version)
- **Database**: PostgreSQL 17+ with asyncpg
- **Cache**: Redis 7+ with redis-py
- **Authentication**: Keycloak integration via python-keycloak
- **Validation**: Pydantic v2
- **Testing**: pytest, pytest-asyncio, pytest-cov
- **Documentation**: OpenAPI/Scalar (auto-generated)

### Key Libraries
- **asyncpg**: Direct PostgreSQL access for performance
- **redis-py**: Async Redis client with Lua scripting support
- **python-keycloak**: Keycloak realm-specific operations
- **httpx**: Async HTTP client
- **prometheus-client**: Metrics collection
- **structlog**: Structured logging with tenant context
- **python-jose**: JWT token handling
- **passlib**: Password hashing (backup for local auth)

## Database Usage

### Database Access Strategy
- Connects to tenant-specific database/schema dynamically
- Database connection info retrieved from admin.database_connections
- Supports both schema-based and database-based multi-tenancy
- Connection pooling per tenant for optimal performance

### Regional Databases
- **neofast_shared_us**: US region tenant schemas
- **neofast_shared_eu**: EU region tenant schemas (GDPR)
- **tenant_***: Dedicated databases for enterprise tenants

### Tenant Schema Structure
- Uses tenant_template schema as base
- Dynamic schema creation per tenant
- Complete data isolation between tenants
- Shared platform_common functions

## Core Features

### 1. Authentication & Authorization
**Purpose**: Secure tenant-specific authentication with Keycloak integration

**Features**:
- Multi-realm Keycloak authentication
- JWT token validation with realm-specific keys
- Automatic user sync from Keycloak to PostgreSQL
- Session management with Redis
- Refresh token handling
- Password reset workflows
- Social login integration support
- Device fingerprinting

**Design Considerations**:
- Realm isolation per tenant
- Token validation caching
- Graceful Keycloak downtime handling
- Rate limiting per user/IP

### 2. User Management
**Purpose**: Comprehensive user lifecycle management within tenant

**Features**:
- User CRUD operations with Keycloak sync
- Profile management with custom attributes
- Avatar upload and management
- User preferences and settings
- Activity tracking and last seen
- Bulk user operations
- User import/export
- Deactivation and reactivation

**Design Considerations**:
- Bi-directional sync with Keycloak
- Efficient bulk operations
- GDPR compliance for data handling
- Soft delete for audit trail

### 3. RBAC & Permissions
**Purpose**: Fine-grained permission system with custom user permissions

**Features**:
- Hierarchical role management
- Resource-based permissions (resource.action.scope)
- Custom permissions per user
- Permission inheritance from roles
- Dynamic permission evaluation
- Permission caching with sub-millisecond checks
- Role templates
- Bulk permission assignment

**Design Considerations**:
- Redis-based permission cache
- Efficient permission resolution algorithm
- Real-time permission updates
- Audit trail for permission changes

### 4. Team Management
**Purpose**: Organize users into hierarchical teams

**Features**:
- Team creation and hierarchy
- Team member management
- Team-based permissions
- Team roles and responsibilities
- Cross-team collaboration
- Team analytics and reporting
- Team templates
- Organizational chart visualization

**Design Considerations**:
- Efficient tree structure queries
- Team-level resource sharing
- Performance with deep hierarchies
- Team merger and split operations

### 5. Invitation System
**Purpose**: Secure user onboarding and invitation

**Features**:
- Email-based invitations
- Invitation templates
- Role pre-assignment
- Expiration management
- Bulk invitations
- Invitation tracking
- Custom onboarding flows
- Re-invitation capability

**Design Considerations**:
- Secure token generation
- Email delivery reliability
- Invitation abuse prevention
- Customizable workflows per tenant

### 6. Settings Management
**Purpose**: Tenant-specific configuration and preferences

**Features**:
- Tenant settings CRUD
- Feature toggles
- Branding customization
- Notification preferences
- Integration configurations
- Webhook settings
- API configuration
- Compliance settings

**Design Considerations**:
- Settings validation and constraints
- Cache invalidation on changes
- Settings versioning
- Default value management

### 7. Audit Logging
**Purpose**: Comprehensive activity tracking for compliance

**Features**:
- All user action logging
- Resource change tracking
- Search and filter capabilities
- Audit report generation
- Tamper-proof storage
- Retention policies
- Export functionality
- Real-time audit streaming

**Design Considerations**:
- High-performance write path
- Efficient storage strategy
- Query optimization for reports
- Integration with SIEM systems

### 8. Resource Management
**Purpose**: Generic resource management framework

**Features**:
- Dynamic resource types
- CRUD operations per resource
- Resource-level permissions
- Relationships between resources
- Tagging and categorization
- Search and filtering
- Bulk operations
- Import/export

**Design Considerations**:
- Flexible schema design
- Performance with large datasets
- Full-text search capabilities
- Resource versioning

### 9. Notification System
**Purpose**: Multi-channel notification delivery

**Features**:
- In-app notifications
- Email notifications
- SMS notifications (optional)
- Push notifications (optional)
- Notification templates
- User preferences
- Delivery tracking
- Bulk notifications

**Design Considerations**:
- Queue-based delivery
- Retry mechanisms
- Template management
- Delivery analytics

### 10. Integration APIs
**Purpose**: Enable third-party integrations

**Features**:
- Webhook management
- API key generation
- OAuth2 client management
- Rate limiting per client
- Integration marketplace
- Custom integration builder
- Event streaming
- Data synchronization

**Design Considerations**:
- Secure credential storage
- Rate limiting strategies
- Event delivery guarantees
- API versioning

## API Design

### Endpoint Structure
- Tenant context from JWT or subdomain
- RESTful resource design
- Consistent URL patterns
- Nested resource support
- Batch operations endpoints

### Authentication Flow
1. Frontend obtains JWT from Keycloak tenant realm
2. API validates JWT with cached public key
3. User context loaded from cache or database
4. Permissions evaluated for requested resource
5. Audit trail recorded

### Permission Evaluation
- Cache check (< 1ms)
- Database fallback if cache miss
- Role hierarchy traversal
- Custom permission overlay
- Resource-specific checks

## Performance Optimizations

### Caching Strategy
- User permissions: 5-minute TTL
- User profile: 15-minute TTL
- Tenant settings: 1-hour TTL
- Permission checks: 1-minute TTL
- Automatic invalidation on changes

### Database Optimizations
- Connection pooling per tenant
- Prepared statements
- JSONB indexes for permissions
- Partial indexes for active records
- Query result caching

### Async Operations
- All I/O operations async
- Background task processing
- Webhook delivery queues
- Batch processing for bulk operations

## Security Considerations

### Tenant Isolation
- Complete data isolation
- No cross-tenant queries
- Tenant context validation
- Schema/database level separation

### Authentication Security
- JWT signature validation
- Token expiration enforcement
- Refresh token rotation
- Rate limiting per user
- Suspicious activity detection

### Data Protection
- Encryption at rest for sensitive data
- PII handling compliance
- Audit trail for all access
- Data retention policies
- Right to be forgotten support

## Multi-Region Support

### Region Detection
- User's tenant determines region
- Database connection from registry
- Latency-based routing
- Regional compliance rules

### Data Residency
- EU tenants use EU databases
- US tenants use US databases
- No cross-region data transfer
- Regional backup strategies

## Development Guidelines

### Code Organization
- Feature-based modules
- Repository pattern for data access
- Service layer for business logic
- Clear separation of concerns
- Dependency injection

### Testing Strategy
- Unit tests for business logic
- Integration tests for API endpoints
- Permission system tests
- Multi-tenant isolation tests
- Performance benchmarks

### Error Handling
- Consistent error responses
- Proper HTTP status codes
- Detailed error messages
- Error tracking and monitoring
- Graceful degradation

### Monitoring
- Request/response logging
- Performance metrics
- Error rates and alerts
- Cache hit rates
- Database query performance