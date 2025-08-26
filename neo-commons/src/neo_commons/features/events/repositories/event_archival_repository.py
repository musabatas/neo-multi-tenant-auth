"""Event archival repository implementations."""

from typing import List, Optional, Dict, Any, Protocol, runtime_checkable
from datetime import datetime
from uuid import UUID

from ....features.database.entities.protocols import DatabaseRepository
from neo_commons.features.events.entities.event_archive import (
    EventArchive, ArchivalRule, ArchivalJob, ArchivalStatus, ArchivalPolicy
)
from neo_commons.core.value_objects import EventId


@runtime_checkable
class EventArchivalRepository(Protocol):
    """Protocol for event archival repository operations."""
    
    async def save_archive(self, archive: EventArchive) -> EventArchive:
        """Save an event archive record."""
        ...
    
    async def get_archive_by_id(self, archive_id: UUID) -> Optional[EventArchive]:
        """Get archive by ID."""
        ...
    
    async def get_archives_by_status(self, status: ArchivalStatus) -> List[EventArchive]:
        """Get archives by status."""
        ...
    
    async def get_archives_by_date_range(
        self, 
        from_date: datetime, 
        to_date: datetime
    ) -> List[EventArchive]:
        """Get archives within date range."""
        ...
    
    async def get_expired_archives(self) -> List[EventArchive]:
        """Get archives that have exceeded their retention period."""
        ...
    
    async def update_archive_status(self, archive_id: UUID, status: ArchivalStatus) -> None:
        """Update archive status."""
        ...
    
    async def delete_archive(self, archive_id: UUID) -> None:
        """Delete archive record."""
        ...
    
    async def get_storage_statistics(self) -> Dict[str, Any]:
        """Get archival storage statistics."""
        ...


@runtime_checkable
class ArchivalRuleRepository(Protocol):
    """Protocol for archival rule repository operations."""
    
    async def save_rule(self, rule: ArchivalRule) -> ArchivalRule:
        """Save an archival rule."""
        ...
    
    async def get_rule_by_id(self, rule_id: UUID) -> Optional[ArchivalRule]:
        """Get rule by ID."""
        ...
    
    async def get_enabled_rules(self) -> List[ArchivalRule]:
        """Get all enabled archival rules."""
        ...
    
    async def get_rules_by_policy(self, policy: ArchivalPolicy) -> List[ArchivalRule]:
        """Get rules by archival policy."""
        ...
    
    async def get_rules_due_for_execution(self) -> List[ArchivalRule]:
        """Get rules that are due for execution."""
        ...
    
    async def update_rule_last_run(self, rule_id: UUID, last_run_at: datetime) -> None:
        """Update rule's last run timestamp."""
        ...
    
    async def update_rule_next_run(self, rule_id: UUID, next_run_at: datetime) -> None:
        """Update rule's next run timestamp."""
        ...
    
    async def delete_rule(self, rule_id: UUID) -> None:
        """Delete archival rule."""
        ...


@runtime_checkable
class ArchivalJobRepository(Protocol):
    """Protocol for archival job repository operations."""
    
    async def save_job(self, job: ArchivalJob) -> ArchivalJob:
        """Save an archival job."""
        ...
    
    async def get_job_by_id(self, job_id: UUID) -> Optional[ArchivalJob]:
        """Get job by ID."""
        ...
    
    async def get_jobs_by_rule(self, rule_id: UUID) -> List[ArchivalJob]:
        """Get jobs by rule ID."""
        ...
    
    async def get_jobs_by_status(self, status: ArchivalStatus) -> List[ArchivalJob]:
        """Get jobs by status."""
        ...
    
    async def get_failed_jobs_for_retry(self) -> List[ArchivalJob]:
        """Get failed jobs that can be retried."""
        ...
    
    async def update_job_status(self, job_id: UUID, status: ArchivalStatus) -> None:
        """Update job status."""
        ...
    
    async def update_job_progress(
        self, 
        job_id: UUID, 
        events_processed: int,
        events_archived: int,
        events_skipped: int
    ) -> None:
        """Update job progress statistics."""
        ...
    
    async def complete_job(
        self, 
        job_id: UUID,
        archive_id: Optional[UUID],
        final_stats: Dict[str, Any]
    ) -> None:
        """Mark job as completed with final statistics."""
        ...
    
    async def fail_job(self, job_id: UUID, error_message: str) -> None:
        """Mark job as failed with error message."""
        ...
    
    async def delete_old_jobs(self, older_than_days: int) -> int:
        """Delete job records older than specified days."""
        ...


