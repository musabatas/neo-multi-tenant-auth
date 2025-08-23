"""Cache management API endpoints."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, status, Depends

from ....common.dependencies import get_cache_service

router = APIRouter()


@router.post("/clear")
async def clear_cache(
    pattern: str = "*",
    cache_service = Depends(get_cache_service)
):
    """Clear cache by pattern.
    
    Requires platform administrator permissions.
    
    Args:
        pattern: Redis key pattern to match (default: "*" clears all)
        cache_service: Injected cache service dependency
        
    Returns:
        Dict with pattern, cleared keys count, and success message
    """
    from typing import Annotated
    from fastapi import Depends
    from ....common.dependencies import get_cache_service
    
    try:
        # Clear cache keys matching the pattern
        cleared_keys = await cache_service.delete_pattern(pattern)
        
        return {
            "pattern": pattern,
            "cleared_keys": cleared_keys,
            "message": f"Cleared {cleared_keys} cache keys matching pattern '{pattern}'"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        ) from e