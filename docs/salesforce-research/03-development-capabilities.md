# Salesforce Development Capabilities

## Overview
Analysis of Salesforce development tools and frameworks relevant to migrating Orienteer's Apache Wicket-based UI and business logic.

## Salesforce Development Platforms

### Platform Overview

| Technology | Type | Use Case | Comparison to Orienteer |
|-----------|------|----------|------------------------|
| **Apex** | Server-side language | Business logic, triggers, API services | Replaces Java backend logic |
| **Lightning Web Components (LWC)** | UI framework | Modern UI components | Replaces Wicket components |
| **Aura Components** | UI framework (legacy) | Legacy UI (being phased out) | Alternative to Wicket |
| **Visualforce** | UI framework (legacy) | Server-rendered pages | Similar to Wicket approach |
| **Flow Builder** | No-code automation | Visual workflows | Replaces BPM module |
| **Process Builder** | No-code automation | Simple automation (deprecated) | Limited BPM features |
| **Lightning App Builder** | Page builder | Declarative UI composition | Replaces Wicket panels/widgets |

## Apex Programming Language

### Overview
- **Type**: Object-oriented, strongly-typed
- **Syntax**: Java-like syntax
- **Execution**: Runs on Salesforce multi-tenant cloud
- **Access**: Database operations, web services, email services

### Key Characteristics

#### Similarities to Java
```apex
// Class definition (similar to Java)
public class AccountService {
    // Private variable
    private static final Integer MAX_RECORDS = 200;

    // Constructor
    public AccountService() {
        // Initialization
    }

    // Methods
    public List<Account> getAccounts(String industry) {
        return [SELECT Id, Name FROM Account WHERE Industry = :industry];
    }

    // Static methods
    public static void processAccounts(List<Account> accounts) {
        for(Account acc : accounts) {
            // Processing logic
        }
    }
}
```

#### Differences from Java
1. **Database Integration**: Built-in SOQL/SOSL
2. **Governor Limits**: Strict execution limits
3. **Multi-tenancy**: Shared execution context
4. **DML Operations**: Specific database methods
5. **No File I/O**: Cannot access file system
6. **Limited Libraries**: Restricted standard library

### Apex Features

#### 1. Database Operations (DML)
```apex
// Insert records
Account acc = new Account(Name='Test Account');
insert acc;

// Update records
acc.Industry = 'Technology';
update acc;

// Delete records
delete acc;

// Upsert (insert or update based on external ID)
upsert accountList Account_External_Id__c;

// Bulk operations (best practice)
List<Account> accounts = new List<Account>();
for(Integer i = 0; i < 200; i++) {
    accounts.add(new Account(Name='Account ' + i));
}
insert accounts; // Single DML for all records
```

#### 2. SOQL (Salesforce Object Query Language)
```apex
// Basic query
List<Account> accounts = [SELECT Id, Name FROM Account WHERE Industry = 'Technology'];

// Complex query with relationships
List<Contact> contacts = [
    SELECT Id, Name, Account.Name, Account.Industry
    FROM Contact
    WHERE Account.Industry = 'Technology'
    AND CreatedDate = LAST_N_DAYS:30
    ORDER BY LastModifiedDate DESC
    LIMIT 100
];

// Dynamic SOQL
String query = 'SELECT Id, Name FROM Account WHERE Industry = :industry';
List<Account> results = Database.query(query);

// Aggregate queries
AggregateResult[] results = [
    SELECT COUNT(Id) cnt, Industry
    FROM Account
    GROUP BY Industry
    HAVING COUNT(Id) > 10
];
```

#### 3. Triggers (Database Hooks)
```apex
// Account Trigger
trigger AccountTrigger on Account (before insert, before update, after insert, after update) {
    if(Trigger.isBefore) {
        if(Trigger.isInsert) {
            // Before insert logic
            for(Account acc : Trigger.new) {
                if(acc.Industry == null) {
                    acc.Industry = 'Unknown';
                }
            }
        }
        else if(Trigger.isUpdate) {
            // Before update logic
            for(Account acc : Trigger.new) {
                Account oldAcc = Trigger.oldMap.get(acc.Id);
                if(acc.Industry != oldAcc.Industry) {
                    // Industry changed
                }
            }
        }
    }
    else if(Trigger.isAfter) {
        if(Trigger.isInsert) {
            // After insert logic (call async processes, etc.)
            AccountService.processNewAccounts(Trigger.new);
        }
    }
}
```

