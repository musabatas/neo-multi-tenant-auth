"""Realm configuration domain entity."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Set
from ....core.value_objects.identifiers import TenantId
from ..value_objects import RealmIdentifier


@dataclass
class RealmConfig:
    """Realm configuration entity for authentication domain.
    
    Handles ONLY realm configuration representation and management.
    Does not perform realm operations - that's handled by realm services.
    """
    
    # Core Identity
    realm_id: RealmIdentifier
    tenant_id: Optional[TenantId] = None
    
    # Basic Configuration
    realm_name: str = ""
    display_name: Optional[str] = None
    enabled: bool = True
    
    # Authentication Configuration
    login_with_email_allowed: bool = True
    duplicate_emails_allowed: bool = False
    verify_email: bool = True
    reset_password_allowed: bool = True
    remember_me: bool = True
    
    # Token Configuration
    access_token_lifespan: int = 300  # 5 minutes in seconds
    refresh_token_lifespan: int = 1800  # 30 minutes in seconds
    sso_session_idle_timeout: int = 1800  # 30 minutes in seconds
    sso_session_max_lifespan: int = 36000  # 10 hours in seconds
    
    # Security Configuration
    brute_force_protection: bool = True
    permanent_lockout: bool = False
    max_failure_wait_seconds: int = 900  # 15 minutes
    minimum_quick_login_wait_seconds: int = 60
    wait_increment_seconds: int = 60
    quick_login_check_millis: int = 1000
    max_delta_time_seconds: int = 43200  # 12 hours
    failure_reset_time_seconds: int = 43200  # 12 hours
    
    # Registration Configuration
    registration_allowed: bool = True
    registration_email_as_username: bool = True
    edit_username_allowed: bool = False
    
    # Password Policy
    password_policy: Dict[str, Any] = field(default_factory=lambda: {
        'length': 8,
        'digits': 1,
        'lower_case': 1,
        'upper_case': 1,
        'special_chars': 1,
        'not_username': True,
        'not_email': True,
        'password_history': 3
    })
    
    # SSL Configuration
    ssl_required: str = "external"  # all, external, none
    
    # Custom Configuration
    custom_themes: Set[str] = field(default_factory=set)
    allowed_origins: Set[str] = field(default_factory=set)
    web_origins: Set[str] = field(default_factory=set)
    
    # Internationalization
    internationalization_enabled: bool = True
    supported_locales: Set[str] = field(default_factory=lambda: {'en', 'es', 'fr', 'de'})
    default_locale: str = 'en'
    
    # Events Configuration
    events_enabled: bool = True
    events_expiration: int = 2592000  # 30 days in seconds
    admin_events_enabled: bool = True
    admin_events_details_enabled: bool = True
    
    # Additional Configuration
    custom_config: Dict[str, Any] = field(default_factory=dict)
    features: Set[str] = field(default_factory=set)
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1.0"
    
    def __post_init__(self) -> None:
        """Initialize realm configuration after creation."""
        # Ensure timezone awareness
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)
        
        if self.updated_at.tzinfo is None:
            self.updated_at = self.updated_at.replace(tzinfo=timezone.utc)
        
        # Set default realm name if not provided
        if not self.realm_name and self.tenant_id:
            self.realm_name = f"tenant-{self.tenant_id.value}"
        
        # Validate configuration consistency
        self._validate_configuration()
    
    def _validate_configuration(self) -> None:
        """Validate realm configuration for consistency."""
        # Validate token lifespans
        if self.access_token_lifespan <= 0:
            raise ValueError("Access token lifespan must be positive")
        
        if self.refresh_token_lifespan <= self.access_token_lifespan:
            raise ValueError("Refresh token lifespan must be greater than access token lifespan")
        
        # Validate password policy
        if self.password_policy.get('length', 0) < 4:
            raise ValueError("Minimum password length must be at least 4 characters")
        
        # Validate SSL configuration
        if self.ssl_required not in ['all', 'external', 'none']:
            raise ValueError("SSL required must be 'all', 'external', or 'none'")
        
        # Validate locale
        if self.default_locale not in self.supported_locales:
            self.supported_locales.add(self.default_locale)
    
    @property
    def is_active(self) -> bool:
        """Check if realm is active and properly configured."""
        return self.enabled and bool(self.realm_name)
    
    @property
    def is_secure(self) -> bool:
        """Check if realm has secure configuration."""
        return (
            self.ssl_required in ['all', 'external'] and
            self.brute_force_protection and
            self.verify_email and
            self.password_policy.get('length', 0) >= 8
        )
    
    @property
    def session_timeout_minutes(self) -> int:
        """Get session timeout in minutes."""
        return self.sso_session_idle_timeout // 60
    
    @property
    def access_token_lifespan_minutes(self) -> int:
        """Get access token lifespan in minutes."""
        return self.access_token_lifespan // 60
    
    def update_configuration(self, **kwargs) -> None:
        """Update realm configuration."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        self.updated_at = datetime.now(timezone.utc)
        self._validate_configuration()
    
    def add_custom_config(self, key: str, value: Any) -> None:
        """Add custom configuration entry."""
        self.custom_config[key] = value
        self.updated_at = datetime.now(timezone.utc)
    
    def remove_custom_config(self, key: str) -> None:
        """Remove custom configuration entry."""
        self.custom_config.pop(key, None)
        self.updated_at = datetime.now(timezone.utc)
    
    def add_feature(self, feature: str) -> None:
        """Add a feature to the realm."""
        self.features.add(feature.lower())
        self.updated_at = datetime.now(timezone.utc)
    
    def remove_feature(self, feature: str) -> None:
        """Remove a feature from the realm."""
        self.features.discard(feature.lower())
        self.updated_at = datetime.now(timezone.utc)
    
    def has_feature(self, feature: str) -> bool:
        """Check if realm has a specific feature."""
        return feature.lower() in self.features
    
    def add_allowed_origin(self, origin: str) -> None:
        """Add an allowed origin."""
        self.allowed_origins.add(origin)
        self.updated_at = datetime.now(timezone.utc)
    
    def remove_allowed_origin(self, origin: str) -> None:
        """Remove an allowed origin."""
        self.allowed_origins.discard(origin)
        self.updated_at = datetime.now(timezone.utc)
    
    def is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed."""
        return origin in self.allowed_origins
    
    def add_supported_locale(self, locale: str) -> None:
        """Add a supported locale."""
        self.supported_locales.add(locale.lower())
        self.updated_at = datetime.now(timezone.utc)
    
    def is_locale_supported(self, locale: str) -> bool:
        """Check if locale is supported."""
        return locale.lower() in self.supported_locales
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert realm configuration to dictionary representation."""
        return {
            'realm_id': str(self.realm_id.value),
            'tenant_id': str(self.tenant_id.value) if self.tenant_id else None,
            'realm_name': self.realm_name,
            'display_name': self.display_name,
            'enabled': self.enabled,
            'login_with_email_allowed': self.login_with_email_allowed,
            'duplicate_emails_allowed': self.duplicate_emails_allowed,
            'verify_email': self.verify_email,
            'reset_password_allowed': self.reset_password_allowed,
            'remember_me': self.remember_me,
            'access_token_lifespan': self.access_token_lifespan,
            'refresh_token_lifespan': self.refresh_token_lifespan,
            'sso_session_idle_timeout': self.sso_session_idle_timeout,
            'sso_session_max_lifespan': self.sso_session_max_lifespan,
            'brute_force_protection': self.brute_force_protection,
            'permanent_lockout': self.permanent_lockout,
            'max_failure_wait_seconds': self.max_failure_wait_seconds,
            'minimum_quick_login_wait_seconds': self.minimum_quick_login_wait_seconds,
            'wait_increment_seconds': self.wait_increment_seconds,
            'quick_login_check_millis': self.quick_login_check_millis,
            'max_delta_time_seconds': self.max_delta_time_seconds,
            'failure_reset_time_seconds': self.failure_reset_time_seconds,
            'registration_allowed': self.registration_allowed,
            'registration_email_as_username': self.registration_email_as_username,
            'edit_username_allowed': self.edit_username_allowed,
            'password_policy': self.password_policy,
            'ssl_required': self.ssl_required,
            'custom_themes': list(self.custom_themes),
            'allowed_origins': list(self.allowed_origins),
            'web_origins': list(self.web_origins),
            'internationalization_enabled': self.internationalization_enabled,
            'supported_locales': list(self.supported_locales),
            'default_locale': self.default_locale,
            'events_enabled': self.events_enabled,
            'events_expiration': self.events_expiration,
            'admin_events_enabled': self.admin_events_enabled,
            'admin_events_details_enabled': self.admin_events_details_enabled,
            'custom_config': self.custom_config,
            'features': list(self.features),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'version': self.version,
            'is_active': self.is_active,
            'is_secure': self.is_secure,
            'session_timeout_minutes': self.session_timeout_minutes,
            'access_token_lifespan_minutes': self.access_token_lifespan_minutes
        }
    
    def __str__(self) -> str:
        """String representation."""
        status = "active" if self.is_active else "inactive"
        return f"RealmConfig(realm={self.realm_name}, status={status}, secure={self.is_secure})"
    
    def __repr__(self) -> str:
        """Debug representation."""
        return (
            f"RealmConfig(realm_id={self.realm_id}, realm_name={self.realm_name}, "
            f"tenant_id={self.tenant_id}, enabled={self.enabled})"
        )