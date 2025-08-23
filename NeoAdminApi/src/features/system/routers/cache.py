"""Cache management API endpoints."""

from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.post("/clear")
async def clear_cache(
    pattern: str = "*"
):
    """Clear cache by pattern.
    
    Requires platform administrator permissions.
    """
    try:
        # TODO: Use neo-commons cache service to clear cache
        cleared_keys = 0  # Placeholder
        
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