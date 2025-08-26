"""Event archival entities and protocols for long-term scalability."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, List
from uuid import UUID

from neo_commons.core.value_objects import EventId


class ArchivalStatus(Enum):
    """Status of event archival process."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"
    RESTORED = "restored"


class ArchivalPolicy(Enum):
    """Archival policy strategies."""
    AGE_BASED = "age_based"           # Archive events older than X days
    SIZE_BASED = "size_based"         # Archive when table size exceeds threshold
    HYBRID = "hybrid"                 # Combination of age and size
    CUSTOM = "custom"                 # Custom archival rules


class StorageType(Enum):
    """Types of archival storage backends."""
    DATABASE_PARTITION = "database_partition"    # PostgreSQL partitioning
    COLD_STORAGE = "cold_storage"                # S3, GCS, Azure Blob
    COMPRESSED_ARCHIVE = "compressed_archive"     # Compressed database tables
    DATA_WAREHOUSE = "data_warehouse"            # Analytics warehouse


@dataclass(frozen=True)
class EventArchive:
    """Represents an archived batch of events."""
    
    id: UUID
    archive_name: str
    description: Optional[str]
    policy: ArchivalPolicy
    storage_type: StorageType
    storage_location: str
    created_at: datetime
    archived_at: Optional[datetime]
    restored_at: Optional[datetime]
    status: ArchivalStatus
    
    # Archival metadata
    event_count: int
    size_bytes: int
    compression_ratio: Optional[float]
    checksum: Optional[str]
    
    # Time range of archived events
    events_from: datetime
    events_to: datetime
    
    # Context information
    context_ids: List[UUID]
    event_types: List[str]
    
    # Archival configuration
    retention_days: Optional[int]
    auto_delete_after_days: Optional[int]
    
    # Metadata
    created_by_user_id: UUID
    tags: Dict[str, str]
    
    def __post_init__(self):
        """Validate archive data."""
        if self.event_count < 0:
            raise ValueError("Event count cannot be negative")
        
        if self.size_bytes < 0:
            raise ValueError("Size bytes cannot be negative")
        
        if self.compression_ratio is not None and (self.compression_ratio < 0 or self.compression_ratio > 1):
            raise ValueError("Compression ratio must be between 0 and 1")
        
        if self.events_from >= self.events_to:
            raise ValueError("Events 'from' date must be before 'to' date")
        
        if self.retention_days is not None and self.retention_days <= 0:
            raise ValueError("Retention days must be positive")
        
        if self.auto_delete_after_days is not None and self.auto_delete_after_days <= 0:
            raise ValueError("Auto delete days must be positive")
    
    def is_expired(self) -> bool:
        """Check if archive has exceeded its retention period."""
        if self.auto_delete_after_days is None:
            return False
        
        if self.archived_at is None:
            return False
        
        expiry_date = self.archived_at.replace(
            day=self.archived_at.day + self.auto_delete_after_days
        )
        
        return datetime.now(timezone.utc) > expiry_date
    
    def calculate_storage_efficiency(self) -> Dict[str, float]:
        """Calculate storage efficiency metrics."""
        if self.event_count == 0:
            return {
                "bytes_per_event": 0.0,
                "compression_efficiency": 0.0,
                "storage_density": 0.0
            }
        
        bytes_per_event = self.size_bytes / self.event_count
        compression_efficiency = self.compression_ratio or 0.0
        
        # Storage density: events per MB
        storage_density = self.event_count / (self.size_bytes / (1024 * 1024)) if self.size_bytes > 0 else 0.0
        
        return {
            "bytes_per_event": bytes_per_event,
            "compression_efficiency": compression_efficiency,
            "storage_density": storage_density
        }


