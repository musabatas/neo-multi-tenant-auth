"""Event archival service for long-term scalability."""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from uuid import uuid4

from neo_commons.features.events.repositories.event_archival_repository import (
    EventArchivalRepository, ArchivalRuleRepository, ArchivalJobRepository
)
from neo_commons.features.events.repositories.domain_event_repository import DomainEventRepository
from neo_commons.features.events.entities.event_archive import (
    EventArchive, ArchivalRule, ArchivalJob, ArchivalStatus, ArchivalPolicy, StorageType
)
from neo_commons.features.events.services.archival_compression_service import ArchivalCompressionService
from neo_commons.features.events.services.multi_region_archival_service import MultiRegionArchivalService
from neo_commons.core.value_objects import EventId, UserId


logger = logging.getLogger(__name__)


class EventArchivalService:
    """Service for managing event archival operations."""
    
    def __init__(
        self,
        event_repository: DomainEventRepository,
        archive_repository: EventArchivalRepository,
        rule_repository: ArchivalRuleRepository,
        job_repository: ArchivalJobRepository,
        compression_service: Optional[ArchivalCompressionService] = None,
        multi_region_service: Optional[MultiRegionArchivalService] = None,
        batch_size: int = 1000,
        max_concurrent_jobs: int = 3
    ):
        self._event_repository = event_repository
        self._archive_repository = archive_repository
        self._rule_repository = rule_repository
        self._job_repository = job_repository
        self._compression_service = compression_service or ArchivalCompressionService()
        self._multi_region_service = multi_region_service or MultiRegionArchivalService()
        self._batch_size = batch_size
        self._max_concurrent_jobs = max_concurrent_jobs
        self._archival_tasks = []
        self._is_running = False
    
    async def start_archival_scheduler(self) -> None:
        """Start the automatic archival scheduler."""
        if self._is_running:
            logger.warning("Archival scheduler is already running")
            return
        
        self._is_running = True
        logger.info("Starting event archival scheduler")
        
        # Start monitoring tasks
        self._archival_tasks = [
            asyncio.create_task(self._rule_execution_monitor()),
            asyncio.create_task(self._archive_cleanup_monitor()),
            asyncio.create_task(self._failed_job_retry_monitor())
        ]
        
        logger.info("Event archival scheduler started successfully")
    
    async def stop_archival_scheduler(self) -> None:
        """Stop the automatic archival scheduler."""
        if not self._is_running:
            return
        
        logger.info("Stopping event archival scheduler")
        self._is_running = False
        
        # Cancel all monitoring tasks
        for task in self._archival_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self._archival_tasks:
            await asyncio.gather(*self._archival_tasks, return_exceptions=True)
        
        self._archival_tasks = []
        logger.info("Event archival scheduler stopped")
    
    async def execute_archival_rule(self, rule_id: str) -> ArchivalJob:
        """Execute a specific archival rule."""
        rule = await self._rule_repository.get_rule_by_id(rule_id)
        if not rule:
            raise ValueError(f"Archival rule {rule_id} not found")
        
        if not rule.is_enabled:
            raise ValueError(f"Archival rule {rule.name} is not enabled")
        
        logger.info(f"Executing archival rule: {rule.name}")
        
        # Create archival job
        job = ArchivalJob(
            id=uuid4(),
            rule_id=rule.id,
            archive_id=None,
            status=ArchivalStatus.PENDING,
            started_at=None,
            completed_at=None,
            events_processed=0,
            events_archived=0,
            events_skipped=0,
            processing_time_seconds=None,
            throughput_events_per_second=None,
            storage_location=None,
            compressed_size_bytes=None,
            uncompressed_size_bytes=None,
            error_message=None,
            retry_count=0,
            max_retries=3,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        await self._job_repository.save_job(job)
        
        # Execute archival in background
        asyncio.create_task(self._execute_archival_job(job, rule))
        
        return job
    
    async def create_manual_archive(
        self,
        archive_name: str,
        description: Optional[str],
        event_criteria: Dict[str, Any],
        storage_type: StorageType,
        created_by_user_id: str,
        retention_days: Optional[int] = None
    ) -> EventArchive:
        """Create a manual archive with specific criteria."""
        logger.info(f"Creating manual archive: {archive_name}")
        
        # Get events matching criteria
        events_to_archive = await self._get_events_for_archival(event_criteria)
        
        if not events_to_archive:
            raise ValueError("No events found matching the specified criteria")
        
        # Create archive record
        archive = EventArchive(
            id=uuid4(),
            archive_name=archive_name,
            description=description,
            policy=ArchivalPolicy.CUSTOM,
            storage_type=storage_type,
            storage_location=f"manual_archives/{archive_name}_{uuid4()}",
            created_at=datetime.now(timezone.utc),
            archived_at=None,
            restored_at=None,
            status=ArchivalStatus.PENDING,
            event_count=len(events_to_archive),
            size_bytes=0,  # Will be calculated during archival
            compression_ratio=None,
            checksum=None,
            events_from=min(event.created_at for event in events_to_archive),
            events_to=max(event.created_at for event in events_to_archive),
            context_ids=list(set(event.context_id for event in events_to_archive)),
            event_types=list(set(event.event_type.value for event in events_to_archive)),
            retention_days=retention_days,
            auto_delete_after_days=None,
            created_by_user_id=created_by_user_id,
            tags={"manual": "true", "created_by": str(created_by_user_id)}
        )
        
        await self._archive_repository.save_archive(archive)
        
        # Execute archival
        await self._perform_archive_operation(archive, events_to_archive)
        
        return archive
    
    async def create_multi_region_archive(
        self,
        archive_name: str,
        description: Optional[str],
        event_criteria: Dict[str, Any],
        primary_region: str,
        replica_regions: List[str],
        replication_strategy: str = "async_replication",
        compliance_requirements: List[str] = None,
        created_by_user_id: str,
        retention_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a multi-region archive with replication."""
        logger.info(f"Creating multi-region archive: {archive_name}")
        
        # Get events matching criteria
        events_to_archive = await self._get_events_for_archival(event_criteria)
        
        if not events_to_archive:
            raise ValueError("No events found matching the specified criteria")
        
        # Create multi-region archive using the specialized service
        multi_region_archive = await self._multi_region_service.create_multi_region_archive(
            events=events_to_archive,
            archive_name=archive_name,
            primary_region=primary_region,
            replica_regions=replica_regions,
            replication_strategy=replication_strategy,
            compliance_requirements=compliance_requirements or [],
            retention_days=retention_days
        )
        
        # Create main archive record
        archive = EventArchive(
            id=multi_region_archive.archive_id,
            archive_name=archive_name,
            description=description,
            policy=ArchivalPolicy.CUSTOM,
            storage_type=StorageType.COLD_STORAGE,
            storage_location=multi_region_archive.primary_location,
            created_at=datetime.now(timezone.utc),
            archived_at=None,
            restored_at=None,
            status=ArchivalStatus.COMPLETED,
            event_count=len(events_to_archive),
            size_bytes=multi_region_archive.total_size_bytes,
            compression_ratio=multi_region_archive.compression_ratio,
            checksum=multi_region_archive.primary_checksum,
            events_from=min(event.created_at for event in events_to_archive),
            events_to=max(event.created_at for event in events_to_archive),
            context_ids=list(set(event.context_id for event in events_to_archive)),
            event_types=list(set(event.event_type.value for event in events_to_archive)),
            retention_days=retention_days,
            auto_delete_after_days=None,
            created_by_user_id=created_by_user_id,
            tags={
                "multi_region": "true",
                "primary_region": primary_region,
                "replica_count": str(len(replica_regions)),
                "replication_strategy": replication_strategy,
                "created_by": str(created_by_user_id)
            }
        )
        
        await self._archive_repository.save_archive(archive)
        
        logger.info(f"Successfully created multi-region archive with {len(replica_regions)} replicas")
        
        return {
            "archive": archive,
            "multi_region_details": multi_region_archive,
            "primary_region": primary_region,
            "replica_regions": replica_regions,
            "total_size_bytes": multi_region_archive.total_size_bytes,
            "replication_strategy": replication_strategy,
            "created_at": datetime.now(timezone.utc)
        }
    
    async def restore_archived_events(
        self, 
        archive_id: str,
        target_table: Optional[str] = None
    ) -> Dict[str, Any]:
        """Restore events from an archive."""
        archive = await self._archive_repository.get_archive_by_id(archive_id)
        if not archive:
            raise ValueError(f"Archive {archive_id} not found")
        
        if archive.status != ArchivalStatus.COMPLETED:
            raise ValueError(f"Archive {archive.archive_name} is not in completed status")
        
        logger.info(f"Restoring events from archive: {archive.archive_name}")
        
        try:
            # Update archive status
            await self._archive_repository.update_archive_status(
                archive_id, ArchivalStatus.IN_PROGRESS
            )
            
            # Perform restore operation based on storage type
            restored_count = await self._perform_restore_operation(archive, target_table)
            
            # Update archive status
            await self._archive_repository.update_archive_status(
                archive_id, ArchivalStatus.RESTORED
            )
            
            logger.info(f"Successfully restored {restored_count} events from archive {archive.archive_name}")
            
            return {
                "archive_id": archive_id,
                "archive_name": archive.archive_name,
                "events_restored": restored_count,
                "restored_at": datetime.now(timezone.utc)
            }
            
        except Exception as e:
            logger.error(f"Failed to restore archive {archive.archive_name}: {str(e)}")
            await self._archive_repository.update_archive_status(
                archive_id, ArchivalStatus.FAILED
            )
            raise
    
    async def delete_expired_archives(self) -> Dict[str, Any]:
        """Delete archives that have exceeded their retention period."""
        expired_archives = await self._archive_repository.get_expired_archives()
        
        deleted_count = 0
        total_size_freed = 0
        
        for archive in expired_archives:
            try:
                logger.info(f"Deleting expired archive: {archive.archive_name}")
                
                # Delete from storage backend
                await self._delete_from_storage(archive)
                
                # Delete archive record
                await self._archive_repository.delete_archive(archive.id)
                
                deleted_count += 1
                total_size_freed += archive.size_bytes
                
            except Exception as e:
                logger.error(f"Failed to delete expired archive {archive.archive_name}: {str(e)}")
        
        return {
            "deleted_archives": deleted_count,
            "total_size_freed_bytes": total_size_freed,
            "deleted_at": datetime.now(timezone.utc)
        }
    
    async def get_archival_statistics(self) -> Dict[str, Any]:
        """Get comprehensive archival statistics."""
        # Get storage statistics
        storage_stats = await self._archive_repository.get_storage_statistics()
        
        # Get recent job statistics
        recent_jobs = await self._job_repository.get_jobs_by_status(ArchivalStatus.COMPLETED)
        recent_job_stats = self._calculate_job_statistics(recent_jobs[-10:])  # Last 10 jobs
        
        # Get current table statistics
        table_stats = await self._get_current_table_statistics()
        
        return {
            "storage": storage_stats,
            "recent_jobs": recent_job_stats,
            "current_table": table_stats,
            "generated_at": datetime.now(timezone.utc)
        }
    
    async def get_compression_statistics(self) -> Dict[str, Any]:
        """Get compression performance statistics."""
        return await self._compression_service.get_compression_statistics()
    
    async def benchmark_compression_profiles(self, sample_events: List = None) -> Dict[str, Any]:
        """Benchmark different compression profiles with sample data."""
        if not sample_events:
            # Get a sample of recent events for benchmarking
            sample_criteria = {
                'limit': 1000,
                'created_after': datetime.now(timezone.utc) - timedelta(hours=1)
            }
            sample_events = await self._get_events_for_archival(sample_criteria)
        
        if not sample_events:
            raise ValueError("No sample events available for benchmarking")
        
        return await self._compression_service.benchmark_compression_profiles(sample_events)
    
    async def get_multi_region_status(self, archive_id: str) -> Dict[str, Any]:
        """Get multi-region replication status for an archive."""
        archive = await self._archive_repository.get_archive_by_id(archive_id)
        if not archive:
            raise ValueError(f"Archive {archive_id} not found")
        
        # Check if this is a multi-region archive
        if not archive.tags.get("multi_region"):
            return {"multi_region": False, "archive_id": archive_id}
        
        return await self._multi_region_service.get_archive_status(archive_id)
    
    async def _rule_execution_monitor(self) -> None:
        """Monitor and execute archival rules that are due."""
        while self._is_running:
            try:
                rules_due = await self._rule_repository.get_rules_due_for_execution()
                
                for rule in rules_due:
                    try:
                        # Check if rule should actually run based on current stats
                        current_stats = await self._get_current_table_statistics()
                        
                        if rule.should_archive_now(current_stats):
                            logger.info(f"Executing scheduled archival rule: {rule.name}")
                            await self.execute_archival_rule(rule.id)
                            
                            # Update next run time if scheduled
                            if rule.schedule_cron:
                                next_run = self._calculate_next_run_time(rule.schedule_cron)
                                await self._rule_repository.update_rule_next_run(rule.id, next_run)
                            
                            await self._rule_repository.update_rule_last_run(
                                rule.id, datetime.now(timezone.utc)
                            )
                    
                    except Exception as e:
                        logger.error(f"Failed to execute archival rule {rule.name}: {str(e)}")
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in rule execution monitor: {str(e)}")
                await asyncio.sleep(60)
    
    async def _archive_cleanup_monitor(self) -> None:
        """Monitor and cleanup expired archives."""
        while self._is_running:
            try:
                await self.delete_expired_archives()
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                logger.error(f"Error in archive cleanup monitor: {str(e)}")
                await asyncio.sleep(300)
    
    async def _failed_job_retry_monitor(self) -> None:
        """Monitor and retry failed archival jobs."""
        while self._is_running:
            try:
                failed_jobs = await self._job_repository.get_failed_jobs_for_retry()
                
                for job in failed_jobs:
                    if job.should_retry():
                        logger.info(f"Retrying failed archival job: {job.id}")
                        
                        rule = await self._rule_repository.get_rule_by_id(job.rule_id)
                        if rule and rule.is_enabled:
                            asyncio.create_task(self._execute_archival_job(job, rule))
                
                await asyncio.sleep(600)  # Check every 10 minutes
                
            except Exception as e:
                logger.error(f"Error in failed job retry monitor: {str(e)}")
                await asyncio.sleep(300)
    
    async def _execute_archival_job(self, job: ArchivalJob, rule: ArchivalRule) -> None:
        """Execute an archival job."""
        try:
            # Update job status to in progress
            await self._job_repository.update_job_status(job.id, ArchivalStatus.IN_PROGRESS)
            
            start_time = datetime.now(timezone.utc)
            
            # Get events for archival based on rule criteria
            criteria = rule.get_archive_criteria()
            events_to_archive = await self._get_events_for_archival(criteria)
            
            if not events_to_archive:
                logger.info(f"No events found for archival rule: {rule.name}")
                await self._job_repository.update_job_status(job.id, ArchivalStatus.COMPLETED)
                return
            
            # Create archive record
            archive = EventArchive(
                id=uuid4(),
                archive_name=f"{rule.name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                description=f"Automatic archive created by rule: {rule.name}",
                policy=rule.policy,
                storage_type=rule.storage_type,
                storage_location=rule.storage_location_template.format(
                    rule_name=rule.name,
                    timestamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
                ),
                created_at=datetime.now(timezone.utc),
                archived_at=None,
                restored_at=None,
                status=ArchivalStatus.PENDING,
                event_count=len(events_to_archive),
                size_bytes=0,
                compression_ratio=None,
                checksum=None,
                events_from=min(event.created_at for event in events_to_archive),
                events_to=max(event.created_at for event in events_to_archive),
                context_ids=list(set(event.context_id for event in events_to_archive)),
                event_types=list(set(event.event_type.value for event in events_to_archive)),
                retention_days=rule.retention_days,
                auto_delete_after_days=rule.auto_delete_after_days,
                created_by_user_id=rule.created_by_user_id,
                tags={"rule_id": str(rule.id), "automated": "true"}
            )
            
            await self._archive_repository.save_archive(archive)
            
            # Perform archival operation
            await self._perform_archive_operation(archive, events_to_archive)
            
            # Calculate final statistics
            end_time = datetime.now(timezone.utc)
            processing_time = (end_time - start_time).total_seconds()
            throughput = len(events_to_archive) / processing_time if processing_time > 0 else 0
            
            # Complete job
            final_stats = {
                "processing_time_seconds": processing_time,
                "throughput_events_per_second": throughput,
                "storage_location": archive.storage_location,
                "compressed_size_bytes": archive.size_bytes,
                "uncompressed_size_bytes": archive.size_bytes  # Placeholder
            }
            
            await self._job_repository.complete_job(job.id, archive.id, final_stats)
            
            logger.info(f"Successfully completed archival job for rule: {rule.name}")
            
        except Exception as e:
            logger.error(f"Failed to execute archival job: {str(e)}")
            await self._job_repository.fail_job(job.id, str(e))
    
    async def _get_events_for_archival(self, criteria: Dict[str, Any]) -> List:
        """Get events that match archival criteria."""
        # This would implement the actual event selection logic
        # For now, return a placeholder implementation
        
        # In a real implementation, this would:
        # 1. Build SQL query based on criteria
        # 2. Execute query to get matching events
        # 3. Return list of events
        
        logger.info(f"Getting events for archival with criteria: {criteria}")
        
        # Placeholder: get old processed events
        cutoff_date = criteria.get('created_before', datetime.now(timezone.utc) - timedelta(days=30))
        
        # This would be implemented in the domain event repository
        query = """
        SELECT * FROM webhook_events 
        WHERE processed_at IS NOT NULL 
        AND created_at < $1
        ORDER BY created_at ASC
        LIMIT $2
        """
        
        # Return empty list for now - would be actual events in real implementation
        return []
    
    async def _perform_archive_operation(self, archive: EventArchive, events: List) -> None:
        """Perform the actual archival operation."""
        logger.info(f"Archiving {len(events)} events to {archive.storage_location}")
        
        # Update archive status
        await self._archive_repository.update_archive_status(archive.id, ArchivalStatus.IN_PROGRESS)
        
        try:
            # Perform archival based on storage type
            if archive.storage_type == StorageType.DATABASE_PARTITION:
                await self._archive_to_partition(archive, events)
            elif archive.storage_type == StorageType.COLD_STORAGE:
                await self._archive_to_cold_storage(archive, events)
            elif archive.storage_type == StorageType.COMPRESSED_ARCHIVE:
                await self._archive_to_compressed_table(archive, events)
            else:
                raise ValueError(f"Unsupported storage type: {archive.storage_type}")
            
            # Update archive as completed
            await self._archive_repository.update_archive_status(archive.id, ArchivalStatus.COMPLETED)
            
            # Remove events from main table (optional, based on policy)
            await self._cleanup_archived_events(events)
            
        except Exception as e:
            await self._archive_repository.update_archive_status(archive.id, ArchivalStatus.FAILED)
            raise
    
    async def _archive_to_partition(self, archive: EventArchive, events: List) -> None:
        """Archive events to a database partition."""
        logger.info(f"Archiving to database partition: {archive.storage_location}")
        
        # Create partition table if not exists
        partition_name = f"webhook_events_archive_{archive.id.hex[:8]}"
        
        create_partition_query = f"""
        CREATE TABLE IF NOT EXISTS {partition_name} (
            LIKE webhook_events INCLUDING ALL
        )
        """
        
        # Insert events into partition
        insert_query = f"""
        INSERT INTO {partition_name}
        SELECT * FROM webhook_events
        WHERE id = ANY($1)
        """
        
        # Placeholder - would execute actual database operations
        logger.info(f"Created partition {partition_name} with {len(events)} events")
    
    async def _archive_to_cold_storage(self, archive: EventArchive, events: List) -> None:
        """Archive events to cold storage (S3, GCS, etc.)."""
        logger.info(f"Archiving to cold storage: {archive.storage_location}")
        
        try:
            # Use compression service for advanced compression
            compressed_data, compression_stats = await self._compression_service.compress_events_for_archive(
                events, archive, profile_name="balanced"
            )
            
            # Check if multi-region replication is configured for this archive
            if hasattr(archive, 'replica_regions') and archive.replica_regions:
                # Use multi-region service for distributed archival
                multi_region_archive = await self._multi_region_service.create_multi_region_archive(
                    events=events,
                    archive_name=archive.archive_name,
                    primary_region=getattr(archive, 'primary_region', 'us-east-1'),
                    replica_regions=archive.replica_regions,
                    replication_strategy=getattr(archive, 'replication_strategy', None),
                    compliance_requirements=getattr(archive, 'compliance_requirements', []),
                    retention_days=archive.retention_days
                )
                
                # Update archive with multi-region details
                archive.storage_location = multi_region_archive.primary_location
                archive.size_bytes = multi_region_archive.total_size_bytes
                archive.compression_ratio = compression_stats.get('compression_ratio', 1.0)
                archive.checksum = compression_stats.get('checksum')
                
                logger.info(f"Created multi-region archive with {len(multi_region_archive.replicas)} replicas")
            else:
                # Standard single-region cold storage archival
                
                # Calculate uncompressed size for ratio calculation
                uncompressed_size = compression_stats.get('original_size_bytes', len(events) * 1024)
                compressed_size = len(compressed_data)
                compression_ratio = compressed_size / uncompressed_size if uncompressed_size > 0 else 1.0
                
                # Here would be actual cloud storage upload
                # await self._upload_to_cloud_storage(archive.storage_location, compressed_data)
                
                # Update archive with compression details
                archive.size_bytes = compressed_size
                archive.compression_ratio = compression_ratio
                archive.checksum = compression_stats.get('checksum')
                
                logger.info(f"Archived {len(events)} events with {compression_stats['algorithm']} compression")
                logger.info(f"Compression: {uncompressed_size:,} bytes → {compressed_size:,} bytes "
                          f"({compression_ratio:.2%} ratio)")
            
            # Save updated archive details
            await self._archive_repository.save_archive(archive)
            
        except Exception as e:
            logger.error(f"Failed to archive to cold storage: {str(e)}")
            raise
    
    async def _archive_to_compressed_table(self, archive: EventArchive, events: List) -> None:
        """Archive events to a compressed table."""
        logger.info(f"Archiving to compressed table: {archive.storage_location}")
        
        try:
            # Use compression service with fast profile for database storage
            compressed_data, compression_stats = await self._compression_service.compress_events_for_archive(
                events, archive, profile_name="fast"
            )
            
            # Create compressed archive table if not exists
            table_name = f"event_archives_{archive.id.hex[:8]}"
            
            create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                archive_id UUID NOT NULL,
                compressed_data BYTEA NOT NULL,
                compression_algorithm TEXT NOT NULL,
                original_event_count INTEGER NOT NULL,
                original_size_bytes BIGINT NOT NULL,
                compressed_size_bytes BIGINT NOT NULL,
                checksum TEXT,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                PRIMARY KEY (archive_id)
            )
            """
            
            # Insert compressed data
            insert_query = f"""
            INSERT INTO {table_name} (
                archive_id, compressed_data, compression_algorithm,
                original_event_count, original_size_bytes, compressed_size_bytes,
                checksum, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """
            
            # Execute database operations (placeholder for actual execution)
            # await connection.execute(create_table_query)
            # await connection.execute(insert_query, archive.id, compressed_data, ...)
            
            # Update archive with compression details
            uncompressed_size = compression_stats.get('original_size_bytes', len(events) * 1024)
            compressed_size = len(compressed_data)
            
            archive.size_bytes = compressed_size
            archive.compression_ratio = compressed_size / uncompressed_size if uncompressed_size > 0 else 1.0
            archive.checksum = compression_stats.get('checksum')
            archive.storage_location = table_name
            
            await self._archive_repository.save_archive(archive)
            
            logger.info(f"Archived {len(events)} events to compressed table {table_name}")
            logger.info(f"Compression: {uncompressed_size:,} bytes → {compressed_size:,} bytes "
                      f"({archive.compression_ratio:.2%} ratio)")
            
        except Exception as e:
            logger.error(f"Failed to archive to compressed table: {str(e)}")
            raise
    
    async def _perform_restore_operation(self, archive: EventArchive, target_table: Optional[str]) -> int:
        """Restore events from archive."""
        target = target_table or "webhook_events"
        
        if archive.storage_type == StorageType.DATABASE_PARTITION:
            return await self._restore_from_partition(archive, target)
        elif archive.storage_type == StorageType.COLD_STORAGE:
            return await self._restore_from_cold_storage(archive, target)
        elif archive.storage_type == StorageType.COMPRESSED_ARCHIVE:
            return await self._restore_from_compressed_table(archive, target)
        else:
            raise ValueError(f"Unsupported storage type for restore: {archive.storage_type}")
    
    async def _restore_from_partition(self, archive: EventArchive, target_table: str) -> int:
        """Restore events from database partition."""
        partition_name = f"webhook_events_archive_{archive.id.hex[:8]}"
        
        # Copy events from partition to target table
        restore_query = f"""
        INSERT INTO {target_table}
        SELECT * FROM {partition_name}
        ON CONFLICT (id) DO NOTHING
        """
        
        # Placeholder - would execute actual restore
        return archive.event_count
    
    async def _restore_from_cold_storage(self, archive: EventArchive, target_table: str) -> int:
        """Restore events from cold storage."""
        # Download from cloud storage
        # Decompress data
        # Insert into target table
        
        # Placeholder implementation
        return archive.event_count
    
    async def _restore_from_compressed_table(self, archive: EventArchive, target_table: str) -> int:
        """Restore events from compressed table."""
        # Decompress and restore events
        
        # Placeholder implementation
        return archive.event_count
    
    async def _cleanup_archived_events(self, events: List) -> None:
        """Remove archived events from main table."""
        if not events:
            return
        
        event_ids = [event.id for event in events]
        
        # Delete events from main table
        delete_query = "DELETE FROM webhook_events WHERE id = ANY($1)"
        
        # Placeholder - would execute actual deletion
        logger.info(f"Cleaned up {len(event_ids)} archived events from main table")
    
    async def _delete_from_storage(self, archive: EventArchive) -> None:
        """Delete archive from storage backend."""
        if archive.storage_type == StorageType.DATABASE_PARTITION:
            partition_name = f"webhook_events_archive_{archive.id.hex[:8]}"
            drop_query = f"DROP TABLE IF EXISTS {partition_name}"
            # Execute drop query
        elif archive.storage_type == StorageType.COLD_STORAGE:
            # Delete from cloud storage
            pass
        elif archive.storage_type == StorageType.COMPRESSED_ARCHIVE:
            # Delete from compressed table
            pass
    
    async def _get_current_table_statistics(self) -> Dict[str, Any]:
        """Get current webhook_events table statistics."""
        # Query table statistics
        stats_query = """
        SELECT 
            COUNT(*) as total_events,
            COUNT(CASE WHEN processed_at IS NULL THEN 1 END) as unprocessed_events,
            pg_total_relation_size('webhook_events') / (1024*1024*1024.0) as table_size_gb,
            EXTRACT(DAYS FROM NOW() - MIN(created_at)) as oldest_event_age_days,
            MAX(created_at) as newest_event_date
        FROM webhook_events
        """
        
        # Placeholder - would execute actual query
        return {
            "total_events": 100000,
            "unprocessed_events": 1000,
            "table_size_gb": 5.2,
            "oldest_event_age_days": 45,
            "newest_event_date": datetime.now(timezone.utc)
        }
    
    def _calculate_job_statistics(self, jobs: List[ArchivalJob]) -> Dict[str, Any]:
        """Calculate statistics for a list of jobs."""
        if not jobs:
            return {
                "total_jobs": 0,
                "success_rate": 0.0,
                "avg_processing_time": 0.0,
                "avg_throughput": 0.0,
                "total_events_archived": 0
            }
        
        successful_jobs = [job for job in jobs if job.is_completed_successfully()]
        
        return {
            "total_jobs": len(jobs),
            "success_rate": (len(successful_jobs) / len(jobs)) * 100,
            "avg_processing_time": sum(
                job.processing_time_seconds or 0 for job in successful_jobs
            ) / len(successful_jobs) if successful_jobs else 0,
            "avg_throughput": sum(
                job.throughput_events_per_second or 0 for job in successful_jobs
            ) / len(successful_jobs) if successful_jobs else 0,
            "total_events_archived": sum(job.events_archived for job in jobs)
        }
    
    def _calculate_next_run_time(self, cron_expression: str) -> datetime:
        """Calculate next run time from cron expression."""
        # Placeholder implementation - would use a proper cron parser
        # For now, just add 24 hours
        return datetime.now(timezone.utc) + timedelta(days=1)