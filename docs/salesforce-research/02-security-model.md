# Salesforce Security Model Capabilities

## Overview
Comprehensive analysis of Salesforce security features for migrating Orienteer's role-based access control and security model.

## Salesforce Security Layers

Salesforce implements a layered security model with multiple levels of access control:

```
Organization Level (IP restrictions, login hours)
    ↓
User Authentication (Passwords, MFA, SSO)
    ↓
Object-Level Security (Profiles, Permission Sets)
    ↓
Record-Level Security (OWD, Sharing Rules, Manual Sharing)
    ↓
Field-Level Security (FLS per profile/permission set)
    ↓
Feature-Level Security (Permissions, Settings)
```

## User Authentication

### Authentication Methods

#### 1. Username and Password
- **Standard Auth**: Username (email-based) + password
- **Password Policies**:
  - Minimum length: 8-25 characters (configurable)
  - Complexity requirements: Letters, numbers, special chars
  - Password expiration: 30, 60, 90 days, or never
  - Password history: Prevent reuse of last 3-24 passwords
  - Login attempt limits: Lockout after N failed attempts
  - Session timeout: 15 mins to 24 hours

#### 2. Multi-Factor Authentication (MFA)
- **Required**: For all Salesforce orgs (as of Feb 2022)
- **Methods**:
  - Salesforce Authenticator mobile app
  - Third-party TOTP apps (Google Authenticator, etc.)
  - Security keys (FIDO2/WebAuthn)
  - Built-in authenticator
- **Configuration**: Per user or enforced org-wide
- **API Access**: App-specific passwords or connected app OAuth

#### 3. Single Sign-On (SSO)
- **SAML 2.0**: Industry standard for SSO
- **Identity Providers**: Okta, Azure AD, Ping Identity, etc.
- **Just-in-Time (JIT) Provisioning**: Auto-create users on first login
- **My Domain**: Required for SSO configuration
- **Federation**: Both SAML and OAuth 2.0 supported

#### 4. Social Login
- **OAuth 2.0**: Login with Facebook, Google, LinkedIn, etc.
- **External Identity**: Link to external identity providers
- **Custom Authentication**: Build custom auth flows with Apex

### Session Management
- **Session Security**:
  - Session timeout (configurable)
  - IP address restrictions
  - Session invalidation on logout
  - Cross-site scripting (XSS) protection
  - Clickjacking protection

- **Session Settings**:
  - Lock sessions to IP address
  - Require HttpOnly attribute
  - Enable caching and autocomplete
  - Enforce login IP ranges
  - Require secure connections (HTTPS)

## Profiles and Permission Sets

### Profiles
**Definition**: Define a user's baseline permissions and settings.

**Components**:
- Object permissions (CRUD)
- Field-level security
- Record type visibility
- Page layout assignments
- Tab visibility
- App visibility
- Administrative permissions
- General user permissions
- Apex class access
- Visualforce page access

**Standard Profiles**:
- System Administrator (full access)
- Standard User (read/create/edit on most objects)
- Read Only (view-only access)
- Standard Platform User (custom app access)
- Minimum Access - Salesforce (limited access)
- Contract Manager, Marketing User, Solution Manager (role-specific)

**Custom Profiles**:
- Clone from standard profile
- Customize permissions
- Up to 1000 custom profiles per org
- Cannot be deleted if assigned to users

### Permission Sets
**Definition**: Extend user permissions beyond their profile.

**Advantages**:
- Additive only (grant permissions, not remove)
- Assign multiple permission sets to one user
- Easier to manage than creating many profiles
- Group-based assignment (Permission Set Groups)
- Time-based assignments (Muting Permission Sets)

**Use Cases**:
- Temporary elevated access
- Role-specific permissions
- Feature-specific access
- Project-based permissions

**Components**: Same as profiles, but additive
- Object permissions
- Field permissions
- App access
- Custom permissions
- Apex class/Visualforce page access

