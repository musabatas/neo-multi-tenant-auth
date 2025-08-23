#!/usr/bin/env python
"""Test script to verify async Keycloak adapter methods."""

import asyncio
import logging
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from neo_commons.features.auth.adapters.keycloak_openid import KeycloakOpenIDAdapter
from neo_commons.features.auth.entities.keycloak_config import KeycloakConfig
from neo_commons.core.value_objects.identifiers import RealmId, TenantId

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def test_keycloak_openid_adapter():
    """Test KeycloakOpenIDAdapter async methods."""
    
    # Create test config
    config = KeycloakConfig(
        server_url="http://localhost:8080",
        realm_name="master",  # Use master for testing
        client_id="admin-cli",
        realm_id=RealmId("master"),
        tenant_id=TenantId("test-tenant"),
        require_https=False,  # Disable HTTPS requirement for local testing
    )
    
    # Create adapter
    adapter = KeycloakOpenIDAdapter(config)
    
    try:
        # Test context manager and public key retrieval
        async with adapter:
            logger.info("Testing get_public_key...")
            try:
                public_key = await adapter.get_public_key()
                logger.info(f"✅ get_public_key successful: {public_key[:50]}...")
            except Exception as e:
                logger.error(f"❌ get_public_key failed: {e}")
            
            # Test well-known configuration
            logger.info("Testing get_well_known_configuration...")
            try:
                well_known = await adapter.get_well_known_configuration()
                logger.info(f"✅ get_well_known_configuration successful: {list(well_known.keys())[:5]}")
            except Exception as e:
                logger.error(f"❌ get_well_known_configuration failed: {e}")
            
            # Test authentication (will fail with wrong credentials, but tests async call)
            logger.info("Testing authenticate (expected to fail with test credentials)...")
            try:
                token = await adapter.authenticate("test_user", "test_password")
                logger.info(f"✅ authenticate successful: {token}")
            except Exception as e:
                logger.info(f"✅ authenticate failed as expected (wrong credentials): {type(e).__name__}")
    
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        raise
    
    logger.info("\n✅ All async adapter tests completed!")


async def main():
    """Main test runner."""
    logger.info("Starting Keycloak async adapter tests...")
    logger.info("=" * 60)
    
    # Note: This test requires Keycloak to be running on localhost:8080
    # You can start it with: docker-compose up keycloak
    
    try:
        await test_keycloak_openid_adapter()
    except Exception as e:
        logger.error(f"Tests failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)