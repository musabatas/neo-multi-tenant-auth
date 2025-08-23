"""Constants and enums for neo-commons.

This module defines all the constants, enums, and configuration values
that are used throughout the neo-commons library. These correspond to
the database enums defined in the platform migrations.
"""

from enum import Enum
from typing import Final


# Performance and Cache Configuration
class PerformanceTargets:
    """Performance targets for the platform."""
    
    PERMISSION_CHECK_MAX_MS: Final[int] = 1
    API_P95_LATENCY_MAX_MS: Final[int] = 100
    SIMPLE_QUERY_MAX_MS: Final[int] = 10
    COMPLEX_QUERY_MAX_MS: Final[int] = 50
    CACHE_HIT_RATE_MIN_PERCENT: Final[int] = 90


class CacheKeys:
    """Cache key patterns for Redis."""
    
    USER_PERMISSIONS: Final[str] = "user:permissions:{user_id}:{tenant_id}"
    USER_ROLES: Final[str] = "user:roles:{user_id}:{tenant_id}"
    TENANT_CONFIG: Final[str] = "tenant:config:{tenant_id}"
    SCHEMA_MAPPING: Final[str] = "schema:mapping:{tenant_id}"
    DB_CONNECTION: Final[str] = "db:connection:{connection_name}"
    KEYCLOAK_PUBLIC_KEY: Final[str] = "keycloak:public_key:{realm}"


class CacheTTL:
    """Cache TTL values in seconds."""
    
    PERMISSIONS_SHORT: Final[int] = 300      # 5 minutes
    PERMISSIONS_LONG: Final[int] = 3600      # 1 hour
    TENANT_CONFIG: Final[int] = 1800         # 30 minutes
    SCHEMA_MAPPING: Final[int] = 7200        # 2 hours
    DB_CONNECTION: Final[int] = 1800         # 30 minutes
    KEYCLOAK_PUBLIC_KEY: Final[int] = 3600   # 1 hour


# Database Schema Names
class DatabaseSchemas:
    """Database schema names."""
    
    ADMIN: Final[str] = "admin"
    PLATFORM_COMMON: Final[str] = "platform_common"
    TENANT_TEMPLATE: Final[str] = "tenant_template"
    TENANT_PREFIX: Final[str] = "tenant_"
    ANALYTICS: Final[str] = "analytics"


# Platform Common Enums (from platform_common schema)
class AuthProvider(str, Enum):
    """Authentication providers - corresponds to platform_common.auth_provider."""
    
    KEYCLOAK = "keycloak"
    AUTH0 = "auth0"
    AUTHENTIK = "authentik"
    AUTHELIA = "authelia"
    AZURE = "azure"
    GOOGLE = "google"
    CUSTOM = "custom"


class RoleLevel(str, Enum):
    """Role levels - corresponds to platform_common.role_level."""
    
    SYSTEM = "system"
    PLATFORM = "platform"
    TENANT = "tenant"
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"
    VIEWER = "viewer"
    GUEST = "guest"


class UserStatus(str, Enum):
    """User status - corresponds to platform_common.user_status."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class PermissionScope(str, Enum):
    """Permission scope - corresponds to platform_common.permission_scope."""
    
    PLATFORM = "platform"
    TENANT = "tenant"
    TEAM = "team"
    USER = "user"


class TeamType(str, Enum):
    """Team types - corresponds to platform_common.team_types."""
    
    DEPARTMENT = "department"
    PROJECT = "project"
    WORKING_GROUP = "working_group"
    COMMITTEE = "committee"
    OTHER = "other"


class RiskLevel(str, Enum):
    """Risk levels - corresponds to platform_common.risk_levels."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SettingType(str, Enum):
    """Setting types - corresponds to platform_common.setting_type."""
    
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    JSON = "json"
    ARRAY = "array"
    EMAIL = "email"
    URL = "url"
    PASSWORD = "password"
    TEXT = "text"
    SELECT = "select"
    MULTISELECT = "multiselect"


