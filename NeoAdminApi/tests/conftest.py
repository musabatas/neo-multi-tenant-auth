"""Test configuration and fixtures for NeoAdminApi."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from neo_commons.core.value_objects.identifiers import UserId, TenantId, RealmId
from neo_commons.features.auth.entities.auth_context import AuthContext
from neo_commons.features.auth.entities.jwt_token import JWTToken
from neo_commons.features.auth import AuthServiceFactory

from src.app import create_app


@pytest.fixture
def mock_auth_factory():
    """Mock auth service factory."""
    factory = MagicMock(spec=AuthServiceFactory)
    
    # Mock services
    factory.get_auth_cache = AsyncMock()
    factory.get_realm_repository = MagicMock()
    factory.get_user_mapping_repository = MagicMock()
    factory.get_keycloak_service = MagicMock()
    factory.get_jwt_validator = AsyncMock()
    factory.get_realm_manager = AsyncMock()
    factory.get_user_mapper = AsyncMock()
    factory.get_token_service = AsyncMock()
    factory.get_auth_service = AsyncMock()
    factory.get_auth_dependencies = AsyncMock()
    factory.initialize_all_services = AsyncMock()
    factory.cleanup = AsyncMock()
    
    return factory


@pytest.fixture
def mock_auth_context():
    """Mock authenticated admin user context."""
    from datetime import datetime, timezone
    from neo_commons.core.value_objects.identifiers import (
        UserId, TenantId, RealmId, PermissionCode, RoleCode
    )
    
    return AuthContext(
        user_id=UserId("550e8400-e29b-41d4-a716-446655440000"),
        keycloak_user_id=UserId("550e8400-e29b-41d4-a716-446655440001"),
        tenant_id=TenantId("platform"),
        realm_id=RealmId("platform"),
        username="admin",
        email="admin@platform.com",
        first_name="Platform",
        last_name="Administrator",
        display_name="Platform Administrator",
        roles={RoleCode("platform_admin")},
        permissions={
            PermissionCode("admin:read"),
            PermissionCode("admin:write"),
            PermissionCode("organizations:*"),
            PermissionCode("tenants:*"),
        },
        session_id="session-123",
        authenticated_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc),
        is_fresh=True,
        is_platform_admin=True,
        is_tenant_admin=False,
    )


@pytest.fixture
def mock_jwt_token():
    """Mock JWT token response."""
    return JWTToken(
        access_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.test.token",
        refresh_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.refresh.token",
        token_type="Bearer",
        expires_in=3600,
        refresh_expires_in=7200,
        scope="openid profile email",
    )


@pytest.fixture
def app():
    """Create FastAPI test app."""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(app):
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(autouse=True)
def mock_dependencies_factory(monkeypatch, mock_auth_factory):
    """Mock the dependencies factory globally."""
    from src.common.services.dependencies_factory import DependenciesFactory
    
    # Mock the global factory
    mock_factory = MagicMock(spec=DependenciesFactory)
    mock_factory.get_auth_factory = AsyncMock(return_value=mock_auth_factory)
    mock_factory.get_auth_dependencies = AsyncMock()
    mock_factory.get_database_service = AsyncMock()
    mock_factory.get_cache_service = AsyncMock()
    mock_factory.initialize_all = AsyncMock()
    mock_factory.cleanup = AsyncMock()
    
    # Patch the factory creation
    monkeypatch.setattr(
        "src.common.services.dependencies_factory.get_dependencies_factory",
        lambda: mock_factory
    )
    
    # Patch initialization functions
    monkeypatch.setattr(
        "src.common.services.dependencies_factory.initialize_dependencies",
        AsyncMock()
    )
    monkeypatch.setattr(
        "src.common.services.dependencies_factory.cleanup_dependencies",
        AsyncMock()
    )
    
    return mock_factory


@pytest.fixture
def auth_headers():
    """Create authorization headers for authenticated requests."""
    return {"Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.test.token"}