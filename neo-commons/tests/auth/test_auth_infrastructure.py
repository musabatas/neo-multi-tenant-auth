"""
Integration Tests for Neo-Commons Auth Infrastructure

Comprehensive tests validating the extracted auth infrastructure works correctly with:
- Protocol compliance testing
- Import validation
- Backward compatibility verification
- Permission registry functionality
- Service wrapper integration
"""

import asyncio
import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock

# Import all auth components to validate imports work
from neo_commons.auth import (
    # Protocols
    TokenValidatorProtocol,
    PermissionCheckerProtocol, 
    GuestAuthServiceProtocol,
    CacheServiceProtocol,
    AuthConfigProtocol,
    ValidationStrategy,
    PermissionScope,
    
    # Decorators
    RequirePermission,
    require_permission,
    PermissionMetadata,
    
    # Dependencies
    CurrentUser,
    CheckPermission,
    TokenData,
    GuestOrAuthenticated,
    GuestSessionInfo,
    
    # Registry
    PermissionRegistry,
    PermissionDefinition,
    get_permission_registry,
    PLATFORM_PERMISSIONS,
    TENANT_PERMISSIONS,
    PERMISSION_GROUPS,
    
    # Services
    AuthServiceWrapper,
    PermissionServiceWrapper,
    GuestAuthServiceWrapper,
    create_auth_service,
    create_permission_service,
    create_guest_auth_service
)


class MockTokenValidator:
    """Mock implementation of TokenValidatorProtocol for testing."""
    
    async def validate_token(
        self,
        token: str,
        realm: str,
        strategy: ValidationStrategy = ValidationStrategy.DUAL,
        critical: bool = False
    ) -> Dict[str, Any]:
        """Mock token validation."""
        return {
            "sub": "test-user-123",
            "preferred_username": "testuser",
            "email": "test@example.com",
            "given_name": "Test",
            "family_name": "User",
            "name": "Test User",
            "iss": f"http://keycloak/realms/{realm}",
            "iat": 1640995200,
            "exp": 1641081600,
            "access_token": token,
            "realm": realm
        }
    
    async def authenticate_user(
        self,
        username: str,
        password: str,
        realm: str
    ) -> Dict[str, Any]:
        """Mock user authentication."""
        return {
            "sub": "test-user-123",
            "preferred_username": username,
            "email": f"{username}@example.com",
            "access_token": "mock-access-token",
            "refresh_token": "mock-refresh-token",
            "expires_in": 3600,
            "realm": realm
        }
    
    async def is_token_revoked(self, token: str) -> bool:
        """Mock token revocation check."""
        return False
    
    async def revoke_token(self, token: str, realm: str) -> bool:
        """Mock token revocation."""
        return True
    
    async def refresh_if_needed(self, token: str, refresh_token: str, realm: str) -> Optional[tuple]:
        """Mock token refresh."""
        return None
    
    async def clear_user_tokens(self, user_id: str) -> int:
        """Mock clear user tokens."""
        return 1


