"""
Permission Data Source for Neo-Commons

Provides abstraction for loading permission data from various sources
including databases, external services, and cached stores.
"""
from typing import Optional, Dict, Any, List, Set
from loguru import logger

from ..core import (
    AuthConfigProtocol,
    AuthenticationError,
    UserNotFoundError,
    ExternalServiceError,
)
from .protocols import PermissionDataSourceProtocol


class DatabasePermissionDataSource:
    """
    Database-based permission data source.
    
    Loads permission data directly from PostgreSQL databases using
    the repository pattern and protocol-based dependency injection.
    """
    
    def __init__(
        self,
        repository,  # BasePermissionRepositoryProtocol - avoiding import for now
        config: Optional[AuthConfigProtocol] = None
    ):
        """
        Initialize database permission data source.
        
        Args:
            repository: Permission repository for database operations
            config: Optional configuration
        """
        self.repository = repository
        self.config = config
        logger.info("Initialized DatabasePermissionDataSource")
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all permissions for a user from database.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant context
            
        Returns:
            List of permission details
            
        Raises:
            UserNotFoundError: If user doesn't exist
            ExternalServiceError: If database operation fails
        """
        try:
            # Get permissions from repository
            permissions = await self.repository.get_user_permissions(user_id, tenant_id)
            
            if permissions is None:
                logger.warning(f"User {user_id} not found")
                raise UserNotFoundError(f"User {user_id} not found")
            
            logger.debug(f"Loaded {len(permissions)} permissions for user {user_id}")
            return permissions
            
        except UserNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to load permissions for user {user_id}: {e}")
            raise ExternalServiceError(f"Database permission lookup failed: {str(e)}")
    
    async def get_user_roles(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all roles for a user from database.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant context
            
        Returns:
            List of role assignments
            
        Raises:
            UserNotFoundError: If user doesn't exist
            ExternalServiceError: If database operation fails
        """
        try:
            # Get roles from repository
            roles = await self.repository.get_user_roles(user_id, tenant_id)
            
            if roles is None:
                logger.warning(f"User {user_id} not found")
                raise UserNotFoundError(f"User {user_id} not found")
            
            logger.debug(f"Loaded {len(roles)} roles for user {user_id}")
            return roles
            
        except UserNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to load roles for user {user_id}: {e}")
            raise ExternalServiceError(f"Database role lookup failed: {str(e)}")
    
    async def get_user_permission_summary(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Set[str]]:
        """
        Get a summary of user permissions grouped by resource.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant context
            
        Returns:
            Dict mapping resource to set of actions
            
        Raises:
            UserNotFoundError: If user doesn't exist
            ExternalServiceError: If database operation fails
        """
        try:
            # Get permission summary from repository
            summary = await self.repository.get_user_permission_summary(user_id, tenant_id)
            
            if summary is None:
                logger.warning(f"User {user_id} not found")
                raise UserNotFoundError(f"User {user_id} not found")
            
            logger.debug(f"Loaded permission summary for user {user_id}")
            return summary
            
        except UserNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to load permission summary for user {user_id}: {e}")
            raise ExternalServiceError(f"Database permission summary failed: {str(e)}")
    
    async def get_users_with_role(
        self,
        role_id: str,
        tenant_id: Optional[str] = None
    ) -> List[str]:
        """
        Get all user IDs that have a specific role.
        
        Args:
            role_id: Role UUID
            tenant_id: Optional tenant context
            
        Returns:
            List of user IDs
            
        Raises:
            ExternalServiceError: If database operation fails
        """
        try:
            # Get users with role from repository
            user_ids = await self.repository.get_users_with_role(role_id, tenant_id)
            
            logger.debug(f"Found {len(user_ids)} users with role {role_id}")
            return user_ids
            
        except Exception as e:
            logger.error(f"Failed to get users with role {role_id}: {e}")
            raise ExternalServiceError(f"Database role lookup failed: {str(e)}")
    
    async def validate_user_exists(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Validate that a user exists in the database.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant context
            
        Returns:
            True if user exists
            
        Raises:
            ExternalServiceError: If database operation fails
        """
        try:
            # Check if user exists
            exists = await self.repository.user_exists(user_id, tenant_id)
            
            logger.debug(f"User {user_id} exists: {exists}")
            return exists
            
        except Exception as e:
            logger.error(f"Failed to validate user {user_id}: {e}")
            raise ExternalServiceError(f"Database user validation failed: {str(e)}")


class CompositePermissionDataSource:
    """
    Composite permission data source.
    
    Combines multiple data sources with fallback strategies and
    intelligent caching for optimal performance.
    """
    
    def __init__(
        self,
        primary_source: PermissionDataSourceProtocol,
        fallback_sources: Optional[List[PermissionDataSourceProtocol]] = None,
        config: Optional[AuthConfigProtocol] = None
    ):
        """
        Initialize composite permission data source.
        
        Args:
            primary_source: Primary data source
            fallback_sources: Optional list of fallback sources
            config: Optional configuration
        """
        self.primary_source = primary_source
        self.fallback_sources = fallback_sources or []
        self.config = config
        logger.info(f"Initialized CompositePermissionDataSource with {len(self.fallback_sources)} fallback sources")
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get user permissions with fallback support.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant context
            
        Returns:
            List of permission details
            
        Raises:
            UserNotFoundError: If user doesn't exist in any source
            ExternalServiceError: If all sources fail
        """
        # Try primary source first
        try:
            return await self.primary_source.get_user_permissions(user_id, tenant_id)
        except UserNotFoundError:
            # User not found, don't try fallback sources
            raise
        except Exception as e:
            logger.warning(f"Primary source failed for user {user_id}: {e}")
        
        # Try fallback sources
        for i, fallback_source in enumerate(self.fallback_sources):
            try:
                logger.info(f"Trying fallback source {i+1} for user {user_id}")
                return await fallback_source.get_user_permissions(user_id, tenant_id)
            except UserNotFoundError:
                # User not found, don't try remaining sources
                raise
            except Exception as e:
                logger.warning(f"Fallback source {i+1} failed for user {user_id}: {e}")
        
        # All sources failed
        raise ExternalServiceError("All permission data sources failed")
    
    async def get_user_roles(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get user roles with fallback support.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant context
            
        Returns:
            List of role assignments
            
        Raises:
            UserNotFoundError: If user doesn't exist in any source
            ExternalServiceError: If all sources fail
        """
        # Try primary source first
        try:
            return await self.primary_source.get_user_roles(user_id, tenant_id)
        except UserNotFoundError:
            # User not found, don't try fallback sources
            raise
        except Exception as e:
            logger.warning(f"Primary source failed for user roles {user_id}: {e}")
        
        # Try fallback sources
        for i, fallback_source in enumerate(self.fallback_sources):
            try:
                logger.info(f"Trying fallback source {i+1} for user roles {user_id}")
                return await fallback_source.get_user_roles(user_id, tenant_id)
            except UserNotFoundError:
                # User not found, don't try remaining sources
                raise
            except Exception as e:
                logger.warning(f"Fallback source {i+1} failed for user roles {user_id}: {e}")
        
        # All sources failed
        raise ExternalServiceError("All role data sources failed")
    
    async def get_user_permission_summary(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Set[str]]:
        """
        Get user permission summary with fallback support.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant context
            
        Returns:
            Dict mapping resource to set of actions
            
        Raises:
            UserNotFoundError: If user doesn't exist in any source
            ExternalServiceError: If all sources fail
        """
        # Try primary source first
        try:
            return await self.primary_source.get_user_permission_summary(user_id, tenant_id)
        except UserNotFoundError:
            # User not found, don't try fallback sources
            raise
        except Exception as e:
            logger.warning(f"Primary source failed for user summary {user_id}: {e}")
        
        # Try fallback sources
        for i, fallback_source in enumerate(self.fallback_sources):
            try:
                logger.info(f"Trying fallback source {i+1} for user summary {user_id}")
                return await fallback_source.get_user_permission_summary(user_id, tenant_id)
            except UserNotFoundError:
                # User not found, don't try remaining sources
                raise
            except Exception as e:
                logger.warning(f"Fallback source {i+1} failed for user summary {user_id}: {e}")
        
        # All sources failed
        raise ExternalServiceError("All permission summary sources failed")
    
    async def get_users_with_role(
        self,
        role_id: str,
        tenant_id: Optional[str] = None
    ) -> List[str]:
        """
        Get users with role with fallback support.
        
        Args:
            role_id: Role UUID
            tenant_id: Optional tenant context
            
        Returns:
            List of user IDs
            
        Raises:
            ExternalServiceError: If all sources fail
        """
        # Try primary source first
        try:
            return await self.primary_source.get_users_with_role(role_id, tenant_id)
        except Exception as e:
            logger.warning(f"Primary source failed for role users {role_id}: {e}")
        
        # Try fallback sources
        for i, fallback_source in enumerate(self.fallback_sources):
            try:
                logger.info(f"Trying fallback source {i+1} for role users {role_id}")
                return await fallback_source.get_users_with_role(role_id, tenant_id)
            except Exception as e:
                logger.warning(f"Fallback source {i+1} failed for role users {role_id}: {e}")
        
        # All sources failed
        raise ExternalServiceError("All role user sources failed")


class CachedPermissionDataSource:
    """
    Cached permission data source wrapper.
    
    Wraps any data source with intelligent caching to improve performance.
    """
    
    def __init__(
        self,
        wrapped_source: PermissionDataSourceProtocol,
        cache_service,  # TenantAwareCacheProtocol - avoiding import for now
        config: Optional[AuthConfigProtocol] = None
    ):
        """
        Initialize cached permission data source.
        
        Args:
            wrapped_source: Data source to wrap with caching
            cache_service: Cache service for storing data
            config: Optional configuration
        """
        self.wrapped_source = wrapped_source
        self.cache = cache_service
        self.config = config
        
        # Cache TTL configuration
        self.PERMISSION_CACHE_TTL = 600  # 10 minutes
        self.ROLE_CACHE_TTL = 900        # 15 minutes
        self.SUMMARY_CACHE_TTL = 300     # 5 minutes
        
        logger.info("Initialized CachedPermissionDataSource")
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get user permissions with caching.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant context
            
        Returns:
            List of permission details
        """
        # Build cache key
        cache_key = f"datasource:permissions:user:{user_id}"
        if tenant_id:
            cache_key += f":tenant:{tenant_id}"
        
        # Try cache first
        cached = await self.cache.get(cache_key, tenant_id=tenant_id)
        if cached:
            logger.debug(f"Cache hit for user {user_id} permissions")
            return cached
        
        # Load from wrapped source
        permissions = await self.wrapped_source.get_user_permissions(user_id, tenant_id)
        
        # Cache the result
        if permissions:
            await self.cache.set(
                cache_key,
                permissions,
                ttl=self.PERMISSION_CACHE_TTL,
                tenant_id=tenant_id
            )
        
        return permissions
    
    async def get_user_roles(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get user roles with caching.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant context
            
        Returns:
            List of role assignments
        """
        # Build cache key
        cache_key = f"datasource:roles:user:{user_id}"
        if tenant_id:
            cache_key += f":tenant:{tenant_id}"
        
        # Try cache first
        cached = await self.cache.get(cache_key, tenant_id=tenant_id)
        if cached:
            logger.debug(f"Cache hit for user {user_id} roles")
            return cached
        
        # Load from wrapped source
        roles = await self.wrapped_source.get_user_roles(user_id, tenant_id)
        
        # Cache the result
        if roles:
            await self.cache.set(
                cache_key,
                roles,
                ttl=self.ROLE_CACHE_TTL,
                tenant_id=tenant_id
            )
        
        return roles
    
    async def get_user_permission_summary(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Set[str]]:
        """
        Get user permission summary with caching.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant context
            
        Returns:
            Dict mapping resource to set of actions
        """
        # Build cache key
        cache_key = f"datasource:summary:user:{user_id}"
        if tenant_id:
            cache_key += f":tenant:{tenant_id}"
        
        # Try cache first
        cached = await self.cache.get(cache_key, tenant_id=tenant_id)
        if cached:
            logger.debug(f"Cache hit for user {user_id} permission summary")
            # Convert sets back from list format if needed
            if isinstance(cached, dict):
                for resource, actions in cached.items():
                    if isinstance(actions, list):
                        cached[resource] = set(actions)
            return cached
        
        # Load from wrapped source
        summary = await self.wrapped_source.get_user_permission_summary(user_id, tenant_id)
        
        # Cache the result (convert sets to lists for JSON serialization)
        if summary:
            cache_data = {}
            for resource, actions in summary.items():
                cache_data[resource] = list(actions) if isinstance(actions, set) else actions
            
            await self.cache.set(
                cache_key,
                cache_data,
                ttl=self.SUMMARY_CACHE_TTL,
                tenant_id=tenant_id
            )
        
        return summary
    
    async def get_users_with_role(
        self,
        role_id: str,
        tenant_id: Optional[str] = None
    ) -> List[str]:
        """
        Get users with role with caching.
        
        Args:
            role_id: Role UUID
            tenant_id: Optional tenant context
            
        Returns:
            List of user IDs
        """
        # Always delegate to wrapped source for this operation
        # (user lists can change frequently)
        return await self.wrapped_source.get_users_with_role(role_id, tenant_id)


__all__ = [
    "DatabasePermissionDataSource",
    "CompositePermissionDataSource", 
    "CachedPermissionDataSource",
]