### Permission Set Groups
- **Bundling**: Group multiple permission sets together
- **Muting**: Temporarily disable permissions in a group
- **Management**: Easier permission management at scale
- **Delegation**: Assign groups instead of individual permission sets

## Object-Level Security

### Object Permissions (CRUD)
Controlled via Profiles and Permission Sets:

| Permission | Description | Impact |
|-----------|-------------|--------|
| Read | View records | Can see object and records (subject to sharing) |
| Create | Insert new records | Can create new records |
| Edit | Modify existing records | Can update records they can view |
| Delete | Remove records | Can delete records they can edit |
| View All | See all records | Bypasses sharing rules (admin) |
| Modify All | Edit all records | Bypasses sharing rules (admin) |

**Special Permissions**:
- View All Data: See all records in all objects
- Modify All Data: Edit all records in all objects
- Delete All Data: Remove all records (destructive)

**Granularity**: Per object (Standard and Custom)

**OrientDB Mapping**:
- OrientDB: Class-level CRUD permissions via roles
- Salesforce: Object-level CRUD via profiles/permission sets
- **Compatibility**: Strong alignment, direct mapping possible

## Record-Level Security (Sharing)

### Organization-Wide Defaults (OWD)

**Definition**: Baseline record access for all objects.

**Sharing Models**:

| Model | Description | Use Case |
|-------|-------------|----------|
| Private | Only owner and above in hierarchy | Confidential data |
| Public Read Only | All users can view, only owner can edit | Reference data |
| Public Read/Write | All users can view and edit | Collaborative data |
| Controlled by Parent | Inherits from parent (master-detail) | Child records |
| Public Read/Write/Transfer | All users can change ownership | - |
| Public Full Access | All users have full control | Open access data |

**Hierarchy Override**: Users above in role hierarchy can access records below them
- Grant Access Using Hierarchies: Enabled by default
- Can be disabled per object

### Role Hierarchy
**Purpose**: Organizational structure for record access.

**Characteristics**:
- Tree structure (not DAG)
- Users higher in hierarchy can access records of users below
- Maximum depth: 500 levels (recommended: 10-15)
- Optional per object (can disable hierarchy access)

**Comparison to Orienteer**:
- Orienteer: Role-based with inheritance
- Salesforce: Role hierarchy + role-based
- **Difference**: Salesforce role hierarchy is organizational, not permission-based

### Sharing Rules
**Purpose**: Open up record access beyond OWD.

**Types**:

#### 1. Ownership-Based Sharing Rules
- Share records owned by users/roles with other users/roles/groups
- Example: Share all opportunities owned by Sales team with Sales Managers

#### 2. Criteria-Based Sharing Rules
- Share records matching criteria with users/roles/groups
- Example: Share all accounts in California with West Coast team
- Maximum 50 criteria-based sharing rules per object

#### 3. Manual Sharing
- User-initiated sharing of individual records
- Share with users, roles, groups
- Access level: Read Only or Read/Write
- Can be revoked by sharer or record owner

#### 4. Apex Managed Sharing
- Programmatic sharing via Apex code
- Create/delete sharing records (Share objects)
- Custom sharing logic
- Example: Share record with users from related records

**Limitations**:
- Sharing rules can only grant access, not restrict
- Maximum 300 sharing rules per object (total across types)
- Recalculation time for large data volumes

### Territory Management
**Purpose**: Geographic or account-based record assignment.

**Enterprise Territory Management**:
- Hierarchical territory structure
- Assignment rules for automatic record assignment
- Sharing rules based on territory membership
- Territory-based forecasting

**Use Cases**:
- Sales territory management
- Geographic-based access
- Account segmentation

## Field-Level Security (FLS)

### Definition
Control visibility and editability of fields on a per-profile/permission set basis.

### Access Levels
- **Visible**: Field is visible to user (read access)
- **Read-Only**: User can see but not edit field
- **Hidden**: Field is completely hidden from user
- **Editable**: User can view and modify field (requires visible)

