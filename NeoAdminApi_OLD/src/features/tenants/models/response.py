"""
Response models for tenant API endpoints.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from src.common.models.base import BaseSchema, PaginatedResponse
from .domain import Tenant, TenantContact, DeploymentType, EnvironmentType, TenantStatus, AuthProvider


class OrganizationSummary(BaseSchema):
    """Summary information about an organization."""
    
    id: UUID
    name: str
    slug: str
    is_active: bool


class RegionSummary(BaseSchema):
    """Summary information about a region."""
    
    id: UUID
    code: str
    name: str
    country_code: str
    is_active: bool


class SubscriptionSummary(BaseSchema):
    """Summary information about a subscription."""
    
    id: UUID
    plan_name: str
    plan_tier: str
    status: str
    current_period_end: datetime


class TenantResponse(BaseSchema):
    """Response model for tenant details."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    organization: OrganizationSummary
    slug: str
    name: str
    description: Optional[str]
    
    # Database configuration
    schema_name: str
    database_name: Optional[str]
    deployment_type: DeploymentType
    environment: EnvironmentType
    
    # Regional configuration
    region: Optional[RegionSummary]
    custom_domain: Optional[str]
    
    # Authentication
    external_auth_provider: AuthProvider
    external_auth_realm: str
    allow_impersonations: bool
    
    # Status
    status: TenantStatus
    provisioned_at: Optional[datetime]
    activated_at: Optional[datetime]
    suspended_at: Optional[datetime]
    last_activity_at: Optional[datetime]
    
    # Subscription
    subscription: Optional[SubscriptionSummary]
    
    # Features
    features_enabled: Dict[str, bool]
    feature_overrides: Dict[str, Any]
    
    # Metadata
    internal_notes: Optional[str]
    metadata: Dict[str, Any]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    # Statistics
    user_count: int = 0
    active_user_count: int = 0
    storage_used_mb: float = 0
    
    @classmethod
    def from_domain(
        cls,
        tenant: Tenant,
        organization: OrganizationSummary,
        region: Optional[RegionSummary] = None,
        subscription: Optional[SubscriptionSummary] = None,
        stats: Optional[Dict[str, Any]] = None
    ) -> "TenantResponse":
        """Create response from domain model."""
        stats = stats or {}
        
        return cls(
            id=tenant.id,
            organization=organization,
            slug=tenant.slug,
            name=tenant.name,
            description=tenant.description,
            schema_name=tenant.schema_name,
            database_name=tenant.database_name,
            deployment_type=tenant.deployment_type,
            environment=tenant.environment,
            region=region,
            custom_domain=tenant.custom_domain,
            external_auth_provider=tenant.external_auth_provider,
            external_auth_realm=tenant.external_auth_realm,
            allow_impersonations=tenant.allow_impersonations,
            status=tenant.status,
            provisioned_at=tenant.provisioned_at,
            activated_at=tenant.activated_at,
            suspended_at=tenant.suspended_at,
            last_activity_at=tenant.last_activity_at,
            subscription=subscription,
            features_enabled=tenant.features_enabled,
            feature_overrides=tenant.feature_overrides,
            internal_notes=tenant.internal_notes,
            metadata=tenant.metadata,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
            user_count=stats.get('user_count', 0),
            active_user_count=stats.get('active_user_count', 0),
            storage_used_mb=stats.get('storage_used_mb', 0.0)
        )


class TenantListItem(BaseSchema):
    """Simplified tenant information for list views."""
    
    id: UUID
    organization_id: UUID
    organization_name: str
    slug: str
    name: str
    status: TenantStatus
    environment: EnvironmentType
    region_code: Optional[str]
    custom_domain: Optional[str]
    user_count: int
    created_at: datetime
    last_activity_at: Optional[datetime]


class TenantListSummary(BaseSchema):
    """Summary statistics for tenant list."""
    
    total_tenants: int
    active_tenants: int
    suspended_tenants: int
    by_status: Dict[str, int]
    by_environment: Dict[str, int]
    by_region: Dict[str, int]
    by_deployment_type: Dict[str, int]
    total_users: int
    total_storage_mb: float


class TenantListResponse(BaseSchema):
    """Response model for tenant list with pagination."""
    
    items: List[TenantListItem]
    pagination: Dict[str, Any]


class TenantContactResponse(BaseSchema):
    """Response model for tenant contact."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: UUID
    user_id: UUID
    user_email: str
    user_name: str
    contact_type: str
    contact_info: Dict[str, Any]
    is_primary: bool
    receive_notifications: bool
    receive_billing_emails: bool
    receive_technical_alerts: bool
    receive_marketing_emails: bool
    emergency_phone: Optional[str]
    alternative_email: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_domain(
        cls,
        contact: TenantContact,
        user_email: str,
        user_name: str
    ) -> "TenantContactResponse":
        """Create response from domain model."""
        return cls(
            id=contact.id,
            tenant_id=contact.tenant_id,
            user_id=contact.user_id,
            user_email=user_email,
            user_name=user_name,
            contact_type=contact.contact_type,
            contact_info=contact.contact_info,
            is_primary=contact.is_primary,
            receive_notifications=contact.receive_notifications,
            receive_billing_emails=contact.receive_billing_emails,
            receive_technical_alerts=contact.receive_technical_alerts,
            receive_marketing_emails=contact.receive_marketing_emails,
            emergency_phone=contact.emergency_phone,
            alternative_email=contact.alternative_email,
            created_at=contact.created_at,
            updated_at=contact.updated_at
        )


class TenantProvisionResponse(BaseSchema):
    """Response model for tenant provisioning."""
    
    tenant_id: UUID
    status: str
    provisioning_started_at: datetime
    estimated_completion_time: datetime
    keycloak_realm_created: bool
    database_schema_created: bool
    initial_admin_created: bool
    welcome_email_sent: bool
    message: str