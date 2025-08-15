"""
Tenant context value objects.

Immutable types representing tenant and organizational context for authorization.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class TenantStatus(str, Enum):
    """Tenant status for access control."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    CANCELLED = "cancelled"
    PENDING = "pending"


class SubscriptionTier(str, Enum):
    """Subscription tier affecting access permissions."""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


@dataclass(frozen=True)
class TenantContext:
    """
    Immutable tenant context for authorization decisions.
    
    Contains tenant information needed for access control and feature gating.
    """
    # Core tenant info
    tenant_id: str
    tenant_slug: str
    tenant_name: str
    
    # Organization context
    organization_id: str
    organization_name: Optional[str] = None
    
    # Status and subscription
    status: TenantStatus = TenantStatus.ACTIVE
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    
    # Regional and database context
    region_id: Optional[str] = None
    database_name: Optional[str] = None
    schema_name: Optional[str] = None
    
    # Keycloak context
    auth_realm: Optional[str] = None
    
    # Feature flags and limits
    feature_flags: Dict[str, bool] = None
    resource_limits: Dict[str, int] = None
    
    # Metadata
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize collections as empty if None."""
        if self.feature_flags is None:
            object.__setattr__(self, 'feature_flags', {})
        if self.resource_limits is None:
            object.__setattr__(self, 'resource_limits', {})
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})
    
    @property
    def is_active(self) -> bool:
        """Check if tenant is active."""
        return self.status == TenantStatus.ACTIVE
    
    @property
    def is_suspended(self) -> bool:
        """Check if tenant is suspended."""
        return self.status == TenantStatus.SUSPENDED
    
    @property
    def is_trial(self) -> bool:
        """Check if tenant is in trial."""
        return self.status == TenantStatus.TRIAL
    
    @property
    def is_enterprise(self) -> bool:
        """Check if tenant has enterprise subscription."""
        return self.subscription_tier == SubscriptionTier.ENTERPRISE
    
    @property
    def is_premium(self) -> bool:
        """Check if tenant has premium subscription (pro or enterprise)."""
        return self.subscription_tier in [SubscriptionTier.PROFESSIONAL, SubscriptionTier.ENTERPRISE]
    
    @property
    def context_key(self) -> str:
        """Get context key for caching."""
        return f"tenant:{self.tenant_id}"
    
    def get_cache_namespace(self) -> str:
        """Get cache namespace for tenant-specific caching."""
        return f"tenant:{self.tenant_id}"
    
    def has_feature(self, feature_name: str) -> bool:
        """
        Check if tenant has a specific feature enabled.
        
        Args:
            feature_name: Feature flag name to check
            
        Returns:
            True if feature is enabled, False if disabled or not found
        """
        return self.feature_flags.get(feature_name, False)
    
    def get_resource_limit(self, resource_name: str, default: int = 0) -> int:
        """
        Get resource limit for tenant.
        
        Args:
            resource_name: Resource limit name to check
            default: Default value if limit not found
            
        Returns:
            Resource limit value
        """
        return self.resource_limits.get(resource_name, default)
    
    def can_access_resource(self, resource_name: str, required_tier: SubscriptionTier = SubscriptionTier.FREE) -> bool:
        """
        Check if tenant subscription tier allows access to resource.
        
        Args:
            resource_name: Resource to check access for
            required_tier: Minimum subscription tier required
            
        Returns:
            True if tenant can access resource
        """
        # Define tier hierarchy
        tier_hierarchy = {
            SubscriptionTier.FREE: 0,
            SubscriptionTier.STARTER: 1,
            SubscriptionTier.PROFESSIONAL: 2,
            SubscriptionTier.ENTERPRISE: 3,
            SubscriptionTier.CUSTOM: 4
        }
        
        current_tier_level = tier_hierarchy.get(self.subscription_tier, 0)
        required_tier_level = tier_hierarchy.get(required_tier, 0)
        
        return current_tier_level >= required_tier_level
    
    def get_database_connection_key(self) -> str:
        """Get database connection key for regional routing."""
        if self.region_id:
            return f"region:{self.region_id}"
        return "default"
    
    def get_schema_name(self) -> str:
        """Get schema name for tenant data isolation."""
        return self.schema_name or f"tenant_{self.tenant_slug}"
    
    @classmethod
    def platform_context(cls) -> "TenantContext":
        """Create platform-level tenant context (no specific tenant)."""
        return cls(
            tenant_id="platform",
            tenant_slug="platform", 
            tenant_name="Platform",
            organization_id="platform",
            organization_name="Platform Organization",
            status=TenantStatus.ACTIVE,
            subscription_tier=SubscriptionTier.ENTERPRISE
        )
    
    def with_feature_flags(self, feature_flags: Dict[str, bool]) -> "TenantContext":
        """Create new context with updated feature flags."""
        new_flags = {**self.feature_flags, **feature_flags}
        return TenantContext(
            tenant_id=self.tenant_id,
            tenant_slug=self.tenant_slug,
            tenant_name=self.tenant_name,
            organization_id=self.organization_id,
            organization_name=self.organization_name,
            status=self.status,
            subscription_tier=self.subscription_tier,
            region_id=self.region_id,
            database_name=self.database_name,
            schema_name=self.schema_name,
            auth_realm=self.auth_realm,
            feature_flags=new_flags,
            resource_limits=self.resource_limits,
            metadata=self.metadata
        )
    
    def with_resource_limits(self, resource_limits: Dict[str, int]) -> "TenantContext":
        """Create new context with updated resource limits."""
        new_limits = {**self.resource_limits, **resource_limits}
        return TenantContext(
            tenant_id=self.tenant_id,
            tenant_slug=self.tenant_slug,
            tenant_name=self.tenant_name,
            organization_id=self.organization_id,
            organization_name=self.organization_name,
            status=self.status,
            subscription_tier=self.subscription_tier,
            region_id=self.region_id,
            database_name=self.database_name,
            schema_name=self.schema_name,
            auth_realm=self.auth_realm,
            feature_flags=self.feature_flags,
            resource_limits=new_limits,
            metadata=self.metadata
        )
    
    def __str__(self) -> str:
        return f"{self.tenant_name} ({self.tenant_slug})"
    
    def __repr__(self) -> str:
        return f"TenantContext(id='{self.tenant_id}', slug='{self.tenant_slug}', status='{self.status}')"