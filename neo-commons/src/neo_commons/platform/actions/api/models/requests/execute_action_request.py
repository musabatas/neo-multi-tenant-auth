"""Execute action request model."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from uuid import UUID


class ExecuteActionRequest(BaseModel):
    """Request model for manually executing an action."""
    
    action_id: UUID = Field(..., description="ID of action to execute")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input data for execution")
    context_data: Optional[Dict[str, Any]] = Field(None, description="Additional context data")
    priority: Optional[int] = Field(None, ge=0, le=1000, description="Execution priority override")
    timeout_seconds: Optional[int] = Field(None, ge=1, le=3600, description="Timeout override")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True