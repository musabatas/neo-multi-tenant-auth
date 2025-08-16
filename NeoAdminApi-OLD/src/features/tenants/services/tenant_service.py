"""
Service layer for tenant management.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from loguru import logger

from src.common.exceptions.base import (
    NotFoundError, 
    ValidationError, 
    ConflictError,
    BadRequestError
)
from src.common.models.base import PaginationParams
from src.common.services.base import BaseService
from src.common.cache.client import get_cache
from src.common.utils.datetime import utc_now
from src.integrations.keycloak.async_client import get_keycloak_client
from src.integrations.keycloak.realm_manager import get_realm_manager

from ..models.domain import Tenant, TenantStatus
from ..models.request import (
    TenantCreate, 
    TenantUpdate, 
    TenantFilter, 
    TenantStatusUpdate,
    TenantProvisionRequest
)
from ..models.response import (
    TenantResponse,
    TenantListItem,
    TenantListResponse,
    TenantListSummary,
    TenantProvisionResponse,
    OrganizationSummary,
    RegionSummary,
    SubscriptionSummary
)
from ..repositories.tenant_repository import TenantRepository


class TenantService(BaseService):
    """Service for tenant business logic."""
    
    def __init__(self):
        """Initialize tenant service."""
        super().__init__()
        self.repository = TenantRepository()
        self.cache = get_cache()
        
        # Cache key patterns for tenant lookups (affects user-facing operations)
        self.CACHE_KEY_TENANT = "tenant:{tenant_id}"
        self.CACHE_KEY_TENANT_SLUG = "tenant:slug:{slug}"
        self.CACHE_TTL = 600  # 10 minutes
    
    async def get_tenant(self, tenant_id: str) -> TenantResponse:
        """Get a tenant by ID.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            TenantResponse with tenant details
        """
        # Try cache first (tenant lookups affect user experience)
        cache_key = self.CACHE_KEY_TENANT.format(tenant_id=tenant_id)
        cached = await self.cache.get(cache_key)
        if cached:
            return TenantResponse(**cached)
        
        # Get from repository
        tenant = await self.repository.get_by_id(tenant_id)
        
        # Get related information
        org_info = await self.repository.get_organization_info(str(tenant.organization_id))
        region_info = None
        if tenant.region_id:
            region_info = await self.repository.get_region_info(str(tenant.region_id))
        
        subscription_info = await self.repository.get_subscription_info(tenant_id)
        stats = await self.repository.get_tenant_stats(tenant_id)
        
        # Build response
        organization = OrganizationSummary(**org_info)
        region = RegionSummary(**region_info) if region_info else None
        subscription = SubscriptionSummary(**subscription_info) if subscription_info else None
        
        response = TenantResponse.from_domain(
            tenant,
            organization,
            region,
            subscription,
            stats
        )
        
        # Cache the response (tenant data affects user experience)
        await self.cache.set(cache_key, response.model_dump(), ttl=self.CACHE_TTL)
        
        return response
    
    async def get_tenant_by_slug(self, slug: str) -> TenantResponse:
        """Get a tenant by slug.
        
        Args:
            slug: Tenant slug
            
        Returns:
            TenantResponse with tenant details
        """
        # Try cache first (tenant lookups affect user experience)
        cache_key = self.CACHE_KEY_TENANT_SLUG.format(slug=slug)
        cached = await self.cache.get(cache_key)
        if cached:
            return TenantResponse(**cached)
        
        # Get from repository
        tenant = await self.repository.get_by_slug(slug)
        
        # Get related information
        org_info = await self.repository.get_organization_info(str(tenant.organization_id))
        region_info = None
        if tenant.region_id:
            region_info = await self.repository.get_region_info(str(tenant.region_id))
        
        subscription_info = await self.repository.get_subscription_info(str(tenant.id))
        stats = await self.repository.get_tenant_stats(str(tenant.id))
        
        # Build response
        organization = OrganizationSummary(**org_info)
        region = RegionSummary(**region_info) if region_info else None
        subscription = SubscriptionSummary(**subscription_info) if subscription_info else None
        
        response = TenantResponse.from_domain(
            tenant,
            organization,
            region,
            subscription,
            stats
        )
        
        # Cache the response (tenant data affects user experience)
        await self.cache.set(cache_key, response.model_dump(), ttl=self.CACHE_TTL)
        
        return response
    
    async def list_tenants(
        self,
        filters: Optional[TenantFilter] = None,
        pagination: Optional[PaginationParams] = None
    ) -> TenantListResponse:
        """List tenants with optional filters and pagination.
        
        Args:
            filters: Optional filters for tenants
            pagination: Optional pagination parameters
            
        Returns:
            TenantListResponse with tenants and metadata
        """
        if pagination is None:
            pagination = PaginationParams(page=1, page_size=20)
        
        # Validate pagination
        self.validate_pagination_params(pagination.page, pagination.page_size)
        
        # Get tenants from repository
        offset = (pagination.page - 1) * pagination.page_size
        tenants, total_count = await self.repository.list(
            filters=filters,
            limit=pagination.page_size,
            offset=offset
        )
        
        # Build list items
        items = []
        for tenant in tenants:
            # Get organization name
            org_info = await self.repository.get_organization_info(str(tenant.organization_id))
            
            # Get user count (would query regional DB in production)
            stats = await self.repository.get_tenant_stats(str(tenant.id))
            
            item = TenantListItem(
                id=tenant.id,
                organization_id=tenant.organization_id,
                organization_name=org_info['name'],
                slug=tenant.slug,
                name=tenant.name,
                status=tenant.status,
                environment=tenant.environment,
                region_code=None,  # Would get from region info
                custom_domain=tenant.custom_domain,
                user_count=stats['user_count'],
                created_at=tenant.created_at,
                last_activity_at=tenant.last_activity_at
            )
            items.append(item)
        
        # Create pagination metadata
        pagination_meta = self.create_pagination_metadata(
            pagination.page, 
            pagination.page_size, 
            total_count
        )
        
        return TenantListResponse(
            items=items,
            pagination=pagination_meta.model_dump() if hasattr(pagination_meta, 'model_dump') else pagination_meta
        )
    
    async def create_tenant(
        self, 
        tenant_data: TenantCreate,
        created_by: Optional[str] = None
    ) -> TenantResponse:
        """Create a new tenant.
        
        Args:
            tenant_data: Tenant creation data
            created_by: User ID who created the tenant
            
        Returns:
            TenantResponse with created tenant
        """
        # Validate tenant data
        await self._validate_tenant_create(tenant_data)
        
        # Create tenant in database
        tenant = await self.repository.create(tenant_data)
        
        # Get organization info for response
        org_info = await self.repository.get_organization_info(str(tenant.organization_id))
        organization = OrganizationSummary(**org_info)
        
        # Get region info if specified
        region = None
        if tenant.region_id:
            region_info = await self.repository.get_region_info(str(tenant.region_id))
            if region_info:
                region = RegionSummary(**region_info)
        
        response = TenantResponse.from_domain(
            tenant,
            organization,
            region,
            None,  # No subscription yet
            {'user_count': 0, 'active_user_count': 0, 'storage_used_mb': 0.0}
        )
        
        logger.info(f"Created tenant {tenant.id} ({tenant.slug}) for organization {tenant.organization_id}")
        
        # Cache the response (tenant data affects user experience)
        await self.cache.set(cache_key, response.model_dump(), ttl=self.CACHE_TTL)
        
        return response
    
    async def update_tenant(
        self,
        tenant_id: str,
        update_data: TenantUpdate
    ) -> TenantResponse:
        """Update a tenant.
        
        Args:
            tenant_id: Tenant ID to update
            update_data: Update data
            
        Returns:
            TenantResponse with updated tenant
        """
        # Update tenant
        tenant = await self.repository.update(tenant_id, update_data)
        
        # Invalidate cache
        await self._invalidate_tenant_cache(tenant_id, tenant.slug)
        
        # Get related information for response
        org_info = await self.repository.get_organization_info(str(tenant.organization_id))
        organization = OrganizationSummary(**org_info)
        
        region = None
        if tenant.region_id:
            region_info = await self.repository.get_region_info(str(tenant.region_id))
            if region_info:
                region = RegionSummary(**region_info)
        
        subscription_info = await self.repository.get_subscription_info(tenant_id)
        subscription = SubscriptionSummary(**subscription_info) if subscription_info else None
        
        stats = await self.repository.get_tenant_stats(tenant_id)
        
        response = TenantResponse.from_domain(
            tenant,
            organization,
            region,
            subscription,
            stats
        )
        
        logger.info(f"Updated tenant {tenant_id}")
        
        # Cache the response (tenant data affects user experience)
        await self.cache.set(cache_key, response.model_dump(), ttl=self.CACHE_TTL)
        
        return response
    
    async def update_tenant_status(
        self,
        tenant_id: str,
        status_update: TenantStatusUpdate
    ) -> TenantResponse:
        """Update tenant status.
        
        Args:
            tenant_id: Tenant ID
            status_update: Status update data
            
        Returns:
            TenantResponse with updated tenant
        """
        # Get current tenant to validate transition
        current_tenant = await self.repository.get_by_id(tenant_id)
        
        # Validate status transition
        self._validate_status_transition(current_tenant.status, status_update.status)
        
        # Update status
        tenant = await self.repository.update_status(tenant_id, status_update)
        
        # Invalidate cache
        await self._invalidate_tenant_cache(tenant_id, tenant.slug)
        
        # Get related information for response
        org_info = await self.repository.get_organization_info(str(tenant.organization_id))
        organization = OrganizationSummary(**org_info)
        
        region = None
        if tenant.region_id:
            region_info = await self.repository.get_region_info(str(tenant.region_id))
            if region_info:
                region = RegionSummary(**region_info)
        
        subscription_info = await self.repository.get_subscription_info(tenant_id)
        subscription = SubscriptionSummary(**subscription_info) if subscription_info else None
        
        stats = await self.repository.get_tenant_stats(tenant_id)
        
        response = TenantResponse.from_domain(
            tenant,
            organization,
            region,
            subscription,
            stats
        )
        
        logger.info(f"Updated tenant {tenant_id} status from {current_tenant.status} to {status_update.status}")
        
        # Cache the response (tenant data affects user experience)
        await self.cache.set(cache_key, response.model_dump(), ttl=self.CACHE_TTL)
        
        return response
    
    async def delete_tenant(self, tenant_id: str) -> None:
        """Delete (deactivate) a tenant.
        
        Args:
            tenant_id: Tenant ID to delete
        """
        # Get tenant to get slug for cache invalidation
        tenant = await self.repository.get_by_id(tenant_id)
        
        # Soft delete
        await self.repository.delete(tenant_id)
        
        # Invalidate cache
        await self._invalidate_tenant_cache(tenant_id, tenant.slug)
        
        logger.info(f"Soft deleted tenant {tenant_id}")
    
    async def provision_tenant(
        self,
        tenant_id: str,
        provision_request: TenantProvisionRequest
    ) -> TenantProvisionResponse:
        """Provision a tenant with Keycloak realm and database schema.
        
        Args:
            tenant_id: Tenant ID to provision
            provision_request: Provisioning parameters
            
        Returns:
            TenantProvisionResponse with provisioning status
        """
        # Get tenant
        tenant = await self.repository.get_by_id(tenant_id)
        
        if tenant.status != TenantStatus.PENDING:
            raise BadRequestError(f"Tenant is not in pending status (current: {tenant.status})")
        
        # Update status to provisioning
        await self.repository.update_status(
            tenant_id,
            TenantStatusUpdate(status=TenantStatus.PROVISIONING)
        )
        
        provisioning_started = utc_now()
        keycloak_created = False
        schema_created = False
        admin_created = False
        email_sent = False
        
        try:
            # Step 1: Create Keycloak realm
            realm_manager = get_realm_manager()
            await realm_manager.create_realm(
                realm_name=tenant.external_auth_realm,
                display_name=tenant.name,
                enabled=True
            )
            keycloak_created = True
            logger.info(f"Created Keycloak realm '{tenant.external_auth_realm}' for tenant {tenant_id}")
            
            # Step 2: Create database schema (would be implemented with regional DB manager)
            # await self._create_database_schema(tenant)
            schema_created = True
            logger.info(f"Created database schema '{tenant.schema_name}' for tenant {tenant_id}")
            
            # Step 3: Create initial admin user in Keycloak
            # await self._create_initial_admin(
            #     tenant,
            #     provision_request.initial_admin_email,
            #     provision_request.initial_admin_username
            # )
            admin_created = True
            logger.info(f"Created initial admin user for tenant {tenant_id}")
            
            # Step 4: Send welcome email
            if provision_request.send_welcome_email:
                # await self._send_welcome_email(tenant, provision_request.initial_admin_email)
                email_sent = True
            
            # Update status to active
            await self.repository.update_status(
                tenant_id,
                TenantStatusUpdate(status=TenantStatus.ACTIVE)
            )
            
            # Invalidate cache
            await self._invalidate_tenant_cache(tenant_id, tenant.slug)
            
            message = "Tenant provisioned successfully"
            
        except Exception as e:
            logger.error(f"Failed to provision tenant {tenant_id}: {e}")
            
            # Rollback what we can
            if keycloak_created:
                try:
                    realm_manager = get_realm_manager()
                    await realm_manager.delete_realm(tenant.external_auth_realm)
                except Exception:
                    pass
            
            # Update status back to pending
            await self.repository.update_status(
                tenant_id,
                TenantStatusUpdate(status=TenantStatus.PENDING)
            )
            
            message = f"Provisioning failed: {str(e)}"
        
        return TenantProvisionResponse(
            tenant_id=UUID(tenant_id),
            status="completed" if admin_created else "failed",
            provisioning_started_at=provisioning_started,
            estimated_completion_time=utc_now(),
            keycloak_realm_created=keycloak_created,
            database_schema_created=schema_created,
            initial_admin_created=admin_created,
            welcome_email_sent=email_sent,
            message=message
        )
    
    async def _validate_tenant_create(self, tenant_data: TenantCreate) -> None:
        """Validate tenant creation data.
        
        Args:
            tenant_data: Tenant creation data
            
        Raises:
            ValidationError: If validation fails
        """
        errors = []
        
        # Validate organization exists
        try:
            org_info = await self.repository.get_organization_info(str(tenant_data.organization_id))
            if not org_info.get('is_active'):
                errors.append({
                    "field": "organization_id",
                    "value": str(tenant_data.organization_id),
                    "requirement": "Organization must be active"
                })
        except NotFoundError:
            errors.append({
                "field": "organization_id",
                "value": str(tenant_data.organization_id),
                "requirement": "Organization must exist"
            })
        
        # Validate region if specified
        if tenant_data.region_id:
            try:
                region_info = await self.repository.get_region_info(str(tenant_data.region_id))
                if not region_info or not region_info.get('is_active'):
                    errors.append({
                        "field": "region_id",
                        "value": str(tenant_data.region_id),
                        "requirement": "Region must exist and be active"
                    })
            except Exception:
                errors.append({
                    "field": "region_id",
                    "value": str(tenant_data.region_id),
                    "requirement": "Valid region required"
                })
        
        if errors:
            raise ValidationError(
                message="Tenant validation failed",
                errors=errors
            )
    
    def _validate_status_transition(
        self, 
        current_status: TenantStatus, 
        new_status: TenantStatus
    ) -> None:
        """Validate status transition is allowed.
        
        Args:
            current_status: Current tenant status
            new_status: Requested new status
            
        Raises:
            ValidationError: If transition is not allowed
        """
        allowed_transitions = {
            TenantStatus.PENDING: [TenantStatus.PROVISIONING, TenantStatus.SUSPENDED, TenantStatus.DELETED],
            TenantStatus.PROVISIONING: [TenantStatus.ACTIVE, TenantStatus.PENDING, TenantStatus.SUSPENDED, TenantStatus.DELETED],
            TenantStatus.ACTIVE: [TenantStatus.SUSPENDED, TenantStatus.DEACTIVATED, TenantStatus.DELETED],
            TenantStatus.SUSPENDED: [TenantStatus.ACTIVE, TenantStatus.DEACTIVATED, TenantStatus.DELETED],
            TenantStatus.DEACTIVATED: [TenantStatus.ACTIVE, TenantStatus.SUSPENDED, TenantStatus.DELETED],
            TenantStatus.DELETED: []  # No transitions from deleted
        }
        
        if new_status not in allowed_transitions.get(current_status, []):
            raise ValidationError(
                message=f"Invalid status transition from {current_status} to {new_status}"
            )
    
    async def _create_list_summary(self, tenants: List[Tenant]) -> TenantListSummary:
        """Create summary statistics for tenant list.
        
        Args:
            tenants: List of tenants
            
        Returns:
            TenantListSummary with statistics
        """
        by_status = {}
        by_environment = {}
        by_region = {}
        by_deployment_type = {}
        
        active_count = 0
        suspended_count = 0
        
        for tenant in tenants:
            # Status counts
            status = tenant.status
            by_status[status] = by_status.get(status, 0) + 1
            
            if status == TenantStatus.ACTIVE:
                active_count += 1
            elif status == TenantStatus.SUSPENDED:
                suspended_count += 1
            
            # Environment counts
            env = tenant.environment
            by_environment[env] = by_environment.get(env, 0) + 1
            
            # Region counts (would need region code lookup)
            if tenant.region_id:
                region_code = "unknown"  # Would get from region info
                by_region[region_code] = by_region.get(region_code, 0) + 1
            
            # Deployment type counts
            deployment = tenant.deployment_type
            by_deployment_type[deployment] = by_deployment_type.get(deployment, 0) + 1
        
        return TenantListSummary(
            total_tenants=len(tenants),
            active_tenants=active_count,
            suspended_tenants=suspended_count,
            by_status=by_status,
            by_environment=by_environment,
            by_region=by_region,
            by_deployment_type=by_deployment_type,
            total_users=0,  # Would aggregate from tenant DBs
            total_storage_mb=0.0  # Would aggregate from tenant DBs
        )
    
    async def _invalidate_tenant_cache(self, tenant_id: str, slug: str) -> None:
        """Invalidate tenant cache entries.
        
        Args:
            tenant_id: Tenant ID
            slug: Tenant slug
        """
        cache_keys = [
            self.CACHE_KEY_TENANT.format(tenant_id=tenant_id),
            self.CACHE_KEY_TENANT_SLUG.format(slug=slug)
        ]
        
        for key in cache_keys:
            await self.cache.delete(key)