"""
Application entry point.
"""
import uvicorn
from loguru import logger

from src.common.config.settings import settings
from src.app import create_app

# Create the FastAPI application
app = create_app()


def main():
    """Run the application."""
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=1 if settings.reload else settings.workers,
        log_level=settings.log_level.lower(),
        access_log=True,
        use_colors=True
    )


if __name__ == "__main__":
    main()