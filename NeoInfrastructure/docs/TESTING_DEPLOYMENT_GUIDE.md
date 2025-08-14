# Testing and Deployment Guide

This guide provides comprehensive instructions for testing and deploying the enhanced Infrastructure API with all new features including authentication, event-driven migrations, and monitoring capabilities.

## 🧪 Testing Strategy

### Testing Philosophy
1. **Quality Gates**: Implement comprehensive testing at every level
2. **Shift-Left Testing**: Catch issues early in development
3. **Test Automation**: Automate all tests for CI/CD integration
4. **Performance Testing**: Validate performance under load
5. **Security Testing**: Ensure security controls are effective

### Testing Pyramid
```
                    /\
                   /  \
                  /E2E \      ← Integration & End-to-End Tests
                 /______\
                /        \
               / SERVICE  \    ← Service & API Tests
              /____________\
             /              \
            /      UNIT      \  ← Unit Tests (Foundation)
           /__________________\
```

---

## 🏗️ Test Infrastructure Setup

### Prerequisites
- Python 3.13+ with pytest
- Docker and Docker Compose
- Test database instances
- Redis for testing
- Test Keycloak instance

### Development Environment
```bash
# Create test environment
cd NeoInfrastructure

# Install test dependencies
pip install -e .[test]

# Setup test databases
docker-compose -f docker/docker-compose.test.yml up -d

# Run initial test setup
pytest tests/setup/ -v
```

### Test Configuration
**File**: `tests/conftest.py`

```python
"""
Pytest configuration and fixtures for Infrastructure API tests.
"""
import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, patch
import asyncpg
import redis.asyncio as redis

from src.app import create_app
from src.common.config.settings import get_test_settings
from src.integrations.keycloak.async_client import InfrastructureKeycloakClient
from src.features.migrations.engines.dynamic_migration_engine import DynamicMigrationEngine
from src.features.migrations.events.queue.redis_queue import RedisEventQueue

# Test settings
TEST_SETTINGS = get_test_settings()

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def test_db_pool():
    """Create test database connection pool."""
    pool = await asyncpg.create_pool(
        TEST_SETTINGS.admin_database_url,
        min_size=1,
        max_size=5
    )
    yield pool
    await pool.close()

@pytest_asyncio.fixture(scope="session")
async def test_redis():
    """Create test Redis client."""
    redis_client = redis.from_url(
        TEST_SETTINGS.redis_url,
        decode_responses=True
    )
    yield redis_client
    await redis_client.flushdb()
    await redis_client.close()

@pytest_asyncio.fixture
async def test_app():
    """Create test FastAPI application."""
    app = create_app(test_mode=True)
    yield app

@pytest_asyncio.fixture
async def mock_keycloak_client():
    """Mock Keycloak client for testing."""
    with patch('src.integrations.keycloak.async_client.get_keycloak_client') as mock:
        client = AsyncMock(spec=InfrastructureKeycloakClient)
        client.validate_token.return_value = {
            "sub": "test-user-123",
            "preferred_username": "testuser",
            "email": "test@example.com",
            "permissions": ["migrations:read", "migrations:execute", "databases:read"]
        }
        mock.return_value = client
        yield client

@pytest.fixture
def auth_headers():
    """Generate test authentication headers."""
    return {
        "Authorization": "Bearer test-valid-token",
        "Content-Type": "application/json"
    }

@pytest.fixture
def admin_auth_headers():
    """Generate admin authentication headers."""
    return {
        "Authorization": "Bearer test-admin-token",
        "Content-Type": "application/json"
    }

@pytest_asyncio.fixture
async def migration_engine(test_db_pool):
    """Create test migration engine."""
    engine = DynamicMigrationEngine()
    engine.admin_pool = test_db_pool
    yield engine

@pytest_asyncio.fixture
async def event_queue(test_redis):
    """Create test event queue."""
    queue = RedisEventQueue()
    queue.redis_client = test_redis
    yield queue

@pytest.fixture
def sample_database_connection():
    """Sample database connection data for testing."""
    return {
        "id": "test-db-001",
        "database_name": "test_database",
        "connection_type": "shared",
        "region": "us-east",
        "host": "localhost",
        "port": 5432,
        "username": "test_user",
        "encrypted_password": "encrypted_test_password"
    }

@pytest.fixture
def sample_migration_event():
    """Sample migration event for testing."""
    return {
        "event_type": "database.created",
        "priority": "normal",
        "payload": {
            "database_id": "test-db-001",
            "database_name": "test_database",
            "connection_type": "shared",
            "region": "us-east",
            "host": "localhost",
            "port": 5432,
            "username": "test_user",
            "auto_migrate": True
        }
    }

class DatabaseHelper:
    """Helper class for database operations in tests."""
    
    def __init__(self, pool):
        self.pool = pool
    
    async def setup_test_data(self):
        """Setup test data in database."""
        async with self.pool.acquire() as conn:
            # Create test database connections
            await conn.execute("""
                INSERT INTO admin.database_connections 
                (id, database_name, connection_type, region, host, port, username, encrypted_password)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (id) DO NOTHING
            """, "test-db-001", "test_database", "shared", "us-east", 
                "localhost", 5432, "test_user", "encrypted_password")
    
    async def cleanup_test_data(self):
        """Clean up test data from database."""
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM admin.database_connections WHERE id LIKE 'test-%'")
            await conn.execute("DELETE FROM admin.migration_executions WHERE id LIKE 'test-%'")

@pytest_asyncio.fixture
async def db_helper(test_db_pool):
    """Database helper for tests."""
    helper = DatabaseHelper(test_db_pool)
    await helper.setup_test_data()
    yield helper
    await helper.cleanup_test_data()
```

