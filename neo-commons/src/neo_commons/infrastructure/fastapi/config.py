"""FastAPI configuration classes with environment-based defaults.

Provides configuration data classes for different service types with
sensible defaults and environment variable overrides.
"""

import os
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum


class Environment(Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class ServiceType(Enum):
    """Service type classifications."""
    ADMIN_API = "admin_api"
    TENANT_API = "tenant_api"
    DEPLOYMENT_API = "deployment_api"
    MARKETING_API = "marketing_api"
    CUSTOM = "custom"


@dataclass
class CORSConfig:
    """CORS configuration with environment-based defaults."""
    
    allow_origins: List[str] = field(default_factory=lambda: [
        "http://localhost:3000",  # Marketing frontend
        "http://localhost:3001",  # Admin dashboard
        "http://localhost:3002",  # Tenant admin
        "http://localhost:3003",  # Tenant frontend
    ])
    allow_methods: List[str] = field(default_factory=lambda: [
        "GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"
    ])
    allow_headers: List[str] = field(default_factory=lambda: [
        "*"
    ])
    allow_credentials: bool = True
    allow_origin_regex: Optional[str] = None
    expose_headers: List[str] = field(default_factory=list)
    max_age: int = 600
    
    @classmethod
    def from_environment(cls, env: Environment) -> 'CORSConfig':
        """Create CORS config based on environment."""
        if env == Environment.PRODUCTION:
            return cls(
                allow_origins=[
                    os.getenv("ADMIN_FRONTEND_URL", "https://admin.yourdomain.com"),
                    os.getenv("TENANT_FRONTEND_URL", "https://app.yourdomain.com"),
                    os.getenv("MARKETING_URL", "https://yourdomain.com"),
                ],
                allow_origin_regex=os.getenv("CORS_ORIGIN_REGEX"),
                max_age=3600
            )
        elif env == Environment.STAGING:
            return cls(
                allow_origins=[
                    "https://admin-staging.yourdomain.com",
                    "https://app-staging.yourdomain.com",
                    "https://staging.yourdomain.com",
                ],
                max_age=1800
            )
        else:
            return cls()  # Development defaults


@dataclass
class SecurityConfig:
    """Security configuration for FastAPI applications."""
    
    enable_security_headers: bool = True
    enable_https_redirect: bool = False
    enable_rate_limiting: bool = True
    rate_limit: str = "1000/minute"
    burst_rate_limit: str = "50/second"
    rate_limit_by: str = "ip"  # ip, user, tenant
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    blocked_user_agents: List[str] = field(default_factory=list)
    blocked_ips: List[str] = field(default_factory=list)
    trusted_proxies: List[str] = field(default_factory=list)
    
    @classmethod
    def from_environment(cls, env: Environment, service_type: ServiceType) -> 'SecurityConfig':
        """Create security config based on environment and service type."""
        if env == Environment.PRODUCTION:
            config = cls(
                enable_https_redirect=True,
                rate_limit=os.getenv("RATE_LIMIT", "2000/minute"),
                burst_rate_limit=os.getenv("BURST_RATE_LIMIT", "100/second"),
                max_request_size=int(os.getenv("MAX_REQUEST_SIZE", str(5 * 1024 * 1024))),
                trusted_proxies=os.getenv("TRUSTED_PROXIES", "").split(",") if os.getenv("TRUSTED_PROXIES") else []
            )
        elif env == Environment.STAGING:
            config = cls(
                rate_limit="1500/minute",
                burst_rate_limit="75/second"
            )
        else:
            config = cls(
                enable_https_redirect=False,
                rate_limit="5000/minute",  # More lenient for development
                burst_rate_limit="200/second"
            )
        
        # Service-specific adjustments
        if service_type == ServiceType.ADMIN_API:
            config.rate_limit_by = "user"
        elif service_type == ServiceType.TENANT_API:
            config.rate_limit_by = "tenant"
        elif service_type == ServiceType.DEPLOYMENT_API:
            config.rate_limit = "100/minute"  # More restrictive for admin operations
        
        return config


@dataclass
class DocsConfig:
    """OpenAPI documentation configuration with Scalar as default."""
    
    title: str = "Neo Multi-Tenant API"
    description: str = "Enterprise multi-tenant platform API"
    version: str = "1.0.0"
    docs_url: Optional[str] = "/docs"  # Scalar docs
    redoc_url: Optional[str] = "/redoc"
    swagger_url: Optional[str] = "/swagger"  # Traditional Swagger UI
    openapi_url: Optional[str] = "/openapi.json"
    include_in_schema: bool = True
    
    # Scalar-specific configuration
    use_scalar: bool = True
    scalar_config: Dict[str, Any] = field(default_factory=lambda: {
        "layout": "modern",  # Layout.MODERN or Layout.CLASSIC
        "show_sidebar": True,
        "hide_download_button": False,
        "hide_models": False,
        "dark_mode": True,
        "search_hot_key": "k",  # SearchHotKey.K
        "servers": [],
        "default_open_all_tags": False,
        "authentication": {
            "bearerToken": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            }
        },
        "hide_client_button": False,
        "scalar_theme": "",  # Custom CSS theme
        "scalar_favicon_url": "https://fastapi.tiangolo.com/img/favicon.png"
    })
    
    # Swagger UI configuration (fallback)
    swagger_ui_oauth2_redirect_url: Optional[str] = None
    swagger_ui_parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Contact and license info
    contact: Optional[Dict[str, str]] = None
    license_info: Optional[Dict[str, str]] = None
    
    # Server information
    servers: List[Dict[str, str]] = field(default_factory=list)
    
    @classmethod
    def from_environment(cls, env: Environment, service_type: ServiceType) -> 'DocsConfig':
        """Create docs config based on environment and service type."""
        
        # Service-specific titles and descriptions
        service_configs = {
            ServiceType.ADMIN_API: {
                "title": "Neo Admin API",
                "description": "Platform administration and management API"
            },
            ServiceType.TENANT_API: {
                "title": "Neo Tenant API", 
                "description": "Multi-tenant application API"
            },
            ServiceType.DEPLOYMENT_API: {
                "title": "Neo Deployment API",
                "description": "Database migration and deployment management API"
            }
        }
        
        service_config = service_configs.get(service_type, {})
        
        config = cls(
            title=service_config.get("title", cls.title),
            description=service_config.get("description", cls.description),
            version=os.getenv("API_VERSION", "1.0.0")
        )
        
        # Environment-specific adjustments
        if env == Environment.PRODUCTION:
            # Disable docs in production for security
            config.docs_url = None
            config.redoc_url = None
            config.swagger_url = None
            config.openapi_url = None
            config.include_in_schema = False
            config.use_scalar = False
        elif env == Environment.STAGING:
            # Limited docs in staging with Scalar configuration
            config.swagger_ui_parameters = {"defaultModelsExpandDepth": -1}
            config.scalar_config.update({
                "dark_mode": False,  # Light mode for staging
                "hide_download_button": True,
                "hide_models": True,
                "scalar_theme": "/* Staging environment styling */"
            })
        else:
            # Development environment - full featured Scalar
            config.scalar_config.update({
                "layout": "modern",
                "show_sidebar": True,
                "hide_download_button": False,
                "hide_models": False,
                "dark_mode": True,
                "default_open_all_tags": False
            })
        
        # Add contact and license info
        config.contact = {
            "name": "Neo Platform Team",
            "email": os.getenv("CONTACT_EMAIL", "support@yourdomain.com")
        }
        
        config.license_info = {
            "name": "Proprietary",
            "url": "https://yourdomain.com/license"
        }
        
        return config


