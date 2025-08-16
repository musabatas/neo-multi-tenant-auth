## NeoAdminApi Auth Feature – Deep Review and Commons Consolidation Plan (Keycloak-only)

### Scope and premise
- **Service**: `NeoAdminApi`
- **Area**: `src/features/auth/**` and related common wiring
- **Commons**: `neo-commons/src/neo_commons/auth/**` and `neo_commons/repositories/**`
- **Auth Provider**: Keycloak only (confirmed)
- **Goal**: Minimize per-service code; centralize shared functionality in `neo-commons`; keep table schemas consistent across services with configurable schema/table names.

---

### High-level assessment
- **Good**
  - NeoAdminApi already routes most token work to `neo-commons` via `create_auth_service()` and protocol-driven dependencies.
  - Backward-compat wrappers from `neo-commons.auth.services.compatibility` are used correctly in `dependencies.py`.
  - Permission scanning/sync is nicely separated and nearly generic.
  - Repositories use `neo_commons.repositories.base.BaseRepository` with configurable schema – aligned with multi-service reuse.

- **Redundancies / Duplications**
  - Two `AuthConfig` implementations exist:
    - `src/features/auth/implementations/auth_config.py: NeoAdminAuthConfig`
    - `src/features/auth/services/auth_service.py: NeoAdminAuthConfig` (inner class)
    - Recommendation: keep only the implementations version; remove the inner class.
  - `CurrentUser`, `TokenData`, and permission extraction helpers in `src/features/auth/dependencies.py` largely duplicate `neo_commons.auth.dependencies.auth` capabilities. They wrap commons again instead of instantiating the provided factories directly.
  - Token validation + platform user mapping is implemented in `NeoAdminTokenValidator`. Some of this responsibility belongs to the permission layer (or a mapping service) rather than validation itself.
  - `GuestAuthService` exists in NeoAdminApi while `neo-commons` already provides the guest dependency surface. The service implementation is generic and can be moved.
  - Permission registry is static in service (`models/permission_registry.py`); highly reusable across services (with per-service add/override hooks).

- **Gaps / Opportunities**
  - Commons lacks a generic, shared `PermissionRepository` and `PermissionService` equivalent to NeoAdminApi’s implementation. These are prime targets to centralize: multi-level RBAC, wildcard support, caching, role resolution, and summary building.
  - A user-id mapping step (Keycloak user id → platform user id) is performed in several places (validator, permission checker, service). This should be a shared, pluggable strategy in commons to avoid re-implementations.
  - Wiring of dependencies could be simplified by using `neo-commons` factories directly and centralizing service-specific config.

---

### File-by-file notes (NeoAdminApi)
- `src/features/auth/dependencies.py`
  - Wraps commons dependencies (`NeoCurrentUser`, `NeoCheckPermission`, `NeoGuestOrAuthenticated`) but re-exports local wrappers again. Consider direct wiring using `neo-commons` factories: `create_current_user`, `create_permission_checker`, `create_guest_or_authenticated`.
  - Duplicated helpers `get_user_permissions` and `get_user_roles` exist in commons. Prefer importing commons helpers or a single, local thin adapter that injects `auth_config` to determine client id.

- `src/features/auth/implementations/auth_config.py`
  - Clean, protocol-compliant. Keep this single source of truth for service auth config.
  - Note: `default_validation_strategy` converts string→enum via `ValidationStrategy(strategy_str.lower())`. Ensure enum accepts lower-case names. Else, normalize to upper-case.

- `src/features/auth/implementations/token_validator.py`
  - Delegates to `neo-commons` token validator via `create_auth_service()`; then maps `sub` (Keycloak) to platform user id using `AuthRepository`.
  - Suggestion: move the user-id mapping concern into a commons “user identity resolver” protocol so all services can share the behavior.

- `src/features/auth/implementations/permission_checker.py`
  - Uses `PermissionService` and repository to check permissions; contains user-id mapping (duplicate concern). Should rely on a shared identity resolver or a repository method exposed by commons.

- `src/features/auth/implementations/cache_service.py`
  - Generic Redis wrapper with namespacing – reusable. Consider moving to commons under `auth/providers` or `cache/` with protocol alignment.