**Best Practice**: Use trigger framework pattern
```apex
// TriggerHandler pattern
trigger AccountTrigger on Account (before insert, before update, after insert, after update) {
    new AccountTriggerHandler().run();
}

public class AccountTriggerHandler extends TriggerHandler {
    protected override void beforeInsert() {
        // Before insert logic
    }

    protected override void afterUpdate() {
        // After update logic
    }
}
```

#### 4. Classes and Interfaces
```apex
// Interface
public interface IAccountService {
    List<Account> getAccounts(String industry);
    void processAccounts(List<Account> accounts);
}

// Implementation
public class AccountServiceImpl implements IAccountService {
    public List<Account> getAccounts(String industry) {
        return [SELECT Id, Name FROM Account WHERE Industry = :industry];
    }

    public void processAccounts(List<Account> accounts) {
        // Processing logic
    }
}

// Abstract class
public abstract class BaseService {
    protected String getNamespace() {
        return 'MyNamespace';
    }

    public abstract void execute();
}

// Inheritance
public class ConcreteService extends BaseService {
    public override void execute() {
        // Implementation
    }
}
```

#### 5. Exception Handling
```apex
public class SafeOperations {
    public static void performDML(List<Account> accounts) {
        try {
            insert accounts;
        }
        catch(DmlException e) {
            // Handle DML errors
            System.debug('DML Error: ' + e.getMessage());
            for(Integer i = 0; i < e.getNumDml(); i++) {
                System.debug('Record ' + i + ': ' + e.getDmlMessage(i));
            }
        }
        catch(Exception e) {
            // Handle other exceptions
            System.debug('Error: ' + e.getMessage());
            throw e; // Re-throw if needed
        }
        finally {
            // Cleanup logic
        }
    }
}
```

#### 6. Collections
```apex
// List
List<String> stringList = new List<String>();
stringList.add('First');
stringList.add('Second');
String first = stringList.get(0);

// Set
Set<Id> accountIds = new Set<Id>();
accountIds.add(acc1.Id);
accountIds.add(acc2.Id);
Boolean contains = accountIds.contains(acc1.Id);

// Map
Map<Id, Account> accountMap = new Map<Id, Account>();
accountMap.put(acc.Id, acc);
Account retrieved = accountMap.get(acc.Id);

// Map from SOQL
Map<Id, Account> accountMap = new Map<Id, Account>(
    [SELECT Id, Name FROM Account]
);
```

### Apex vs. Java Backend Logic Migration

| Orienteer (Java) | Salesforce (Apex) | Notes |
|-----------------|------------------|-------|
| Service Classes | Apex Classes | Direct mapping |
| DAO Layer | SOQL queries | Built-in database access |
| ORM (OrientDB) | sObject CRUD | Native object-database mapping |
| Dependency Injection (Guice) | Dependency Injection (limited) | Some DI patterns supported |
| Event Listeners | Triggers + Platform Events | Different event model |
| Scheduled Jobs | Scheduled Apex | Similar functionality |
| Async Processing | Queueable, Future, Batch Apex | Multiple async patterns |
| Web Services | REST/SOAP Apex | Built-in web service support |

## Lightning Web Components (LWC)

### Overview
- **Standard**: Web Components standard (Custom Elements, Shadow DOM, Templates)
- **Framework**: Lightweight JavaScript framework
- **Performance**: Faster than Aura Components
- **Modern**: ES6+ JavaScript syntax

### Component Structure
```
myComponent/
  ├── myComponent.html       (Template)
  ├── myComponent.js         (JavaScript controller)
  ├── myComponent.css        (Styles)
  └── myComponent.js-meta.xml (Metadata)
```

### Example Component

#### HTML Template
```html
<!-- myComponent.html -->
<template>
    <lightning-card title="Account List" icon-name="standard:account">
        <div class="slds-m-around_medium">
            <template if:true={accounts}>
                <template for:each={accounts} for:item="account">
                    <div key={account.Id} class="slds-box slds-m-bottom_small">
                        <p><strong>{account.Name}</strong></p>
                        <p>Industry: {account.Industry}</p>
                        <lightning-button
                            label="View Details"
                            onclick={handleViewDetails}
                            data-id={account.Id}>
                        </lightning-button>
                    </div>
                </template>
            </template>
            <template if:true={error}>
                <p class="slds-text-color_error">{error}</p>
            </template>
        </div>
    </lightning-card>
</template>
```

