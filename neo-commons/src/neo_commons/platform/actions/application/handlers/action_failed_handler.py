"""Action failed handler for platform actions infrastructure.

This module handles ONLY action failed notifications following maximum separation architecture.
Single responsibility: Handle failed action processing, error analysis, and recovery actions.

Pure application layer - no infrastructure concerns.
Uses protocols for dependency injection and clean architecture compliance.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum

from ...core.entities import Action, DomainEvent
from ...core.value_objects import ActionId, EventId, ActionResult
from .....core.value_objects import UserId
from ...core.events import ActionFailed
from ...core.protocols import ActionRepository, EventRepository, NotificationService
from ...core.exceptions import ActionExecutionFailed
from .....utils import utc_now


class FailureAnalysisType(Enum):
    """Types of action failure analysis."""
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    IMPACT_ASSESSMENT = "impact_assessment"
    RECOVERY_PLANNING = "recovery_planning"
    PATTERN_DETECTION = "pattern_detection"
    ESCALATION_ANALYSIS = "escalation_analysis"


class FailureSeverity(Enum):
    """Action failure severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ActionFailedHandlerResult:
    """Result of action failed handling."""
    success: bool
    processed_at: datetime
    failure_analyzed: bool
    recovery_actions_created: List[ActionId]
    alerts_sent: List[str]
    escalation_triggered: bool
    failure_severity: FailureSeverity
    metrics_recorded: Dict[str, Any]
    analysis_results: Dict[str, Any]
    errors: List[str]
    processing_duration_ms: float
    
    message: str = "Action failed processing completed"


