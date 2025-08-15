"""
Application entry point.

ENHANCED WITH NEO-COMMONS: Now using neo-commons structured logging and enhanced error handling.
Improved configuration management and better application lifecycle handling.
"""
import sys
import uvicorn
from loguru import logger

# NEO-COMMONS INTEGRATION: Enhanced configuration and utilities
from neo_commons.utils.datetime import utc_now
from neo_commons.config import BaseConfigProtocol

from src.common.config.settings import settings
from src.app import create_app

# Create the FastAPI application with enhanced error handling
try:
    app = create_app()
except Exception as e:
    logger.error(f"Failed to create application: {e}")
    sys.exit(1)


def main():
    """Run the application with enhanced logging and error handling."""
    
    # Enhanced startup logging with neo-commons datetime utilities
    startup_time = utc_now()
    
    logger.info(
        f"Starting {settings.app_name} v{settings.app_version}",
        extra={
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "environment": settings.environment,
            "host": settings.host,
            "port": settings.port,
            "startup_time": startup_time.isoformat(),
            "is_production": settings.is_production,
            "is_development": settings.is_development
        }
    )
    
    # Validate configuration
    if not _validate_config(settings):
        logger.error("Configuration validation failed")
        sys.exit(1)
    
    # Configure uvicorn with enhanced settings
    uvicorn_config = {
        "app": "src.main:app",
        "host": settings.host,
        "port": settings.port,
        "reload": settings.reload,
        "workers": 1 if settings.reload else settings.workers,
        "log_level": settings.log_level.lower(),
        "access_log": not settings.is_production,  # Disable access logs in production for performance
        "use_colors": not settings.is_production,  # Disable colors in production for log aggregation
        "loop": "uvloop" if not settings.reload else "auto",  # Use uvloop for better performance
    }
    
    # Additional production optimizations
    if settings.is_production:
        uvicorn_config.update({
            "access_log": False,
            "server_header": False,  # Disable server header for security
            "date_header": False,    # Disable date header for performance
        })
    
    try:
        logger.info("Starting uvicorn server", extra=uvicorn_config)
        uvicorn.run(**uvicorn_config)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down gracefully")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


def _validate_config(config: BaseConfigProtocol) -> bool:
    """
    Validate critical configuration settings.
    
    Args:
        config: Configuration object implementing BaseConfigProtocol
        
    Returns:
        bool: True if configuration is valid, False otherwise
    """
    try:
        # Check required settings
        if not config.app_name:
            logger.error("APP_NAME is required")
            return False
            
        if not config.database_url:
            logger.error("DATABASE_URL is required")
            return False
            
        # Validate port range
        if not (1 <= config.port <= 65535):
            logger.error(f"Invalid port number: {config.port}")
            return False
            
        # Validate environment
        if config.environment not in ("development", "staging", "production", "testing"):
            logger.warning(f"Unknown environment: {config.environment}")
            
        # Validate workers in production
        if config.is_production and config.workers < 1:
            logger.error("At least 1 worker required in production")
            return False
            
        # Log configuration validation success
        logger.info(
            "Configuration validation passed",
            extra={
                "app_name": config.app_name,
                "environment": config.environment,
                "port": config.port,
                "workers": config.workers,
                "reload": config.reload
            }
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Configuration validation error: {e}")
        return False


if __name__ == "__main__":
    main()