"""Action executed handler for platform actions infrastructure.

This module handles ONLY action executed notifications following maximum separation architecture.
Single responsibility: Handle post-execution action processing, result analysis, and follow-up actions.

Pure application layer - no infrastructure concerns.
Uses protocols for dependency injection and clean architecture compliance.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

from ...core.entities import Action, DomainEvent
from ...core.value_objects import ActionId, EventId, ActionResult
from .....core.value_objects import UserId
from ...core.events import ActionExecuted
from ...core.protocols import ActionRepository, EventRepository, NotificationService
from ...core.exceptions import ActionExecutionFailed
from .....utils import utc_now


class ResultAnalysisType(Enum):
    """Types of action execution result analysis."""
    SUCCESS_METRICS = "success_metrics"
    FAILURE_ANALYSIS = "failure_analysis"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    RESOURCE_USAGE = "resource_usage"
    SIDE_EFFECTS = "side_effects"


@dataclass
class ActionExecutedHandlerResult:
    """Result of action executed handling."""
    success: bool
    processed_at: datetime
    result_analyzed: bool
    follow_up_actions: List[ActionId]
    notifications_sent: List[str]
    metrics_recorded: Dict[str, Any]
    analysis_results: Dict[str, Any]
    errors: List[str]
    processing_duration_ms: float
    
    message: str = "Action executed processing completed"


class ActionExecutedHandler:
    """Handler for action executed notifications.
    
    Processes actions after they have been successfully executed,
    analyzing results, triggering follow-up actions, and recording metrics.
    
    Single responsibility: ONLY post-execution action processing logic.
    Uses dependency injection through protocols for clean architecture.
    """
    
    def __init__(self, 
                 action_repository: ActionRepository,
                 event_repository: EventRepository,
                 notification_service: Optional[NotificationService] = None):
        """Initialize handler with required dependencies.
        
        Args:
            action_repository: Repository for action persistence operations
            event_repository: Repository for event operations
            notification_service: Optional service for sending notifications
        """
        self._action_repository = action_repository
        self._event_repository = event_repository
        self._notification_service = notification_service
    
    async def handle(self, action_executed: ActionExecuted) -> ActionExecutedHandlerResult:
        """Handle action executed notification.
        
        Processes the executed action by:
        1. Analyzing execution results and performance
        2. Recording execution metrics and outcomes
        3. Triggering follow-up actions based on results
        4. Sending notifications if configured
        5. Updating action status and metadata
        
        Args:
            action_executed: Action executed notification
            
        Returns:
            ActionExecutedHandlerResult with processing outcome
            
        Raises:
            ActionExecutionFailed: If handler processing fails
        """
        start_time = utc_now()
        result = ActionExecutedHandlerResult(
            success=True,
            processed_at=start_time,
            result_analyzed=False,
            follow_up_actions=[],
            notifications_sent=[],
            metrics_recorded={},
            analysis_results={},
            errors=[],
            processing_duration_ms=0.0
        )
        
        try:
            # Retrieve the executed action
            action = await self._get_executed_action(action_executed.action_id, result)
            if not action:
                result.success = False
                result.message = f"Action {action_executed.action_id} not found for post-execution processing"
                return result
            
            # Analyze execution results
            await self._analyze_execution_results(action, action_executed, result)
            
            # Record execution metrics
            await self._record_execution_metrics(action, action_executed, result)
            
            # Process follow-up actions based on results
            await self._process_result_based_actions(action, action_executed, result)
            
            # Send execution notifications if configured
            await self._send_execution_notifications(action, action_executed, result)
            
            # Update action status and metadata
            await self._update_action_status(action, action_executed, result)
            
            # Calculate processing duration
            end_time = utc_now()
            result.processing_duration_ms = (end_time - start_time).total_seconds() * 1000
            
            result.message = f"Action {action_executed.action_id} execution processing completed successfully"
            return result
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Handler processing failed: {str(e)}")
            result.message = f"Action execution processing failed: {str(e)}"
            
            # Calculate duration even on failure
            end_time = utc_now()
            result.processing_duration_ms = (end_time - start_time).total_seconds() * 1000
            
            # Log error but don't re-raise to avoid breaking event flow
            await self._log_handler_error(action_executed.action_id, str(e))
            
            return result
    
    async def _get_executed_action(self, action_id: ActionId, result: ActionExecutedHandlerResult) -> Optional[Action]:
        """Retrieve the executed action from repository.
        
        Args:
            action_id: ID of the action to retrieve
            result: Result object to update with errors
            
        Returns:
            Action if found, None otherwise
        """
        try:
            return await self._action_repository.get_by_id(action_id)
        except Exception as e:
            result.errors.append(f"Failed to retrieve action {action_id}: {str(e)}")
            return None
    
    async def _analyze_execution_results(self, action: Action, action_executed: ActionExecuted, 
                                       result: ActionExecutedHandlerResult):
        """Analyze the execution results and extract insights.
        
        Args:
            action: The executed action
            action_executed: Execution notification
            result: Result object to update with analysis
        """
        try:
            analysis = {}
            
            # Basic execution analysis
            analysis["execution_successful"] = action_executed.result.success
            analysis["execution_duration_ms"] = action_executed.execution_duration_ms
            analysis["result_data_size"] = len(str(action_executed.result.data)) if action_executed.result.data else 0
            
            # Success metrics analysis
            if action_executed.result.success:
                analysis.update(await self._analyze_success_metrics(action, action_executed))
            else:
                analysis.update(await self._analyze_failure_details(action, action_executed))
            
            # Performance analysis
            analysis.update(await self._analyze_performance_metrics(action, action_executed))
            
            # Resource usage analysis
            analysis.update(await self._analyze_resource_usage(action, action_executed))
            
            # Side effects analysis
            analysis.update(await self._analyze_side_effects(action, action_executed))
            
            result.analysis_results = analysis
            result.result_analyzed = True
            
        except Exception as e:
            result.errors.append(f"Failed to analyze execution results: {str(e)}")
            result.result_analyzed = False
    
    async def _analyze_success_metrics(self, action: Action, action_executed: ActionExecuted) -> Dict[str, Any]:
        """Analyze metrics for successful execution.
        
        Args:
            action: The executed action
            action_executed: Execution notification
            
        Returns:
            Dictionary of success metrics
        """
        metrics = {
            "analysis_type": ResultAnalysisType.SUCCESS_METRICS.value,
            "result_quality_score": self._calculate_result_quality_score(action_executed.result),
            "expected_vs_actual": self._compare_expected_vs_actual(action, action_executed.result),
            "completeness_score": self._calculate_completeness_score(action_executed.result),
            "data_consistency": self._check_data_consistency(action_executed.result)
        }
        
        # Check if execution time is within expected bounds
        if hasattr(action, "expected_duration_ms") and action.expected_duration_ms:
            expected_duration = action.expected_duration_ms
            actual_duration = action_executed.execution_duration_ms
            metrics["duration_efficiency"] = min(expected_duration / max(actual_duration, 1), 2.0)
        
        return metrics
    
    async def _analyze_failure_details(self, action: Action, action_executed: ActionExecuted) -> Dict[str, Any]:
        """Analyze details of failed execution.
        
        Args:
            action: The executed action
            action_executed: Execution notification
            
        Returns:
            Dictionary of failure analysis
        """
        analysis = {
            "analysis_type": ResultAnalysisType.FAILURE_ANALYSIS.value,
            "error_message": action_executed.result.error_message,
            "error_code": action_executed.result.error_code,
            "failure_category": self._categorize_failure(action_executed.result),
            "retry_recommended": self._should_recommend_retry(action, action_executed.result),
            "root_cause_indicators": self._identify_root_cause_indicators(action_executed.result)
        }
        
        # Check if this is a recurring failure pattern
        analysis["recurring_failure"] = await self._check_recurring_failure_pattern(action, action_executed)
        
        return analysis
    
    async def _analyze_performance_metrics(self, action: Action, action_executed: ActionExecuted) -> Dict[str, Any]:
        """Analyze performance metrics of the execution.
        
        Args:
            action: The executed action
            action_executed: Execution notification
            
        Returns:
            Dictionary of performance metrics
        """
        metrics = {
            "analysis_type": ResultAnalysisType.PERFORMANCE_ANALYSIS.value,
            "execution_duration_ms": action_executed.execution_duration_ms,
            "performance_rating": self._rate_performance(action, action_executed.execution_duration_ms),
        }
        
        # Memory usage analysis (if available in result data)
        if action_executed.result.data and isinstance(action_executed.result.data, dict):
            result_data = action_executed.result.data
            if "memory_usage_mb" in result_data:
                metrics["memory_usage_mb"] = result_data["memory_usage_mb"]
                metrics["memory_efficiency"] = self._rate_memory_usage(result_data["memory_usage_mb"])
        
        # CPU usage analysis (if available)
        if action_executed.result.metadata and "cpu_time_ms" in action_executed.result.metadata:
            cpu_time = action_executed.result.metadata["cpu_time_ms"]
            metrics["cpu_time_ms"] = cpu_time
            metrics["cpu_efficiency"] = cpu_time / max(action_executed.execution_duration_ms, 1)
        
        return metrics
    
    async def _analyze_resource_usage(self, action: Action, action_executed: ActionExecuted) -> Dict[str, Any]:
        """Analyze resource usage during execution.
        
        Args:
            action: The executed action
            action_executed: Execution notification
            
        Returns:
            Dictionary of resource usage metrics
        """
        usage = {
            "analysis_type": ResultAnalysisType.RESOURCE_USAGE.value,
            "execution_cost_estimate": self._estimate_execution_cost(action, action_executed),
            "resource_efficiency": self._calculate_resource_efficiency(action, action_executed)
        }
        
        # Network resource usage (if available)
        if action_executed.result.metadata and "network_requests" in action_executed.result.metadata:
            usage["network_requests"] = action_executed.result.metadata["network_requests"]
            usage["network_efficiency"] = self._rate_network_usage(action_executed.result.metadata)
        
        # Database resource usage (if available)
        if action_executed.result.metadata and "db_queries" in action_executed.result.metadata:
            usage["database_queries"] = action_executed.result.metadata["db_queries"]
            usage["db_efficiency"] = self._rate_database_usage(action_executed.result.metadata)
        
        return usage
    
    async def _analyze_side_effects(self, action: Action, action_executed: ActionExecuted) -> Dict[str, Any]:
        """Analyze side effects of the action execution.
        
        Args:
            action: The executed action
            action_executed: Execution notification
            
        Returns:
            Dictionary of side effects analysis
        """
        side_effects = {
            "analysis_type": ResultAnalysisType.SIDE_EFFECTS.value,
            "external_calls_made": self._count_external_calls(action_executed.result),
            "data_modifications": self._analyze_data_modifications(action_executed.result),
            "state_changes": self._analyze_state_changes(action_executed.result)
        }
        
        # Check for unexpected side effects
        side_effects["unexpected_effects"] = self._detect_unexpected_side_effects(action, action_executed.result)
        
        return side_effects
    
    async def _record_execution_metrics(self, action: Action, action_executed: ActionExecuted,
                                      result: ActionExecutedHandlerResult):
        """Record metrics about the action execution.
        
        Args:
            action: The executed action
            action_executed: Execution notification
            result: Result object to update with metrics
        """
        try:
            metrics = {
                "action_id": str(action.id),
                "action_type": action.action_type,
                "handler_type": action.handler_type,
                "execution_successful": action_executed.result.success,
                "execution_duration_ms": action_executed.execution_duration_ms,
                "executed_at": action_executed.executed_at.isoformat() if action_executed.executed_at else None,
                "executed_by": str(action_executed.executed_by) if action_executed.executed_by else None,
                "retry_attempt": action_executed.retry_attempt,
                "result_size_bytes": len(str(action_executed.result.data)) if action_executed.result.data else 0,
                "event_id": str(action.event_id) if action.event_id else None
            }
            
            # Add error details if execution failed
            if not action_executed.result.success:
                metrics.update({
                    "error_message": action_executed.result.error_message,
                    "error_code": action_executed.result.error_code,
                    "failure_category": result.analysis_results.get("failure_category", "unknown")
                })
            
            # Add performance metrics
            if "performance_rating" in result.analysis_results:
                metrics["performance_rating"] = result.analysis_results["performance_rating"]
            
            result.metrics_recorded.update(metrics)
            
            # TODO: Send metrics to monitoring system
            # This would integrate with monitoring service when available
            
        except Exception as e:
            result.errors.append(f"Failed to record execution metrics: {str(e)}")
    
    async def _process_result_based_actions(self, action: Action, action_executed: ActionExecuted,
                                          result: ActionExecutedHandlerResult):
        """Process follow-up actions based on execution results.
        
        Args:
            action: The executed action
            action_executed: Execution notification
            result: Result object to update with follow-up actions
        """
        try:
            follow_up_actions = []
            
            if action_executed.result.success:
                follow_up_actions.extend(await self._determine_success_follow_ups(action, action_executed, result))
            else:
                follow_up_actions.extend(await self._determine_failure_follow_ups(action, action_executed, result))
            
            # Create follow-up actions
            for follow_up_spec in follow_up_actions:
                try:
                    action_id = await self._create_follow_up_action(follow_up_spec, action)
                    result.follow_up_actions.append(action_id)
                except Exception as e:
                    result.errors.append(f"Failed to create follow-up action: {str(e)}")
                    
        except Exception as e:
            result.errors.append(f"Failed to process result-based actions: {str(e)}")
    
    async def _determine_success_follow_ups(self, action: Action, action_executed: ActionExecuted,
                                          handler_result: ActionExecutedHandlerResult) -> List[Dict[str, Any]]:
        """Determine follow-up actions for successful execution.
        
        Args:
            action: The executed action
            action_executed: Execution notification
            handler_result: Handler result with analysis
            
        Returns:
            List of follow-up action specifications
        """
        follow_ups = []
        
        # If execution was slow, create performance monitoring action
        if (action_executed.execution_duration_ms > 5000 and 
            handler_result.analysis_results.get("performance_rating", "good") == "poor"):
            follow_ups.append({
                "action_type": "monitor_performance",
                "handler_type": "function",
                "configuration": {
                    "target_action_type": action.action_type,
                    "monitor_duration_minutes": 60,
                    "performance_threshold_ms": action_executed.execution_duration_ms * 0.8
                },
                "description": f"Monitor performance for slow {action.action_type} actions"
            })
        
        # If action had significant side effects, create validation action
        side_effects = handler_result.analysis_results.get("external_calls_made", 0)
        if side_effects > 10:
            follow_ups.append({
                "action_type": "validate_side_effects",
                "handler_type": "function",
                "configuration": {
                    "source_action_id": str(action.id),
                    "validation_timeout_minutes": 15
                },
                "description": f"Validate side effects of action {action.id}"
            })
        
        # If action produced valuable data, create archival action
        result_size = handler_result.analysis_results.get("result_data_size", 0)
        if result_size > 1000000:  # 1MB
            follow_ups.append({
                "action_type": "archive_result_data",
                "handler_type": "function",
                "configuration": {
                    "source_action_id": str(action.id),
                    "compression_enabled": True,
                    "retention_days": 30
                },
                "description": f"Archive large result data from action {action.id}"
            })
        
        return follow_ups
    
    async def _determine_failure_follow_ups(self, action: Action, action_executed: ActionExecuted,
                                          handler_result: ActionExecutedHandlerResult) -> List[Dict[str, Any]]:
        """Determine follow-up actions for failed execution.
        
        Args:
            action: The executed action
            action_executed: Execution notification
            handler_result: Handler result with analysis
            
        Returns:
            List of follow-up action specifications
        """
        follow_ups = []
        
        # If retry is recommended and attempts remain
        if (handler_result.analysis_results.get("retry_recommended", False) and
            action_executed.retry_attempt < action.max_retry_attempts):
            follow_ups.append({
                "action_type": "retry_failed_action",
                "handler_type": "function",
                "configuration": {
                    "original_action_id": str(action.id),
                    "retry_delay_seconds": min(60 * (2 ** action_executed.retry_attempt), 3600),  # Exponential backoff
                    "retry_attempt": action_executed.retry_attempt + 1
                },
                "description": f"Retry failed action {action.id} (attempt {action_executed.retry_attempt + 1})"
            })
        
        # If this is a recurring failure, create analysis action
        if handler_result.analysis_results.get("recurring_failure", False):
            follow_ups.append({
                "action_type": "analyze_recurring_failure",
                "handler_type": "function",
                "configuration": {
                    "action_type": action.action_type,
                    "failure_pattern": handler_result.analysis_results.get("failure_category", "unknown"),
                    "analysis_window_hours": 24
                },
                "description": f"Analyze recurring failures for {action.action_type} actions"
            })
        
        # If failure indicates system issue, create alert action
        failure_category = handler_result.analysis_results.get("failure_category", "")
        if failure_category in ["system_error", "resource_exhaustion", "timeout"]:
            follow_ups.append({
                "action_type": "system_alert",
                "handler_type": "notification",
                "configuration": {
                    "alert_type": "action_system_failure",
                    "severity": "high",
                    "failure_details": {
                        "action_id": str(action.id),
                        "error_message": action_executed.result.error_message,
                        "failure_category": failure_category
                    }
                },
                "description": f"System alert for {failure_category} in action {action.id}"
            })
        
        return follow_ups
    
    async def _create_follow_up_action(self, action_spec: Dict[str, Any], original_action: Action) -> ActionId:
        """Create a follow-up action based on specification.
        
        Args:
            action_spec: Action specification dictionary
            original_action: The original executed action
            
        Returns:
            ActionId of the created follow-up action
        """
        # Create Action entity for the follow-up action
        action = Action.create(
            event_id=original_action.event_id,
            action_type=action_spec["action_type"],
            handler_type=action_spec["handler_type"],
            configuration=action_spec.get("configuration", {}),
            description=action_spec.get("description", ""),
            priority="normal",
            max_retry_attempts=3
        )
        
        # Add reference to original action
        if not action.metadata:
            action.metadata = {}
        action.metadata["triggered_by_action"] = str(original_action.id)
        
        # Save to repository
        saved_action = await self._action_repository.save(action)
        return saved_action.id
    
    async def _send_execution_notifications(self, action: Action, action_executed: ActionExecuted,
                                          result: ActionExecutedHandlerResult):
        """Send notifications about action execution results.
        
        Args:
            action: The executed action
            action_executed: Execution notification
            result: Result object to update with notification results
        """
        if not self._notification_service:
            return
        
        try:
            # Determine notification recipients
            recipients = await self._determine_execution_notification_recipients(action, action_executed, result)
            
            for recipient in recipients:
                try:
                    notification_id = await self._send_execution_notification(
                        recipient, action, action_executed, result
                    )
                    result.notifications_sent.append(notification_id)
                except Exception as e:
                    result.errors.append(f"Failed to send notification to {recipient}: {str(e)}")
                    
        except Exception as e:
            result.errors.append(f"Failed to process execution notifications: {str(e)}")
    
    async def _determine_execution_notification_recipients(self, action: Action, action_executed: ActionExecuted,
                                                         result: ActionExecutedHandlerResult) -> List[str]:
        """Determine who should receive execution notifications.
        
        Args:
            action: The executed action
            action_executed: Execution notification
            result: Handler result
            
        Returns:
            List of notification recipient identifiers
        """
        recipients = []
        
        # Notify executor if specified
        if action_executed.executed_by:
            recipients.append(f"user:{action_executed.executed_by}")
        
        # Notify on failures
        if not action_executed.result.success:
            recipients.append("admin:action_failures")
            
            # Notify on system failures
            if result.analysis_results.get("failure_category") == "system_error":
                recipients.append("ops:system_alerts")
        
        # Notify on performance issues
        if result.analysis_results.get("performance_rating") == "poor":
            recipients.append("ops:performance_alerts")
        
        return recipients
    
    async def _send_execution_notification(self, recipient: str, action: Action, action_executed: ActionExecuted,
                                         result: ActionExecutedHandlerResult) -> str:
        """Send execution notification to specific recipient.
        
        Args:
            recipient: Notification recipient
            action: The executed action
            action_executed: Execution notification
            result: Handler result
            
        Returns:
            Notification ID
        """
        notification_data = {
            "type": "action_executed",
            "action_id": str(action.id),
            "action_type": action.action_type,
            "success": action_executed.result.success,
            "execution_duration_ms": action_executed.execution_duration_ms,
            "executed_at": action_executed.executed_at.isoformat() if action_executed.executed_at else None,
            "performance_rating": result.analysis_results.get("performance_rating", "unknown"),
            "recipient": recipient
        }
        
        if not action_executed.result.success:
            notification_data.update({
                "error_message": action_executed.result.error_message,
                "error_code": action_executed.result.error_code,
                "failure_category": result.analysis_results.get("failure_category", "unknown")
            })
        
        return await self._notification_service.send_notification(
            recipient=recipient,
            notification_type="action_executed",
            data=notification_data
        )
    
    async def _update_action_status(self, action: Action, action_executed: ActionExecuted,
                                  result: ActionExecutedHandlerResult):
        """Update action status and metadata after execution processing.
        
        Args:
            action: The executed action
            action_executed: Execution notification
            result: Processing result
        """
        try:
            metadata_updates = {
                "post_execution_processed_at": utc_now().isoformat(),
                "result_analyzed": result.result_analyzed,
                "follow_up_actions_created": len(result.follow_up_actions),
                "notifications_sent": len(result.notifications_sent),
                "analysis_results": result.analysis_results,
                "execution_metrics": result.metrics_recorded,
                "processing_duration_ms": result.processing_duration_ms
            }
            
            if result.errors:
                metadata_updates["post_execution_errors"] = result.errors
            
            if result.follow_up_actions:
                metadata_updates["follow_up_action_ids"] = [str(action_id) for action_id in result.follow_up_actions]
            
            await self._action_repository.update_metadata(action.id, metadata_updates)
            
        except Exception as e:
            result.errors.append(f"Failed to update action status: {str(e)}")
    
    # Helper methods for analysis
    
    def _calculate_result_quality_score(self, action_result: ActionResult) -> float:
        """Calculate quality score for action result."""
        if not action_result.success:
            return 0.0
        
        score = 1.0
        
        # Reduce score if no data returned
        if not action_result.data:
            score -= 0.2
        
        # Reduce score if errors present even in successful result
        if action_result.error_message:
            score -= 0.3
        
        return max(score, 0.0)
    
    def _compare_expected_vs_actual(self, action: Action, action_result: ActionResult) -> Dict[str, Any]:
        """Compare expected vs actual results."""
        return {
            "has_expected_data": bool(action_result.data),
            "success_as_expected": action_result.success,
            "metadata_complete": bool(action_result.metadata)
        }
    
    def _calculate_completeness_score(self, action_result: ActionResult) -> float:
        """Calculate completeness score for result."""
        score = 0.0
        
        if action_result.success:
            score += 0.4
        if action_result.data:
            score += 0.3
        if action_result.metadata:
            score += 0.2
        if not action_result.error_message:
            score += 0.1
        
        return score
    
    def _check_data_consistency(self, action_result: ActionResult) -> Dict[str, Any]:
        """Check data consistency in result."""
        return {
            "data_present": bool(action_result.data),
            "success_consistent": action_result.success and not action_result.error_message,
            "metadata_consistent": bool(action_result.metadata) if action_result.data else True
        }
    
    def _categorize_failure(self, action_result: ActionResult) -> str:
        """Categorize the type of failure."""
        if not action_result.error_message:
            return "unknown"
        
        error_msg = action_result.error_message.lower()
        
        if "timeout" in error_msg:
            return "timeout"
        elif "permission" in error_msg or "unauthorized" in error_msg:
            return "authorization"
        elif "network" in error_msg or "connection" in error_msg:
            return "network"
        elif "memory" in error_msg or "resource" in error_msg:
            return "resource_exhaustion"
        elif "validation" in error_msg or "invalid" in error_msg:
            return "validation"
        else:
            return "system_error"
    
    def _should_recommend_retry(self, action: Action, action_result: ActionResult) -> bool:
        """Determine if retry is recommended."""
        if not action_result.error_message:
            return False
        
        # Don't retry validation errors
        if self._categorize_failure(action_result) == "validation":
            return False
        
        # Don't retry authorization errors
        if self._categorize_failure(action_result) == "authorization":
            return False
        
        # Retry timeouts and network errors
        failure_category = self._categorize_failure(action_result)
        return failure_category in ["timeout", "network", "system_error"]
    
    def _identify_root_cause_indicators(self, action_result: ActionResult) -> List[str]:
        """Identify potential root cause indicators."""
        indicators = []
        
        if action_result.error_code:
            indicators.append(f"error_code:{action_result.error_code}")
        
        if action_result.error_message:
            error_msg = action_result.error_message.lower()
            if "timeout" in error_msg:
                indicators.append("timeout_occurred")
            if "memory" in error_msg:
                indicators.append("memory_issue")
            if "connection" in error_msg:
                indicators.append("connection_issue")
        
        return indicators
    
    async def _check_recurring_failure_pattern(self, action: Action, action_executed: ActionExecuted) -> bool:
        """Check if this represents a recurring failure pattern."""
        try:
            # Look for similar recent failures
            # This would query the repository for recent failures of the same type
            # For now, return False as placeholder
            return False
        except:
            return False
    
    def _rate_performance(self, action: Action, duration_ms: float) -> str:
        """Rate the performance of action execution."""
        if duration_ms < 1000:  # < 1 second
            return "excellent"
        elif duration_ms < 5000:  # < 5 seconds
            return "good"
        elif duration_ms < 15000:  # < 15 seconds
            return "acceptable"
        elif duration_ms < 60000:  # < 1 minute
            return "slow"
        else:
            return "poor"
    
    def _rate_memory_usage(self, memory_mb: float) -> str:
        """Rate memory usage efficiency."""
        if memory_mb < 50:
            return "excellent"
        elif memory_mb < 200:
            return "good"
        elif memory_mb < 500:
            return "acceptable"
        else:
            return "poor"
    
    def _estimate_execution_cost(self, action: Action, action_executed: ActionExecuted) -> float:
        """Estimate the cost of execution."""
        base_cost = 0.001  # Base cost per action
        duration_cost = action_executed.execution_duration_ms * 0.000001  # Cost per millisecond
        return base_cost + duration_cost
    
    def _calculate_resource_efficiency(self, action: Action, action_executed: ActionExecuted) -> float:
        """Calculate overall resource efficiency score."""
        duration_score = min(5000 / max(action_executed.execution_duration_ms, 1), 1.0)
        return duration_score
    
    def _rate_network_usage(self, metadata: Dict[str, Any]) -> str:
        """Rate network resource usage."""
        requests = metadata.get("network_requests", 0)
        if requests == 0:
            return "none"
        elif requests < 5:
            return "low"
        elif requests < 20:
            return "moderate"
        else:
            return "high"
    
    def _rate_database_usage(self, metadata: Dict[str, Any]) -> str:
        """Rate database resource usage."""
        queries = metadata.get("db_queries", 0)
        if queries == 0:
            return "none"
        elif queries < 10:
            return "low"
        elif queries < 50:
            return "moderate"
        else:
            return "high"
    
    def _count_external_calls(self, action_result: ActionResult) -> int:
        """Count external API calls made during execution."""
        if not action_result.metadata:
            return 0
        return action_result.metadata.get("external_calls", 0)
    
    def _analyze_data_modifications(self, action_result: ActionResult) -> Dict[str, Any]:
        """Analyze data modifications made during execution."""
        if not action_result.metadata:
            return {"modifications": 0, "types": []}
        
        return {
            "modifications": action_result.metadata.get("data_changes", 0),
            "types": action_result.metadata.get("modification_types", [])
        }
    
    def _analyze_state_changes(self, action_result: ActionResult) -> Dict[str, Any]:
        """Analyze state changes caused by execution."""
        if not action_result.metadata:
            return {"state_changes": 0, "affected_entities": []}
        
        return {
            "state_changes": action_result.metadata.get("state_changes", 0),
            "affected_entities": action_result.metadata.get("affected_entities", [])
        }
    
    def _detect_unexpected_side_effects(self, action: Action, action_result: ActionResult) -> List[str]:
        """Detect unexpected side effects from execution."""
        unexpected_effects = []
        
        # Check for unexpected external calls
        if self._count_external_calls(action_result) > 0 and action.action_type not in ["webhook", "notification", "api_call"]:
            unexpected_effects.append("unexpected_external_calls")
        
        # Check for unexpected data modifications
        modifications = self._analyze_data_modifications(action_result)
        if modifications["modifications"] > 0 and action.action_type not in ["create", "update", "delete", "modify"]:
            unexpected_effects.append("unexpected_data_modifications")
        
        return unexpected_effects
    
    async def _log_handler_error(self, action_id: ActionId, error_message: str):
        """Log handler error for monitoring and debugging."""
        error_log = {
            "handler": "ActionExecutedHandler",
            "action_id": str(action_id),
            "error": error_message,
            "timestamp": utc_now().isoformat(),
            "level": "error"
        }
        
        # In a real implementation, this would be sent to a logging service
        print(f"Handler Error: {error_log}")


def create_action_executed_handler(
    action_repository: ActionRepository,
    event_repository: EventRepository,
    notification_service: Optional[NotificationService] = None
) -> ActionExecutedHandler:
    """Factory function to create ActionExecutedHandler instance.
    
    Args:
        action_repository: Repository for action persistence operations
        event_repository: Repository for event operations
        notification_service: Optional service for sending notifications
        
    Returns:
        Configured ActionExecutedHandler instance
    """
    return ActionExecutedHandler(
        action_repository=action_repository,
        event_repository=event_repository,
        notification_service=notification_service
    )