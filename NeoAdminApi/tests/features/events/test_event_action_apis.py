"""Tests for Event Action management APIs."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime, timezone

from neo_commons.core.value_objects import ActionId, UserId
from neo_commons.features.events.entities.event_action import (
    EventAction, ActionStatus, HandlerType, ActionPriority, ExecutionMode, ActionCondition
)

from NeoAdminApi.src.features.events.routers.event_actions import router
from NeoAdminApi.src.features.events.services import AdminEventActionService
from NeoAdminApi.src.features.events.models import (
    EventActionCreateRequest, EventActionUpdateRequest, ActionTestRequest
)


@pytest.fixture
def app():
    """Create FastAPI app with event action router."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/event-actions")
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_admin_service():
    """Create mock AdminEventActionService."""
    return AsyncMock(spec=AdminEventActionService)


@pytest.fixture
def sample_action():
    """Create sample EventAction for testing."""
    return EventAction(
        id=ActionId.generate(),
        name="Test Webhook Action",
        description="Test webhook action for user events",
        handler_type=HandlerType.WEBHOOK,
        configuration={"url": "https://example.com/webhook", "method": "POST"},
        event_types=["user.created", "user.updated"],
        execution_mode=ExecutionMode.ASYNC,
        priority=ActionPriority.NORMAL,
        status=ActionStatus.ACTIVE,
        is_enabled=True,
        created_by_user_id=UserId.generate()
    )


