# Onboarding Implementation Plan

## Overview
This document outlines the implementation plan for user onboarding status management across Keycloak and our PostgreSQL database, ensuring proper synchronization and a seamless frontend experience.

## Current State Analysis

### Database Schema (✅ Already Exists)
The `admin.platform_users` table already contains:
- `is_onboarding_completed` (boolean, default: false)
- `profile_completion_percentage` (smallint, default: 0)
- `first_name`, `last_name`, `display_name`
- `job_title`, `company`, `departments`
- `timezone`, `locale`
- `notification_preferences`, `ui_preferences`
- `avatar_url`, `phone`

### Missing Components
1. **Keycloak Attribute Sync**: No current sync of onboarding status to Keycloak
2. **Complete User Response**: `/auth/me` and login endpoints don't return full user data
3. **Profile Completion Logic**: No calculation of profile completion percentage
4. **Onboarding Workflow**: No API endpoints for updating onboarding status

## Implementation Strategy

### 1. Keycloak Custom Attributes

#### Option A: Sync to Keycloak (Recommended for SSO)
**Pros:**
- Single source of truth for authentication state
- Available in JWT tokens without DB lookup
- Works across all services that validate tokens
- Frontend can access directly from decoded JWT

**Cons:**
- Requires Keycloak API calls to update
- Adds complexity to sync logic
- Potential sync delays

#### Option B: Database-Only (Recommended for Simplicity)
**Pros:**
- Simpler implementation
- No external API dependencies
- Instant updates
- Already exists in our schema

**Cons:**
- Requires DB lookup on each request
- Not available in JWT tokens
- Frontend must call `/auth/me` to get status

### 2. Recommended Approach: Hybrid Solution

```
┌─────────────────────────────────────────────────────────────┐
│                     AUTHENTICATION FLOW                       │
├─────────────────────────────────────────────────────────────┤
│  1. User logs in via Keycloak                                │
│  2. Backend receives JWT token                               │
│  3. Backend fetches full user data from DB                  │
│  4. Backend returns combined data to frontend                │
│  5. Frontend caches user data in state/localStorage          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     ONBOARDING UPDATE FLOW                    │
├─────────────────────────────────────────────────────────────┤
│  1. Frontend calls onboarding API endpoints                  │
│  2. Backend updates PostgreSQL immediately                   │
│  3. Backend optionally syncs to Keycloak (async)            │
│  4. Frontend updates cached user data                        │
└─────────────────────────────────────────────────────────────┘
```

### 3. API Response Structure

#### `/auth/login` Response
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "expires_in": 3600,
    "user": {
      "id": "01989680-6e67-723b-a9b6-7fdbf6e10f97",
      "email": "admin@neomultitenant.com",
      "username": "admin",
      "first_name": "Platform",
      "last_name": "Administrator",
      "display_name": "Platform Admin",
      "avatar_url": null,
      "is_onboarding_completed": false,
      "profile_completion_percentage": 25,
      "is_active": true,
      "is_superadmin": true,
      "timezone": "UTC",
      "locale": "en-US",
      "job_title": "System Administrator",
      "company": "NeoMultiTenant",
      "roles": [
        {
          "id": 1,
          "code": "super_admin",
          "name": "Super Administrator",
          "level": "system"
        }
      ],
      "permissions": [
        "users:list",
        "users:create",
        "users:update",
        "users:delete",
        "roles:list",
        "roles:create",
        "roles:update",
        "roles:delete",
        "roles:assign",
        "tenants:list",
        "tenants:create"
      ],
      "tenant_memberships": [
        {
          "tenant_id": "uuid",
          "tenant_name": "Acme Corp",
          "tenant_slug": "acme",
          "roles": ["tenant_admin"],
          "is_primary": true
        }
      ],
      "notification_preferences": {
        "email": true,
        "sms": false,
        "in_app": true
      },
      "ui_preferences": {
        "theme": "light",
        "sidebar_collapsed": false,
        "language": "en"
      }
    }
  },
  "message": "Login successful"
}
```

#### `/auth/me` Response
```json
{
  "success": true,
  "data": {
    "id": "01989680-6e67-723b-a9b6-7fdbf6e10f97",
    "email": "admin@neomultitenant.com",
    "username": "admin",
    "first_name": "Platform",
    "last_name": "Administrator",
    "display_name": "Platform Admin",
    "avatar_url": null,
    "phone": "+1234567890",
    "is_onboarding_completed": false,
    "profile_completion_percentage": 25,
    "onboarding_steps": {
      "profile_completed": false,
      "organization_created": false,
      "first_tenant_created": false,
      "team_invited": false,
      "billing_setup": false
    },
    "is_active": true,
    "is_superadmin": true,
    "timezone": "UTC",
    "locale": "en-US",
    "job_title": "System Administrator",
    "company": "NeoMultiTenant",
    "departments": ["IT", "Engineering"],
    "roles": [...],
    "permissions": [...],
    "tenant_memberships": [...],
    "notification_preferences": {...},
    "ui_preferences": {...},
    "last_login_at": "2024-01-01T12:00:00Z",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z"
  }
}
```

### 4. New API Endpoints for Onboarding

#### `PUT /users/me/profile`
Update user profile and calculate completion percentage
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "display_name": "John Doe",
  "job_title": "CTO",
  "company": "Acme Corp",
  "departments": ["Engineering", "Product"],
  "phone": "+1234567890",
  "timezone": "America/New_York",
  "locale": "en-US"
}
```