### Configuration Methods
1. **Profile/Permission Set**: Field-level security settings
2. **Page Layouts**: Control field visibility on layouts (UI only, not API)
3. **Record Types**: Different page layouts per record type

### Behavior
- **API Access**: FLS applies to API access
- **Reports**: Hidden fields cannot be added to reports
- **Formulas**: Can reference fields users cannot see
- **Validation Rules**: Apply even if user cannot see field
- **Workflow/Process**: Can update hidden fields

### OrientDB Mapping
- OrientDB: Property-level security per role
- Salesforce: Field-level security per profile/permission set
- **Compatibility**: Strong alignment for property-level security

## Comparison to Orienteer Security Model

### Orienteer Security Architecture

Based on analysis of requirements and OrientDB security:

1. **Role-Based Access Control (RBAC)**
   - Roles with hierarchical inheritance
   - Users can have multiple roles
   - Permissions at database, class, document, property levels

2. **Permission Levels**
   - Database: CREATE, READ, UPDATE, DELETE, EXECUTE
   - Class: Access to specific data types
   - Document: Row-level security
   - Property: Field-level security

3. **Dynamic Permissions**
   - Runtime permission evaluation
   - Custom permission logic
   - Function-level permissions

### Mapping Analysis

| Orienteer Feature | Salesforce Equivalent | Compatibility |
|------------------|----------------------|---------------|
| **User** | User | ✅ Direct mapping |
| **Role** | Profile + Permission Sets | ✅ Combined approach |
| **Role Inheritance** | Permission Sets | ⚠️ Partial - no hierarchy in permission sets |
| **Multiple Roles per User** | Multiple Permission Sets | ✅ Direct mapping |
| **Database-level permissions** | Organization-wide settings | ⚠️ Limited granularity |
| **Class-level permissions** | Object permissions (CRUD) | ✅ Direct mapping |
| **Document-level permissions** | OWD + Sharing Rules | ✅ Good mapping |
| **Property-level permissions** | Field-Level Security | ✅ Direct mapping |
| **Function-level permissions** | Apex Class permissions | ⚠️ Different model |
| **Dynamic permission evaluation** | Sharing Rules + Apex | ⚠️ More complex |

### Migration Strategy

#### 1. User Migration
- **Approach**: One-to-one user migration
- **Authentication**: Configure SSO if Orienteer uses external auth
- **Password Reset**: Force password reset on first login
- **MFA**: Enable MFA for all users

#### 2. Role to Profile/Permission Set Migration

**Strategy A: Profile-Heavy**
- Create custom profile per Orienteer role
- Use permission sets for additional permissions
- **Pros**: Clear role mapping, simpler to understand
- **Cons**: More profiles to maintain, less flexible

**Strategy B: Permission Set-Heavy**
- Use standard profiles (System Admin, Standard User, etc.)
- Create permission set per Orienteer role
- Assign multiple permission sets per user
- **Pros**: More flexible, easier to modify
- **Cons**: Complex permission combinations

**Recommended**: **Strategy B** (Permission Set-Heavy)
- Aligns with Salesforce best practices
- Easier to manage multiple role assignments
- More flexible for future changes

#### 3. Permission Mapping

**Class-level (OrientDB) → Object-level (Salesforce)**:
```
OrientDB OClass Permission → Salesforce Object Permission
CREATE → Create
READ → Read
UPDATE → Edit
DELETE → Delete
EXECUTE → Custom Permission or Apex Class Access
```

**Document-level → Record-level**:
```
OrientDB Document Security → Salesforce Sharing
Private → OWD: Private + Sharing Rules
Public Read → OWD: Public Read Only
Public Write → OWD: Public Read/Write
Custom Rules → Criteria-Based Sharing Rules
```

**Property-level → Field-level**:
```
OrientDB Property Security → Salesforce FLS
Hidden → FLS: Not Visible
Read-Only → FLS: Visible, Not Editable
Read/Write → FLS: Visible, Editable
```

