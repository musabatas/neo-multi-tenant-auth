"""
Auth Infrastructure Protocol Interfaces

DEPRECATED: This file has been split into multiple modules for better organization.
New imports should use the protocols subdirectory:

- auth.protocols.base: Core enums and configuration
- auth.protocols.keycloak: Keycloak integration
- auth.protocols.permissions: Permission management  
- auth.protocols.services: Service operations

This file maintains backward compatibility by re-exporting all protocols.
"""

# Re-export all protocols for backward compatibility
from .protocols.base import (
    ValidationStrategy,
    PermissionScope,
    AuthConfigProtocol,
    CacheKeyProviderProtocol,
)

from .protocols.keycloak import (
    RealmProviderProtocol,
    RealmManagerProtocol,
    KeycloakClientProtocol,
    TokenValidatorProtocol,
)

from .protocols.permissions import (
    PermissionValidatorProtocol,
    PermissionRegistryProtocol,
    PermissionDecoratorProtocol,
    PermissionCheckerProtocol,
    PermissionCacheProtocol,
    PermissionDataSourceProtocol,
    WildcardMatcherProtocol,
)

from .protocols.services import (
    GuestAuthServiceProtocol,
    CacheServiceProtocol,
    UserIdentityResolverProtocol,
)

# Legacy imports for backward compatibility
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable, Tuple, Union, Set
from enum import Enum
from datetime import datetime