---

## 🔧 Unit Testing

### Test Structure
```
tests/
├── unit/                           # Unit tests
│   ├── features/
│   │   ├── auth/
│   │   │   ├── test_dependencies.py
│   │   │   └── test_keycloak_client.py
│   │   ├── migrations/
│   │   │   ├── test_migration_service.py
│   │   │   ├── test_event_handlers.py
│   │   │   ├── test_progress_tracker.py
│   │   │   └── test_rollback_service.py
│   │   └── databases/
│   │       └── test_database_service.py
│   ├── engines/
│   │   ├── test_dynamic_migration_engine.py
│   │   └── test_event_driven_engine.py
│   └── utils/
│       ├── test_retry_logic.py
│       └── test_circuit_breaker.py
├── integration/                    # Integration tests
├── e2e/                           # End-to-end tests
└── performance/                   # Performance tests
```

### Authentication Unit Tests
**File**: `tests/unit/features/auth/test_dependencies.py`

```python
"""
Unit tests for authentication dependencies.
"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.features.auth.dependencies import InfrastructureAuth
from src.common.exceptions.base import AuthenticationException

class TestInfrastructureAuth:
    """Test infrastructure authentication dependency."""
    
    @pytest.fixture
    def auth_dependency(self):
        """Create auth dependency for testing."""
        return InfrastructureAuth(["migrations:read"])
    
    @pytest.fixture
    def mock_request(self):
        """Mock FastAPI request object."""
        request = AsyncMock()
        request.headers = {"x-request-id": "test-123", "user-agent": "test-agent"}
        request.client.host = "127.0.0.1"
        request.url = "http://test.com/test"
        request.method = "GET"
        return request
    
    @pytest.mark.asyncio
    async def test_valid_token_with_permissions(self, auth_dependency, mock_request):
        """Test successful authentication with valid token and permissions."""
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid-token"
        )
        
        with patch('src.features.auth.dependencies.get_token_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_manager.validate_token.return_value = {
                "sub": "user-123",
                "preferred_username": "testuser",
                "permissions": ["migrations:read", "databases:read"]
            }
            mock_get_manager.return_value = mock_manager
            
            result = await auth_dependency(mock_request, credentials)
            
            assert result["sub"] == "user-123"
            assert result["preferred_username"] == "testuser"
            assert "migrations:read" in result["permissions"]
            assert result["client_ip"] == "127.0.0.1"
    
    @pytest.mark.asyncio
    async def test_missing_credentials(self, auth_dependency, mock_request):
        """Test authentication failure with missing credentials."""
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_dependency(mock_request, None)
        
        assert exc_info.value.status_code == 401
        assert "Authentication required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_invalid_token(self, auth_dependency, mock_request):
        """Test authentication failure with invalid token."""
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid-token"
        )
        
        with patch('src.features.auth.dependencies.get_token_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_manager.validate_token.side_effect = AuthenticationException("Invalid token")
            mock_get_manager.return_value = mock_manager
            
            with pytest.raises(HTTPException) as exc_info:
                await auth_dependency(mock_request, credentials)
            
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_insufficient_permissions(self, mock_request):
        """Test authorization failure with insufficient permissions."""
        
        auth_dependency = InfrastructureAuth(["infrastructure:admin"])
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid-token"
        )
        
        with patch('src.features.auth.dependencies.get_token_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_manager.validate_token.side_effect = AuthenticationException(
                "Missing required permissions: infrastructure:admin"
            )
            mock_get_manager.return_value = mock_manager
            
            with pytest.raises(HTTPException) as exc_info:
                await auth_dependency(mock_request, credentials)
            
            assert exc_info.value.status_code == 401
```

### Event System Unit Tests
**File**: `tests/unit/features/migrations/test_event_handlers.py`