# Admin Schema Enums (from admin schema)
class ContactType(str, Enum):
    """Contact types - corresponds to admin.contact_type."""
    
    OWNER = "owner"
    ADMIN = "admin"
    BILLING = "billing"
    TECHNICAL = "technical"
    LEGAL = "legal"
    EMERGENCY = "emergency"


class TenantStatus(str, Enum):
    """Tenant status - corresponds to admin.tenant_status."""
    
    PENDING = "pending"
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    MIGRATING = "migrating"
    ARCHIVED = "archived"
    DELETED = "deleted"


class DeploymentType(str, Enum):
    """Deployment types - corresponds to admin.deployment_type."""
    
    SCHEMA = "schema"
    DATABASE = "database"
    DEDICATED = "dedicated"


class EnvironmentType(str, Enum):
    """Environment types - corresponds to admin.environment_type."""
    
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class PlanTier(str, Enum):
    """Plan tiers - corresponds to admin.plan_tier."""
    
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class BillingCycle(str, Enum):
    """Billing cycles - corresponds to admin.billing_cycle."""
    
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionStatus(str, Enum):
    """Subscription status - corresponds to admin.subscription_status."""
    
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"


class InvoiceStatus(str, Enum):
    """Invoice status - corresponds to admin.invoice_status."""
    
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"


class LineItemType(str, Enum):
    """Line item types - corresponds to admin.line_item_type."""
    
    SUBSCRIPTION = "subscription"
    USAGE = "usage"
    ADDON = "addon"
    DISCOUNT = "discount"
    TAX = "tax"


class ConnectionType(str, Enum):
    """Database connection types - corresponds to admin.connection_type."""
    
    PRIMARY = "primary"
    REPLICA = "replica"
    ANALYTICS = "analytics"
    BACKUP = "backup"


class HealthStatus(str, Enum):
    """Health status - corresponds to admin.health_status."""
    
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ActorType(str, Enum):
    """Actor types for audit logs - corresponds to admin.actor_type."""
    
    USER = "user"
    SYSTEM = "system"
    API = "api"
    SERVICE = "service"


# Application Constants
class DefaultValues:
    """Default values used throughout the application."""
    
    DEFAULT_REGION: Final[str] = "us-east"
    DEFAULT_SCHEMA: Final[str] = "admin"
    DEFAULT_PAGE_SIZE: Final[int] = 50
    MAX_PAGE_SIZE: Final[int] = 1000
    DEFAULT_TENANT_LIMITS: Final[dict] = {
        "max_users": 100,
        "max_teams": 10,
        "max_roles": 50,
        "max_permissions": 500,
        "storage_gb": 10,
        "api_requests_per_hour": 10000,
    }


class ValidationLimits:
    """Validation limits for various fields."""
    
    USERNAME_MIN_LENGTH: Final[int] = 3
    USERNAME_MAX_LENGTH: Final[int] = 50
    PASSWORD_MIN_LENGTH: Final[int] = 8
    PASSWORD_MAX_LENGTH: Final[int] = 128
    EMAIL_MAX_LENGTH: Final[int] = 255
    NAME_MAX_LENGTH: Final[int] = 100
    DESCRIPTION_MAX_LENGTH: Final[int] = 500
    SLUG_MAX_LENGTH: Final[int] = 50
    URL_MAX_LENGTH: Final[int] = 2000
    JSON_MAX_SIZE_BYTES: Final[int] = 1024 * 1024  # 1MB


class SecurityDefaults:
    """Security-related default values."""
    
    TOKEN_EXPIRY_SECONDS: Final[int] = 3600      # 1 hour
    REFRESH_TOKEN_EXPIRY_SECONDS: Final[int] = 86400 * 7  # 7 days
    RATE_LIMIT_PER_MINUTE: Final[int] = 60
    RATE_LIMIT_PER_HOUR: Final[int] = 1000
    MAX_LOGIN_ATTEMPTS: Final[int] = 5
    LOCKOUT_DURATION_MINUTES: Final[int] = 15
    MFA_CODE_EXPIRY_SECONDS: Final[int] = 300     # 5 minutes