#### JavaScript Controller
```javascript
// myComponent.js
import { LightningElement, wire, track } from 'lwc';
import getAccounts from '@salesforce/apex/AccountController.getAccounts';

export default class MyComponent extends LightningElement {
    @track accounts;
    @track error;

    // Wire service to call Apex method
    @wire(getAccounts, { industry: 'Technology' })
    wiredAccounts({ error, data }) {
        if (data) {
            this.accounts = data;
            this.error = undefined;
        } else if (error) {
            this.error = error;
            this.accounts = undefined;
        }
    }

    handleViewDetails(event) {
        const accountId = event.target.dataset.id;
        // Navigate to record page or show details
        this[NavigationMixin.Navigate]({
            type: 'standard__recordPage',
            attributes: {
                recordId: accountId,
                actionName: 'view'
            }
        });
    }
}
```

#### Apex Controller
```apex
// AccountController.cls
public with sharing class AccountController {
    @AuraEnabled(cacheable=true)
    public static List<Account> getAccounts(String industry) {
        return [
            SELECT Id, Name, Industry
            FROM Account
            WHERE Industry = :industry
            LIMIT 50
        ];
    }
}
```

#### Metadata
```xml
<!-- myComponent.js-meta.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<LightningComponentBundle xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>58.0</apiVersion>
    <isExposed>true</isExposed>
    <targets>
        <target>lightning__AppPage</target>
        <target>lightning__RecordPage</target>
        <target>lightning__HomePage</target>
    </targets>
</LightningComponentBundle>
```

### LWC Features

#### 1. Component Communication
```javascript
// Parent to Child: Public Properties
// child.js
import { LightningElement, api } from 'lwc';
export default class Child extends LightningElement {
    @api message; // Public property
}

// Child to Parent: Events
// child.js
this.dispatchEvent(new CustomEvent('notify', {
    detail: { message: 'Something happened' }
}));

// parent.html
<c-child onnotify={handleNotify}></c-child>

// parent.js
handleNotify(event) {
    console.log(event.detail.message);
}
```

#### 2. Lightning Data Service
```javascript
// Read record
import { LightningElement, api, wire } from 'lwc';
import { getRecord } from 'lightning/uiRecordApi';

export default class RecordViewer extends LightningElement {
    @api recordId;
    @wire(getRecord, { recordId: '$recordId', fields: ['Account.Name', 'Account.Industry'] })
    account;
}

// Update record
import { updateRecord } from 'lightning/uiRecordApi';

updateAccount() {
    const fields = {};
    fields[ID_FIELD.fieldApiName] = this.accountId;
    fields[NAME_FIELD.fieldApiName] = this.newName;

    const recordInput = { fields };

    updateRecord(recordInput)
        .then(() => {
            // Success
        })
        .catch(error => {
            // Error handling
        });
}
```

#### 3. Navigation
```javascript
import { NavigationMixin } from 'lightning/navigation';

export default class MyComponent extends NavigationMixin(LightningElement) {
    navigateToRecord() {
        this[NavigationMixin.Navigate]({
            type: 'standard__recordPage',
            attributes: {
                recordId: this.recordId,
                objectApiName: 'Account',
                actionName: 'view'
            }
        });
    }

    navigateToList() {
        this[NavigationMixin.Navigate]({
            type: 'standard__objectPage',
            attributes: {
                objectApiName: 'Account',
                actionName: 'list'
            },
            state: {
                filterName: 'Recent'
            }
        });
    }
}
```

### LWC vs. Apache Wicket Migration

| Wicket Feature | LWC Equivalent | Migration Approach |
|---------------|---------------|-------------------|
| Wicket Component | LWC Component | Rebuild as LWC components |
| Wicket Panel | LWC Component | Modular LWC components |
| Wicket Page | Lightning Page | Use Lightning App Builder |
| Model/LoadableDetachableModel | @wire / Apex | Wire service + Apex controllers |
| Ajax Behaviors | Lightning Data Service | Automatic refresh with LDS |
| Form Validation | HTML5 + Custom Validation | lightning-input validation |
| Component Hierarchy | Component Composition | Nested LWC components |
| Session State | Component State + LDS | Client-side state management |
| Wicket Repeaters | for:each / iterator | Template iteration |
| Feedback Messages | toast events | Lightning toast notifications |

