# NeoMultiTenant Project Overview

## Purpose
Enterprise-grade multi-tenant platform built with Python FastAPI, PostgreSQL 17+, Redis, and Keycloak. Features ultra-scalability, comprehensive RBAC with custom permissions, and sub-millisecond permission checks.

## Architecture Components
- **NeoInfrastructure**: Database migrations, Docker infrastructure, multi-region PostgreSQL setup
- **neo-commons**: Shared library with authentication, caching, database operations, and utilities
- **NeoAdminApi**: Platform administration API (Port 8001)
- **NeoTenantApi**: Tenant-specific API (Port 8002)
- **Frontend Services**: React/Next.js applications on ports 3000-3003

## Key Principles
1. Always use neo-commons first - check shared library before creating new functionality
2. Protocol-based dependency injection with @runtime_checkable interfaces
3. Follow Feature-First + Clean Core architecture
4. Use asyncpg for database operations, never ORMs for performance paths
5. Configure schemas dynamically - never hardcode database schema names
6. Use UUIDv7 for all UUID generation
7. Cache aggressively with Redis and proper invalidation

## Technology Stack
- API: Python 3.13+ with FastAPI (async)
- Database: PostgreSQL 17+ with asyncpg
- Caching: Redis with automatic invalidation
- Authentication: Keycloak (external IAM)
- RBAC: Custom PostgreSQL-based with intelligent caching