@dataclass
class FastAPIConfig:
    """Base FastAPI application configuration."""
    
    # Basic app settings
    title: str = "Neo Multi-Tenant API"
    description: str = "Enterprise multi-tenant platform"
    version: str = "1.0.0"
    debug: bool = False
    
    # Environment and service info
    environment: Environment = Environment.DEVELOPMENT
    service_type: ServiceType = ServiceType.CUSTOM
    
    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    workers: int = 1
    
    # Security and middleware
    cors_config: CORSConfig = field(default_factory=CORSConfig)
    security_config: SecurityConfig = field(default_factory=SecurityConfig)
    docs_config: DocsConfig = field(default_factory=DocsConfig)
    
    # Feature toggles
    enable_auth: bool = True
    enable_tenant_context: bool = True
    enable_logging: bool = True
    enable_performance_monitoring: bool = True
    enable_error_handling: bool = True
    
    # Database and cache
    database_url: Optional[str] = None
    redis_url: Optional[str] = None
    
    # JWT configuration
    jwt_secret: Optional[str] = None
    jwt_algorithm: str = "RS256"
    
    # Custom settings
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize configuration from environment variables."""
        # Load from environment
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.host = os.getenv("HOST", self.host)
        self.port = int(os.getenv("PORT", str(self.port)))
        self.workers = int(os.getenv("WORKERS", str(self.workers)))
        
        # Environment detection
        env_name = os.getenv("ENVIRONMENT", "development").lower()
        try:
            self.environment = Environment(env_name)
        except ValueError:
            self.environment = Environment.DEVELOPMENT
        
        # Database and cache URLs
        self.database_url = os.getenv("DATABASE_URL", self.database_url)
        self.redis_url = os.getenv("REDIS_URL", self.redis_url)
        
        # JWT configuration
        self.jwt_secret = os.getenv("JWT_SECRET", self.jwt_secret)
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", self.jwt_algorithm)
        
        # Update sub-configs based on environment and service type
        self.cors_config = CORSConfig.from_environment(self.environment)
        self.security_config = SecurityConfig.from_environment(self.environment, self.service_type)
        self.docs_config = DocsConfig.from_environment(self.environment, self.service_type)
        
        # Development-specific settings
        if self.environment == Environment.DEVELOPMENT:
            self.reload = True
            self.debug = True
        elif self.environment == Environment.PRODUCTION:
            self.debug = False
            self.reload = False
    
    @classmethod
    def from_environment(cls, service_type: ServiceType, **overrides) -> 'FastAPIConfig':
        """Create configuration from environment with service-specific defaults."""
        config = cls(service_type=service_type)
        
        # Apply any overrides
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return config


@dataclass
class AdminAPIConfig(FastAPIConfig):
    """Configuration for Neo Admin API."""
    
    service_type: ServiceType = ServiceType.ADMIN_API
    port: int = 8001
    title: str = "Neo Admin API"
    description: str = "Platform administration and management API"
    
    # Admin-specific settings
    enable_tenant_context: bool = False  # Admin operates at platform level
    enable_system_metrics: bool = True
    enable_audit_logging: bool = True
    
    def __post_init__(self):
        super().__post_init__()
        self.port = int(os.getenv("ADMIN_API_PORT", str(self.port)))


@dataclass
class TenantAPIConfig(FastAPIConfig):
    """Configuration for Neo Tenant API."""
    
    service_type: ServiceType = ServiceType.TENANT_API
    port: int = 8002
    title: str = "Neo Tenant API"
    description: str = "Multi-tenant application API"
    
    # Tenant-specific settings
    enable_tenant_context: bool = True  # Required for tenant operations
    tenant_header: str = "X-Tenant-ID"
    subdomain_extraction: bool = True
    
    def __post_init__(self):
        super().__post_init__()
        self.port = int(os.getenv("TENANT_API_PORT", str(self.port)))
        self.tenant_header = os.getenv("TENANT_HEADER", self.tenant_header)
        self.subdomain_extraction = os.getenv("SUBDOMAIN_EXTRACTION", "true").lower() == "true"


@dataclass
class DeploymentAPIConfig(FastAPIConfig):
    """Configuration for Neo Deployment API."""
    
    service_type: ServiceType = ServiceType.DEPLOYMENT_API
    port: int = 8000
    title: str = "Neo Deployment API"
    description: str = "Database migration and deployment management API"
    
    # Deployment-specific settings
    enable_auth: bool = False  # Typically internal service
    enable_tenant_context: bool = False
    enable_migration_endpoints: bool = True
    
    def __post_init__(self):
        super().__post_init__()
        self.port = int(os.getenv("DEPLOYMENT_API_PORT", str(self.port)))
        
        # Override rate limiting for deployment operations
        self.security_config.rate_limit = "50/minute"
        self.security_config.rate_limit_by = "ip"