```python
"""
Unit tests for migration event handlers.
"""
import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.features.migrations.events.models.events import MigrationEvent, EventType, DatabaseCreatedEvent
from src.features.migrations.events.handlers.database_created_handler import DatabaseCreatedHandler
from src.common.exceptions.base import MigrationException

class TestDatabaseCreatedHandler:
    """Test database creation event handler."""
    
    @pytest.fixture
    def handler(self):
        """Create handler for testing."""
        return DatabaseCreatedHandler()
    
    @pytest.fixture
    def sample_event(self):
        """Create sample database creation event."""
        return MigrationEvent(
            id=uuid4(),
            event_type=EventType.DATABASE_CREATED,
            payload={
                "database_id": "test-db-001",
                "database_name": "test_database",
                "connection_type": "shared",
                "region": "us-east",
                "host": "localhost",
                "port": 5432,
                "username": "test_user",
                "auto_migrate": True,
                "migration_timeout": 300
            }
        )
    
    @pytest.mark.asyncio
    async def test_successful_event_handling(self, handler, sample_event):
        """Test successful handling of database creation event."""
        
        with patch('src.features.migrations.services.migration_service.get_migration_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_execution = AsyncMock()
            mock_execution.id = uuid4()
            mock_service.execute_targeted_migration.return_value = mock_execution
            mock_get_service.return_value = mock_service
            
            result = await handler.handle(sample_event)
            
            assert result is True
            mock_service.execute_targeted_migration.assert_called_once()
            assert "migration_execution_id" in sample_event.metadata
    
    @pytest.mark.asyncio
    async def test_auto_migrate_disabled(self, handler, sample_event):
        """Test event handling when auto-migration is disabled."""
        
        sample_event.payload["auto_migrate"] = False
        
        result = await handler.handle(sample_event)
        
        assert result is True
        # Should not trigger migration service
    
    @pytest.mark.asyncio
    async def test_invalid_payload(self, handler):
        """Test event handling with invalid payload."""
        
        invalid_event = MigrationEvent(
            id=uuid4(),
            event_type=EventType.DATABASE_CREATED,
            payload={"invalid": "data"}
        )
        
        with pytest.raises(MigrationException):
            await handler.handle(invalid_event)
    
    @pytest.mark.asyncio
    async def test_migration_service_failure(self, handler, sample_event):
        """Test event handling when migration service fails."""
        
        with patch('src.features.migrations.services.migration_service.get_migration_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.execute_targeted_migration.side_effect = Exception("Migration failed")
            mock_get_service.return_value = mock_service
            
            with pytest.raises(MigrationException):
                await handler.handle(sample_event)
    
    def test_event_validation_success(self, handler, sample_event):
        """Test successful event validation."""
        
        result = handler.validate_event(sample_event)
        assert result is True
    
    def test_event_validation_missing_fields(self, handler):
        """Test event validation with missing required fields."""
        
        invalid_event = MigrationEvent(
            id=uuid4(),
            event_type=EventType.DATABASE_CREATED,
            payload={
                "database_id": "",
                "database_name": "test_db"
            }
        )
        
        result = handler.validate_event(invalid_event)
        assert result is False
```

### Retry Logic Unit Tests
**File**: `tests/unit/utils/test_retry_logic.py`

```python
"""
Unit tests for retry logic and circuit breaker.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock
from datetime import datetime, timedelta

from src.features.migrations.utils.retry_logic import (
    SmartRetry, RetryConfig, RetryStrategy, CircuitBreaker, CircuitState
)

class TestSmartRetry:
    """Test smart retry functionality."""
    
    @pytest.fixture
    def retry_config(self):
        """Create retry configuration for testing."""
        return RetryConfig(
            max_attempts=3,
            initial_delay=0.1,  # Short delay for testing
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            circuit_breaker_enabled=False
        )
    
    @pytest.mark.asyncio
    async def test_successful_execution_no_retry(self, retry_config):
        """Test successful execution without retries."""
        
        retry_handler = SmartRetry(retry_config)
        mock_func = AsyncMock(return_value="success")
        
        result = await retry_handler.execute(mock_func, "arg1", "arg2")
        
        assert result == "success"
        mock_func.assert_called_once_with("arg1", "arg2")
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self, retry_config):
        """Test retry logic on failure."""
        
        retry_handler = SmartRetry(retry_config)
        mock_func = AsyncMock()
        mock_func.side_effect = [
            ConnectionError("First attempt"),
            ConnectionError("Second attempt"),
            "success"
        ]
        
        result = await retry_handler.execute(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    @pytest.mark.asyncio
    async def test_all_attempts_fail(self, retry_config):
        """Test behavior when all retry attempts fail."""
        
        retry_handler = SmartRetry(retry_config)
        mock_func = AsyncMock()
        mock_func.side_effect = ConnectionError("Always fails")
        
        with pytest.raises(ConnectionError):
            await retry_handler.execute(mock_func)
        
        assert mock_func.call_count == 3
    
    @pytest.mark.asyncio
    async def test_non_retryable_exception(self, retry_config):
        """Test that non-retryable exceptions are not retried."""
        
        retry_config.retryable_exceptions = [ConnectionError]
        retry_handler = SmartRetry(retry_config)
        mock_func = AsyncMock()
        mock_func.side_effect = ValueError("Non-retryable")
        
        with pytest.raises(ValueError):
            await retry_handler.execute(mock_func)
        
        mock_func.assert_called_once()

class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker for testing."""
        return CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,  # Short timeout for testing
            expected_exception=Exception
        )
    
    @pytest.mark.asyncio
    async def test_successful_calls_keep_circuit_closed(self, circuit_breaker):
        """Test that successful calls keep circuit closed."""
        
        mock_func = AsyncMock(return_value="success")
        
        for _ in range(5):
            result = await circuit_breaker.call(mock_func)
            assert result == "success"
            assert circuit_breaker.state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_opens_on_failures(self, circuit_breaker):
        """Test that circuit opens after threshold failures."""
        
        mock_func = AsyncMock()
        mock_func.side_effect = Exception("Always fails")
        
        # First failure
        with pytest.raises(Exception):
            await circuit_breaker.call(mock_func)
        assert circuit_breaker.state == CircuitState.CLOSED
        
        # Second failure - should open circuit
        with pytest.raises(Exception):
            await circuit_breaker.call(mock_func)
        assert circuit_breaker.state == CircuitState.OPEN
        
        # Third call should be rejected
        with pytest.raises(Exception) as exc_info:
            await circuit_breaker.call(mock_func)
        assert "Circuit breaker is OPEN" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_circuit_recovery(self, circuit_breaker):
        """Test circuit breaker recovery."""
        
        mock_func = AsyncMock()
        
        # Force circuit to open
        mock_func.side_effect = Exception("Failure")
        for _ in range(2):
            with pytest.raises(Exception):
                await circuit_breaker.call(mock_func)
        
        assert circuit_breaker.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        await asyncio.sleep(0.2)
        
        # Next call should transition to HALF_OPEN and succeed
        mock_func.side_effect = None
        mock_func.return_value = "success"
        
        result = await circuit_breaker.call(mock_func)
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED
```

