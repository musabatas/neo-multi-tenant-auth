"""System API v1 router - combines all system sub-routers."""

from fastapi import APIRouter

from . import system, database, cache

# Create main v1 router
router = APIRouter()

# Include sub-routers with appropriate prefixes
router.include_router(system.router, tags=["System"])
router.include_router(database.router, prefix="/database", tags=["Database"])  
router.include_router(cache.router, prefix="/cache", tags=["Cache"])