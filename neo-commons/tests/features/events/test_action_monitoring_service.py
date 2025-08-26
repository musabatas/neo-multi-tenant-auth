"""Tests for ActionMonitoringService and related components."""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from neo_commons.core.value_objects import ActionId
from neo_commons.features.events.entities.event_action import EventAction, HandlerType, ActionStatus
from neo_commons.features.events.services.action_monitoring_service import (
    ActionMonitoringService, ActionMonitoringConfig, ExecutionMetrics, MonitoringLevel
)


class MockActionExecution:
    """Mock ActionExecution for testing."""
    
    def __init__(
        self,
        action_id: str,
        status: str = "success",
        duration_ms: int = 100,
        error_message: str = None,
        started_at: datetime = None,
        completed_at: datetime = None
    ):
        self.id = Mock()
        self.id.value = f"exec_{action_id}"
        self.action_id = Mock()
        self.action_id.value = action_id
        self.status = status
        self.duration_ms = duration_ms
        self.error_message = error_message
        self.started_at = started_at or datetime.now(timezone.utc)
        self.completed_at = completed_at or datetime.now(timezone.utc)


class TestExecutionMetrics:
    """Tests for ExecutionMetrics dataclass."""
    
    def test_metrics_initialization(self):
        """Test metrics initialization with default values."""
        metrics = ExecutionMetrics()
        
        assert metrics.total_executions == 0
        assert metrics.successful_executions == 0
        assert metrics.failed_executions == 0
        assert metrics.timeout_executions == 0
        assert metrics.avg_duration_ms == 0.0
        assert metrics.min_duration_ms == 0
        assert metrics.max_duration_ms == 0
        assert metrics.p95_duration_ms == 0.0
        assert metrics.executions_per_minute == 0.0
        assert metrics.success_rate_percent == 0.0
        assert len(metrics.error_count_by_type) == 0
        assert len(metrics.recent_errors) == 0
    
    def test_calculate_success_rate(self):
        """Test success rate calculation."""
        metrics = ExecutionMetrics()
        
        # No executions
        assert metrics.calculate_success_rate() == 0.0
        
        # With executions
        metrics.total_executions = 10
        metrics.successful_executions = 8
        assert metrics.calculate_success_rate() == 80.0
        
        # Perfect success rate
        metrics.successful_executions = 10
        assert metrics.calculate_success_rate() == 100.0
    
    def test_add_successful_execution(self):
        """Test adding successful execution to metrics."""
        metrics = ExecutionMetrics()
        execution = MockActionExecution("action_1", status="success", duration_ms=150)
        
        metrics.add_execution_result(execution)
        
        assert metrics.total_executions == 1
        assert metrics.successful_executions == 1
        assert metrics.failed_executions == 0
        assert metrics.timeout_executions == 0
        assert metrics.avg_duration_ms == 150.0
        assert metrics.min_duration_ms == 150
        assert metrics.max_duration_ms == 150
        assert metrics.success_rate_percent == 100.0
    
    def test_add_failed_execution(self):
        """Test adding failed execution to metrics."""
        metrics = ExecutionMetrics()
        execution = MockActionExecution(
            "action_1", 
            status="failed", 
            duration_ms=200,
            error_message="Connection timeout"
        )
        
        metrics.add_execution_result(execution)
        
        assert metrics.total_executions == 1
        assert metrics.successful_executions == 0
        assert metrics.failed_executions == 1
        assert metrics.timeout_executions == 0
        assert metrics.success_rate_percent == 0.0
        assert "timeout" in metrics.error_count_by_type
        assert metrics.error_count_by_type["timeout"] == 1
        assert len(metrics.recent_errors) == 1
    
    def test_add_timeout_execution(self):
        """Test adding timeout execution to metrics."""
        metrics = ExecutionMetrics()
        execution = MockActionExecution(
            "action_1", 
            status="timeout", 
            duration_ms=5000,
            error_message="Execution timed out after 5s"
        )
        
        metrics.add_execution_result(execution)
        
        assert metrics.total_executions == 1
        assert metrics.successful_executions == 0
        assert metrics.failed_executions == 0
        assert metrics.timeout_executions == 1
        assert metrics.success_rate_percent == 0.0
    
    def test_duration_metrics_update(self):
        """Test duration metrics with multiple executions."""
        metrics = ExecutionMetrics()
        
        # Add multiple executions with different durations
        executions = [
            MockActionExecution("action_1", status="success", duration_ms=100),
            MockActionExecution("action_2", status="success", duration_ms=200),
            MockActionExecution("action_3", status="success", duration_ms=50),
            MockActionExecution("action_4", status="success", duration_ms=300)
        ]
        
        for execution in executions:
            metrics.add_execution_result(execution)
        
        assert metrics.total_executions == 4
        assert metrics.min_duration_ms == 50
        assert metrics.max_duration_ms == 300
        assert metrics.avg_duration_ms == 162.5  # (100 + 200 + 50 + 300) / 4
    
    def test_error_classification(self):
        """Test error message classification."""
        metrics = ExecutionMetrics()
        
        test_cases = [
            ("Connection timeout occurred", "timeout"),
            ("Network connection failed", "network"),
            ("404 Not Found", "not_found"),
            ("401 Unauthorized", "auth"),
            ("500 Internal Server Error", "server_error"),
            ("Validation failed: invalid input", "validation"),
            ("Something unexpected happened", "unknown")
        ]
        
        for error_message, expected_type in test_cases:
            execution = MockActionExecution(
                "action_test", 
                status="failed",
                error_message=error_message
            )
            
            error_type = metrics._classify_error(error_message)
            assert error_type == expected_type
    
    def test_recent_errors_limit(self):
        """Test that recent errors list is limited."""
        metrics = ExecutionMetrics()
        
        # Add more than 10 failed executions
        for i in range(15):
            execution = MockActionExecution(
                f"action_{i}", 
                status="failed",
                error_message=f"Error {i}"
            )
            metrics.add_execution_result(execution)
        
        # Should only keep the most recent 10
        assert len(metrics.recent_errors) == 10
        
        # Verify it's the latest ones (Error 5-14)
        error_messages = [error["message"] for error in metrics.recent_errors]
        assert "Error 14" in error_messages[0]  # Most recent first