- `src/features/auth/services/auth_service.py`
  - Thin orchestration layer around `neo-commons` authentication; handles session cache and user sync to DB.
  - Has a local duplicate `NeoAdminAuthConfig`. Remove in favor of `implementations/auth_config.py` to avoid drift.
  - Good use of `user_sync_callback`; this hook is a strong pattern for all services.

- `src/features/auth/services/permission_service.py` and `repositories/permission_repository.py`
  - Robust multi-level RBAC with caching and wildcard support. This design should be generalized and lifted into `neo-commons` so other services can reuse it by providing `connection_provider` and `schema`.
  - Some authorization checks (superadmin bypass, tenant access) are embedded here. Make them togglable via config flags in commons.

- `src/features/auth/services/guest_auth_service.py` and `implementations/guest_auth_service.py`
  - Service is generic; adapter wraps it into the commons protocol. Move core service to commons; keep only service-specific wiring as needed.

- `src/features/auth/services/permission_scanner.py` and `permission_manager.py`
  - Already generic and protocol-friendly. These can live in commons to avoid duplication across services.

- `src/features/auth/models/permission_registry.py`
  - Static registry suitable for commons. Support per-service extension via registry provider (DI) rather than inlining.

- `src/features/auth/routers/*`
  - Endpoints rely on the above services and decorators. Safe once services and dependencies are centralized.

- `src/features/auth/repositories/auth_repository.py`
  - Generic platform user lookups and sync. Strong candidate to move to `neo-commons` with schema + connection provider injected.

---

### Relevant `neo-commons` capabilities already present
- Protocols: `TokenValidatorProtocol`, `PermissionCheckerProtocol`, `AuthConfigProtocol`, `GuestAuthServiceProtocol`.
- Factories: `auth/dependencies/auth.py` and `auth/dependencies/guest.py` provide `create_*` helpers for dependencies.
- Backward-compat wrappers: `AuthServiceWrapper`, `PermissionServiceWrapper`, `GuestAuthServiceWrapper`.
- Keycloak-specific implementations and token validation are already centralized.

Gaps to fill in `neo-commons`:
- A generalized `PermissionRepository` and `PermissionService` (multi-level RBAC + caching) with:
  - Configurable schema and connection provider
  - Wildcard permissions and role hierarchy
  - Platform vs tenant scoping
  - Summaries and cache warming/invalidation
- A `UserIdentityResolver` protocol for mapping external auth IDs (Keycloak `sub`) to platform user IDs using a provided repository – avoids re-implementations across services.
- A shared `GuestAuthService` implementation (the NeoAdminApi one is suitable to move) plus a thin per-service adapter (if needed).
- Centralized `PermissionRegistryProvider` and `PermissionSyncManager` (your implementations are nearly drop-in).

---

### Consolidation plan (incremental, low-risk)
1) Remove local duplicates and wire directly to commons
   - Keep `src/features/auth/implementations/auth_config.py` as the sole `AuthConfig`.
   - In `src/features/auth/services/auth_service.py`, import and reuse that config; delete the inner class.
   - In `src/features/auth/dependencies.py`, replace custom wrapper classes by instantiating `neo-commons` dependencies via `create_current_user`, `create_permission_checker`, `create_token_data`, `create_guest_or_authenticated`. Keep only tiny glue functions to pass service-specific implementations.

2) Extract generic components into `neo-commons`
   - Move `PermissionRepository` and `PermissionService` into `neo-commons` under `auth/permissions/` with DI for `connection_provider` and `default_schema`. Provide the same public methods so NeoAdminApi becomes an adapter only.
   - Move `GuestAuthService` core to `neo-commons` under `auth/services/guest.py` and keep only the per-service wiring (if any) in NeoAdminApi.
   - Move `PermissionSyncManager` and `EndpointPermissionScanner` to `neo-commons` under `auth/registry/` or `auth/tools/`, with a `PermissionRegistryProvider` interface. NeoAdminApi can register extra permissions via provider.
   - Move `permission_registry.py` seeds to `neo-commons` and expose an extension hook to append/override per service.

