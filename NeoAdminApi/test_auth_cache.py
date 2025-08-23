#!/usr/bin/env python3
"""Test script for auth cache functionality."""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_auth_cache():
    """Test the auth cache service functionality."""
    
    # Import neo-commons components
    from neo_commons.features.auth import AuthServiceFactory
    from neo_commons.core.value_objects.identifiers import UserId, TenantId, PermissionCode, RoleCode
    from neo_commons.config.manager import get_env_config
    
    print("=== Testing Auth Cache Service ===\n")
    
    # Get environment configuration
    env_config = get_env_config()
    print(f"Cache TTL Configuration:")
    print(f"  Default TTL: {env_config.cache_default_ttl}s")
    print(f"  Permissions TTL: {env_config.cache_permissions_ttl}s")
    print(f"  Roles TTL: {env_config.cache_roles_ttl}s")
    print(f"  User Data TTL: {env_config.cache_user_data_ttl}s")
    print(f"  Auth Context TTL: {env_config.cache_auth_context_ttl}s")
    print()
    
    # Create auth service factory
    print("Creating auth service factory...")
    factory = AuthServiceFactory(
        keycloak_server_url=env_config.keycloak_server_url,
        keycloak_admin_username=env_config.keycloak_admin or "admin",
        keycloak_admin_password=env_config.keycloak_password or "admin",
        redis_url=env_config.redis_url,
        redis_password=env_config.redis_password,
    )
    
    # Get auth cache service
    print("Initializing auth cache service...")
    auth_cache_service = await factory.get_auth_cache_service()
    print("Auth cache service initialized successfully!\n")
    
    # Test data
    user_id = UserId("550e8400-e29b-41d4-a716-446655440001")
    tenant_id = TenantId("550e8400-e29b-41d4-a716-446655440002")
    
    # Test permissions caching
    print("Testing permissions caching...")
    
    # Create test permissions
    test_permissions = {
        PermissionCode("read:users"),
        PermissionCode("write:users"),
        PermissionCode("delete:users"),
    }
    
    # Cache permissions
    await auth_cache_service.set_user_permissions(
        user_id, tenant_id, test_permissions
    )
    print(f"Cached {len(test_permissions)} permissions")
    
    # Retrieve from cache
    cached_permissions = await auth_cache_service.get_user_permissions(
        user_id, tenant_id
    )
    
    if cached_permissions:
        print(f"Retrieved {len(cached_permissions)} permissions from cache:")
        for perm in cached_permissions:
            print(f"  - {perm.value}")
    else:
        print("No permissions found in cache")
    
    print()
    
    # Test roles caching
    print("Testing roles caching...")
    
    # Create test roles
    test_roles = {
        RoleCode("admin"),
        RoleCode("user"),
        RoleCode("moderator"),
    }
    
    # Cache roles
    await auth_cache_service.set_user_roles(
        user_id, tenant_id, test_roles
    )
    print(f"Cached {len(test_roles)} roles")
    
    # Retrieve from cache
    cached_roles = await auth_cache_service.get_user_roles(
        user_id, tenant_id
    )
    
    if cached_roles:
        print(f"Retrieved {len(cached_roles)} roles from cache:")
        for role in cached_roles:
            print(f"  - {role.value}")
    else:
        print("No roles found in cache")
    
    print()
    
    # Test user data caching
    print("Testing user data caching...")
    
    # Create test user data
    test_user_data = {
        "id": user_id.value,
        "tenant_id": tenant_id.value,
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "is_active": True,
    }
    
    # Cache user data
    await auth_cache_service.set_user_data(
        user_id, tenant_id, test_user_data
    )
    print("Cached user data")
    
    # Retrieve from cache
    cached_user_data = await auth_cache_service.get_user_data(
        user_id, tenant_id
    )
    
    if cached_user_data:
        print("Retrieved user data from cache:")
        for key, value in cached_user_data.items():
            print(f"  {key}: {value}")
    else:
        print("No user data found in cache")
    
    print()
    
    # Test cache invalidation
    print("Testing cache invalidation...")
    
    # Invalidate specific caches
    await auth_cache_service.invalidate_user_permissions(user_id, tenant_id)
    print("Invalidated permissions cache")
    
    await auth_cache_service.invalidate_user_roles(user_id, tenant_id)
    print("Invalidated roles cache")
    
    # Check if cache was invalidated
    cached_permissions = await auth_cache_service.get_user_permissions(
        user_id, tenant_id
    )
    cached_roles = await auth_cache_service.get_user_roles(
        user_id, tenant_id
    )
    
    print(f"Permissions after invalidation: {cached_permissions}")
    print(f"Roles after invalidation: {cached_roles}")
    
    # Invalidate all user cache
    count = await auth_cache_service.invalidate_user(user_id, tenant_id)
    print(f"Invalidated {count} total cache entries for user")
    
    # Check user data after invalidation
    cached_user_data = await auth_cache_service.get_user_data(
        user_id, tenant_id
    )
    print(f"User data after invalidation: {cached_user_data}")
    
    print()
    
    # Get cache statistics
    print("Cache statistics:")
    stats = await auth_cache_service.get_cache_stats()
    for key, value in stats.get('auth_cache', {}).items():
        print(f"  {key}: {value}")
    
    print("\n=== Auth Cache Test Complete ===")
    
    # Cleanup
    cache_service = await factory.get_cache_service()
    await cache_service.shutdown()


if __name__ == "__main__":
    asyncio.run(test_auth_cache())