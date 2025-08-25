"""Organization SQL query constants to eliminate duplicate queries and follow DRY principles.

This module centralizes all SQL queries used across the organizations feature,
making them reusable, parameterized, and easily maintainable.
"""

from typing import Dict

# Organization CRUD queries (parameterized by schema)
ORGANIZATION_INSERT = """
    INSERT INTO {schema}.organizations (
        id, name, slug, legal_name, tax_id, business_type, industry, company_size,
        website_url, primary_contact_id, address_line1, address_line2, city,
        state_province, postal_code, country_code, default_timezone,
        default_locale, default_currency, logo_url, brand_colors, is_active,
        verified_at, verification_documents, metadata, created_at, updated_at
    ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, 
        $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27
    ) RETURNING *
"""

ORGANIZATION_UPDATE = """
    UPDATE {schema}.organizations SET
        name = COALESCE($2, name),
        legal_name = COALESCE($3, legal_name),
        tax_id = COALESCE($4, tax_id),
        business_type = COALESCE($5, business_type),
        industry = COALESCE($6, industry),
        company_size = COALESCE($7, company_size),
        website_url = COALESCE($8, website_url),
        primary_contact_id = COALESCE($9, primary_contact_id),
        address_line1 = COALESCE($10, address_line1),
        address_line2 = COALESCE($11, address_line2),
        city = COALESCE($12, city),
        state_province = COALESCE($13, state_province),
        postal_code = COALESCE($14, postal_code),
        country_code = COALESCE($15, country_code),
        default_timezone = COALESCE($16, default_timezone),
        default_locale = COALESCE($17, default_locale),
        default_currency = COALESCE($18, default_currency),
        logo_url = COALESCE($19, logo_url),
        brand_colors = COALESCE($20, brand_colors),
        is_active = COALESCE($21, is_active),
        deleted_at = COALESCE($22, deleted_at),
        metadata = COALESCE($23, metadata),
        updated_at = $24
    WHERE id = $1
    RETURNING *
"""

ORGANIZATION_DELETE_SOFT = """
    UPDATE {schema}.organizations SET
        is_active = false,
        updated_at = $2
    WHERE id = $1
    RETURNING *
"""

ORGANIZATION_DELETE_HARD = """
    DELETE FROM {schema}.organizations
    WHERE id = $1
    RETURNING *
"""

# Organization retrieval queries
ORGANIZATION_GET_BY_ID = """
    SELECT * FROM {schema}.organizations
    WHERE id = $1 AND is_active = true AND deleted_at IS NULL
"""

ORGANIZATION_GET_BY_SLUG = """
    SELECT * FROM {schema}.organizations
    WHERE slug = $1 AND is_active = true AND deleted_at IS NULL
"""

ORGANIZATION_EXISTS_BY_ID = """
    SELECT EXISTS(
        SELECT 1 FROM {schema}.organizations
        WHERE id = $1 AND is_active = true AND deleted_at IS NULL
    )
"""

ORGANIZATION_EXISTS_BY_SLUG = """
    SELECT EXISTS(
        SELECT 1 FROM {schema}.organizations
        WHERE slug = $1 AND is_active = true AND deleted_at IS NULL
    )
"""

ORGANIZATION_GET_BY_PRIMARY_CONTACT = """
    SELECT * FROM {schema}.organizations
    WHERE primary_contact_id = $1 AND is_active = true AND deleted_at IS NULL
    ORDER BY created_at DESC
"""

# Organization listing and search queries
ORGANIZATION_LIST_ALL = """
    SELECT * FROM {schema}.organizations
    WHERE is_active = true AND deleted_at IS NULL
    ORDER BY name
    LIMIT $1 OFFSET $2
"""

ORGANIZATION_LIST_PAGINATED = """
    SELECT * FROM {schema}.organizations
    WHERE is_active = true AND deleted_at IS NULL
    ORDER BY {order_by}
    LIMIT $1 OFFSET $2
"""

ORGANIZATION_COUNT_ALL = """
    SELECT COUNT(*) FROM {schema}.organizations
    WHERE is_active = true AND deleted_at IS NULL
"""