class TestEventActionAPIs:
    """Tests for Event Action management APIs."""
    
    def test_list_event_actions_empty(self, client, mock_admin_service):
        """Test listing actions when none exist."""
        mock_admin_service.list_actions.return_value = ([], 0)
        
        with patch("NeoAdminApi.src.features.events.routers.event_actions.get_admin_event_action_service", 
                  return_value=mock_admin_service):
            response = client.get("/api/v1/event-actions/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["actions"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["size"] == 50
        
        mock_admin_service.list_actions.assert_called_once_with(
            skip=0, limit=50, status=None, handler_type=None, 
            event_type=None, search=None, tenant_id=None
        )
    
    def test_list_event_actions_with_data(self, client, mock_admin_service, sample_action):
        """Test listing actions with data."""
        mock_admin_service.list_actions.return_value = ([sample_action], 1)
        
        with patch("NeoAdminApi.src.features.events.routers.event_actions.get_admin_event_action_service", 
                  return_value=mock_admin_service):
            response = client.get("/api/v1/event-actions/?skip=0&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["actions"]) == 1
        assert data["total"] == 1
        assert data["page"] == 1
        assert data["size"] == 10
        
        action_data = data["actions"][0]
        assert action_data["name"] == "Test Webhook Action"
        assert action_data["handler_type"] == "webhook"
        assert action_data["event_types"] == ["user.created", "user.updated"]
    
    def test_list_event_actions_with_filters(self, client, mock_admin_service):
        """Test listing actions with filters."""
        mock_admin_service.list_actions.return_value = ([], 0)
        
        with patch("NeoAdminApi.src.features.events.routers.event_actions.get_admin_event_action_service", 
                  return_value=mock_admin_service):
            response = client.get(
                "/api/v1/event-actions/"
                "?status=active&handler_type=webhook&event_type=user.created&search=test&tenant_id=tenant_123"
            )
        
        assert response.status_code == 200
        
        mock_admin_service.list_actions.assert_called_once_with(
            skip=0, limit=50, status="active", handler_type="webhook", 
            event_type="user.created", search="test", tenant_id="tenant_123"
        )
    
    def test_create_event_action_success(self, client, mock_admin_service, sample_action):
        """Test successful action creation."""
        mock_admin_service.create_action.return_value = sample_action
        
        create_request = {
            "name": "Test Webhook Action",
            "description": "Test webhook action for user events",
            "handler_type": "webhook",
            "configuration": {"url": "https://example.com/webhook", "method": "POST"},
            "event_types": ["user.created", "user.updated"],
            "execution_mode": "async",
            "priority": "normal",
            "is_enabled": True
        }
        
        with patch("NeoAdminApi.src.features.events.routers.event_actions.get_admin_event_action_service", 
                  return_value=mock_admin_service):
            response = client.post("/api/v1/event-actions/", json=create_request)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Webhook Action"
        assert data["handler_type"] == "webhook"
        
        mock_admin_service.create_action.assert_called_once()
        call_args = mock_admin_service.create_action.call_args[0]
        assert call_args[0].name == "Test Webhook Action"
    
    def test_create_event_action_validation_error(self, client, mock_admin_service):
        """Test action creation with validation error."""
        mock_admin_service.create_action.side_effect = ValueError("Action name cannot be empty")
        
        create_request = {
            "name": "",  # Empty name should cause validation error
            "handler_type": "webhook",
            "configuration": {"url": "https://example.com/webhook"},
            "event_types": ["user.created"]
        }
        
        with patch("NeoAdminApi.src.features.events.routers.event_actions.get_admin_event_action_service", 
                  return_value=mock_admin_service):
            response = client.post("/api/v1/event-actions/", json=create_request)
        
        assert response.status_code == 400
        assert "Action name cannot be empty" in response.json()["detail"]
    
    def test_create_event_action_invalid_request(self, client, mock_admin_service):
        """Test action creation with invalid request data."""
        create_request = {
            "name": "Test Action",
            "handler_type": "invalid_handler",  # Invalid handler type
            "configuration": {"url": "https://example.com/webhook"},
            "event_types": []  # Empty event types
        }
        
        with patch("NeoAdminApi.src.features.events.routers.event_actions.get_admin_event_action_service", 
                  return_value=mock_admin_service):
            response = client.post("/api/v1/event-actions/", json=create_request)
        
        assert response.status_code == 422  # Validation error from Pydantic
    
    def test_get_event_action_success(self, client, mock_admin_service, sample_action):
        """Test successful action retrieval."""
        action_id = str(sample_action.id.value)
        mock_admin_service.get_action.return_value = sample_action
        
        with patch("NeoAdminApi.src.features.events.routers.event_actions.get_admin_event_action_service", 
                  return_value=mock_admin_service):
            response = client.get(f"/api/v1/event-actions/{action_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Webhook Action"
        assert data["id"] == action_id
        
        mock_admin_service.get_action.assert_called_once_with(action_id)
    
    def test_get_event_action_not_found(self, client, mock_admin_service):
        """Test action retrieval when action not found."""
        action_id = "non-existent-id"
        mock_admin_service.get_action.return_value = None
        
        with patch("NeoAdminApi.src.features.events.routers.event_actions.get_admin_event_action_service", 
                  return_value=mock_admin_service):
            response = client.get(f"/api/v1/event-actions/{action_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_update_event_action_success(self, client, mock_admin_service, sample_action):
        """Test successful action update."""
        action_id = str(sample_action.id.value)
        updated_action = sample_action
        updated_action.name = "Updated Action Name"
        mock_admin_service.update_action.return_value = updated_action
        
        update_request = {
            "name": "Updated Action Name",
            "description": "Updated description"
        }
        
        with patch("NeoAdminApi.src.features.events.routers.event_actions.get_admin_event_action_service", 
                  return_value=mock_admin_service):
            response = client.put(f"/api/v1/event-actions/{action_id}", json=update_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Action Name"
        
        mock_admin_service.update_action.assert_called_once()
    
    def test_update_event_action_not_found(self, client, mock_admin_service):
        """Test updating non-existent action."""
        action_id = "non-existent-id"
        mock_admin_service.update_action.return_value = None
        
        update_request = {"name": "Updated Name"}
        
        with patch("NeoAdminApi.src.features.events.routers.event_actions.get_admin_event_action_service", 
                  return_value=mock_admin_service):
            response = client.put(f"/api/v1/event-actions/{action_id}", json=update_request)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_delete_event_action_success(self, client, mock_admin_service):
        """Test successful action deletion."""
        action_id = "test-action-id"
        mock_admin_service.delete_action.return_value = True
        
        with patch("NeoAdminApi.src.features.events.routers.event_actions.get_admin_event_action_service", 
                  return_value=mock_admin_service):
            response = client.delete(f"/api/v1/event-actions/{action_id}")
        
        assert response.status_code == 204
        mock_admin_service.delete_action.assert_called_once_with(action_id)
    
    def test_delete_event_action_not_found(self, client, mock_admin_service):
        """Test deleting non-existent action."""
        action_id = "non-existent-id"
        mock_admin_service.delete_action.return_value = False
        
        with patch("NeoAdminApi.src.features.events.routers.event_actions.get_admin_event_action_service", 
                  return_value=mock_admin_service):
            response = client.delete(f"/api/v1/event-actions/{action_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_test_event_action_success(self, client, mock_admin_service):
        """Test action testing functionality."""
        action_id = "test-action-id"
        
        from NeoAdminApi.src.features.events.models import ActionTestResponse
        test_response = ActionTestResponse(
            matched=True,
            reason="All conditions match",
            conditions_evaluated=[],
            would_execute=True,
            dry_run=True
        )
        mock_admin_service.test_action.return_value = test_response
        
        test_request = {
            "event_type": "user.created",
            "event_data": {"user": {"id": "123", "email": "test@example.com"}},
            "dry_run": True
        }
        
        with patch("NeoAdminApi.src.features.events.routers.event_actions.get_admin_event_action_service", 
                  return_value=mock_admin_service):
            response = client.post(f"/api/v1/event-actions/{action_id}/test", json=test_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["matched"] is True
        assert data["reason"] == "All conditions match"
        assert data["dry_run"] is True
        
        mock_admin_service.test_action.assert_called_once()
    
    def test_enable_event_action(self, client, mock_admin_service, sample_action):
        """Test enabling an action."""
        action_id = str(sample_action.id.value)
        enabled_action = sample_action
        enabled_action.is_enabled = True
        mock_admin_service.update_action.return_value = enabled_action
        
        with patch("NeoAdminApi.src.features.events.routers.event_actions.get_admin_event_action_service", 
                  return_value=mock_admin_service):
            response = client.post(f"/api/v1/event-actions/{action_id}/enable")
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is True
        
        mock_admin_service.update_action.assert_called_once()
        call_args = mock_admin_service.update_action.call_args
        assert call_args[0][1].is_enabled is True
    
    def test_disable_event_action(self, client, mock_admin_service, sample_action):
        """Test disabling an action."""
        action_id = str(sample_action.id.value)
        disabled_action = sample_action
        disabled_action.is_enabled = False
        mock_admin_service.update_action.return_value = disabled_action
        
        with patch("NeoAdminApi.src.features.events.routers.event_actions.get_admin_event_action_service", 
                  return_value=mock_admin_service):
            response = client.post(f"/api/v1/event-actions/{action_id}/disable")
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is False
        
        mock_admin_service.update_action.assert_called_once()
        call_args = mock_admin_service.update_action.call_args
        assert call_args[0][1].is_enabled is False
    
    def test_get_action_executions(self, client, mock_admin_service):
        """Test getting action execution history."""
        action_id = "test-action-id"
        mock_admin_service.get_action_executions.return_value = ([], 0)
        
        with patch("NeoAdminApi.src.features.events.routers.event_actions.get_admin_event_action_service", 
                  return_value=mock_admin_service):
            response = client.get(f"/api/v1/event-actions/{action_id}/executions")
        
        assert response.status_code == 200
        data = response.json()
        assert data["executions"] == []
        assert data["total"] == 0
        
        mock_admin_service.get_action_executions.assert_called_once_with(
            action_id, skip=0, limit=50, status=None
        )
    
    def test_get_global_stats(self, client, mock_admin_service):
        """Test getting global action statistics."""
        from NeoAdminApi.src.features.events.models import ActionStatsResponse
        stats = ActionStatsResponse(
            total_actions=5,
            active_actions=4,
            enabled_actions=3,
            total_executions=100,
            successful_executions=90,
            failed_executions=10,
            overall_success_rate=90.0,
            by_handler_type={"webhook": 3, "email": 2},
            by_status={"active": 4, "paused": 1}
        )
        mock_admin_service.get_action_stats.return_value = stats
        
        with patch("NeoAdminApi.src.features.events.routers.event_actions.get_admin_event_action_service", 
                  return_value=mock_admin_service):
            response = client.get("/api/v1/event-actions/stats/overview")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_actions"] == 5
        assert data["overall_success_rate"] == 90.0
        assert data["by_handler_type"]["webhook"] == 3
        
        mock_admin_service.get_action_stats.assert_called_once_with(None)
    
    def test_get_action_specific_stats(self, client, mock_admin_service):
        """Test getting stats for a specific action."""
        action_id = "test-action-id"
        
        from NeoAdminApi.src.features.events.models import ActionStatsResponse
        stats = ActionStatsResponse(
            total_actions=1,
            active_actions=1,
            enabled_actions=1,
            total_executions=20,
            successful_executions=18,
            failed_executions=2,
            overall_success_rate=90.0,
            by_handler_type={"webhook": 1},
            by_status={"active": 1}
        )
        mock_admin_service.get_action_stats.return_value = stats
        
        with patch("NeoAdminApi.src.features.events.routers.event_actions.get_admin_event_action_service", 
                  return_value=mock_admin_service):
            response = client.get(f"/api/v1/event-actions/{action_id}/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_executions"] == 20
        assert data["overall_success_rate"] == 90.0
        
        mock_admin_service.get_action_stats.assert_called_once_with(action_id)
    
    def test_server_error_handling(self, client, mock_admin_service):
        """Test handling of server errors."""
        mock_admin_service.list_actions.side_effect = Exception("Database connection failed")
        
        with patch("NeoAdminApi.src.features.events.routers.event_actions.get_admin_event_action_service", 
                  return_value=mock_admin_service):
            response = client.get("/api/v1/event-actions/")
        
        assert response.status_code == 500
        assert "Database connection failed" in response.json()["detail"]
    
    def test_create_action_with_conditions(self, client, mock_admin_service, sample_action):
        """Test creating action with conditions."""
        mock_admin_service.create_action.return_value = sample_action
        
        create_request = {
            "name": "Conditional Action",
            "handler_type": "webhook",
            "configuration": {"url": "https://example.com/webhook"},
            "event_types": ["user.created"],
            "conditions": [
                {
                    "field": "data.user.email",
                    "operator": "contains",
                    "value": "@company.com"
                },
                {
                    "field": "data.user.active",
                    "operator": "equals",
                    "value": True
                }
            ],
            "context_filters": {"tenant_id": "tenant_123"}
        }
        
        with patch("NeoAdminApi.src.features.events.routers.event_actions.get_admin_event_action_service", 
                  return_value=mock_admin_service):
            response = client.post("/api/v1/event-actions/", json=create_request)
        
        assert response.status_code == 201
        
        mock_admin_service.create_action.assert_called_once()
        call_args = mock_admin_service.create_action.call_args[0]
        request_obj = call_args[0]
        assert len(request_obj.conditions) == 2
        assert request_obj.context_filters == {"tenant_id": "tenant_123"}
    
    def test_pagination_calculations(self, client, mock_admin_service):
        """Test pagination calculations in responses."""
        mock_admin_service.list_actions.return_value = ([], 100)
        
        with patch("NeoAdminApi.src.features.events.routers.event_actions.get_admin_event_action_service", 
                  return_value=mock_admin_service):
            response = client.get("/api/v1/event-actions/?skip=20&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 3  # (20 / 10) + 1
        assert data["size"] == 10
        assert data["total"] == 100
    
    def test_complex_test_scenario(self, client, mock_admin_service):
        """Test complex action testing scenario."""
        action_id = "complex-action-id"
        
        from NeoAdminApi.src.features.events.models import ActionTestResponse
        test_response = ActionTestResponse(
            matched=False,
            reason="Event type 'order.created' does not match configured types: ['user.*']",
            conditions_evaluated=[
                {
                    "field": "data.user.email",
                    "operator": "contains",
                    "value": "@company.com",
                    "result": True,
                    "error": None
                }
            ],
            would_execute=False,
            dry_run=True
        )
        mock_admin_service.test_action.return_value = test_response
        
        test_request = {
            "event_type": "order.created",
            "event_data": {"user": {"email": "test@company.com"}},
            "dry_run": True
        }
        
        with patch("NeoAdminApi.src.features.events.routers.event_actions.get_admin_event_action_service", 
                  return_value=mock_admin_service):
            response = client.post(f"/api/v1/event-actions/{action_id}/test", json=test_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["matched"] is False
        assert "does not match configured types" in data["reason"]
        assert len(data["conditions_evaluated"]) == 1
        assert data["conditions_evaluated"][0]["result"] is True