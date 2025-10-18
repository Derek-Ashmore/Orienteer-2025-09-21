# Salesforce Governor Limits and Constraints

## Overview
Comprehensive analysis of Salesforce platform limits, constraints, and best practices for migrating Orienteer (<500MB data, 20+ modules).

## Understanding Governor Limits

### What Are Governor Limits?
- **Purpose**: Ensure fair resource usage in multi-tenant environment
- **Scope**: Per-transaction limits (Apex execution context)
- **Enforcement**: Automatic, non-configurable
- **Impact**: Code must be designed for bulk processing

### Multi-Tenancy Impact
Salesforce is a multi-tenant platform where multiple customers share the same infrastructure. Governor limits prevent any single tenant from monopolizing resources.

## Per-Transaction Apex Limits

### DML Operations
| Limit | Synchronous | Asynchronous |
|-------|------------|--------------|
| **DML Statements** | 150 | 150 |
| **Records Processed by DML** | 10,000 | 10,000 |
| **Total Records Retrieved by SOQL** | 50,000 | 50,000 |
| **Total Records Retrieved by SOSL** | 2,000 | 2,000 |
| **SOQL Queries** | 100 | 200 |
| **SOSL Queries** | 20 | 20 |

**Example Violation**:
```apex
// ❌ BAD: DML in loop (can hit 150 DML limit)
for(Account acc : accounts) {
    update acc;  // Separate DML per record
}

// ✅ GOOD: Bulk DML
List<Account> accountsToUpdate = new List<Account>();
for(Account acc : accounts) {
    // Modify account
    accountsToUpdate.add(acc);
}
update accountsToUpdate;  // Single DML for all
```

### SOQL Query Limits
| Limit | Value |
|-------|-------|
| **Total SOQL queries** | 100 (sync), 200 (async) |
| **Total records from SOQL** | 50,000 |
| **Total records from SOQL (selector)** | 50,000 |
| **SOQL query rows** | 50,000 per query |

**Example Violation**:
```apex
// ❌ BAD: Query in loop
for(Contact con : contacts) {
    Account acc = [SELECT Id, Name FROM Account WHERE Id = :con.AccountId];
    // Process
}

// ✅ GOOD: Single query with relationship
Set<Id> accountIds = new Set<Id>();
for(Contact con : contacts) {
    accountIds.add(con.AccountId);
}
List<Account> accounts = [SELECT Id, Name FROM Account WHERE Id IN :accountIds];
Map<Id, Account> accountMap = new Map<Id, Account>(accounts);

for(Contact con : contacts) {
    Account acc = accountMap.get(con.AccountId);
    // Process
}

// ✅ BETTER: Use relationship query
List<Contact> contactsWithAccounts = [
    SELECT Id, Name, Account.Id, Account.Name
    FROM Contact
    WHERE Id IN :contactIds
];
```

### CPU Time Limits
| Limit | Synchronous | Asynchronous |
|-------|------------|--------------|
| **CPU Time** | 10,000 ms (10 sec) | 60,000 ms (60 sec) |

**What Counts as CPU Time**:
- Apex code execution
- Formula evaluation
- Validation rules
- Workflow rules

**What Does NOT Count**:
- Database time (SOQL, DML)
- Callout time
- ViewState serialization

**Example Optimization**:
```apex
// ❌ BAD: Complex nested loops
for(Account acc : accounts) {
    for(Contact con : contacts) {
        for(Opportunity opp : opportunities) {
            // O(n³) complexity - CPU intensive
        }
    }
}

// ✅ GOOD: Use maps for lookup
Map<Id, List<Contact>> contactsByAccount = new Map<Id, List<Contact>>();
for(Contact con : contacts) {
    if(!contactsByAccount.containsKey(con.AccountId)) {
        contactsByAccount.put(con.AccountId, new List<Contact>());
    }
    contactsByAccount.get(con.AccountId).add(con);
}

for(Account acc : accounts) {
    List<Contact> relatedContacts = contactsByAccount.get(acc.Id);
    // O(n) complexity
}
```

### Heap Size Limits
| Limit | Synchronous | Asynchronous |
|-------|------------|--------------|
| **Heap Size** | 6 MB | 12 MB |

