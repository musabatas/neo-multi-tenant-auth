"""Get action status query for platform actions infrastructure.

This module handles ONLY action status retrieval operations following maximum separation architecture.
Single responsibility: Retrieve comprehensive action status including configuration, execution history, and analytics.

Pure application layer - no infrastructure concerns.
Uses protocols for dependency injection and clean architecture compliance.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime

from ...core.protocols import ActionRepository
from ...core.entities import Action, ActionExecution
from ...core.value_objects import ActionId
from ...core.exceptions import ActionExecutionFailed
from neo_commons.core.value_objects import UserId
from neo_commons.utils import utc_now


@dataclass
class GetActionStatusData:
    """Data required to retrieve action status.
    
    Contains all the parameters needed for comprehensive action status operations.
    Separates data from business logic following CQRS patterns.
    """
    action_id: ActionId
    include_configuration: bool = True
    include_executions: bool = True
    include_statistics: bool = True
    include_analytics: bool = False
    execution_limit: int = 50
    execution_offset: int = 0
    analytics_time_range_hours: int = 24
    
    
@dataclass
class GetActionStatusResult:
    """Result of action status retrieval operation.
    
    Contains comprehensive action status data for monitoring and analysis.
    Provides structured feedback about the action's current state and performance.
    """
    action_id: ActionId
    action_found: bool
    action_configuration: Optional[Action] = None
    current_status: Optional[str] = None
    execution_summary: Optional[Dict[str, Any]] = None
    recent_executions: Optional[List[Dict[str, Any]]] = None
    performance_statistics: Optional[Dict[str, Any]] = None
    performance_analytics: Optional[Dict[str, Any]] = None
    retrieval_time_ms: Optional[int] = None
    error_message: Optional[str] = None


class GetActionStatusQuery:
    """Query to retrieve comprehensive action status information.
    
    Single responsibility: Orchestrate the retrieval of complete action status including
    configuration, execution history, performance statistics, and analytics data.
    Provides comprehensive action monitoring for operational visibility and debugging.
    
    Following enterprise query pattern with protocol-based dependencies.
    Pure application logic - delegates infrastructure concerns to protocols.
    """
    
    def __init__(
        self,
        action_repository: ActionRepository
    ):
        """Initialize get action status query with required dependencies.
        
        Args:
            action_repository: Protocol for action data access operations
        """
        self._action_repository = action_repository
    
    async def execute(self, data: GetActionStatusData) -> GetActionStatusResult:
        """Execute action status retrieval query.
        
        Orchestrates the complete action status retrieval process:
        1. Retrieve action configuration from repository
        2. Validate action exists
        3. Optionally retrieve execution summary and recent executions
        4. Optionally retrieve performance statistics
        5. Optionally retrieve performance analytics
        6. Return comprehensive action status data
        
        Args:
            data: Action status retrieval configuration data
            
        Returns:
            GetActionStatusResult with comprehensive action status information
        """
        start_time = utc_now()
        
        try:
            # 1. Retrieve action configuration from repository
            action = await self._action_repository.get_action_by_id(
                action_id=data.action_id,
                include_metadata=data.include_configuration
            )
            
            if not action:
                return GetActionStatusResult(
                    action_id=data.action_id,
                    action_found=False,
                    error_message=f"Action with ID {data.action_id.value} not found"
                )
            
            # 2. Initialize result with basic action data
            result_data = {
                "action_id": data.action_id,
                "action_found": True,
                "action_configuration": action if data.include_configuration else None,
                "current_status": self._determine_current_status(action)
            }
            
            # 3. Optionally retrieve execution summary and recent executions
            if data.include_executions:
                execution_data = await self._get_execution_data(data)
                result_data["execution_summary"] = execution_data["summary"]
                result_data["recent_executions"] = execution_data["recent_executions"]
            
            # 4. Optionally retrieve performance statistics
            if data.include_statistics:
                performance_statistics = await self._get_performance_statistics(data)
                result_data["performance_statistics"] = performance_statistics
            
            # 5. Optionally retrieve performance analytics
            if data.include_analytics:
                performance_analytics = await self._get_performance_analytics(data)
                result_data["performance_analytics"] = performance_analytics
            
            # 6. Calculate retrieval metrics
            end_time = utc_now()
            retrieval_time_ms = int((end_time - start_time).total_seconds() * 1000)
            result_data["retrieval_time_ms"] = retrieval_time_ms
            
            return GetActionStatusResult(**result_data)
            
        except Exception as e:
            # Calculate retrieval time for failed operations
            end_time = utc_now()
            retrieval_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return GetActionStatusResult(
                action_id=data.action_id,
                action_found=False,
                retrieval_time_ms=retrieval_time_ms,
                error_message=f"Failed to retrieve action status {data.action_id.value}: {str(e)}"
            )
    
    async def execute_simple(self, action_id: ActionId) -> GetActionStatusResult:
        """Execute simple action status retrieval with basic information.
        
        Convenience method for basic action status with minimal data.
        Useful for quick action health checks and basic status information.
        
        Args:
            action_id: ID of the action to retrieve status for
            
        Returns:
            GetActionStatusResult with basic action status information
        """
        data = GetActionStatusData(
            action_id=action_id,
            include_configuration=True,
            include_executions=False,
            include_statistics=False,
            include_analytics=False
        )
        return await self.execute(data)
    
    async def execute_with_executions(self, action_id: ActionId) -> GetActionStatusResult:
        """Execute action status retrieval with execution history.
        
        Convenience method for retrieving action status with execution data.
        Useful for debugging action performance and execution patterns.
        
        Args:
            action_id: ID of the action to retrieve status for
            
        Returns:
            GetActionStatusResult with action status and execution history
        """
        data = GetActionStatusData(
            action_id=action_id,
            include_configuration=True,
            include_executions=True,
            include_statistics=True,
            include_analytics=False
        )
        return await self.execute(data)
    
    async def execute_comprehensive(self, action_id: ActionId) -> GetActionStatusResult:
        """Execute comprehensive action status retrieval with all available data.
        
        Convenience method for complete action analysis including all
        configuration, executions, statistics, and analytics data.
        
        Args:
            action_id: ID of the action to retrieve status for
            
        Returns:
            GetActionStatusResult with complete action status information
        """
        data = GetActionStatusData(
            action_id=action_id,
            include_configuration=True,
            include_executions=True,
            include_statistics=True,
            include_analytics=True,
            analytics_time_range_hours=168  # 7 days for comprehensive analysis
        )
        return await self.execute(data)
    
    async def execute_batch(
        self,
        action_ids: List[ActionId],
        include_executions: bool = False
    ) -> List[GetActionStatusResult]:
        """Execute batch action status retrieval for multiple actions.
        
        Retrieves status for multiple actions efficiently while maintaining
        individual result tracking. Uses parallel processing for performance.
        
        Args:
            action_ids: List of action IDs to retrieve status for
            include_executions: Whether to include execution data
            
        Returns:
            List of action status results for each action
        """
        import asyncio
        
        # Create status retrieval tasks for parallel execution
        status_tasks = [
            self.execute(GetActionStatusData(
                action_id=action_id,
                include_configuration=True,
                include_executions=include_executions,
                include_statistics=include_executions,
                include_analytics=False
            ))
            for action_id in action_ids
        ]
        
        # Execute all status retrievals in parallel
        results = await asyncio.gather(*status_tasks, return_exceptions=True)
        
        # Convert exceptions to failed results
        status_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                status_results.append(
                    GetActionStatusResult(
                        action_id=action_ids[i],
                        action_found=False,
                        retrieval_time_ms=0,
                        error_message=str(result)
                    )
                )
            else:
                status_results.append(result)
        
        return status_results
    
    def _determine_current_status(self, action: Action) -> str:
        """Determine the current status of an action based on its configuration.
        
        Analyzes action configuration to determine operational status.
        
        Args:
            action: Action to analyze
            
        Returns:
            String representation of current action status
        """
        try:
            # Check if action is active and properly configured
            if not hasattr(action, 'is_enabled') or not action.is_enabled:
                return "inactive"
            
            if not hasattr(action, 'configuration') or not action.configuration:
                return "misconfigured"
            
            # Check for recent execution activity (would need execution data)
            return "active"
            
        except Exception:
            return "unknown"
    
    async def _get_execution_data(self, data: GetActionStatusData) -> Dict[str, Any]:
        """Get execution summary and recent execution data for an action.
        
        Retrieves comprehensive execution information including summary statistics
        and recent execution details for monitoring and debugging.
        
        Args:
            data: Action status data configuration
            
        Returns:
            Dictionary with execution summary and recent executions
        """
        try:
            # Get recent executions with pagination
            executions_result = await self._action_repository.get_executions_by_action(
                action_id=data.action_id,
                status_filter=None,  # All statuses
                from_time=None,
                to_time=None,
                limit=data.execution_limit,
                offset=data.execution_offset
            )
            
            executions = executions_result.get("executions", [])
            total_count = executions_result.get("total_count", 0)
            
            # Create execution summary
            execution_summary = {
                "total_executions": total_count,
                "recent_executions_count": len(executions),
                "has_more_executions": executions_result.get("has_more", False),
                "last_execution_time": self._get_last_execution_time(executions),
                "status_distribution": self._calculate_status_distribution(executions)
            }
            
            # Format recent executions for response
            recent_executions = [
                {
                    "execution_id": str(execution.get("id", "")),
                    "status": execution.get("status", "unknown"),
                    "started_at": execution.get("started_at"),
                    "completed_at": execution.get("completed_at"),
                    "duration_ms": execution.get("duration_ms"),
                    "error_message": execution.get("error_message")
                }
                for execution in executions
            ]
            
            return {
                "summary": execution_summary,
                "recent_executions": recent_executions
            }
            
        except Exception:
            return {
                "summary": {"error": "Could not retrieve execution data"},
                "recent_executions": []
            }
    
    async def _get_performance_statistics(self, data: GetActionStatusData) -> Dict[str, Any]:
        """Get performance statistics for an action.
        
        Retrieves comprehensive performance metrics including success rates,
        execution times, and operational statistics.
        
        Args:
            data: Action status data configuration
            
        Returns:
            Dictionary with performance statistics
        """
        try:
            # Get action statistics from repository
            statistics = await self._action_repository.get_action_statistics(
                action_id=data.action_id,
                handler_type=None,
                time_range_hours=data.analytics_time_range_hours,
                include_performance_metrics=True
            )
            
            return statistics
            
        except Exception:
            return {"error": "Could not retrieve performance statistics"}
    
    async def _get_performance_analytics(self, data: GetActionStatusData) -> Dict[str, Any]:
        """Get detailed performance analytics for an action.
        
        Retrieves advanced analytics including trends, capacity utilization,
        and performance analysis over time.
        
        Args:
            data: Action status data configuration
            
        Returns:
            Dictionary with performance analytics
        """
        try:
            # Get execution analytics from repository
            analytics = await self._action_repository.get_execution_analytics(
                action_id=data.action_id,
                event_type=None,
                time_range_hours=data.analytics_time_range_hours,
                group_by="hour"
            )
            
            return analytics
            
        except Exception:
            return {"error": "Could not retrieve performance analytics"}
    
    def _get_last_execution_time(self, executions: List[Dict[str, Any]]) -> Optional[datetime]:
        """Get the timestamp of the most recent execution.
        
        Args:
            executions: List of execution records
            
        Returns:
            Datetime of last execution or None if no executions
        """
        if not executions:
            return None
        
        try:
            # Executions should be ordered by time descending
            return executions[0].get("started_at")
        except (IndexError, KeyError):
            return None
    
    def _calculate_status_distribution(self, executions: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate the distribution of execution statuses.
        
        Args:
            executions: List of execution records
            
        Returns:
            Dictionary with status counts
        """
        status_counts = {}
        
        for execution in executions:
            status = execution.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return status_counts