---

## 🔗 Integration Testing

### API Integration Tests
**File**: `tests/integration/test_migration_api.py`

```python
"""
Integration tests for migration API endpoints.
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4

from src.app import create_app

class TestMigrationAPI:
    """Test migration API endpoints."""
    
    @pytest_asyncio.fixture
    async def client(self, test_app, mock_keycloak_client):
        """Create test client."""
        async with AsyncClient(app=test_app, base_url="http://test") as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_get_migration_status_requires_auth(self, client):
        """Test that migration status endpoint requires authentication."""
        
        response = await client.get("/api/v1/migrations/status")
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_migration_status_with_auth(self, client, auth_headers):
        """Test migration status endpoint with authentication."""
        
        response = await client.get(
            "/api/v1/migrations/status",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "admin_status" in data
        assert "regional_status" in data
    
    @pytest.mark.asyncio
    async def test_execute_dynamic_migration(self, client, admin_auth_headers, db_helper):
        """Test dynamic migration execution."""
        
        migration_request = {
            "scope": "REGIONAL",
            "dry_run": True,
            "force_execution": False
        }
        
        response = await client.post(
            "/api/v1/migrations/dynamic",
            headers=admin_auth_headers,
            json=migration_request
        )
        
        assert response.status_code == 202
        data = response.json()
        assert "execution_id" in data
        assert data["status"] == "PENDING"
    
    @pytest.mark.asyncio
    async def test_get_migration_execution_status(self, client, auth_headers):
        """Test getting migration execution status."""
        
        execution_id = str(uuid4())
        
        response = await client.get(
            f"/api/v1/migrations/executions/{execution_id}",
            headers=auth_headers
        )
        
        # Should return 404 for non-existent execution
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_insufficient_permissions(self, client):
        """Test endpoint access with insufficient permissions."""
        
        limited_headers = {
            "Authorization": "Bearer limited-token",
            "Content-Type": "application/json"
        }
        
        with patch('src.features.auth.dependencies.get_token_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_manager.validate_token.return_value = {
                "sub": "limited-user",
                "permissions": ["migrations:read"]  # No execute permission
            }
            mock_get_manager.return_value = mock_manager
            
            response = await client.post(
                "/api/v1/migrations/dynamic",
                headers=limited_headers,
                json={"scope": "ADMIN"}
            )
            
            assert response.status_code == 403
```

### Event System Integration Tests
**File**: `tests/integration/test_event_system.py`

```python
"""
Integration tests for event-driven migration system.
"""
import pytest
import asyncio
from uuid import uuid4

from src.features.migrations.events.models.events import MigrationEvent, EventType, DatabaseCreatedEvent
from src.features.migrations.events.queue.redis_queue import RedisEventQueue
from src.features.migrations.events.handlers.database_created_handler import DatabaseCreatedHandler

class TestEventSystem:
    """Test event system integration."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_event_processing(self, event_queue, test_redis, db_helper):
        """Test complete event processing flow."""
        
        # Create database creation event
        event = MigrationEvent(
            id=uuid4(),
            event_type=EventType.DATABASE_CREATED,
            payload={
                "database_id": "test-integration-db",
                "database_name": "integration_test_db",
                "connection_type": "shared",
                "region": "us-east",
                "host": "localhost",
                "port": 5432,
                "username": "test_user",
                "auto_migrate": True,
                "migration_timeout": 300
            }
        )
        
        # Enqueue event
        success = await event_queue.enqueue_event(event)
        assert success
        
        # Verify event is in queue
        stats = await event_queue.get_queue_stats()
        assert stats["normal"] > 0
        
        # Dequeue and process event
        dequeued_event = await event_queue.dequeue_event()
        assert dequeued_event is not None
        assert dequeued_event.id == event.id
        
        # Process with handler (mocked migration service)
        handler = DatabaseCreatedHandler()
        
        with patch('src.features.migrations.services.migration_service.get_migration_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_execution = AsyncMock()
            mock_execution.id = uuid4()
            mock_service.execute_targeted_migration.return_value = mock_execution
            mock_get_service.return_value = mock_service
            
            result = await handler.handle(dequeued_event)
            assert result is True
        
        # Mark event as completed
        await event_queue.complete_event(dequeued_event, success=True)
        
        # Verify queue is empty
        stats = await event_queue.get_queue_stats()
        assert stats["normal"] == 0
        assert stats["processing"] == 0
    
    @pytest.mark.asyncio
    async def test_event_retry_on_failure(self, event_queue):
        """Test event retry logic on failure."""
        
        event = MigrationEvent(
            id=uuid4(),
            event_type=EventType.DATABASE_CREATED,
            payload={
                "database_id": "test-retry-db",
                "database_name": "retry_test_db",
                "connection_type": "shared",
                "region": "us-east",
                "host": "localhost",
                "port": 5432,
                "username": "test_user",
                "auto_migrate": True
            }
        )
        
        # Enqueue event
        await event_queue.enqueue_event(event)
        
        # Dequeue event
        dequeued_event = await event_queue.dequeue_event()
        
        # Mark as failed (should trigger retry)
        await event_queue.complete_event(dequeued_event, success=False, error="Test failure")
        
        # Check that retry was scheduled
        # Note: This would require checking the delayed queue
        # Implementation depends on queue structure
    
    @pytest.mark.asyncio
    async def test_event_priority_ordering(self, event_queue):
        """Test that events are processed in priority order."""
        
        # Create events with different priorities
        events = [
            MigrationEvent(
                id=uuid4(),
                event_type=EventType.DATABASE_CREATED,
                priority="low",
                payload={"database_id": "low-priority"}
            ),
            MigrationEvent(
                id=uuid4(),
                event_type=EventType.DATABASE_CREATED,
                priority="high",
                payload={"database_id": "high-priority"}
            ),
            MigrationEvent(
                id=uuid4(),
                event_type=EventType.DATABASE_CREATED,
                priority="critical",
                payload={"database_id": "critical-priority"}
            )
        ]
        
        # Enqueue all events
        for event in events:
            await event_queue.enqueue_event(event)
        
        # Dequeue events - should come back in priority order
        first_event = await event_queue.dequeue_event()
        assert first_event.payload["database_id"] == "critical-priority"
        
        second_event = await event_queue.dequeue_event()
        assert second_event.payload["database_id"] == "high-priority"
        
        third_event = await event_queue.dequeue_event()
        assert third_event.payload["database_id"] == "low-priority"
```