**What Uses Heap**:
- Variables
- Collections (Lists, Sets, Maps)
- Objects in memory
- String concatenation

**Example Violation**:
```apex
// ❌ BAD: Large collections in memory
List<Account> allAccounts = [SELECT Id, Name, Description, ... FROM Account];
// If 50,000 accounts with many fields, can exceed heap

// ✅ GOOD: Query in batches
for(List<Account> accountBatch : [SELECT Id, Name FROM Account]) {
    // Process batch (default 200 records)
    // Each batch iteration has separate heap
}
```

### Callout Limits
| Limit | Value |
|-------|-------|
| **Maximum callouts** | 100 per transaction |
| **Maximum callout time** | 120 seconds total |
| **Maximum response size** | 6 MB (synchronous), 12 MB (asynchronous) |

**Example**:
```apex
// ✅ GOOD: Callout best practices
public class ExternalAPIService {
    private static final Integer TIMEOUT = 30000; // 30 seconds

    public static String callAPI(String endpoint) {
        Http http = new Http();
        HttpRequest req = new HttpRequest();
        req.setEndpoint(endpoint);
        req.setMethod('GET');
        req.setTimeout(TIMEOUT);

        HttpResponse res = http.send(req);

        if(res.getStatusCode() == 200) {
            return res.getBody();
        }
        throw new CalloutException('API Error: ' + res.getStatus());
    }
}
```

### Email Limits
| Limit | Value |
|-------|-------|
| **Single email messages** | 10 per transaction |
| **Mass email invocations** | 10 per transaction |
| **Total recipients (mass + single)** | 5,000 per transaction |

**Daily Limits**:
- **Single Email**: 5,000 per org per day
- **Mass Email**: Based on Salesforce edition

## Organization-Wide Limits

### Data Storage Limits

| Edition | Storage per Org | Storage per User License |
|---------|----------------|-------------------------|
| **Developer Edition** | 5 MB data + 20 MB files | N/A |
| **Professional** | 10 GB | 20 MB per user (data), 2 GB per user (files) |
| **Enterprise** | 10 GB | 20 MB per user (data), 2 GB per user (files) |
| **Performance** | 10 GB | 20 MB per user (data), 2 GB per user (files) |
| **Unlimited** | 10 GB | 20 MB per user (data), 2 GB per user (files) |

**Formula**: Base Storage + (User Licenses × Per-User Storage)

**Example**: Enterprise with 100 users
- Data Storage: 10 GB + (100 × 20 MB) = 10 GB + 2 GB = 12 GB
- File Storage: 10 GB + (100 × 2 GB) = 10 GB + 200 GB = 210 GB

**Orienteer Migration Impact**:
- Current OrientDB size: <500 MB
- Salesforce minimum: 10 GB base
- ✅ **Sufficient storage** for current data volume

### Custom Object Limits

| Edition | Custom Objects | Custom Fields per Object |
|---------|---------------|-------------------------|
| **Professional** | 200 | 500 |
| **Enterprise** | 2,000 | 800 |
| **Unlimited** | 3,000 | 800 |
| **Developer Edition** | Unlimited (standard limits) | 800 |

**Orienteer Modules**: 20+ modules with various entities
- Estimated custom objects needed: 50-100
- ✅ **Well within Enterprise edition limits**

### API Call Limits (Daily)

| License Type | API Calls per 24 Hours |
|-------------|----------------------|
| **Professional** | 1,000 base + (1,000 × users) |
| **Enterprise** | 1,000 base + (1,000 × users) |
| **Performance** | 1,000 base + (2,000 × users) |
| **Unlimited** | 1,000 base + (5,000 × users) |
| **Developer Edition** | 15,000 |

**Calculation Example**: 100 Enterprise users
- API Calls = 1,000 + (100 × 1,000) = 101,000 calls/day
- **Per minute**: ~70 calls/minute average
- **Per hour**: ~4,208 calls/hour

**Orienteer Integration Needs**:
- Apache Camel integration routes: Moderate API usage
- Real-time sync requirements: May need optimization
- **Recommendation**: Use Platform Events to reduce API calls

