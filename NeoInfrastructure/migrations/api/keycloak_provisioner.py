"""
Keycloak Provisioner

Creates realms and clients in Keycloak and writes credentials to admin.tenants.

Notes:
- Uses Keycloak Admin REST API with admin username/password
- Designed for dev infra where SSL is disabled and hostname is http
- Stores client credentials under tenants.external_auth_metadata JSONB
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import os
import asyncio
import requests


DEFAULT_CLIENT_ID = "NeoTenantApi"


@dataclass
class KeycloakProvisioner:
    server_url: str
    admin_username: str
    admin_password: str

    async def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        # Run blocking requests in thread to avoid blocking event loop
        def _do_request():
            return requests.request(method, url, timeout=10, **kwargs)

        return await asyncio.to_thread(_do_request)

    async def _get_admin_token(self) -> str:
        token_url = f"{self.server_url}/realms/master/protocol/openid-connect/token"
        data = {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": self.admin_username,
            "password": self.admin_password,
        }
        resp = await self._request("POST", token_url, data=data)
        resp.raise_for_status()
        body = resp.json()
        return body["access_token"]

    async def _realm_exists(self, token: str, realm: str) -> bool:
        url = f"{self.server_url}/admin/realms/{realm}"
        resp = await self._request("GET", url, headers={"Authorization": f"Bearer {token}"})
        if resp.status_code == 200:
            return True
        if resp.status_code == 404:
            return False
        resp.raise_for_status()
        return False

    async def _create_realm(self, token: str, realm: str) -> None:
        url = f"{self.server_url}/admin/realms"
        payload = {
            "realm": realm,
            "enabled": True,
            # Dev environment: SSL off; production should be EXTERNAL
            "sslRequired": "NONE",
            "registrationAllowed": False,
            "loginWithEmailAllowed": True,
        }
        resp = await self._request("POST", url, json=payload, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        # 201 Created or 409 if already exists (race)
        if resp.status_code in (201, 204):
            return
        if resp.status_code == 409:
            return
        resp.raise_for_status()

    async def _find_client(self, token: str, realm: str, client_id: str) -> Optional[Dict[str, Any]]:
        url = f"{self.server_url}/admin/realms/{realm}/clients"
        resp = await self._request("GET", url, params={"clientId": client_id}, headers={"Authorization": f"Bearer {token}"})
        resp.raise_for_status()
        items = resp.json() or []
        return items[0] if items else None

    async def _create_client(self, token: str, realm: str, client_id: str) -> str:
        url = f"{self.server_url}/admin/realms/{realm}/clients"
        payload = {
            "clientId": client_id,
            "enabled": True,
            "protocol": "openid-connect",
            "publicClient": False,
            "directAccessGrantsEnabled": True,
            "serviceAccountsEnabled": False,
            "standardFlowEnabled": True,
            "redirectUris": ["*"],
            "webOrigins": ["*"],
        }
        resp = await self._request("POST", url, json=payload, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        if resp.status_code not in (201, 204):
            resp.raise_for_status()

        # Fetch created client to get its UUID id
        found = await self._find_client(token, realm, client_id)
        if not found:
            raise RuntimeError("Client created but not found when querying back")
        return found["id"]

    async def _get_client_secret(self, token: str, realm: str, client_uuid: str) -> str:
        url = f"{self.server_url}/admin/realms/{realm}/clients/{client_uuid}/client-secret"
        resp = await self._request("GET", url, headers={"Authorization": f"Bearer {token}"})
        resp.raise_for_status()
        data = resp.json()
        # Keycloak returns {"type":"secret","value":"..."}
        return data.get("value") or data.get("secret") or ""

    async def ensure_realm_and_client(self, realm: str, client_id: str = DEFAULT_CLIENT_ID) -> Tuple[str, str, str]:
        """
        Ensure realm and client exist. Returns (realm_name, client_id, client_secret)
        """
        token = await self._get_admin_token()

        # Realm
        exists = await self._realm_exists(token, realm)
        if not exists:
            await self._create_realm(token, realm)

        # Client
        client = await self._find_client(token, realm, client_id)
        if client is None:
            client_uuid = await self._create_client(token, realm, client_id)
        else:
            client_uuid = client["id"]

        secret = await self._get_client_secret(token, realm, client_uuid)
        if not secret:
            # Secret might not exist until regenerated; attempt rotation via POST
            # Some Keycloak versions use POST to /client-secret to regenerate
            regen = await self._request("POST", f"{self.server_url}/admin/realms/{realm}/clients/{client_uuid}/client-secret", headers={"Authorization": f"Bearer {token}"})
            if regen.status_code not in (200, 201, 204):
                regen.raise_for_status()
            secret = await self._get_client_secret(token, realm, client_uuid)

        return realm, client_id, secret


def build_default_provisioner_from_env() -> KeycloakProvisioner:
    server_url = os.getenv("KEYCLOAK_URL", "http://neo-keycloak:8080")
    username = os.getenv("KEYCLOAK_ADMIN", os.getenv("KC_BOOTSTRAP_ADMIN_USERNAME", "admin"))
    password = os.getenv("KEYCLOAK_PASSWORD", os.getenv("KC_BOOTSTRAP_ADMIN_PASSWORD", "admin"))
    return KeycloakProvisioner(server_url=server_url.rstrip("/"), admin_username=username, admin_password=password)


