-- Migration: Create core RBAC tables (roles and permissions)
-- Description: Sets up the foundation for role-based access control with optimized caching

-- 1. Create auth_roles table with built-in permission cache
CREATE TABLE auth_roles (
    id BIGSERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    priority INTEGER DEFAULT 0,
    is_system BOOLEAN DEFAULT false,
    cached_permissions TEXT[] DEFAULT ARRAY[]::TEXT[], -- Cache permissions directly in role
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    deleted_at TIMESTAMPTZ
);

-- Create indexes for auth_roles
CREATE INDEX idx_auth_roles_name ON auth_roles(name) WHERE deleted_at IS NULL;
CREATE INDEX idx_auth_roles_priority ON auth_roles(priority DESC);
CREATE INDEX idx_auth_roles_is_system ON auth_roles(is_system);

-- Enable RLS
ALTER TABLE auth_roles ENABLE ROW LEVEL SECURITY;

-- RLS Policies for auth_roles
CREATE POLICY "Everyone can view roles" ON auth_roles
    FOR SELECT USING (deleted_at IS NULL);

-- 2. Create auth_permissions table
CREATE TABLE auth_permissions (
    id BIGSERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    resource TEXT NOT NULL,
    action TEXT NOT NULL,
    scope TEXT DEFAULT 'any' NOT NULL,  -- 'own', 'any', 'team', 'organization', etc.
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    
    CONSTRAINT auth_permissions_unique_resource_action_scope UNIQUE(resource, action, scope),
    CONSTRAINT auth_permissions_valid_scope CHECK (scope IN ('own', 'any', 'team', 'organization', 'system'))
);

-- Create indexes for auth_permissions
CREATE INDEX idx_auth_permissions_name ON auth_permissions(name);
CREATE INDEX idx_auth_permissions_resource ON auth_permissions(resource);
CREATE INDEX idx_auth_permissions_action ON auth_permissions(action);
CREATE INDEX idx_auth_permissions_scope ON auth_permissions(scope);
CREATE INDEX idx_auth_permissions_resource_action ON auth_permissions(resource, action);
CREATE INDEX idx_auth_permissions_resource_action_scope ON auth_permissions(resource, action, scope);

-- Enable RLS
ALTER TABLE auth_permissions ENABLE ROW LEVEL SECURITY;

-- RLS Policies for auth_permissions
CREATE POLICY "Everyone can view permissions" ON auth_permissions
    FOR SELECT USING (true);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_auth_roles_updated_at 
    BEFORE UPDATE ON auth_roles
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default roles
INSERT INTO auth_roles (name, description, priority, is_system) VALUES
    ('admin', 'System administrator with full access', 100, true),
    ('moderator', 'Content moderator with limited admin access', 50, true),
    ('user', 'Standard user with basic access', 10, true),
    ('guest', 'Guest user with minimal access', 0, true);

COMMENT ON TABLE auth_roles IS 'System roles for RBAC authorization with built-in permission cache';
COMMENT ON TABLE auth_permissions IS 'Available permissions for RBAC system (optimized with BIGSERIAL)';