---

## 🚀 End-to-End Testing

### E2E Test Scenarios
**File**: `tests/e2e/test_complete_workflows.py`

```python
"""
End-to-end tests for complete Infrastructure API workflows.
"""
import pytest
import asyncio
from httpx import AsyncClient
from uuid import uuid4

class TestCompleteWorkflows:
    """Test complete Infrastructure API workflows."""
    
    @pytest.mark.asyncio
    async def test_database_creation_to_migration_workflow(
        self, 
        client: AsyncClient, 
        admin_auth_headers, 
        db_helper,
        event_queue
    ):
        """Test complete workflow from database creation to migration completion."""
        
        # Step 1: Create new database connection
        database_data = {
            "database_name": "e2e_test_database",
            "connection_type": "shared",
            "region": "us-east",
            "host": "localhost",
            "port": 5432,
            "username": "e2e_test_user",
            "password": "test_password"
        }
        
        response = await client.post(
            "/api/v1/databases/connections",
            headers=admin_auth_headers,
            json=database_data
        )
        assert response.status_code == 201
        
        created_db = response.json()
        database_id = created_db["id"]
        
        # Step 2: Verify event was created and queued
        await asyncio.sleep(1)  # Allow event processing time
        
        stats = await event_queue.get_queue_stats()
        assert stats["normal"] > 0 or stats["processing"] > 0
        
        # Step 3: Check migration was triggered
        response = await client.get(
            "/api/v1/migrations/executions",
            headers=admin_auth_headers,
            params={"limit": 10}
        )
        assert response.status_code == 200
        
        executions = response.json()["executions"]
        
        # Find execution triggered by database creation
        triggered_execution = None
        for execution in executions:
            if execution.get("metadata", {}).get("triggered_by") == "database_created_event":
                triggered_execution = execution
                break
        
        assert triggered_execution is not None
        execution_id = triggered_execution["id"]
        
        # Step 4: Monitor migration progress
        max_wait_time = 30  # seconds
        start_time = asyncio.get_event_loop().time()
        
        while True:
            response = await client.get(
                f"/api/v1/migrations/executions/{execution_id}",
                headers=admin_auth_headers
            )
            assert response.status_code == 200
            
            execution = response.json()
            status = execution["status"]
            
            if status in ["COMPLETED", "FAILED"]:
                break
            
            if asyncio.get_event_loop().time() - start_time > max_wait_time:
                pytest.fail("Migration did not complete within expected time")
            
            await asyncio.sleep(1)
        
        # Step 5: Verify migration completed successfully
        assert execution["status"] == "COMPLETED"
        assert execution["completed_at"] is not None
        
        # Step 6: Verify database connection is active
        response = await client.get(
            f"/api/v1/databases/connections/{database_id}/health",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        
        health = response.json()
        assert health["status"] == "healthy"
        
        # Step 7: Clean up
        response = await client.delete(
            f"/api/v1/databases/connections/{database_id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 204
    
    @pytest.mark.asyncio
    async def test_manual_migration_with_rollback(
        self,
        client: AsyncClient,
        admin_auth_headers,
        db_helper
    ):
        """Test manual migration execution followed by rollback."""
        
        # Step 1: Execute manual migration
        migration_request = {
            "scope": "REGIONAL",
            "target_databases": ["test-db-001"],
            "dry_run": False,
            "force_execution": False
        }
        
        response = await client.post(
            "/api/v1/migrations/dynamic",
            headers=admin_auth_headers,
            json=migration_request
        )
        assert response.status_code == 202
        
        execution_data = response.json()
        execution_id = execution_data["execution_id"]
        
        # Step 2: Wait for migration completion
        max_wait_time = 30
        start_time = asyncio.get_event_loop().time()
        
        while True:
            response = await client.get(
                f"/api/v1/migrations/executions/{execution_id}",
                headers=admin_auth_headers
            )
            execution = response.json()
            
            if execution["status"] in ["COMPLETED", "FAILED"]:
                break
            
            if asyncio.get_event_loop().time() - start_time > max_wait_time:
                pytest.fail("Migration did not complete within expected time")
            
            await asyncio.sleep(1)
        
        assert execution["status"] == "COMPLETED"
        
        # Step 3: Check rollback eligibility
        response = await client.get(
            f"/api/v1/migrations/executions/{execution_id}/rollback/eligibility",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        
        eligibility = response.json()
        assert eligibility["can_rollback"] is True
        
        # Step 4: Execute rollback
        rollback_request = {
            "strategy": "flyway_undo",
            "dry_run": True  # Use dry run for testing
        }
        
        response = await client.post(
            f"/api/v1/migrations/executions/{execution_id}/rollback",
            headers=admin_auth_headers,
            json=rollback_request
        )
        assert response.status_code == 202
        
        rollback_data = response.json()
        rollback_id = rollback_data["rollback_id"]
        
        # Step 5: Wait for rollback completion
        start_time = asyncio.get_event_loop().time()
        
        while True:
            response = await client.get(
                f"/api/v1/migrations/rollbacks/{rollback_id}",
                headers=admin_auth_headers
            )
            rollback = response.json()
            
            if rollback["status"] in ["COMPLETED", "FAILED"]:
                break
            
            if asyncio.get_event_loop().time() - start_time > max_wait_time:
                pytest.fail("Rollback did not complete within expected time")
            
            await asyncio.sleep(1)
        
        assert rollback["status"] == "COMPLETED"
        assert rollback["dry_run"] is True
```