### Record Limits

| Limit Type | Value |
|-----------|-------|
| **Accounts** | Unlimited (performance degrades >10M) |
| **Custom Objects** | Unlimited (same performance note) |
| **Reports/Dashboards** | Unlimited |
| **List Views** | 100 recent per user |

**Performance Best Practices**:
- **Under 10 million records**: Standard performance
- **10-100 million records**: Use custom indexes, selective queries
- **Over 100 million records**: Consider data archiving, big object usage

**Orienteer Data Volume**: <500 MB total
- Estimated records: Tens of thousands to low hundreds of thousands
- ✅ **No performance concerns** for current volume

## Sharing and Security Limits

### Sharing Rules
| Limit | Value |
|-------|-------|
| **Ownership-based sharing rules** | 300 per object |
| **Criteria-based sharing rules** | 50 per object |
| **Total sharing rules** | 300 per object |
| **Share objects (total)** | 10 million |

**Sharing Recalculation**:
- **Trigger**: Role hierarchy changes, OWD changes, sharing rule changes
- **Time**: Can take hours for large data volumes
- **Best Practice**: Schedule during off-hours

### Role Hierarchy
| Limit | Value |
|-------|-------|
| **Maximum depth** | 500 levels (recommended: 10-15) |
| **Roles per org** | Unlimited (performance impact >1,000) |

**Orienteer Security Model**:
- Role-based with inheritance
- Multiple roles per user
- **Mapping**: Use permission sets + role hierarchy
- ✅ **Salesforce structure sufficient**

## Bulk API Limits

### Bulk API 2.0 Limits

| Limit | Value |
|-------|-------|
| **Batches per 24 hours** | 15,000 |
| **Records per 24 hours** | 150 million |
| **Batch size** | Up to 100 MB |
| **Job duration** | Up to 48 hours |

**Use Cases for Bulk API**:
1. **Data Migration**: Initial Orienteer data load (<500 MB)
2. **Large Batch Updates**: Periodic bulk operations
3. **ETL Processes**: Integration with external systems

**Orienteer Migration**:
- Total data: <500 MB
- Estimated time via Bulk API: 1-2 hours
- ✅ **Well within limits** for one-time migration

## Flow and Process Limits

### Flow Execution Limits

| Limit | Per Flow Interview | Notes |
|-------|-------------------|-------|
| **DML statements** | 150 | Same as Apex |
| **SOQL queries** | 100 | Same as Apex |
| **CPU time** | 10,000 ms (sync) | Same as Apex |
| **Heap size** | 6 MB | Same as Apex |
| **Elements executed** | 2,000 | Flow-specific |

**Flow vs. Apex**:
- Flows have same governor limits as Apex
- Complex logic may require Apex invocable methods
- **Orienteer BPM Migration**: Some processes may need Apex due to complexity

### Process Builder Limits (Deprecated)

| Limit | Value |
|-------|-------|
| **Active processes per object** | No hard limit (performance degrades) |
| **Actions per criteria** | No hard limit |

**Note**: Process Builder is deprecated. Use Record-Triggered Flows instead.

## Lightning Component Limits

### Lightning Web Component Limits

| Limit | Value |
|-------|-------|
| **Components per page** | No hard limit (performance consideration) |
| **Aura-enabled Apex methods** | Counts toward SOQL/DML limits |
| **LDS wire calls** | Cached automatically |

**Best Practices**:
- Use Lightning Data Service (LDS) for automatic caching
- Minimize Apex callouts
- Optimize component hierarchy

## Integration Limits

### Platform Events

| Limit | Value | Notes |
|-------|-------|-------|
| **Event deliveries per hour** | 250,000 (standard), 1M+ (high volume) | Enterprise and Unlimited editions |
| **Event publish allocations** | 250,000 per 24 hours | Per org |
| **Retention** | 72 hours (standard), 7 days (high volume) | |

**Orienteer Integration Needs**:
- Apache Camel JMS replacement
- Event-driven architecture
- ✅ **Platform Events sufficient** for moderate event volume

### Change Data Capture

