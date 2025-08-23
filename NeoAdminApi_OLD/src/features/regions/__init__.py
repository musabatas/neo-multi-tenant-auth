"""
Regions feature module for managing regional databases and connections.
"""

from .routers.database import router as database_router
from .routers.region import router as region_router

# Export the individual routers
__all__ = ["database_router", "region_router"]