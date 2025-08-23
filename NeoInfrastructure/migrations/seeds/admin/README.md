# Admin Schema Comprehensive Seed Data

This directory contains comprehensive seed files for populating the admin schema with realistic, production-like data. The files are designed to be run in dependency order and create a complete multi-tenant ecosystem.

## 📋 Seed Files Overview

### File Execution Order (Critical!)

The seed files **MUST** be executed in this exact order due to foreign key dependencies:

```bash
01_regions_and_connections.sql      # Infrastructure foundation
02_roles_and_permissions.sql        # Auth system foundation  
03_subscription_plans_and_quotas.sql # Billing foundation
04_organizations_and_tenants.sql    # Core business entities
05_tenant_management.sql            # Tenant operations
06_teams_and_advanced_users.sql     # Team structure & users
07_billing_and_monitoring.sql       # Transactions & monitoring
```

## 🗃️ Data Summary

### 01_regions_and_connections.sql
**Infrastructure & Connectivity**
- ✅ **2 Regions**: US East (Virginia), EU West (Ireland)
- ✅ **5 Database Connections**: Admin, US Shared/Analytics, EU Shared/Analytics
- ✅ **GDPR Compliance**: EU region configured for data residency
- ✅ **Multi-region Setup**: Production-ready infrastructure

### 02_roles_and_permissions.sql  
**Authentication & Authorization**
- ✅ **12 Permissions**: Platform and tenant-level permissions
- ✅ **12 Roles**: From system admin to tenant guest (hierarchical)
- ✅ **Role-Permission Mappings**: Comprehensive RBAC setup
- ✅ **Default Admin User**: Platform admin with super_admin role
- ✅ **Unified Structure**: Uses harmonized auth tables

### 03_subscription_plans_and_quotas.sql
**Subscription & Billing Foundation**
- ✅ **5 Subscription Plans**: Free, Starter, Professional, Enterprise, Custom
- ✅ **30+ Plan Quotas**: Detailed resource limits per plan
- ✅ **Pricing Tiers**: From $0 (free) to custom enterprise pricing
- ✅ **Overage Handling**: Configurable limits and overage rates
- ✅ **Feature Matrices**: Plan-specific feature enablement

### 04_organizations_and_tenants.sql
**Core Business Entities**
- ✅ **12 Additional Users**: Diverse roles across organizations
- ✅ **5 Organizations**: Different sizes, industries, and tiers
  - **TechCorp Solutions**: Medium tech company (US)
  - **StartupFlex**: Small SaaS startup (US)
  - **AI Innovate Labs**: Medium AI company (EU - GDPR)
  - **Enterprise Solutions Inc**: Large enterprise (Multi-region)
  - **Global Corp International**: Global manufacturing (Multi-region)
- ✅ **9 Tenants**: Production, staging, and specialized environments
- ✅ **Multi-region Distribution**: Proper data residency compliance
- ✅ **Realistic Metadata**: Industry-specific configurations

### 05_tenant_management.sql
**Tenant Operations & Configuration**
- ✅ **9 Tenant Subscriptions**: Linked to appropriate plans
- ✅ **Realistic Billing**: Annual/monthly cycles, discounts, trials
- ✅ **Resource Quotas**: Usage tracking for all tenants
- ✅ **Tenant Settings**: 140+ configuration settings
- ✅ **Compliance Settings**: GDPR, security, and industry-specific
- ✅ **Tenant Contacts**: Technical and administrative contacts

### 06_teams_and_advanced_users.sql
**Team Structure & Advanced User Management**
- ✅ **10 Additional Users**: Specialists across different companies
- ✅ **13 Teams**: Department-based teams with realistic structures
  - Engineering, QA, Product, Research, Security, Manufacturing, etc.
- ✅ **35+ Team Memberships**: Users assigned to appropriate teams
- ✅ **Role Assignments**: Platform, tenant, and team-level roles
- ✅ **Realistic Hierarchies**: Lead/member roles with proper permissions
- ✅ **Cross-functional Teams**: Some users on multiple teams

### 07_billing_and_monitoring.sql
**Transactions & Operations**
- ✅ **11 Invoices**: Historical billing with line items
- ✅ **25+ Invoice Line Items**: Detailed billing breakdowns
- ✅ **11 Payment Transactions**: Multiple payment methods
- ✅ **8 System Alerts**: Performance, security, infrastructure alerts  
- ✅ **17 API Rate Limits**: Role-based API access controls
- ✅ **Realistic Financial Data**: Proper tax calculations, discounts

