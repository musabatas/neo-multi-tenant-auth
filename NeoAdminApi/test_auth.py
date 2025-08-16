#!/usr/bin/env python3
"""
Test authentication directly using the same configuration as the API.
"""
import asyncio
import sys
import os
sys.path.insert(0, '/Users/musabatas/Workspaces/NeoMultiTenant/neo-commons/src')

import httpx
from loguru import logger

async def test_keycloak_auth():
    """Test Keycloak authentication directly."""
    
    # Read configuration from environment (same as SimpleAuthConfig)
    keycloak_url = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
    realm = os.getenv("KEYCLOAK_ADMIN_REALM", "platform-admin")
    client_id = os.getenv("KEYCLOAK_ADMIN_CLIENT_ID", "neo-admin-api")
    client_secret = os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET", "7TmupPIzq61a8WkwoYhny8kJoUpyDtoa")
    
    print(f"Testing authentication with:")
    print(f"  URL: {keycloak_url}")
    print(f"  Realm: {realm}")
    print(f"  Client ID: {client_id}")
    print(f"  Client Secret: {client_secret[:8]}...{client_secret[-4:]}")
    
    token_endpoint = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token"
    print(f"  Token Endpoint: {token_endpoint}")
    
    request_data = {
        "grant_type": "password",
        "client_id": client_id,
        "client_secret": client_secret,
        "username": "test",
        "password": "12345678",
    }
    
    print(f"\nSending request...")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_endpoint,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=request_data
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            print("✅ Authentication successful!")
            print(f"Access token: {token_data.get('access_token', '')[:50]}...")
            print(f"Token type: {token_data.get('token_type')}")
            print(f"Expires in: {token_data.get('expires_in')} seconds")
        else:
            print("❌ Authentication failed!")
            print(f"Response: {response.text}")

if __name__ == "__main__":
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(test_keycloak_auth())