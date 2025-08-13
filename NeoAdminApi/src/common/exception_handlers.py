"""
Application exception handlers.
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from loguru import logger

from src.common.config.settings import settings
from src.common.exceptions.base import NeoAdminException
from src.common.models.base import APIResponse


def register_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers for the application.
    
    Args:
        app: FastAPI application instance
    """
    @app.exception_handler(NeoAdminException)
    async def neo_admin_exception_handler(request: Request, exc: NeoAdminException):
        """Handle application-specific exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content=APIResponse.error_response(
                message=exc.message,
                errors=[exc.to_dict()]
            ).model_dump()
        )
    
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle value errors."""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=APIResponse.error_response(
                message=str(exc)
            ).model_dump()
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        
        if settings.is_production:
            message = "An unexpected error occurred"
        else:
            message = str(exc)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=APIResponse.error_response(
                message=message
            ).model_dump()
        )