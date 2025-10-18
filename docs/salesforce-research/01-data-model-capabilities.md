# Salesforce Data Model Capabilities

## Overview
Analysis of Salesforce platform data modeling capabilities for migrating Orienteer Business Application Platform.

## Custom Objects and Fields

### Custom Object Capabilities
- **Creation**: Unlimited custom objects in Developer/Enterprise editions
- **Naming**: API name (up to 40 chars) and Label (user-friendly display name)
- **Metadata**: Description, Record Name format, deployment settings
- **Organization**: Tab creation, app integration, search optimization
- **Limits**: 200-2000 custom objects depending on Salesforce edition

### Field Data Types

| Salesforce Type | Description | Max Size | OrientDB Equivalent |
|----------------|-------------|----------|---------------------|
| Text | Short text field | 255 chars | STRING |
| Text Area (Long) | Multi-line text | 131,072 chars | STRING (large) |
| Rich Text Area | HTML formatted text | 131,072 chars | STRING (HTML) |
| Number | Integer or decimal | 18 digits | INTEGER, DECIMAL |
| Currency | Currency with precision | 18 digits | DECIMAL |
| Percent | Percentage value | 18 digits | DECIMAL |
| Date | Date only | - | DATE |
| Date/Time | Date with time | - | DATETIME |
| Checkbox | Boolean value | - | BOOLEAN |
| Picklist | Single selection | 1000 values | STRING (enum) |
| Multi-Select Picklist | Multiple selections | 4096 chars | EMBEDDEDLIST |
| Lookup Relationship | Reference to record | - | LINK |
| Master-Detail | Strong reference | - | LINK (cascade) |
| Email | Email address | 80 chars | STRING (email) |
| Phone | Phone number | 40 chars | STRING (phone) |
| URL | Web address | 255 chars | STRING (url) |
| Formula | Calculated field | Varies | Computed |
| Roll-Up Summary | Aggregate calculation | - | Computed |
| Auto-Number | Sequential number | - | INTEGER (auto) |
| Geolocation | Lat/Long coordinates | - | Custom |
| Text Area | Multi-line text | 255 chars | STRING |
| External Lookup | External ID reference | - | LINK (external) |

### Field Properties and Constraints
- **Required**: Field must have a value (enforced on UI and API)
- **Unique**: Ensures no duplicate values across records
- **External ID**: Marked for external system integration
- **Default Value**: Static or formula-based default
- **Help Text**: Inline help for users
- **Field-Level Security**: Permission-based field visibility
- **Track Field History**: Audit trail for field changes (up to 20 fields per object)
- **Min/Max Length**: For text fields
- **Min/Max Value**: For numeric fields
- **Validation Rules**: Cross-field validation formulas

## Relationship Types

### 1. Lookup Relationship
**Characteristics**:
- One-to-many relationship
- Loosely coupled - child can exist without parent
- No cascade delete (configurable)
- Up to 40 lookup relationships per object
- Can be optional or required

**Use Cases**:
- Account → Contact (optional)
- Case → Account (required)
- Document → Category (optional)

**OrientDB Mapping**: LINK with cascade=false

### 2. Master-Detail Relationship
**Characteristics**:
- Tightly coupled parent-child relationship
- Child cannot exist without parent
- Cascade delete when parent is deleted
- Sharing rules inherited from parent
- Roll-up summary fields supported
- Up to 2 master-detail per object (3 in some cases)

**Use Cases**:
- Order → Order Line Items
- Opportunity → Opportunity Products
- Invoice → Invoice Line Items

**OrientDB Mapping**: LINK with cascade=true

### 3. Many-to-Many Relationship
**Implementation**: Junction object with two master-detail relationships

**Example**:
```
Student ← (Student_Course__c) → Course
         [Junction Object with 2 Master-Details]
```

**Characteristics**:
- Requires intermediate junction object
- Both parent records can have multiple children
- Cascade delete from both parents
- Supports additional fields on junction

**OrientDB Mapping**: LINKSET/LINKLIST with bidirectional links

### 4. Hierarchical Relationship
**Characteristics**:
- Lookup relationship to same object
- Special UI for hierarchy display
- Limited to specific standard objects (User, Account, etc.)
- Custom objects need custom hierarchy implementation

**OrientDB Mapping**: LINK to same OClass

### 5. External Lookup Relationship
**Characteristics**:
- Links to external data sources (Salesforce Connect)
- Read-only in most cases
- No referential integrity enforcement
- Useful for integration scenarios

**OrientDB Mapping**: Custom integration pattern

## Schema Management

### Schema Design Tools

