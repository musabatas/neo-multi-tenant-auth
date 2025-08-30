"""Action list response model."""

from typing import List, Optional
from pydantic import BaseModel, Field

from .action_response import ActionResponse


class ActionListResponse(BaseModel):
    """Response model for paginated action lists."""
    
    actions: List[ActionResponse] = Field(..., description="List of actions")
    total_count: int = Field(..., description="Total number of actions")
    limit: int = Field(..., description="Items per page")
    offset: int = Field(..., description="Offset from start")
    has_more: bool = Field(..., description="Whether there are more items")
    
    @classmethod
    def from_domain_list(
        cls, 
        actions: List, 
        total_count: int, 
        limit: int, 
        offset: int
    ) -> "ActionListResponse":
        """Create response from domain action list."""
        return cls(
            actions=[ActionResponse.from_domain(action) for action in actions],
            total_count=total_count,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total_count
        )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True