3) Add a shared identity mapping protocol
   - Define `UserIdentityResolverProtocol` in `neo-commons/auth/protocols.py` with `resolve_platform_user_id(external_provider, external_user_id) -> str | None`.
   - Provide a default adapter that uses a supplied repository (DI) implementing `get_user_by_external_id`.
   - Use this resolver in token validation and permission checking paths to unify mapping and ensure consistent caching keys.

4) Schema/table reuse strategy across services
   - Keep column names identical across services. Allow per-service schema and optional table name overrides via repository constructor params.
   - Expose a `RepositoryConfig` in `neo-commons` that receives `{ default_schema, table_overrides: { logical_table_name: actual_table_name } }`.
   - This lets services point to the same logical model while allowing different schema names or table name prefixes.

5) Configuration unification
   - Ensure all TTLs and switches (token cache, permission cache, rate limiting, MFA) are read from `AuthConfigProtocol` / `get_feature_flags()` style methods in a single place (`implementations/auth_config.py`). Commons should consume these instead of literals.

6) API surface for new services (minimal code recipe)
   - Implement only:
     - `AuthConfigProtocol` adapter that reads that service’s settings
     - `connection_provider` and (optionally) `schema_provider`
   - Then wire commons:
     - `token_validator = neo_commons.auth.implementations.token_validator.TokenValidator(...)` or reuse factory
     - `permission_checker = commons PermissionService` (from step 2)
     - `guest_service = commons GuestAuthService` (from step 2)
     - Dependencies via `create_current_user(...)`, `create_permission_checker(...)`, `create_guest_or_authenticated(...)`
   - Optional: register extra permissions via `PermissionRegistryProvider`.

---

### Concrete refactor suggestions
- **Delete duplication**
  - Remove `NeoAdminAuthConfig` class defined inside `src/features/auth/services/auth_service.py`.
  - In `dependencies.py`, delete local `CurrentUser`, `TokenData`, `GuestOrAuthenticated` and instead construct the commons classes with the local implementations passed in. Keep the exported callables (`get_current_user`, `get_current_user_optional`, etc.) for route imports.

- **Move to commons**
  - Move `PermissionRepository`, `PermissionService` to `neo-commons` with same API.
  - Move `GuestAuthService` core to `neo-commons`; keep `NeoAdminGuestAuthService` minimal or eliminate if the core already implements the protocol.
  - Move `PermissionSyncManager` and `EndpointPermissionScanner` to `neo-commons`; expose provider-based registries.
  - Move `permission_registry.py` base content to `neo-commons` registry; allow per-service provider to extend.

- **Add to commons**
  - Introduce `UserIdentityResolverProtocol` and default resolver using a repository adapter.
  - Introduce optional `RepositoryConfig` for schema/table overrides.

- **Wiring changes**
  - Create a single `get_auth_config()` provider in NeoAdminApi and inject it everywhere (validator, permission checker, guest service) instead of scattering `settings` access.
  - Route all dependency construction through commons factories in one module (`features/auth/dependencies.py`) for clarity.

---

### Risks and mitigations
- Moving repositories/services to commons can break imports.
  - Mitigation: keep compatibility shims for one release (`from neo_commons... import ... as OldName`).
- Identity resolution changes could affect permission checks if platform user mapping is inconsistent.
  - Mitigation: centralize resolver and add unit tests for mapping paths; log mismatches.
- Permission registry consolidation could diverge from live DB.
  - Mitigation: rely on `PermissionSyncManager` with `dry_run` and reports; run in CI.

---

### Test plan
- Unit tests for:
  - Token validation with local/dual strategies and identity mapping.
  - Permission checks (platform/tenant, any/all, wildcard) hitting the consolidated commons services.
  - Guest flow (create/validate/extend) using commons implementation.
  - Permission sync scan + DB upsert (dry_run and apply) using a test DB schema.

---

### Summary of impact
- NeoAdminApi auth code size will decrease substantially.
- New services can integrate auth by implementing only config + connection provider and reusing commons services and dependencies.
- Shared DB schema is preserved via configurable schema/table names; column names remain consistent.
- Reduced duplication around identity mapping, permission logic, and guest sessions improves reliability and maintainability.


