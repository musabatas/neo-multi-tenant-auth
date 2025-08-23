"""Neo Admin API application using neo-commons FastAPI factory.

Properly configured FastAPI application with neo-commons infrastructure,
Scalar documentation, and comprehensive middleware stack.
"""

import logging
from fastapi import FastAPI

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create Neo Admin API using neo-commons FastAPI factory.
    
    Returns:
        Properly configured FastAPI application with neo-commons infrastructure
    """
    # Load environment variables from .env file
    import os
    from pathlib import Path
    
    # Load environment variables from .env files
    from dotenv import load_dotenv
    project_root = Path(__file__).parent.parent
    
    # Load .env first (default configuration)
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        logger.info(f"Loaded environment variables from {env_file}")
        # Debug: Check if ADMIN_DATABASE_URL was loaded
        admin_db_url = os.getenv("ADMIN_DATABASE_URL")
        if admin_db_url:
            logger.info(f"ADMIN_DATABASE_URL loaded: {admin_db_url[:50]}...")
        else:
            logger.error("ADMIN_DATABASE_URL not found in environment after loading .env")
    
    # Load .env.local second (local overrides)
    env_local_file = project_root / ".env.local"
    if env_local_file.exists():
        load_dotenv(env_local_file, override=True)
        logger.info(f"Loaded local environment overrides from {env_local_file}")
    
    if not env_file.exists() and not env_local_file.exists():
        logger.warning(f"No environment files found in {project_root}")
    
    from neo_commons.infrastructure.fastapi import (
        create_fastapi_factory,
        create_admin_api
    )
    from neo_commons.infrastructure.fastapi.config import ServiceType, Environment
    
    # Create factory (without services for now - add them as they're implemented)
    factory = create_fastapi_factory()
    
    # Configure for development environment using AdminAPIConfig defaults
    config_overrides = {
        "environment": Environment.DEVELOPMENT,
        "enable_auth": True,  # Enable auth - neo-commons provides complete auth infrastructure
        # enable_tenant_context is already False by default in AdminAPIConfig
        "cors_config": {
            "allow_origins": ["*"],
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"]
        }
    }
    
    # Create admin API using neo-commons factory with AdminAPIConfig defaults
    app = create_admin_api(factory, config_overrides)
    
    # Add feature routers
    from .features.auth.routers.v1 import router as auth_router
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
    
    from .features.organizations.routers.v1 import router as orgs_router  
    app.include_router(orgs_router, prefix="/api/v1/organizations", tags=["Organizations"])
    
    from .features.system.routers.v1 import router as system_router
    app.include_router(system_router, prefix="/api/v1/system")
    
    logger.info("Created Neo Admin API using neo-commons FastAPI factory")
    return app