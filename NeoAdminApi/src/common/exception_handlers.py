"""
Application exception handlers.

Service wrapper that extends neo-commons exception handlers with
NeoAdminApi-specific response formatting and error handling.
"""
from typing import Dict, Any, Optional, List
from fastapi import FastAPI

from neo_commons.api.exception_handlers import register_exception_handlers as base_register_handlers
from src.common.config.settings import settings
from src.common.models.base import APIResponse


def _api_response_formatter(
    message: str, 
    errors: Optional[List[Dict[str, Any]]] = None, 
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Custom response formatter using APIResponse model."""
    response = APIResponse.error_response(message=message, errors=errors or [])
    return response.model_dump()


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register exception handlers for the NeoAdminApi application.
    
    This function uses neo-commons exception handlers with a custom response
    formatter that maintains backward compatibility with APIResponse.
    
    Args:
        app: FastAPI application instance
    """
    base_register_handlers(
        app=app,
        response_formatter=_api_response_formatter,
        is_production=settings.is_production
    )