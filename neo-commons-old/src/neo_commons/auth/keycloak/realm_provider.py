"""
Realm Provider Implementations

Provides realm resolution for multi-tenant Keycloak configurations.
Supports both admin and tenant realm patterns.
"""

from typing import Any, Dict, Optional

from .protocols import RealmProviderProtocol


class AdminRealmProvider:
    """
    Realm provider for admin service operations.
    
    Uses admin realm for all operations by default.
    """
    
    def __init__(self, admin_realm: str = "admin"):
        """
        Initialize admin realm provider.
        
        Args:
            admin_realm: Admin realm name
        """
        self.admin_realm = admin_realm
    
    async def get_admin_realm(self) -> str:
        """Get the admin realm name."""
        return self.admin_realm
    
    async def get_tenant_realm(self, tenant_id: str) -> str:
        """
        For admin service, tenant operations use admin realm.
        
        Args:
            tenant_id: Tenant identifier (not used for admin realm)
            
        Returns:
            Admin realm name
        """
        return self.admin_realm
    
    async def resolve_realm_from_context(self, context: Dict[str, Any]) -> str:
        """
        Resolve realm from request context (always admin realm).
        
        Args:
            context: Request context (not used for admin realm)
            
        Returns:
            Admin realm name
        """
        return self.admin_realm
    
    async def get_realm_for_user(self, user_id: str) -> str:
        """
        Get realm for user (always admin realm).
        
        Args:
            user_id: User identifier (not used for admin realm)
            
        Returns:
            Admin realm name
        """
        return self.admin_realm


class TenantRealmProvider:
    """
    Realm provider for tenant service operations.
    
    Uses tenant-specific realms with fallback to admin realm.
    """
    
    def __init__(
        self,
        admin_realm: str = "admin",
        realm_pattern: str = "tenant-{slug}"
    ):
        """
        Initialize tenant realm provider.
        
        Args:
            admin_realm: Admin realm name for fallback
            realm_pattern: Pattern for tenant realm names
        """
        self.admin_realm = admin_realm
        self.realm_pattern = realm_pattern
    
    async def get_admin_realm(self) -> str:
        """Get the admin realm name."""
        return self.admin_realm
    
    async def get_tenant_realm(self, tenant_id: str) -> str:
        """
        Get tenant-specific realm.
        
        Args:
            tenant_id: Tenant identifier or slug
            
        Returns:
            Tenant realm name
        """
        # For now, use simple pattern - can be enhanced with DB lookup
        return self.realm_pattern.format(slug=tenant_id)
    
    async def resolve_realm_from_context(self, context: Dict[str, Any]) -> str:
        """
        Resolve realm from request context.
        
        Args:
            context: Request context containing tenant info
            
        Returns:
            Appropriate realm name
        """
        tenant_id = context.get("tenant_id")
        if tenant_id:
            return await self.get_tenant_realm(tenant_id)
        return self.admin_realm
    
    async def get_realm_for_user(self, user_id: str) -> str:
        """
        Get realm for user (requires tenant context).
        
        Args:
            user_id: User identifier
            
        Returns:
            Realm name (admin realm as fallback)
        """
        # For now, fallback to admin realm
        # Can be enhanced with user-to-tenant mapping
        return self.admin_realm


class ConfigurableRealmProvider:
    """
    Configurable realm provider for flexible deployment scenarios.
    
    Supports both single-realm and multi-realm configurations.
    """
    
    def __init__(
        self,
        admin_realm: str = "admin",
        default_tenant_realm: Optional[str] = None,
        use_tenant_realms: bool = True,
        realm_pattern: str = "tenant-{slug}"
    ):
        """
        Initialize configurable realm provider.
        
        Args:
            admin_realm: Admin realm name
            default_tenant_realm: Default tenant realm (if not using pattern)
            use_tenant_realms: Whether to use separate tenant realms
            realm_pattern: Pattern for tenant realm names
        """
        self.admin_realm = admin_realm
        self.default_tenant_realm = default_tenant_realm
        self.use_tenant_realms = use_tenant_realms
        self.realm_pattern = realm_pattern
    
    async def get_admin_realm(self) -> str:
        """Get the admin realm name."""
        return self.admin_realm
    
    async def get_tenant_realm(self, tenant_id: str) -> str:
        """
        Get realm for tenant based on configuration.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Tenant realm name
        """
        if not self.use_tenant_realms:
            return self.default_tenant_realm or self.admin_realm
        
        return self.realm_pattern.format(slug=tenant_id)
    
    async def resolve_realm_from_context(self, context: Dict[str, Any]) -> str:
        """
        Resolve realm from request context.
        
        Args:
            context: Request context
            
        Returns:
            Appropriate realm name
        """
        # Check for explicit realm override
        realm = context.get("realm")
        if realm:
            return realm
        
        # Check for tenant context
        tenant_id = context.get("tenant_id")
        if tenant_id:
            return await self.get_tenant_realm(tenant_id)
        
        # Check if this is admin operation
        is_admin = context.get("is_admin", False)
        if is_admin:
            return self.admin_realm
        
        # Default to admin realm
        return self.admin_realm
    
    async def get_realm_for_user(self, user_id: str) -> str:
        """
        Get realm for user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Realm name
        """
        # This would typically involve DB lookup
        # For now, return admin realm as safe fallback
        return self.admin_realm


__all__ = [
    "AdminRealmProvider",
    "TenantRealmProvider", 
    "ConfigurableRealmProvider",
]