#### 4. Hierarchical Roles

**Challenge**: OrientDB supports role inheritance, Salesforce does not for permission sets.

**Solutions**:
1. **Flatten Hierarchy**: Create permission sets with accumulated permissions
2. **Permission Set Groups**: Bundle related permission sets
3. **Role Hierarchy**: Use Salesforce role hierarchy for organizational structure
4. **Combination**: Use both approaches - org structure via roles, permissions via permission sets

**Example**:
```
OrientDB Role Hierarchy:
  Admin (has all Manager + Admin permissions)
    ├─ Manager (has all User + Manager permissions)
    │   └─ User (base permissions)

Salesforce Mapping:
  Profile: Standard User (base)
  Permission Sets:
    - User_Permissions (base permissions)
    - Manager_Permissions (includes User_Permissions)
    - Admin_Permissions (includes Manager_Permissions)

  OR

  Permission Set Group: Admin_Access
    - User_Permissions
    - Manager_Permissions
    - Admin_Permissions
```

## Advanced Security Features

### Platform Encryption
- **Field Encryption**: Encrypt sensitive field data at rest
- **Encryption at Rest**: Shield Platform Encryption
- **Key Management**: Customer-managed encryption keys
- **Searchability**: Deterministic vs. Probabilistic encryption
- **Use Cases**: PII, PHI, PCI compliance

### Event Monitoring
- **Login History**: Track all login attempts
- **Field History**: Track field value changes
- **Setup Audit Trail**: Track configuration changes
- **API Usage**: Monitor API calls and limits
- **Real-time Events**: Platform Events for security monitoring

### Security Health Check
- **Risk Assessment**: Automatically assess security settings
- **Best Practices**: Compare against Salesforce baseline
- **Compliance**: Meet industry standards
- **Remediation**: Guided steps to improve security

### Shield
**Components**:
1. **Shield Platform Encryption**: Encrypt data at rest
2. **Shield Event Monitoring**: Advanced audit trail
3. **Shield Field Audit Trail**: Extended field history (10 years)

## Governor Limits Impact on Security

### Sharing Recalculation
- **Trigger**: Changes to sharing rules, role hierarchy, OWD
- **Performance**: Can take hours for large data volumes
- **Limits**: Background jobs for recalculation
- **Best Practice**: Schedule sharing recalculation during off-hours

### Permission Set Assignments
- **Limits**:
  - 1000 permission sets per org
  - 1000 permission set groups per org
  - Unlimited permission sets per user (practical limit ~50)
- **Performance**: Large numbers of permission sets can slow login

### Sharing Rules
- **Limits**:
  - 300 sharing rules per object (total)
  - 50 criteria-based sharing rules per object
  - Share objects created for each sharing rule
- **Performance**: Complex sharing rules slow queries

## Migration Recommendations

### Pre-Migration Assessment
1. **Audit Orienteer Roles**: Document all roles and their permissions
2. **Map Permissions**: Create mapping matrix (Orienteer → Salesforce)
3. **Identify Gaps**: Note custom security logic requiring Apex
4. **User Count**: Estimate Salesforce license requirements
5. **Security Policies**: Document password policies, MFA requirements, IP restrictions

### Migration Approach

#### Phase 1: Foundation
1. **Configure Organization Security**:
   - Set password policies
   - Enable MFA
   - Configure IP restrictions
   - Set session settings
   - Configure login hours

2. **Create Base Profiles**:
   - Clone standard profiles
   - Set object permissions
   - Configure application access
   - Set administrative permissions

3. **Define Permission Sets**:
   - Create permission set per Orienteer role
   - Set object permissions
   - Configure field-level security
   - Add custom permissions

#### Phase 2: Object and Field Security
1. **Set Organization-Wide Defaults**:
   - Determine sharing model per object
   - Configure hierarchy access
   - Document exceptions

2. **Create Sharing Rules**:
   - Ownership-based sharing rules
   - Criteria-based sharing rules
   - Test sharing logic

