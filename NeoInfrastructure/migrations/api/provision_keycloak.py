#!/usr/bin/env python3
"""
Provision Keycloak realms/clients for tenants using the built-in provisioner.

Usage:
  python provision_keycloak.py                 # provision all missing tenants
  python provision_keycloak.py --tenant TENANT_ID  # provision specific tenant
  python provision_keycloak.py --admin-realm       # ensure platform-admin realm exists
"""

from __future__ import annotations

import os
import sys
import asyncio
import argparse
import asyncpg
from typing import Optional

sys.path.append("/app/api")
from keycloak_provisioner import build_default_provisioner_from_env  # type: ignore


async def init_db_pool() -> asyncpg.Pool:
    pool = await asyncpg.create_pool(
        host=os.getenv('POSTGRES_US_HOST', 'neo-postgres-us-east'),
        port=int(os.getenv('POSTGRES_US_PORT', '5432')),
        database='neofast_admin',
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', 'postgres'),
        min_size=1,
        max_size=5,
    )
    return pool


async def provision_all_missing() -> None:
    kc = build_default_provisioner_from_env()
    pool = await init_db_pool()
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, slug
                FROM admin.tenants
                WHERE external_auth_provider = 'keycloak'
                  AND (
                        external_auth_realm IS NULL OR external_auth_realm = ''
                        OR (external_auth_metadata ->> 'client_secret') IS NULL
                      )
                """
            )
            for row in rows:
                tenant_id = row['id']
                slug = row['slug']
                realm = f"tenant-{slug}"
                ensured_realm, client_id, client_secret = await kc.ensure_realm_and_client(realm)
                await conn.execute(
                    """
                    UPDATE admin.tenants
                    SET external_auth_realm = $2,
                        external_auth_metadata = COALESCE(external_auth_metadata, '{}'::jsonb)
                            || jsonb_build_object(
                                'realm', $2,
                                'client_id', $3,
                                'client_secret', $4
                               ),
                        updated_at = NOW()
                    WHERE id = $1
                    """,
                    tenant_id,
                    ensured_realm,
                    client_id,
                    client_secret,
                )
                print(f"Provisioned tenant {slug}: realm={ensured_realm}, client_id={client_id}")
    finally:
        await pool.close()


async def provision_tenant(tenant_id: str) -> None:
    kc = build_default_provisioner_from_env()
    pool = await init_db_pool()
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, slug FROM admin.tenants
                WHERE id = $1 AND external_auth_provider = 'keycloak'
                """,
                tenant_id,
            )
            if row is None:
                print("Tenant not found or not using Keycloak", file=sys.stderr)
                return
            slug = row['slug']
            realm = f"tenant-{slug}"
            ensured_realm, client_id, client_secret = await kc.ensure_realm_and_client(realm)
            await conn.execute(
                """
                UPDATE admin.tenants
                SET external_auth_realm = $2,
                    external_auth_metadata = COALESCE(external_auth_metadata, '{}'::jsonb)
                        || jsonb_build_object(
                            'realm', $2,
                            'client_id', $3,
                            'client_secret', $4
                           ),
                    updated_at = NOW()
                WHERE id = $1
                """,
                tenant_id,
                ensured_realm,
                client_id,
                client_secret,
            )
            print(f"Provisioned tenant {slug}: realm={ensured_realm}, client_id={client_id}")
    finally:
        await pool.close()


async def ensure_admin_realm(realm_name: str = "platform-admin", client_id: str = "neo-admin-api") -> None:
    kc = build_default_provisioner_from_env()
    ensured_realm, ensured_client_id, client_secret = await kc.ensure_realm_and_client(realm_name, client_id)
    # Print to stdout so operator can copy to service env vars
    print({
        "realm": ensured_realm,
        "client_id": ensured_client_id,
        "client_secret": client_secret,
    })


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision Keycloak realms/clients")
    parser.add_argument("--tenant", type=str, help="Tenant UUID to provision")
    parser.add_argument("--admin-realm", action="store_true", help="Ensure admin realm exists")
    args = parser.parse_args()

    if args.admin_realm:
        asyncio.run(ensure_admin_realm())
        return

    if args.tenant:
        asyncio.run(provision_tenant(args.tenant))
        return

    asyncio.run(provision_all_missing())


if __name__ == "__main__":
    main()


