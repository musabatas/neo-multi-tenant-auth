"""
Routers for regions feature.
"""
from .database import router as database_router
from .region import router as region_router

__all__ = ["database_router", "region_router"]