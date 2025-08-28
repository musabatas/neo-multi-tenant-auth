-- Migration: Create assignment tables for users to roles and permissions
-- Description: Links users to roles and allows direct permission assignments

-- 1. Create auth_user_roles table
CREATE TABLE auth_user_roles (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role_id BIGINT NOT NULL REFERENCES auth_roles(id) ON DELETE RESTRICT,
    granted_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    granted_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    revoked_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Create unique index for active roles
CREATE UNIQUE INDEX idx_auth_user_roles_unique_active 
    ON auth_user_roles(user_id, role_id) 
    WHERE revoked_at IS NULL;

-- Create other indexes
CREATE INDEX idx_auth_user_roles_user_id ON auth_user_roles(user_id);
CREATE INDEX idx_auth_user_roles_role_id ON auth_user_roles(role_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_auth_user_roles_expires_at ON auth_user_roles(expires_at) 
    WHERE expires_at IS NOT NULL AND revoked_at IS NULL;

-- Add constraints
ALTER TABLE auth_user_roles ADD CONSTRAINT auth_user_roles_valid_dates
    CHECK (
        (expires_at IS NULL OR expires_at > granted_at) AND
        (revoked_at IS NULL OR revoked_at >= granted_at)
    );

-- Add triggers
CREATE TRIGGER update_auth_user_roles_updated_at 
    BEFORE UPDATE ON auth_user_roles
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Enable RLS
ALTER TABLE auth_user_roles ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own roles" ON auth_user_roles
    FOR SELECT USING (auth.uid() = user_id);

-- 2. Create auth_role_permissions table
CREATE TABLE auth_role_permissions (
    id BIGSERIAL PRIMARY KEY,
    role_id BIGINT NOT NULL REFERENCES auth_roles(id) ON DELETE CASCADE,
    permission_id BIGINT NOT NULL REFERENCES auth_permissions(id) ON DELETE CASCADE,
    granted_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    
    CONSTRAINT auth_role_permissions_unique_role_permission UNIQUE(role_id, permission_id)
);

-- Create indexes
CREATE INDEX idx_auth_role_permissions_role_id ON auth_role_permissions(role_id);
CREATE INDEX idx_auth_role_permissions_permission_id ON auth_role_permissions(permission_id);

-- Enable RLS
ALTER TABLE auth_role_permissions ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Everyone can view role permissions" ON auth_role_permissions
    FOR SELECT USING (true);

-- Create permission type enum
CREATE TYPE permission_grant_type AS ENUM ('grant', 'deny');

-- 3. Create auth_user_permissions table (for direct permission assignments)
CREATE TABLE auth_user_permissions (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    permission_id BIGINT NOT NULL REFERENCES auth_permissions(id) ON DELETE CASCADE,
    grant_type permission_grant_type NOT NULL DEFAULT 'grant',
    granted_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    granted_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    revoked_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Create unique index for active permissions (considering grant_type)
CREATE UNIQUE INDEX idx_auth_user_permissions_unique_active 
    ON auth_user_permissions(user_id, permission_id, grant_type) 
    WHERE revoked_at IS NULL;

-- Create other indexes
CREATE INDEX idx_auth_user_permissions_user_id ON auth_user_permissions(user_id);
CREATE INDEX idx_auth_user_permissions_permission_id ON auth_user_permissions(permission_id);
CREATE INDEX idx_auth_user_permissions_expires_at ON auth_user_permissions(expires_at) 
    WHERE expires_at IS NOT NULL AND revoked_at IS NULL;
CREATE INDEX idx_auth_user_permissions_user_id_active ON auth_user_permissions(user_id) 
    WHERE revoked_at IS NULL;

-- Add constraints
ALTER TABLE auth_user_permissions ADD CONSTRAINT auth_user_permissions_valid_dates
    CHECK (
        (expires_at IS NULL OR expires_at > granted_at) AND
        (revoked_at IS NULL OR revoked_at >= granted_at)
    );

ALTER TABLE auth_user_permissions ADD CONSTRAINT auth_user_permissions_revoked_logic
    CHECK (
        (revoked_at IS NULL AND revoked_by IS NULL) OR
        (revoked_at IS NOT NULL AND revoked_by IS NOT NULL)
    );

-- Enable RLS
ALTER TABLE auth_user_permissions ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own direct permissions" ON auth_user_permissions
    FOR SELECT USING (auth.uid() = user_id);

COMMENT ON TABLE auth_user_roles IS 'User role assignments with expiration support';
COMMENT ON TABLE auth_role_permissions IS 'Permissions assigned to roles';
COMMENT ON TABLE auth_user_permissions IS 'Direct user permissions bypassing roles - can grant or deny';
COMMENT ON COLUMN auth_user_permissions.grant_type IS 'Whether this permission is granted or denied. Denials override grants.';