## 📊 Final Data Statistics

| Entity Type | Count | Details |
|-------------|-------|---------|
| **Regions** | 2 | US East, EU West |
| **Database Connections** | 5 | Multi-region setup |
| **Users** | 22 | Including admin and diverse roles |
| **Organizations** | 5 | Different sizes and industries |
| **Tenants** | 9 | Prod/staging/specialized environments |
| **Subscription Plans** | 5 | Free to enterprise custom |
| **Plan Quotas** | 30 | Detailed resource limits |
| **Tenant Subscriptions** | 9 | Active billing relationships |
| **Teams** | 13 | Department and functional teams |
| **Team Members** | 35+ | Realistic team assignments |
| **Roles** | 12 | Hierarchical RBAC system |
| **Permissions** | 12 | Platform and tenant permissions |
| **User Roles** | 19 | Role assignments with scoping |
| **Tenant Settings** | 140+ | Comprehensive configuration |
| **Invoices** | 11 | Historical billing data |
| **Payment Transactions** | 11 | Multiple payment methods |
| **System Alerts** | 8 | Operational monitoring |
| **API Rate Limits** | 17 | User-specific API access |

## 🌍 Multi-Tenant Ecosystem Features

### Geographic Distribution
- **US East Region**: TechCorp, StartupFlex, Enterprise US, Global Corp US
- **EU West Region**: AI Innovate, Enterprise EU, Global Corp EU
- **GDPR Compliance**: Automatic data residency for EU tenants

### Industry Diversity
- **Technology/SaaS**: TechCorp, StartupFlex
- **AI/Machine Learning**: AI Innovate Labs
- **Enterprise Software**: Enterprise Solutions
- **Manufacturing**: Global Corp International

### Organization Tiers
- **Growth Tier**: TechCorp (Professional plans)
- **Standard Tier**: StartupFlex (Starter plans) 
- **Enterprise Tier**: Enterprise Solutions, Global Corp (Enterprise/Custom plans)

### Realistic Usage Patterns
- **Development Environments**: Staging tenants with appropriate settings
- **Production Workloads**: Full-featured production tenants
- **Research Environments**: Specialized ML/AI configurations
- **Compliance-Heavy**: Manufacturing and enterprise with audit requirements

## 🚀 Usage Instructions

### Running All Seed Files
```bash
# Run with deployment script (recommended)
./deploy.sh --seed

# Or run manually in order
for file in 01_regions_and_connections.sql 02_roles_and_permissions.sql 03_subscription_plans_and_quotas.sql 04_organizations_and_tenants.sql 05_tenant_management.sql 06_teams_and_advanced_users.sql 07_billing_and_monitoring.sql; do
    docker exec -i neo-postgres-us-east psql -U postgres -d neofast_admin < "migrations/seeds/admin/$file"
done
```

### Verification Queries
Each seed file includes verification queries that show:
- Data counts and summaries
- Relationship integrity
- Business logic validation
- Sample data for testing

## 🎯 Benefits for Development & Testing

### Realistic Test Environment
- **Complete multi-tenant ecosystem** ready for testing
- **Real-world data patterns** for performance testing
- **Compliance scenarios** for regulatory testing
- **Financial workflows** for billing system testing

### Development Productivity
- **No manual data creation** needed for development
- **Consistent test data** across team members
- **Edge cases covered** (trials, discounts, overages, alerts)
- **Multi-region scenarios** for geographic testing

### Quality Assurance
- **Comprehensive user roles** for permission testing
- **Various organization types** for feature testing
- **Historical data** for reporting and analytics testing
- **Alert scenarios** for monitoring system testing

## 🔧 Customization

### Adding New Organizations
1. Add users in `04_organizations_and_tenants.sql`
2. Create organization entry with proper contact references
3. Add tenants for the organization
4. Configure subscriptions in `05_tenant_management.sql`
5. Set up teams in `06_teams_and_advanced_users.sql`

### Modifying Subscription Plans
1. Update plan definitions in `03_subscription_plans_and_quotas.sql`
2. Adjust quotas for new limits
3. Update tenant subscriptions in `05_tenant_management.sql`
4. Regenerate invoices in `07_billing_and_monitoring.sql`

### Adding New Regions
1. Add region in `01_regions_and_connections.sql`
2. Configure database connections
3. Update tenants to use new region in `04_organizations_and_tenants.sql`

---

**This comprehensive seed dataset provides a production-ready foundation for developing, testing, and demonstrating a sophisticated multi-tenant SaaS platform.** 🎉
