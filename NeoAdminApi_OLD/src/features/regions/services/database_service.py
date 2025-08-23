"""
Service layer for database connection management.
"""

from typing import Optional, Dict, Any
from src.common.utils import utc_now, format_iso8601
import asyncio
import logging
import time
import asyncpg

from src.common.config import settings
from src.common.services.base import BaseService
from src.common.exceptions import NotFoundError
from src.common.utils.encryption import decrypt_password, is_encrypted
from ..models.domain import DatabaseConnection, HealthStatus
from ..models.request import DatabaseConnectionFilter, HealthCheckRequest
from ..models.response import (
    DatabaseConnectionResponse,
    DatabaseConnectionListResponse,
    DatabaseHealthInfo,
    DatabaseListSummary
)
from ..repositories.database import DatabaseConnectionRepository

logger = logging.getLogger(__name__)


class DatabaseConnectionService(BaseService[DatabaseConnection]):
    """Service for managing database connections."""
    
    def __init__(self):
        self.repository = DatabaseConnectionRepository()
    
    async def list_connections(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[DatabaseConnectionFilter] = None
    ) -> DatabaseConnectionListResponse:
        """
        List database connections with pagination and filtering.
        """
        # Apply filters if provided
        filter_params = {}
        if filters:
            filter_params = {
                'region_id': filters.region_id,
                'connection_type': filters.connection_type.value if filters.connection_type else None,
                'is_active': filters.is_active,
                'is_healthy': filters.is_healthy,
                'tags': filters.tags,
                'search': filters.search
            }
        
        # Get connections and total count
        connections, total_count = await self.repository.list_connections(
            page=page,
            page_size=page_size,
            **filter_params
        )
        
        # Get summary statistics
        summary_stats = await self.repository.get_summary_stats()
        
        # Convert to response models
        response_items = []
        for conn in connections:
            health_status = self._determine_health_status(conn)
            uptime_percentage = self._calculate_uptime_percentage(conn)
            
            response_items.append(DatabaseConnectionResponse(
                id=conn.id,
                connection_name=conn.connection_name,
                connection_type=conn.connection_type,
                host=conn.host,
                port=conn.port,
                database_name=conn.database_name,
                ssl_mode=conn.ssl_mode,
                region_id=conn.region_id,
                region_name=conn.region_name or "Unknown",
                region_display_name=conn.region_display_name or "Unknown",
                region_active=conn.region_active or False,
                pool_config={
                    'min_size': conn.pool_min_size,
                    'max_size': conn.pool_max_size,
                    'timeout_seconds': conn.pool_timeout_seconds,
                    'recycle_seconds': conn.pool_recycle_seconds,
                    'pre_ping': conn.pool_pre_ping
                },
                health=DatabaseHealthInfo(
                    status=health_status,
                    is_active=conn.is_active,
                    is_healthy=conn.is_healthy,
                    last_check=conn.last_health_check,
                    consecutive_failures=conn.consecutive_failures,
                    max_failures=conn.max_consecutive_failures,
                    uptime_percentage=uptime_percentage,
                    response_time_ms=conn.metadata.get('last_response_time_ms') if conn.metadata else None
                ),
                metadata=conn.metadata or {},
                tags=conn.tags,
                created_at=conn.created_at,
                updated_at=conn.updated_at
            ))
        
        # Create pagination metadata using base service method
        pagination = self.create_pagination_metadata(page, page_size, total_count)
        
        return DatabaseConnectionListResponse(
            items=response_items,
            pagination=pagination
        )
    
    async def get_connection(self, connection_id: str) -> DatabaseConnectionResponse:
        """Get a single database connection."""
        conn = await self.repository.get_connection(connection_id)
        
        if not conn:
            raise NotFoundError(
                resource="Database connection",
                identifier=connection_id
            )
        
        health_status = self._determine_health_status(conn)
        uptime_percentage = self._calculate_uptime_percentage(conn)
        
        return DatabaseConnectionResponse(
            id=conn.id,
            connection_name=conn.connection_name,
            connection_type=conn.connection_type,
            host=conn.host,
            port=conn.port,
            database_name=conn.database_name,
            ssl_mode=conn.ssl_mode,
            region_id=conn.region_id,
            region_name=conn.region_name or "Unknown",
            region_display_name=conn.region_display_name or "Unknown",
            region_active=conn.region_active or False,
            pool_config={
                'min_size': conn.pool_min_size,
                'max_size': conn.pool_max_size,
                'timeout_seconds': conn.pool_timeout_seconds,
                'recycle_seconds': conn.pool_recycle_seconds,
                'pre_ping': conn.pool_pre_ping
            },
            health=DatabaseHealthInfo(
                status=health_status,
                is_active=conn.is_active,
                is_healthy=conn.is_healthy,
                last_check=conn.last_health_check,
                consecutive_failures=conn.consecutive_failures,
                max_failures=conn.max_consecutive_failures,
                uptime_percentage=uptime_percentage,
                response_time_ms=conn.metadata.get('last_response_time_ms') if conn.metadata else None
            ),
            metadata=conn.metadata or {},
            tags=conn.tags,
            created_at=conn.created_at,
            updated_at=conn.updated_at
        )
    
    async def perform_health_checks(
        self,
        request: HealthCheckRequest
    ) -> Dict[str, Any]:
        """
        Perform health checks on database connections.
        """
        # Get connections to check
        connections = await self.repository.get_connections_for_health_check(
            connection_ids=request.connection_ids,
            force_check=request.force_check
        )
        
        if not connections:
            return {
                'checked': 0,
                'healthy': 0,
                'unhealthy': 0,
                'results': []
            }
        
        # Perform health checks concurrently
        tasks = [
            self._check_connection_health(conn, request.timeout_seconds)
            for conn in connections
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        checked = 0
        healthy = 0
        unhealthy = 0
        check_results = []
        
        for conn, result in zip(connections, results):
            if isinstance(result, Exception):
                # Health check failed with exception
                is_healthy = False
                response_time = None
                error = str(result)
            else:
                is_healthy = result['is_healthy']
                response_time = result.get('response_time_ms')
                error = result.get('error')
            
            # Update health status in database
            await self.repository.update_health_status(
                conn.id,
                is_healthy,
                response_time
            )
            
            checked += 1
            if is_healthy:
                healthy += 1
            else:
                unhealthy += 1
            
            check_results.append({
                'connection_id': conn.id,
                'connection_name': conn.connection_name,
                'database_name': conn.database_name,
                'is_healthy': is_healthy,
                'response_time_ms': response_time,
                'error': error,
                'checked_at': format_iso8601(utc_now())
            })
        
        return {
            'checked': checked,
            'healthy': healthy,
            'unhealthy': unhealthy,
            'results': check_results
        }
    
    async def _check_connection_health(
        self,
        connection: DatabaseConnection,
        timeout: int
    ) -> Dict[str, Any]:
        """
        Check health of a single database connection.
        """
        start_time = time.time()
        
        try:
            # Get encrypted password from connection
            encrypted_password = connection.encrypted_password or ''
            
            # Try to decrypt password if encrypted
            if is_encrypted(encrypted_password):
                try:
                    password = decrypt_password(encrypted_password)
                except Exception as decrypt_error:
                    # If decryption fails, use default password for development
                    logger.warning(f"Failed to decrypt password for {connection.connection_name}: {decrypt_error}")
                    password = 'postgres'  # Development default
            else:
                # Use the value as-is if not encrypted, or default to 'postgres'
                password = encrypted_password if encrypted_password else 'postgres'
            
            # Build connection string
            dsn = f"postgresql://{connection.username}:{password}@{connection.host}:{connection.port}/{connection.database_name}"
            
            if connection.ssl_mode and connection.ssl_mode != 'disable':
                dsn += f"?sslmode={connection.ssl_mode}"
            
            # Try to connect and execute a simple query
            conn = await asyncio.wait_for(
                asyncpg.connect(dsn),
                timeout=timeout
            )
            
            try:
                # Execute a simple health check query
                result = await asyncio.wait_for(
                    conn.fetchval("SELECT 1"),
                    timeout=timeout
                )
                
                response_time_ms = (time.time() - start_time) * 1000
                
                return {
                    'is_healthy': result == 1,
                    'response_time_ms': round(response_time_ms, 2),
                    'error': None
                }
            finally:
                await conn.close()
                
        except asyncio.TimeoutError:
            return {
                'is_healthy': False,
                'response_time_ms': None,
                'error': f"Connection timeout after {timeout} seconds"
            }
        except Exception as e:
            return {
                'is_healthy': False,
                'response_time_ms': None,
                'error': str(e)
            }
    
    def _determine_health_status(self, connection: DatabaseConnection) -> HealthStatus:
        """
        Determine the health status of a connection.
        """
        if not connection.is_active:
            return HealthStatus.UNHEALTHY
        
        if not connection.is_healthy:
            return HealthStatus.UNHEALTHY
        
        if connection.consecutive_failures > 0:
            if connection.consecutive_failures >= connection.max_consecutive_failures:
                return HealthStatus.UNHEALTHY
            else:
                return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    def _calculate_uptime_percentage(self, connection: DatabaseConnection) -> Optional[float]:
        """
        Calculate uptime percentage based on available data.
        
        This is a simplified calculation based on:
        - Current health status
        - Consecutive failures
        - Health history in metadata (if available)
        
        For accurate uptime tracking, implement a health_check_history table.
        """
        if not connection.last_health_check:
            return None
        
        # If we have health history in metadata, use it
        if connection.metadata and 'health_history' in connection.metadata:
            history = connection.metadata['health_history']
            if isinstance(history, list) and len(history) > 0:
                total_checks = len(history)
                successful_checks = sum(1 for h in history if h.get('is_healthy', False))
                return round((successful_checks / total_checks) * 100, 2)
        
        # Otherwise, use a simple calculation based on consecutive failures
        # This is an estimation assuming regular health checks
        if connection.consecutive_failures == 0 and connection.is_healthy:
            # Currently healthy with no recent failures
            return 99.9  # Assume very high uptime if no failures
        elif connection.consecutive_failures > 0:
            # Estimate based on consecutive failures
            # Assume we keep track of last 100 checks
            max_tracked_checks = 100
            # Each failure reduces uptime percentage
            failure_impact = (connection.consecutive_failures / max_tracked_checks) * 100
            uptime = max(0.0, 100.0 - failure_impact)
            return round(uptime, 2)
        else:
            # Currently unhealthy, but check if it was recently healthy
            if connection.consecutive_failures < 5:
                # Recently became unhealthy
                return 95.0
            else:
                # Has been unhealthy for a while
                return 50.0