| Limit | Value |
|-------|-------|
| **Events published per hour** | 100,000-500,000 (varies by edition) |
| **Entities tracked** | 5 (standard), more with add-on |
| **Event retention** | 3 days |

**Use Case**: Real-time data synchronization with external systems

## File Storage Limits

### ContentVersion (Files)

| Limit | Value |
|-------|-------|
| **Maximum file size** | 2 GB per file (most editions) |
| **Files API downloads** | 20,000 per 24 hours |
| **Total file storage** | Based on edition + user licenses |

**Attachment (Legacy)**:

| Limit | Value |
|-------|-------|
| **Maximum file size** | 25 MB per file |
| **Recommended**: Use ContentVersion instead |

**Orienteer Document Management**:
- Pages module with attachments
- BIRT reports (PDF generation)
- ✅ **Salesforce file storage adequate**

## Asynchronous Processing Limits

### Queueable Apex

| Limit | Synchronous | Asynchronous |
|-------|------------|--------------|
| **Queueable jobs added** | 50 | 1 |
| **Maximum stack depth** | 5 chained jobs | |

**Use Cases**:
- Long-running processes
- Chained asynchronous operations
- External callouts

### Batch Apex

| Limit | Value |
|-------|-------|
| **Concurrent batch jobs** | 5 |
| **Batch jobs queued** | 100 |
| **Records per batch** | 200 (default), max 2,000 |
| **Start method SOQL rows** | 50 million |

**Use Cases**:
- Process millions of records
- Complex data transformations
- Scheduled maintenance tasks

**Example**:
```apex
global class AccountBatchProcessor implements Database.Batchable<SObject> {
    global Database.QueryLocator start(Database.BatchableContext bc) {
        return Database.getQueryLocator([
            SELECT Id, Name, Industry
            FROM Account
            WHERE Industry = 'Technology'
        ]);
    }

    global void execute(Database.BatchableContext bc, List<Account> scope) {
        // Process batch of 200 records
        for(Account acc : scope) {
            // Processing logic
        }
        update scope;
    }

    global void finish(Database.BatchableContext bc) {
        // Post-processing
    }
}

// Execute batch
Database.executeBatch(new AccountBatchProcessor(), 200);
```

### Future Methods

| Limit | Value |
|-------|-------|
| **Future calls per transaction** | 50 |
| **Method executions per 24 hours** | 250,000 (Enterprise and Unlimited) |

**Use Cases**:
- Callouts from triggers
- Asynchronous processing
- Operations that don't need chaining

## Email Limits

### Single Email Messages

| Limit | Value |
|-------|-------|
| **Per Apex transaction** | 10 |
| **Per org per day** | 5,000 (most editions) |

### Mass Email

| Limit | Value |
|-------|-------|
| **Invocations per day** | 5,000 |
| **Recipients per invocation** | 5,000 |
| **Total recipients per day** | Based on user licenses |

**Orienteer Notification Module**:
- Email notifications
- In-app notifications
- SMS (via Twilio)
- ✅ **Salesforce email limits sufficient** for most use cases
- **Alternative**: Use external email service (SendGrid, etc.) for high-volume

## Best Practices for Governor Limits

### 1. Bulkification
Always design code to handle multiple records:

```apex
// ❌ BAD: Non-bulkified trigger
trigger AccountTrigger on Account (after insert) {
    for(Account acc : Trigger.new) {
        Contact con = new Contact(
            FirstName = 'Primary',
            LastName = 'Contact',
            AccountId = acc.Id
        );
        insert con; // DML in loop!
    }
}

// ✅ GOOD: Bulkified trigger
trigger AccountTrigger on Account (after insert) {
    List<Contact> contacts = new List<Contact>();

    for(Account acc : Trigger.new) {
        contacts.add(new Contact(
            FirstName = 'Primary',
            LastName = 'Contact',
            AccountId = acc.Id
        ));
    }

    insert contacts; // Single DML
}
```

### 2. SOQL Best Practices