ORGANIZATION_SEARCH_BY_NAME = """
    SELECT * FROM {schema}.organizations
    WHERE is_active = true AND deleted_at IS NULL
    AND (name ILIKE $1 OR legal_name ILIKE $1)
    ORDER BY 
        CASE WHEN name ILIKE $1 THEN 1 ELSE 2 END,
        name
    LIMIT $2 OFFSET $3
"""

ORGANIZATION_SEARCH_ADVANCED = """
    SELECT * FROM {schema}.organizations
    WHERE ($1::text IS NULL OR name ILIKE $1::text)
    AND ($2::text IS NULL OR industry = $2::text)
    AND ($3::text IS NULL OR country_code = $3::text)
    AND ($4::boolean IS NULL OR 
         CASE WHEN $4::boolean = true THEN verified_at IS NOT NULL 
              WHEN $4::boolean = false THEN verified_at IS NULL
              ELSE true END)
    AND ($5::boolean IS NULL OR is_active = $5::boolean)
    ORDER BY name
    LIMIT $6 OFFSET $7
"""

# Organization statistics queries
ORGANIZATION_STATS_BASIC = """
    SELECT 
        COUNT(*) as total_organizations,
        COUNT(CASE WHEN verified_at IS NOT NULL THEN 1 END) as verified_organizations,
        COUNT(CASE WHEN is_active THEN 1 END) as active_organizations
    FROM {schema}.organizations
"""

ORGANIZATION_STATS_BY_INDUSTRY = """
    SELECT 
        COALESCE(industry, 'Unknown') as industry,
        COUNT(*) as organization_count
    FROM {schema}.organizations
    WHERE is_active = true
    GROUP BY industry
    ORDER BY organization_count DESC
"""

ORGANIZATION_STATS_BY_COUNTRY = """
    SELECT 
        COALESCE(country_code, 'Unknown') as country_code,
        COUNT(*) as organization_count
    FROM {schema}.organizations
    WHERE is_active = true
    GROUP BY country_code
    ORDER BY organization_count DESC
"""

ORGANIZATION_STATS_BY_COMPANY_SIZE = """
    SELECT 
        COALESCE(company_size, 'Unknown') as company_size,
        COUNT(*) as organization_count
    FROM {schema}.organizations
    WHERE is_active = true
    GROUP BY company_size
    ORDER BY organization_count DESC
"""

ORGANIZATION_STATS_RECENT_ACTIVITY = """
    SELECT 
        DATE(created_at) as creation_date,
        COUNT(*) as organizations_created
    FROM {schema}.organizations
    WHERE created_at >= NOW() - INTERVAL '{days} days'
    GROUP BY DATE(created_at)
    ORDER BY creation_date DESC
"""

ORGANIZATION_STATS_VERIFICATION_TRENDS = """
    SELECT 
        DATE(verified_at) as verification_date,
        COUNT(*) as organizations_verified
    FROM {schema}.organizations
    WHERE verified_at >= NOW() - INTERVAL '{days} days'
    AND verified_at IS NOT NULL
    GROUP BY DATE(verified_at)
    ORDER BY verification_date DESC
"""

# Organization configuration queries
ORGANIZATION_CONFIG_GET = """
    SELECT config_key, config_value, updated_at
    FROM {schema}.organization_configs
    WHERE organization_id = $1
    AND ($2 IS NULL OR namespace = $2)
    ORDER BY config_key
"""

ORGANIZATION_CONFIG_SET = """
    INSERT INTO {schema}.organization_configs (
        organization_id, config_key, config_value, namespace, updated_at
    )
    VALUES ($1, $2, $3, $4, $5)
    ON CONFLICT (organization_id, config_key, namespace)
    DO UPDATE SET
        config_value = EXCLUDED.config_value,
        updated_at = EXCLUDED.updated_at
    RETURNING *
"""

ORGANIZATION_CONFIG_DELETE = """
    DELETE FROM {schema}.organization_configs
    WHERE organization_id = $1
    AND config_key = $2
    AND ($3 IS NULL OR namespace = $3)
    RETURNING *
"""

# Organization relationship queries
ORGANIZATION_GET_TENANTS = """
    SELECT t.* FROM {schema}.tenants t
    JOIN {schema}.organizations o ON t.organization_id = o.id
    WHERE o.id = $1 AND t.is_active = true
    ORDER BY t.name
"""

