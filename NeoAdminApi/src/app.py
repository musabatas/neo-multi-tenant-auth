"""Neo Admin API application using neo-commons FastAPI factory.

Properly configured FastAPI application with neo-commons infrastructure,
Scalar documentation, and comprehensive middleware stack.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global _auth_factory
    
    # Load environment variables
    import os
    from pathlib import Path
    from dotenv import load_dotenv
    
    project_root = Path(__file__).parent.parent
    
    # Load .env first (default configuration)
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        logger.info(f"Loaded environment variables from {env_file}")
    
    # Load .env.local second (local overrides)
    env_local_file = project_root / ".env.local"
    if env_local_file.exists():
        load_dotenv(env_local_file, override=True)
        logger.info(f"Loaded local environment overrides from {env_local_file}")
    
    from neo_commons.config.manager import get_env_config
    from neo_commons.features.auth import AuthServiceFactory
    from .common.dependencies import get_database_service
    
    # Get database service first
    database_service = await get_database_service()
    
    # Get centralized configuration
    env_config = get_env_config()
    
    # Initialize auth factory with standard neo-commons configuration
    # Initialize neo-commons auth factory directly
    from neo_commons.features.auth import AuthServiceFactory
    _auth_factory = AuthServiceFactory(
        keycloak_server_url=env_config.keycloak_server_url,
        keycloak_admin_username=env_config.keycloak_admin or "admin",
        keycloak_admin_password=env_config.keycloak_password or "admin",
        redis_url=env_config.redis_url,
        redis_password=env_config.redis_password,
        database_service=database_service,
    )
    
    # Initialize all auth services
    await _auth_factory.initialize_all_services()
    
    # Register platform admin realm configuration for neo-commons
    realm_manager = await _auth_factory.get_realm_manager()
    from neo_commons.core.value_objects.identifiers import RealmId
    from neo_commons.features.auth.entities.keycloak_config import KeycloakConfig
    
    platform_realm_id = RealmId(env_config.keycloak_realm)
    platform_config = KeycloakConfig(
        server_url=env_config.keycloak_server_url,
        realm_name=env_config.keycloak_realm,
        client_id=env_config.keycloak_client_id,
        client_secret=env_config.keycloak_client_secret,
        audience=env_config.keycloak_client_id,  # Set audience to match client_id
        verify_audience=False,  # Disable audience verification for platform admin
        require_https=False,  # Allow HTTP in development
    )
    
    realm_manager.register_platform_realm_config(platform_realm_id, platform_config)
    logger.info(f"Registered platform admin realm config: {platform_realm_id.value}")
    
    # Initialize global neo-commons auth dependencies
    from neo_commons.features.auth.dependencies import init_auth_dependencies
    auth_dependencies = await _auth_factory.get_auth_dependencies()
    init_auth_dependencies(
        auth_service=auth_dependencies.auth_service,
        jwt_validator=auth_dependencies.jwt_validator,
        token_service=auth_dependencies.token_service,
        user_mapper=auth_dependencies.user_mapper,
        realm_manager=auth_dependencies.realm_manager,
    )
    
    logger.info("Auth factory initialized for admin context")
    
    yield
    
    # Cleanup
    if _auth_factory:
        await _auth_factory.cleanup()


def create_app() -> FastAPI:
    """Create Neo Admin API with proper auth dependencies.
    
    Returns:
        Properly configured FastAPI application with neo-commons auth infrastructure
    """
    # Use neo-commons FastAPI factory with Scalar documentation
    from neo_commons.infrastructure.fastapi.factory import create_admin_api, create_fastapi_factory
    
    # Create factory without services initially (lifespan will handle initialization)
    factory = create_fastapi_factory()
    
    # Create admin API with neo-commons factory (includes Scalar docs)
    app = create_admin_api(
        factory,
        lifespan=lifespan,
        config_overrides={
            "title": "Neo Admin API",
            "version": "1.0.0", 
            "description": "Enterprise admin API with comprehensive authentication and RBAC",
        }
    )
    
    # Include admin-specific auth router (no overrides needed)
    from .features.auth.routers.admin_auth_router import router as admin_auth_router
    app.include_router(admin_auth_router, prefix="/api/v1")
    
    from .features.organizations.routers.v1 import router as orgs_router  
    app.include_router(orgs_router, prefix="/api/v1/organizations", tags=["Organizations"])
    
    from .features.system.routers.v1 import router as system_router
    app.include_router(system_router, prefix="/api/v1/system")
    
    # Add debug endpoint to check auth factory status
    @app.get("/debug/auth-status")
    async def debug_auth_status():
        try:
            from neo_commons.features.auth.dependencies import get_auth_dependencies
            auth_deps = get_auth_dependencies()
            
            return {
                "neo_commons_auth_initialized": auth_deps is not None,
                "auth_dependencies_type": type(auth_deps).__name__ if auth_deps else None,
                "services_available": {
                    "auth_service": hasattr(auth_deps, 'auth_service') and auth_deps.auth_service is not None,
                    "jwt_validator": hasattr(auth_deps, 'jwt_validator') and auth_deps.jwt_validator is not None,
                    "token_service": hasattr(auth_deps, 'token_service') and auth_deps.token_service is not None,
                    "user_mapper": hasattr(auth_deps, 'user_mapper') and auth_deps.user_mapper is not None,
                    "realm_manager": hasattr(auth_deps, 'realm_manager') and auth_deps.realm_manager is not None,
                } if auth_deps else {}
            }
        except Exception as e:
            return {
                "neo_commons_auth_initialized": False,
                "error": str(e)
            }
    
    logger.info("Created Neo Admin API with proper auth dependencies")
    return app