```apex
// ❌ BAD: Multiple queries
for(Account acc : accounts) {
    List<Contact> contacts = [SELECT Id FROM Contact WHERE AccountId = :acc.Id];
}

// ✅ GOOD: Single query with relationship
List<Account> accountsWithContacts = [
    SELECT Id, Name,
           (SELECT Id, Name FROM Contacts)
    FROM Account
    WHERE Id IN :accountIds
];
```

### 3. Use Maps for Lookups

```apex
// ❌ BAD: Nested loops
for(Contact con : contacts) {
    for(Account acc : accounts) {
        if(con.AccountId == acc.Id) {
            // Process
        }
    }
}

// ✅ GOOD: Map lookup
Map<Id, Account> accountMap = new Map<Id, Account>(accounts);
for(Contact con : contacts) {
    Account acc = accountMap.get(con.AccountId);
    if(acc != null) {
        // Process
    }
}
```

### 4. Asynchronous Processing

```apex
// ❌ BAD: Long-running synchronous process
public void processLargeDataset() {
    List<Account> allAccounts = [SELECT Id FROM Account]; // 50,000 records
    for(Account acc : allAccounts) {
        // Complex processing - will hit CPU limit
    }
}

// ✅ GOOD: Use Batch Apex
global class AccountProcessor implements Database.Batchable<SObject> {
    global Database.QueryLocator start(Database.BatchableContext bc) {
        return Database.getQueryLocator([SELECT Id FROM Account]);
    }

    global void execute(Database.BatchableContext bc, List<Account> scope) {
        // Process 200 records at a time
        for(Account acc : scope) {
            // Complex processing
        }
    }

    global void finish(Database.BatchableContext bc) {
        // Completion logic
    }
}
```

### 5. Query Optimization

```apex
// ❌ BAD: Non-selective query
List<Account> accounts = [SELECT Id FROM Account];

// ✅ GOOD: Selective query with indexed field
List<Account> accounts = [
    SELECT Id, Name
    FROM Account
    WHERE Industry = 'Technology'
    AND CreatedDate = LAST_N_DAYS:30
    LIMIT 10000
];
```

### 6. Limit Monitoring

```apex
public class LimitChecker {
    public static void logLimits() {
        System.debug('SOQL Queries: ' + Limits.getQueries() + '/' + Limits.getLimitQueries());
        System.debug('DML Statements: ' + Limits.getDmlStatements() + '/' + Limits.getLimitDmlStatements());
        System.debug('DML Rows: ' + Limits.getDmlRows() + '/' + Limits.getLimitDmlRows());
        System.debug('CPU Time: ' + Limits.getCpuTime() + '/' + Limits.getLimitCpuTime());
        System.debug('Heap Size: ' + Limits.getHeapSize() + '/' + Limits.getLimitHeapSize());
        System.debug('Callouts: ' + Limits.getCallouts() + '/' + Limits.getLimitCallouts());
    }
}
```

## Orienteer Migration Considerations

### Current Orienteer Scale
- **Data Volume**: <500 MB
- **Modules**: 20+ functional modules
- **Users**: Unknown (estimate 10-100 based on small data volume)
- **Integration**: Apache Camel routes (moderate volume)

### Salesforce Limits Assessment

| Concern | Orienteer Need | Salesforce Limit | Assessment |
|---------|---------------|------------------|------------|
| **Data Storage** | <500 MB | 10 GB+ | ✅ Sufficient (20x overhead) |
| **Custom Objects** | 50-100 estimated | 2,000 (Enterprise) | ✅ Sufficient (20x overhead) |
| **API Calls** | Moderate (Camel integration) | 101,000/day (100 users) | ✅ Sufficient with optimization |
| **Bulk Data Load** | One-time <500 MB | 150M records/day | ✅ Sufficient |
| **Users** | 10-100 estimated | Unlimited | ✅ No constraint |
| **File Storage** | Document management | 210 GB+ (100 users) | ✅ Sufficient |
| **Email** | Notification module | 5,000/day | ⚠️ May need external service |
| **Workflow** | BPM module | Flow limits | ✅ Sufficient for most processes |

### Recommended Salesforce Edition

