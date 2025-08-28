"""
Archive event request model.

ONLY handles event archival API request validation and transformation.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator

from neo_commons.platform.events.core.value_objects.event_id import EventId
from neo_commons.core.value_objects import TenantId


class ArchiveEventRequest(BaseModel):
    """Request model for archiving events."""
    
    event_id: str = Field(
        ...,
        description="ID of the event to archive",
        example="evt_123456789"
    )
    
    tenant_id: str = Field(
        ...,
        description="Tenant identifier",
        example="tenant_123"
    )
    
    reason: Optional[str] = Field(
        None,
        description="Reason for archiving the event",
        example="Event processing completed successfully"
    )
    
    archive_at: Optional[datetime] = Field(
        None,
        description="When to archive the event (if scheduled)"
    )
    
    force_archive: bool = Field(
        default=False,
        description="Force archive even if event has pending actions"
    )
    
    @validator('event_id')
    def validate_event_id(cls, v):
        """Validate event ID format."""
        if not v.strip():
            raise ValueError("Event ID cannot be empty")
        return v.strip()
    
    @validator('reason')
    def validate_reason(cls, v):
        """Validate archive reason if provided."""
        if v and not v.strip():
            raise ValueError("Archive reason cannot be empty if provided")
        return v.strip() if v else None
    
    @validator('archive_at')
    def validate_archive_at(cls, v):
        """Validate archive timestamp if provided."""
        if v and v <= datetime.utcnow():
            raise ValueError("Archive timestamp must be in the future")
        return v
    
    def to_domain(self) -> Dict[str, Any]:
        """Convert to domain representation."""
        return {
            "event_id": EventId(self.event_id),
            "tenant_id": TenantId(self.tenant_id),
            "reason": self.reason,
            "archive_at": self.archive_at,
            "force_archive": self.force_archive,
        }
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "event_id": "evt_123456789",
                "tenant_id": "tenant_123",
                "reason": "Event processing completed successfully",
                "archive_at": None,
                "force_archive": False
            }
        }