## Visualforce (Legacy UI Framework)

### Overview
- **Type**: Server-side rendered pages
- **Syntax**: JSP-like tag-based markup
- **Use Case**: Legacy applications, complex forms, PDF generation
- **Status**: Maintained but not actively developed (use LWC for new development)

### Comparison to Wicket
Both are server-side rendering frameworks with similar patterns:

| Feature | Wicket | Visualforce |
|---------|--------|-------------|
| Rendering | Server-side | Server-side |
| State Management | Session-based | ViewState |
| Component Model | Java components | Tag-based components |
| Data Binding | Model objects | Controller properties |
| Event Handling | Java methods | Apex controller methods |
| AJAX Support | Yes | Yes (action functions) |

### Example Visualforce Page
```html
<apex:page controller="AccountController">
    <apex:form>
        <apex:pageBlock title="Accounts">
            <apex:pageBlockTable value="{!accounts}" var="acc">
                <apex:column value="{!acc.Name}"/>
                <apex:column value="{!acc.Industry}"/>
                <apex:column>
                    <apex:commandButton value="Edit" action="{!editAccount}">
                        <apex:param name="accId" value="{!acc.Id}"/>
                    </apex:commandButton>
                </apex:column>
            </apex:pageBlockTable>
        </apex:pageBlock>
    </apex:form>
</apex:page>
```

### When to Use Visualforce
1. **PDF Generation**: Render pages as PDF
2. **Legacy Migration**: Interim step before LWC migration
3. **Complex Forms**: Multi-step wizards
4. **Custom Layouts**: Highly customized UIs not possible with Lightning

## Flow Builder (No-Code/Low-Code Automation)

### Overview
- **Type**: Visual workflow automation tool
- **Use Case**: Business process automation, data transformations, guided UI flows
- **Comparison**: Replaces Orienteer BPM module functionality

### Flow Types

#### 1. Screen Flows
- **Purpose**: Guided UI experiences
- **Features**: Multi-step forms, conditional logic, data collection
- **Use Case**: Onboarding wizards, data entry forms, troubleshooting guides

#### 2. Auto-Launched Flows
- **Purpose**: Backend automation
- **Triggers**: Record changes, scheduled, platform events
- **Use Case**: Data validation, calculations, integration

#### 3. Record-Triggered Flows
- **Purpose**: Respond to record changes
- **Triggers**: Before save, after save, delete
- **Use Case**: Field updates, notifications, related record creation

### Flow Capabilities vs. Orienteer BPM

| BPM Feature | Flow Equivalent | Compatibility |
|------------|----------------|---------------|
| Process Definition | Flow Definition | ✅ Similar concept |
| Process Variables | Flow Variables | ✅ Direct mapping |
| User Tasks | Screen Elements | ✅ Interactive screens |
| Service Tasks | Apex Actions | ✅ Custom logic via Apex |
| Decision Gateways | Decision Elements | ✅ Conditional branching |
| Parallel Execution | Parallel Paths | ⚠️ Limited parallelism |
| Timers | Scheduled Paths | ✅ Wait elements |
| Sub-processes | Subflows | ✅ Reusable flows |
| Process Monitoring | Debug Logs + Events | ⚠️ Limited visibility |
| BPMN Modeling | Visual Flow Builder | ⚠️ Different notation |

### Example Flow
```
Flow: New Account Onboarding
1. Screen: Collect Account Information
   - Input: Account Name (required)
   - Input: Industry (picklist)
   - Input: Annual Revenue (number)

2. Decision: Check Industry
   - If Industry = "Technology"
     → Create Record: Technology Contact
     → Send Email: Welcome to Tech Team
   - Else
     → Create Record: Standard Contact
     → Send Email: Welcome

3. Assignment: Set Account Rating
   - If Annual Revenue > 1000000
     → Rating = "Hot"
   - Else
     → Rating = "Warm"

4. Update Record: Account
   - Set Rating field

5. Screen: Confirmation
   - Display: Account created successfully
   - Display: Account ID and Name
```

## Lightning App Builder