**Enterprise Edition**:
- ✅ 2,000 custom objects (sufficient for 50-100 needed)
- ✅ 1,000 + (1,000 × users) API calls/day
- ✅ 10 GB + (20 MB × users) data storage
- ✅ 10 GB + (2 GB × users) file storage
- ✅ Platform Events, Change Data Capture
- ✅ Advanced security features
- ✅ Apex, LWC, Flow Builder

**Cost Consideration**: Performance or Unlimited editions offer more API calls but at higher cost. Enterprise sufficient for current scale.

### Migration Strategy for Limits

#### 1. API Call Optimization
- **Use Platform Events**: Reduce polling API calls
- **Batch Operations**: Use Composite API
- **Caching**: Implement client-side caching
- **Change Data Capture**: Subscribe to changes vs. polling

#### 2. Data Migration
- **Bulk API 2.0**: For one-time migration of <500 MB
- **Batch Size**: Optimize for performance (100 MB batches)
- **Validation**: Post-migration data integrity checks

#### 3. Integration Migration
- **Camel to Platform Events**: Event-driven integration
- **Scheduled Apex**: Replace polling routes
- **REST APIs**: Direct API integration where needed
- **Named Credentials**: Centralize authentication

#### 4. Complex Processes
- **Batch Apex**: For long-running processes
- **Queueable Apex**: For chained asynchronous tasks
- **Flow Builder**: For moderate complexity workflows
- **Apex**: For CPU-intensive or complex logic

### Potential Bottlenecks

1. **Email Volume**: If notification module sends >5,000 emails/day
   - **Solution**: Integrate with SendGrid, Mailchimp, etc.

2. **Complex BPM Processes**: If processes exceed Flow limits
   - **Solution**: Break into Apex-based custom logic

3. **Real-time Integration**: If Camel routes require sub-second response
   - **Solution**: Use Platform Events + external middleware (MuleSoft)

4. **Large Reports**: BIRT reports with >50,000 rows
   - **Solution**: Use Batch Apex to generate reports asynchronously

## Monitoring and Optimization

### 1. Organization Limits Monitoring
- **Setup → System Overview**: View storage, API usage
- **API Usage Dashboard**: Track daily API calls
- **Storage Usage**: Monitor data and file storage

### 2. Apex Execution Monitoring
- **Debug Logs**: Track governor limit consumption
- **Event Monitoring**: Track API calls, logins, reports
- **Developer Console**: Real-time debugging

### 3. Optimization Tools
- **Query Plan Tool**: Analyze SOQL query performance
- **Bulk API Jobs**: Monitor batch job performance
- **Platform Event Monitoring**: Track event delivery

### 4. Alerting
- **Email Alerts**: When approaching 80% of API limit
- **Custom Notifications**: Governor limit exceptions
- **Health Check**: Regular limit consumption reports

## Key Takeaways

### Orienteer Migration Feasibility: ✅ **FEASIBLE**

**Reasons**:
1. ✅ **Data Volume**: <500 MB well within Salesforce limits
2. ✅ **Custom Objects**: 50-100 needed, 2,000 available (Enterprise)
3. ✅ **API Calls**: Current scale fits within Enterprise limits
4. ✅ **Storage**: Ample data and file storage
5. ✅ **Functionality**: Salesforce features cover Orienteer capabilities

### Constraints to Plan For

1. ⚠️ **Governor Limits**: Code must be bulkified
2. ⚠️ **API Limits**: Need to optimize integration patterns
3. ⚠️ **Email Limits**: May need external email service
4. ⚠️ **CPU Time**: Complex logic may need optimization
5. ⚠️ **Learning Curve**: Developers need Salesforce training

### Success Factors

1. **Design for Bulk**: Always handle multiple records
2. **Async Processing**: Use Batch Apex for large operations
3. **Event-Driven**: Leverage Platform Events
4. **Monitoring**: Track limit consumption proactively
5. **Testing**: Load test to verify limits not exceeded

### Recommendations

1. **Start with Enterprise Edition**: Sufficient for current scale
2. **Optimize Integrations**: Use Platform Events, CDC
3. **External Email Service**: For high-volume notifications
4. **Developer Training**: Apex best practices, bulkification
5. **Monitoring Setup**: Track API usage, storage, limits