# Error Codes
class ErrorCodes:
    """Standardized error codes."""
    
    # Authentication
    INVALID_CREDENTIALS = "AUTH_001"
    TOKEN_EXPIRED = "AUTH_002"
    TOKEN_INVALID = "AUTH_003"
    USER_INACTIVE = "AUTH_004"
    USER_NOT_FOUND = "AUTH_005"
    MFA_REQUIRED = "AUTH_006"
    
    # Authorization
    PERMISSION_DENIED = "AUTHZ_001"
    ROLE_NOT_FOUND = "AUTHZ_002"
    INSUFFICIENT_PERMISSIONS = "AUTHZ_003"
    
    # Tenant
    TENANT_NOT_FOUND = "TENANT_001"
    TENANT_INACTIVE = "TENANT_002"
    TENANT_LIMIT_EXCEEDED = "TENANT_003"
    TENANT_PROVISIONING = "TENANT_004"
    
    # Database
    CONNECTION_FAILED = "DB_001"
    CONNECTION_NOT_FOUND = "DB_002"
    SCHEMA_NOT_FOUND = "DB_003"
    QUERY_FAILED = "DB_004"
    
    # Cache
    CACHE_CONNECTION_FAILED = "CACHE_001"
    CACHE_KEY_INVALID = "CACHE_002"
    
    # Validation
    VALIDATION_FAILED = "VALID_001"
    INVALID_INPUT = "VALID_002"
    REQUIRED_FIELD_MISSING = "VALID_003"
    
    # Rate Limiting
    RATE_LIMIT_EXCEEDED = "RATE_001"
    
    # Configuration
    CONFIG_INVALID = "CONFIG_001"
    CONFIG_MISSING = "CONFIG_002"


# HTTP Headers
class Headers:
    """Standard HTTP headers used in the platform."""
    
    REQUEST_ID = "X-Request-ID"
    TENANT_ID = "X-Tenant-ID"
    USER_ID = "X-User-ID"
    CORRELATION_ID = "X-Correlation-ID"
    API_VERSION = "X-API-Version"
    RATE_LIMIT_REMAINING = "X-RateLimit-Remaining"
    RATE_LIMIT_RESET = "X-RateLimit-Reset"


# Audit Event Types
class AuditEventTypes:
    """Types of events that should be audited."""
    
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_ACTIVATED = "user.activated"
    USER_DEACTIVATED = "user.deactivated"
    
    TENANT_CREATED = "tenant.created"
    TENANT_UPDATED = "tenant.updated"
    TENANT_DELETED = "tenant.deleted"
    TENANT_SUSPENDED = "tenant.suspended"
    TENANT_ACTIVATED = "tenant.activated"
    
    PERMISSION_GRANTED = "permission.granted"
    PERMISSION_REVOKED = "permission.revoked"
    ROLE_ASSIGNED = "role.assigned"
    ROLE_UNASSIGNED = "role.unassigned"
    
    SYSTEM_CONFIG_CHANGED = "system.config.changed"
    SECURITY_VIOLATION = "security.violation"
    DATA_EXPORT = "data.export"
    DATA_IMPORT = "data.import"


# API Versions
class APIVersions:
    """Supported API versions."""
    
    V1 = "v1"
    V2 = "v2"
    CURRENT = V1
    SUPPORTED = [V1, V2]


# Feature Flags
class FeatureFlags:
    """Feature flags that can be enabled/disabled per tenant."""
    
    ADVANCED_ANALYTICS = "advanced_analytics"
    CUSTOM_ROLES = "custom_roles"
    API_ACCESS = "api_access"
    WEBHOOKS = "webhooks"
    AUDIT_LOGS = "audit_logs"
    SSO_INTEGRATION = "sso_integration"
    MULTI_FACTOR_AUTH = "multi_factor_auth"
    CUSTOM_BRANDING = "custom_branding"
    ADVANCED_PERMISSIONS = "advanced_permissions"
    TEAM_MANAGEMENT = "team_management"