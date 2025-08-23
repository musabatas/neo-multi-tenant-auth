"""Neo Admin API main entry point."""

import logging
import sys
import os

import uvicorn

from .app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

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