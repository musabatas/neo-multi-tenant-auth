"""
Tests for tenant service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID
from datetime import datetime

from src.features.tenants.services.tenant_service import TenantService
from src.features.tenants.models.domain import Tenant, TenantStatus
from src.features.tenants.models.response import TenantResponse, OrganizationSummary, RegionSummary
from src.common.exceptions.base import NotFoundError


@pytest.fixture
def mock_repository():
    """Create mock tenant repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_cache():
    """Create mock cache client."""
    cache = AsyncMock()
    cache.get.return_value = None  # Default to no cache
    return cache


@pytest.fixture
def tenant_service(mock_repository, mock_cache):
    """Create tenant service with mocks."""
    service = TenantService()
    service.repository = mock_repository
    service.cache = mock_cache
    return service


@pytest.fixture
def sample_tenant():
    """Sample tenant domain model."""
    return Tenant(
        id=UUID('01989bd2-e795-7140-a54c-8ed28f09d31e'),
        organization_id=UUID('01989bd2-e795-7140-a54c-8ed28f09d31f'),
        slug='test-tenant',
        name='Test Tenant',
        description='Test tenant description',
        schema_name='tenant_test',
        database_name=None,
        deployment_type='schema',
        environment='production',
        region_id=UUID('01989bd2-e795-7140-a54c-8ed28f09d320'),
        database_connection_id=None,
        custom_domain=None,
        external_auth_provider='keycloak',
        external_auth_realm='test-realm',
        external_user_id='test-user-123',
        external_auth_metadata={},
        allow_impersonations=False,
        status=TenantStatus.ACTIVE,
        provisioned_at=datetime.utcnow(),
        activated_at=datetime.utcnow(),
        suspended_at=None,
        last_activity_at=datetime.utcnow(),
        features_enabled={'feature1': True},
        feature_overrides={},
        internal_notes=None,
        metadata={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        deleted_at=None
    )


@pytest.mark.asyncio
async def test_get_tenant_success(tenant_service, mock_repository, mock_cache, sample_tenant):
    """Test successful retrieval of tenant."""
    # Setup mocks
    mock_repository.get_by_id.return_value = sample_tenant
    mock_repository.get_organization_info.return_value = {
        'id': '01989bd2-e795-7140-a54c-8ed28f09d31f',
        'name': 'Test Organization',
        'slug': 'test-org',
        'is_active': True
    }
    mock_repository.get_region_info.return_value = {
        'id': '01989bd2-e795-7140-a54c-8ed28f09d320',
        'code': 'us-east-1',
        'name': 'US East',
        'country_code': 'US',
        'is_active': True
    }
    mock_repository.get_subscription_info.return_value = {
        'id': '01989bd2-e795-7140-a54c-8ed28f09d321',
        'plan_name': 'Professional',
        'plan_tier': 'pro',
        'status': 'active',
        'current_period_end': datetime.utcnow()
    }
    mock_repository.get_tenant_stats.return_value = {
        'user_count': 10,
        'active_user_count': 8,
        'storage_used_mb': 100.5
    }
    
    # Call service
    result = await tenant_service.get_tenant('01989bd2-e795-7140-a54c-8ed28f09d31e')
    
    # Assertions
    assert isinstance(result, TenantResponse)
    assert result.slug == 'test-tenant'
    assert result.name == 'Test Tenant'
    assert result.organization.name == 'Test Organization'
    assert result.region.code == 'us-east-1'
    assert result.subscription.plan_name == 'Professional'
    assert result.user_count == 10
    assert result.active_user_count == 8
    assert result.storage_used_mb == 100.5
    
    # Verify caching
    mock_cache.set.assert_called_once()


@pytest.mark.asyncio
async def test_get_tenant_from_cache(tenant_service, mock_repository, mock_cache):
    """Test retrieval of tenant from cache."""
    # Setup cache to return complete data
    cached_data = {
        'id': '01989bd2-e795-7140-a54c-8ed28f09d31e',
        'slug': 'test-tenant',
        'name': 'Test Tenant',
        'description': 'Test tenant description',
        'schema_name': 'tenant_test',
        'database_name': None,
        'deployment_type': 'schema',
        'environment': 'production',
        'region': {
            'id': '01989bd2-e795-7140-a54c-8ed28f09d320',
            'code': 'us-east-1',
            'name': 'US East',
            'country_code': 'US',
            'is_active': True
        },
        'custom_domain': None,
        'external_auth_provider': 'keycloak',
        'external_auth_realm': 'test-realm',
        'allow_impersonations': False,
        'status': 'active',
        'provisioned_at': '2024-01-01T00:00:00Z',
        'activated_at': '2024-01-01T00:00:00Z',
        'suspended_at': None,
        'last_activity_at': '2024-01-01T00:00:00Z',
        'subscription': None,
        'features_enabled': {},
        'feature_overrides': {},
        'internal_notes': None,
        'metadata': {},
        'created_at': '2024-01-01T00:00:00Z',
        'updated_at': '2024-01-01T00:00:00Z',
        'user_count': 0,
        'active_user_count': 0,
        'storage_used_mb': 0.0,
        'organization': {
            'id': '01989bd2-e795-7140-a54c-8ed28f09d31f',
            'name': 'Test Organization',
            'slug': 'test-org',
            'is_active': True
        }
    }
    mock_cache.get.return_value = cached_data
    
    # Call service
    result = await tenant_service.get_tenant('01989bd2-e795-7140-a54c-8ed28f09d31e')
    
    # Assertions
    assert isinstance(result, TenantResponse)
    assert result.slug == 'test-tenant'
    
    # Repository should not be called
    mock_repository.get_by_id.assert_not_called()


@pytest.mark.asyncio
async def test_get_tenant_not_found(tenant_service, mock_repository):
    """Test tenant not found."""
    mock_repository.get_by_id.side_effect = NotFoundError("Tenant", "01989bd2-e795-7140-a54c-8ed28f09d31e")
    
    with pytest.raises(NotFoundError) as exc_info:
        await tenant_service.get_tenant('01989bd2-e795-7140-a54c-8ed28f09d31e')
    
    assert "Tenant" in str(exc_info.value)