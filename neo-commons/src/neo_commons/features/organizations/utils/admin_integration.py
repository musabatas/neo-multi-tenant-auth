"""Admin-specific utilities for organization management.

Provides utilities specific to admin operations, system management,
and platform-level organization functionality following DRY principles.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import asdict

from ....core.value_objects import OrganizationId
from ..entities.organization import Organization
from .queries import (
    build_organization_stats_query, 
    ORGANIZATION_QUERIES,
    ORGANIZATION_VALIDATE_UNIQUE_SLUG,
    ORGANIZATION_CLEANUP_INACTIVE
)

logger = logging.getLogger(__name__)


class OrganizationAdminUtils:
    """Administrative utilities for organization management."""
    
    @staticmethod
    async def generate_organization_report(
        database_repository,
        schema: str,
        include_stats: bool = True,
        include_recent_activity: bool = True,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Generate comprehensive organization report for admin dashboard.
        
        Args:
            database_repository: Database repository instance
            schema: Database schema name
            include_stats: Whether to include statistical data
            include_recent_activity: Whether to include recent activity
            days_back: Days to look back for recent activity
            
        Returns:
            Comprehensive organization report
        """
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "schema": schema,
            "time_period_days": days_back
        }
        
        try:
            # Basic counts
            total_query = ORGANIZATION_QUERIES["count_all"].format(schema=schema)
            async with database_repository.get_connection() as conn:
                total_count = await conn.fetchval(total_query)
                report["total_organizations"] = total_count
                
                # Health check
                health_query = ORGANIZATION_QUERIES["health_check"].format(schema=schema)
                health_data = await conn.fetchrow(health_query)
                if health_data:
                    report["health"] = dict(health_data)
            
            # Statistical data
            if include_stats:
                stats = await OrganizationAdminUtils._gather_organization_statistics(
                    database_repository, schema
                )
                report["statistics"] = stats
            
            # Recent activity
            if include_recent_activity:
                activity = await OrganizationAdminUtils._gather_recent_activity(
                    database_repository, schema, days_back
                )
                report["recent_activity"] = activity
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate organization report: {e}")
            report["error"] = str(e)
            return report
    
    @staticmethod
    async def _gather_organization_statistics(
        database_repository,
        schema: str
    ) -> Dict[str, Any]:
        """Gather organization statistics."""
        stats = {}
        
        try:
            async with database_repository.get_connection() as conn:
                # Industry statistics
                industry_query = build_organization_stats_query(schema, "industry")
                industry_results = await conn.fetch(industry_query)
                stats["by_industry"] = [dict(row) for row in industry_results]
                
                # Country statistics
                country_query = build_organization_stats_query(schema, "country")
                country_results = await conn.fetch(country_query)
                stats["by_country"] = [dict(row) for row in country_results]
                
                # Company size statistics
                size_query = build_organization_stats_query(schema, "company_size")
                size_results = await conn.fetch(size_query)
                stats["by_company_size"] = [dict(row) for row in size_results]
                
        except Exception as e:
            logger.error(f"Failed to gather organization statistics: {e}")
            stats["error"] = str(e)
        
        return stats
    
    @staticmethod
    async def _gather_recent_activity(
        database_repository,
        schema: str,
        days_back: int
    ) -> Dict[str, Any]:
        """Gather recent organization activity."""
        activity = {}
        
        try:
            async with database_repository.get_connection() as conn:
                # Recent creation trends
                creation_query = build_organization_stats_query(
                    schema, "recent_activity", days_back
                )
                creation_results = await conn.fetch(creation_query)
                activity["recent_creations"] = [dict(row) for row in creation_results]
                
                # Recent verification trends
                verification_query = build_organization_stats_query(
                    schema, "verification_trends", days_back
                )
                verification_results = await conn.fetch(verification_query)
                activity["recent_verifications"] = [dict(row) for row in verification_results]
                
        except Exception as e:
            logger.error(f"Failed to gather recent activity: {e}")
            activity["error"] = str(e)
        
        return activity
    
    @staticmethod
    async def validate_organization_integrity(
        database_repository,
        schema: str,
        fix_issues: bool = False
    ) -> Dict[str, Any]:
        """Validate organization data integrity across the system.
        
        Args:
            database_repository: Database repository instance
            schema: Database schema name
            fix_issues: Whether to automatically fix found issues
            
        Returns:
            Integrity validation report
        """
        report = {
            "validated_at": datetime.utcnow().isoformat(),
            "schema": schema,
            "issues_found": [],
            "issues_fixed": [] if fix_issues else None
        }
        
        try:
            async with database_repository.get_connection() as conn:
                # Check for duplicate slugs
                duplicate_slugs_query = f"""
                    SELECT slug, COUNT(*) as count
                    FROM {schema}.organizations
                    WHERE is_active = true
                    GROUP BY slug
                    HAVING COUNT(*) > 1
                """
                duplicate_slugs = await conn.fetch(duplicate_slugs_query)
                
                if duplicate_slugs:
                    for row in duplicate_slugs:
                        issue = f"Duplicate slug '{row['slug']}' found {row['count']} times"
                        report["issues_found"].append(issue)
                
                # Check for organizations without valid country codes
                invalid_countries_query = f"""
                    SELECT id, name, country_code
                    FROM {schema}.organizations
                    WHERE is_active = true
                    AND country_code IS NOT NULL
                    AND LENGTH(country_code) != 2
                """
                invalid_countries = await conn.fetch(invalid_countries_query)
                
                if invalid_countries:
                    for row in invalid_countries:
                        issue = f"Invalid country code '{row['country_code']}' for organization {row['name']}"
                        report["issues_found"].append(issue)
                
                # Check for missing full addresses when components exist
                missing_addresses_query = f"""
                    SELECT id, name
                    FROM {schema}.organizations
                    WHERE is_active = true
                    AND (address_line1 IS NOT NULL OR city IS NOT NULL)
                    AND full_address IS NULL
                """
                missing_addresses = await conn.fetch(missing_addresses_query)
                
                if missing_addresses:
                    for row in missing_addresses:
                        issue = f"Missing full address for organization {row['name']} with address components"
                        report["issues_found"].append(issue)
                        
                        if fix_issues:
                            # Fix by generating full address
                            fix_query = f"""
                                UPDATE {schema}.organizations SET
                                    full_address = CONCAT_WS(', ',
                                        address_line1,
                                        address_line2,
                                        city,
                                        state_province,
                                        postal_code,
                                        country_code
                                    ),
                                    updated_at = $1
                                WHERE id = $2
                            """
                            await conn.execute(fix_query, datetime.utcnow(), row['id'])
                            report["issues_fixed"].append(f"Generated full address for {row['name']}")
                
        except Exception as e:
            logger.error(f"Failed to validate organization integrity: {e}")
            report["error"] = str(e)
        
        return report
    
    @staticmethod
    async def cleanup_inactive_organizations(
        database_repository,
        schema: str,
        retention_days: int = 365,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Clean up inactive organizations based on retention policy.
        
        Args:
            database_repository: Database repository instance
            schema: Database schema name
            retention_days: Days to retain inactive organizations
            dry_run: Whether to perform a dry run (don't actually delete)
            
        Returns:
            Cleanup operation report
        """
        report = {
            "performed_at": datetime.utcnow().isoformat(),
            "schema": schema,
            "retention_days": retention_days,
            "dry_run": dry_run,
            "organizations_to_delete": [],
            "organizations_deleted": []
        }
        
        try:
            async with database_repository.get_connection() as conn:
                # Find inactive organizations older than retention period
                find_query = f"""
                    SELECT id, name, slug, updated_at
                    FROM {schema}.organizations
                    WHERE is_active = false
                    AND updated_at < $1
                    ORDER BY updated_at
                """
                cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
                inactive_orgs = await conn.fetch(find_query, cutoff_date)
                
                for org in inactive_orgs:
                    org_info = {
                        "id": str(org['id']),
                        "name": org['name'],
                        "slug": org['slug'],
                        "last_updated": org['updated_at'].isoformat()
                    }
                    report["organizations_to_delete"].append(org_info)
                
                # Perform deletion if not dry run
                if not dry_run and inactive_orgs:
                    delete_query = f"""
                        DELETE FROM {schema}.organizations
                        WHERE is_active = false
                        AND updated_at < $1
                        RETURNING id, name, slug
                    """
                    deleted_orgs = await conn.fetch(delete_query, cutoff_date)
                    
                    for org in deleted_orgs:
                        org_info = {
                            "id": str(org['id']),
                            "name": org['name'],
                            "slug": org['slug']
                        }
                        report["organizations_deleted"].append(org_info)
                    
                    logger.info(f"Deleted {len(deleted_orgs)} inactive organizations from {schema}")
                
        except Exception as e:
            logger.error(f"Failed to cleanup inactive organizations: {e}")
            report["error"] = str(e)
        
        return report
    
    @staticmethod
    def generate_organization_export(
        organizations: List[Organization],
        export_format: str = "dict",
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """Generate organization data export for admin purposes.
        
        Args:
            organizations: List of organization entities
            export_format: Export format ('dict', 'minimal', 'admin')
            include_metadata: Whether to include metadata fields
            
        Returns:
            List of exported organization data
        """
        exported_data = []
        
        for org in organizations:
            if export_format == "minimal":
                data = {
                    "id": str(org.id.value),
                    "name": org.name,
                    "slug": org.slug,
                    "industry": org.industry,
                    "country_code": org.country_code,
                    "is_active": org.is_active,
                    "is_verified": org.is_verified,
                    "created_at": org.created_at.isoformat() if org.created_at else None
                }
            elif export_format == "admin":
                data = asdict(org)
                data["id"] = str(org.id.value)  # Convert ID to string
                
                # Convert datetime objects to ISO strings
                for field in ["created_at", "updated_at", "verified_at"]:
                    if data.get(field):
                        data[field] = data[field].isoformat()
                        
                if include_metadata:
                    data["export_metadata"] = {
                        "exported_at": datetime.utcnow().isoformat(),
                        "export_format": export_format
                    }
            else:  # dict format
                data = asdict(org)
                data["id"] = str(org.id.value)
                
                # Convert datetime objects to ISO strings
                for field in ["created_at", "updated_at", "verified_at"]:
                    if data.get(field):
                        data[field] = data[field].isoformat()
            
            exported_data.append(data)
        
        return exported_data
    
    @staticmethod
    def calculate_organization_health_score(
        organization: Organization,
        tenant_count: int = 0,
        user_count: int = 0,
        last_activity_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """Calculate health score for an organization based on various metrics.
        
        Args:
            organization: Organization entity
            tenant_count: Number of tenants for this organization
            user_count: Number of users for this organization
            last_activity_days: Days since last activity
            
        Returns:
            Health score report
        """
        score = 0
        max_score = 100
        factors = []
        
        # Basic information completeness (30 points)
        basic_fields = [
            organization.legal_name, organization.industry, organization.country_code,
            organization.address_line1, organization.city, organization.website_url
        ]
        basic_completeness = sum(1 for field in basic_fields if field) / len(basic_fields)
        basic_score = int(basic_completeness * 30)
        score += basic_score
        factors.append(f"Basic information completeness: {basic_score}/30")
        
        # Verification status (20 points)
        verification_score = 20 if organization.is_verified else 0
        score += verification_score
        factors.append(f"Verification status: {verification_score}/20")
        
        # Activity level (25 points)
        activity_score = 0
        if tenant_count > 0:
            activity_score += min(tenant_count * 5, 15)  # Up to 15 points for tenants
        if user_count > 0:
            activity_score += min(user_count * 2, 10)   # Up to 10 points for users
        activity_score = min(activity_score, 25)
        score += activity_score
        factors.append(f"Activity level: {activity_score}/25")
        
        # Recency (15 points)
        recency_score = 15
        if last_activity_days is not None:
            if last_activity_days > 365:
                recency_score = 0
            elif last_activity_days > 90:
                recency_score = 5
            elif last_activity_days > 30:
                recency_score = 10
        score += recency_score
        factors.append(f"Recent activity: {recency_score}/15")
        
        # Branding completeness (10 points)
        branding_fields = [organization.logo_url, organization.brand_colors]
        branding_completeness = sum(1 for field in branding_fields if field) / len(branding_fields)
        branding_score = int(branding_completeness * 10)
        score += branding_score
        factors.append(f"Branding completeness: {branding_score}/10")
        
        # Determine health category
        if score >= 80:
            health_category = "Excellent"
        elif score >= 60:
            health_category = "Good"
        elif score >= 40:
            health_category = "Fair"
        elif score >= 20:
            health_category = "Poor"
        else:
            health_category = "Critical"
        
        return {
            "organization_id": str(organization.id.value),
            "organization_name": organization.name,
            "health_score": score,
            "max_score": max_score,
            "health_percentage": round((score / max_score) * 100, 1),
            "health_category": health_category,
            "scoring_factors": factors,
            "calculated_at": datetime.utcnow().isoformat()
        }