class MockPermissionChecker:
    """Mock implementation of PermissionCheckerProtocol for testing."""
    
    async def check_permission(
        self,
        user_id: str,
        permissions: List[str],
        scope: str = "platform",
        tenant_id: Optional[str] = None,
        any_of: bool = False
    ) -> bool:
        """Mock permission checking."""
        # Grant permissions for test user
        if user_id == "test-user-123":
            return True
        return False
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Mock get user permissions."""
        if user_id == "test-user-123":
            return [
                {"code": "users:read", "scope": "platform"},
                {"code": "tenants:read", "scope": "platform"}
            ]
        return []


class MockGuestAuthService:
    """Mock implementation of GuestAuthServiceProtocol for testing."""
    
    async def get_or_create_guest_session(
        self,
        session_token: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        referrer: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mock guest session creation."""
        return {
            "session_token": session_token or "guest-session-123",
            "guest_id": "guest-456",
            "ip_address": ip_address or "127.0.0.1",
            "user_agent": user_agent or "test-agent",
            "created_at": "2024-01-01T00:00:00Z",
            "expires_at": "2024-01-01T01:00:00Z"
        }
    
    async def get_session_stats(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Mock session statistics."""
        return {
            "session_token": session_token,
            "request_count": 5,
            "last_activity": "2024-01-01T00:30:00Z"
        }


class MockCacheService:
    """Mock implementation of CacheServiceProtocol for testing."""
    
    def __init__(self):
        self._cache = {}
    
    async def get(self, key: str) -> Any:
        """Mock cache get."""
        return self._cache.get(key)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Mock cache set."""
        self._cache[key] = value
    
    async def delete(self, key: str) -> None:
        """Mock cache delete."""
        self._cache.pop(key, None)
    
    async def health_check(self) -> bool:
        """Mock cache health check."""
        return True


class MockAuthConfig:
    """Mock implementation of AuthConfigProtocol for testing."""
    
    @property
    def keycloak_url(self) -> str:
        return "http://localhost:8080"
    
    @property
    def admin_client_id(self) -> str:
        return "admin-client"
    
    @property
    def admin_client_secret(self) -> str:
        return "admin-secret"
    
    @property
    def admin_username(self) -> str:
        return "admin"
    
    @property
    def admin_password(self) -> str:
        return "admin-password"
    
    @property
    def jwt_algorithm(self) -> str:
        return "RS256"
    
    @property
    def jwt_verify_audience(self) -> bool:
        return True
    
    @property
    def jwt_verify_issuer(self) -> bool:
        return True
    
    @property
    def jwt_audience(self) -> Optional[str]:
        return "account"
    
    @property
    def jwt_issuer(self) -> Optional[str]:
        return "http://localhost:8080/realms/master"
    
    @property
    def default_realm(self) -> str:
        return "master"
    
    @property
    def default_validation_strategy(self) -> ValidationStrategy:
        return ValidationStrategy.DUAL


class TestAuthInfrastructureIntegration:
    """Integration tests for auth infrastructure."""
    
    def test_import_validation(self):
        """Test that all auth modules can be imported without errors."""
        # All imports should work (already imported at top)
        assert TokenValidatorProtocol is not None
        assert PermissionCheckerProtocol is not None
        assert RequirePermission is not None
        assert PermissionRegistry is not None
        assert AuthServiceWrapper is not None
        print("✅ All auth module imports successful")
    
    def test_protocol_compliance(self):
        """Test that mock implementations are protocol compliant."""
        mock_token_validator = MockTokenValidator()
        mock_permission_checker = MockPermissionChecker()
        mock_guest_service = MockGuestAuthService()
        mock_cache_service = MockCacheService()
        mock_auth_config = MockAuthConfig()
        
        # Verify protocol compliance
        assert isinstance(mock_token_validator, TokenValidatorProtocol)
        assert isinstance(mock_permission_checker, PermissionCheckerProtocol)
        assert isinstance(mock_guest_service, GuestAuthServiceProtocol)
        assert isinstance(mock_cache_service, CacheServiceProtocol)
        assert isinstance(mock_auth_config, AuthConfigProtocol)
        print("✅ All mock implementations are protocol compliant")
    
    def test_permission_registry_functionality(self):
        """Test permission registry core functionality."""
        registry = PermissionRegistry()
        
        # Test basic functionality
        assert len(PLATFORM_PERMISSIONS) > 0
        assert len(TENANT_PERMISSIONS) > 0
        assert len(PERMISSION_GROUPS) > 0
        
        # Test permission lookup
        async def test_permission_lookup():
            # Test platform permission exists
            platform_perm = await registry.get_permission("users:read")
            assert platform_perm is not None
            assert platform_perm.scope == "platform"
            
            # Test tenant permission exists  
            tenant_perm = await registry.get_permission("tenant:read")
            assert tenant_perm is not None
            assert tenant_perm.scope == "tenant"
            
            # Test validation
            assert await registry.validate_permission("users:read") == True
            assert await registry.validate_permission("invalid:permission") == False
            
            # Test scope filtering
            platform_perms = await registry.get_permissions_by_scope("platform")
            assert len(platform_perms) > 0
            
            tenant_perms = await registry.get_permissions_by_scope("tenant")
            assert len(tenant_perms) > 0
            
            # Test dangerous permissions
            dangerous_perms = await registry.get_dangerous_permissions()
            assert len(dangerous_perms) > 0
            
            # Test permission group expansion
            admin_perms = await registry.expand_permission_group("platform_admin")
            assert len(admin_perms) > 0
            assert "users:read" in admin_perms
        
        asyncio.run(test_permission_lookup())
        print("✅ Permission registry functionality validated")
    
    def test_service_wrapper_integration(self):
        """Test service wrapper backward compatibility."""
        mock_token_validator = MockTokenValidator()
        mock_permission_checker = MockPermissionChecker()
        mock_guest_service = MockGuestAuthService()
        mock_cache_service = MockCacheService()
        mock_auth_config = MockAuthConfig()
        
        # Test factory functions
        auth_service = create_auth_service(
            mock_token_validator, mock_permission_checker, mock_auth_config, mock_cache_service
        )
        permission_service = create_permission_service(
            mock_permission_checker, mock_cache_service
        )
        guest_service = create_guest_auth_service(
            mock_guest_service, mock_cache_service
        )
        
        assert isinstance(auth_service, AuthServiceWrapper)
        assert isinstance(permission_service, PermissionServiceWrapper)
        assert isinstance(guest_service, GuestAuthServiceWrapper)
        
        # Test service wrapper functionality
        async def test_service_operations():
            # Test authentication
            auth_result = await auth_service.authenticate("testuser", "password")
            assert auth_result["user"]["username"] == "testuser"
            
            # Test permission checking
            has_permission = await permission_service.check_permission(
                "test-user-123", "users:read"
            )
            assert has_permission == True
            
            # Test guest session
            guest_session = await guest_service.get_or_create_guest_session()
            assert "session_token" in guest_session
        
        asyncio.run(test_service_operations())
        print("✅ Service wrapper integration validated")
    
    def test_permission_metadata_extraction(self):
        """Test permission decorator metadata extraction."""
        
        @require_permission("users:read", scope="platform")
        def test_function():
            pass
        
        @RequirePermission("tenants:write", scope="platform", is_dangerous=True)
        def dangerous_function():
            pass
        
        # Test metadata extraction
        metadata = PermissionMetadata.get_all_permissions(test_function)
        assert "users:read" in metadata
        
        # Test has_permissions check
        assert PermissionMetadata.has_permissions(test_function) == True
        assert PermissionMetadata.has_permissions(dangerous_function) == True
        
        # Test extract method
        dangerous_metadata = PermissionMetadata.extract(dangerous_function)
        assert len(dangerous_metadata) > 0
        assert dangerous_metadata[0]["is_dangerous"] == True
        
        print("✅ Permission metadata extraction validated")
    
    def test_dependency_injection_compatibility(self):
        """Test that dependencies can be instantiated with protocol implementations."""
        mock_token_validator = MockTokenValidator()
        mock_permission_checker = MockPermissionChecker()
        mock_guest_service = MockGuestAuthService()
        mock_cache_service = MockCacheService()
        mock_auth_config = MockAuthConfig()
        
        # Test CurrentUser dependency
        current_user = CurrentUser(mock_token_validator, mock_cache_service)
        assert current_user is not None
        
        # Test CheckPermission dependency
        check_permission = CheckPermission(
            mock_permission_checker, mock_token_validator, 
            ["users:read"], mock_cache_service
        )
        assert check_permission is not None
        
        # Test GuestOrAuthenticated dependency with all required parameters
        guest_auth = GuestOrAuthenticated(
            mock_guest_service, mock_permission_checker, 
            mock_token_validator, mock_auth_config
        )
        assert guest_auth is not None
        
        print("✅ Dependency injection compatibility validated")
    
    def test_global_registry_singleton(self):
        """Test global permission registry singleton pattern."""
        registry1 = get_permission_registry()
        registry2 = get_permission_registry()
        
        # Should be the same instance
        assert registry1 is registry2
        
        # Should have permissions loaded
        async def test_registry_loaded():
            permissions = await registry1.list_permission_codes()
            assert len(permissions) > 0
        
        asyncio.run(test_registry_loaded())
        print("✅ Global registry singleton validated")


def run_integration_tests():
    """Run all integration tests."""
    print("🧪 Starting Neo-Commons Auth Infrastructure Integration Tests\n")
    
    test_suite = TestAuthInfrastructureIntegration()
    
    try:
        test_suite.test_import_validation()
        test_suite.test_protocol_compliance()
        test_suite.test_permission_registry_functionality()
        test_suite.test_service_wrapper_integration()
        test_suite.test_permission_metadata_extraction()
        test_suite.test_dependency_injection_compatibility()
        test_suite.test_global_registry_singleton()
        
        print("\n🎉 All integration tests passed successfully!")
        print("✅ Neo-Commons auth infrastructure is ready for integration")
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)