class ActionFailedHandler:
    """Handler for action failed notifications.
    
    Processes actions after they have failed, analyzing failures,
    creating recovery actions, and managing escalation procedures.
    
    Single responsibility: ONLY action failure processing logic.
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
    
    async def handle(self, action_failed: ActionFailed) -> ActionFailedHandlerResult:
        """Handle action failed notification.
        
        Processes the failed action by:
        1. Analyzing failure cause and impact
        2. Recording failure metrics and patterns
        3. Creating recovery actions if applicable
        4. Triggering alerts and escalation procedures
        5. Sending notifications to stakeholders
        6. Updating action status and failure metadata
        
        Args:
            action_failed: Action failed notification
            
        Returns:
            ActionFailedHandlerResult with processing outcome
            
        Raises:
            ActionExecutionFailed: If handler processing fails
        """
        start_time = utc_now()
        result = ActionFailedHandlerResult(
            success=True,
            processed_at=start_time,
            failure_analyzed=False,
            recovery_actions_created=[],
            alerts_sent=[],
            escalation_triggered=False,
            failure_severity=FailureSeverity.LOW,
            metrics_recorded={},
            analysis_results={},
            errors=[],
            processing_duration_ms=0.0
        )
        
        try:
            # Retrieve the failed action
            action = await self._get_failed_action(action_failed.action_id, result)
            if not action:
                result.success = False
                result.message = f"Action {action_failed.action_id} not found for failure processing"
                return result
            
            # Analyze failure cause and severity
            await self._analyze_action_failure(action, action_failed, result)
            
            # Record failure metrics and patterns
            await self._record_failure_metrics(action, action_failed, result)
            
            # Create recovery actions based on failure type
            await self._create_recovery_actions(action, action_failed, result)
            
            # Handle escalation and alerting
            await self._handle_failure_escalation(action, action_failed, result)
            
            # Send failure notifications
            await self._send_failure_notifications(action, action_failed, result)
            
            # Update action status with failure details
            await self._update_action_failure_status(action, action_failed, result)
            
            # Calculate processing duration
            end_time = utc_now()
            result.processing_duration_ms = (end_time - start_time).total_seconds() * 1000
            
            result.message = f"Action {action_failed.action_id} failure processing completed successfully"
            return result
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Handler processing failed: {str(e)}")
            result.message = f"Action failure processing failed: {str(e)}"
            
            # Calculate duration even on failure
            end_time = utc_now()
            result.processing_duration_ms = (end_time - start_time).total_seconds() * 1000
            
            # Log error but don't re-raise to avoid breaking event flow
            await self._log_handler_error(action_failed.action_id, str(e))
            
            return result
    
    async def _get_failed_action(self, action_id: ActionId, result: ActionFailedHandlerResult) -> Optional[Action]:
        """Retrieve the failed action from repository.
        
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
    
    async def _analyze_action_failure(self, action: Action, action_failed: ActionFailed, 
                                    result: ActionFailedHandlerResult):
        """Analyze the action failure to determine cause, impact, and severity.
        
        Args:
            action: The failed action
            action_failed: Failure notification
            result: Result object to update with analysis
        """
        try:
            analysis = {}
            
            # Basic failure analysis
            analysis["failure_reason"] = action_failed.result.error_message
            analysis["failure_code"] = action_failed.result.error_code
            analysis["failed_at"] = action_failed.failed_at.isoformat() if action_failed.failed_at else None
            analysis["attempt_number"] = action_failed.attempt_number
            analysis["total_attempts"] = action.max_retry_attempts
            
            # Root cause analysis
            analysis.update(await self._perform_root_cause_analysis(action, action_failed))
            
            # Impact assessment
            analysis.update(await self._assess_failure_impact(action, action_failed))
            
            # Pattern detection
            analysis.update(await self._detect_failure_patterns(action, action_failed))
            
            # Determine severity
            severity = await self._determine_failure_severity(action, action_failed, analysis)
            result.failure_severity = severity
            analysis["failure_severity"] = severity.value
            
            # Recovery planning
            analysis.update(await self._plan_recovery_strategy(action, action_failed, severity))
            
            result.analysis_results = analysis
            result.failure_analyzed = True
            
        except Exception as e:
            result.errors.append(f"Failed to analyze action failure: {str(e)}")
            result.failure_analyzed = False
    
    async def _perform_root_cause_analysis(self, action: Action, action_failed: ActionFailed) -> Dict[str, Any]:
        """Perform root cause analysis of the failure.
        
        Args:
            action: The failed action
            action_failed: Failure notification
            
        Returns:
            Dictionary of root cause analysis results
        """
        analysis = {
            "analysis_type": FailureAnalysisType.ROOT_CAUSE_ANALYSIS.value
        }
        
        # Categorize failure type
        failure_category = self._categorize_failure_type(action_failed.result)
        analysis["failure_category"] = failure_category
        
        # Identify contributing factors
        analysis["contributing_factors"] = self._identify_contributing_factors(action, action_failed)
        
        # Check for system-wide issues
        analysis["system_wide_issue"] = await self._check_system_wide_issues(action, action_failed)
        
        # Analyze timing patterns
        analysis["timing_factors"] = await self._analyze_timing_factors(action, action_failed)
        
        # Check resource constraints
        analysis["resource_constraints"] = await self._check_resource_constraints(action, action_failed)
        
        return analysis
    
    async def _assess_failure_impact(self, action: Action, action_failed: ActionFailed) -> Dict[str, Any]:
        """Assess the impact of the action failure.
        
        Args:
            action: The failed action
            action_failed: Failure notification
            
        Returns:
            Dictionary of impact assessment results
        """
        analysis = {
            "analysis_type": FailureAnalysisType.IMPACT_ASSESSMENT.value
        }
        
        # Assess business impact
        analysis["business_impact"] = await self._assess_business_impact(action, action_failed)
        
        # Assess technical impact
        analysis["technical_impact"] = await self._assess_technical_impact(action, action_failed)
        
        # Assess user impact
        analysis["user_impact"] = await self._assess_user_impact(action, action_failed)
        
        # Check downstream dependencies
        analysis["downstream_affected"] = await self._check_downstream_dependencies(action)
        
        # Calculate impact score
        analysis["impact_score"] = self._calculate_impact_score(analysis)
        
        return analysis
    
    async def _detect_failure_patterns(self, action: Action, action_failed: ActionFailed) -> Dict[str, Any]:
        """Detect patterns in action failures.
        
        Args:
            action: The failed action
            action_failed: Failure notification
            
        Returns:
            Dictionary of pattern detection results
        """
        analysis = {
            "analysis_type": FailureAnalysisType.PATTERN_DETECTION.value
        }
        
        # Check for similar recent failures
        analysis["similar_failures"] = await self._find_similar_recent_failures(action, action_failed)
        
        # Detect failure cascades
        analysis["failure_cascade"] = await self._detect_failure_cascades(action, action_failed)
        
        # Check temporal patterns
        analysis["temporal_patterns"] = await self._analyze_temporal_failure_patterns(action, action_failed)
        
        # Detect configuration-related patterns
        analysis["config_patterns"] = await self._detect_configuration_patterns(action, action_failed)
        
        return analysis
    
    async def _determine_failure_severity(self, action: Action, action_failed: ActionFailed, 
                                        analysis: Dict[str, Any]) -> FailureSeverity:
        """Determine the severity level of the failure.
        
        Args:
            action: The failed action
            action_failed: Failure notification
            analysis: Failure analysis results
            
        Returns:
            FailureSeverity level
        """
        severity_score = 0
        
        # Factor in failure category
        failure_category = analysis.get("failure_category", "unknown")
        if failure_category in ["system_error", "resource_exhaustion"]:
            severity_score += 3
        elif failure_category in ["timeout", "network_error"]:
            severity_score += 2
        elif failure_category in ["validation_error", "configuration_error"]:
            severity_score += 1
        
        # Factor in business impact
        business_impact = analysis.get("business_impact", {})
        if business_impact.get("critical_process_affected", False):
            severity_score += 3
        elif business_impact.get("important_process_affected", False):
            severity_score += 2
        
        # Factor in user impact
        user_impact = analysis.get("user_impact", {})
        if user_impact.get("users_affected", 0) > 1000:
            severity_score += 3
        elif user_impact.get("users_affected", 0) > 100:
            severity_score += 2
        elif user_impact.get("users_affected", 0) > 0:
            severity_score += 1
        
        # Factor in failure patterns
        if analysis.get("system_wide_issue", False):
            severity_score += 4
        elif analysis.get("failure_cascade", {}).get("cascade_detected", False):
            severity_score += 2
        
        # Factor in retry attempts
        if action_failed.attempt_number >= action.max_retry_attempts:
            severity_score += 1  # Exhausted all retries
        
        # Determine severity based on score
        if severity_score >= 8:
            return FailureSeverity.CRITICAL
        elif severity_score >= 6:
            return FailureSeverity.HIGH
        elif severity_score >= 3:
            return FailureSeverity.MEDIUM
        else:
            return FailureSeverity.LOW
    
    async def _plan_recovery_strategy(self, action: Action, action_failed: ActionFailed, 
                                    severity: FailureSeverity) -> Dict[str, Any]:
        """Plan recovery strategy based on failure analysis.
        
        Args:
            action: The failed action
            action_failed: Failure notification
            severity: Failure severity level
            
        Returns:
            Dictionary of recovery planning results
        """
        analysis = {
            "analysis_type": FailureAnalysisType.RECOVERY_PLANNING.value
        }
        
        # Determine if retry is viable
        analysis["retry_recommended"] = self._should_recommend_retry(action, action_failed)
        
        # Plan alternative approaches
        analysis["alternative_approaches"] = await self._identify_alternative_approaches(action, action_failed)
        
        # Plan compensating actions
        analysis["compensating_actions"] = await self._plan_compensating_actions(action, action_failed)
        
        # Plan rollback actions if needed
        analysis["rollback_actions"] = await self._plan_rollback_actions(action, action_failed)
        
        # Determine recovery urgency
        analysis["recovery_urgency"] = self._determine_recovery_urgency(severity)
        
        return analysis
    
    async def _record_failure_metrics(self, action: Action, action_failed: ActionFailed,
                                    result: ActionFailedHandlerResult):
        """Record metrics about the action failure.
        
        Args:
            action: The failed action
            action_failed: Failure notification
            result: Result object to update with metrics
        """
        try:
            metrics = {
                "action_id": str(action.id),
                "action_type": action.action_type,
                "handler_type": action.handler_type,
                "failure_reason": action_failed.result.error_message,
                "failure_code": action_failed.result.error_code,
                "failed_at": action_failed.failed_at.isoformat() if action_failed.failed_at else None,
                "failed_by": str(action_failed.failed_by) if action_failed.failed_by else None,
                "attempt_number": action_failed.attempt_number,
                "max_attempts": action.max_retry_attempts,
                "exhausted_retries": action_failed.attempt_number >= action.max_retry_attempts,
                "failure_severity": result.failure_severity.value,
                "event_id": str(action.event_id) if action.event_id else None,
                "failure_category": result.analysis_results.get("failure_category", "unknown"),
                "business_impact": result.analysis_results.get("business_impact", {}),
                "system_wide_issue": result.analysis_results.get("system_wide_issue", False)
            }
            
            # Add timing metrics
            if action.created_at and action_failed.failed_at:
                time_to_failure = action_failed.failed_at - action.created_at
                metrics["time_to_failure_seconds"] = time_to_failure.total_seconds()
            
            # Add pattern metrics
            similar_failures = result.analysis_results.get("similar_failures", {})
            if similar_failures:
                metrics["similar_failure_count"] = similar_failures.get("count", 0)
                metrics["failure_pattern_detected"] = similar_failures.get("pattern_detected", False)
            
            result.metrics_recorded.update(metrics)
            
            # TODO: Send metrics to monitoring system
            # This would integrate with monitoring service when available
            
        except Exception as e:
            result.errors.append(f"Failed to record failure metrics: {str(e)}")
    
    async def _create_recovery_actions(self, action: Action, action_failed: ActionFailed,
                                     result: ActionFailedHandlerResult):
        """Create recovery actions based on failure analysis.
        
        Args:
            action: The failed action
            action_failed: Failure notification
            result: Result object to update with recovery actions
        """
        try:
            recovery_specs = []
            
            # Create retry action if recommended and attempts remain
            if (result.analysis_results.get("retry_recommended", False) and
                action_failed.attempt_number < action.max_retry_attempts):
                recovery_specs.append(await self._create_retry_action_spec(action, action_failed, result))
            
            # Create compensating actions
            compensating_actions = result.analysis_results.get("compensating_actions", [])
            for compensation_spec in compensating_actions:
                recovery_specs.append(compensation_spec)
            
            # Create rollback actions if needed
            rollback_actions = result.analysis_results.get("rollback_actions", [])
            for rollback_spec in rollback_actions:
                recovery_specs.append(rollback_spec)
            
            # Create alternative approach actions
            alternative_approaches = result.analysis_results.get("alternative_approaches", [])
            for alternative_spec in alternative_approaches:
                recovery_specs.append(alternative_spec)
            
            # Execute recovery action creation
            for recovery_spec in recovery_specs:
                try:
                    recovery_action_id = await self._create_recovery_action(recovery_spec, action)
                    result.recovery_actions_created.append(recovery_action_id)
                except Exception as e:
                    result.errors.append(f"Failed to create recovery action: {str(e)}")
                    
        except Exception as e:
            result.errors.append(f"Failed to create recovery actions: {str(e)}")
    
    async def _create_retry_action_spec(self, action: Action, action_failed: ActionFailed,
                                      result: ActionFailedHandlerResult) -> Dict[str, Any]:
        """Create specification for retry action.
        
        Args:
            action: The failed action
            action_failed: Failure notification
            result: Handler result
            
        Returns:
            Dictionary specifying retry action
        """
        # Calculate retry delay (exponential backoff with jitter)
        base_delay = 60  # 1 minute base
        retry_delay = min(base_delay * (2 ** (action_failed.attempt_number - 1)), 1800)  # Max 30 minutes
        jitter = retry_delay * 0.1  # 10% jitter
        
        return {
            "action_type": "retry_failed_action",
            "handler_type": "function",
            "configuration": {
                "original_action_id": str(action.id),
                "retry_attempt": action_failed.attempt_number + 1,
                "retry_delay_seconds": retry_delay + jitter,
                "retry_reason": result.analysis_results.get("failure_category", "unknown"),
                "original_configuration": action.configuration
            },
            "description": f"Retry failed action {action.id} (attempt {action_failed.attempt_number + 1})",
            "priority": action.priority,  # Maintain original priority
            "scheduled_for": utc_now().replace(second=utc_now().second + int(retry_delay + jitter))
        }
    
    async def _create_recovery_action(self, action_spec: Dict[str, Any], failed_action: Action) -> ActionId:
        """Create a recovery action based on specification.
        
        Args:
            action_spec: Action specification dictionary
            failed_action: The original failed action
            
        Returns:
            ActionId of the created recovery action
        """
        # Create Action entity for the recovery action
        recovery_action = Action.create(
            event_id=failed_action.event_id,
            action_type=action_spec["action_type"],
            handler_type=action_spec["handler_type"],
            configuration=action_spec.get("configuration", {}),
            description=action_spec.get("description", ""),
            priority=action_spec.get("priority", "normal"),
            max_retry_attempts=action_spec.get("max_retry_attempts", 3)
        )
        
        # Add reference to failed action
        if not recovery_action.metadata:
            recovery_action.metadata = {}
        recovery_action.metadata.update({
            "recovery_for_action": str(failed_action.id),
            "recovery_type": action_spec["action_type"],
            "created_by_handler": "ActionFailedHandler"
        })
        
        # Schedule action if specified
        if "scheduled_for" in action_spec:
            recovery_action.scheduled_for = action_spec["scheduled_for"]
        
        # Save to repository
        saved_action = await self._action_repository.save(recovery_action)
        return saved_action.id
    
    async def _handle_failure_escalation(self, action: Action, action_failed: ActionFailed,
                                       result: ActionFailedHandlerResult):
        """Handle escalation procedures for the failure.
        
        Args:
            action: The failed action
            action_failed: Failure notification
            result: Result object to update with escalation results
        """
        try:
            # Determine if escalation is needed
            escalation_needed = self._should_escalate_failure(action, action_failed, result)
            
            if escalation_needed:
                # Create escalation alerts
                alert_specs = await self._create_escalation_alerts(action, action_failed, result)
                
                for alert_spec in alert_specs:
                    try:
                        alert_id = await self._send_escalation_alert(alert_spec)
                        result.alerts_sent.append(alert_id)
                        result.escalation_triggered = True
                    except Exception as e:
                        result.errors.append(f"Failed to send escalation alert: {str(e)}")
                        
        except Exception as e:
            result.errors.append(f"Failed to handle failure escalation: {str(e)}")
    
    def _should_escalate_failure(self, action: Action, action_failed: ActionFailed,
                               result: ActionFailedHandlerResult) -> bool:
        """Determine if failure should be escalated.
        
        Args:
            action: The failed action
            action_failed: Failure notification
            result: Handler result
            
        Returns:
            True if escalation is needed
        """
        # Always escalate critical failures
        if result.failure_severity == FailureSeverity.CRITICAL:
            return True
        
        # Escalate high severity failures during business hours
        if result.failure_severity == FailureSeverity.HIGH:
            current_hour = utc_now().hour
            business_hours = 9 <= current_hour <= 17  # 9 AM to 5 PM UTC
            if business_hours:
                return True
        
        # Escalate system-wide issues
        if result.analysis_results.get("system_wide_issue", False):
            return True
        
        # Escalate if all retries exhausted
        if action_failed.attempt_number >= action.max_retry_attempts:
            return True
        
        # Escalate if part of failure cascade
        if result.analysis_results.get("failure_cascade", {}).get("cascade_detected", False):
            return True
        
        return False
    
    async def _create_escalation_alerts(self, action: Action, action_failed: ActionFailed,
                                      result: ActionFailedHandlerResult) -> List[Dict[str, Any]]:
        """Create escalation alert specifications.
        
        Args:
            action: The failed action
            action_failed: Failure notification
            result: Handler result
            
        Returns:
            List of alert specifications
        """
        alerts = []
        
        # Primary escalation alert
        alerts.append({
            "alert_type": "action_failure_escalation",
            "severity": result.failure_severity.value,
            "recipients": await self._determine_escalation_recipients(action, action_failed, result),
            "title": f"{result.failure_severity.value.title()} Action Failure: {action.action_type}",
            "message": self._create_escalation_message(action, action_failed, result),
            "metadata": {
                "action_id": str(action.id),
                "failure_category": result.analysis_results.get("failure_category", "unknown"),
                "system_wide": result.analysis_results.get("system_wide_issue", False),
                "business_impact": result.analysis_results.get("business_impact", {}),
                "recovery_actions": len(result.recovery_actions_created)
            }
        })
        
        # System-wide issue alert
        if result.analysis_results.get("system_wide_issue", False):
            alerts.append({
                "alert_type": "system_wide_issue",
                "severity": "critical",
                "recipients": ["ops:system_alerts", "admin:critical_issues"],
                "title": "System-Wide Issue Detected",
                "message": f"Multiple action failures detected. Root cause: {result.analysis_results.get('failure_category', 'unknown')}",
                "metadata": {
                    "trigger_action_id": str(action.id),
                    "affected_systems": result.analysis_results.get("system_wide_issue", {}),
                }
            })
        
        return alerts
    
    async def _determine_escalation_recipients(self, action: Action, action_failed: ActionFailed,
                                             result: ActionFailedHandlerResult) -> List[str]:
        """Determine recipients for escalation alerts.
        
        Args:
            action: The failed action
            action_failed: Failure notification
            result: Handler result
            
        Returns:
            List of recipient identifiers
        """
        recipients = []
        
        # Always notify operations team for escalated failures
        recipients.append("ops:escalations")
        
        # Notify based on severity
        if result.failure_severity == FailureSeverity.CRITICAL:
            recipients.extend(["admin:critical_failures", "ops:oncall"])
        elif result.failure_severity == FailureSeverity.HIGH:
            recipients.append("admin:high_priority_failures")
        
        # Notify based on action type
        if action.action_type in ["payment", "billing", "financial"]:
            recipients.append("finance:system_alerts")
        elif action.action_type in ["user_auth", "security", "authentication"]:
            recipients.append("security:alerts")
        
        # Notify action owner if specified
        if action_failed.failed_by:
            recipients.append(f"user:{action_failed.failed_by}")
        
        return list(set(recipients))  # Remove duplicates
    
    def _create_escalation_message(self, action: Action, action_failed: ActionFailed,
                                 result: ActionFailedHandlerResult) -> str:
        """Create escalation alert message.
        
        Args:
            action: The failed action
            action_failed: Failure notification
            result: Handler result
            
        Returns:
            Formatted alert message
        """
        message_parts = [
            f"Action Failure Escalation - {result.failure_severity.value.title()} Severity",
            f"",
            f"Action Details:",
            f"  - ID: {action.id}",
            f"  - Type: {action.action_type}",
            f"  - Handler: {action.handler_type}",
            f"  - Attempt: {action_failed.attempt_number}/{action.max_retry_attempts}",
            f"",
            f"Failure Details:",
            f"  - Category: {result.analysis_results.get('failure_category', 'unknown')}",
            f"  - Reason: {action_failed.result.error_message}",
            f"  - Failed At: {action_failed.failed_at.isoformat() if action_failed.failed_at else 'Unknown'}",
            f"",
            f"Impact Assessment:",
            f"  - Business Impact: {result.analysis_results.get('business_impact', {}).get('level', 'unknown')}",
            f"  - Users Affected: {result.analysis_results.get('user_impact', {}).get('users_affected', 0)}",
            f"  - System Wide: {'Yes' if result.analysis_results.get('system_wide_issue', False) else 'No'}",
            f"",
            f"Recovery Actions:",
            f"  - Actions Created: {len(result.recovery_actions_created)}",
            f"  - Retry Recommended: {'Yes' if result.analysis_results.get('retry_recommended', False) else 'No'}",
            f"  - Recovery Urgency: {result.analysis_results.get('recovery_urgency', 'normal')}"
        ]
        
        return "\n".join(message_parts)
    
    async def _send_escalation_alert(self, alert_spec: Dict[str, Any]) -> str:
        """Send escalation alert.
        
        Args:
            alert_spec: Alert specification
            
        Returns:
            Alert ID
        """
        if not self._notification_service:
            return "no_notification_service"
        
        # Send to each recipient
        alert_ids = []
        for recipient in alert_spec["recipients"]:
            alert_id = await self._notification_service.send_notification(
                recipient=recipient,
                notification_type=alert_spec["alert_type"],
                data={
                    "title": alert_spec["title"],
                    "message": alert_spec["message"],
                    "severity": alert_spec["severity"],
                    "metadata": alert_spec["metadata"]
                }
            )
            alert_ids.append(alert_id)
        
        return f"alerts:{','.join(alert_ids)}"
    
    async def _send_failure_notifications(self, action: Action, action_failed: ActionFailed,
                                        result: ActionFailedHandlerResult):
        """Send notifications about action failure.
        
        Args:
            action: The failed action
            action_failed: Failure notification
            result: Result object to update with notification results
        """
        if not self._notification_service:
            return
        
        # Regular failure notifications (non-escalation)
        if not result.escalation_triggered:
            try:
                recipients = await self._determine_failure_notification_recipients(action, action_failed, result)
                
                for recipient in recipients:
                    try:
                        notification_id = await self._send_failure_notification(
                            recipient, action, action_failed, result
                        )
                        # Note: Not adding to alerts_sent as these are regular notifications
                    except Exception as e:
                        result.errors.append(f"Failed to send notification to {recipient}: {str(e)}")
                        
            except Exception as e:
                result.errors.append(f"Failed to process failure notifications: {str(e)}")
    
    async def _determine_failure_notification_recipients(self, action: Action, action_failed: ActionFailed,
                                                       result: ActionFailedHandlerResult) -> List[str]:
        """Determine recipients for regular failure notifications.
        
        Args:
            action: The failed action
            action_failed: Failure notification
            result: Handler result
            
        Returns:
            List of recipient identifiers
        """
        recipients = []
        
        # Notify action owner
        if action_failed.failed_by:
            recipients.append(f"user:{action_failed.failed_by}")
        
        # Notify based on failure patterns
        if result.analysis_results.get("similar_failures", {}).get("pattern_detected", False):
            recipients.append("ops:pattern_alerts")
        
        # Notify on medium severity (high and critical handled by escalation)
        if result.failure_severity == FailureSeverity.MEDIUM:
            recipients.append("ops:medium_priority_failures")
        
        return recipients
    
    async def _send_failure_notification(self, recipient: str, action: Action, action_failed: ActionFailed,
                                       result: ActionFailedHandlerResult) -> str:
        """Send failure notification to specific recipient.
        
        Args:
            recipient: Notification recipient
            action: The failed action
            action_failed: Failure notification
            result: Handler result
            
        Returns:
            Notification ID
        """
        notification_data = {
            "type": "action_failed",
            "action_id": str(action.id),
            "action_type": action.action_type,
            "failure_reason": action_failed.result.error_message,
            "failure_severity": result.failure_severity.value,
            "failed_at": action_failed.failed_at.isoformat() if action_failed.failed_at else None,
            "attempt_number": action_failed.attempt_number,
            "max_attempts": action.max_retry_attempts,
            "recovery_actions_created": len(result.recovery_actions_created),
            "escalation_triggered": result.escalation_triggered,
            "recipient": recipient
        }
        
        return await self._notification_service.send_notification(
            recipient=recipient,
            notification_type="action_failed",
            data=notification_data
        )
    
    async def _update_action_failure_status(self, action: Action, action_failed: ActionFailed,
                                          result: ActionFailedHandlerResult):
        """Update action status and metadata after failure processing.
        
        Args:
            action: The failed action
            action_failed: Failure notification
            result: Processing result
        """
        try:
            metadata_updates = {
                "failure_processed_at": utc_now().isoformat(),
                "failure_analyzed": result.failure_analyzed,
                "failure_severity": result.failure_severity.value,
                "recovery_actions_created": len(result.recovery_actions_created),
                "escalation_triggered": result.escalation_triggered,
                "alerts_sent": len(result.alerts_sent),
                "analysis_results": result.analysis_results,
                "failure_metrics": result.metrics_recorded,
                "processing_duration_ms": result.processing_duration_ms
            }
            
            if result.errors:
                metadata_updates["failure_processing_errors"] = result.errors
            
            if result.recovery_actions_created:
                metadata_updates["recovery_action_ids"] = [str(action_id) for action_id in result.recovery_actions_created]
            
            await self._action_repository.update_metadata(action.id, metadata_updates)
            
        except Exception as e:
            result.errors.append(f"Failed to update action failure status: {str(e)}")
    
    # Helper methods for failure analysis
    
    def _categorize_failure_type(self, action_result: ActionResult) -> str:
        """Categorize the type of failure based on error details."""
        if not action_result.error_message:
            return "unknown"
        
        error_msg = action_result.error_message.lower()
        
        # System-level errors
        if "system" in error_msg or "internal" in error_msg:
            return "system_error"
        elif "timeout" in error_msg:
            return "timeout"
        elif "memory" in error_msg or "resource" in error_msg:
            return "resource_exhaustion"
        elif "network" in error_msg or "connection" in error_msg:
            return "network_error"
        elif "database" in error_msg or "db" in error_msg:
            return "database_error"
        
        # Application-level errors
        elif "validation" in error_msg or "invalid" in error_msg:
            return "validation_error"
        elif "permission" in error_msg or "unauthorized" in error_msg:
            return "authorization_error"
        elif "configuration" in error_msg or "config" in error_msg:
            return "configuration_error"
        elif "business" in error_msg or "rule" in error_msg:
            return "business_logic_error"
        
        # External service errors
        elif "service" in error_msg and "unavailable" in error_msg:
            return "external_service_error"
        elif "api" in error_msg:
            return "api_error"
        
        return "application_error"
    
    def _identify_contributing_factors(self, action: Action, action_failed: ActionFailed) -> List[str]:
        """Identify factors that may have contributed to the failure."""
        factors = []
        
        # Time-based factors
        failure_hour = action_failed.failed_at.hour if action_failed.failed_at else None
        if failure_hour is not None:
            if 2 <= failure_hour <= 4:  # Early morning maintenance window
                factors.append("maintenance_window_activity")
            elif 9 <= failure_hour <= 11 or 14 <= failure_hour <= 16:  # Peak business hours
                factors.append("high_traffic_period")
        
        # Retry-related factors
        if action_failed.attempt_number > 1:
            factors.append("previous_retry_attempts")
        
        # Configuration factors
        if action.configuration and len(str(action.configuration)) > 1000:
            factors.append("complex_configuration")
        
        # Priority factors
        if action.priority == "high":
            factors.append("high_priority_action")
        
        return factors
    
    async def _check_system_wide_issues(self, action: Action, action_failed: ActionFailed) -> bool:
        """Check if this failure is part of a system-wide issue."""
        try:
            # This would query for similar recent failures across the system
            # For now, return False as placeholder
            return False
        except:
            return False
    
    async def _analyze_timing_factors(self, action: Action, action_failed: ActionFailed) -> Dict[str, Any]:
        """Analyze timing-related factors in the failure."""
        factors = {}
        
        if action_failed.failed_at:
            factors["failure_hour"] = action_failed.failed_at.hour
            factors["failure_day_of_week"] = action_failed.failed_at.weekday()
            factors["failure_month"] = action_failed.failed_at.month
        
        # Calculate time from creation to failure
        if action.created_at and action_failed.failed_at:
            time_to_failure = action_failed.failed_at - action.created_at
            factors["time_to_failure_seconds"] = time_to_failure.total_seconds()
            
            if time_to_failure.total_seconds() < 10:
                factors["immediate_failure"] = True
            elif time_to_failure.total_seconds() > 3600:  # 1 hour
                factors["delayed_failure"] = True
        
        return factors
    
    async def _check_resource_constraints(self, action: Action, action_failed: ActionFailed) -> Dict[str, Any]:
        """Check for resource constraint indicators."""
        constraints = {}
        
        if action_failed.result.error_message:
            error_msg = action_failed.result.error_message.lower()
            
            constraints["memory_constraint"] = "memory" in error_msg or "oom" in error_msg
            constraints["cpu_constraint"] = "cpu" in error_msg or "timeout" in error_msg
            constraints["disk_constraint"] = "disk" in error_msg or "space" in error_msg
            constraints["network_constraint"] = "network" in error_msg or "bandwidth" in error_msg
            constraints["database_constraint"] = "connection" in error_msg and ("pool" in error_msg or "limit" in error_msg)
        
        return constraints
    
    async def _assess_business_impact(self, action: Action, action_failed: ActionFailed) -> Dict[str, Any]:
        """Assess the business impact of the failure."""
        impact = {"level": "low"}
        
        # Critical business processes
        critical_types = ["payment", "billing", "order_processing", "user_registration", "authentication"]
        if action.action_type in critical_types:
            impact["level"] = "high"
            impact["critical_process_affected"] = True
        
        # Important business processes
        important_types = ["notification", "reporting", "data_export", "backup", "sync"]
        if action.action_type in important_types:
            impact["level"] = "medium"
            impact["important_process_affected"] = True
        
        return impact
    
    async def _assess_technical_impact(self, action: Action, action_failed: ActionFailed) -> Dict[str, Any]:
        """Assess the technical impact of the failure."""
        impact = {"level": "low"}
        
        # High technical impact scenarios
        if action.action_type in ["database_migration", "system_upgrade", "configuration_change"]:
            impact["level"] = "high"
            impact["system_stability_risk"] = True
        
        return impact
    
    async def _assess_user_impact(self, action: Action, action_failed: ActionFailed) -> Dict[str, Any]:
        """Assess the user impact of the failure."""
        impact = {"users_affected": 0}
        
        # Estimate users affected based on action type
        user_facing_types = {
            "user_registration": 100,
            "authentication": 500,
            "payment": 50,
            "notification": 200,
            "report_generation": 10
        }
        
        if action.action_type in user_facing_types:
            impact["users_affected"] = user_facing_types[action.action_type]
        
        return impact
    
    async def _check_downstream_dependencies(self, action: Action) -> List[str]:
        """Check what downstream systems might be affected."""
        dependencies = []
        
        # Map action types to their dependencies
        dependency_map = {
            "payment": ["billing", "accounting", "inventory"],
            "user_registration": ["authentication", "profile", "permissions"],
            "order_processing": ["inventory", "payment", "shipping"],
            "data_export": ["reporting", "analytics"],
            "backup": ["disaster_recovery", "compliance"]
        }
        
        if action.action_type in dependency_map:
            dependencies = dependency_map[action.action_type]
        
        return dependencies
    
    def _calculate_impact_score(self, impact_analysis: Dict[str, Any]) -> float:
        """Calculate overall impact score."""
        score = 0.0
        
        # Business impact
        business_level = impact_analysis.get("business_impact", {}).get("level", "low")
        if business_level == "high":
            score += 0.4
        elif business_level == "medium":
            score += 0.2
        
        # Technical impact
        technical_level = impact_analysis.get("technical_impact", {}).get("level", "low")
        if technical_level == "high":
            score += 0.3
        elif technical_level == "medium":
            score += 0.15
        
        # User impact
        users_affected = impact_analysis.get("user_impact", {}).get("users_affected", 0)
        if users_affected > 1000:
            score += 0.3
        elif users_affected > 100:
            score += 0.2
        elif users_affected > 0:
            score += 0.1
        
        return min(score, 1.0)
    
    async def _find_similar_recent_failures(self, action: Action, action_failed: ActionFailed) -> Dict[str, Any]:
        """Find similar failures in recent history."""
        # This would query the repository for similar failures
        # For now, return empty result as placeholder
        return {
            "count": 0,
            "pattern_detected": False,
            "time_window_hours": 24
        }
    
    async def _detect_failure_cascades(self, action: Action, action_failed: ActionFailed) -> Dict[str, Any]:
        """Detect if this failure is part of a cascade."""
        # This would analyze related failures and their timing
        # For now, return empty result as placeholder
        return {
            "cascade_detected": False,
            "cascade_size": 0,
            "cascade_duration_minutes": 0
        }
    
    async def _analyze_temporal_failure_patterns(self, action: Action, action_failed: ActionFailed) -> Dict[str, Any]:
        """Analyze temporal patterns in failures."""
        patterns = {}
        
        if action_failed.failed_at:
            hour = action_failed.failed_at.hour
            day_of_week = action_failed.failed_at.weekday()
            
            patterns["peak_hour_failure"] = 9 <= hour <= 17
            patterns["off_hours_failure"] = hour < 6 or hour > 22
            patterns["weekend_failure"] = day_of_week >= 5
        
        return patterns
    
    async def _detect_configuration_patterns(self, action: Action, action_failed: ActionFailed) -> Dict[str, Any]:
        """Detect configuration-related failure patterns."""
        patterns = {}
        
        if action.configuration:
            config_str = str(action.configuration)
            patterns["complex_config"] = len(config_str) > 1000
            patterns["has_external_urls"] = "http" in config_str.lower()
            patterns["has_credentials"] = any(key in config_str.lower() for key in ["password", "key", "token", "secret"])
        
        return patterns
    
    def _should_recommend_retry(self, action: Action, action_failed: ActionFailed) -> bool:
        """Determine if retry should be recommended."""
        # Don't retry if all attempts exhausted
        if action_failed.attempt_number >= action.max_retry_attempts:
            return False
        
        # Don't retry validation errors
        if action_failed.result.error_message and "validation" in action_failed.result.error_message.lower():
            return False
        
        # Don't retry authorization errors
        if action_failed.result.error_message and any(term in action_failed.result.error_message.lower() 
                                                     for term in ["unauthorized", "forbidden", "permission"]):
            return False
        
        # Retry transient failures
        return True
    
    async def _identify_alternative_approaches(self, action: Action, action_failed: ActionFailed) -> List[Dict[str, Any]]:
        """Identify alternative approaches to accomplish the action's goal."""
        alternatives = []
        
        # Map common action types to their alternatives
        if action.action_type == "webhook":
            alternatives.append({
                "action_type": "email_notification",
                "handler_type": "email",
                "description": "Send email notification instead of webhook",
                "configuration": {"fallback_from_webhook": True}
            })
        
        elif action.action_type == "sync_operation":
            alternatives.append({
                "action_type": "async_operation",
                "handler_type": "queue",
                "description": "Process asynchronously instead of synchronously",
                "configuration": {"original_sync_action": str(action.id)}
            })
        
        return alternatives
    
    async def _plan_compensating_actions(self, action: Action, action_failed: ActionFailed) -> List[Dict[str, Any]]:
        """Plan compensating actions for the failure."""
        compensating = []
        
        # Data consistency compensation
        if "data" in action.action_type or "update" in action.action_type:
            compensating.append({
                "action_type": "data_consistency_check",
                "handler_type": "function",
                "description": "Verify data consistency after failed update",
                "configuration": {"failed_action_id": str(action.id)}
            })
        
        # Notification compensation
        if "notification" in action.action_type:
            compensating.append({
                "action_type": "notification_failure_alert",
                "handler_type": "notification",
                "description": "Alert about failed notification",
                "configuration": {"original_notification_action": str(action.id)}
            })
        
        return compensating
    
    async def _plan_rollback_actions(self, action: Action, action_failed: ActionFailed) -> List[Dict[str, Any]]:
        """Plan rollback actions if the failure requires them."""
        rollbacks = []
        
        # Actions that may require rollback
        rollback_types = ["database_migration", "configuration_change", "deployment", "data_import"]
        
        if action.action_type in rollback_types:
            rollbacks.append({
                "action_type": f"rollback_{action.action_type}",
                "handler_type": "function",
                "description": f"Rollback changes from failed {action.action_type}",
                "configuration": {
                    "rollback_target": str(action.id),
                    "rollback_reason": "action_failure"
                },
                "priority": "high"
            })
        
        return rollbacks
    
    def _determine_recovery_urgency(self, severity: FailureSeverity) -> str:
        """Determine urgency level for recovery actions."""
        urgency_map = {
            FailureSeverity.CRITICAL: "immediate",
            FailureSeverity.HIGH: "urgent",
            FailureSeverity.MEDIUM: "normal",
            FailureSeverity.LOW: "low"
        }
        return urgency_map.get(severity, "normal")
    
    async def _log_handler_error(self, action_id: ActionId, error_message: str):
        """Log handler error for monitoring and debugging."""
        error_log = {
            "handler": "ActionFailedHandler",
            "action_id": str(action_id),
            "error": error_message,
            "timestamp": utc_now().isoformat(),
            "level": "error"
        }
        
        # In a real implementation, this would be sent to a logging service
        print(f"Handler Error: {error_log}")


def create_action_failed_handler(
    action_repository: ActionRepository,
    event_repository: EventRepository,
    notification_service: Optional[NotificationService] = None
) -> ActionFailedHandler:
    """Factory function to create ActionFailedHandler instance.
    
    Args:
        action_repository: Repository for action persistence operations
        event_repository: Repository for event operations
        notification_service: Optional service for sending notifications
        
    Returns:
        Configured ActionFailedHandler instance
    """
    return ActionFailedHandler(
        action_repository=action_repository,
        event_repository=event_repository,
        notification_service=notification_service
    )