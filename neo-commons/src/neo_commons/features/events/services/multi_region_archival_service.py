"""
Multi-Region Event Archival Service

Provides intelligent multi-region archival strategies with automated replication,
geo-distributed storage, cross-region disaster recovery, and compliance-aware
data placement for global webhook event archival systems.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4

from ..entities.domain_event import DomainEvent
from ..entities.event_archive import EventArchive, StorageType, ArchivalStatus
from .archival_compression_service import ArchivalCompressionService, CompressionProfile
from .event_archival_service import EventArchivalService

logger = logging.getLogger(__name__)


class RegionTier(Enum):
    """Geographic region tiers for archival strategy."""
    PRIMARY = "primary"         # Main production region
    SECONDARY = "secondary"     # Backup/DR region
    COMPLIANCE = "compliance"   # Compliance-required region
    EDGE = "edge"              # Edge/CDN region
    COLD = "cold"              # Cold storage region


class ReplicationStrategy(Enum):
    """Archival replication strategies for multi-region deployment."""
    NONE = "none"                           # Single region only
    SYNC_REPLICATION = "sync_replication"   # Synchronous replication
    ASYNC_REPLICATION = "async_replication" # Asynchronous replication
    EVENTUAL_CONSISTENCY = "eventual"       # Eventually consistent
    COMPLIANCE_COPY = "compliance_copy"     # Compliance-driven copies
    DISASTER_RECOVERY = "disaster_recovery" # DR-focused replication


@dataclass
class RegionConfig:
    """Configuration for a single archival region."""
    region_id: str
    region_name: str
    tier: RegionTier
    storage_types: List[StorageType]
    
    # Geographic and compliance settings
    country_code: str
    data_residency_compliant: bool = True
    gdpr_compliant: bool = False
    
    # Storage configuration
    default_storage_type: StorageType = StorageType.COLD_STORAGE
    compression_profile: str = "balanced"
    retention_days_default: int = 2555  # 7 years
    
    # Performance settings
    max_concurrent_operations: int = 10
    operation_timeout_seconds: int = 3600  # 1 hour
    
    # Cost and priority
    storage_cost_tier: str = "standard"  # standard, ia, glacier
    priority: int = 1  # 1=highest, 10=lowest
    
    # Availability settings
    is_active: bool = True
    last_health_check: Optional[datetime] = None
    consecutive_failures: int = 0


@dataclass
class MultiRegionArchive:
    """Represents an archive distributed across multiple regions."""
    primary_archive: EventArchive
    replica_archives: Dict[str, EventArchive] = field(default_factory=dict)
    replication_strategy: ReplicationStrategy = ReplicationStrategy.ASYNC_REPLICATION
    
    # Consistency and synchronization
    consistency_state: str = "pending"  # pending, synced, diverged
    last_sync_check: Optional[datetime] = None
    sync_lag_seconds: Optional[float] = None
    
    # Multi-region metadata
    regions: List[str] = field(default_factory=list)
    total_replicas: int = 0
    successful_replicas: int = 0
    failed_replicas: int = 0
    
    # Compliance tracking
    compliance_regions: List[str] = field(default_factory=list)
    data_residency_satisfied: bool = True


class MultiRegionArchivalService:
    """Service for managing multi-region event archival operations."""
    
    def __init__(
        self,
        archival_service: EventArchivalService,
        compression_service: ArchivalCompressionService,
        region_configs: Dict[str, RegionConfig],
        default_replication_strategy: ReplicationStrategy = ReplicationStrategy.ASYNC_REPLICATION
    ):
        """Initialize multi-region archival service.
        
        Args:
            archival_service: Base event archival service
            compression_service: Compression service for optimized transfers
            region_configs: Configuration for each region
            default_replication_strategy: Default replication approach
        """
        self._archival_service = archival_service
        self._compression_service = compression_service
        self._region_configs = region_configs
        self._default_replication_strategy = default_replication_strategy
        
        # Multi-region tracking
        self._multi_region_archives: Dict[UUID, MultiRegionArchive] = {}
        self._region_health: Dict[str, Dict[str, Any]] = {}
        self._replication_queue: Dict[str, List[Dict[str, Any]]] = {}
        
        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        self._is_running = False
        
        # Performance metrics
        self._metrics = {
            "total_multi_region_archives": 0,
            "successful_replications": 0,
            "failed_replications": 0,
            "cross_region_bandwidth_gb": 0.0,
            "average_replication_time_seconds": 0.0,
            "compliance_archives_created": 0
        }
    
    async def start_multi_region_service(self) -> None:
        """Start multi-region archival background services."""
        if self._is_running:
            logger.warning("Multi-region archival service already running")
            return
        
        logger.info("Starting multi-region archival service")
        self._is_running = True
        
        # Start background monitoring tasks
        self._background_tasks = [
            asyncio.create_task(self._region_health_monitor()),
            asyncio.create_task(self._replication_processor()),
            asyncio.create_task(self._consistency_checker()),
            asyncio.create_task(self._compliance_monitor())
        ]
        
        # Initial region health check
        await self._check_all_regions_health()
        
        logger.info("Multi-region archival service started successfully")
    
    async def stop_multi_region_service(self) -> None:
        """Stop multi-region archival background services."""
        if not self._is_running:
            return
        
        logger.info("Stopping multi-region archival service")
        self._is_running = False
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        self._background_tasks = []
        logger.info("Multi-region archival service stopped")
    
    async def create_multi_region_archive(
        self,
        events: List[DomainEvent],
        archive_name: str,
        primary_region: str,
        replica_regions: List[str],
        replication_strategy: Optional[ReplicationStrategy] = None,
        compliance_requirements: List[str] = None,
        retention_days: Optional[int] = None
    ) -> MultiRegionArchive:
        """Create an archive distributed across multiple regions.
        
        Args:
            events: Domain events to archive
            archive_name: Name for the archive
            primary_region: Primary region for the archive
            replica_regions: Regions for replicas
            replication_strategy: Replication approach
            compliance_requirements: Compliance requirements (GDPR, etc.)
            retention_days: Retention period override
            
        Returns:
            Multi-region archive with all replicas
        """
        if not events:
            raise ValueError("Cannot create archive from empty event list")
        
        if primary_region not in self._region_configs:
            raise ValueError(f"Unknown primary region: {primary_region}")
        
        strategy = replication_strategy or self._default_replication_strategy
        
        logger.info(
            f"Creating multi-region archive '{archive_name}' with {len(events)} events "
            f"(primary: {primary_region}, replicas: {replica_regions}, strategy: {strategy.value})"
        )
        
        # Validate compliance requirements
        validated_regions = await self._validate_compliance_regions(
            [primary_region] + replica_regions, compliance_requirements or []
        )
        
        # Create primary archive
        primary_config = self._region_configs[primary_region]
        primary_archive = await self._create_regional_archive(
            events, archive_name, primary_region, primary_config, 
            is_primary=True, retention_days=retention_days
        )
        
        # Initialize multi-region archive
        multi_region_archive = MultiRegionArchive(
            primary_archive=primary_archive,
            replication_strategy=strategy,
            regions=[primary_region] + replica_regions,
            compliance_regions=validated_regions,
            data_residency_satisfied=len(validated_regions) >= len(compliance_requirements or [])
        )
        
        # Create replicas based on strategy
        if strategy == ReplicationStrategy.SYNC_REPLICATION:
            await self._create_sync_replicas(
                events, multi_region_archive, replica_regions, retention_days
            )
        else:
            # Queue for async replication
            await self._queue_async_replicas(
                events, multi_region_archive, replica_regions, retention_days
            )
        
        # Store multi-region archive
        self._multi_region_archives[primary_archive.id] = multi_region_archive
        self._metrics["total_multi_region_archives"] += 1
        
        if compliance_requirements:
            self._metrics["compliance_archives_created"] += 1
        
        logger.info(f"Multi-region archive created: {primary_archive.id}")
        return multi_region_archive
    
    async def restore_from_multi_region_archive(
        self,
        archive_id: UUID,
        target_region: Optional[str] = None,
        prefer_closest_replica: bool = True
    ) -> Tuple[List[DomainEvent], str]:
        """Restore events from multi-region archive.
        
        Args:
            archive_id: Archive identifier
            target_region: Preferred region for restore
            prefer_closest_replica: Use closest available replica
            
        Returns:
            Tuple of (restored_events, source_region)
        """
        if archive_id not in self._multi_region_archives:
            raise ValueError(f"Multi-region archive {archive_id} not found")
        
        multi_archive = self._multi_region_archives[archive_id]
        
        # Determine best source region for restore
        source_region = await self._select_restore_source_region(
            multi_archive, target_region, prefer_closest_replica
        )
        
        logger.info(f"Restoring archive {archive_id} from region {source_region}")
        
        # Get the appropriate archive (primary or replica)
        if source_region == multi_archive.primary_archive.storage_location:
            source_archive = multi_archive.primary_archive
        else:
            if source_region not in multi_archive.replica_archives:
                raise ValueError(f"Replica in region {source_region} not found")
            source_archive = multi_archive.replica_archives[source_region]
        
        # Restore events from selected region
        restored_events = await self._archival_service.restore_archived_events(
            str(source_archive.id)
        )
        
        return restored_events, source_region
    
    async def sync_multi_region_archive(self, archive_id: UUID) -> Dict[str, Any]:
        """Synchronize a multi-region archive across all regions.
        
        Args:
            archive_id: Archive to synchronize
            
        Returns:
            Synchronization results and status
        """
        if archive_id not in self._multi_region_archives:
            raise ValueError(f"Multi-region archive {archive_id} not found")
        
        multi_archive = self._multi_region_archives[archive_id]
        logger.info(f"Synchronizing multi-region archive {archive_id}")
        
        sync_results = {
            "archive_id": str(archive_id),
            "primary_region": multi_archive.primary_archive.storage_location,
            "sync_started": datetime.now(timezone.utc).isoformat(),
            "regions_synced": [],
            "regions_failed": [],
            "consistency_achieved": False
        }
        
        # Check primary archive status
        primary_status = await self._check_archive_consistency(
            multi_archive.primary_archive
        )
        
        if not primary_status["available"]:
            sync_results["error"] = "Primary archive not available for sync"
            return sync_results
        
        # Sync all replicas
        for region_id, replica_archive in multi_archive.replica_archives.items():
            try:
                replica_status = await self._check_archive_consistency(replica_archive)
                
                if replica_status["available"] and replica_status["checksum_match"]:
                    sync_results["regions_synced"].append(region_id)
                else:
                    # Re-replicate from primary
                    await self._re_replicate_archive(
                        multi_archive.primary_archive, replica_archive, region_id
                    )
                    sync_results["regions_synced"].append(region_id)
                    
            except Exception as e:
                logger.error(f"Failed to sync replica in region {region_id}: {e}")
                sync_results["regions_failed"].append(region_id)
        
        # Update consistency state
        if not sync_results["regions_failed"]:
            multi_archive.consistency_state = "synced"
            multi_archive.last_sync_check = datetime.now(timezone.utc)
            sync_results["consistency_achieved"] = True
        
        sync_results["sync_completed"] = datetime.now(timezone.utc).isoformat()
        return sync_results
    
    async def get_multi_region_statistics(self) -> Dict[str, Any]:
        """Get comprehensive multi-region archival statistics."""
        stats = self._metrics.copy()
        
        # Add region-specific statistics
        region_stats = {}
        for region_id, config in self._region_configs.items():
            region_health = self._region_health.get(region_id, {})
            region_stats[region_id] = {
                "config": config.__dict__,
                "health": region_health,
                "archives_hosted": sum(
                    1 for archive in self._multi_region_archives.values()
                    if region_id in archive.regions
                ),
                "primary_archives": sum(
                    1 for archive in self._multi_region_archives.values()
                    if archive.primary_archive.storage_location == region_id
                ),
                "replica_archives": sum(
                    1 for archive in self._multi_region_archives.values()
                    if region_id in archive.replica_archives
                )
            }
        
        # Add consistency statistics
        consistency_stats = {
            "total_multi_region_archives": len(self._multi_region_archives),
            "synced_archives": sum(
                1 for archive in self._multi_region_archives.values()
                if archive.consistency_state == "synced"
            ),
            "diverged_archives": sum(
                1 for archive in self._multi_region_archives.values()
                if archive.consistency_state == "diverged"
            ),
            "pending_archives": sum(
                1 for archive in self._multi_region_archives.values()
                if archive.consistency_state == "pending"
            )
        }
        
        return {
            "service_metrics": stats,
            "region_statistics": region_stats,
            "consistency_statistics": consistency_stats,
            "replication_queue_sizes": {
                region: len(queue) for region, queue in self._replication_queue.items()
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    # Background monitoring and processing methods
    
    async def _region_health_monitor(self) -> None:
        """Monitor health of all configured regions."""
        while self._is_running:
            try:
                await self._check_all_regions_health()
                await asyncio.sleep(300)  # Check every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in region health monitor: {e}")
                await asyncio.sleep(60)  # Wait before retry
    
    async def _replication_processor(self) -> None:
        """Process queued replication requests."""
        while self._is_running:
            try:
                for region_id in list(self._replication_queue.keys()):
                    queue = self._replication_queue.get(region_id, [])
                    
                    if queue:
                        # Process up to 5 replications per region per cycle
                        batch = queue[:5]
                        self._replication_queue[region_id] = queue[5:]
                        
                        for replication_task in batch:
                            await self._process_replication_task(replication_task)
                
                await asyncio.sleep(30)  # Process every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in replication processor: {e}")
                await asyncio.sleep(60)
    
    async def _consistency_checker(self) -> None:
        """Check consistency of multi-region archives."""
        while self._is_running:
            try:
                for archive_id, multi_archive in self._multi_region_archives.items():
                    if multi_archive.consistency_state != "synced":
                        continue
                    
                    # Periodically verify consistency
                    if (multi_archive.last_sync_check and 
                        datetime.now(timezone.utc) - multi_archive.last_sync_check > timedelta(hours=24)):
                        
                        await self._verify_archive_consistency(archive_id)
                
                await asyncio.sleep(3600)  # Check every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in consistency checker: {e}")
                await asyncio.sleep(300)
    
    async def _compliance_monitor(self) -> None:
        """Monitor compliance requirements for multi-region archives."""
        while self._is_running:
            try:
                # Check compliance for all archives
                compliance_issues = []
                
                for archive_id, multi_archive in self._multi_region_archives.items():
                    if not multi_archive.data_residency_satisfied:
                        compliance_issues.append({
                            "archive_id": str(archive_id),
                            "issue": "data_residency_not_satisfied",
                            "regions": multi_archive.regions,
                            "compliance_regions": multi_archive.compliance_regions
                        })
                
                if compliance_issues:
                    logger.warning(f"Found {len(compliance_issues)} compliance issues")
                
                await asyncio.sleep(3600)  # Check every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in compliance monitor: {e}")
                await asyncio.sleep(300)
    
    # Helper methods for multi-region operations
    
    async def _validate_compliance_regions(
        self, 
        regions: List[str], 
        compliance_requirements: List[str]
    ) -> List[str]:
        """Validate that regions satisfy compliance requirements."""
        validated_regions = []
        
        for region_id in regions:
            if region_id not in self._region_configs:
                continue
                
            config = self._region_configs[region_id]
            
            # Check GDPR compliance
            if "GDPR" in compliance_requirements and config.gdpr_compliant:
                validated_regions.append(region_id)
            
            # Check data residency
            if any(req.startswith("DATA_RESIDENCY_") for req in compliance_requirements):
                country_requirements = [
                    req.replace("DATA_RESIDENCY_", "") 
                    for req in compliance_requirements 
                    if req.startswith("DATA_RESIDENCY_")
                ]
                if config.country_code in country_requirements:
                    validated_regions.append(region_id)
            
            # If no specific compliance requirements, include region
            if not compliance_requirements:
                validated_regions.append(region_id)
        
        return validated_regions
    
    async def _create_regional_archive(
        self,
        events: List[DomainEvent],
        archive_name: str,
        region_id: str,
        config: RegionConfig,
        is_primary: bool = False,
        retention_days: Optional[int] = None
    ) -> EventArchive:
        """Create an archive in a specific region."""
        region_suffix = f"_primary_{region_id}" if is_primary else f"_replica_{region_id}"
        regional_name = f"{archive_name}{region_suffix}"
        
        # Use region-specific compression profile
        compression_profile = config.compression_profile
        
        # Create archive with region-specific settings
        archive = await self._archival_service.create_manual_archive(
            archive_name=regional_name,
            event_criteria={},  # Events already filtered
            description=f"{'Primary' if is_primary else 'Replica'} archive in {config.region_name}",
            storage_type=config.default_storage_type,
            retention_days=retention_days or config.retention_days_default
        )
        
        return archive
    
    async def _create_sync_replicas(
        self,
        events: List[DomainEvent],
        multi_archive: MultiRegionArchive,
        replica_regions: List[str],
        retention_days: Optional[int]
    ) -> None:
        """Create replicas synchronously across regions."""
        replica_tasks = []
        
        for region_id in replica_regions:
            if region_id not in self._region_configs:
                logger.warning(f"Skipping unknown region: {region_id}")
                continue
            
            config = self._region_configs[region_id]
            task = self._create_regional_archive(
                events, 
                multi_archive.primary_archive.archive_name,
                region_id, 
                config, 
                is_primary=False,
                retention_days=retention_days
            )
            replica_tasks.append((region_id, task))
        
        # Execute all replica creations
        for region_id, task in replica_tasks:
            try:
                replica_archive = await task
                multi_archive.replica_archives[region_id] = replica_archive
                multi_archive.successful_replicas += 1
                self._metrics["successful_replications"] += 1
            except Exception as e:
                logger.error(f"Failed to create replica in region {region_id}: {e}")
                multi_archive.failed_replicas += 1
                self._metrics["failed_replications"] += 1
        
        multi_archive.total_replicas = len(replica_regions)
    
    async def _queue_async_replicas(
        self,
        events: List[DomainEvent],
        multi_archive: MultiRegionArchive,
        replica_regions: List[str],
        retention_days: Optional[int]
    ) -> None:
        """Queue replica creation for asynchronous processing."""
        for region_id in replica_regions:
            if region_id not in self._region_configs:
                continue
            
            replication_task = {
                "type": "create_replica",
                "archive_id": multi_archive.primary_archive.id,
                "region_id": region_id,
                "events": events,
                "archive_name": multi_archive.primary_archive.archive_name,
                "retention_days": retention_days,
                "queued_at": datetime.now(timezone.utc).isoformat()
            }
            
            if region_id not in self._replication_queue:
                self._replication_queue[region_id] = []
            
            self._replication_queue[region_id].append(replication_task)
        
        multi_archive.total_replicas = len(replica_regions)
    
    async def _check_all_regions_health(self) -> None:
        """Check health status of all configured regions."""
        for region_id, config in self._region_configs.items():
            try:
                health_status = await self._check_region_health(region_id, config)
                self._region_health[region_id] = health_status
                
                # Update region config with health info
                config.last_health_check = datetime.now(timezone.utc)
                if health_status["healthy"]:
                    config.consecutive_failures = 0
                else:
                    config.consecutive_failures += 1
                    
            except Exception as e:
                logger.error(f"Health check failed for region {region_id}: {e}")
                config.consecutive_failures += 1
    
    async def _check_region_health(
        self, 
        region_id: str, 
        config: RegionConfig
    ) -> Dict[str, Any]:
        """Check health of a specific region."""
        # This would implement actual health checks for the region
        # For now, return a mock health status
        
        is_healthy = config.is_active and config.consecutive_failures < 3
        
        return {
            "region_id": region_id,
            "healthy": is_healthy,
            "response_time_ms": 100 if is_healthy else 5000,
            "storage_available": is_healthy,
            "last_check": datetime.now(timezone.utc).isoformat(),
            "consecutive_failures": config.consecutive_failures,
            "error": None if is_healthy else "Region experiencing issues"
        }
    
    async def _process_replication_task(self, task: Dict[str, Any]) -> None:
        """Process a single replication task."""
        try:
            if task["type"] == "create_replica":
                # Implementation for creating replicas
                logger.info(f"Processing replica creation for {task['archive_id']} in {task['region_id']}")
                # Actual replication logic would go here
                
        except Exception as e:
            logger.error(f"Failed to process replication task: {e}")
    
    async def _verify_archive_consistency(self, archive_id: UUID) -> None:
        """Verify consistency of a multi-region archive."""
        if archive_id not in self._multi_region_archives:
            return
        
        multi_archive = self._multi_region_archives[archive_id]
        # Implementation would check checksums, event counts, etc.
        logger.debug(f"Verifying consistency for archive {archive_id}")
    
    async def _check_archive_consistency(self, archive: EventArchive) -> Dict[str, Any]:
        """Check consistency of a single archive."""
        # Mock implementation
        return {
            "available": True,
            "checksum_match": True,
            "event_count_match": True,
            "last_verified": datetime.now(timezone.utc).isoformat()
        }
    
    async def _re_replicate_archive(
        self, 
        primary_archive: EventArchive, 
        replica_archive: EventArchive, 
        region_id: str
    ) -> None:
        """Re-replicate an archive to fix consistency issues."""
        logger.info(f"Re-replicating archive {primary_archive.id} to region {region_id}")
        # Implementation would restore from primary and re-create replica
    
    async def _select_restore_source_region(
        self,
        multi_archive: MultiRegionArchive,
        target_region: Optional[str],
        prefer_closest: bool
    ) -> str:
        """Select the best region for archive restoration."""
        # Priority: target_region > healthy replicas > primary
        if target_region and target_region in multi_archive.replica_archives:
            region_health = self._region_health.get(target_region, {})
            if region_health.get("healthy", False):
                return target_region
        
        # Find healthiest replica
        for region_id in multi_archive.replica_archives.keys():
            region_health = self._region_health.get(region_id, {})
            if region_health.get("healthy", False):
                return region_id
        
        # Fall back to primary
        return multi_archive.primary_archive.storage_location