### Overview
- **Type**: Declarative page builder
- **Use Case**: Build Lightning pages by dragging and dropping components
- **Comparison**: Replaces Wicket's programmatic panel/widget composition

### Features
- **Component Library**: Standard and custom Lightning components
- **Layout**: Drag-and-drop layout design
- **Filtering**: Component visibility rules
- **Templates**: Standard page templates (record, home, app pages)
- **Activation**: Assign pages to apps, record types, profiles

### Page Types
1. **App Page**: Custom application pages
2. **Home Page**: Custom home page layouts
3. **Record Page**: Custom record detail pages
4. **Email Template**: Lightning email templates

### Comparison to Orienteer Dashboard/Widgets

| Orienteer Feature | Lightning Equivalent | Migration |
|------------------|---------------------|-----------|
| Dashboard | Lightning Home Page | Use App Builder |
| Widget | Lightning Component | Build as LWC |
| Widget Configuration | Component Properties | Configure in App Builder |
| Widget Library | AppExchange + Custom | Use standard + build custom |
| Tab-based Dashboards | Multiple Home Pages | Create multiple pages |
| Role-based Widgets | Component Visibility Rules | Filter by profile/permission |
| Drag-and-drop Layout | App Builder | Direct mapping |

## Integration and APIs

### REST API
```apex
// Apex REST Service
@RestResource(urlMapping='/AccountService/*')
global class AccountRESTService {
    @HttpGet
    global static Account getAccount() {
        RestRequest req = RestContext.request;
        String accountId = req.requestURI.substring(
            req.requestURI.lastIndexOf('/') + 1
        );
        Account result = [SELECT Id, Name, Industry FROM Account WHERE Id = :accountId];
        return result;
    }

    @HttpPost
    global static String createAccount(String name, String industry) {
        Account acc = new Account(Name=name, Industry=industry);
        insert acc;
        return acc.Id;
    }

    @HttpPut
    global static Account updateAccount(String id, String name, String industry) {
        Account acc = new Account(Id=id, Name=name, Industry=industry);
        update acc;
        return acc;
    }

    @HttpDelete
    global static void deleteAccount() {
        RestRequest req = RestContext.request;
        String accountId = req.requestURI.substring(
            req.requestURI.lastIndexOf('/') + 1
        );
        Account acc = new Account(Id=accountId);
        delete acc;
    }
}
```

### SOAP API
```apex
// Apex SOAP Service
global class AccountSOAPService {
    webservice static String createAccount(String name, String industry) {
        Account acc = new Account(Name=name, Industry=industry);
        insert acc;
        return acc.Id;
    }

    webservice static Account getAccount(String accountId) {
        return [SELECT Id, Name, Industry FROM Account WHERE Id = :accountId];
    }
}
```

### External Services (Callouts)
```apex
// HTTP Callout
public class ExternalAPIService {
    public static String callExternalAPI() {
        Http http = new Http();
        HttpRequest request = new HttpRequest();
        request.setEndpoint('https://api.example.com/data');
        request.setMethod('GET');
        request.setHeader('Content-Type', 'application/json');

        HttpResponse response = http.send(request);

        if(response.getStatusCode() == 200) {
            return response.getBody();
        }
        else {
            throw new CalloutException('Error: ' + response.getStatus());
        }
    }
}
```

## Migration Strategy: Orienteer to Salesforce

### Backend Logic Migration (Java → Apex)

#### 1. Service Layer
```java
// Orienteer (Java)
public class AccountService {
    @Inject
    private ODatabaseDocument db;

    public List<ODocument> getAccounts(String industry) {
        return db.query(
            new OSQLSynchQuery<ODocument>(
                "SELECT FROM Account WHERE industry = ?"
            ),
            industry
        );
    }
}
```

```apex
// Salesforce (Apex)
public class AccountService {
    public static List<Account> getAccounts(String industry) {
        return [
            SELECT Id, Name, Industry
            FROM Account
            WHERE Industry = :industry
        ];
    }
}
```

#### 2. Trigger/Event Handlers
```java
// Orienteer (Java) - OClass hook
public class AccountHook extends ODocumentHookAbstract {
    @Override
    public RESULT onRecordBeforeCreate(ODocument doc) {
        if(doc.field("industry") == null) {
            doc.field("industry", "Unknown");
        }
        return RESULT.RECORD_CHANGED;
    }
}
```