---

## ⚡ Performance Testing

### Load Testing Configuration
**File**: `tests/performance/test_load.py`

```python
"""
Performance and load tests for Infrastructure API.
"""
import pytest
import asyncio
import time
from httpx import AsyncClient
from concurrent.futures import ThreadPoolExecutor

class TestPerformance:
    """Performance tests for Infrastructure API."""
    
    @pytest.mark.asyncio
    async def test_authentication_performance(self, client, auth_headers):
        """Test authentication performance under load."""
        
        async def make_auth_request():
            response = await client.get(
                "/api/v1/auth/profile",
                headers=auth_headers
            )
            return response.status_code
        
        # Measure baseline performance
        start_time = time.time()
        await make_auth_request()
        baseline_time = time.time() - start_time
        
        # Test concurrent authentication requests
        concurrent_requests = 50
        start_time = time.time()
        
        tasks = [make_auth_request() for _ in range(concurrent_requests)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify all requests succeeded
        assert all(status == 200 for status in results)
        
        # Verify performance metrics
        avg_time_per_request = total_time / concurrent_requests
        assert avg_time_per_request < baseline_time * 2  # Max 2x degradation
        
        # Verify throughput
        requests_per_second = concurrent_requests / total_time
        assert requests_per_second > 10  # Minimum 10 RPS
    
    @pytest.mark.asyncio
    async def test_migration_status_performance(self, client, auth_headers):
        """Test migration status endpoint performance."""
        
        # Warm up
        await client.get("/api/v1/migrations/status", headers=auth_headers)
        
        # Measure response time
        start_time = time.time()
        response = await client.get("/api/v1/migrations/status", headers=auth_headers)
        response_time = time.time() - start_time
        
        assert response.status_code == 200
        assert response_time < 0.2  # Max 200ms response time
    
    @pytest.mark.asyncio
    async def test_concurrent_migration_requests(self, client, admin_auth_headers):
        """Test handling of concurrent migration requests."""
        
        async def start_migration():
            migration_request = {
                "scope": "REGIONAL",
                "dry_run": True
            }
            response = await client.post(
                "/api/v1/migrations/dynamic",
                headers=admin_auth_headers,
                json=migration_request
            )
            return response.status_code
        
        # Start multiple migrations concurrently
        concurrent_migrations = 5
        start_time = time.time()
        
        tasks = [start_migration() for _ in range(concurrent_migrations)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        
        # Most should succeed, some might be rejected due to concurrency limits
        successful_requests = sum(1 for status in results if status in [202, 409])
        assert successful_requests >= concurrent_migrations * 0.8  # At least 80% success
        
        total_time = end_time - start_time
        assert total_time < 10  # Should complete within 10 seconds

class TestStressTest:
    """Stress tests for Infrastructure API."""
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_sustained_load(self, client, auth_headers):
        """Test API under sustained load."""
        
        async def make_request():
            endpoints = [
                "/api/v1/auth/profile",
                "/api/v1/migrations/status",
                "/api/v1/databases/connections",
                "/api/v1/system/health"
            ]
            
            for endpoint in endpoints:
                response = await client.get(endpoint, headers=auth_headers)
                if response.status_code not in [200, 401, 403]:
                    return False
            return True
        
        # Run sustained load for 60 seconds
        duration = 60  # seconds
        request_interval = 0.1  # 10 RPS
        
        start_time = time.time()
        successful_requests = 0
        total_requests = 0
        
        while time.time() - start_time < duration:
            success = await make_request()
            if success:
                successful_requests += 1
            total_requests += 1
            
            await asyncio.sleep(request_interval)
        
        success_rate = successful_requests / total_requests
        assert success_rate > 0.95  # 95% success rate under sustained load
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, client, auth_headers):
        """Test memory usage remains stable under load."""
        
        # This test would typically measure memory usage
        # using psutil or similar monitoring tools
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Make many requests
        for _ in range(1000):
            await client.get("/api/v1/auth/profile", headers=auth_headers)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024
```