3. **Configure Field-Level Security**:
   - Set FLS per profile/permission set
   - Match Orienteer property security
   - Validate API access

#### Phase 3: User Migration
1. **Prepare User Data**:
   - Extract Orienteer users
   - Map roles to permission sets
   - Assign profiles

2. **Load Users**:
   - Create Salesforce users
   - Assign profiles
   - Assign permission sets
   - Set role hierarchy

3. **Configure Authentication**:
   - Setup SSO (if applicable)
   - Configure MFA
   - Set password reset flow

#### Phase 4: Testing and Validation
1. **Security Testing**:
   - Test object access per role
   - Verify record-level access
   - Validate field visibility
   - Test API access

2. **User Acceptance Testing**:
   - Test with sample users from each role
   - Verify access patterns match Orienteer
   - Document access issues

3. **Performance Testing**:
   - Test login performance
   - Measure sharing recalculation time
   - Validate query performance with sharing

#### Phase 5: Production Deployment
1. **Deploy Security Configuration**:
   - Metadata deployment (profiles, permission sets, sharing rules)
   - Change sets or Salesforce DX
   - Document deployment

2. **User Training**:
   - Train on Salesforce security model
   - Document permission assignments
   - Provide self-service documentation

3. **Monitoring**:
   - Setup login monitoring
   - Track permission changes
   - Monitor sharing recalculation

### Custom Security Logic

For Orienteer security features not directly supported:

#### Apex Managed Sharing
```apex
// Example: Share records based on custom criteria
public class CustomSharingService {
    public static void shareRecords(List<Id> recordIds, Id userId) {
        List<MyObject__Share> shares = new List<MyObject__Share>();

        for(Id recordId : recordIds) {
            MyObject__Share share = new MyObject__Share();
            share.ParentId = recordId;
            share.UserOrGroupId = userId;
            share.AccessLevel = 'Edit';
            share.RowCause = Schema.MyObject__Share.RowCause.Manual;
            shares.add(share);
        }

        Database.insert(shares, false);
    }
}
```

#### Dynamic Permission Checks
```apex
// Example: Check object and field permissions at runtime
public class PermissionService {
    public static Boolean canAccessField(String objectName, String fieldName) {
        Schema.DescribeFieldResult fieldDescribe =
            Schema.getGlobalDescribe()
                  .get(objectName)
                  .getDescribe()
                  .fields
                  .getMap()
                  .get(fieldName)
                  .getDescribe();

        return fieldDescribe.isAccessible();
    }

    public static Boolean canEditRecord(SObject record) {
        return record.getSObjectType().getDescribe().isUpdateable();
    }
}
```

## Key Takeaways

### Strengths of Salesforce Security
1. ✅ **Comprehensive**: Multi-layered security model
2. ✅ **Flexible**: Profiles + Permission Sets provide granular control
3. ✅ **Scalable**: Handles large user bases effectively
4. ✅ **Compliant**: Meets enterprise security standards
5. ✅ **Auditable**: Extensive audit trail capabilities

### Limitations vs. Orienteer
1. ⚠️ **No Permission Set Hierarchy**: Need to flatten or use groups
2. ⚠️ **Sharing Complexity**: Complex sharing rules can impact performance
3. ⚠️ **Dynamic Permissions**: Requires custom Apex code
4. ⚠️ **Schema-Level Security**: Less dynamic than OrientDB
5. ⚠️ **Custom Logic**: Some security patterns require development

### Migration Complexity: **Medium**
- Core security features map well to Salesforce
- Permission set model flexible enough for multiple roles
- Custom security logic requires Apex development
- Sharing rules cover most document-level security needs
- Field-level security directly supported

### Recommended Approach
1. Use **Permission Sets** as primary role mapping
2. Leverage **Sharing Rules** for record-level security
3. Implement **Apex Managed Sharing** for complex scenarios
4. Use **Field-Level Security** for property-level control
5. **Document** all security mappings for audit and maintenance
