# Salesforce Architecture Design
# Orienteer Business Application Platform Migration

## Document Information
- **Version**: 1.0
- **Date**: 2025-10-01
- **Status**: Architecture Design Phase
- **Migration Type**: One-time migration from OrientDB to Salesforce

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Data Model Architecture](#data-model-architecture)
4. [Application Architecture](#application-architecture)
5. [Migration Architecture](#migration-architecture)
6. [Security Architecture](#security-architecture)
7. [Integration Architecture](#integration-architecture)
8. [Architecture Decision Records](#architecture-decision-records)

---

## 1. Executive Summary

### 1.1 Overview
This document defines the comprehensive Salesforce architecture for migrating the Orienteer Business Application Platform from OrientDB to Salesforce. The migration involves transforming a graph-based database platform into Salesforce's relational model while preserving core functionality.

### 1.2 Key Constraints
- **Database Size**: < 500MB OrientDB database
- **Migration Type**: One-time with expected downtime
- **Target Environment**: Clean Salesforce org (no existing data)
- **Graph Relationships**: Not required in migration (simplified data model)
- **Test Requirements**: Multiple test migrations needed for validation

### 1.3 Architecture Approach
- **Data Model**: Custom Objects with Master-Detail and Lookup relationships
- **Application**: Lightning Experience with Aura/LWC components
- **Migration**: Automated ETL pipeline using Salesforce Bulk API 2.0
- **Security**: Profiles, Permission Sets, and Sharing Rules
- **Integration**: REST APIs and Platform Events for extensibility

---

## 2. Current State Analysis

### 2.1 OrientDB Schema Analysis

#### Core Entity Classes (from OrientDB)

**System & Framework**
- `OUser` - User authentication and identity
- `ORole` - Role-based access control
- `OIdentity` - Base security class
- `ORestricted` - Document-level security

**Application Core**
- `OPerspective` - UI perspective/view definitions
- `OPerspectiveItem` - Menu items within perspectives
- `ODashboard` - Dashboard configurations
- `OWidget` - Widget instances on dashboards
- `OLocalization` - Localization/translation data
- `OModule` - Module configuration and metadata

**Task Management**
- `OTask` - Background task definitions
- `OTaskSession` - Task execution sessions
- `OConsoleTask` - Console-based tasks

#### OrientDB Schema Characteristics
- **Document-Oriented**: Flexible schema with embedded documents
- **Graph Relationships**: LINK and LINKLIST types for relationships
- **Custom Attributes**: Metadata stored on classes and properties
- **Inheritance**: Class hierarchy with extends relationships
- **Embedded Data**: EMBEDDEDMAP for localization and configuration

### 2.2 OrientDB → Salesforce Mapping Strategy

| OrientDB Feature | Salesforce Equivalent | Approach |
|------------------|----------------------|----------|
| OClass | Custom Object | Direct mapping with __c suffix |
| OProperty | Custom Field | Type conversion required |
| LINK | Lookup Relationship | Master-Detail or Lookup based on cascade |
| LINKLIST | Junction Object | Many-to-many via junction object |
| EMBEDDEDMAP | Long Text/JSON | Store as JSON text or separate child records |
| ODocument | Salesforce Record | Standard record structure |
| Graph Edges | NOT MIGRATED | Per requirements |
| Custom Attributes | Custom Metadata Types | Configuration storage |

---

## 3. Data Model Architecture

### 3.1 Custom Object Design

#### 3.1.1 Core Custom Objects

##### **Orienteer_User__c** (extends standard User)
```
Purpose: User profile and preferences (extends Salesforce User)
Type: Custom Object linked to User
Fields:
  - User__c (Lookup to User) - Master-Detail
  - Locale__c (Text 10) - User locale preference
  - Perspective__c (Lookup to Orienteer_Perspective__c)
  - Status__c (Picklist) - Active, Inactive, Locked
  - Last_Login__c (DateTime)
Indexes:
  - User__c (Unique)
Security:
  - Private sharing model
  - Profile-based access
```

##### **Orienteer_Role__c** (extends standard Permission Set)
```
Purpose: Role definitions and permissions
Type: Custom Object
Fields:
  - Name (Text 80, Required, Unique)
  - External_Id__c (Text 50) - OrientDB RID reference
  - Permission_Set__c (Lookup to PermissionSet)
  - Parent_Role__c (Lookup to Orienteer_Role__c) - Self-referencing
  - Mode__c (Picklist) - ALLOW_ALL_BUT, DENY_ALL_BUT
  - Description__c (Long Text)
Relationships:
  - Parent-Child hierarchy (self-lookup)
Security:
  - Public Read Only
  - Admin write access
```

##### **Orienteer_Perspective__c**
```
Purpose: UI perspective/view configurations
Type: Custom Object
Fields:
  - Name (Text 80, Required)
  - Alias__c (Text 50, Unique) - System identifier
  - Icon__c (Text 50) - Font Awesome class
  - Home_URL__c (URL) - Default landing page
  - Order__c (Number 5,2) - Display order
  - Active__c (Checkbox, default true)
  - Menu_JSON__c (Long Text) - Serialized menu structure
Relationships:
  - Perspective_Items__r (Child of Orienteer_Perspective_Item__c)
Indexes:
  - Alias__c (Unique)
Security:
  - Public Read Only
```

##### **Orienteer_Perspective_Item__c**
```
Purpose: Menu items within perspectives
Type: Custom Object
Fields:
  - Perspective__c (Master-Detail to Orienteer_Perspective__c, Required)
  - Name (Text 80)
  - Alias__c (Text 50)
  - Label_Key__c (Text 255) - Localization key
  - Icon__c (Text 50)
  - URL__c (URL)
  - Order__c (Number 5,2)
  - Active__c (Checkbox)
Relationships:
  - Roll-up to Perspective__c (Master-Detail)
Indexes:
  - Perspective__c + Order__c (Compound)
Security:
  - Controlled by Master (Perspective)
```

##### **Orienteer_Dashboard__c**
```
Purpose: Dashboard configurations
Type: Custom Object
Fields:
  - Name (Text 80, Required)
  - Domain__c (Text 50) - browse, view, edit
  - Tab__c (Text 50) - Tab identifier
  - Class_Name__c (Text 80) - Associated object type
  - Linked_Record__c (Text 18) - Generic record reference
  - Owner__c (Lookup to User)
  - Configuration_JSON__c (Long Text) - Dashboard settings
Relationships:
  - Widgets__r (Children Orienteer_Widget__c records)
Indexes:
  - Domain__c + Tab__c (Compound)
Security:
  - Private, share via criteria
```

##### **Orienteer_Widget__c**
```
Purpose: Widget instances on dashboards
Type: Custom Object
Fields:
  - Dashboard__c (Master-Detail to Orienteer_Dashboard__c, Required)
  - Type_Id__c (Text 80, Required) - Widget type identifier
  - Title_JSON__c (Long Text) - Localized titles
  - Column__c (Number 3,0) - Grid column position
  - Row__c (Number 3,0) - Grid row position
  - Size_X__c (Number 2,0) - Width in grid units
  - Size_Y__c (Number 2,0) - Height in grid units
  - Hidden__c (Checkbox)
  - Page_URL__c (URL) - For external widgets
  - Style__c (Text 255) - Custom CSS
  - Settings_JSON__c (Long Text) - Widget configuration
Relationships:
  - Roll-up to Dashboard__c (Master-Detail)
Security:
  - Controlled by Master (Dashboard)
```

##### **Orienteer_Localization__c**
```
Purpose: Localization strings
Type: Custom Object
Fields:
  - Key__c (Text 255, Required, Unique)
  - Language__c (Picklist) - en, es, fr, de, etc.
  - Value__c (Long Text, Required)
  - Style__c (Picklist) - default, label, hint, error
  - Active__c (Checkbox, default true)
  - Last_Modified_Date__c (DateTime, Auto)
Indexes:
  - Key__c + Language__c (Unique compound)
Custom Metadata Type Alternative:
  - Consider Orienteer_Translation__mdt for static strings
Security:
  - Public Read Only
  - Admin write access
```

##### **Orienteer_Module__c**
```
Purpose: Module configuration and metadata
Type: Custom Object
Fields:
  - Name (Text 80, Required, Unique)
  - Version__c (Number 5,0)
  - Active__c (Checkbox)
  - Description__c (Long Text)
  - Configuration_JSON__c (Long Text)
  - Install_Date__c (DateTime)
  - Dependencies_JSON__c (Long Text) - Module dependencies
Indexes:
  - Name (Unique)
Security:
  - Public Read Only
```

##### **Orienteer_Task__c**
```
Purpose: Background task definitions
Type: Custom Object
Fields:
  - Name (Text 80, Required)
  - Type__c (Picklist) - Batch, Queueable, Scheduled
  - Class_Name__c (Text 255) - Apex class name
  - Status__c (Picklist) - Pending, Running, Completed, Failed
  - Schedule_CRON__c (Text 255) - Cron expression
  - Active__c (Checkbox)
  - Configuration_JSON__c (Long Text)
Integration:
  - Link to Salesforce AsyncApexJob
Security:
  - Admin access only
```

##### **Orienteer_Task_Session__c**
```
Purpose: Task execution history
Type: Custom Object
Fields:
  - Task__c (Lookup to Orienteer_Task__c)
  - Start_Time__c (DateTime)
  - End_Time__c (DateTime)
  - Status__c (Picklist) - Running, Completed, Failed
  - Progress__c (Percent)
  - Result_JSON__c (Long Text)
  - Error_Message__c (Long Text)
  - Apex_Job_Id__c (Text 18) - AsyncApexJob ID
Relationships:
  - Lookup to Task__c
Security:
  - Admin read access
```

### 3.2 Relationship Architecture

#### 3.2.1 Master-Detail Relationships

**Master-Detail is used for:**
- Strong parent-child ownership
- Cascade delete requirements
- Roll-up summary fields
- Sharing model inheritance

```
Master-Detail Relationships:
1. Orienteer_Perspective__c → Orienteer_Perspective_Item__c
   - Cascade delete: Yes
   - Sharing: Controlled by Parent

2. Orienteer_Dashboard__c → Orienteer_Widget__c
   - Cascade delete: Yes
   - Roll-up: Widget count

3. Standard User → Orienteer_User__c (via lookup with unique constraint)
   - One-to-one relationship
   - Required field
```

#### 3.2.2 Lookup Relationships

**Lookup is used for:**
- Optional relationships
- Many-to-one without cascade
- Cross-object references

```
Lookup Relationships:
1. Orienteer_User__c.Perspective__c → Orienteer_Perspective__c
   - Optional, default perspective assignment

2. Orienteer_Role__c.Parent_Role__c → Orienteer_Role__c
   - Self-referencing hierarchy
   - Optional parent

3. Orienteer_Task_Session__c.Task__c → Orienteer_Task__c
   - Task execution history

4. Orienteer_Dashboard__c.Owner__c → User
   - Dashboard ownership
```

#### 3.2.3 Junction Objects (Many-to-Many)

**Required Junction Objects:**

##### **Orienteer_User_Role__c**
```
Purpose: User to Role assignment (many-to-many)
Fields:
  - User__c (Master-Detail to Orienteer_User__c)
  - Role__c (Master-Detail to Orienteer_Role__c)
  - Inherited__c (Checkbox) - Inherited from parent role
  - Assignment_Date__c (DateTime)
Indexes:
  - User__c + Role__c (Unique compound)
Sharing:
  - Controlled by both parents
```

### 3.3 Data Type Mapping

| OrientDB Type | Salesforce Type | Notes |
|---------------|-----------------|-------|
| STRING | Text(255) or Long Text | Length-dependent |
| INTEGER | Number(18,0) | Standard precision |
| LONG | Number(18,0) | Standard precision |
| DOUBLE | Number(16,2) | Decimal precision |
| FLOAT | Number(16,2) | Decimal precision |
| BOOLEAN | Checkbox | Direct mapping |
| DATE | Date | No time component |
| DATETIME | DateTime | Full timestamp |
| LINK | Lookup/Master-Detail | Relationship field |
| LINKLIST | Junction Object | Many-to-many |
| EMBEDDEDMAP | Long Text (JSON) | Serialized as JSON |
| EMBEDDEDSET | Long Text (JSON) | Array serialized |
| BINARY | Attachment or Files | ContentVersion |

### 3.4 Custom Metadata Types

**For static configuration (not migrated data):**

##### **Orienteer_Widget_Type__mdt**
```
Purpose: Widget type registry
Fields:
  - Type_Id__c (Text 80, Required)
  - Display_Name__c (Text 80)
  - Icon_Class__c (Text 50)
  - Aura_Component__c (Text 255)
  - LWC_Component__c (Text 255)
  - Default_Config_JSON__c (Long Text)
  - Category__c (Text 50)
```

##### **Orienteer_Custom_Attribute__mdt**
```
Purpose: Custom attribute definitions
Fields:
  - Attribute_Name__c (Text 80)
  - Data_Type__c (Picklist)
  - Default_Value__c (Text 255)
  - Scope__c (Picklist) - Class, Property, Document
```

---

## 4. Application Architecture

### 4.1 Lightning Experience Architecture

#### 4.1.1 Application Structure

```
Lightning App: Orienteer Platform
├── App Navigation
│   ├── Home
│   ├── Perspectives
│   ├── Dashboards
│   ├── Tasks
│   ├── Localization
│   ├── Modules
│   └── Administration
├── Utility Bar
│   ├── Task Monitor
│   ├── User Preferences
│   └── Help Center
└── Components
    ├── Aura Components (Legacy support)
    └── LWC Components (New development)
```

#### 4.1.2 Component Hierarchy

##### **Lightning Web Components (LWC)**

**Core Components:**

1. **orienteerDashboard** (Container)
   - Manages dashboard layout
   - Widget placement and resizing
   - Grid layout engine
   - Child: orienteerWidget

2. **orienteerWidget** (Reusable)
   - Base widget component
   - Extensible for custom widgets
   - Configuration-driven rendering
   - Types: table, chart, external, calculated

3. **orienteerPerspectiveMenu**
   - Dynamic menu rendering
   - Perspective switching
   - Responsive navigation
   - Integrates with Orienteer_Perspective__c

4. **orienteerLocalizationEditor**
   - Translation management UI
   - Multi-language support
   - Inline editing
   - Batch operations

5. **orienteerTaskMonitor**
   - Real-time task status
   - Platform Events integration
   - Progress visualization
   - Error handling

6. **orienteerDataTable** (Generic)
   - Configurable data tables
   - Sorting and filtering
   - Inline editing
   - Export capabilities

**Component Communication:**
- Lightning Message Service (LMS) for cross-component communication
- Platform Events for real-time updates
- Custom Events for parent-child communication

#### 4.1.3 Page Layouts

**Record Pages (Lightning App Builder):**

1. **Perspective Detail Page**
   - Perspective Information
   - Perspective Items (Related List)
   - Quick Actions (Edit, Clone, Delete)

2. **Dashboard Detail Page**
   - Dashboard Configuration
   - Widget Grid (Custom Component)
   - Quick Actions (Add Widget, Export)

3. **Task Execution Page**
   - Task Configuration
   - Execution History (Related List)
   - Real-time Status Monitor
   - Quick Actions (Run Now, Schedule)

### 4.2 Business Logic Architecture

#### 4.2.1 Apex Class Structure

```
Apex Architecture:
├── Controllers
│   ├── OrienteerDashboardController.cls
│   ├── OrienteerWidgetController.cls
│   ├── OrienteerPerspectiveController.cls
│   └── OrienteerTaskController.cls
├── Services
│   ├── OrienteerLocalizationService.cls
│   ├── OrienteerSecurityService.cls
│   ├── OrienteerDashboardService.cls
│   └── OrienteerTaskService.cls
├── Domain
│   ├── OrienteerDashboard.cls
│   ├── OrienteerWidget.cls
│   ├── OrienteerPerspective.cls
│   └── OrienteerTask.cls
├── Triggers
│   ├── OrienteerDashboardTrigger.trigger
│   ├── OrienteerWidgetTrigger.trigger
│   ├── OrienteerPerspectiveTrigger.trigger
│   └── OrienteerUserTrigger.trigger
├── Batch Jobs
│   ├── OrienteerTaskExecutorBatch.cls
│   ├── OrienteerCleanupBatch.cls
│   └── OrienteerDataArchiveBatch.cls
└── Utilities
    ├── OrienteerConstants.cls
    ├── OrienteerException.cls
    └── OrienteerJSONUtil.cls
```

#### 4.2.2 Trigger Framework

**Enterprise Trigger Pattern:**

```apex
// Trigger Handler Framework
public abstract class OrienteerTriggerHandler {
    public void execute() {
        if (Trigger.isBefore) {
            if (Trigger.isInsert) beforeInsert();
            if (Trigger.isUpdate) beforeUpdate();
            if (Trigger.isDelete) beforeDelete();
        } else {
            if (Trigger.isInsert) afterInsert();
            if (Trigger.isUpdate) afterUpdate();
            if (Trigger.isDelete) afterDelete();
            if (Trigger.isUndelete) afterUndelete();
        }
    }

    protected virtual void beforeInsert() {}
    protected virtual void beforeUpdate() {}
    protected virtual void beforeDelete() {}
    protected virtual void afterInsert() {}
    protected virtual void afterUpdate() {}
    protected virtual void afterDelete() {}
    protected virtual void afterUndelete() {}
}

// Example Implementation
public class OrienteerDashboardTriggerHandler extends OrienteerTriggerHandler {
    protected override void beforeInsert() {
        validateDashboardConfiguration((List<Orienteer_Dashboard__c>)Trigger.new);
    }

    protected override void afterInsert() {
        createDefaultWidgets((List<Orienteer_Dashboard__c>)Trigger.new);
    }
}
```

#### 4.2.3 Service Layer Pattern

```apex
// Service Layer for Business Logic
public with sharing class OrienteerDashboardService {

    // Create dashboard with default widgets
    public static Id createDashboard(String name, String domain, String tabName) {
        Orienteer_Dashboard__c dashboard = new Orienteer_Dashboard__c(
            Name = name,
            Domain__c = domain,
            Tab__c = tabName,
            Owner__c = UserInfo.getUserId()
        );
        insert dashboard;

        // Create default widgets asynchronously
        System.enqueueJob(new CreateDefaultWidgetsQueueable(dashboard.Id));

        return dashboard.Id;
    }

    // Get dashboard with widgets
    public static DashboardWrapper getDashboardWithWidgets(Id dashboardId) {
        Orienteer_Dashboard__c dashboard = [
            SELECT Id, Name, Domain__c, Tab__c, Configuration_JSON__c,
                   (SELECT Id, Type_Id__c, Title_JSON__c, Column__c, Row__c,
                           Size_X__c, Size_Y__c, Settings_JSON__c
                    FROM Widgets__r
                    WHERE Hidden__c = false
                    ORDER BY Row__c, Column__c)
            FROM Orienteer_Dashboard__c
            WHERE Id = :dashboardId
        ];

        return new DashboardWrapper(dashboard);
    }

    // Wrapper class for dashboard data
    public class DashboardWrapper {
        @AuraEnabled public Id id;
        @AuraEnabled public String name;
        @AuraEnabled public String domain;
        @AuraEnabled public Map<String, Object> configuration;
        @AuraEnabled public List<WidgetWrapper> widgets;

        public DashboardWrapper(Orienteer_Dashboard__c dashboard) {
            this.id = dashboard.Id;
            this.name = dashboard.Name;
            this.domain = dashboard.Domain__c;
            this.configuration = parseJSON(dashboard.Configuration_JSON__c);
            this.widgets = new List<WidgetWrapper>();
            for (Orienteer_Widget__c widget : dashboard.Widgets__r) {
                this.widgets.add(new WidgetWrapper(widget));
            }
        }
    }
}
```

### 4.3 Integration Architecture

#### 4.3.1 REST API Design

**Salesforce REST API Endpoints:**

```
Base URL: /services/apexrest/orienteer/v1/

Endpoints:
├── /dashboards
│   ├── GET    /dashboards                  - List dashboards
│   ├── POST   /dashboards                  - Create dashboard
│   ├── GET    /dashboards/{id}            - Get dashboard details
│   ├── PATCH  /dashboards/{id}            - Update dashboard
│   └── DELETE /dashboards/{id}            - Delete dashboard
├── /widgets
│   ├── GET    /widgets?dashboard={id}     - List widgets
│   ├── POST   /widgets                    - Create widget
│   ├── PATCH  /widgets/{id}               - Update widget
│   └── DELETE /widgets/{id}               - Delete widget
├── /perspectives
│   ├── GET    /perspectives               - List perspectives
│   ├── GET    /perspectives/{alias}       - Get by alias
│   └── POST   /perspectives/menu          - Get menu structure
└── /tasks
    ├── POST   /tasks/{id}/execute         - Execute task
    ├── GET    /tasks/{id}/status          - Get task status
    └── POST   /tasks/{id}/cancel          - Cancel task
```

**Sample REST Resource:**

```apex
@RestResource(urlMapping='/orienteer/v1/dashboards/*')
global with sharing class OrienteerDashboardAPI {

    @HttpGet
    global static DashboardResponse getDashboard() {
        RestRequest req = RestContext.request;
        String dashboardId = req.requestURI.substring(
            req.requestURI.lastIndexOf('/') + 1
        );

        try {
            OrienteerDashboardService.DashboardWrapper dashboard =
                OrienteerDashboardService.getDashboardWithWidgets(dashboardId);

            return new DashboardResponse(true, dashboard, null);
        } catch (Exception e) {
            return new DashboardResponse(false, null, e.getMessage());
        }
    }

    @HttpPost
    global static DashboardResponse createDashboard(DashboardRequest request) {
        try {
            Id dashboardId = OrienteerDashboardService.createDashboard(
                request.name,
                request.domain,
                request.tab
            );

            OrienteerDashboardService.DashboardWrapper dashboard =
                OrienteerDashboardService.getDashboardWithWidgets(dashboardId);

            return new DashboardResponse(true, dashboard, null);
        } catch (Exception e) {
            return new DashboardResponse(false, null, e.getMessage());
        }
    }

    global class DashboardRequest {
        public String name;
        public String domain;
        public String tab;
        public Map<String, Object> configuration;
    }

    global class DashboardResponse {
        public Boolean success;
        public OrienteerDashboardService.DashboardWrapper data;
        public String error;

        public DashboardResponse(Boolean success,
                                OrienteerDashboardService.DashboardWrapper data,
                                String error) {
            this.success = success;
            this.data = data;
            this.error = error;
        }
    }
}
```

#### 4.3.2 Platform Events

**Custom Platform Events:**

1. **Orienteer_Task_Event__e**
   ```
   Purpose: Real-time task execution updates
   Fields:
     - Task_Id__c (Text 18)
     - Status__c (Text 50)
     - Progress__c (Number 5,2)
     - Message__c (Long Text)
     - Timestamp__c (DateTime)
   ```

2. **Orienteer_Dashboard_Event__e**
   ```
   Purpose: Dashboard refresh notifications
   Fields:
     - Dashboard_Id__c (Text 18)
     - Action__c (Text 50) - refresh, update, delete
     - User_Id__c (Text 18)
   ```

3. **Orienteer_Notification__e**
   ```
   Purpose: User notifications
   Fields:
     - User_Id__c (Text 18)
     - Type__c (Text 50) - info, warning, error, success
     - Title__c (Text 255)
     - Message__c (Long Text)
     - Action_URL__c (URL)
   ```

---

## 5. Migration Architecture

### 5.1 Migration Pipeline Design

#### 5.1.1 High-Level Architecture

```
Migration Pipeline Architecture:

┌─────────────────────────────────────────────────────────────┐
│                    ORIENTDB SOURCE                          │
│  ┌──────────────────────────────────────────────────┐      │
│  │  OrientDB Database (< 500MB)                     │      │
│  │  - Extract schema definitions                    │      │
│  │  - Export data to JSON                           │      │
│  │  - Generate relationship mapping                 │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              ETL TRANSFORMATION LAYER                       │
│  ┌──────────────────────────────────────────────────┐      │
│  │  Data Transformation (Python/Node.js)            │      │
│  │  1. Schema Mapping                               │      │
│  │  2. Data Type Conversion                         │      │
│  │  3. Relationship Resolution                      │      │
│  │  4. JSON Field Transformation                    │      │
│  │  5. Validation & Cleansing                       │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              SALESFORCE BULK API 2.0                        │
│  ┌──────────────────────────────────────────────────┐      │
│  │  Bulk API Jobs (Parallel Processing)             │      │
│  │  - Metadata deployment                           │      │
│  │  - Master records (Users, Roles, Perspectives)   │      │
│  │  - Detail records (Items, Widgets)               │      │
│  │  - Junction objects (User-Role)                  │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│           VALIDATION & VERIFICATION LAYER                   │
│  ┌──────────────────────────────────────────────────┐      │
│  │  Post-Migration Validation                       │      │
│  │  - Record count verification                     │      │
│  │  - Relationship integrity check                  │      │
│  │  - Data quality validation                       │      │
│  │  - Functional testing                            │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 ETL Process Design

#### 5.2.1 Extraction Phase

**OrientDB Data Extraction:**

```javascript
// Node.js Extraction Script (orientdb-extract.js)
const OrientDB = require('orientjs');
const fs = require('fs');

class OrientDBExtractor {
    constructor(config) {
        this.server = OrientDB({
            host: config.host,
            port: config.port,
            username: config.username,
            password: config.password
        });
        this.db = this.server.use(config.database);
    }

    async extractSchema() {
        const classes = await this.db.class.list();
        const schemaMap = {};

        for (const oClass of classes) {
            if (this.shouldMigrate(oClass.name)) {
                schemaMap[oClass.name] = {
                    name: oClass.name,
                    superClass: oClass.superClass,
                    properties: await this.extractProperties(oClass),
                    indexes: await this.extractIndexes(oClass)
                };
            }
        }

        fs.writeFileSync(
            './migration-data/schema-map.json',
            JSON.stringify(schemaMap, null, 2)
        );

        return schemaMap;
    }

    async extractData(className, batchSize = 1000) {
        let skip = 0;
        let hasMore = true;
        const outputFile = `./migration-data/${className}.json`;
        const stream = fs.createWriteStream(outputFile);

        stream.write('[\n');

        while (hasMore) {
            const records = await this.db.query(
                `SELECT * FROM ${className} SKIP ${skip} LIMIT ${batchSize}`
            );

            if (records.length === 0) {
                hasMore = false;
                break;
            }

            for (let i = 0; i < records.length; i++) {
                const record = this.transformRecord(records[i]);
                stream.write(JSON.stringify(record));
                if (i < records.length - 1 || hasMore) {
                    stream.write(',\n');
                }
            }

            skip += batchSize;
        }

        stream.write('\n]');
        stream.end();

        console.log(`Extracted ${skip} records from ${className}`);
    }

    shouldMigrate(className) {
        const systemClasses = ['OUser', 'ORole', 'OIdentity'];
        const customClasses = ['OPerspective', 'OPerspectiveItem',
                              'ODashboard', 'OWidget', 'OLocalization',
                              'OModule', 'OTask', 'OTaskSession'];

        return systemClasses.includes(className) ||
               customClasses.includes(className) ||
               className.startsWith('O') && !className.startsWith('O_');
    }
}

// Execute extraction
const extractor = new OrientDBExtractor({
    host: process.env.ORIENTDB_HOST,
    port: 2424,
    username: process.env.ORIENTDB_USER,
    password: process.env.ORIENTDB_PASSWORD,
    database: process.env.ORIENTDB_DATABASE
});

extractor.extractSchema()
    .then(() => extractor.extractData('OUser'))
    .then(() => extractor.extractData('ORole'))
    .then(() => extractor.extractData('OPerspective'))
    // ... continue for all classes
    .catch(console.error);
```

#### 5.2.2 Transformation Phase

**Data Transformation Pipeline:**

```python
# Python Transformation Script (transform.py)
import json
import csv
from datetime import datetime
from typing import Dict, List, Any

class SalesforceTransformer:
    def __init__(self, schema_map_path: str):
        with open(schema_map_path, 'r') as f:
            self.schema_map = json.load(f)

        self.type_mapping = {
            'STRING': 'Text',
            'INTEGER': 'Number',
            'LONG': 'Number',
            'DOUBLE': 'Number',
            'BOOLEAN': 'Checkbox',
            'DATE': 'Date',
            'DATETIME': 'DateTime',
            'LINK': 'Lookup',
            'LINKLIST': 'Junction',
            'EMBEDDEDMAP': 'LongText'
        }

        self.relationship_map = {}

    def transform_class_to_object(self, class_name: str) -> Dict:
        """Transform OrientDB class to Salesforce object definition"""
        orientdb_class = self.schema_map[class_name]

        sf_object = {
            'label': self.format_label(class_name),
            'pluralLabel': self.format_plural_label(class_name),
            'nameField': {'type': 'Text', 'label': 'Name'},
            'deploymentStatus': 'Deployed',
            'sharingModel': self.determine_sharing_model(class_name),
            'fields': []
        }

        # Transform properties to fields
        for prop_name, prop_def in orientdb_class['properties'].items():
            field = self.transform_property_to_field(
                prop_name,
                prop_def,
                class_name
            )
            if field:
                sf_object['fields'].append(field)

        return sf_object

    def transform_property_to_field(self,
                                   prop_name: str,
                                   prop_def: Dict,
                                   class_name: str) -> Dict:
        """Transform OrientDB property to Salesforce field"""
        orient_type = prop_def.get('type')
        sf_type = self.type_mapping.get(orient_type, 'Text')

        field = {
            'fullName': f"{prop_name}__c",
            'label': self.format_label(prop_name),
            'type': sf_type
        }

        # Handle specific types
        if orient_type == 'STRING':
            field['length'] = min(prop_def.get('length', 255), 255)
        elif orient_type in ['INTEGER', 'LONG']:
            field['precision'] = 18
            field['scale'] = 0
        elif orient_type in ['DOUBLE', 'FLOAT']:
            field['precision'] = 16
            field['scale'] = 2
        elif orient_type == 'LINK':
            linked_class = prop_def.get('linkedClass')
            field['type'] = 'Lookup'
            field['referenceTo'] = f"Orienteer_{linked_class}__c"
            field['relationshipName'] = f"{prop_name}_r"
        elif orient_type == 'EMBEDDEDMAP':
            field['type'] = 'LongTextArea'
            field['length'] = 131072
            field['visibleLines'] = 10

        # Required field
        if prop_def.get('notNull'):
            field['required'] = True

        # Default value
        if 'defaultValue' in prop_def:
            field['defaultValue'] = prop_def['defaultValue']

        return field

    def transform_record_data(self,
                             class_name: str,
                             records: List[Dict]) -> List[Dict]:
        """Transform OrientDB records to Salesforce format"""
        transformed_records = []

        for record in records:
            sf_record = {
                'External_Id__c': record.get('@rid', '').replace('#', '_')
            }

            for field_name, value in record.items():
                if field_name.startswith('@'):
                    continue  # Skip OrientDB metadata

                prop_def = self.schema_map[class_name]['properties'].get(field_name)
                if not prop_def:
                    continue

                sf_field_name = f"{field_name}__c"
                sf_record[sf_field_name] = self.transform_value(
                    value,
                    prop_def['type']
                )

            transformed_records.append(sf_record)

        return transformed_records

    def transform_value(self, value: Any, orient_type: str) -> Any:
        """Transform individual field values"""
        if value is None:
            return None

        if orient_type == 'DATETIME':
            # Convert to ISO format
            if isinstance(value, int):
                return datetime.fromtimestamp(value/1000).isoformat()
            return value

        elif orient_type == 'LINK':
            # Convert RID to external ID reference
            if isinstance(value, str) and value.startswith('#'):
                return value.replace('#', '_')
            return value

        elif orient_type == 'LINKLIST':
            # Convert list of RIDs
            if isinstance(value, list):
                return [v.replace('#', '_') for v in value if isinstance(v, str)]
            return value

        elif orient_type == 'EMBEDDEDMAP':
            # Serialize to JSON
            return json.dumps(value)

        return value

    def generate_csv_for_bulk_api(self,
                                  object_name: str,
                                  records: List[Dict],
                                  output_path: str):
        """Generate CSV file for Salesforce Bulk API"""
        if not records:
            return

        # Get field names from first record
        fieldnames = list(records[0].keys())

        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

        print(f"Generated CSV for {object_name}: {len(records)} records")

# Execute transformation
transformer = SalesforceTransformer('./migration-data/schema-map.json')

# Load OrientDB data
with open('./migration-data/OUser.json', 'r') as f:
    user_records = json.load(f)

# Transform to Salesforce format
sf_users = transformer.transform_record_data('OUser', user_records)

# Generate CSV for Bulk API
transformer.generate_csv_for_bulk_api(
    'Orienteer_User__c',
    sf_users,
    './salesforce-data/Orienteer_User__c.csv'
)
```

#### 5.2.3 Loading Phase

**Salesforce Bulk API 2.0 Loader:**

```python
# Python Bulk API Loader (sf_loader.py)
import requests
import time
import csv
from typing import Dict, List
from simple_salesforce import Salesforce

class SalesforceBulkLoader:
    def __init__(self, instance_url: str, access_token: str):
        self.instance_url = instance_url
        self.access_token = access_token
        self.api_version = 'v58.0'
        self.base_url = f"{instance_url}/services/data/{self.api_version}"

        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

    def create_bulk_job(self,
                       object_name: str,
                       operation: str = 'insert') -> str:
        """Create a Bulk API 2.0 job"""
        url = f"{self.base_url}/jobs/ingest"

        payload = {
            'object': object_name,
            'operation': operation,
            'lineEnding': 'LF',
            'columnDelimiter': 'COMMA',
            'contentType': 'CSV'
        }

        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()

        job_info = response.json()
        job_id = job_info['id']

        print(f"Created bulk job {job_id} for {object_name}")
        return job_id

    def upload_job_data(self, job_id: str, csv_file_path: str):
        """Upload CSV data to bulk job"""
        url = f"{self.base_url}/jobs/ingest/{job_id}/batches"

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'text/csv'
        }

        with open(csv_file_path, 'rb') as f:
            response = requests.put(url, data=f, headers=headers)
            response.raise_for_status()

        print(f"Uploaded data for job {job_id}")

    def close_job(self, job_id: str):
        """Close the bulk job to start processing"""
        url = f"{self.base_url}/jobs/ingest/{job_id}"

        payload = {'state': 'UploadComplete'}

        response = requests.patch(url, json=payload, headers=self.headers)
        response.raise_for_status()

        print(f"Closed job {job_id} for processing")

    def get_job_status(self, job_id: str) -> Dict:
        """Get current job status"""
        url = f"{self.base_url}/jobs/ingest/{job_id}"

        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        return response.json()

    def wait_for_job_completion(self, job_id: str, timeout: int = 3600):
        """Wait for job to complete"""
        start_time = time.time()

        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")

            status = self.get_job_status(job_id)
            state = status['state']

            print(f"Job {job_id} state: {state} - " +
                  f"Processed: {status.get('numberRecordsProcessed', 0)}")

            if state in ['JobComplete', 'Failed', 'Aborted']:
                return status

            time.sleep(5)  # Poll every 5 seconds

    def get_job_results(self, job_id: str) -> Dict:
        """Get job results including failures"""
        # Get successful records
        success_url = f"{self.base_url}/jobs/ingest/{job_id}/successfulResults"
        success_response = requests.get(success_url, headers=self.headers)

        # Get failed records
        failed_url = f"{self.base_url}/jobs/ingest/{job_id}/failedResults"
        failed_response = requests.get(failed_url, headers=self.headers)

        return {
            'successful': success_response.text if success_response.ok else '',
            'failed': failed_response.text if failed_response.ok else ''
        }

    def load_data(self, object_name: str, csv_file_path: str) -> Dict:
        """Complete load process for an object"""
        print(f"\n=== Loading {object_name} ===")

        # Create job
        job_id = self.create_bulk_job(object_name, 'insert')

        # Upload data
        self.upload_job_data(job_id, csv_file_path)

        # Close job
        self.close_job(job_id)

        # Wait for completion
        final_status = self.wait_for_job_completion(job_id)

        # Get results
        results = self.get_job_results(job_id)

        # Save failed records if any
        if final_status.get('numberRecordsFailed', 0) > 0:
            with open(f'./errors/{object_name}_failures.csv', 'w') as f:
                f.write(results['failed'])

        print(f"Completed: {final_status.get('numberRecordsProcessed', 0)} processed, " +
              f"{final_status.get('numberRecordsFailed', 0)} failed")

        return final_status

# Migration execution order (respects dependencies)
MIGRATION_ORDER = [
    'Orienteer_Role__c',
    'Orienteer_Perspective__c',
    'Orienteer_User__c',
    'Orienteer_Perspective_Item__c',
    'Orienteer_Dashboard__c',
    'Orienteer_Widget__c',
    'Orienteer_Module__c',
    'Orienteer_Localization__c',
    'Orienteer_Task__c',
    'Orienteer_Task_Session__c',
    'Orienteer_User_Role__c'  # Junction object last
]

# Execute migration
loader = SalesforceBulkLoader(
    instance_url=os.environ['SF_INSTANCE_URL'],
    access_token=os.environ['SF_ACCESS_TOKEN']
)

results_summary = {}

for object_name in MIGRATION_ORDER:
    csv_file = f'./salesforce-data/{object_name}.csv'

    if os.path.exists(csv_file):
        result = loader.load_data(object_name, csv_file)
        results_summary[object_name] = result
    else:
        print(f"Skipping {object_name} - no data file found")

# Print summary
print("\n=== MIGRATION SUMMARY ===")
for obj, result in results_summary.items():
    print(f"{obj}: {result['numberRecordsProcessed']} processed, " +
          f"{result['numberRecordsFailed']} failed")
```

### 5.3 Migration Workflow

#### 5.3.1 Pre-Migration Phase

```
1. Environment Setup
   ├── Create Salesforce sandbox
   ├── Deploy metadata (objects, fields, relationships)
   ├── Configure profiles and permission sets
   └── Set up integration users

2. Data Analysis
   ├── Analyze OrientDB schema
   ├── Identify data volumes per class
   ├── Map relationships and dependencies
   └── Generate transformation specifications

3. Test Run Preparation
   ├── Extract sample data (10% of records)
   ├── Set up validation queries
   ├── Prepare rollback procedures
   └── Document expected results
```

#### 5.3.2 Migration Execution Phase

```
1. Metadata Deployment (Salesforce CLI/Ant)
   └── deploy_metadata.sh
       ├── Deploy Custom Objects
       ├── Deploy Custom Fields
       ├── Deploy Validation Rules
       ├── Deploy Triggers & Classes
       └── Deploy Lightning Components

2. Data Extraction (OrientDB)
   └── extract_data.sh
       ├── Extract schema definitions
       ├── Export all class data to JSON
       ├── Generate relationship map
       └── Create data manifest

3. Data Transformation
   └── transform_data.sh
       ├── Transform schema to Salesforce objects
       ├── Convert data types
       ├── Resolve relationships (RID → External ID)
       ├── Generate CSV files
       └── Validate transformed data

4. Data Loading (Bulk API 2.0)
   └── load_data.sh
       ├── Load in dependency order
       ├── Monitor job progress
       ├── Handle failures
       └── Verify record counts

5. Post-Migration Validation
   └── validate_migration.sh
       ├── Compare record counts
       ├── Validate relationships
       ├── Run test queries
       └── Execute functional tests
```

#### 5.3.3 Post-Migration Phase

```
1. Data Verification
   ├── Record count validation
   ├── Relationship integrity check
   ├── Data quality assessment
   └── User acceptance testing

2. System Configuration
   ├── Configure Lightning Apps
   ├── Assign permission sets
   ├── Set up dashboards
   └── Enable Platform Events

3. Cutover Preparation
   ├── Document migration results
   ├── Prepare production runbook
   ├── Schedule downtime window
   └── Brief stakeholders
```

### 5.4 Validation Strategy

#### 5.4.1 Automated Validation

```python
# Validation Script (validate_migration.py)
import pandas as pd
from simple_salesforce import Salesforce

class MigrationValidator:
    def __init__(self, sf: Salesforce, orientdb_data_path: str):
        self.sf = sf
        self.orientdb_data_path = orientdb_data_path
        self.validation_results = {}

    def validate_record_counts(self, object_name: str, expected_count: int):
        """Validate record count matches expected"""
        query = f"SELECT COUNT() FROM {object_name}"
        result = self.sf.query(query)
        actual_count = result['totalSize']

        status = 'PASS' if actual_count == expected_count else 'FAIL'

        self.validation_results[f"{object_name}_count"] = {
            'test': 'Record Count',
            'expected': expected_count,
            'actual': actual_count,
            'status': status
        }

        print(f"{object_name} Record Count: {status} " +
              f"(Expected: {expected_count}, Actual: {actual_count})")

    def validate_relationships(self, object_name: str,
                              relationship_field: str,
                              parent_object: str):
        """Validate relationship integrity"""
        query = f"""
            SELECT COUNT()
            FROM {object_name}
            WHERE {relationship_field} = null
        """
        result = self.sf.query(query)
        null_count = result['totalSize']

        status = 'PASS' if null_count == 0 else 'WARNING'

        self.validation_results[f"{object_name}_{relationship_field}"] = {
            'test': 'Relationship Integrity',
            'field': relationship_field,
            'null_count': null_count,
            'status': status
        }

        print(f"{object_name}.{relationship_field}: {status} " +
              f"({null_count} null references)")

    def validate_data_quality(self, object_name: str, sample_size: int = 100):
        """Validate data quality with sample checks"""
        query = f"SELECT Id, Name FROM {object_name} LIMIT {sample_size}"
        records = self.sf.query(query)['records']

        empty_names = sum(1 for r in records if not r.get('Name'))

        status = 'PASS' if empty_names == 0 else 'FAIL'

        self.validation_results[f"{object_name}_quality"] = {
            'test': 'Data Quality',
            'sample_size': len(records),
            'empty_names': empty_names,
            'status': status
        }

        print(f"{object_name} Data Quality: {status} " +
              f"({empty_names}/{len(records)} empty names)")

    def generate_validation_report(self, output_path: str):
        """Generate HTML validation report"""
        df = pd.DataFrame.from_dict(self.validation_results, orient='index')

        html = df.to_html(classes='table table-striped')

        with open(output_path, 'w') as f:
            f.write(f"""
            <html>
            <head>
                <title>Migration Validation Report</title>
                <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
            </head>
            <body>
                <div class="container mt-5">
                    <h1>Migration Validation Report</h1>
                    <p>Generated: {datetime.now().isoformat()}</p>
                    {html}
                </div>
            </body>
            </html>
            """)

        print(f"Validation report generated: {output_path}")

    def run_all_validations(self):
        """Execute complete validation suite"""
        print("\n=== Running Migration Validations ===\n")

        # Validate counts
        self.validate_record_counts('Orienteer_User__c', 150)
        self.validate_record_counts('Orienteer_Role__c', 20)
        self.validate_record_counts('Orienteer_Perspective__c', 5)
        self.validate_record_counts('Orienteer_Dashboard__c', 80)
        self.validate_record_counts('Orienteer_Widget__c', 320)

        # Validate relationships
        self.validate_relationships('Orienteer_User__c', 'Perspective__c',
                                   'Orienteer_Perspective__c')
        self.validate_relationships('Orienteer_Widget__c', 'Dashboard__c',
                                   'Orienteer_Dashboard__c')

        # Validate data quality
        self.validate_data_quality('Orienteer_User__c')
        self.validate_data_quality('Orienteer_Dashboard__c')

        # Generate report
        self.generate_validation_report('./validation-report.html')

        return self.validation_results
```

---

## 6. Security Architecture

### 6.1 Security Model Mapping

#### 6.1.1 OrientDB → Salesforce Security Translation

| OrientDB Security | Salesforce Equivalent | Implementation |
|-------------------|----------------------|----------------|
| OUser | Standard User | 1:1 mapping with Orienteer_User__c extension |
| ORole | Permission Set + Profile | Hybrid approach |
| OIdentity | User/Role base class | Standard platform security |
| ORestricted | Sharing Rules | Criteria-based sharing |
| Database ACLs | Object/Field Permissions | Permission Sets |
| Class-level security | Object Permissions | OWD + Sharing |
| Property-level security | Field-Level Security | Profile/Permission Set |

#### 6.1.2 Permission Set Architecture

**Core Permission Sets:**

1. **Orienteer_Admin**
   ```
   Purpose: Full administrative access
   Object Permissions:
     - All Orienteer objects: CRUDV
     - System objects: Read
   Field Permissions:
     - All fields: Read/Edit
   Apex Classes:
     - All Orienteer classes
   Lightning Components:
     - All components
   System Permissions:
     - Modify All Data
     - View All Data
   ```

2. **Orienteer_Power_User**
   ```
   Purpose: Advanced user capabilities
   Object Permissions:
     - Orienteer_Dashboard__c: CRUD
     - Orienteer_Widget__c: CRUD
     - Orienteer_Perspective__c: Read
     - Orienteer_User__c: Read (Own)
   Field Permissions:
     - Standard fields: Read/Edit
     - System fields: Read only
   Apex Classes:
     - OrienteerDashboardController
     - OrienteerWidgetController
   ```

3. **Orienteer_Standard_User**
   ```
   Purpose: Standard user access
   Object Permissions:
     - Orienteer_Dashboard__c: Read, Create (Own)
     - Orienteer_Widget__c: Read
     - Orienteer_Perspective__c: Read
   Field Permissions:
     - Limited field access
   Apex Classes:
     - OrienteerDashboardController (read methods)
   ```

4. **Orienteer_Task_Manager**
   ```
   Purpose: Task execution and monitoring
   Object Permissions:
     - Orienteer_Task__c: CRUD
     - Orienteer_Task_Session__c: CRU
   Apex Classes:
     - OrienteerTaskController
     - OrienteerTaskExecutorBatch
   System Permissions:
     - Run Flows
   ```

### 6.2 Sharing Rules Architecture

#### 6.2.1 Organization-Wide Defaults

```
Object                          | OWD Setting
--------------------------------|------------------
Orienteer_User__c               | Private
Orienteer_Role__c               | Public Read Only
Orienteer_Perspective__c        | Public Read Only
Orienteer_Perspective_Item__c   | Controlled by Parent
Orienteer_Dashboard__c          | Private
Orienteer_Widget__c             | Controlled by Parent
Orienteer_Localization__c       | Public Read Only
Orienteer_Module__c             | Public Read Only
Orienteer_Task__c               | Private
Orienteer_Task_Session__c       | Private
```

#### 6.2.2 Sharing Rules

**Criteria-Based Sharing:**

1. **Public Dashboard Sharing**
   ```
   Rule: Share_Public_Dashboards
   Object: Orienteer_Dashboard__c
   Criteria: Public__c = true
   Share With: All Internal Users
   Access Level: Read Only
   ```

2. **Role-Based Dashboard Sharing**
   ```
   Rule: Share_Role_Dashboards
   Object: Orienteer_Dashboard__c
   Criteria: Role_Based__c = true
   Share With: Roles and Subordinates
   Access Level: Read/Write
   Determined By: Owner Role
   ```

#### 6.2.3 Apex Sharing

```apex
// Programmatic sharing for dynamic access control
public class OrienteerSharingService {

    public static void shareDashboardWithUsers(Id dashboardId, Set<Id> userIds) {
        List<Orienteer_Dashboard__Share> shares = new List<Orienteer_Dashboard__Share>();

        for (Id userId : userIds) {
            Orienteer_Dashboard__Share share = new Orienteer_Dashboard__Share(
                ParentId = dashboardId,
                UserOrGroupId = userId,
                AccessLevel = 'Edit',
                RowCause = Schema.Orienteer_Dashboard__Share.RowCause.Manual
            );
            shares.add(share);
        }

        insert shares;
    }

    public static void removeAccess(Id dashboardId, Id userId) {
        List<Orienteer_Dashboard__Share> shares = [
            SELECT Id
            FROM Orienteer_Dashboard__Share
            WHERE ParentId = :dashboardId
              AND UserOrGroupId = :userId
              AND RowCause = :Schema.Orienteer_Dashboard__Share.RowCause.Manual
        ];

        delete shares;
    }
}
```

### 6.3 Data Security

#### 6.3.1 Field-Level Security

```
Sensitive Field Protection:

1. Orienteer_User__c.API_Key__c
   - Encrypted field
   - Visible to: Admins only
   - Masked in UI

2. Orienteer_Task__c.Configuration_JSON__c
   - Contains credentials
   - FLS: Admin read/write
   - Audit trail enabled

3. Orienteer_Widget__c.Settings_JSON__c
   - May contain sensitive data
   - FLS: Owner + Admins
```

#### 6.3.2 Encryption

```
Platform Encryption:
- API Keys and Tokens
- User passwords (if stored)
- Sensitive configuration data

Shield Platform Encryption objects:
- Orienteer_User__c.API_Key__c
- Orienteer_Task__c.Credentials__c
```

---

## 7. Integration Architecture

### 7.1 API Architecture

#### 7.1.1 REST API Structure

```
API Design:
├── Authentication: OAuth 2.0
├── Base URL: /services/apexrest/orienteer/v1
├── Format: JSON
├── Rate Limiting: Standard Salesforce limits
└── Versioning: URI versioning (v1, v2)

API Documentation:
- OpenAPI 3.0 specification
- Swagger UI for testing
- Postman collections
```

#### 7.1.2 Webhook Integration

```apex
// Outbound webhook for external systems
public class OrienteerWebhookService {

    @future(callout=true)
    public static void sendDashboardUpdateWebhook(Id dashboardId) {
        Orienteer_Dashboard__c dashboard = [
            SELECT Id, Name, Domain__c, LastModifiedDate
            FROM Orienteer_Dashboard__c
            WHERE Id = :dashboardId
        ];

        Map<String, Object> payload = new Map<String, Object>{
            'event' => 'dashboard.updated',
            'timestamp' => System.now().format(),
            'data' => new Map<String, Object>{
                'id' => dashboard.Id,
                'name' => dashboard.Name,
                'domain' => dashboard.Domain__c,
                'modifiedDate' => dashboard.LastModifiedDate.format()
            }
        };

        HttpRequest req = new HttpRequest();
        req.setEndpoint('callout:Orienteer_Webhook');
        req.setMethod('POST');
        req.setHeader('Content-Type', 'application/json');
        req.setBody(JSON.serialize(payload));

        Http http = new Http();
        HttpResponse res = http.send(req);

        // Log response
        insert new Orienteer_Webhook_Log__c(
            Endpoint__c = req.getEndpoint(),
            Status_Code__c = res.getStatusCode(),
            Response__c = res.getBody()
        );
    }
}
```

### 7.2 Real-Time Architecture

#### 7.2.1 Platform Events Flow

```
Event Flow:
1. Trigger fires on record change
2. Publish Platform Event
3. Subscribers receive event
4. Update UI/External systems

Platform Event Subscribers:
├── Lightning Components (real-time UI updates)
├── Flow automations
├── Apex triggers
└── External systems (Event Bus API)
```

---

## 8. Architecture Decision Records

### ADR-001: Use Custom Objects Instead of Custom Settings

**Status**: Accepted
**Date**: 2025-10-01

**Context**: Need to store Orienteer entities in Salesforce. Options were Custom Objects, Custom Settings, or Custom Metadata Types.

**Decision**: Use Custom Objects for all data entities.

**Rationale**:
- Large data volumes (> 500MB requires Custom Objects)
- Need for complex relationships (Master-Detail, Lookup)
- Reporting requirements
- API access requirements
- Record-level security needed

**Consequences**:
- ✅ Full CRUD capabilities
- ✅ Relationship support
- ✅ Better scalability
- ❌ Higher storage consumption
- ❌ More complex security model

---

### ADR-002: Master-Detail vs Lookup for Parent-Child Relationships

**Status**: Accepted
**Date**: 2025-10-01

**Context**: Need to model parent-child relationships (Perspective-Items, Dashboard-Widgets).

**Decision**: Use Master-Detail for tight parent-child relationships with cascade delete.

**Rationale**:
- Cascade delete maintains data integrity
- Roll-up summary fields for counts/aggregations
- Sharing model inheritance simplifies security
- Aligns with OrientDB embedded document pattern

**Consequences**:
- ✅ Automatic cascade delete
- ✅ Simplified sharing model
- ✅ Roll-up summaries
- ❌ Limited to 2 levels deep
- ❌ Cannot reparent records

---

### ADR-003: JSON Storage for EMBEDDEDMAP Fields

**Status**: Accepted
**Date**: 2025-10-01

**Context**: OrientDB uses EMBEDDEDMAP extensively for configuration and localization.

**Decision**: Store EMBEDDEDMAP as JSON in Long Text fields.

**Rationale**:
- Preserves data structure
- No data loss during migration
- Flexible schema
- Easy to parse in Apex/JavaScript

**Consequences**:
- ✅ Complete data preservation
- ✅ Schema flexibility
- ❌ Cannot query within JSON (without custom parsing)
- ❌ No field-level validation
- ❌ Requires JSON parsing overhead

**Alternative Considered**: Create child Custom Objects for each embedded type
- Rejected due to complexity and migration overhead

---

### ADR-004: Bulk API 2.0 for Data Migration

**Status**: Accepted
**Date**: 2025-10-01

**Context**: Need to migrate < 500MB of data efficiently with minimal downtime.

**Decision**: Use Salesforce Bulk API 2.0 for all data loading.

**Rationale**:
- Optimized for large data volumes
- Parallel processing support
- Better error handling than Bulk API 1.0
- CSV format simplicity
- Built-in monitoring

**Consequences**:
- ✅ Fast parallel processing
- ✅ Better error reporting
- ✅ Resumable jobs
- ❌ Async processing (requires polling)
- ❌ CSV format limitations (no complex nesting)

---

### ADR-005: Lightning Web Components Over Aura

**Status**: Accepted
**Date**: 2025-10-01

**Context**: Need to build UI components for dashboards and widgets.

**Decision**: Use LWC for all new components; Aura only for legacy compatibility.

**Rationale**:
- LWC is the strategic direction
- Better performance
- Modern JavaScript standards
- Smaller bundle size
- Easier testing

**Consequences**:
- ✅ Better performance
- ✅ Modern development experience
- ✅ Easier maintenance
- ❌ Learning curve for team
- ❌ Some Aura-only features unavailable

---

### ADR-006: External ID Strategy

**Status**: Accepted
**Date**: 2025-10-01

**Context**: Need to maintain references between OrientDB RIDs and Salesforce IDs during migration.

**Decision**: Create External_Id__c field on all migrated objects to store transformed OrientDB RID.

**Rationale**:
- Enables upsert operations
- Simplifies relationship resolution
- Supports re-migration scenarios
- Audit trail for data lineage

**Consequences**:
- ✅ Idempotent migrations
- ✅ Easy relationship mapping
- ✅ Data lineage tracking
- ❌ Additional field on every object
- ❌ Storage overhead

**Format**: OrientDB RID `#12:34` → Salesforce External ID `12_34`

---

### ADR-007: No Graph Relationship Migration

**Status**: Accepted
**Date**: 2025-10-01

**Context**: OrientDB supports graph edges for complex relationships. Salesforce is relational.

**Decision**: Do not migrate OrientDB graph edges; only standard relationships (LINK, LINKLIST).

**Rationale**:
- Per requirements, graph data not needed
- Salesforce is relational, not graph-based
- Would require complex junction object network
- No business requirement for traversal queries

**Consequences**:
- ✅ Simplified migration
- ✅ Better Salesforce performance
- ✅ Reduced complexity
- ❌ Loss of graph traversal capabilities
- ❌ Some advanced OrientDB features unavailable

---

### ADR-008: Apex Trigger Framework

**Status**: Accepted
**Date**: 2025-10-01

**Context**: Need consistent trigger handling across all objects.

**Decision**: Implement trigger handler framework pattern.

**Rationale**:
- Consistent structure
- Testability
- Single trigger per object
- Governor limit management
- Maintainability

**Consequences**:
- ✅ Clean separation of concerns
- ✅ Easy to test
- ✅ Reusable patterns
- ❌ Initial setup overhead
- ❌ Abstraction layer complexity

---

## 9. Deployment Architecture

### 9.1 Metadata Deployment Strategy

```
Deployment Order:
1. Custom Objects (no relationships)
2. Custom Fields (non-lookup)
3. Lookup/Master-Detail Relationships
4. Validation Rules
5. Workflow Rules / Process Builder
6. Apex Classes (dependencies first)
7. Apex Triggers
8. Lightning Components
9. Permission Sets
10. Custom Metadata Types
```

### 9.2 DevOps Pipeline

```
CI/CD Pipeline:
├── Source Control: Git
├── Build: Salesforce CLI
├── Testing: Automated Apex tests (85%+ coverage)
├── Deployment: Salesforce CLI / Ant
└── Monitoring: Salesforce Setup Audit Trail

Environments:
1. Developer Sandbox (development)
2. QA Sandbox (testing)
3. UAT Sandbox (user acceptance)
4. Production (live)
```

---

## 10. Monitoring and Observability

### 10.1 Monitoring Strategy

```
Monitoring Components:
├── Data Migration Monitoring
│   ├── Bulk API job status
│   ├── Record counts
│   └── Error logs
├── Application Monitoring
│   ├── Apex debug logs
│   ├── Lightning component errors
│   └── API usage metrics
└── Performance Monitoring
    ├── SOQL query performance
    ├── Apex CPU time
    └── View state size
```

### 10.2 Logging Architecture

```apex
// Centralized logging service
public class OrienteerLogger {
    public enum Level { DEBUG, INFO, WARN, ERROR }

    public static void log(Level level, String message, Exception ex) {
        Orienteer_Log__c logEntry = new Orienteer_Log__c(
            Level__c = level.name(),
            Message__c = message,
            Exception_Type__c = ex?.getTypeName(),
            Stack_Trace__c = ex?.getStackTraceString(),
            User__c = UserInfo.getUserId(),
            Timestamp__c = System.now()
        );

        insert logEntry;

        // Also log to debug log
        System.debug(LoggingLevel.valueOf(level.name()), message);
        if (ex != null) {
            System.debug(LoggingLevel.ERROR, ex);
        }
    }
}
```

---

## Appendices

### Appendix A: Object Field Reference

Detailed field specifications for each Custom Object (see sections 3.1.1)

### Appendix B: API Reference

Complete REST API endpoint documentation (see section 7.1.1)

### Appendix C: Migration Scripts

Full scripts for extraction, transformation, and loading (see section 5.2)

### Appendix D: Testing Strategy

```
Testing Levels:
1. Unit Tests (Apex)
   - 85%+ code coverage
   - Test all service methods
   - Test trigger handlers

2. Integration Tests
   - API endpoint testing
   - Bulk API testing
   - Platform Event testing

3. UI Tests
   - Lightning component tests
   - User flow tests
   - Cross-browser testing

4. Performance Tests
   - Load testing (concurrent users)
   - Data volume testing
   - API rate limit testing

5. Security Tests
   - Permission set testing
   - Sharing rule testing
   - Field-level security testing
```

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-01 | Architecture Team | Initial architecture design |

**Review Status**: Draft
**Next Review Date**: Post test migration
**Approvers**: Technical Lead, Salesforce Architect, Product Owner
