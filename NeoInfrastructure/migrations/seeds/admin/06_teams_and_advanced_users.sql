-- NeoMultiTenant - Seed Data: Teams and Advanced User Management
-- This seed file populates teams, team members, and user role/permission assignments
-- Run with: ./deploy.sh --seed

-- ============================================================================
-- ADDITIONAL USERS: Create diverse user base for teams
-- ============================================================================

-- Create additional users to populate teams realistically
INSERT INTO admin.users (
    email, username, first_name, last_name, display_name, status,
    external_auth_provider, external_user_id, job_title, company, phone,
    timezone, locale, default_role_level, is_system_user, is_onboarding_completed,
    profile_completion_percentage, departments, notification_preferences, ui_preferences,
    feature_flags, tags, custom_fields, last_login_at, last_activity_at, metadata
) VALUES 
-- TechCorp team members
(
    'alice.developer@techcorp.com', 'alice_dev', 'Alice', 'Williams', 'Alice Williams (Dev)',
    'active', 'keycloak', 'techcorp_user_001', 'Senior Frontend Developer', 'TechCorp Solutions', '+1-555-0201',
    'America/New_York', 'en-US', 'member', false, true, 95,
    ARRAY['Engineering', 'Frontend'], 
    '{"email": true, "push": true, "digest": "weekly"}',
    '{"theme": "dark", "sidebar": "collapsed", "notifications": "enabled"}',
    '{"beta_features": true, "advanced_ui": true}',
    ARRAY['developer', 'frontend', 'react'],
    '{"specialization": "React/TypeScript", "years_experience": 5}',
    NOW() - INTERVAL '3 hours', NOW() - INTERVAL '1 hour',
    '{"hire_date": "2022-03-15", "team": "frontend", "level": "senior"}'
),
(
    'bob.backend@techcorp.com', 'bob_backend', 'Bob', 'Johnson', 'Bob Johnson (Backend)',
    'active', 'keycloak', 'techcorp_user_002', 'Backend Engineer', 'TechCorp Solutions', '+1-555-0202',
    'America/New_York', 'en-US', 'member', false, true, 88,
    ARRAY['Engineering', 'Backend'],
    '{"email": true, "push": false, "digest": "daily"}',
    '{"theme": "light", "sidebar": "expanded", "notifications": "minimal"}',
    '{"beta_features": false, "api_explorer": true}',
    ARRAY['developer', 'backend', 'python'],
    '{"specialization": "Python/Django", "years_experience": 3}',
    NOW() - INTERVAL '5 hours', NOW() - INTERVAL '2 hours',
    '{"hire_date": "2023-01-10", "team": "backend", "level": "mid"}'
),
(
    'carol.qa@techcorp.com', 'carol_qa', 'Carol', 'Davis', 'Carol Davis (QA)',
    'active', 'keycloak', 'techcorp_user_003', 'QA Engineer', 'TechCorp Solutions', '+1-555-0203',
    'America/New_York', 'en-US', 'member', false, true, 92,
    ARRAY['Quality Assurance', 'Testing'],
    '{"email": true, "push": true, "digest": "weekly"}',
    '{"theme": "light", "sidebar": "expanded", "notifications": "all"}',
    '{"automation_tools": true, "test_analytics": true}',
    ARRAY['qa', 'automation', 'testing'],
    '{"specialization": "Test Automation", "certifications": ["ISTQB"]}',
    NOW() - INTERVAL '4 hours', NOW() - INTERVAL '1.5 hours',
    '{"hire_date": "2022-08-22", "team": "qa", "level": "senior"}'
),

-- StartupFlex team members
(
    'emma.fullstack@startupflex.io', 'emma_fullstack', 'Emma', 'Garcia', 'Emma Garcia (Fullstack)',
    'active', 'keycloak', 'startupflex_user_001', 'Fullstack Developer', 'StartupFlex', '+1-555-0301',
    'America/Los_Angeles', 'en-US', 'member', false, true, 90,
    ARRAY['Engineering', 'Product'],
    '{"email": true, "push": true, "digest": "daily"}',
    '{"theme": "auto", "sidebar": "collapsed", "notifications": "important"}',
    '{"startup_mode": true, "rapid_deployment": true}',
    ARRAY['fullstack', 'javascript', 'startup'],
    '{"specialization": "MERN Stack", "startup_experience": true}',
    NOW() - INTERVAL '2 hours', NOW() - INTERVAL '30 minutes',
    '{"hire_date": "2023-06-01", "equity": "0.5%", "level": "mid"}'
),
(
    'frank.design@startupflex.io', 'frank_design', 'Frank', 'Miller', 'Frank Miller (Design)',
    'active', 'keycloak', 'startupflex_user_002', 'UX/UI Designer', 'StartupFlex', '+1-555-0302',
    'America/Los_Angeles', 'en-US', 'member', false, true, 85,
    ARRAY['Design', 'Product'],
    '{"email": true, "push": false, "digest": "weekly"}',
    '{"theme": "light", "sidebar": "expanded", "notifications": "minimal"}',
    '{"design_system": true, "prototyping_tools": true}',
    ARRAY['designer', 'ux', 'ui'],
    '{"specialization": "Product Design", "tools": ["Figma", "Sketch"]}',
    NOW() - INTERVAL '6 hours', NOW() - INTERVAL '3 hours',
    '{"hire_date": "2023-09-15", "equity": "0.3%", "level": "mid"}'
),

-- AI Innovate team members  
(
    'dr.smith@aiinnovate.eu', 'dr_smith_ml', 'Dr. James', 'Smith', 'Dr. James Smith (ML)',
    'active', 'keycloak', 'aiinnovate_user_001', 'Machine Learning Engineer', 'AI Innovate Labs', '+33-1-23-45-67-90',
    'Europe/Paris', 'en-GB', 'member', false, true, 98,
    ARRAY['Machine Learning', 'Research'],
    '{"email": true, "push": true, "digest": "daily"}',
    '{"theme": "dark", "sidebar": "collapsed", "notifications": "all"}',
    '{"ml_experiments": true, "gpu_access": true, "research_tools": true}',
    ARRAY['ml-engineer', 'phd', 'research'],
    '{"education": "PhD Computer Science", "specialization": "Deep Learning", "publications": 15}',
    NOW() - INTERVAL '1 hour', NOW() - INTERVAL '15 minutes',
    '{"hire_date": "2021-11-01", "research_budget": 50000, "level": "principal"}'
),
(
    'anna.data@aiinnovate.eu', 'anna_data', 'Anna', 'Kowalski', 'Anna Kowalski (Data)',
    'active', 'keycloak', 'aiinnovate_user_002', 'Data Scientist', 'AI Innovate Labs', '+33-1-23-45-67-91',
    'Europe/Paris', 'fr-FR', 'member', false, true, 93,
    ARRAY['Data Science', 'Analytics'],
    '{"email": true, "push": true, "digest": "weekly"}',
    '{"theme": "light", "sidebar": "expanded", "notifications": "important"}',
    '{"jupyter_access": true, "data_lake_access": true}',
    ARRAY['data-scientist', 'python', 'analytics'],
    '{"education": "MSc Statistics", "specialization": "Statistical Analysis", "languages": ["Python", "R"]}',
    NOW() - INTERVAL '4 hours', NOW() - INTERVAL '2 hours',
    '{"hire_date": "2022-05-20", "level": "senior"}'
),

-- Enterprise Solutions team members
(
    'michael.devops@enterprisesol.com', 'michael_devops', 'Michael', 'Brown', 'Michael Brown (DevOps)',
    'active', 'keycloak', 'enterprise_user_001', 'Senior DevOps Engineer', 'Enterprise Solutions Inc', '+1-555-0401',
    'America/Chicago', 'en-US', 'member', false, true, 96,
    ARRAY['Infrastructure', 'DevOps'],
    '{"email": true, "push": true, "digest": "immediate"}',
    '{"theme": "dark", "sidebar": "collapsed", "notifications": "critical_only"}',
    '{"infrastructure_access": true, "monitoring_tools": true, "deployment_automation": true}',
    ARRAY['devops', 'kubernetes', 'aws'],
    '{"specialization": "Cloud Infrastructure", "certifications": ["AWS Solutions Architect", "CKA"]}',
    NOW() - INTERVAL '2 hours', NOW() - INTERVAL '45 minutes',
    '{"hire_date": "2020-09-12", "security_clearance": "level_2", "level": "senior"}'
),
(
    'jennifer.architect@enterprisesol.com', 'jennifer_arch', 'Jennifer', 'Wilson', 'Jennifer Wilson (Architect)',
    'active', 'keycloak', 'enterprise_user_002', 'Solutions Architect', 'Enterprise Solutions Inc', '+1-555-0402',
    'America/Chicago', 'en-US', 'admin', false, true, 100,
    ARRAY['Architecture', 'Engineering'],
    '{"email": true, "push": false, "digest": "weekly"}',
    '{"theme": "light", "sidebar": "expanded", "notifications": "important"}',
    '{"architecture_tools": true, "system_design": true, "enterprise_patterns": true}',
    ARRAY['architect', 'enterprise', 'systems'],
    '{"education": "MSc Software Engineering", "specialization": "Enterprise Architecture", "years_experience": 12}',
    NOW() - INTERVAL '1 day', NOW() - INTERVAL '8 hours',
    '{"hire_date": "2019-03-01", "architect_level": "principal", "level": "principal"}'
),

-- Global Corp team members
(
    'hans.security@globalcorp.com', 'hans_security', 'Hans', 'Mueller', 'Hans Mueller (Security)',
    'active', 'keycloak', 'globalcorp_user_001', 'Information Security Manager', 'Global Corp International', '+49-89-123-45679',
    'Europe/Berlin', 'de-DE', 'admin', false, true, 100,
    ARRAY['Security', 'Compliance'],
    '{"email": true, "push": true, "digest": "immediate"}',
    '{"theme": "dark", "sidebar": "collapsed", "notifications": "security_only"}',
    '{"security_tools": true, "audit_access": true, "compliance_dashboard": true}',
    ARRAY['security', 'committee', 'iso27001'],
    '{"education": "MSc Cybersecurity", "specialization": "Enterprise Security", "certifications": ["CISSP", "CISM"]}',
    NOW() - INTERVAL '3 hours', NOW() - INTERVAL '1 hour',
    '{"hire_date": "2018-01-15", "security_clearance": "level_3", "level": "manager"}'
),
(
    'priya.manufacturing@globalcorp.com', 'priya_mfg', 'Priya', 'Patel', 'Priya Patel (Manufacturing)',
    'active', 'keycloak', 'globalcorp_user_002', 'Manufacturing Systems Analyst', 'Global Corp International', '+49-89-123-45680',
    'Europe/Berlin', 'en-GB', 'member', false, true, 94,
    ARRAY['Manufacturing', 'Operations'],
    '{"email": true, "push": true, "digest": "daily"}',
    '{"theme": "light", "sidebar": "expanded", "notifications": "operational"}',
    '{"manufacturing_dashboard": true, "iot_monitoring": true, "production_analytics": true}',
    ARRAY['manufacturing', 'iot', 'analytics'],
    '{"education": "BEng Industrial Engineering", "specialization": "Manufacturing Systems", "languages": ["English", "German", "Hindi"]}',
    NOW() - INTERVAL '5 hours', NOW() - INTERVAL '2.5 hours',
    '{"hire_date": "2021-07-10", "plant_access": ["berlin", "munich"], "level": "senior"}'
)
ON CONFLICT (email) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    job_title = EXCLUDED.job_title,
    last_activity_at = EXCLUDED.last_activity_at,
    updated_at = NOW();

-- ============================================================================
-- TEAMS: Create organizational teams within each major tenant
-- ============================================================================

-- Create teams with realistic hierarchies and structures
WITH tenant_data AS (
    SELECT id as tenant_id, slug as tenant_slug FROM admin.tenants
),
team_owners AS (
    SELECT 
        id as owner_id, 
        email,
        CASE 
            WHEN email LIKE '%techcorp%' THEN 'techcorp'
            WHEN email LIKE '%startupflex%' THEN 'startupflex' 
            WHEN email LIKE '%aiinnovate%' THEN 'aiinnovate'
            WHEN email LIKE '%enterprisesol%' THEN 'enterprise'
            WHEN email LIKE '%globalcorp%' THEN 'globalcorp'
        END as company_prefix
    FROM admin.users
    WHERE email IN ('manager@techcorp.com', 'admin@startupflex.io', 'founder@aiinnovate.eu', 
                    'cto@enterprisesol.com', 'director@globalcorp.com')
)
INSERT INTO admin.teams (
    name, slug, description, team_type, is_active, max_members, owner_id,
    settings
)
SELECT 
    t.name,
    LOWER(REPLACE(REPLACE(t.name, ' ', '-'), '&', 'and')),
    t.description,
    t.team_type::platform_common.team_types,
    t.is_active,
    t.max_members,
    team_owners.owner_id,
    t.settings::jsonb
FROM team_owners
JOIN (
    VALUES 
        -- TechCorp teams
        ('techcorp', 'Engineering', 'Core engineering team responsible for product development', 'department', true, 25, '{"meeting_day": "monday", "standup_time": "09:00", "timezone": "America/New_York"}', '{"department": "engineering", "budget_code": "ENG-001"}'),
        ('techcorp', 'Product', 'Product management and strategy team', 'department', true, 8, '{"meeting_day": "tuesday", "review_time": "14:00", "timezone": "America/New_York"}', '{"department": "product", "budget_code": "PRD-001"}'),
        ('techcorp', 'Quality Assurance', 'QA and testing team ensuring product quality', 'department', true, 12, '{"meeting_day": "wednesday", "testing_cycle": "2_weeks", "timezone": "America/New_York"}', '{"department": "qa", "budget_code": "QA-001"}'),
        
        -- StartupFlex teams (smaller, more flexible)
        ('startupflex', 'Core Team', 'Main product development team', 'working_group', true, 15, '{"meeting_day": "daily", "standup_time": "10:00", "timezone": "America/Los_Angeles"}', '{"department": "all", "equity_pool": "team_pool"}'),
        ('startupflex', 'Growth', 'Marketing and growth team', 'department', true, 10, '{"meeting_day": "friday", "growth_review": "weekly", "timezone": "America/Los_Angeles"}', '{"department": "growth", "budget_code": "GRW-001"}'),
        
        -- AI Innovate teams (research-focused)
        ('aiinnovate', 'Research Lab', 'Core AI/ML research and development team', 'department', true, 20, '{"meeting_day": "thursday", "research_review": "monthly", "timezone": "Europe/Paris"}', '{"department": "research", "funding_source": "research_grant"}'),
        ('aiinnovate', 'Production ML', 'Production ML systems and deployment', 'department', true, 15, '{"meeting_day": "tuesday", "deployment_cycle": "weekly", "timezone": "Europe/Paris"}', '{"department": "ml_ops", "budget_code": "MLO-001"}'),
        ('aiinnovate', 'Data Science', 'Data analysis and insights team', 'department', true, 12, '{"meeting_day": "wednesday", "data_review": "bi_weekly", "timezone": "Europe/Paris"}', '{"department": "data_science", "budget_code": "DS-001"}'),
        
        -- Enterprise Solutions teams (structured)
        ('enterprise', 'Platform Engineering', 'Core platform and infrastructure team', 'department', true, 30, '{"meeting_day": "monday", "architecture_review": "weekly", "timezone": "America/Chicago"}', '{"department": "platform", "budget_code": "PLT-001", "compliance_level": "high"}'),
        ('enterprise', 'Security Team', 'Information security and compliance team', 'committee', true, 15, '{"meeting_day": "friday", "security_review": "weekly", "timezone": "America/Chicago"}', '{"department": "security", "budget_code": "SEC-001", "clearance_required": true}'),
        ('enterprise', 'Solutions Architecture', 'Enterprise solutions and architecture team', 'working_group', true, 20, '{"meeting_day": "thursday", "architecture_board": "monthly", "timezone": "America/Chicago"}', '{"department": "architecture", "budget_code": "ARC-001"}'),
        
        -- Global Corp teams (large, distributed)
        ('globalcorp', 'Global IT', 'Global information technology team', 'department', true, 50, '{"meeting_day": "monday", "global_sync": "weekly", "timezone": "Europe/Berlin"}', '{"department": "global_it", "budget_code": "GIT-001", "multi_region": true}'),
        ('globalcorp', 'Manufacturing Systems', 'Manufacturing and operations systems team', 'department', true, 35, '{"meeting_day": "tuesday", "production_review": "daily", "timezone": "Europe/Berlin"}', '{"department": "manufacturing", "budget_code": "MFG-001", "plant_access": true}'),
        ('globalcorp', 'Compliance & Security', 'Global compliance and security oversight', 'committee', true, 25, '{"meeting_day": "wednesday", "audit_cycle": "quarterly", "timezone": "Europe/Berlin"}', '{"department": "compliance", "budget_code": "CMP-001", "iso_certified": true}}')
) AS t(company_prefix, name, description, team_type, is_active, max_members, settings, metadata) ON team_owners.company_prefix = t.company_prefix
ON CONFLICT (slug) DO UPDATE SET
    description = EXCLUDED.description,
    max_members = EXCLUDED.max_members,
    settings = EXCLUDED.settings,
    updated_at = NOW();

-- ============================================================================
-- TEAM MEMBERS: Assign users to appropriate teams
-- ============================================================================

-- Assign team members based on their roles and companies
WITH team_data AS (
    SELECT 
        t.id as team_id,
        t.name as team_name,
        u.email as owner_email,
        CASE 
            WHEN u.email LIKE '%techcorp%' THEN 'techcorp'
            WHEN u.email LIKE '%startupflex%' THEN 'startupflex'
            WHEN u.email LIKE '%aiinnovate%' THEN 'aiinnovate'
            WHEN u.email LIKE '%enterprisesol%' THEN 'enterprise'
            WHEN u.email LIKE '%globalcorp%' THEN 'globalcorp'
        END as company_prefix
    FROM admin.teams t
    JOIN admin.users u ON t.owner_id = u.id
),
user_data AS (
    SELECT 
        id as user_id,
        email,
        job_title,
        CASE 
            WHEN email LIKE '%techcorp%' THEN 'techcorp'
            WHEN email LIKE '%startupflex%' THEN 'startupflex'
            WHEN email LIKE '%aiinnovate%' THEN 'aiinnovate'
            WHEN email LIKE '%enterprisesol%' THEN 'enterprise'
            WHEN email LIKE '%globalcorp%' THEN 'globalcorp'
        END as company_prefix
    FROM admin.users
    WHERE email NOT LIKE '%admin@neomultitenant%'
),
inviter_data AS (
    SELECT id as inviter_id FROM admin.users WHERE email = 'admin@neomultitenant.com' LIMIT 1
)
INSERT INTO admin.team_members (
    team_id, user_id, role, status, member_config, invited_by,
    joined_at
)
SELECT 
    td.team_id,
    ud.user_id,
    tm.role,
    'active',
    tm.permissions::jsonb,
    id.inviter_id,
    tm.joined_at::timestamptz
FROM team_data td
JOIN user_data ud ON td.company_prefix = ud.company_prefix
CROSS JOIN inviter_data id
JOIN (
    VALUES 
        -- TechCorp team assignments
        ('techcorp', 'Engineering', 'manager@techcorp.com', 'lead', '{"code_review": true, "deployment": true, "team_management": true}', NOW() - INTERVAL '6 months', '{"founding_member": true}'),
        ('techcorp', 'Engineering', 'alice.developer@techcorp.com', 'member', '{"code_review": true, "frontend_lead": true}', NOW() - INTERVAL '18 months', '{"specialty": "frontend", "mentor": true}'),
        ('techcorp', 'Engineering', 'bob.backend@techcorp.com', 'member', '{"code_review": false, "backend_access": true}', NOW() - INTERVAL '10 months', '{"specialty": "backend", "junior_level": false}'),
        ('techcorp', 'Quality Assurance', 'carol.qa@techcorp.com', 'lead', '{"test_planning": true, "automation": true, "team_management": true}', NOW() - INTERVAL '16 months', '{"qa_lead": true, "automation_expert": true}'),
        ('techcorp', 'Quality Assurance', 'manager@techcorp.com', 'member', '{"oversight": true, "strategy": true}', NOW() - INTERVAL '6 months', '{"cross_team": true}'),
        
        -- StartupFlex team assignments (everyone on core team)
        ('startupflex', 'Core Team', 'admin@startupflex.io', 'lead', '{"full_access": true, "admin": true, "hiring": true}', NOW() - INTERVAL '3 months', '{"founder_team": true}'),
        ('startupflex', 'Core Team', 'dev@startupflex.io', 'member', '{"development": true, "architecture": true}', NOW() - INTERVAL '3 months', '{"employee_number": 1}'),
        ('startupflex', 'Core Team', 'emma.fullstack@startupflex.io', 'member', '{"fullstack": true, "product": true}', NOW() - INTERVAL '6 months', '{"early_employee": true}'),
        ('startupflex', 'Growth', 'frank.design@startupflex.io', 'member', '{"design": true, "ux_research": true}', NOW() - INTERVAL '3 months', '{"design_lead": true}'),
        
        -- AI Innovate team assignments
        ('aiinnovate', 'Research Lab', 'founder@aiinnovate.eu', 'lead', '{"research_direction": true, "funding": true, "publications": true}', NOW() - INTERVAL '8 months', '{"founder": true, "principal_investigator": true}'),
        ('aiinnovate', 'Research Lab', 'dr.smith@aiinnovate.eu', 'member', '{"research": true, "mentoring": true, "publications": true}', NOW() - INTERVAL '32 months', '{"phd_level": true, "publications": 15}'),
        ('aiinnovate', 'Data Science', 'anna.data@aiinnovate.eu', 'member', '{"data_analysis": true, "statistics": true, "visualization": true}', NOW() - INTERVAL '20 months', '{"statistics_expert": true}'),
        ('aiinnovate', 'Production ML', 'dr.smith@aiinnovate.eu', 'member', '{"ml_ops": true, "deployment": true}', NOW() - INTERVAL '6 months', '{"cross_team": true}'),
        
        -- Enterprise Solutions team assignments
        ('enterprise', 'Platform Engineering', 'cto@enterprisesol.com', 'lead', '{"platform_strategy": true, "architecture": true, "budget": true}', NOW() - INTERVAL '2 years', '{"cto_level": true}'),
        ('enterprise', 'Platform Engineering', 'michael.devops@enterprisesol.com', 'member', '{"infrastructure": true, "deployment": true, "monitoring": true}', NOW() - INTERVAL '3 years 3 months', '{"senior_level": true, "infrastructure_lead": true}'),
        ('enterprise', 'Solutions Architecture', 'jennifer.architect@enterprisesol.com', 'lead', '{"solution_design": true, "client_facing": true, "standards": true}', NOW() - INTERVAL '4 years 9 months', '{"principal_architect": true}'),
        ('enterprise', 'Solutions Architecture', 'cto@enterprisesol.com', 'member', '{"oversight": true, "strategy": true}', NOW() - INTERVAL '2 years', '{"executive_sponsor": true}'),
        
        -- Global Corp team assignments
        ('globalcorp', 'Global IT', 'director@globalcorp.com', 'lead', '{"global_strategy": true, "budget": true, "governance": true}', NOW() - INTERVAL '3 years', '{"director_level": true}'),
        ('globalcorp', 'Compliance & Security', 'hans.security@globalcorp.com', 'lead', '{"security_policy": true, "compliance": true, "audit": true}', NOW() - INTERVAL '6 years', '{"security_manager": true, "iso_lead": true}'),
        ('globalcorp', 'Manufacturing Systems', 'priya.manufacturing@globalcorp.com', 'member', '{"manufacturing_analysis": true, "iot_systems": true, "operations": true}', NOW() - INTERVAL '2 years 5 months', '{"manufacturing_expert": true, "multi_plant": true}'),
        ('globalcorp', 'Manufacturing Systems', 'director@globalcorp.com', 'member', '{"oversight": true, "strategy": true}', NOW() - INTERVAL '3 years', '{"executive_sponsor": true}')
) AS tm(company_prefix, team_name, user_email, role, permissions, joined_at, metadata) ON td.company_prefix = tm.company_prefix 
  AND td.team_name = tm.team_name 
  AND ud.email = tm.user_email
ON CONFLICT (team_id, user_id) DO UPDATE SET
    role = EXCLUDED.role,
    member_config = EXCLUDED.member_config,
    joined_at = EXCLUDED.joined_at;

-- ============================================================================
-- USER ROLES: Assign roles to users with proper scoping
-- ============================================================================

-- Assign roles to users based on their position and responsibilities
WITH user_data AS (
    SELECT 
        id as user_id,
        email,
        job_title,
        default_role_level
    FROM admin.users
    WHERE email NOT LIKE '%admin@neomultitenant%'
),
role_data AS (
    SELECT id as role_id, code as role_code FROM admin.roles
),
admin_user AS (
    SELECT id as admin_id FROM admin.users WHERE email = 'admin@neomultitenant.com' LIMIT 1
)
INSERT INTO admin.user_roles (
    user_id, role_id, scope_type, scope_id, granted_by, granted_reason,
    is_active, granted_at
)
SELECT 
    ud.user_id,
    rd.role_id,
    ur.scope_type,
    ur.scope_id,
    au.admin_id,
    ur.granted_reason,
    true,
    ur.granted_at::timestamptz
FROM user_data ud
CROSS JOIN admin_user au
JOIN (
    VALUES 
        -- Platform-level roles (global scope)
        ('cto@enterprisesol.com', 'platform_admin', 'global', NULL::UUID, 'CTO level access for enterprise customer', NOW() - INTERVAL '2 years'),
        ('director@globalcorp.com', 'platform_admin', 'global', NULL::UUID, 'Director level access for global customer', NOW() - INTERVAL '3 years'),
        
        -- Tenant-level admin roles
        ('manager@techcorp.com', 'tenant_admin', 'tenant', NULL::UUID, 'Project manager with admin responsibilities', NOW() - INTERVAL '6 months'),
        ('admin@startupflex.io', 'tenant_admin', 'tenant', NULL::UUID, 'Operations manager with full tenant access', NOW() - INTERVAL '3 months'),
        ('founder@aiinnovate.eu', 'tenant_owner', 'tenant', NULL::UUID, 'Founder and primary tenant owner', NOW() - INTERVAL '8 months'),
        ('cto@enterprisesol.com', 'tenant_admin', 'tenant', NULL::UUID, 'Technical lead for enterprise tenants', NOW() - INTERVAL '2 years'),
        ('director@globalcorp.com', 'tenant_admin', 'tenant', NULL::UUID, 'IT Director with tenant administration rights', NOW() - INTERVAL '3 years'),
        
        -- Team-level manager roles
        ('jennifer.architect@enterprisesol.com', 'tenant_manager', 'team', NULL::UUID, 'Solutions architecture team lead', NOW() - INTERVAL '4 years'),
        ('hans.security@globalcorp.com', 'tenant_manager', 'team', NULL::UUID, 'Security team manager', NOW() - INTERVAL '6 years'),
        ('dr.smith@aiinnovate.eu', 'tenant_manager', 'team', NULL::UUID, 'ML research team lead', NOW() - INTERVAL '2 years'),
        
        -- Standard user roles
        ('alice.developer@techcorp.com', 'tenant_user', 'tenant', NULL::UUID, 'Senior frontend developer access', NOW() - INTERVAL '18 months'),
        ('bob.backend@techcorp.com', 'tenant_user', 'tenant', NULL::UUID, 'Backend engineer access', NOW() - INTERVAL '10 months'),
        ('carol.qa@techcorp.com', 'tenant_user', 'tenant', NULL::UUID, 'QA engineer access', NOW() - INTERVAL '16 months'),
        ('dev@startupflex.io', 'tenant_user', 'tenant', NULL::UUID, 'Senior developer access', NOW() - INTERVAL '3 months'),
        ('emma.fullstack@startupflex.io', 'tenant_user', 'tenant', NULL::UUID, 'Fullstack developer access', NOW() - INTERVAL '6 months'),
        ('frank.design@startupflex.io', 'tenant_user', 'tenant', NULL::UUID, 'UX/UI designer access', NOW() - INTERVAL '3 months'),
        ('anna.data@aiinnovate.eu', 'tenant_user', 'tenant', NULL::UUID, 'Data scientist access', NOW() - INTERVAL '20 months'),
        ('michael.devops@enterprisesol.com', 'tenant_user', 'tenant', NULL::UUID, 'DevOps engineer access', NOW() - INTERVAL '3 years'),
        ('priya.manufacturing@globalcorp.com', 'tenant_user', 'tenant', NULL::UUID, 'Manufacturing analyst access', NOW() - INTERVAL '2 years')
) AS ur(user_email, role_code, scope_type, scope_id, granted_reason, granted_at) ON ud.email = ur.user_email
JOIN role_data rd ON rd.role_code = ur.role_code
ON CONFLICT (user_id, role_id, scope_id) DO UPDATE SET
    granted_reason = EXCLUDED.granted_reason,
    is_active = true;

-- ============================================================================
-- VERIFICATION: Show teams and user assignments
-- ============================================================================

-- Show teams with member counts
SELECT 
    t.name as team_name,
    t.team_type,
    u.display_name as owner,
    COUNT(tm.user_id) as member_count,
    t.max_members,
    t.is_active
FROM admin.teams t
JOIN admin.users u ON t.owner_id = u.id
LEFT JOIN admin.team_members tm ON t.id = tm.team_id AND tm.status = 'active'
GROUP BY t.id, t.name, t.team_type, u.display_name, t.max_members, t.is_active
ORDER BY t.name;

-- Show team members with roles
SELECT 
    t.name as team,
    u.display_name as member,
    u.job_title,
    tm.role as team_role,
    tm.status,
    tm.joined_at::date as joined_date
FROM admin.team_members tm
JOIN admin.teams t ON tm.team_id = t.id
JOIN admin.users u ON tm.user_id = u.id
ORDER BY t.name, tm.role DESC, u.display_name;

-- Show user roles summary
SELECT 
    u.display_name as user_name,
    u.job_title,
    r.name as role_name,
    ur.scope_type,
    ur.granted_at::date as granted_date,
    ur.is_active
FROM admin.user_roles ur
JOIN admin.users u ON ur.user_id = u.id
JOIN admin.roles r ON ur.role_id = r.id
WHERE u.email NOT LIKE '%admin@neomultitenant%'
ORDER BY u.display_name, r.priority DESC;

-- Summary statistics
SELECT 
    'Teams' as entity_type,
    COUNT(*) as total_count,
    COUNT(CASE WHEN is_active THEN 1 END) as active_count
FROM admin.teams
UNION ALL
SELECT 
    'Team Members' as entity_type,
    COUNT(*) as total_count,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_count
FROM admin.team_members
UNION ALL
SELECT 
    'User Role Assignments' as entity_type,
    COUNT(*) as total_count,
    COUNT(CASE WHEN is_active THEN 1 END) as active_count
FROM admin.user_roles;

-- Log completion
SELECT 'Teams and advanced user management seeded successfully' as seed_status;
