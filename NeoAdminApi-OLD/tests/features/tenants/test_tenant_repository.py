"""
Tests for tenant repository.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID
from datetime import datetime

from src.features.tenants.repositories.tenant_repository import TenantRepository
from src.features.tenants.models.domain import Tenant, TenantStatus, DeploymentType, EnvironmentType, AuthProvider
from src.common.exceptions.base import NotFoundError


@pytest.fixture
def mock_db():
    """Create mock database."""
    db = AsyncMock()
    return db


@pytest.fixture
def tenant_repository(mock_db):
    """Create tenant repository with mock database."""
    repo = TenantRepository()
    repo.db = mock_db
    return repo


@pytest.fixture
def sample_tenant_row():
    """Sample tenant database row."""
    return {
        'id': UUID('01989bd2-e795-7140-a54c-8ed28f09d31e'),
        'organization_id': UUID('01989bd2-e795-7140-a54c-8ed28f09d31f'),
        'slug': 'test-tenant',
        'name': 'Test Tenant',
        'description': 'Test tenant description',
        'schema_name': 'tenant_test',
        'database_name': None,
        'deployment_type': 'schema',
        'environment': 'production',
        'region_id': UUID('01989bd2-e795-7140-a54c-8ed28f09d320'),
        'database_connection_id': None,
        'custom_domain': None,
        'external_auth_provider': 'keycloak',
        'external_auth_realm': 'test-realm',
        'external_user_id': 'test-user-123',
        'external_auth_metadata': {},
        'allow_impersonations': False,
        'status': 'active',
        'provisioned_at': datetime.utcnow(),
        'activated_at': datetime.utcnow(),
        'suspended_at': None,
        'last_activity_at': datetime.utcnow(),
        'features_enabled': {'feature1': True},
        'feature_overrides': {},
        'internal_notes': None,
        'metadata': {},
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        'deleted_at': None
    }


@pytest.mark.asyncio
async def test_get_by_id_success(tenant_repository, mock_db, sample_tenant_row):
    """Test successful retrieval of tenant by ID."""
    mock_db.fetchrow.return_value = sample_tenant_row
    
    tenant = await tenant_repository.get_by_id('01989bd2-e795-7140-a54c-8ed28f09d31e')
    
    assert isinstance(tenant, Tenant)
    assert tenant.id == UUID('01989bd2-e795-7140-a54c-8ed28f09d31e')
    assert tenant.slug == 'test-tenant'
    assert tenant.name == 'Test Tenant'
    assert tenant.status == TenantStatus.ACTIVE
    
    mock_db.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_get_by_id_not_found(tenant_repository, mock_db):
    """Test tenant not found by ID."""
    mock_db.fetchrow.return_value = None
    
    with pytest.raises(NotFoundError) as exc_info:
        await tenant_repository.get_by_id('01989bd2-e795-7140-a54c-8ed28f09d31e')
    
    assert "Tenant" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_by_slug_success(tenant_repository, mock_db, sample_tenant_row):
    """Test successful retrieval of tenant by slug."""
    mock_db.fetchrow.return_value = sample_tenant_row
    
    tenant = await tenant_repository.get_by_slug('test-tenant')
    
    assert isinstance(tenant, Tenant)
    assert tenant.slug == 'test-tenant'
    assert tenant.name == 'Test Tenant'
    
    mock_db.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_get_organization_info_success(tenant_repository, mock_db):
    """Test successful retrieval of organization info."""
    mock_db.fetchrow.return_value = {
        'id': UUID('01989bd2-e795-7140-a54c-8ed28f09d31f'),
        'name': 'Test Organization',
        'slug': 'test-org',
        'is_active': True
    }
    
    org_info = await tenant_repository.get_organization_info('01989bd2-e795-7140-a54c-8ed28f09d31f')
    
    assert org_info['name'] == 'Test Organization'
    assert org_info['slug'] == 'test-org'
    assert org_info['is_active'] is True
    
    mock_db.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_get_region_info_success(tenant_repository, mock_db):
    """Test successful retrieval of region info."""
    mock_db.fetchrow.return_value = {
        'id': UUID('01989bd2-e795-7140-a54c-8ed28f09d320'),
        'code': 'us-east-1',
        'name': 'US East',
        'country_code': 'US',
        'is_active': True
    }
    
    region_info = await tenant_repository.get_region_info('01989bd2-e795-7140-a54c-8ed28f09d320')
    
    assert region_info['code'] == 'us-east-1'
    assert region_info['name'] == 'US East'
    assert region_info['country_code'] == 'US'
    
    mock_db.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_get_subscription_info_success(tenant_repository, mock_db):
    """Test successful retrieval of subscription info."""
    mock_db.fetchrow.return_value = {
        'id': UUID('01989bd2-e795-7140-a54c-8ed28f09d321'),
        'plan_name': 'Professional',
        'plan_tier': 'pro',
        'status': 'active',
        'current_period_end': datetime.utcnow()
    }
    
    sub_info = await tenant_repository.get_subscription_info('01989bd2-e795-7140-a54c-8ed28f09d31e')
    
    assert sub_info['plan_name'] == 'Professional'
    assert sub_info['plan_tier'] == 'pro'
    assert sub_info['status'] == 'active'
    
    mock_db.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_get_subscription_info_not_found(tenant_repository, mock_db):
    """Test subscription not found returns None."""
    mock_db.fetchrow.return_value = None
    
    sub_info = await tenant_repository.get_subscription_info('01989bd2-e795-7140-a54c-8ed28f09d31e')
    
    assert sub_info is None
    mock_db.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_get_tenant_stats(tenant_repository):
    """Test retrieval of tenant statistics."""
    stats = await tenant_repository.get_tenant_stats('01989bd2-e795-7140-a54c-8ed28f09d31e')
    
    assert stats['user_count'] == 0
    assert stats['active_user_count'] == 0
    assert stats['storage_used_mb'] == 0.0