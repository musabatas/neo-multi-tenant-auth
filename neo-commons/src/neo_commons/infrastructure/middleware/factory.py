"""Middleware factory for easy FastAPI application configuration.

Provides convenience functions to configure all middleware components
with sensible defaults and proper ordering for optimal security and performance.
"""

from typing import Optional, List, Dict, Any, Callable
from fastapi import FastAPI

# from .auth_middleware import AuthenticationMiddleware, OptionalAuthenticationMiddleware  # TODO: Enable when UserService is implemented
# from .tenant_middleware import TenantContextMiddleware, MultiTenantDatabaseMiddleware  # TODO: Enable when TenantService is implemented
from .logging_middleware import StructuredLoggingMiddleware
from .security_middleware import SecurityMiddleware, CORSMiddleware, RateLimitMiddleware
from .performance_middleware import PerformanceMiddleware, TimingMiddleware, DatabasePerformanceMiddleware
from .error_middleware import ErrorHandlingMiddleware

# from ...features.users.services import UserService  # TODO: Enable when UserService is implemented
from ...features.cache.services import CacheService
# from ...features.tenants.services import TenantService  # TODO: Enable when TenantService is implemented
from ...features.database.services import DatabaseService


class MiddlewareFactory:
    """Factory for configuring FastAPI middleware stack."""
    
    def __init__(
        self,
        cache_service: CacheService,
        database_service: DatabaseService,
        jwt_secret: str,
        jwt_algorithm: str = "RS256",
        user_service=None,  # Optional until UserService is implemented
        tenant_service=None  # Optional until TenantService is implemented
    ):
        self.user_service = user_service
        self.cache_service = cache_service
        self.tenant_service = tenant_service
        self.database_service = database_service
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
    
    def configure_full_stack(
        self,
        app: FastAPI,
        enable_auth: bool = True,
        enable_tenant_context: bool = True,
        enable_logging: bool = True,
        enable_security: bool = True,
        enable_performance: bool = True,
        enable_error_handling: bool = True,
        cors_origins: Optional[List[str]] = None,
        rate_limit: str = "100/minute",
        **kwargs
    ) -> FastAPI:
        """Configure complete middleware stack with optimal ordering.
        
        Middleware order (outer to inner):
        1. Error Handling (outermost - catches all exceptions)
        2. Security (CORS, security headers)
        3. Logging (request/response logging)
        4. Performance (timing, metrics)
        5. Rate Limiting (throttling)
        6. Authentication (JWT validation, user mapping)
        7. Tenant Context (tenant resolution, schema setup)
        8. Database Context (innermost - ensures proper schema)
        """
        
        # 8. Database Context (innermost) - TODO: Enable when MultiTenantDatabaseMiddleware is implemented
        # if enable_tenant_context and self.tenant_service:
        #     app.add_middleware(
        #         MultiTenantDatabaseMiddleware,
        #         database_service=self.database_service
        #     )
        
        # 7. Tenant Context - TODO: Enable when TenantContextMiddleware is implemented
        # if enable_tenant_context and self.tenant_service:
        #     app.add_middleware(
        #         TenantContextMiddleware,
        #         tenant_service=self.tenant_service,
        #         cache_service=self.cache_service,
        #         database_service=self.database_service,
        #         **kwargs.get('tenant_middleware', {})
        #     )
        
        # 6. Authentication - TODO: Enable when AuthenticationMiddleware is implemented
        # if enable_auth and self.user_service:
        #     auth_middleware_class = kwargs.get('auth_middleware_class', AuthenticationMiddleware)
        #     app.add_middleware(
        #         auth_middleware_class,
        #         user_service=self.user_service,
        #         cache_service=self.cache_service,
        #         jwt_secret=self.jwt_secret,
        #         jwt_algorithm=self.jwt_algorithm,
        #         **kwargs.get('auth_middleware', {})
        #     )
        
        # 5. Rate Limiting
        if enable_security and rate_limit:
            app.add_middleware(
                RateLimitMiddleware,
                cache_service=self.cache_service,
                default_rate_limit=rate_limit,
                **kwargs.get('rate_limit_middleware', {})
            )
        
        # 4. Performance Monitoring
        if enable_performance:
            app.add_middleware(
                PerformanceMiddleware,
                cache_service=self.cache_service,
                **kwargs.get('performance_middleware', {})
            )
        
        # 3. Structured Logging
        if enable_logging:
            app.add_middleware(
                StructuredLoggingMiddleware,
                **kwargs.get('logging_middleware', {})
            )
        
        # 2. Security Headers and General Security
        if enable_security:
            app.add_middleware(
                SecurityMiddleware,
                **kwargs.get('security_middleware', {})
            )
        
        # CORS (if origins specified)
        if cors_origins:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=cors_origins,
                allow_credentials=True,
                **kwargs.get('cors_middleware', {})
            )
        
        # 1. Error Handling (outermost)
        if enable_error_handling:
            app.add_middleware(
                ErrorHandlingMiddleware,
                debug=kwargs.get('debug', False),
                **kwargs.get('error_middleware', {})
            )
        
        return app
    
    def configure_minimal_stack(
        self,
        app: FastAPI,
        cors_origins: Optional[List[str]] = None,
        **kwargs
    ) -> FastAPI:
        """Configure minimal middleware stack for development or lightweight applications."""
        
        # Basic timing
        app.add_middleware(TimingMiddleware)
        
        # CORS if needed
        if cors_origins:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=cors_origins,
                allow_credentials=True
            )
        
        # Basic error handling
        app.add_middleware(
            ErrorHandlingMiddleware,
            debug=kwargs.get('debug', True),
            include_trace=kwargs.get('debug', True)
        )
        
        return app
    
    def configure_production_stack(
        self,
        app: FastAPI,
        cors_origins: List[str],
        rate_limit: str = "1000/minute",
        burst_limit: str = "50/second",
        **kwargs
    ) -> FastAPI:
        """Configure production-ready middleware stack with enhanced security."""
        
        return self.configure_full_stack(
            app=app,
            cors_origins=cors_origins,
            rate_limit=rate_limit,
            debug=False,
            # Enhanced security settings
            security_middleware={
                'enable_security_headers': True,
                'enable_request_validation': True,
                'max_request_size': 5 * 1024 * 1024,  # 5MB limit
                **kwargs.get('security_middleware', {})
            },
            # Enhanced rate limiting
            rate_limit_middleware={
                'burst_rate_limit': burst_limit,
                'enable_burst_protection': True,
                **kwargs.get('rate_limit_middleware', {})
            },
            # Production logging
            logging_middleware={
                'log_requests': True,
                'log_responses': True,
                'log_request_body': False,  # Security: don't log request bodies
                'log_response_body': False,  # Security: don't log response bodies
                **kwargs.get('logging_middleware', {})
            },
            # Performance monitoring
            performance_middleware={
                'enable_metrics': True,
                'slow_request_threshold': 0.5,  # 500ms
                **kwargs.get('performance_middleware', {})
            },
            **kwargs
        )
    
    def configure_api_only_stack(
        self,
        app: FastAPI,
        require_auth: bool = True,
        **kwargs
    ) -> FastAPI:
        """Configure middleware stack for API-only applications."""
        
        # Database context (if tenant support needed) - TODO: Enable when middleware is implemented
        # if kwargs.get('enable_tenant_context', False) and self.tenant_service:
        #     app.add_middleware(
        #         MultiTenantDatabaseMiddleware,
        #         database_service=self.database_service
        #     )
        #     
        #     app.add_middleware(
        #         TenantContextMiddleware,
        #         tenant_service=self.tenant_service,
        #         cache_service=self.cache_service,
        #         database_service=self.database_service,
        #         **kwargs.get('tenant_middleware', {})
        #     )
        
        # Authentication (required for APIs) - TODO: Enable when AuthenticationMiddleware is implemented
        # if require_auth and self.user_service:
        #     app.add_middleware(
        #         AuthenticationMiddleware,
        #         user_service=self.user_service,
        #         cache_service=self.cache_service,
        #         jwt_secret=self.jwt_secret,
        #         jwt_algorithm=self.jwt_algorithm,
        #         **kwargs.get('auth_middleware', {})
        #     )
        
        # Rate limiting for API protection
        app.add_middleware(
            RateLimitMiddleware,
            cache_service=self.cache_service,
            default_rate_limit=kwargs.get('rate_limit', '200/minute'),
            **kwargs.get('rate_limit_middleware', {})
        )
        
        # Performance monitoring
        app.add_middleware(
            PerformanceMiddleware,
            cache_service=self.cache_service,
            **kwargs.get('performance_middleware', {})
        )
        
        # Structured logging for APIs
        app.add_middleware(
            StructuredLoggingMiddleware,
            log_requests=True,
            log_responses=True,
            **kwargs.get('logging_middleware', {})
        )
        
        # Security headers
        app.add_middleware(
            SecurityMiddleware,
            **kwargs.get('security_middleware', {})
        )
        
        # Error handling
        app.add_middleware(
            ErrorHandlingMiddleware,
            debug=kwargs.get('debug', False),
            **kwargs.get('error_middleware', {})
        )
        
        return app