#### `PUT /users/me/onboarding/complete`
Mark onboarding as complete
```json
{
  "completed_steps": [
    "profile_completed",
    "organization_created",
    "first_tenant_created"
  ]
}
```

#### `GET /users/me/onboarding/status`
Get detailed onboarding status
```json
{
  "is_completed": false,
  "completion_percentage": 60,
  "completed_steps": ["profile_completed"],
  "pending_steps": ["organization_created", "first_tenant_created"],
  "next_step": {
    "code": "organization_created",
    "title": "Create Your Organization",
    "description": "Set up your organization to manage teams and projects",
    "action_url": "/organizations/new"
  }
}
```

### 5. Profile Completion Calculation

```python
def calculate_profile_completion(user: PlatformUser) -> int:
    """Calculate profile completion percentage."""
    
    # Define weights for each field
    field_weights = {
        'first_name': 10,
        'last_name': 10,
        'display_name': 5,
        'avatar_url': 10,
        'phone': 10,
        'job_title': 10,
        'company': 10,
        'departments': 10,
        'timezone': 5,    # Has default, lower weight
        'locale': 5,      # Has default, lower weight
        'notification_preferences': 10,
        'ui_preferences': 5
    }
    
    total_weight = sum(field_weights.values())
    completed_weight = 0
    
    # Check each field
    if user.first_name and user.first_name.strip():
        completed_weight += field_weights['first_name']
    if user.last_name and user.last_name.strip():
        completed_weight += field_weights['last_name']
    if user.display_name and user.display_name.strip():
        completed_weight += field_weights['display_name']
    if user.avatar_url:
        completed_weight += field_weights['avatar_url']
    if user.phone:
        completed_weight += field_weights['phone']
    if user.job_title:
        completed_weight += field_weights['job_title']
    if user.company:
        completed_weight += field_weights['company']
    if user.departments and len(user.departments) > 0:
        completed_weight += field_weights['departments']
    if user.timezone != 'UTC':  # Not default
        completed_weight += field_weights['timezone']
    if user.locale != 'en-US':  # Not default
        completed_weight += field_weights['locale']
    if user.notification_preferences and len(user.notification_preferences) > 0:
        completed_weight += field_weights['notification_preferences']
    if user.ui_preferences and len(user.ui_preferences) > 0:
        completed_weight += field_weights['ui_preferences']
    
    return int((completed_weight / total_weight) * 100)
```

### 6. Keycloak Sync (Optional Enhancement)

If we decide to sync to Keycloak for SSO purposes:

```python
async def sync_user_attributes_to_keycloak(
    user_id: str,
    attributes: dict
) -> bool:
    """Sync user attributes to Keycloak."""
    
    keycloak_client = get_keycloak_client()
    
    # Attributes to sync
    keycloak_attributes = {
        'is_onboarding_completed': str(attributes.get('is_onboarding_completed', False)),
        'profile_completion': str(attributes.get('profile_completion_percentage', 0)),
        'job_title': attributes.get('job_title', ''),
        'company': attributes.get('company', ''),
        'departments': json.dumps(attributes.get('departments', [])),
        'timezone': attributes.get('timezone', 'UTC'),
        'locale': attributes.get('locale', 'en-US')
    }
    
    try:
        # Update user attributes in Keycloak
        await keycloak_client.update_user_attributes(
            user_id=user_id,
            attributes=keycloak_attributes
        )
        return True
    except Exception as e:
        logger.error(f"Failed to sync attributes to Keycloak: {e}")
        # Don't fail the operation, just log
        return False
```

