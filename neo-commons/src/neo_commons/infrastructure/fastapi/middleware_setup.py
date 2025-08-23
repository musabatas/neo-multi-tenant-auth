"""Middleware setup functions for different service configurations.

Provides service-specific middleware configuration based on service type,
environment, and feature requirements.
"""

from typing import Dict, Any
from fastapi import FastAPI

from .config import FastAPIConfig, Environment, ServiceType
from ..middleware import MiddlewareFactory


def setup_middleware_stack(
    app: FastAPI,
    config: FastAPIConfig,
    middleware_factory: MiddlewareFactory
) -> None:
    """Setup middleware stack based on service type and configuration."""
    
    if config.service_type == ServiceType.ADMIN_API:
        setup_admin_middleware(app, config, middleware_factory)
    elif config.service_type == ServiceType.TENANT_API:
        setup_tenant_middleware(app, config, middleware_factory)
    elif config.service_type == ServiceType.DEPLOYMENT_API:
        setup_deployment_middleware(app, config, middleware_factory)
    else:
        setup_default_middleware(app, config, middleware_factory)


def setup_admin_middleware(
    app: FastAPI,
    config: FastAPIConfig,
    middleware_factory: MiddlewareFactory
) -> None:
    """Setup middleware for Admin API."""
    
    # Admin API specific configuration
    middleware_config = {
        "enable_auth": config.enable_auth,
        "enable_tenant_context": False,  # Admin operates at platform level
        "enable_logging": config.enable_logging,
        "enable_security": True,
        "enable_performance": config.enable_performance_monitoring,
        "enable_error_handling": config.enable_error_handling,
        "cors_origins": config.cors_config.allow_origins,
        "rate_limit": config.security_config.rate_limit,
        "debug": config.debug
    }
    
    # Environment-specific adjustments
    if config.environment == Environment.PRODUCTION:
        middleware_config.update({
            "security_middleware": {
                "enable_security_headers": True,
                "enable_request_validation": True,
                "max_request_size": config.security_config.max_request_size,
                "blocked_user_agents": config.security_config.blocked_user_agents,
                "blocked_ips": config.security_config.blocked_ips
            },
            "rate_limit_middleware": {
                "burst_rate_limit": config.security_config.burst_rate_limit,
                "rate_limit_by": "user",  # Admin users
                "enable_burst_protection": True
            },
            "logging_middleware": {
                "log_requests": True,
                "log_responses": True,
                "log_request_body": False,  # Security: don't log admin request bodies
                "log_response_body": False
            }
        })
    
    middleware_factory.configure_full_stack(app, **middleware_config)


def setup_tenant_middleware(
    app: FastAPI,
    config: FastAPIConfig,
    middleware_factory: MiddlewareFactory
) -> None:
    """Setup middleware for Tenant API."""
    
    # Tenant API specific configuration
    middleware_config = {
        "enable_auth": config.enable_auth,
        "enable_tenant_context": True,  # Required for multi-tenancy
        "enable_logging": config.enable_logging,
        "enable_security": True,
        "enable_performance": config.enable_performance_monitoring,
        "enable_error_handling": config.enable_error_handling,
        "cors_origins": config.cors_config.allow_origins,
        "rate_limit": config.security_config.rate_limit,
        "debug": config.debug
    }
    
    # Tenant-specific middleware configuration
    tenant_middleware_config = {}
    if hasattr(config, 'tenant_header'):
        tenant_middleware_config["tenant_header"] = config.tenant_header
    if hasattr(config, 'subdomain_extraction'):
        tenant_middleware_config["subdomain_extraction"] = config.subdomain_extraction
    
    if tenant_middleware_config:
        middleware_config["tenant_middleware"] = tenant_middleware_config
    
    # Environment-specific adjustments
    if config.environment == Environment.PRODUCTION:
        middleware_config.update({
            "rate_limit_middleware": {
                "burst_rate_limit": config.security_config.burst_rate_limit,
                "rate_limit_by": "tenant",  # Tenant-based rate limiting
                "enable_burst_protection": True
            },
            "performance_middleware": {
                "enable_metrics": True,
                "slow_request_threshold": 0.5  # 500ms for tenant operations
            }
        })
    
    middleware_factory.configure_full_stack(app, **middleware_config)


def setup_deployment_middleware(
    app: FastAPI,
    config: FastAPIConfig,
    middleware_factory: MiddlewareFactory
) -> None:
    """Setup middleware for Deployment API."""
    
    # Deployment API typically has minimal middleware
    middleware_config = {
        "enable_auth": config.enable_auth,  # Usually False for internal service
        "enable_tenant_context": False,
        "enable_logging": True,  # Important for deployment operations
        "enable_security": True,
        "enable_performance": config.enable_performance_monitoring,
        "enable_error_handling": True,
        "cors_origins": config.cors_config.allow_origins,
        "rate_limit": config.security_config.rate_limit,  # More restrictive
        "debug": config.debug
    }
    
    # Deployment-specific security
    middleware_config.update({
        "security_middleware": {
            "enable_security_headers": True,
            "enable_request_validation": True,
            "max_request_size": 50 * 1024 * 1024,  # 50MB for large migration files
        },
        "rate_limit_middleware": {
            "rate_limit_by": "ip",
            "custom_limits": {
                "/api/v1/migrations": "10/minute",  # Very restrictive for migrations
                "/health": "100/minute"
            }
        },
        "logging_middleware": {
            "log_requests": True,
            "log_responses": True,
            "log_request_body": True,  # Log migration requests for audit
            "log_response_body": False
        }
    })
    
    middleware_factory.configure_full_stack(app, **middleware_config)


def setup_default_middleware(
    app: FastAPI,
    config: FastAPIConfig,
    middleware_factory: MiddlewareFactory
) -> None:
    """Setup default middleware for custom services."""
    
    middleware_config = {
        "enable_auth": config.enable_auth,
        "enable_tenant_context": config.enable_tenant_context,
        "enable_logging": config.enable_logging,
        "enable_security": True,
        "enable_performance": config.enable_performance_monitoring,
        "enable_error_handling": config.enable_error_handling,
        "cors_origins": config.cors_config.allow_origins,
        "rate_limit": config.security_config.rate_limit,
        "debug": config.debug
    }
    
    middleware_factory.configure_full_stack(app, **middleware_config)


def setup_minimal_middleware(
    app: FastAPI,
    config: FastAPIConfig,
    middleware_factory: MiddlewareFactory
) -> None:
    """Setup minimal middleware for development or testing."""
    
    middleware_config = {
        "cors_origins": config.cors_config.allow_origins,
        "debug": config.debug
    }
    
    middleware_factory.configure_minimal_stack(app, **middleware_config)


def setup_api_only_middleware(
    app: FastAPI,
    config: FastAPIConfig,
    middleware_factory: MiddlewareFactory,
    require_auth: bool = True
) -> None:
    """Setup API-only middleware stack."""
    
    middleware_config = {
        "require_auth": require_auth,
        "enable_tenant_context": config.enable_tenant_context,
        "rate_limit": config.security_config.rate_limit,
        "debug": config.debug
    }
    
    # API-specific rate limiting
    if config.environment == Environment.PRODUCTION:
        middleware_config["rate_limit_middleware"] = {
            "rate_limit_by": config.security_config.rate_limit_by,
            "burst_rate_limit": config.security_config.burst_rate_limit
        }
    
    middleware_factory.configure_api_only_stack(app, **middleware_config)