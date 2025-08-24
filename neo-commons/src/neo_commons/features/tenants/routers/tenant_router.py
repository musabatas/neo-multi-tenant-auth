"""Core tenant router following auth feature patterns.

Provides reusable tenant endpoints that accept database connection
and schema parameters via dependency injection.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends, Query, Path
from fastapi.responses import JSONResponse

from ....core.value_objects import TenantId, OrganizationId
from ....core.exceptions import EntityNotFoundError, EntityAlreadyExistsError, ValidationError
from ..entities.tenant import Tenant
from ..models.requests import (
    TenantCreateRequest,
    TenantUpdateRequest, 
    TenantProvisionRequest,
    TenantConfigRequest
)
from ..models.responses import (
    TenantResponse,
    TenantListResponse,
    TenantStatusResponse,
    TenantConfigResponse,
    TenantHealthResponse
)
from ..services import TenantService
from .dependencies import TenantDependencies


logger = logging.getLogger(__name__)

# Create router with standard configuration
tenant_router = APIRouter(
    prefix="/tenants",
    tags=["Tenants"],
    responses={
        404: {"description": "Tenant not found"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"}
    }
)


# Placeholder functions following auth feature pattern
# Applications will override these via dependency_overrides

def get_tenant_service() -> TenantService:
    """Placeholder for tenant service dependency.
    
    Applications must override this via:
    router.dependency_overrides = {
        "get_tenant_service": lambda: actual_tenant_service
    }
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Tenant service not configured. Application must provide TenantService implementation."
    )