@dataclass(frozen=True)
class ArchivalRule:
    """Defines rules for automatic event archival."""
    
    id: UUID
    name: str
    description: Optional[str]
    policy: ArchivalPolicy
    storage_type: StorageType
    is_enabled: bool
    
    # Age-based rules
    archive_after_days: Optional[int]
    
    # Size-based rules
    max_table_size_gb: Optional[float]
    max_event_count: Optional[int]
    
    # Filtering rules
    event_types_include: List[str]
    event_types_exclude: List[str]
    context_ids_include: List[UUID]
    context_ids_exclude: List[UUID]
    
    # Scheduling
    schedule_cron: Optional[str]
    next_run_at: Optional[datetime]
    last_run_at: Optional[datetime]
    
    # Storage configuration
    storage_location_template: str
    compression_enabled: bool
    encryption_enabled: bool
    
    # Retention
    retention_days: Optional[int]
    auto_delete_after_days: Optional[int]
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    created_by_user_id: UUID
    
    def __post_init__(self):
        """Validate archival rule configuration."""
        if self.archive_after_days is not None and self.archive_after_days <= 0:
            raise ValueError("Archive after days must be positive")
        
        if self.max_table_size_gb is not None and self.max_table_size_gb <= 0:
            raise ValueError("Max table size must be positive")
        
        if self.max_event_count is not None and self.max_event_count <= 0:
            raise ValueError("Max event count must be positive")
        
        if self.policy == ArchivalPolicy.AGE_BASED and self.archive_after_days is None:
            raise ValueError("Age-based policy requires archive_after_days")
        
        if self.policy == ArchivalPolicy.SIZE_BASED and (
            self.max_table_size_gb is None and self.max_event_count is None
        ):
            raise ValueError("Size-based policy requires max_table_size_gb or max_event_count")
        
        if self.retention_days is not None and self.retention_days <= 0:
            raise ValueError("Retention days must be positive")
        
        if self.auto_delete_after_days is not None and self.auto_delete_after_days <= 0:
            raise ValueError("Auto delete days must be positive")
    
    def should_archive_now(self, current_stats: Dict[str, Any]) -> bool:
        """Determine if archival should run based on current statistics."""
        if not self.is_enabled:
            return False
        
        # Check age-based criteria
        if self.policy in [ArchivalPolicy.AGE_BASED, ArchivalPolicy.HYBRID]:
            if self.archive_after_days is not None:
                oldest_event_age_days = current_stats.get("oldest_event_age_days", 0)
                if oldest_event_age_days >= self.archive_after_days:
                    return True
        
        # Check size-based criteria
        if self.policy in [ArchivalPolicy.SIZE_BASED, ArchivalPolicy.HYBRID]:
            if self.max_table_size_gb is not None:
                current_size_gb = current_stats.get("table_size_gb", 0)
                if current_size_gb >= self.max_table_size_gb:
                    return True
            
            if self.max_event_count is not None:
                current_count = current_stats.get("total_events", 0)
                if current_count >= self.max_event_count:
                    return True
        
        return False
    
    def get_archive_criteria(self) -> Dict[str, Any]:
        """Get archival criteria for event selection."""
        criteria = {
            "event_types_include": self.event_types_include,
            "event_types_exclude": self.event_types_exclude,
            "context_ids_include": self.context_ids_include,
            "context_ids_exclude": self.context_ids_exclude
        }
        
        if self.policy in [ArchivalPolicy.AGE_BASED, ArchivalPolicy.HYBRID]:
            if self.archive_after_days is not None:
                cutoff_date = datetime.now(timezone.utc).replace(
                    day=datetime.now(timezone.utc).day - self.archive_after_days
                )
                criteria["created_before"] = cutoff_date
        
        return criteria


@dataclass(frozen=True)
class ArchivalJob:
    """Represents an archival job execution."""
    
    id: UUID
    rule_id: UUID
    archive_id: Optional[UUID]
    status: ArchivalStatus
    
    # Job execution details
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    # Processing statistics
    events_processed: int
    events_archived: int
    events_skipped: int
    
    # Performance metrics
    processing_time_seconds: Optional[float]
    throughput_events_per_second: Optional[float]
    
    # Storage details
    storage_location: Optional[str]
    compressed_size_bytes: Optional[int]
    uncompressed_size_bytes: Optional[int]
    
    # Error handling
    error_message: Optional[str]
    retry_count: int
    max_retries: int
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    
    def __post_init__(self):
        """Validate job data."""
        if self.events_processed < 0:
            raise ValueError("Events processed cannot be negative")
        
        if self.events_archived < 0:
            raise ValueError("Events archived cannot be negative")
        
        if self.events_skipped < 0:
            raise ValueError("Events skipped cannot be negative")
        
        if self.retry_count < 0:
            raise ValueError("Retry count cannot be negative")
        
        if self.max_retries < 0:
            raise ValueError("Max retries cannot be negative")
        
        if self.retry_count > self.max_retries:
            raise ValueError("Retry count cannot exceed max retries")
    
    def calculate_success_rate(self) -> float:
        """Calculate archival success rate."""
        if self.events_processed == 0:
            return 0.0
        
        return (self.events_archived / self.events_processed) * 100.0
    
    def is_completed_successfully(self) -> bool:
        """Check if job completed successfully."""
        return (
            self.status == ArchivalStatus.COMPLETED and
            self.error_message is None and
            self.events_archived > 0
        )
    
    def should_retry(self) -> bool:
        """Check if job should be retried."""
        return (
            self.status == ArchivalStatus.FAILED and
            self.retry_count < self.max_retries
        )