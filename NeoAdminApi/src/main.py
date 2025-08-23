"""Neo Admin API main entry point."""

import logging
import sys
import os

import uvicorn
from neo_commons.config.logging_config import LoggingConfig

# Configure logging based on environment
LoggingConfig.configure()

from .app import create_app

logger = LoggingConfig.get_logger(__name__)

# Create the FastAPI application
app = create_app()


def main() -> None:
    """Run the application."""
    # Use AdminAPIConfig defaults - these match the neo-commons configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("ADMIN_API_PORT", "8001"))
    debug = os.getenv("DEBUG", "true").lower() == "true"
    
    logger.info(f"Starting Neo Admin API on {host}:{port}")
    
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=debug,  # Reload in debug mode
        log_level="info" if not debug else "debug",
        access_log=True,
    )


if __name__ == "__main__":
    main()