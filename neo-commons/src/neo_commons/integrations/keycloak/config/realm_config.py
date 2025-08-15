"""
Realm configuration and default implementations.

Provides default realm configuration with environment variable support.
"""
import os
from typing import Dict, Any, List
from ..protocols.realm_protocols import RealmConfigProtocol


class DefaultRealmConfig(RealmConfigProtocol):
    """Default realm configuration with environment variable support."""
    
    def __init__(self):
        self._realm_cache_ttl = None
        self._password_policy = None
        self._default_locales = None
        self._brute_force_settings = None
    
    @property
    def realm_cache_ttl(self) -> int:
        """Cache TTL for realm data (1 hour default)."""
        if self._realm_cache_ttl is None:
            self._realm_cache_ttl = int(os.getenv(
                'REALM_CACHE_TTL', 
                os.getenv('KEYCLOAK_REALM_CACHE_TTL', '3600')
            ))
        return self._realm_cache_ttl
    
    @property
    def password_policy(self) -> str:
        """Default password policy."""
        if self._password_policy is None:
            self._password_policy = os.getenv(
                'REALM_PASSWORD_POLICY',
                os.getenv(
                    'KEYCLOAK_PASSWORD_POLICY',
                    "length(12) and upperCase(2) and lowerCase(2) and digits(2) and specialChars(2)"
                )
            )
        return self._password_policy
    
    @property
    def default_locales(self) -> List[str]:
        """Default supported locales."""
        if self._default_locales is None:
            locales_str = os.getenv(
                'REALM_DEFAULT_LOCALES',
                os.getenv('KEYCLOAK_DEFAULT_LOCALES', 'en')
            )
            self._default_locales = [locale.strip() for locale in locales_str.split(',')]
        return self._default_locales
    
    @property
    def brute_force_protection(self) -> Dict[str, Any]:
        """Brute force protection settings."""
        if self._brute_force_settings is None:
            self._brute_force_settings = {
                "bruteForceProtected": os.getenv('REALM_BRUTE_FORCE_ENABLED', 'true').lower() == 'true',
                "permanentLockout": os.getenv('REALM_PERMANENT_LOCKOUT', 'false').lower() == 'true',
                "maxFailureWaitSeconds": int(os.getenv('REALM_MAX_FAILURE_WAIT', '900')),
                "minimumQuickLoginWaitSeconds": int(os.getenv('REALM_MIN_QUICK_LOGIN_WAIT', '60')),
                "waitIncrementSeconds": int(os.getenv('REALM_WAIT_INCREMENT', '60')),
                "quickLoginCheckMilliSeconds": int(os.getenv('REALM_QUICK_LOGIN_CHECK', '1000')),
                "maxDeltaTimeSeconds": int(os.getenv('REALM_MAX_DELTA_TIME', '43200')),
                "failureFactor": int(os.getenv('REALM_FAILURE_FACTOR', '5'))
            }
        return self._brute_force_settings