class EventArchivalRepositoryImpl:
    """Implementation of event archival repository."""
    
    def __init__(self, db_repository: DatabaseRepository, schema: str = "admin"):
        self._db = db_repository
        self._schema = schema
    
    async def save_archive(self, archive: EventArchive) -> EventArchive:
        """Save an event archive record."""
        query = """
        INSERT INTO {schema}.event_archives (
            id, archive_name, description, policy, storage_type, storage_location,
            created_at, archived_at, restored_at, status, event_count, size_bytes,
            compression_ratio, checksum, events_from, events_to, context_ids,
            event_types, retention_days, auto_delete_after_days, created_by_user_id,
            tags
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16,
            $17, $18, $19, $20, $21, $22
        )
        ON CONFLICT (id) DO UPDATE SET
            archive_name = EXCLUDED.archive_name,
            description = EXCLUDED.description,
            status = EXCLUDED.status,
            archived_at = EXCLUDED.archived_at,
            restored_at = EXCLUDED.restored_at,
            event_count = EXCLUDED.event_count,
            size_bytes = EXCLUDED.size_bytes,
            compression_ratio = EXCLUDED.compression_ratio,
            checksum = EXCLUDED.checksum,
            tags = EXCLUDED.tags
        """
        
        await self._db.execute(
            query.format(schema=self._schema),
            archive.id,
            archive.archive_name,
            archive.description,
            archive.policy.value,
            archive.storage_type.value,
            archive.storage_location,
            archive.created_at,
            archive.archived_at,
            archive.restored_at,
            archive.status.value,
            archive.event_count,
            archive.size_bytes,
            archive.compression_ratio,
            archive.checksum,
            archive.events_from,
            archive.events_to,
            archive.context_ids,
            archive.event_types,
            archive.retention_days,
            archive.auto_delete_after_days,
            archive.created_by_user_id,
            archive.tags
        )
        
        return archive
    
    async def get_archive_by_id(self, archive_id: UUID) -> Optional[EventArchive]:
        """Get archive by ID."""
        query = """
        SELECT * FROM {schema}.event_archives WHERE id = $1
        """
        
        row = await self._db.fetchrow(query.format(schema=self._schema), archive_id)
        if not row:
            return None
        
        return self._row_to_archive(row)
    
    async def get_archives_by_status(self, status: ArchivalStatus) -> List[EventArchive]:
        """Get archives by status."""
        query = """
        SELECT * FROM {schema}.event_archives 
        WHERE status = $1 
        ORDER BY created_at DESC
        """
        
        rows = await self._db.fetch(query.format(schema=self._schema), status.value)
        return [self._row_to_archive(row) for row in rows]
    
    async def get_archives_by_date_range(
        self, 
        from_date: datetime, 
        to_date: datetime
    ) -> List[EventArchive]:
        """Get archives within date range."""
        query = """
        SELECT * FROM {schema}.event_archives 
        WHERE created_at >= $1 AND created_at <= $2 
        ORDER BY created_at DESC
        """
        
        rows = await self._db.fetch(query.format(schema=self._schema), from_date, to_date)
        return [self._row_to_archive(row) for row in rows]
    
    async def get_expired_archives(self) -> List[EventArchive]:
        """Get archives that have exceeded their retention period."""
        query = """
        SELECT * FROM {schema}.event_archives 
        WHERE auto_delete_after_days IS NOT NULL 
        AND archived_at IS NOT NULL
        AND archived_at + INTERVAL '1 day' * auto_delete_after_days < NOW()
        AND status != 'deleted'
        ORDER BY archived_at ASC
        """
        
        rows = await self._db.fetch(query.format(schema=self._schema))
        return [self._row_to_archive(row) for row in rows]
    
    async def update_archive_status(self, archive_id: UUID, status: ArchivalStatus) -> None:
        """Update archive status."""
        query = """
        UPDATE {schema}.event_archives 
        SET status = $2, 
            archived_at = CASE WHEN $2 = 'completed' THEN NOW() ELSE archived_at END,
            restored_at = CASE WHEN $2 = 'restored' THEN NOW() ELSE restored_at END
        WHERE id = $1
        """
        
        await self._db.execute(
            query.format(schema=self._schema), archive_id, status.value)
    
    async def delete_archive(self, archive_id: UUID) -> None:
        """Delete archive record."""
        query = "DELETE FROM {schema}.event_archives WHERE id = $1"
        await self._db.execute(
            query.format(schema=self._schema), archive_id)
    
    async def get_storage_statistics(self) -> Dict[str, Any]:
        """Get archival storage statistics."""
        query = """
        SELECT 
            COUNT(*) as total_archives,
            SUM(event_count) as total_archived_events,
            SUM(size_bytes) as total_storage_bytes,
            AVG(compression_ratio) as avg_compression_ratio,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_archives,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_archives,
            MIN(events_from) as oldest_archived_date,
            MAX(events_to) as newest_archived_date
        FROM {schema}.event_archives
        """
        
        row = await self._db.fetchrow(query.format(schema=self._schema))
        return dict(row) if row else {}
    
    def _row_to_archive(self, row: Dict[str, Any]) -> EventArchive:
        """Convert database row to EventArchive entity."""
        return EventArchive(
            id=row['id'],
            archive_name=row['archive_name'],
            description=row['description'],
            policy=ArchivalPolicy(row['policy']),
            storage_type=row['storage_type'],
            storage_location=row['storage_location'],
            created_at=row['created_at'],
            archived_at=row['archived_at'],
            restored_at=row['restored_at'],
            status=ArchivalStatus(row['status']),
            event_count=row['event_count'],
            size_bytes=row['size_bytes'],
            compression_ratio=row['compression_ratio'],
            checksum=row['checksum'],
            events_from=row['events_from'],
            events_to=row['events_to'],
            context_ids=row['context_ids'] or [],
            event_types=row['event_types'] or [],
            retention_days=row['retention_days'],
            auto_delete_after_days=row['auto_delete_after_days'],
            created_by_user_id=row['created_by_user_id'],
            tags=row['tags'] or {}
        )