## Implementation Steps

### Phase 1: Backend Implementation (Priority 1)
1. ✅ Database schema already has required fields
2. Update `/auth/login` endpoint to return full user data
3. Update `/auth/me` endpoint to return comprehensive user profile
4. Create profile update endpoints (`/users/me/profile`)
5. Create onboarding status endpoints
6. Implement profile completion calculation
7. Add caching for user data (Redis with 5-minute TTL)

### Phase 2: Frontend Integration (Priority 2)
1. Update auth store to handle full user data
2. Create onboarding flow components
3. Implement profile completion UI
4. Add onboarding status checks on protected routes
5. Cache user data in localStorage/sessionStorage

### Phase 3: Keycloak Sync (Optional, Priority 3)
1. Create Keycloak attribute mapper configuration
2. Implement async sync service
3. Add sync triggers on profile updates
4. Handle sync failures gracefully
5. Add monitoring for sync status

## Frontend Implementation Guide

### State Management (Zustand/Redux)
```typescript
interface UserState {
  user: User | null;
  isOnboardingCompleted: boolean;
  profileCompletionPercentage: number;
  onboardingSteps: OnboardingSteps;
  
  // Actions
  setUser: (user: User) => void;
  updateProfile: (data: Partial<User>) => Promise<void>;
  completeOnboarding: (steps: string[]) => Promise<void>;
  refreshUser: () => Promise<void>;
}
```

### Route Guards
```typescript
const RequireOnboarding: React.FC = ({ children }) => {
  const { user, isOnboardingCompleted } = useUserStore();
  const navigate = useNavigate();
  
  useEffect(() => {
    if (user && !isOnboardingCompleted) {
      navigate('/onboarding');
    }
  }, [user, isOnboardingCompleted]);
  
  return isOnboardingCompleted ? children : null;
};
```

### API Client
```typescript
class AuthAPI {
  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    const response = await api.post('/auth/login', credentials);
    // Store full user data
    userStore.setUser(response.data.user);
    // Store tokens
    tokenStore.setTokens(response.data.access_token, response.data.refresh_token);
    return response.data;
  }
  
  async getCurrentUser(): Promise<User> {
    const response = await api.get('/auth/me');
    userStore.setUser(response.data);
    return response.data;
  }
  
  async updateProfile(data: Partial<User>): Promise<User> {
    const response = await api.put('/users/me/profile', data);
    userStore.setUser(response.data);
    return response.data;
  }
}
```

## Security Considerations

1. **Token Security**: Never store sensitive user data in JWT tokens
2. **Cache Invalidation**: Clear user cache on logout and role changes
3. **Data Validation**: Validate all profile updates on backend
4. **Rate Limiting**: Limit profile update requests to prevent abuse
5. **Audit Logging**: Log all profile and onboarding status changes

## Performance Considerations

1. **Caching Strategy**:
   - Cache user data in Redis with 5-minute TTL
   - Cache in frontend state and localStorage
   - Invalidate on any user data changes

2. **Query Optimization**:
   - Use single query with JOINs to fetch user + roles + permissions
   - Create indexes on frequently queried fields
   - Use connection pooling for database

3. **Response Size**:
   - Only include necessary fields in responses
   - Paginate large arrays (tenant_memberships)
   - Use compression for API responses

## Migration Requirements

1. **Existing Users**: Set `is_onboarding_completed = true` for existing users
2. **Profile Completion**: Calculate initial percentage for all users
3. **Default Values**: Ensure all JSONB fields have proper defaults

## Success Metrics

1. **Onboarding Completion Rate**: % of users completing onboarding
2. **Profile Completion**: Average profile completion percentage
3. **Time to Complete**: Average time to complete onboarding
4. **Drop-off Points**: Identify where users abandon onboarding

## Timeline

- **Week 1**: Backend implementation (Phase 1)
- **Week 2**: Frontend integration (Phase 2)
- **Week 3**: Testing and refinement
- **Week 4**: (Optional) Keycloak sync implementation

## Decision Required

**Question**: Should we sync onboarding status to Keycloak?

**Recommendation**: Start with database-only approach (simpler, faster to implement). Add Keycloak sync later if needed for SSO scenarios where other services need onboarding status without hitting our API.

## Next Steps

1. Review and approve this plan
2. Implement backend changes to `/auth/login` and `/auth/me`
3. Create profile update endpoints
4. Update frontend to handle full user data
5. Implement onboarding flow UI