class TestActionMonitoringConfig:
    """Tests for ActionMonitoringConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ActionMonitoringConfig()
        
        assert config.log_level == "INFO"
        assert config.log_executions is True
        assert config.log_errors is True
        assert config.log_performance is True
        assert config.collect_metrics is True
        assert config.metrics_window_minutes == 60
        assert config.metrics_retention_hours == 24
        assert config.slow_execution_threshold_ms == 5000
        assert config.log_slow_executions is True
        assert config.max_recent_errors == 50
        assert config.alert_on_error_rate is True
        assert config.error_rate_threshold_percent == 10.0
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        config = ActionMonitoringConfig(
            metrics_window_minutes=30,
            error_rate_threshold_percent=5.0
        )
        assert config.metrics_window_minutes == 30
        assert config.error_rate_threshold_percent == 5.0
        
        # Invalid metrics window
        with pytest.raises(ValueError, match="Metrics window must be positive"):
            ActionMonitoringConfig(metrics_window_minutes=0)
        
        # Invalid error rate threshold
        with pytest.raises(ValueError, match="Error rate threshold must be between 0 and 100"):
            ActionMonitoringConfig(error_rate_threshold_percent=150.0)
        
        with pytest.raises(ValueError, match="Error rate threshold must be between 0 and 100"):
            ActionMonitoringConfig(error_rate_threshold_percent=-5.0)


class TestActionMonitoringService:
    """Tests for ActionMonitoringService."""
    
    @pytest.fixture
    def mock_repository(self):
        """Create mock execution repository."""
        repository = AsyncMock()
        return repository
    
    @pytest.fixture
    def monitoring_service(self, mock_repository):
        """Create monitoring service with mock repository."""
        config = ActionMonitoringConfig(
            collect_metrics=True,
            log_executions=True,
            metrics_retention_hours=1  # Short retention for testing
        )
        return ActionMonitoringService(mock_repository, config)
    
    @pytest.fixture
    def sample_action(self):
        """Create sample action for testing."""
        return EventAction(
            id=ActionId.generate(),
            name="Test Action",
            handler_type=HandlerType.WEBHOOK,
            configuration={"url": "https://example.com/webhook"},
            event_types=["user.created"]
        )
    
    def test_service_initialization(self, mock_repository):
        """Test service initialization."""
        service = ActionMonitoringService(mock_repository)
        
        assert service._repository == mock_repository
        assert service._config is not None
        assert service._metrics_cache == {}
        assert service._global_metrics is not None
        assert service._cleanup_task is None
        assert service._metrics_task is None
    
    @pytest.mark.asyncio
    async def test_log_execution_start(self, monitoring_service, sample_action):
        """Test logging execution start."""
        execution = MockActionExecution(str(sample_action.id.value))
        event_data = {"event_type": "user.created", "user_id": "123"}
        
        with patch.object(monitoring_service._logger, 'info') as mock_log:
            await monitoring_service.log_execution_start(sample_action, execution, event_data)
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert "Action execution started" in call_args[0][0]
            assert "extra" in call_args[1]
            
            extra = call_args[1]["extra"]
            assert extra["action_name"] == "Test Action"
            assert extra["handler_type"] == "webhook"
    
    @pytest.mark.asyncio
    async def test_log_execution_complete_success(self, monitoring_service, sample_action):
        """Test logging successful execution completion."""
        execution = MockActionExecution(
            str(sample_action.id.value), 
            status="success", 
            duration_ms=150
        )
        
        with patch.object(monitoring_service._logger, 'info') as mock_log:
            await monitoring_service.log_execution_complete(sample_action, execution)
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert "completed successfully" in call_args[0][0]
            assert "150ms" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_log_execution_complete_failure(self, monitoring_service, sample_action):
        """Test logging failed execution completion."""
        execution = MockActionExecution(
            str(sample_action.id.value), 
            status="failed", 
            duration_ms=200,
            error_message="Connection failed"
        )
        
        with patch.object(monitoring_service._logger, 'error') as mock_log:
            await monitoring_service.log_execution_complete(sample_action, execution)
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert "execution failed" in call_args[0][0]
            assert "Connection failed" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_log_execution_complete_timeout(self, monitoring_service, sample_action):
        """Test logging timeout execution completion."""
        execution = MockActionExecution(
            str(sample_action.id.value), 
            status="timeout", 
            duration_ms=5000
        )
        
        with patch.object(monitoring_service._logger, 'warning') as mock_log:
            await monitoring_service.log_execution_complete(sample_action, execution)
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert "timed out" in call_args[0][0]
            assert "5000ms" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_log_slow_execution(self, monitoring_service, sample_action):
        """Test logging slow execution detection."""
        execution = MockActionExecution(
            str(sample_action.id.value), 
            status="success", 
            duration_ms=6000  # Above default threshold of 5000ms
        )
        
        with patch.object(monitoring_service._logger, 'warning') as mock_warning, \
             patch.object(monitoring_service._logger, 'info') as mock_info:
            
            await monitoring_service.log_execution_complete(sample_action, execution)
            
            # Should log both success and slow execution warning
            mock_info.assert_called_once()  # Success log
            mock_warning.assert_called_once()  # Slow execution log
            
            warning_call = mock_warning.call_args
            assert "Slow action execution detected" in warning_call[0][0]
            assert "6000ms > 5000ms" in warning_call[0][0]
    
    @pytest.mark.asyncio
    async def test_log_execution_error(self, monitoring_service, sample_action):
        """Test logging execution error."""
        execution = MockActionExecution(str(sample_action.id.value))
        error = ConnectionError("Failed to connect to webhook")
        
        with patch.object(monitoring_service._logger, 'error') as mock_log:
            await monitoring_service.log_execution_error(sample_action, execution, error)
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert "Action execution error" in call_args[0][0]
            assert "ConnectionError" in call_args[0][0]
            assert "Failed to connect to webhook" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self, monitoring_service, sample_action):
        """Test metrics collection from executions."""
        action_id = str(sample_action.id.value)
        
        # Add successful execution
        success_execution = MockActionExecution(action_id, status="success", duration_ms=100)
        await monitoring_service._update_metrics(sample_action, success_execution)
        
        # Add failed execution
        failed_execution = MockActionExecution(
            action_id, 
            status="failed", 
            duration_ms=200,
            error_message="Network error"
        )
        await monitoring_service._update_metrics(sample_action, failed_execution)
        
        # Check action-specific metrics
        action_metrics = await monitoring_service.get_action_metrics(action_id)
        assert action_metrics is not None
        assert action_metrics.total_executions == 2
        assert action_metrics.successful_executions == 1
        assert action_metrics.failed_executions == 1
        assert action_metrics.success_rate_percent == 50.0
        
        # Check global metrics
        global_metrics = await monitoring_service.get_global_metrics()
        assert global_metrics.total_executions == 2
        assert global_metrics.successful_executions == 1
        assert global_metrics.failed_executions == 1
    
    @pytest.mark.asyncio
    async def test_action_health_check(self, monitoring_service, sample_action):
        """Test action health checking."""
        action_id = str(sample_action.id.value)
        
        # No executions - inactive
        health = await monitoring_service.check_action_health(action_id)
        assert health["status"] == "unknown"
        assert "No execution data available" in health["message"]
        
        # Add executions with different success rates
        executions = [
            MockActionExecution(action_id, status="success"),
            MockActionExecution(action_id, status="success"),
            MockActionExecution(action_id, status="success"),
            MockActionExecution(action_id, status="failed", error_message="Error")
        ]
        
        for execution in executions:
            await monitoring_service._update_metrics(sample_action, execution)
        
        # Good success rate (75%) - should be warning
        health = await monitoring_service.check_action_health(action_id)
        assert health["status"] == "warning"  # 75% < 80%
        assert "75.0%" in health["message"]
        assert "metrics" in health
        
        # Add more successful executions to get above 95%
        for _ in range(16):  # Total will be 20 executions, 19 successful = 95%
            success_execution = MockActionExecution(action_id, status="success")
            await monitoring_service._update_metrics(sample_action, success_execution)
        
        health = await monitoring_service.check_action_health(action_id)
        assert health["status"] == "healthy"
        assert "95.0%" in health["message"]
    
    @pytest.mark.asyncio
    async def test_alert_on_high_error_rate(self, monitoring_service, sample_action):
        """Test alerting on high error rate."""
        action_id = str(sample_action.id.value)
        
        with patch.object(monitoring_service._logger, 'critical') as mock_critical:
            # Add executions that exceed error rate threshold (default 10%)
            # 10 executions, 8 failures = 20% failure rate (80% success rate)
            for i in range(10):
                if i < 8:
                    execution = MockActionExecution(action_id, status="failed", error_message="Error")
                else:
                    execution = MockActionExecution(action_id, status="success")
                
                await monitoring_service._update_metrics(sample_action, execution)
            
            # Should trigger alert
            mock_critical.assert_called()
            call_args = mock_critical.call_args
            assert "HIGH ERROR RATE ALERT" in call_args[0][0]
            assert "80.0%" in call_args[0][0]  # Success rate
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, monitoring_service):
        """Test starting and stopping monitoring."""
        # Start monitoring
        await monitoring_service.start_monitoring()
        
        assert monitoring_service._cleanup_task is not None
        assert monitoring_service._metrics_task is not None
        assert not monitoring_service._cleanup_task.done()
        assert not monitoring_service._metrics_task.done()
        
        # Stop monitoring
        await monitoring_service.stop_monitoring()
        
        # Tasks should be cancelled
        assert monitoring_service._cleanup_task.cancelled() or monitoring_service._cleanup_task.done()
        assert monitoring_service._metrics_task.cancelled() or monitoring_service._metrics_task.done()
    
    @pytest.mark.asyncio
    async def test_metrics_cache_cleanup(self, monitoring_service, sample_action):
        """Test cleanup of old metrics."""
        # Set very short retention for testing
        monitoring_service._config.metrics_retention_hours = 0.001  # ~3.6 seconds
        
        action_id = str(sample_action.id.value)
        execution = MockActionExecution(action_id, status="success")
        
        await monitoring_service._update_metrics(sample_action, execution)
        
        # Verify metrics exist
        assert action_id in monitoring_service._metrics_cache
        
        # Simulate time passing (manually set old timestamp)
        old_time = datetime.now(timezone.utc) - timedelta(hours=1)
        monitoring_service._metrics_cache[action_id].window_end = old_time
        
        # Run cleanup
        await monitoring_service._cleanup_loop()
        
        # Metrics should be removed
        assert action_id not in monitoring_service._metrics_cache
    
    def test_disabled_logging(self, mock_repository):
        """Test service with logging disabled."""
        config = ActionMonitoringConfig(
            log_executions=False,
            log_errors=False,
            log_performance=False,
            collect_metrics=False
        )
        service = ActionMonitoringService(mock_repository, config)
        
        assert service._config.log_executions is False
        assert service._config.log_errors is False
        assert service._config.log_performance is False
        assert service._config.collect_metrics is False