#### 1. Setup UI (Point-and-Click)
- **Schema Builder**: Visual drag-and-drop interface
  - View object relationships graphically
  - Create objects and fields visually
  - Define relationships with visual connectors
  - Export schema diagrams

- **Object Manager**: Detailed object configuration
  - Field management
  - Relationship configuration
  - Validation rules
  - Triggers and automation
  - Page layouts

#### 2. Metadata API
- **Capabilities**:
  - Programmatic schema deployment
  - XML-based schema definitions
  - Version control friendly
  - CI/CD integration
  - Bulk operations

- **Deployment Methods**:
  - Change Sets (UI-based)
  - Ant Migration Tool
  - Salesforce DX (modern approach)
  - VS Code Extensions

#### 3. Salesforce DX
- **Features**:
  - Source-driven development
  - Scratch orgs for development
  - Version control integration (Git)
  - Modular development
  - Continuous integration support

### Schema Evolution

#### Adding Fields
- ✅ **Easy**: Add new fields to objects
- ✅ **Safe**: Non-breaking change
- ⚠️ **Consider**: Field-level security, page layouts, existing queries

#### Modifying Fields
- ✅ **Allowed**:
  - Increase text field length
  - Change Text to Text Area or Email/Phone/URL
  - Change Number precision
  - Change Picklist values (add new)

- ❌ **Not Allowed**:
  - Change field type in most cases
  - Decrease text field length (with data)
  - Change from Master-Detail to Lookup (vice versa requires workaround)

#### Deleting Fields
- ⚠️ **Process**:
  1. Check dependencies (reports, workflows, code)
  2. Remove field from page layouts
  3. Delete field (moves to "Deleted Fields" for 15 days)
  4. Permanent deletion after 15 days or manual purge

- ❌ **Blocked by**:
  - Formula fields referencing it
  - Validation rules using it
  - Workflow rules
  - Process Builder/Flow references
  - Apex code references

### Dynamic Schema Capabilities

**Runtime Schema Modification**:
- ✅ **Via Metadata API**: Deploy schema changes programmatically
- ✅ **Via Tooling API**: Create/modify fields and objects
- ⚠️ **Limitations**:
  - Cannot be done in active transaction
  - Requires special permissions
  - Governor limits apply (API calls)
  - Production changes require deployment

**Comparison to OrientDB**:
- OrientDB: Highly dynamic, in-transaction schema changes
- Salesforce: Structured schema deployment, metadata-driven
- **Gap**: Salesforce less dynamic than OrientDB's runtime schema modification

## Indexes and Performance

### Automatic Indexes
- Primary Key (Id field)
- Foreign Keys (Lookup/Master-Detail fields)
- RecordTypeId
- SystemModstamp
- Name fields
- Owner fields

### Custom Indexes
- **Custom Index**: Created on frequently queried fields
- **External ID**: Special index for integration
- **Unique**: Enforces uniqueness with index
- **Limitations**:
  - Maximum of 500 custom indexes per org
  - Text fields limited to 254 chars for indexing
  - Some field types cannot be indexed

### Query Optimization
- **Selective Queries**: Use indexed fields in WHERE clauses
- **Skinny Tables**: Salesforce-created performance tables
- **Formula Fields**: Not indexed, impacts query performance
- **SOQL Optimization**: Use selective filters, avoid non-selective queries

## Data Validation and Business Rules

### Validation Rules
- **Formula-based**: Boolean formula that must evaluate to FALSE
- **Error Messages**: Custom error messages with field-specific placement
- **Error Location**: Display at field or page level
- **Evaluation**: On insert and update
- **Bypass**: Can be bypassed via Process Builder/Flow

**Example**:
```
AND(
  NOT(ISBLANK(Email)),
  NOT(REGEX(Email, "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,4}"))
)
Error: Invalid email format
```

### Formula Fields
- **Calculated Values**: Derived from other fields
- **Real-time**: Recalculated on record access
- **No Storage**: Not stored in database (except deterministic formulas)
- **Cross-Object**: Can reference parent object fields
- **Types**: All standard data types supported
- **Limitations**:
  - 5000 character limit
  - Cannot reference Long Text fields
  - Performance impact on large result sets

### Roll-Up Summary Fields
- **Aggregate Calculations**: COUNT, SUM, MIN, MAX
- **Master-Detail Only**: Only on parent of master-detail relationship
- **Real-time**: Updated when child records change
- **Filter Criteria**: Optional WHERE clause
- **Limitations**:
  - Cannot be changed to other field types
  - Cannot be used in Formula fields (except COUNT)
  - 25 roll-up summaries per object

## OrientDB to Salesforce Mapping

### Class to Object Mapping