ORGANIZATION_GET_USERS = """
    SELECT u.* FROM {schema}.users u
    JOIN {schema}.organizations o ON u.organization_id = o.id
    WHERE o.id = $1 AND u.is_active = true
    ORDER BY u.email
"""

ORGANIZATION_GET_TEAMS = """
    SELECT t.* FROM {schema}.teams t
    WHERE t.organization_id = $1 AND t.is_active = true
    ORDER BY t.name
"""

# Organization validation queries
ORGANIZATION_VALIDATE_UNIQUE_SLUG = """
    SELECT EXISTS(
        SELECT 1 FROM {schema}.organizations
        WHERE slug = $1 AND id != $2 AND is_active = true
    )
"""

ORGANIZATION_VALIDATE_UNIQUE_NAME = """
    SELECT EXISTS(
        SELECT 1 FROM {schema}.organizations
        WHERE name = $1 AND id != $2 AND is_active = true
    )
"""

ORGANIZATION_VALIDATE_TAX_ID = """
    SELECT EXISTS(
        SELECT 1 FROM {schema}.organizations
        WHERE tax_id = $1 AND id != $2 AND is_active = true
    )
"""

# Light vs Full data queries for performance optimization
ORGANIZATION_LIST_LIGHT = """
    SELECT 
        id, name, slug, industry, country_code, 
        is_active, verified_at, created_at, updated_at
    FROM {schema}.organizations
    WHERE is_active = true AND deleted_at IS NULL
    ORDER BY name
    LIMIT $1 OFFSET $2
"""

ORGANIZATION_LIST_FULL = """
    SELECT * FROM {schema}.organizations
    WHERE is_active = true AND deleted_at IS NULL
    ORDER BY name
    LIMIT $1 OFFSET $2
"""

ORGANIZATION_SEARCH_LIGHT = """
    SELECT 
        id, name, slug, industry, country_code, 
        is_active, verified_at, created_at, updated_at
    FROM {schema}.organizations
    WHERE ($1::text IS NULL OR name ILIKE $1::text OR slug ILIKE $1::text)
    AND ($2::text IS NULL OR industry = $2::text)
    AND ($3::text IS NULL OR country_code = $3::text)
    AND ($4::boolean IS NULL OR 
         CASE WHEN $4::boolean = true THEN verified_at IS NOT NULL 
              WHEN $4::boolean = false THEN verified_at IS NULL
              ELSE true END)
    AND ($5::boolean IS NULL OR is_active = $5::boolean)
    ORDER BY 
        CASE WHEN name ILIKE $1::text THEN 1 
             WHEN slug ILIKE $1::text THEN 2 
             ELSE 3 END,
        name
    LIMIT $6 OFFSET $7
"""

ORGANIZATION_SEARCH_FULL = """
    SELECT * FROM {schema}.organizations
    WHERE ($1::text IS NULL OR name ILIKE $1::text OR slug ILIKE $1::text)
    AND ($2::text IS NULL OR industry = $2::text)
    AND ($3::text IS NULL OR country_code = $3::text)
    AND ($4::boolean IS NULL OR 
         CASE WHEN $4::boolean = true THEN verified_at IS NOT NULL 
              WHEN $4::boolean = false THEN verified_at IS NULL
              ELSE true END)
    AND ($5::boolean IS NULL OR is_active = $5::boolean)
    ORDER BY 
        CASE WHEN name ILIKE $1::text THEN 1 
             WHEN slug ILIKE $1::text THEN 2 
             ELSE 3 END,
        name
    LIMIT $6 OFFSET $7
"""

# Admin queries with include_deleted option
ORGANIZATION_LIST_LIGHT_ADMIN = """
    SELECT 
        id, name, slug, industry, country_code, 
        is_active, verified_at, created_at, updated_at, deleted_at
    FROM {schema}.organizations
    WHERE ($1::boolean = false OR deleted_at IS NULL)
    AND is_active = true
    ORDER BY name
    LIMIT $2 OFFSET $3
"""

ORGANIZATION_LIST_FULL_ADMIN = """
    SELECT * FROM {schema}.organizations
    WHERE ($1::boolean = false OR deleted_at IS NULL)
    AND is_active = true
    ORDER BY name
    LIMIT $2 OFFSET $3
"""