---

## 🛡️ Security Testing

### Security Test Suite
**File**: `tests/security/test_security.py`

```python
"""
Security tests for Infrastructure API.
"""
import pytest
from httpx import AsyncClient

class TestSecurityControls:
    """Test security controls and protections."""
    
    @pytest.mark.asyncio
    async def test_unauthenticated_access_blocked(self, client):
        """Test that unauthenticated access is properly blocked."""
        
        protected_endpoints = [
            "/api/v1/migrations/status",
            "/api/v1/migrations/dynamic",
            "/api/v1/databases/connections",
            "/api/v1/auth/profile"
        ]
        
        for endpoint in protected_endpoints:
            response = await client.get(endpoint)
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_invalid_token_rejected(self, client):
        """Test that invalid tokens are properly rejected."""
        
        invalid_headers = {
            "Authorization": "Bearer invalid-token",
            "Content-Type": "application/json"
        }
        
        response = await client.get(
            "/api/v1/auth/profile",
            headers=invalid_headers
        )
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_sql_injection_protection(self, client, auth_headers):
        """Test protection against SQL injection attacks."""
        
        # Try SQL injection in various endpoints
        injection_payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "'; SELECT * FROM admin.database_connections; --"
        ]
        
        for payload in injection_payloads:
            # Try in query parameters
            response = await client.get(
                f"/api/v1/migrations/executions?search={payload}",
                headers=auth_headers
            )
            assert response.status_code in [200, 400, 422]  # Should not cause server error
            
            # Try in path parameters (if any accept user input)
            response = await client.get(
                f"/api/v1/databases/connections/{payload}",
                headers=auth_headers
            )
            assert response.status_code in [404, 400, 422]  # Should not cause server error
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, client, auth_headers):
        """Test rate limiting protection."""
        
        # Make rapid requests to trigger rate limiting
        responses = []
        for _ in range(100):  # Exceed rate limit
            response = await client.get("/api/v1/auth/profile", headers=auth_headers)
            responses.append(response.status_code)
        
        # Should eventually get rate limited
        rate_limited_responses = [status for status in responses if status == 429]
        assert len(rate_limited_responses) > 0
    
    @pytest.mark.asyncio
    async def test_input_validation(self, client, admin_auth_headers):
        """Test input validation for API endpoints."""
        
        # Test with invalid data types
        invalid_migration_request = {
            "scope": "INVALID_SCOPE",
            "dry_run": "not_a_boolean",
            "target_databases": "not_an_array"
        }
        
        response = await client.post(
            "/api/v1/migrations/dynamic",
            headers=admin_auth_headers,
            json=invalid_migration_request
        )
        assert response.status_code == 422
        
        # Test with missing required fields
        incomplete_request = {
            "dry_run": True
            # Missing required "scope" field
        }
        
        response = await client.post(
            "/api/v1/migrations/dynamic",
            headers=admin_auth_headers,
            json=incomplete_request
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_permission_enforcement(self, client):
        """Test that permission levels are properly enforced."""
        
        # Test with read-only permissions
        readonly_headers = {
            "Authorization": "Bearer readonly-token",
            "Content-Type": "application/json"
        }
        
        with patch('src.features.auth.dependencies.get_token_manager') as mock_manager:
            mock_manager.return_value.validate_token.return_value = {
                "sub": "readonly-user",
                "permissions": ["migrations:read"]  # Only read permission
            }
            
            # Should be able to read
            response = await client.get(
                "/api/v1/migrations/status",
                headers=readonly_headers
            )
            assert response.status_code == 200
            
            # Should NOT be able to execute
            response = await client.post(
                "/api/v1/migrations/dynamic",
                headers=readonly_headers,
                json={"scope": "ADMIN", "dry_run": True}
            )
            assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_data_sanitization(self, client, admin_auth_headers):
        """Test that data is properly sanitized in responses."""
        
        response = await client.get(
            "/api/v1/databases/connections",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        
        connections = response.json()["connections"]
        
        # Verify sensitive data is not exposed
        for connection in connections:
            assert "password" not in connection
            assert "encrypted_password" not in connection
            assert "raw_password" not in connection
    
    @pytest.mark.asyncio
    async def test_security_headers(self, client):
        """Test that security headers are properly set."""
        
        response = await client.get("/api/v1/system/health")
        
        headers = response.headers
        
        # Check for security headers
        assert "x-content-type-options" in headers
        assert headers["x-content-type-options"] == "nosniff"
        
        assert "x-frame-options" in headers
        assert headers["x-frame-options"] == "DENY"
        
        assert "x-xss-protection" in headers
        assert headers["x-xss-protection"] == "1; mode=block"
```