class ArchivalRuleRepositoryImpl:
    """Implementation of archival rule repository."""
    
    def __init__(self, db_repository: DatabaseRepository, schema: str = "admin"):
        self._db = db_repository
        self._schema = schema
    
    async def save_rule(self, rule: ArchivalRule) -> ArchivalRule:
        """Save an archival rule."""
        query = """
        INSERT INTO {schema}.archival_rules (
            id, name, description, policy, storage_type, is_enabled,
            archive_after_days, max_table_size_gb, max_event_count,
            event_types_include, event_types_exclude, context_ids_include,
            context_ids_exclude, schedule_cron, next_run_at, last_run_at,
            storage_location_template, compression_enabled, encryption_enabled,
            retention_days, auto_delete_after_days, created_at, updated_at,
            created_by_user_id
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
            $16, $17, $18, $19, $20, $21, $22, $23, $24
        )
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            is_enabled = EXCLUDED.is_enabled,
            archive_after_days = EXCLUDED.archive_after_days,
            max_table_size_gb = EXCLUDED.max_table_size_gb,
            max_event_count = EXCLUDED.max_event_count,
            schedule_cron = EXCLUDED.schedule_cron,
            next_run_at = EXCLUDED.next_run_at,
            storage_location_template = EXCLUDED.storage_location_template,
            compression_enabled = EXCLUDED.compression_enabled,
            encryption_enabled = EXCLUDED.encryption_enabled,
            retention_days = EXCLUDED.retention_days,
            auto_delete_after_days = EXCLUDED.auto_delete_after_days,
            updated_at = EXCLUDED.updated_at
        """
        
        await self._db.execute(
            query.format(schema=self._schema),
            rule.id, rule.name, rule.description, rule.policy.value,
            rule.storage_type.value, rule.is_enabled, rule.archive_after_days,
            rule.max_table_size_gb, rule.max_event_count, rule.event_types_include,
            rule.event_types_exclude, rule.context_ids_include, rule.context_ids_exclude,
            rule.schedule_cron, rule.next_run_at, rule.last_run_at,
            rule.storage_location_template, rule.compression_enabled,
            rule.encryption_enabled, rule.retention_days, rule.auto_delete_after_days,
            rule.created_at, rule.updated_at, rule.created_by_user_id
        )
        
        return rule
    
    async def get_rule_by_id(self, rule_id: UUID) -> Optional[ArchivalRule]:
        """Get rule by ID."""
        query = "SELECT * FROM {schema}.archival_rules WHERE id = $1"
        row = await self._db.fetchrow(query.format(schema=self._schema), rule_id)
        return self._row_to_rule(row) if row else None
    
    async def get_enabled_rules(self) -> List[ArchivalRule]:
        """Get all enabled archival rules."""
        query = """
        SELECT * FROM {schema}.archival_rules 
        WHERE is_enabled = true 
        ORDER BY created_at ASC
        """
        rows = await self._db.fetch(query.format(schema=self._schema))
        return [self._row_to_rule(row) for row in rows]
    
    async def get_rules_due_for_execution(self) -> List[ArchivalRule]:
        """Get rules that are due for execution."""
        query = """
        SELECT * FROM {schema}.archival_rules 
        WHERE is_enabled = true 
        AND (next_run_at IS NULL OR next_run_at <= NOW())
        ORDER BY next_run_at ASC NULLS FIRST
        """
        rows = await self._db.fetch(query.format(schema=self._schema))
        return [self._row_to_rule(row) for row in rows]
    
    async def update_rule_last_run(self, rule_id: UUID, last_run_at: datetime) -> None:
        """Update rule's last run timestamp."""
        query = "UPDATE {schema}.archival_rules SET last_run_at = $2 WHERE id = $1"
        await self._db.execute(
            query.format(schema=self._schema), rule_id, last_run_at)
    
    async def update_rule_next_run(self, rule_id: UUID, next_run_at: datetime) -> None:
        """Update rule's next run timestamp."""
        query = "UPDATE {schema}.archival_rules SET next_run_at = $2 WHERE id = $1"
        await self._db.execute(
            query.format(schema=self._schema), rule_id, next_run_at)
    
    async def delete_rule(self, rule_id: UUID) -> None:
        """Delete archival rule."""
        query = "DELETE FROM {schema}.archival_rules WHERE id = $1"
        await self._db.execute(
            query.format(schema=self._schema), rule_id)
    
    def _row_to_rule(self, row: Dict[str, Any]) -> ArchivalRule:
        """Convert database row to ArchivalRule entity."""
        return ArchivalRule(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            policy=ArchivalPolicy(row['policy']),
            storage_type=row['storage_type'],
            is_enabled=row['is_enabled'],
            archive_after_days=row['archive_after_days'],
            max_table_size_gb=row['max_table_size_gb'],
            max_event_count=row['max_event_count'],
            event_types_include=row['event_types_include'] or [],
            event_types_exclude=row['event_types_exclude'] or [],
            context_ids_include=row['context_ids_include'] or [],
            context_ids_exclude=row['context_ids_exclude'] or [],
            schedule_cron=row['schedule_cron'],
            next_run_at=row['next_run_at'],
            last_run_at=row['last_run_at'],
            storage_location_template=row['storage_location_template'],
            compression_enabled=row['compression_enabled'],
            encryption_enabled=row['encryption_enabled'],
            retention_days=row['retention_days'],
            auto_delete_after_days=row['auto_delete_after_days'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            created_by_user_id=row['created_by_user_id']
        )


class ArchivalJobRepositoryImpl:
    """Implementation of archival job repository."""
    
    def __init__(self, db_repository: DatabaseRepository, schema: str = "admin"):
        self._db = db_repository
        self._schema = schema
    
    async def save_job(self, job: ArchivalJob) -> ArchivalJob:
        """Save an archival job."""
        query = """
        INSERT INTO {schema}.archival_jobs (
            id, rule_id, archive_id, status, started_at, completed_at,
            events_processed, events_archived, events_skipped,
            processing_time_seconds, throughput_events_per_second,
            storage_location, compressed_size_bytes, uncompressed_size_bytes,
            error_message, retry_count, max_retries, created_at, updated_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
            $16, $17, $18, $19
        )
        ON CONFLICT (id) DO UPDATE SET
            archive_id = EXCLUDED.archive_id,
            status = EXCLUDED.status,
            started_at = EXCLUDED.started_at,
            completed_at = EXCLUDED.completed_at,
            events_processed = EXCLUDED.events_processed,
            events_archived = EXCLUDED.events_archived,
            events_skipped = EXCLUDED.events_skipped,
            processing_time_seconds = EXCLUDED.processing_time_seconds,
            throughput_events_per_second = EXCLUDED.throughput_events_per_second,
            storage_location = EXCLUDED.storage_location,
            compressed_size_bytes = EXCLUDED.compressed_size_bytes,
            uncompressed_size_bytes = EXCLUDED.uncompressed_size_bytes,
            error_message = EXCLUDED.error_message,
            retry_count = EXCLUDED.retry_count,
            updated_at = EXCLUDED.updated_at
        """
        
        await self._db.execute(
            query.format(schema=self._schema),
            job.id, job.rule_id, job.archive_id, job.status.value,
            job.started_at, job.completed_at, job.events_processed,
            job.events_archived, job.events_skipped, job.processing_time_seconds,
            job.throughput_events_per_second, job.storage_location,
            job.compressed_size_bytes, job.uncompressed_size_bytes,
            job.error_message, job.retry_count, job.max_retries,
            job.created_at, job.updated_at
        )
        
        return job
    
    async def get_job_by_id(self, job_id: UUID) -> Optional[ArchivalJob]:
        """Get job by ID."""
        query = "SELECT * FROM {schema}.archival_jobs WHERE id = $1"
        row = await self._db.fetchrow(query.format(schema=self._schema), job_id)
        return self._row_to_job(row) if row else None
    
    async def get_jobs_by_rule(self, rule_id: UUID) -> List[ArchivalJob]:
        """Get jobs by rule ID."""
        query = """
        SELECT * FROM {schema}.archival_jobs 
        WHERE rule_id = $1 
        ORDER BY created_at DESC
        """
        rows = await self._db.fetch(query.format(schema=self._schema), rule_id)
        return [self._row_to_job(row) for row in rows]
    
    async def get_jobs_by_status(self, status: ArchivalStatus) -> List[ArchivalJob]:
        """Get jobs by status."""
        query = """
        SELECT * FROM {schema}.archival_jobs 
        WHERE status = $1 
        ORDER BY created_at DESC
        """
        rows = await self._db.fetch(query.format(schema=self._schema), status.value)
        return [self._row_to_job(row) for row in rows]
    
    async def get_failed_jobs_for_retry(self) -> List[ArchivalJob]:
        """Get failed jobs that can be retried."""
        query = """
        SELECT * FROM {schema}.archival_jobs 
        WHERE status = 'failed' 
        AND retry_count < max_retries
        ORDER BY created_at ASC
        """
        rows = await self._db.fetch(query.format(schema=self._schema))
        return [self._row_to_job(row) for row in rows]
    
    async def update_job_status(self, job_id: UUID, status: ArchivalStatus) -> None:
        """Update job status."""
        query = """
        UPDATE {schema}.archival_jobs 
        SET status = $2, 
            started_at = CASE WHEN $2 = 'in_progress' AND started_at IS NULL THEN NOW() ELSE started_at END,
            completed_at = CASE WHEN $2 IN ('completed', 'failed') THEN NOW() ELSE completed_at END,
            updated_at = NOW()
        WHERE id = $1
        """
        await self._db.execute(
            query.format(schema=self._schema), job_id, status.value)
    
    async def update_job_progress(
        self, 
        job_id: UUID, 
        events_processed: int,
        events_archived: int,
        events_skipped: int
    ) -> None:
        """Update job progress statistics."""
        query = """
        UPDATE {schema}.archival_jobs 
        SET events_processed = $2, 
            events_archived = $3, 
            events_skipped = $4,
            updated_at = NOW()
        WHERE id = $1
        """
        await self._db.execute(
            query.format(schema=self._schema), job_id, events_processed, events_archived, events_skipped)
    
    async def complete_job(
        self, 
        job_id: UUID,
        archive_id: Optional[UUID],
        final_stats: Dict[str, Any]
    ) -> None:
        """Mark job as completed with final statistics."""
        query = """
        UPDATE {schema}.archival_jobs 
        SET status = 'completed',
            archive_id = $2,
            completed_at = NOW(),
            processing_time_seconds = $3,
            throughput_events_per_second = $4,
            storage_location = $5,
            compressed_size_bytes = $6,
            uncompressed_size_bytes = $7,
            updated_at = NOW()
        WHERE id = $1
        """
        
        await self._db.execute(
            query.format(schema=self._schema),
            job_id,
            archive_id,
            final_stats.get('processing_time_seconds'),
            final_stats.get('throughput_events_per_second'),
            final_stats.get('storage_location'),
            final_stats.get('compressed_size_bytes'),
            final_stats.get('uncompressed_size_bytes')
        )
    
    async def fail_job(self, job_id: UUID, error_message: str) -> None:
        """Mark job as failed with error message."""
        query = """
        UPDATE {schema}.archival_jobs 
        SET status = 'failed',
            error_message = $2,
            completed_at = NOW(),
            retry_count = retry_count + 1,
            updated_at = NOW()
        WHERE id = $1
        """
        await self._db.execute(
            query.format(schema=self._schema), job_id, error_message)
    
    async def delete_old_jobs(self, older_than_days: int) -> int:
        """Delete job records older than specified days."""
        query = """
        DELETE FROM {schema}.archival_jobs 
        WHERE created_at < NOW() - INTERVAL '%s days'
        """ % older_than_days
        
        result = await self._db.execute(query)
        return result
    
    def _row_to_job(self, row: Dict[str, Any]) -> ArchivalJob:
        """Convert database row to ArchivalJob entity."""
        return ArchivalJob(
            id=row['id'],
            rule_id=row['rule_id'],
            archive_id=row['archive_id'],
            status=ArchivalStatus(row['status']),
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            events_processed=row['events_processed'] or 0,
            events_archived=row['events_archived'] or 0,
            events_skipped=row['events_skipped'] or 0,
            processing_time_seconds=row['processing_time_seconds'],
            throughput_events_per_second=row['throughput_events_per_second'],
            storage_location=row['storage_location'],
            compressed_size_bytes=row['compressed_size_bytes'],
            uncompressed_size_bytes=row['uncompressed_size_bytes'],
            error_message=row['error_message'],
            retry_count=row['retry_count'] or 0,
            max_retries=row['max_retries'] or 3,
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )