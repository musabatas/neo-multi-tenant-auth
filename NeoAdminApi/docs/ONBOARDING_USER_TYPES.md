# User Types and Onboarding Flows

## Overview

The platform distinguishes between two primary user types, each with their own onboarding journey:

1. **Platform Admin Users** - Users who create and manage organizations/tenants
2. **Tenant Users** - Users who are invited to join existing workspaces

## User Type Detection

The system automatically determines user type based on:
- `is_superadmin` flag
- Platform roles (`platform_admin`, `organization_owner`, `organization_admin`)
- Invitation source (direct signup vs invitation link)

## Platform Admin Onboarding Flow

Platform admins are users who sign up directly and intend to create their own organization and workspaces.

### Steps:

1. **Profile Completion** (Weight: 30%)
   - First name, last name
   - Phone number
   - Job title and company
   - Avatar upload
   - Professional information

2. **Organization Creation** (Weight: 20%)
   - Organization name and details
   - Industry selection
   - Size and type
   - Initial configuration

3. **First Tenant Creation** (Weight: 20%)
   - Workspace name
   - Region selection
   - Initial settings
   - Resource allocation

4. **Billing Setup** (Weight: 20%)
   - Payment method
   - Subscription plan selection
   - Billing address
   - Tax information

5. **Security Configuration** (Weight: 10%)
   - Two-factor authentication
   - Security questions
   - API keys (if needed)
   - Audit settings

### Next Step Logic:
```javascript
if (!profile_completed) -> "Complete Your Profile"
else if (!organization_created) -> "Create Your Organization"
else if (!first_tenant_created) -> "Create Your First Workspace"
else if (!billing_setup) -> "Set Up Billing"
else if (!security_configured) -> "Configure Security Settings"
else -> ONBOARDING_COMPLETE
```

## Tenant User Onboarding Flow

Tenant users are invited to join existing workspaces and don't need to create organizations or manage billing.

### Steps:

1. **Profile Completion** (Weight: 40%)
   - Basic information
   - Contact details
   - Department/team info
   - Skills and expertise

2. **Tenant Joined** (Weight: 20%)
   - Accept workspace invitation
   - Verify email
   - Set initial password
   - Accept terms

3. **Team Joined** (Weight: 15%)
   - Assigned to team
   - Meet team members
   - Understand team structure
   - Review team resources

4. **Workspace Accessed** (Weight: 15%)
   - First login to workspace
   - Tour key features
   - Access granted resources
   - Initial activity

5. **Preferences Configured** (Weight: 10%)
   - Notification settings
   - UI preferences
   - Language/timezone
   - Accessibility options

### Next Step Logic:
```javascript
if (!profile_completed) -> "Complete Your Profile"
else if (!tenant_joined) -> "Accept Workspace Invitation"
else if (!team_joined) -> "Join Your Team"
else if (!workspace_accessed) -> "Explore Your Workspace"
else if (!preferences_configured) -> "Configure Your Preferences"
else -> ONBOARDING_COMPLETE
```

## API Response Structure

### GET /users/me/onboarding/status

```json
{
  "is_completed": false,
  "user_type": "platform_admin" | "tenant_user",
  "completion_percentage": 60,
  "completed_steps": ["profile_completed", "organization_created"],
  "pending_steps": ["first_tenant_created", "billing_setup", "security_configured"],
  "onboarding_steps": {
    "profile_completed": true,
    "organization_created": true,
    "first_tenant_created": false,
    "billing_setup": false,
    "security_configured": false
  },
  "next_step": {
    "code": "first_tenant_created",
    "title": "Create Your First Workspace",
    "description": "Create a workspace to start collaborating with your team",
    "action_url": "/tenants/new"
  },
  "user_created_at": "2024-01-01T00:00:00Z"
}
```

## Profile Completion Calculation

The profile completion percentage is calculated with weighted fields:

### Platform Admin Weights:
- Professional info (name, title, company): 40%
- Contact info (email, phone): 20%
- Profile customization (avatar, bio): 20%
- Preferences (timezone, notifications): 20%

### Tenant User Weights:
- Basic info (name, department): 50%
- Contact info (email, phone): 20%
- Profile customization (avatar): 15%
- Preferences (notifications, UI): 15%

## Implementation Details

### User Type Storage

Store user type in metadata:
```json
{
  "metadata": {
    "user_type": "platform_admin",
    "onboarding_version": "2.0",
    "signup_source": "direct" | "invitation",
    "invitation_id": "uuid-if-invited"
  }
}
```

### Automatic Detection Logic

```python
def determine_user_type(user):
    # Superadmins are always platform admins
    if user.is_superadmin:
        return "platform_admin"
    
    # Check platform roles
    admin_roles = ['platform_admin', 'organization_owner', 'organization_admin']
    if any(role in admin_roles for role in user.platform_roles):
        return "platform_admin"
    
    # Check signup source
    if user.metadata.get('signup_source') == 'invitation':
        return "tenant_user"
    
    # Default based on organization ownership
    if user.owns_organization:
        return "platform_admin"
    
    return "tenant_user"
```

## Frontend Recommendations

### Routing

- **Platform Admins**: Route to organization/tenant creation flows
- **Tenant Users**: Route to workspace/team collaboration flows

### UI Differences

Platform Admin Dashboard:
- Organization management
- Tenant creation
- Billing overview
- User management
- Analytics

Tenant User Dashboard:
- Team workspace
- Projects/tasks
- Team collaboration
- Personal productivity
- Team resources

### Progressive Disclosure

Show features progressively based on completion:
- Basic features available immediately
- Advanced features unlock after onboarding
- Admin features only for platform admins
- Team features only after team join

## Migration Strategy

For existing users without onboarding data:

1. **Analyze existing data** to determine completion
2. **Auto-detect user type** based on current roles/permissions
3. **Set reasonable defaults** for completed steps
4. **Mark as onboarded** if account > 30 days old
5. **Prompt for missing info** gradually, not all at once

## Metrics to Track

### Platform Admin Metrics:
- Time to first tenant creation
- Organization setup completion rate
- Billing setup conversion
- Feature adoption rate

### Tenant User Metrics:
- Invitation acceptance rate
- Time to first activity
- Team collaboration score
- Workspace engagement

## Future Enhancements

1. **Customizable Onboarding**: Allow organizations to customize tenant user onboarding
2. **Role-Based Flows**: Different flows for developers, managers, executives
3. **Interactive Tutorials**: Guided tours for complex features
4. **Onboarding Analytics**: Track drop-off points and optimize
5. **Smart Recommendations**: ML-based next step suggestions
6. **Bulk Onboarding**: Tools for onboarding multiple users at once