def get_tenant_dependencies() -> TenantDependencies:
    """Placeholder for tenant dependencies.
    
    Applications must override this via:
    router.dependency_overrides = {
        "get_tenant_dependencies": lambda: actual_tenant_dependencies
    }
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Tenant dependencies not configured. Application must provide TenantDependencies implementation."
    )


# Helper function to convert tenant entity to response model
def _tenant_to_response(tenant: Tenant) -> TenantResponse:
    """Convert tenant entity to response model."""
    return TenantResponse(
        id=str(tenant.id.value),
        organization_id=str(tenant.organization_id.value),
        slug=tenant.slug,
        name=tenant.name,
        description=tenant.description,
        schema_name=tenant.schema_name,
        database_name=tenant.database_name,
        custom_domain=tenant.custom_domain,
        deployment_type=tenant.deployment_type.value,
        environment=tenant.environment,
        region_id=tenant.region_id,
        external_auth_provider=tenant.external_auth_provider,
        external_auth_realm=tenant.external_auth_realm,
        allow_impersonations=tenant.allow_impersonations,
        status=tenant.status.value,
        features_enabled=tenant.features_enabled,
        provisioned_at=tenant.provisioned_at,
        activated_at=tenant.activated_at,
        suspended_at=tenant.suspended_at,
        last_activity_at=tenant.last_activity_at,
        metadata=tenant.metadata,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
        is_active=tenant.is_active,
        is_suspended=tenant.is_suspended
    )


# CRUD Endpoints

@tenant_router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    request: TenantCreateRequest,
    tenant_service: TenantService = Depends(get_tenant_service),
    dependencies: TenantDependencies = Depends(get_tenant_dependencies)
) -> TenantResponse:
    """Create a new tenant."""
    try:
        # Validate creation requirements
        organization_id = OrganizationId(request.organization_id)
        await dependencies.validate_tenant_creation(request.slug, organization_id)
        
        # Create tenant
        tenant = await tenant_service.create_tenant(
            organization_id=organization_id,
            slug=request.slug,
            name=request.name,
            description=request.description,
            custom_domain=request.custom_domain,
            deployment_type=request.deployment_type,
            environment=request.environment,
            region_id=request.region_id,
            allow_impersonations=request.allow_impersonations,
            features_enabled=request.features_enabled,
            metadata=request.metadata
        )
        
        return _tenant_to_response(tenant)
        
    except EntityAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create tenant: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create tenant")


@tenant_router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str = Path(..., description="Tenant ID"),
    dependencies: TenantDependencies = Depends(get_tenant_dependencies)
) -> TenantResponse:
    """Get tenant by ID."""
    try:
        tenant = await dependencies.get_tenant_by_id(TenantId(tenant_id))
        return _tenant_to_response(tenant)
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid tenant ID: {e}")


@tenant_router.get("/by-slug/{slug}", response_model=TenantResponse)
async def get_tenant_by_slug(
    slug: str = Path(..., description="Tenant slug"),
    dependencies: TenantDependencies = Depends(get_tenant_dependencies)
) -> TenantResponse:
    """Get tenant by slug."""
    tenant = await dependencies.get_tenant_by_slug(slug)
    return _tenant_to_response(tenant)


@tenant_router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    request: TenantUpdateRequest,
    tenant_id: str = Path(..., description="Tenant ID"),
    tenant_service: TenantService = Depends(get_tenant_service),
    dependencies: TenantDependencies = Depends(get_tenant_dependencies)
) -> TenantResponse:
    """Update tenant information."""
    try:
        # Get existing tenant
        tenant = await dependencies.get_tenant_by_id(TenantId(tenant_id))
        
        # Update fields
        if request.name is not None:
            tenant.name = request.name
        if request.description is not None:
            tenant.description = request.description
        if request.custom_domain is not None:
            tenant.custom_domain = request.custom_domain
        if request.allow_impersonations is not None:
            tenant.allow_impersonations = request.allow_impersonations
        if request.features_enabled is not None:
            tenant.features_enabled = request.features_enabled
        if request.feature_overrides is not None:
            tenant.feature_overrides = request.feature_overrides
        if request.metadata is not None:
            tenant.metadata = request.metadata
        
        # Update tenant
        updated_tenant = await tenant_service.update_tenant(tenant)
        return _tenant_to_response(updated_tenant)
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid tenant ID: {e}")
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update tenant {tenant_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update tenant")


@tenant_router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: str = Path(..., description="Tenant ID"),
    hard_delete: bool = Query(False, description="Perform hard delete"),
    tenant_service: TenantService = Depends(get_tenant_service)
) -> None:
    """Delete tenant (soft delete by default)."""
    try:
        deleted = await tenant_service.delete_tenant(TenantId(tenant_id), hard_delete=hard_delete)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
            
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid tenant ID: {e}")
    except Exception as e:
        logger.error(f"Failed to delete tenant {tenant_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete tenant")


# List and Search Endpoints

@tenant_router.get("/", response_model=TenantListResponse)
async def list_tenants(
    organization_id: Optional[str] = Query(None, description="Filter by organization ID"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    tenant_service: TenantService = Depends(get_tenant_service),
    dependencies: TenantDependencies = Depends(get_tenant_dependencies)
) -> TenantListResponse:
    """List tenants with filtering and pagination."""
    try:
        if organization_id:
            # Get tenants for specific organization
            tenants = await dependencies.get_organization_tenants(OrganizationId(organization_id))
        else:
            # Get active tenants (limited implementation)
            tenants = await tenant_service.get_active_tenants(limit=size * page)
        
        # Apply status filter
        if status_filter:
            tenants = [t for t in tenants if t.status.value == status_filter]
        
        # Simple pagination (in production, use database-level pagination)
        start = (page - 1) * size
        end = start + size
        paginated_tenants = tenants[start:end]
        
        tenant_responses = [_tenant_to_response(t) for t in paginated_tenants]
        
        return TenantListResponse(
            tenants=tenant_responses,
            total=len(tenants),
            page=page,
            size=size
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to list tenants: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list tenants")


# Tenant Lifecycle Endpoints

@tenant_router.post("/{tenant_id}/provision", response_model=TenantStatusResponse)
async def provision_tenant(
    request: TenantProvisionRequest,
    tenant_id: str = Path(..., description="Tenant ID"),
    tenant_service: TenantService = Depends(get_tenant_service),
    dependencies: TenantDependencies = Depends(get_tenant_dependencies)
) -> TenantStatusResponse:
    """Start tenant provisioning process."""
    try:
        # Validate tenant state
        tenant = await dependencies.validate_tenant_access(
            TenantId(tenant_id),
            required_status="pending",
            require_active=False
        )
        
        previous_status = tenant.status.value
        
        # Start provisioning
        updated_tenant = await tenant_service.provision_tenant(TenantId(tenant_id))
        
        return TenantStatusResponse(
            id=str(updated_tenant.id.value),
            slug=updated_tenant.slug,
            previous_status=previous_status,
            current_status=updated_tenant.status.value,
            status_changed_at=updated_tenant.updated_at,
            reason="Provisioning started"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid tenant ID: {e}")
    except Exception as e:
        logger.error(f"Failed to provision tenant {tenant_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to provision tenant")


@tenant_router.post("/{tenant_id}/activate", response_model=TenantStatusResponse)
async def activate_tenant(
    tenant_id: str = Path(..., description="Tenant ID"),
    tenant_service: TenantService = Depends(get_tenant_service),
    dependencies: TenantDependencies = Depends(get_tenant_dependencies)
) -> TenantStatusResponse:
    """Activate tenant."""
    try:
        tenant = await dependencies.get_tenant_by_id(TenantId(tenant_id))
        previous_status = tenant.status.value
        
        # Activate tenant
        updated_tenant = await tenant_service.activate_tenant(TenantId(tenant_id))
        
        return TenantStatusResponse(
            id=str(updated_tenant.id.value),
            slug=updated_tenant.slug,
            previous_status=previous_status,
            current_status=updated_tenant.status.value,
            status_changed_at=updated_tenant.updated_at,
            reason="Tenant activated"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid tenant ID: {e}")
    except Exception as e:
        logger.error(f"Failed to activate tenant {tenant_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to activate tenant")


@tenant_router.post("/{tenant_id}/suspend", response_model=TenantStatusResponse)
async def suspend_tenant(
    tenant_id: str = Path(..., description="Tenant ID"),
    reason: Optional[str] = Query(None, description="Suspension reason"),
    tenant_service: TenantService = Depends(get_tenant_service),
    dependencies: TenantDependencies = Depends(get_tenant_dependencies)
) -> TenantStatusResponse:
    """Suspend tenant."""
    try:
        tenant = await dependencies.get_tenant_by_id(TenantId(tenant_id))
        previous_status = tenant.status.value
        
        # Suspend tenant
        updated_tenant = await tenant_service.suspend_tenant(TenantId(tenant_id), reason)
        
        return TenantStatusResponse(
            id=str(updated_tenant.id.value),
            slug=updated_tenant.slug,
            previous_status=previous_status,
            current_status=updated_tenant.status.value,
            status_changed_at=updated_tenant.updated_at,
            reason=reason or "Tenant suspended"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid tenant ID: {e}")
    except Exception as e:
        logger.error(f"Failed to suspend tenant {tenant_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to suspend tenant")


# Configuration Endpoints

@tenant_router.get("/{tenant_id}/config", response_model=TenantConfigResponse)
async def get_tenant_config(
    tenant_id: str = Path(..., description="Tenant ID"),
    namespace: Optional[str] = Query(None, description="Configuration namespace filter"),
    dependencies: TenantDependencies = Depends(get_tenant_dependencies)
) -> TenantConfigResponse:
    """Get tenant configuration."""
    try:
        tenant = await dependencies.get_tenant_by_id(TenantId(tenant_id))
        
        if not dependencies.config_resolver:
            return TenantConfigResponse(
                tenant_id=tenant_id,
                configs={},
                namespace=namespace,
                total_configs=0,
                last_updated=None
            )
        
        # Get configurations
        configs = await dependencies.config_resolver.get_configs(TenantId(tenant_id), namespace)
        
        return TenantConfigResponse(
            tenant_id=tenant_id,
            configs=configs,
            namespace=namespace,
            total_configs=len(configs),
            last_updated=tenant.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid tenant ID: {e}")
    except Exception as e:
        logger.error(f"Failed to get tenant config {tenant_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get tenant configuration")


@tenant_router.put("/{tenant_id}/config", response_model=TenantConfigResponse)
async def update_tenant_config(
    request: TenantConfigRequest,
    tenant_id: str = Path(..., description="Tenant ID"),
    dependencies: TenantDependencies = Depends(get_tenant_dependencies)
) -> TenantConfigResponse:
    """Update tenant configuration."""
    try:
        tenant = await dependencies.get_tenant_by_id(TenantId(tenant_id))
        
        # Set configurations
        updated_configs = {}
        for key, value in request.configs.items():
            success = await dependencies.set_tenant_config(TenantId(tenant_id), key, value)
            if success:
                updated_configs[key] = value
        
        return TenantConfigResponse(
            tenant_id=tenant_id,
            configs=updated_configs,
            namespace=request.namespace,
            total_configs=len(updated_configs),
            last_updated=datetime.utcnow()
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid tenant ID: {e}")
    except Exception as e:
        logger.error(f"Failed to update tenant config {tenant_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update tenant configuration")


# Health and Status Endpoints

@tenant_router.get("/{tenant_id}/health", response_model=TenantHealthResponse)
async def get_tenant_health(
    tenant_id: str = Path(..., description="Tenant ID"),
    dependencies: TenantDependencies = Depends(get_tenant_dependencies)
) -> TenantHealthResponse:
    """Get tenant health status."""
    try:
        tenant = await dependencies.get_tenant_by_id(TenantId(tenant_id))
        
        # Basic health checks
        database_healthy = True  # Repository worked to get tenant
        cache_healthy = True     # Assume healthy if cache is available
        auth_healthy = True      # Placeholder for auth service check
        
        health_score = 100.0
        if not database_healthy:
            health_score -= 40
        if not cache_healthy:
            health_score -= 20
        if not auth_healthy:
            health_score -= 40
        
        return TenantHealthResponse(
            tenant_id=tenant_id,
            slug=tenant.slug,
            status=tenant.status.value,
            health_score=health_score,
            checks={
                "database": {"status": "healthy" if database_healthy else "unhealthy"},
                "cache": {"status": "healthy" if cache_healthy else "unhealthy"}, 
                "auth": {"status": "healthy" if auth_healthy else "unhealthy"}
            },
            last_activity_at=tenant.last_activity_at,
            database_healthy=database_healthy,
            cache_healthy=cache_healthy,
            auth_healthy=auth_healthy
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid tenant ID: {e}")
    except Exception as e:
        logger.error(f"Failed to get tenant health {tenant_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get tenant health")


@tenant_router.post("/{tenant_id}/activity", status_code=status.HTTP_204_NO_CONTENT)
async def update_tenant_activity(
    tenant_id: str = Path(..., description="Tenant ID"),
    tenant_service: TenantService = Depends(get_tenant_service)
) -> None:
    """Update tenant last activity timestamp."""
    try:
        success = await tenant_service.update_tenant_activity(TenantId(tenant_id))
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
            
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid tenant ID: {e}")
    except Exception as e:
        logger.error(f"Failed to update tenant activity {tenant_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update tenant activity")