| OrientDB Concept | Salesforce Equivalent | Notes |
|-----------------|----------------------|-------|
| OClass | Custom Object | One-to-one mapping |
| Abstract OClass | Custom Object (no records) | Use for shared fields, implement via lookup |
| OClass Inheritance | Lookup pattern or field duplication | No native inheritance |
| System OClass | Standard Object | If equivalent exists |

### Property to Field Mapping

| OrientDB Type | Salesforce Type | Migration Notes |
|--------------|----------------|----------------|
| STRING | Text or Text Area (Long) | Max 255 chars for Text |
| INTEGER | Number (0 decimals) | Direct mapping |
| LONG | Number (0 decimals) | Direct mapping |
| SHORT | Number (0 decimals) | Direct mapping |
| FLOAT | Number (decimal) | Direct mapping |
| DOUBLE | Number (decimal) | Direct mapping |
| DECIMAL | Currency or Number | Use Currency for money |
| DATE | Date | Direct mapping |
| DATETIME | Date/Time | Direct mapping |
| BOOLEAN | Checkbox | Direct mapping |
| LINK | Lookup or Master-Detail | Choose based on cascade needs |
| LINKLIST | Junction Object | Requires many-to-many pattern |
| LINKSET | Junction Object | Requires many-to-many pattern |
| LINKMAP | JSON field or separate object | Complex mapping |
| EMBEDDED | JSON field or child object | Flatten or serialize |
| EMBEDDEDLIST | JSON field or child records | Flatten or serialize |
| EMBEDDEDSET | JSON field | Serialize as JSON |
| EMBEDDEDMAP | JSON field | Serialize as JSON |
| BINARY | Attachment or ContentVersion | File storage pattern |
| CUSTOM | Varies | Custom implementation |

### Constraint Mapping

| OrientDB Constraint | Salesforce Constraint | Notes |
|--------------------|----------------------|-------|
| MANDATORY | Required | Direct mapping |
| NOTNULL | Required | Direct mapping |
| READONLY | Read-only field | Formula or code enforcement |
| UNIQUE | Unique | Direct mapping |
| MIN/MAX | Validation Rule | Formula-based validation |
| REGEXP | Validation Rule | REGEX formula function |

## Key Differences and Limitations

### Orienteer Features Requiring Adaptation

1. **Dynamic Schema Changes**
   - OrientDB: In-transaction schema modifications
   - Salesforce: Metadata deployment required
   - **Impact**: Need schema versioning and deployment process

2. **Graph Capabilities**
   - OrientDB: Native graph traversal (TRAVERSE, MATCH)
   - Salesforce: Standard relationships only
   - **Impact**: Graph queries need restructuring to relationship queries

3. **Embedded Documents**
   - OrientDB: Native embedded document support
   - Salesforce: No embedded documents
   - **Impact**: Flatten to fields or use JSON serialization

4. **Class Inheritance**
   - OrientDB: Multi-level inheritance
   - Salesforce: No inheritance
   - **Impact**: Denormalize or use lookup patterns

5. **Multi-Model Database**
   - OrientDB: Document, graph, object, key-value
   - Salesforce: Relational model only
   - **Impact**: Adapt data model to relational paradigm

6. **Field Type Flexibility**
   - OrientDB: Custom types, serialization
   - Salesforce: Fixed set of types
   - **Impact**: Map custom types to JSON or standard types

## Recommendations for Migration

### Data Model Strategy
1. **Map OClasses to Custom Objects** - Direct 1:1 mapping where possible
2. **Flatten Inheritance** - Denormalize inherited fields or use lookup patterns
3. **Convert Embedded to Related** - Create child objects or use JSON fields
4. **Restructure Graph Relationships** - Use Lookup/Master-Detail relationships
5. **Validate Constraints** - Implement OrientDB constraints via Salesforce validation rules

### Schema Management Strategy
1. **Version Control** - Use Salesforce DX with Git
2. **Deployment Pipeline** - Automated CI/CD for schema changes
3. **Testing** - Sandbox testing before production deployment
4. **Documentation** - Maintain data dictionary mapping OrientDB to Salesforce

### Performance Considerations
1. **Index Strategy** - Identify high-volume query patterns and create custom indexes
2. **Selective Queries** - Optimize SOQL queries to use indexed fields
3. **Relationship Depth** - Limit relationship traversal depth (max 5 levels)
4. **Data Volume** - Consider data archiving for objects over 10M records

### Migration Approach
1. **Schema First** - Deploy Salesforce schema before data migration
2. **Data Transformation** - ETL process to transform OrientDB data to Salesforce format
3. **Relationship Mapping** - Establish foreign key mappings during migration
4. **Validation** - Post-migration validation of data integrity
5. **Testing** - Comprehensive testing in sandbox environment