ORGANIZATION_SEARCH_LIGHT_ADMIN = """
    SELECT 
        id, name, slug, industry, country_code, 
        is_active, verified_at, created_at, updated_at, deleted_at
    FROM {schema}.organizations
    WHERE ($1::text IS NULL OR name ILIKE $1::text OR slug ILIKE $1::text)
    AND ($2::text IS NULL OR industry = $2::text)
    AND ($3::text IS NULL OR country_code = $3::text)
    AND ($4::boolean IS NULL OR 
         CASE WHEN $4::boolean = true THEN verified_at IS NOT NULL 
              WHEN $4::boolean = false THEN verified_at IS NULL
              ELSE true END)
    AND ($5::boolean IS NULL OR is_active = $5::boolean)
    AND ($6::boolean = false OR deleted_at IS NULL)
    ORDER BY 
        CASE WHEN name ILIKE $1::text THEN 1 
             WHEN slug ILIKE $1::text THEN 2 
             ELSE 3 END,
        name
    LIMIT $7 OFFSET $8
"""

ORGANIZATION_SEARCH_FULL_ADMIN = """
    SELECT * FROM {schema}.organizations
    WHERE ($1::text IS NULL OR name ILIKE $1::text OR slug ILIKE $1::text)
    AND ($2::text IS NULL OR industry = $2::text)
    AND ($3::text IS NULL OR country_code = $3::text)
    AND ($4::boolean IS NULL OR 
         CASE WHEN $4::boolean = true THEN verified_at IS NOT NULL 
              WHEN $4::boolean = false THEN verified_at IS NULL
              ELSE true END)
    AND ($5::boolean IS NULL OR is_active = $5::boolean)
    AND ($6::boolean = false OR deleted_at IS NULL)
    ORDER BY 
        CASE WHEN name ILIKE $1::text THEN 1 
             WHEN slug ILIKE $1::text THEN 2 
             ELSE 3 END,
        name
    LIMIT $7 OFFSET $8
"""

# Organization metadata queries
ORGANIZATION_UPDATE_METADATA = """
    UPDATE {schema}.organizations SET
        metadata = $2,
        updated_at = $3
    WHERE id = $1
    RETURNING *
"""

ORGANIZATION_GET_METADATA = """
    SELECT metadata FROM {schema}.organizations
    WHERE id = $1 AND is_active = true
"""

ORGANIZATION_SEARCH_BY_METADATA = """
    SELECT * FROM {schema}.organizations
    WHERE is_active = true
    AND metadata @> $1
    ORDER BY name
    LIMIT $2 OFFSET $3
"""

# Organization audit queries
ORGANIZATION_AUDIT_LOG = """
    INSERT INTO {schema}.organization_audit_log (
        organization_id, action, actor_id, actor_type, changes, metadata, created_at
    )
    VALUES ($1, $2, $3, $4, $5, $6, $7)
    RETURNING *
"""

ORGANIZATION_AUDIT_HISTORY = """
    SELECT * FROM {schema}.organization_audit_log
    WHERE organization_id = $1
    ORDER BY created_at DESC
    LIMIT $2 OFFSET $3
"""

# Organization health and maintenance queries
ORGANIZATION_HEALTH_CHECK = """
    SELECT 
        COUNT(*) as total_organizations,
        COUNT(CASE WHEN is_active THEN 1 END) as active_organizations,
        COUNT(CASE WHEN verified_at IS NOT NULL THEN 1 END) as verified_organizations,
        COUNT(CASE WHEN created_at > NOW() - INTERVAL '24 hours' THEN 1 END) as recent_organizations
    FROM {schema}.organizations
"""

ORGANIZATION_CLEANUP_INACTIVE = """
    DELETE FROM {schema}.organizations
    WHERE is_active = false
    AND updated_at < NOW() - INTERVAL '{retention_days} days'
    RETURNING id, name, slug
"""

