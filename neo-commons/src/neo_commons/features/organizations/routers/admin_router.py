"""Organization admin router for administrative operations.

Provides ready-to-use FastAPI router for organization administration
with statistics, health checks, and management operations.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from fastapi.responses import JSONResponse

from ....core.value_objects import OrganizationId
from ....core.exceptions import DatabaseError
from ..models.responses import (
    OrganizationResponse,
    OrganizationStatsResponse,
    OrganizationListResponse
)
from ..services.organization_service import OrganizationService
from ..utils.admin_integration import OrganizationAdminUtils
from .dependencies import get_admin_organization_service, get_organization_repository


# Create admin router with consistent tags and prefix
admin_router = APIRouter(
    prefix="/admin/organizations",
    tags=["Organization Management"],
    responses={
        403: {"description": "Insufficient permissions"},
        404: {"description": "Organization not found"},
        500: {"description": "Internal server error"}
    }
)


@admin_router.get(
    "/stats",
    response_model=OrganizationStatsResponse,
    summary="Get organization statistics",
    description="Retrieve comprehensive organization statistics for admin dashboard"
)
async def get_organization_statistics(
    include_trends: bool = Query(True, description="Include growth trends"),
    days_back: int = Query(30, ge=1, le=365, description="Days to look back for trends"),
    repository = Depends(get_organization_repository)
) -> OrganizationStatsResponse:
    """Get organization statistics."""
    try:
        # Generate comprehensive report using admin utils
        report = await OrganizationAdminUtils.generate_organization_report(
            repository,
            include_stats=True,
            include_recent_activity=include_trends,
            days_back=days_back
        )
        
        if "error" in report:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate statistics: {report['error']}"
            )
        
        # Transform to response model
        stats_data = report.get("statistics", {})
        
        return OrganizationStatsResponse(
            total_organizations=report.get("total_organizations", 0),
            active_organizations=report.get("health", {}).get("active_organizations", 0),
            verified_organizations=report.get("health", {}).get("verified_organizations", 0),
            by_industry={
                item["industry"]: item["organization_count"] 
                for item in stats_data.get("by_industry", [])
            },
            by_country={
                item["country_code"]: item["organization_count"] 
                for item in stats_data.get("by_country", [])
            },
            by_company_size={
                item["company_size"]: item["organization_count"] 
                for item in stats_data.get("by_company_size", [])
            },
            recent_verifications=report.get("health", {}).get("recent_organizations", 0),
            growth_rate=None  # Would be calculated from trends data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )


@admin_router.get(
    "/health",
    summary="Organization system health check",
    description="Check organization system health and data integrity"
)
async def organization_health_check(
    repository = Depends(get_organization_repository)
) -> Dict[str, Any]:
    """Perform organization system health check."""
    try:
        # Get basic health data from admin utils
        report = await OrganizationAdminUtils.generate_organization_report(
            repository,
            include_stats=False,
            include_recent_activity=False
        )
        
        health_data = report.get("health", {})
        
        # Determine overall health status
        total = health_data.get("total_organizations", 0)
        active = health_data.get("active_organizations", 0)
        verified = health_data.get("verified_organizations", 0)
        
        health_percentage = (active / total * 100) if total > 0 else 100
        
        if health_percentage >= 95:
            status_level = "excellent"
        elif health_percentage >= 85:
            status_level = "good"
        elif health_percentage >= 70:
            status_level = "fair"
        else:
            status_level = "poor"
        
        return {
            "status": status_level,
            "health_percentage": round(health_percentage, 2),
            "total_organizations": total,
            "active_organizations": active,
            "verified_organizations": verified,
            "inactive_organizations": total - active,
            "verification_rate": round((verified / total * 100), 2) if total > 0 else 0,
            "checked_at": report.get("generated_at")
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


@admin_router.post(
    "/integrity/validate",
    summary="Validate organization data integrity",
    description="Validate organization data integrity across the system"
)
async def validate_organization_integrity(
    fix_issues: bool = Query(False, description="Automatically fix found issues"),
    repository = Depends(get_organization_repository)
) -> Dict[str, Any]:
    """Validate organization data integrity."""
    try:
        validation_report = await OrganizationAdminUtils.validate_organization_integrity(
            repository,
            fix_issues=fix_issues
        )
        
        if "error" in validation_report:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Validation failed: {validation_report['error']}"
            )
        
        return validation_report
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Integrity validation failed: {str(e)}"
        )


@admin_router.post(
    "/cleanup",
    summary="Clean up inactive organizations",
    description="Clean up inactive organizations based on retention policy"
)
async def cleanup_inactive_organizations(
    retention_days: int = Query(365, ge=30, le=3650, description="Days to retain inactive organizations"),
    dry_run: bool = Query(True, description="Perform dry run without actual deletion"),
    repository = Depends(get_organization_repository)
) -> Dict[str, Any]:
    """Clean up inactive organizations."""
    try:
        cleanup_report = await OrganizationAdminUtils.cleanup_inactive_organizations(
            repository,
            retention_days=retention_days,
            dry_run=dry_run
        )
        
        if "error" in cleanup_report:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Cleanup failed: {cleanup_report['error']}"
            )
        
        return cleanup_report
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cleanup operation failed: {str(e)}"
        )


@admin_router.get(
    "/export",
    summary="Export organization data",
    description="Export organization data for admin purposes"
)
async def export_organizations(
    format: str = Query("dict", regex="^(dict|minimal|admin)$", description="Export format"),
    include_metadata: bool = Query(True, description="Include metadata in export"),
    active_only: bool = Query(True, description="Export only active organizations"),
    service: OrganizationService = Depends(get_admin_organization_service)
) -> Dict[str, Any]:
    """Export organization data."""
    try:
        # Get organizations based on filter
        if active_only:
            organizations = await service.get_active_organizations()
        else:
            # Would need to implement get_all_organizations method
            organizations = await service.get_active_organizations()
        
        # Generate export using admin utils
        exported_data = OrganizationAdminUtils.generate_organization_export(
            organizations,
            export_format=format,
            include_metadata=include_metadata
        )
        
        return {
            "exported_at": "2024-01-01T00:00:00Z",  # Would use actual timestamp
            "format": format,
            "total_organizations": len(exported_data),
            "include_metadata": include_metadata,
            "organizations": exported_data
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )


@admin_router.get(
    "/{organization_id}/health",
    summary="Get organization health score",
    description="Calculate health score for specific organization"
)
async def get_organization_health_score(
    organization_id: str = Path(..., description="Organization ID"),
    service: OrganizationService = Depends(get_admin_organization_service)
) -> Dict[str, Any]:
    """Get organization health score."""
    try:
        org_id = OrganizationId(organization_id)
        organization = await service.get_by_id(org_id)
        
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization {organization_id} not found"
            )
        
        # Calculate health score using admin utils
        # Note: In real implementation, tenant_count, user_count, last_activity_days 
        # would be retrieved from respective services
        health_score = OrganizationAdminUtils.calculate_organization_health_score(
            organization,
            tenant_count=0,  # Would be retrieved from tenant service
            user_count=0,    # Would be retrieved from user service
            last_activity_days=None  # Would be calculated from activity logs
        )
        
        return health_score
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid organization ID: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate health score: {str(e)}"
        )


@admin_router.get(
    "/search/advanced",
    response_model=OrganizationListResponse,
    summary="Advanced admin search",
    description="Advanced organization search with admin-specific filters"
)
async def admin_search_organizations(
    query: Optional[str] = Query(None, description="Search query"),
    include_inactive: bool = Query(False, description="Include inactive organizations"),
    include_unverified: bool = Query(True, description="Include unverified organizations"),
    created_after: Optional[str] = Query(None, description="Filter by creation date (ISO format)"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    country_code: Optional[str] = Query(None, description="Filter by country"),
    min_health_score: Optional[int] = Query(None, ge=0, le=100, description="Minimum health score"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum results"),
    service: OrganizationService = Depends(get_admin_organization_service)
) -> OrganizationListResponse:
    """Advanced admin search for organizations."""
    try:
        # Build filters based on parameters
        filters = {}
        
        if not include_inactive:
            filters["is_active"] = True
        
        if not include_unverified:
            filters["is_verified"] = True
            
        if industry:
            filters["industry"] = industry
            
        if country_code:
            filters["country_code"] = country_code
        
        # Perform search
        if query:
            organizations = await service.search_organizations(
                query=query,
                filters=filters,
                limit=limit
            )
        else:
            # Get filtered list
            if industry:
                organizations = await service.get_by_industry(industry)
            elif country_code:
                organizations = await service.get_by_country(country_code)
            else:
                organizations = await service.get_active_organizations(limit)
        
        # Apply additional filters (simplified - should be in repository layer)
        # In real implementation, all filtering would be done at database level
        
        # Convert to responses
        from ..models.responses import OrganizationSummaryResponse
        
        # Convert all results (limit is already applied in service layer)
        org_summaries = [
            OrganizationSummaryResponse.from_entity(org) 
            for org in organizations
        ]
        
        return OrganizationListResponse(
            organizations=org_summaries,
            total=len(organizations),
            page=1,
            per_page=limit,
            has_next=len(organizations) > limit,
            has_prev=False
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Admin search failed: {str(e)}"
        )


@admin_router.post(
    "/{organization_id}/force-verify",
    response_model=OrganizationResponse,
    summary="Force verify organization",
    description="Force verify organization without document validation (admin only)"
)
async def force_verify_organization(
    organization_id: str = Path(..., description="Organization ID"),
    reason: str = Query(..., description="Reason for force verification"),
    service: OrganizationService = Depends(get_admin_organization_service)
) -> OrganizationResponse:
    """Force verify organization (admin override)."""
    try:
        org_id = OrganizationId(organization_id)
        
        # Force verification with admin reason
        organization = await service.verify_organization(
            org_id,
            documents=[f"Admin force verification: {reason}"]
        )
        
        return OrganizationResponse.from_entity(organization)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Force verification failed: {str(e)}"
        )


@admin_router.get(
    "/reports/dashboard",
    summary="Get admin dashboard data",
    description="Get comprehensive data for organization admin dashboard"
)
async def get_admin_dashboard_data(
    repository = Depends(get_organization_repository)
) -> Dict[str, Any]:
    """Get comprehensive admin dashboard data."""
    try:
        # Generate comprehensive report
        report = await OrganizationAdminUtils.generate_organization_report(
            repository,
            include_stats=True,
            include_recent_activity=True,
            days_back=30
        )
        
        if "error" in report:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Dashboard data generation failed: {report['error']}"
            )
        
        # Format for dashboard consumption
        dashboard_data = {
            "summary": {
                "total_organizations": report.get("total_organizations", 0),
                "active_organizations": report.get("health", {}).get("active_organizations", 0),
                "verified_organizations": report.get("health", {}).get("verified_organizations", 0),
                "recent_organizations": report.get("health", {}).get("recent_organizations", 0)
            },
            "statistics": report.get("statistics", {}),
            "recent_activity": report.get("recent_activity", {}),
            "health": report.get("health", {}),
            "generated_at": report.get("generated_at"),
            "time_period_days": report.get("time_period_days", 30)
        }
        
        return dashboard_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate dashboard data: {str(e)}"
        )