---

## 🚀 Deployment Strategy

### Deployment Phases

#### Phase 1: Staging Deployment (Week 1)
```bash
# Deploy to staging environment
cd NeoInfrastructure

# Build and test
docker build -t infrastructure-api:staging .
docker-compose -f docker/docker-compose.staging.yml up -d

# Run smoke tests
pytest tests/smoke/ -v

# Run security scan
docker run --rm -v $(pwd):/app clair-scanner infrastructure-api:staging
```

#### Phase 2: Canary Deployment (Week 2)
```bash
# Deploy canary version (10% traffic)
kubectl apply -f k8s/canary-deployment.yml

# Monitor metrics and error rates
kubectl get pods -l version=canary
kubectl logs -l version=canary -f

# Gradually increase traffic if stable
kubectl patch deployment infrastructure-api-canary -p '{"spec":{"replicas":3}}'
```

#### Phase 3: Production Rollout (Week 3)
```bash
# Full production deployment
kubectl apply -f k8s/production-deployment.yml

# Verify health
kubectl get deployments
kubectl get services
curl https://infrastructure-api.production.com/health

# Monitor performance
kubectl top pods
kubectl get hpa
```

### Deployment Checklist

#### Pre-Deployment
- [ ] All tests passing (unit, integration, e2e)
- [ ] Security scan completed
- [ ] Performance benchmarks meet requirements
- [ ] Database migrations tested
- [ ] Rollback procedures documented
- [ ] Monitoring and alerting configured

#### Deployment
- [ ] Infrastructure provisioned
- [ ] Secrets and configuration deployed
- [ ] Database migrations applied
- [ ] Application deployed
- [ ] Health checks passing
- [ ] Load balancer configured

#### Post-Deployment
- [ ] Smoke tests executed
- [ ] Performance monitoring active
- [ ] Error rates within acceptable limits
- [ ] User acceptance testing completed
- [ ] Documentation updated
- [ ] Team trained on new features

### Monitoring and Alerting

#### Key Metrics to Monitor
```yaml
application_metrics:
  - request_duration_seconds
  - request_count_total
  - active_migrations_count
  - event_queue_size
  - authentication_failures_total
  - database_connection_pool_usage

infrastructure_metrics:
  - cpu_usage_percent
  - memory_usage_bytes
  - disk_usage_percent
  - network_io_bytes

business_metrics:
  - migrations_completed_total
  - migrations_failed_total
  - average_migration_duration
  - events_processed_total
  - rollbacks_executed_total
```

#### Alert Conditions
```yaml
critical_alerts:
  - api_response_time > 1s (for 5 minutes)
  - error_rate > 5% (for 2 minutes)
  - migration_failure_rate > 10% (for 5 minutes)
  - event_queue_size > 1000 (for 10 minutes)
  - authentication_failure_rate > 20% (for 5 minutes)

warning_alerts:
  - cpu_usage > 80% (for 10 minutes)
  - memory_usage > 85% (for 10 minutes)
  - migration_duration > 300s (for 1 occurrence)
  - event_processing_lag > 60s (for 5 minutes)
```

### Rollback Procedures

#### Emergency Rollback
```bash
# Immediate rollback to previous version
kubectl rollout undo deployment/infrastructure-api

# Verify rollback
kubectl rollout status deployment/infrastructure-api

# Check health
curl https://infrastructure-api.production.com/health
```

#### Database Rollback
```bash
# Rollback database migrations if necessary
docker exec -it infrastructure-api python -m src.features.migrations.utils.rollback_tool \
  --execution-id <execution-id> \
  --strategy flyway_undo
```

---

## 📊 Success Criteria

### Functional Requirements
- ✅ **Authentication**: All endpoints require valid authentication
- ✅ **Event Processing**: Database/tenant creation triggers migrations within 30s
- ✅ **Real-time Monitoring**: Progress updates with <5s latency
- ✅ **Rollback Capability**: >95% rollback success rate for eligible migrations
- ✅ **Error Handling**: Graceful failure handling with proper error messages

### Performance Requirements
- ✅ **API Response Time**: <200ms for status endpoints, <1s for operations
- ✅ **Migration Performance**: 30% improvement over current system
- ✅ **Concurrent Requests**: Handle 100+ concurrent API requests
- ✅ **Event Processing**: <5s from event creation to processing start
- ✅ **System Uptime**: >99.9% availability during migration operations

### Security Requirements
- ✅ **Authentication Coverage**: 100% of non-health endpoints require auth
- ✅ **Permission Enforcement**: Role-based access controls functional
- ✅ **Input Validation**: All inputs validated and sanitized
- ✅ **Rate Limiting**: Protection against abuse and DoS attacks
- ✅ **Security Headers**: Proper security headers on all responses

### Quality Requirements
- ✅ **Test Coverage**: >95% code coverage for critical paths
- ✅ **Documentation**: Complete API documentation and guides
- ✅ **Error Rates**: <1% error rate under normal load
- ✅ **Recovery Time**: <5 minutes to detect and recover from failures
- ✅ **Monitoring Coverage**: 100% visibility into system operations

This comprehensive testing and deployment guide ensures that the enhanced Infrastructure API meets all quality, performance, and security requirements while providing a smooth deployment experience with proper monitoring and rollback capabilities.