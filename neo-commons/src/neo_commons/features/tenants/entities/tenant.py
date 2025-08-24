"""Tenant domain entity.

This module defines the Tenant entity and related business logic.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from ....core.value_objects import TenantId, OrganizationId
from ....config.constants import TenantStatus, DeploymentType


@dataclass
class Tenant:
    """Tenant domain entity.
    
    Represents a tenant instance within an organization.
    Matches admin.tenants table structure.
    """
    
    id: TenantId
    organization_id: OrganizationId
    slug: str
    name: str
    description: Optional[str] = None
    schema_name: str = ""
    database_name: Optional[str] = None
    custom_domain: Optional[str] = None
    deployment_type: DeploymentType = DeploymentType.SCHEMA
    environment: str = "production"  # admin.environment_type
    region_id: Optional[str] = None  # UUID references admin.regions
    database_connection_id: Optional[str] = None  # UUID references admin.database_connections
    
    # External auth (required fields)
    external_auth_provider: str = "keycloak"  # platform_common.auth_provider
    external_auth_realm: str = ""
    external_user_id: str = ""
    external_auth_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Configuration
    allow_impersonations: bool = False
    status: TenantStatus = TenantStatus.PENDING
    internal_notes: Optional[str] = None
    features_enabled: Dict[str, Any] = field(default_factory=dict)
    feature_overrides: Dict[str, Any] = field(default_factory=dict)
    
    # Activity tracking
    provisioned_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    
    # Metadata and audit
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Post-initialization validation using centralized validation."""
        from ..utils.validation import TenantValidationRules
        
        # Validate using centralized rules
        errors = TenantValidationRules.validate_all(
            self.slug, 
            self.name, 
            self.description,
            self.schema_name if self.schema_name else None,
            self.custom_domain
        )
        
        if errors:
            raise ValueError(f"Tenant validation failed: {'; '.join(errors)}")
        
        # Set default schema name if not provided
        if not self.schema_name:
            object.__setattr__(self, 'schema_name', TenantValidationRules.generate_schema_name(self.slug))
    
    @property
    def is_active(self) -> bool:
        """Check if tenant is active."""
        return self.status == TenantStatus.ACTIVE and self.deleted_at is None
    
    @property
    def is_pending(self) -> bool:
        """Check if tenant is pending."""
        return self.status == TenantStatus.PENDING
    
    @property
    def is_provisioning(self) -> bool:
        """Check if tenant is being provisioned."""
        return self.status == TenantStatus.PROVISIONING
    
    @property
    def is_suspended(self) -> bool:
        """Check if tenant is suspended."""
        return self.status == TenantStatus.SUSPENDED
    
    @property
    def is_migrating(self) -> bool:
        """Check if tenant is migrating."""
        return self.status == TenantStatus.MIGRATING
    
    @property
    def is_archived(self) -> bool:
        """Check if tenant is archived."""
        return self.status == TenantStatus.ARCHIVED
    
    @property
    def is_deleted(self) -> bool:
        """Check if tenant is deleted."""
        return self.status == TenantStatus.DELETED or self.deleted_at is not None
    
    def has_feature(self, feature: str) -> bool:
        """Check if tenant has specific feature enabled."""
        # Check overrides first, then enabled features
        if feature in self.feature_overrides:
            return bool(self.feature_overrides[feature])
        return bool(self.features_enabled.get(feature, False))
    
    def enable_feature(self, feature: str, override: bool = False) -> None:
        """Enable feature for tenant."""
        if override:
            self.feature_overrides[feature] = True
        else:
            self.features_enabled[feature] = True
        self.updated_at = datetime.now(timezone.utc)
    
    def disable_feature(self, feature: str, override: bool = False) -> None:
        """Disable feature for tenant."""
        if override:
            self.feature_overrides[feature] = False
        else:
            self.features_enabled[feature] = False
        self.updated_at = datetime.now(timezone.utc)
    
    def update_last_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def start_provisioning(self) -> None:
        """Start tenant provisioning process."""
        self.status = TenantStatus.PROVISIONING
        self.updated_at = datetime.now(timezone.utc)
    
    def complete_provisioning(self) -> None:
        """Complete tenant provisioning."""
        self.status = TenantStatus.ACTIVE
        self.provisioned_at = datetime.now(timezone.utc)
        self.activated_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def suspend(self, reason: Optional[str] = None) -> None:
        """Suspend tenant."""
        self.status = TenantStatus.SUSPENDED
        self.suspended_at = datetime.now(timezone.utc)
        if reason:
            if not self.internal_notes:
                self.internal_notes = ""
            self.internal_notes += f"\nSuspended: {reason}"
        self.updated_at = datetime.now(timezone.utc)
    
    def activate(self) -> None:
        """Activate tenant."""
        self.status = TenantStatus.ACTIVE
        self.activated_at = datetime.now(timezone.utc)
        self.suspended_at = None
        self.updated_at = datetime.now(timezone.utc)
    
    def start_migration(self) -> None:
        """Start tenant migration process."""
        self.status = TenantStatus.MIGRATING
        self.updated_at = datetime.now(timezone.utc)
    
    def archive(self, reason: Optional[str] = None) -> None:
        """Archive tenant."""
        self.status = TenantStatus.ARCHIVED
        if reason:
            if not self.internal_notes:
                self.internal_notes = ""
            self.internal_notes += f"\nArchived: {reason}"
        self.updated_at = datetime.now(timezone.utc)
    
    def soft_delete(self, reason: Optional[str] = None) -> None:
        """Soft delete tenant."""
        self.status = TenantStatus.DELETED
        self.deleted_at = datetime.now(timezone.utc)
        if reason:
            if not self.internal_notes:
                self.internal_notes = ""
            self.internal_notes += f"\nDeleted: {reason}"
        self.updated_at = datetime.now(timezone.utc)
    
    def add_internal_note(self, note: str) -> None:
        """Add internal note to tenant."""
        timestamp = datetime.now(timezone.utc).isoformat()
        note_with_timestamp = f"[{timestamp}] {note}"
        if self.internal_notes:
            self.internal_notes += f"\n{note_with_timestamp}"
        else:
            self.internal_notes = note_with_timestamp
        self.updated_at = datetime.now(timezone.utc)