```apex
// Salesforce (Apex) - Trigger
trigger AccountTrigger on Account (before insert) {
    for(Account acc : Trigger.new) {
        if(acc.Industry == null) {
            acc.Industry = 'Unknown';
        }
    }
}
```

### Frontend Migration (Wicket → LWC)

#### 1. Component Structure
```java
// Orienteer (Wicket Panel)
public class AccountPanel extends GenericPanel<ODocument> {
    public AccountPanel(String id, IModel<ODocument> model) {
        super(id, model);
        add(new Label("name", new PropertyModel<>(model, "name")));
        add(new Label("industry", new PropertyModel<>(model, "industry")));
    }
}
```

```javascript
// Salesforce (LWC)
import { LightningElement, api } from 'lwc';

export default class AccountPanel extends LightningElement {
    @api account;

    get name() {
        return this.account.Name;
    }

    get industry() {
        return this.account.Industry;
    }
}
```

```html
<!-- accountPanel.html -->
<template>
    <div>
        <p>Name: {name}</p>
        <p>Industry: {industry}</p>
    </div>
</template>
```

#### 2. Data Tables
```java
// Orienteer (Wicket)
public class AccountTablePanel extends AbstractWidget<ODocument> {
    public AccountTablePanel(String id) {
        super(id);
        IColumn<ODocument, String>[] columns = new IColumn[] {
            new PropertyColumn<>(Model.of("Name"), "name"),
            new PropertyColumn<>(Model.of("Industry"), "industry")
        };
        add(new OrienteerDataTable<>("table", columns, provider, 20));
    }
}
```

```html
<!-- Salesforce (LWC) -->
<template>
    <lightning-datatable
        key-field="Id"
        data={accounts}
        columns={columns}>
    </lightning-datatable>
</template>
```

```javascript
// accountTable.js
import { LightningElement, wire } from 'lwc';
import getAccounts from '@salesforce/apex/AccountController.getAccounts';

const COLUMNS = [
    { label: 'Name', fieldName: 'Name' },
    { label: 'Industry', fieldName: 'Industry' }
];

export default class AccountTable extends LightningElement {
    columns = COLUMNS;
    @wire(getAccounts) accounts;
}
```

## Development Tools and Process

### Salesforce DX (SFDX)
- **Purpose**: Modern development workflow
- **Features**:
  - Source-driven development
  - Scratch orgs (ephemeral environments)
  - CLI tools
  - VS Code integration
  - Version control (Git)
  - CI/CD pipelines

### VS Code + Salesforce Extensions
- **IDE**: Visual Studio Code
- **Extensions**:
  - Salesforce Extension Pack
  - Apex Language Support
  - Lightning Web Components
  - Apex Replay Debugger

### Testing
```apex
// Apex Test Class
@isTest
private class AccountServiceTest {
    @isTest
    static void testGetAccounts() {
        // Setup test data
        Account acc = new Account(Name='Test', Industry='Technology');
        insert acc;

        // Execute test
        Test.startTest();
        List<Account> results = AccountService.getAccounts('Technology');
        Test.stopTest();

        // Assertions
        System.assertEquals(1, results.size());
        System.assertEquals('Test', results[0].Name);
    }
}
```

### Deployment
- **Change Sets**: UI-based deployment
- **Metadata API**: Ant-based deployment
- **Salesforce DX**: Modern deployment with SFDX CLI
- **CI/CD**: Jenkins, GitHub Actions, Azure DevOps

## Key Takeaways

### Migration Complexity: **High**
- Complete UI rewrite required (Wicket → LWC)
- Backend logic translation (Java → Apex)
- Different development paradigms
- Learning curve for Salesforce platform

### Recommendations
1. **Prioritize LWC**: Use Lightning Web Components for all new UI
2. **Modular Migration**: Migrate module by module
3. **Leverage Standard Components**: Use Salesforce standard components where possible
4. **Apex Best Practices**: Follow trigger framework, bulkification patterns
5. **Testing**: Maintain 75%+ code coverage (required for deployment)
6. **Training**: Invest in Salesforce developer training

### Timeline Estimate
- **Small Module** (e.g., User Management): 2-4 weeks
- **Medium Module** (e.g., Dashboard): 4-8 weeks
- **Large Module** (e.g., BPM): 8-16 weeks
- **Full Migration**: 6-12 months (depending on complexity)