def create_middleware_factory(
    cache_service: CacheService,
    database_service: DatabaseService,
    jwt_secret: str,
    jwt_algorithm: str = "RS256",
    user_service=None,  # Optional until UserService is implemented
    tenant_service=None  # Optional until TenantService is implemented
) -> MiddlewareFactory:
    """Create a middleware factory with required services."""
    return MiddlewareFactory(
        cache_service=cache_service,
        database_service=database_service,
        jwt_secret=jwt_secret,
        jwt_algorithm=jwt_algorithm,
        user_service=user_service,
        tenant_service=tenant_service
    )


# Convenience functions for common configurations

def configure_development_app(
    app: FastAPI,
    middleware_factory: MiddlewareFactory,
    cors_origins: Optional[List[str]] = None
) -> FastAPI:
    """Configure FastAPI app for development with minimal security."""
    if cors_origins is None:
        cors_origins = ["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"]
    
    return middleware_factory.configure_minimal_stack(
        app=app,
        cors_origins=cors_origins,
        debug=True
    )


def configure_production_app(
    app: FastAPI,
    middleware_factory: MiddlewareFactory,
    cors_origins: List[str],
    rate_limit: str = "1000/minute"
) -> FastAPI:
    """Configure FastAPI app for production with full security."""
    return middleware_factory.configure_production_stack(
        app=app,
        cors_origins=cors_origins,
        rate_limit=rate_limit
    )


def configure_api_app(
    app: FastAPI,
    middleware_factory: MiddlewareFactory,
    require_auth: bool = True,
    enable_tenant_context: bool = True
) -> FastAPI:
    """Configure FastAPI app for API-only usage."""
    return middleware_factory.configure_api_only_stack(
        app=app,
        require_auth=require_auth,
        enable_tenant_context=enable_tenant_context
    )