"""
Backward Compatibility Tests

Tests ensuring extracted neo-commons auth components maintain backward compatibility
with existing NeoAdminApi patterns and APIs.
"""

import asyncio
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock

from neo_commons.auth.services.compatibility import (
    AuthServiceWrapper,
    PermissionServiceWrapper, 
    GuestAuthServiceWrapper
)
from neo_commons.auth.protocols import (
    TokenValidatorProtocol,
    PermissionCheckerProtocol,
    GuestAuthServiceProtocol,
    CacheServiceProtocol,
    AuthConfigProtocol,
    ValidationStrategy
)


class TestBackwardCompatibility:
    """Test backward compatibility with existing NeoAdminApi patterns."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_token_validator = AsyncMock(spec=TokenValidatorProtocol)
        self.mock_permission_checker = AsyncMock(spec=PermissionCheckerProtocol)
        self.mock_guest_service = AsyncMock(spec=GuestAuthServiceProtocol)
        self.mock_cache_service = AsyncMock(spec=CacheServiceProtocol)
        self.mock_auth_config = MagicMock(spec=AuthConfigProtocol)
        
        # Configure mock config
        self.mock_auth_config.default_realm = "master"
        self.mock_auth_config.default_validation_strategy = ValidationStrategy.DUAL
        
        # Configure mock responses
        self.mock_token_validator.authenticate_user.return_value = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "email": "test@example.com",
            "given_name": "Test",
            "family_name": "User",
            "name": "Test User",
            "access_token": "mock-token",
            "refresh_token": "mock-refresh",
            "expires_in": 3600
        }
        
        self.mock_token_validator.validate_token.return_value = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "email": "test@example.com",
            "iat": 1640995200,
            "exp": 1641081600
        }
        
        self.mock_permission_checker.check_permission.return_value = True
        self.mock_permission_checker.get_user_permissions.return_value = [
            {"code": "users:read", "scope": "platform"}
        ]
        
        self.mock_guest_service.get_or_create_guest_session.return_value = {
            "session_token": "guest-123",
            "guest_id": "guest-456"
        }
        
        self.mock_cache_service.get.return_value = None
        self.mock_cache_service.set.return_value = None
        self.mock_cache_service.delete.return_value = None
    
    def test_auth_service_wrapper_api_compatibility(self):
        """Test AuthServiceWrapper maintains existing API."""
        auth_service = AuthServiceWrapper(
            self.mock_token_validator,
            self.mock_permission_checker,
            self.mock_auth_config,
            self.mock_cache_service
        )
        
        async def test_authenticate_api():
            # Test original authenticate method signature
            result = await auth_service.authenticate("testuser", "password")
            
            assert "user" in result
            assert "session_id" in result
            assert "access_token" in result
            assert result["user"]["username"] == "testuser"
            
            # Verify token validator was called correctly
            self.mock_token_validator.authenticate_user.assert_called_once_with(
                username="testuser",
                password="password", 
                realm="master"
            )
        
        async def test_get_current_user_api():
            # Test original get_current_user method signature
            user = await auth_service.get_current_user("mock-token")
            
            assert user is not None
            assert user["id"] == "user-123"
            assert user["username"] == "testuser"
            
            # Verify token validator was called correctly
            self.mock_token_validator.validate_token.assert_called_once_with(
                token="mock-token",
                realm="master", 
                strategy=ValidationStrategy.DUAL,
                critical=False
            )
        
        async def test_logout_api():
            # Test original logout method signature
            result = await auth_service.logout("session-123")
            
            assert result == True
            
            # Verify cache was called
            self.mock_cache_service.delete.assert_called_once()
        
        # Run all async tests
        asyncio.run(test_authenticate_api())
        asyncio.run(test_get_current_user_api())
        asyncio.run(test_logout_api())
        
        print("✅ AuthServiceWrapper API compatibility validated")
    
    def test_permission_service_wrapper_api_compatibility(self):
        """Test PermissionServiceWrapper maintains existing API."""
        permission_service = PermissionServiceWrapper(
            self.mock_permission_checker,
            self.mock_cache_service
        )
        
        async def test_check_permission_api():
            # Test original check_permission method signature
            has_permission = await permission_service.check_permission(
                "user-123", "users:read", scope="platform"
            )
            
            assert has_permission == True
            
            # Verify permission checker was called correctly
            self.mock_permission_checker.check_permission.assert_called_once_with(
                user_id="user-123",
                permissions=["users:read"],
                scope="platform",
                tenant_id=None,
                any_of=False
            )
        
        async def test_check_permission_with_list():
            # Test with list of permissions
            has_permission = await permission_service.check_permission(
                "user-123", ["users:read", "users:write"], any_of=True
            )
            
            assert has_permission == True
            
            # Verify permission checker was called with list
            self.mock_permission_checker.check_permission.assert_called_with(
                user_id="user-123",
                permissions=["users:read", "users:write"],
                scope="platform",
                tenant_id=None,
                any_of=True
            )
        
        async def test_get_user_permissions_api():
            # Test original get_user_permissions method signature
            permissions = await permission_service.get_user_permissions("user-123")
            
            assert len(permissions) == 1
            assert permissions[0]["code"] == "users:read"
            
            # Verify permission checker was called correctly
            self.mock_permission_checker.get_user_permissions.assert_called_once_with(
                user_id="user-123",
                tenant_id=None
            )
        
        # Run all async tests
        asyncio.run(test_check_permission_api())
        asyncio.run(test_check_permission_with_list())
        asyncio.run(test_get_user_permissions_api())
        
        print("✅ PermissionServiceWrapper API compatibility validated")
    
    def test_guest_auth_service_wrapper_api_compatibility(self):
        """Test GuestAuthServiceWrapper maintains existing API."""
        guest_service = GuestAuthServiceWrapper(
            self.mock_guest_service,
            self.mock_cache_service
        )
        
        async def test_get_or_create_guest_session_api():
            # Test original get_or_create_guest_session method signature
            session = await guest_service.get_or_create_guest_session(
                ip_address="127.0.0.1",
                user_agent="test-agent"
            )
            
            assert session["session_token"] == "guest-123"
            assert session["guest_id"] == "guest-456"
            
            # Verify guest service was called correctly
            self.mock_guest_service.get_or_create_guest_session.assert_called_once_with(
                session_token=None,
                ip_address="127.0.0.1",
                user_agent="test-agent", 
                referrer=None
            )
        
        async def test_get_session_stats_api():
            # Mock session stats response
            self.mock_guest_service.get_session_stats.return_value = {
                "session_token": "guest-123",
                "request_count": 5
            }
            
            # Test original get_session_stats method signature
            stats = await guest_service.get_session_stats("guest-123")
            
            assert stats["session_token"] == "guest-123"
            assert stats["request_count"] == 5
            
            # Verify guest service was called correctly
            self.mock_guest_service.get_session_stats.assert_called_once_with("guest-123")
        
        # Run all async tests
        asyncio.run(test_get_or_create_guest_session_api())
        asyncio.run(test_get_session_stats_api())
        
        print("✅ GuestAuthServiceWrapper API compatibility validated")
    
    def test_protocol_injection_pattern(self):
        """Test that service wrappers accept protocol implementations correctly."""
        # This tests the core pattern of protocol-based dependency injection
        
        # Create service wrappers with protocol implementations
        auth_service = AuthServiceWrapper(
            self.mock_token_validator,  # TokenValidatorProtocol
            self.mock_permission_checker,  # PermissionCheckerProtocol
            self.mock_auth_config,  # AuthConfigProtocol
            self.mock_cache_service  # CacheServiceProtocol
        )
        
        permission_service = PermissionServiceWrapper(
            self.mock_permission_checker,  # PermissionCheckerProtocol
            self.mock_cache_service  # CacheServiceProtocol
        )
        
        guest_service = GuestAuthServiceWrapper(
            self.mock_guest_service,  # GuestAuthServiceProtocol
            self.mock_cache_service  # CacheServiceProtocol
        )
        
        # Verify services were created successfully
        assert auth_service is not None
        assert permission_service is not None
        assert guest_service is not None
        
        # Verify protocol implementations are stored correctly
        assert auth_service.token_validator is self.mock_token_validator
        assert auth_service.permission_checker is self.mock_permission_checker
        assert auth_service.auth_config is self.mock_auth_config
        assert auth_service.cache is self.mock_cache_service
        
        assert permission_service.permission_checker is self.mock_permission_checker
        assert permission_service.cache is self.mock_cache_service
        
        assert guest_service.guest_service is self.mock_guest_service
        assert guest_service.cache is self.mock_cache_service
        
        print("✅ Protocol injection pattern validated")
    
    def test_caching_integration(self):
        """Test that service wrappers integrate correctly with caching."""
        auth_service = AuthServiceWrapper(
            self.mock_token_validator,
            self.mock_permission_checker,
            self.mock_auth_config,
            self.mock_cache_service
        )
        
        async def test_cache_usage():
            # Test that authentication creates cache entries
            await auth_service.authenticate("testuser", "password")
            
            # Verify cache.set was called for session storage
            assert self.mock_cache_service.set.call_count >= 1
            
            # Test that get_current_user uses cache
            await auth_service.get_current_user("mock-token", use_cache=True)
            
            # Verify cache.get and cache.set were called
            assert self.mock_cache_service.get.call_count >= 1
            assert self.mock_cache_service.set.call_count >= 2  # Session + user cache
        
        asyncio.run(test_cache_usage())
        print("✅ Caching integration validated")


def run_backward_compatibility_tests():
    """Run all backward compatibility tests."""
    print("🔄 Starting Backward Compatibility Tests\n")
    
    test_suite = TestBackwardCompatibility()
    
    try:
        test_suite.setup_method()
        test_suite.test_auth_service_wrapper_api_compatibility()
        test_suite.test_permission_service_wrapper_api_compatibility()
        test_suite.test_guest_auth_service_wrapper_api_compatibility()
        test_suite.test_protocol_injection_pattern()
        test_suite.test_caching_integration()
        
        print("\n🎉 All backward compatibility tests passed!")
        print("✅ Neo-Commons auth wrappers maintain full API compatibility")
        return True
        
    except Exception as e:
        print(f"\n❌ Backward compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_backward_compatibility_tests()
    exit(0 if success else 1)