# Specialized query builders
def build_organization_search_query(
    schema: str,
    filters: Dict[str, any] = None,
    order_by: str = "name",
    order_direction: str = "ASC"
) -> str:
    """Build dynamic organization search query with filters.
    
    Args:
        schema: Database schema name
        filters: Optional filters dictionary
        order_by: Order by field
        order_direction: Order direction (ASC/DESC)
        
    Returns:
        Formatted SQL query string
    """
    base_query = f"SELECT * FROM {schema}.organizations WHERE is_active = true AND deleted_at IS NULL"
    
    if filters:
        conditions = []
        param_count = 1
        
        if "name" in filters:
            conditions.append(f"name ILIKE ${param_count}")
            param_count += 1
            
        if "industry" in filters:
            conditions.append(f"industry = ${param_count}")
            param_count += 1
            
        if "country_code" in filters:
            conditions.append(f"country_code = ${param_count}")
            param_count += 1
            
        if "is_verified" in filters:
            if filters["is_verified"]:
                conditions.append(f"verified_at IS NOT NULL")
            else:
                conditions.append(f"verified_at IS NULL")
            
        if "company_size" in filters:
            conditions.append(f"company_size = ${param_count}")
            param_count += 1
            
        if conditions:
            base_query += " AND " + " AND ".join(conditions)
    
    # Add ordering
    base_query += f" ORDER BY {order_by} {order_direction.upper()}"
    
    return base_query


def build_organization_stats_query(
    schema: str, 
    stat_type: str = "basic",
    time_period_days: int = 30
) -> str:
    """Build dynamic organization statistics query.
    
    Args:
        schema: Database schema name
        stat_type: Type of statistics (basic, industry, country, etc.)
        time_period_days: Time period in days for time-based stats
        
    Returns:
        Formatted SQL query string
    """
    queries = {
        "basic": ORGANIZATION_STATS_BASIC,
        "industry": ORGANIZATION_STATS_BY_INDUSTRY,
        "country": ORGANIZATION_STATS_BY_COUNTRY,
        "company_size": ORGANIZATION_STATS_BY_COMPANY_SIZE,
        "recent_activity": ORGANIZATION_STATS_RECENT_ACTIVITY,
        "verification_trends": ORGANIZATION_STATS_VERIFICATION_TRENDS
    }
    
    if stat_type not in queries:
        raise ValueError(f"Unknown stat_type: {stat_type}")
    
    query = queries[stat_type]
    
    # Format schema and time period
    if stat_type in ["recent_activity", "verification_trends"]:
        return query.format(schema=schema, days=time_period_days)
    else:
        return query.format(schema=schema)


# Query templates organized by operation type
ORGANIZATION_QUERIES = {
    "create": ORGANIZATION_INSERT,
    "update": ORGANIZATION_UPDATE,
    "delete_soft": ORGANIZATION_DELETE_SOFT,
    "delete_hard": ORGANIZATION_DELETE_HARD,
    "get_by_id": ORGANIZATION_GET_BY_ID,
    "get_by_slug": ORGANIZATION_GET_BY_SLUG,
    "exists_by_id": ORGANIZATION_EXISTS_BY_ID,
    "exists_by_slug": ORGANIZATION_EXISTS_BY_SLUG,
    "list_all": ORGANIZATION_LIST_ALL,
    "list_paginated": ORGANIZATION_LIST_PAGINATED,
    "count_all": ORGANIZATION_COUNT_ALL,
    "search_by_name": ORGANIZATION_SEARCH_BY_NAME,
    "search_advanced": ORGANIZATION_SEARCH_ADVANCED,
    "search_by_metadata": ORGANIZATION_SEARCH_BY_METADATA,
    "update_metadata": ORGANIZATION_UPDATE_METADATA,
    "get_metadata": ORGANIZATION_GET_METADATA,
    "stats_basic": ORGANIZATION_STATS_BASIC,
    "stats_by_industry": ORGANIZATION_STATS_BY_INDUSTRY,
    "stats_by_country": ORGANIZATION_STATS_BY_COUNTRY,
    "health_check": ORGANIZATION_HEALTH_CHECK,
    "validate_unique_slug": ORGANIZATION_VALIDATE_UNIQUE_SLUG,
    "validate_unique_name": ORGANIZATION_VALIDATE_UNIQUE_NAME,
    "audit_log": ORGANIZATION_AUDIT_LOG,
    "audit_history": ORGANIZATION_AUDIT_HISTORY
}