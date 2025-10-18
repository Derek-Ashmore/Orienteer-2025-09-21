# Salesforce Integration Capabilities

## Overview
Analysis of Salesforce integration options for migrating Orienteer's Apache Camel-based integration platform and external system connectivity.

## Integration Architecture Patterns

### Salesforce Integration Layers

```
External Systems
       ↓
[Integration Layer]
  - REST/SOAP APIs
  - Platform Events
  - Change Data Capture
  - MuleSoft/Integration Tools
       ↓
[Salesforce Platform]
  - Standard Objects
  - Custom Objects
  - Apex Processing
  - Flows/Process
       ↓
[User Interface]
  - Lightning Components
  - Mobile Apps
  - Community/Portal
```

## REST API

### Overview
- **Type**: RESTful web services
- **Authentication**: OAuth 2.0, Session-based
- **Format**: JSON or XML
- **Rate Limits**: API call limits per 24 hours

### API Capabilities

#### 1. Standard REST API
Access Salesforce data via REST endpoints:

**Base URL**: `https://[instance].salesforce.com/services/data/v58.0/`

**Common Operations**:
```bash
# Query records (SOQL)
GET /services/data/v58.0/query?q=SELECT+Id,Name+FROM+Account

# Get record by ID
GET /services/data/v58.0/sobjects/Account/001XXXXXXXXXXXXXXX

# Create record
POST /services/data/v58.0/sobjects/Account
Body: { "Name": "New Account", "Industry": "Technology" }

# Update record
PATCH /services/data/v58.0/sobjects/Account/001XXXXXXXXXXXXXXX
Body: { "Industry": "Finance" }

# Delete record
DELETE /services/data/v58.0/sobjects/Account/001XXXXXXXXXXXXXXX

# Upsert (by external ID)
PATCH /services/data/v58.0/sobjects/Account/External_ID__c/EXT-12345
Body: { "Name": "Upserted Account" }

# Bulk query (up to 50,000 records)
GET /services/data/v58.0/query?q=SELECT+Id+FROM+Account
```

#### 2. Composite REST API
Batch multiple operations in single request:

```json
POST /services/data/v58.0/composite

{
  "allOrNone": true,
  "compositeRequest": [
    {
      "method": "POST",
      "url": "/services/data/v58.0/sobjects/Account",
      "referenceId": "refAccount",
      "body": { "Name": "Parent Account" }
    },
    {
      "method": "POST",
      "url": "/services/data/v58.0/sobjects/Contact",
      "referenceId": "refContact",
      "body": {
        "LastName": "Smith",
        "AccountId": "@{refAccount.id}"
      }
    }
  ]
}
```

**Benefits**:
- Reduces API call count
- Supports cross-object references
- All-or-none transaction support
- Up to 25 subrequests per call

#### 3. Bulk API 2.0
For large data operations:

**Use Cases**:
- Loading millions of records
- Data migration
- Extract-Transform-Load (ETL)
- Mass updates/deletes

**Process**:
```bash
# 1. Create job
POST /services/data/v58.0/jobs/ingest
Body: {
  "object": "Account",
  "operation": "insert",
  "lineEnding": "LF"
}

# 2. Upload CSV data
PUT /services/data/v58.0/jobs/ingest/{jobId}/batches
Content-Type: text/csv
Body: CSV data

# 3. Close job
PATCH /services/data/v58.0/jobs/ingest/{jobId}
Body: { "state": "UploadComplete" }

# 4. Check status
GET /services/data/v58.0/jobs/ingest/{jobId}

# 5. Get results
GET /services/data/v58.0/jobs/ingest/{jobId}/successfulResults
GET /services/data/v58.0/jobs/ingest/{jobId}/failedResults
```

**Limits**:
- 150 million records per rolling 24 hours
- 10,000 batches per rolling 24 hours
- 100 MB per batch

### Custom REST APIs (Apex REST)

Create custom REST endpoints:

```apex
@RestResource(urlMapping='/orders/*')
global class OrderRESTService {

    @HttpGet
    global static OrderResponse getOrder() {
        RestRequest req = RestContext.request;
        String orderId = req.requestURI.substring(req.requestURI.lastIndexOf('/')+1);

        Order__c order = [
            SELECT Id, Name, Status__c, Total_Amount__c,
                   (SELECT Product__c, Quantity__c, Price__c FROM Order_Items__r)
            FROM Order__c
            WHERE Id = :orderId
        ];

        return new OrderResponse(order);
    }

    @HttpPost
    global static OrderResponse createOrder(OrderRequest request) {
        Order__c order = new Order__c(
            Customer__c = request.customerId,
            Status__c = 'New'
        );
        insert order;

        List<Order_Item__c> items = new List<Order_Item__c>();
        for(OrderRequest.Item reqItem : request.items) {
            items.add(new Order_Item__c(
                Order__c = order.Id,
                Product__c = reqItem.productId,
                Quantity__c = reqItem.quantity,
                Price__c = reqItem.price
            ));
        }
        insert items;

        return new OrderResponse([SELECT Id, Name FROM Order__c WHERE Id = :order.Id]);
    }

    global class OrderRequest {
        public String customerId;
        public List<Item> items;

        global class Item {
            public String productId;
            public Decimal quantity;
            public Decimal price;
        }
    }

    global class OrderResponse {
        public String orderId;
        public String orderNumber;
        public String status;

        public OrderResponse(Order__c order) {
            this.orderId = order.Id;
            this.orderNumber = order.Name;
            this.status = order.Status__c;
        }
    }
}
```

**Usage**:
```bash
# GET request
GET https://instance.salesforce.com/services/apexrest/orders/a00XXXXXXXXX

# POST request
POST https://instance.salesforce.com/services/apexrest/orders
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "customerId": "001XXXXXXXXX",
  "items": [
    { "productId": "01tXXXXXXXXXX", "quantity": 2, "price": 99.99 },
    { "productId": "01tYYYYYYYYYY", "quantity": 1, "price": 149.99 }
  ]
}
```

## SOAP API

### Overview
- **Type**: SOAP-based web services
- **WSDL**: Enterprise WSDL, Partner WSDL, Metadata WSDL
- **Format**: XML
- **Use Case**: Legacy system integration, .NET applications

### WSDL Types

#### 1. Enterprise WSDL
- **Strongly typed**: Specific to your org schema
- **Use Case**: Type-safe integration
- **Generation**: Download from Setup → API
- **Pros**: Compile-time type checking
- **Cons**: Must regenerate when schema changes

#### 2. Partner WSDL
- **Loosely typed**: Generic sObject
- **Use Case**: Multi-org or dynamic integrations
- **Generation**: Standard WSDL, no regeneration needed
- **Pros**: Works across orgs, no regeneration
- **Cons**: Requires runtime type casting

### Example SOAP Operations

```xml
<!-- Login -->
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:urn="urn:enterprise.soap.sforce.com">
   <soapenv:Body>
      <urn:login>
         <urn:username>user@example.com</urn:username>
         <urn:password>password{security_token}</urn:password>
      </urn:login>
   </soapenv:Body>
</soapenv:Envelope>

<!-- Create Record -->
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:urn="urn:enterprise.soap.sforce.com"
                  xmlns:urn1="urn:sobject.enterprise.soap.sforce.com">
   <soapenv:Header>
      <urn:SessionHeader>
         <urn:sessionId>{session_id}</urn:sessionId>
      </urn:SessionHeader>
   </soapenv:Header>
   <soapenv:Body>
      <urn:create>
         <urn:sObjects>
            <urn1:type>Account</urn1:type>
            <urn1:Name>New Account</urn1:Name>
            <urn1:Industry>Technology</urn1:Industry>
         </urn:sObjects>
      </urn:create>
   </soapenv:Body>
</soapenv:Envelope>
```

### Apex SOAP Services

Create custom SOAP web services:

```apex
global class AccountSOAPService {

    webservice static Account getAccount(Id accountId) {
        return [SELECT Id, Name, Industry FROM Account WHERE Id = :accountId];
    }

    webservice static Id createAccount(String name, String industry) {
        Account acc = new Account(Name=name, Industry=industry);
        insert acc;
        return acc.Id;
    }

    webservice static void updateAccount(Id accountId, String name, String industry) {
        Account acc = new Account(Id=accountId, Name=name, Industry=industry);
        update acc;
    }

    webservice static AccountWrapper getAccountWithContacts(Id accountId) {
        Account acc = [
            SELECT Id, Name, Industry,
                   (SELECT Id, FirstName, LastName FROM Contacts)
            FROM Account
            WHERE Id = :accountId
        ];
        return new AccountWrapper(acc);
    }

    global class AccountWrapper {
        webservice String accountName;
        webservice String industry;
        webservice List<ContactWrapper> contacts;

        public AccountWrapper(Account acc) {
            this.accountName = acc.Name;
            this.industry = acc.Industry;
            this.contacts = new List<ContactWrapper>();
            for(Contact c : acc.Contacts) {
                this.contacts.add(new ContactWrapper(c));
            }
        }
    }

    global class ContactWrapper {
        webservice String firstName;
        webservice String lastName;

        public ContactWrapper(Contact c) {
            this.firstName = c.FirstName;
            this.lastName = c.LastName;
        }
    }
}
```

**WSDL Generation**: Automatically generated at:
`https://instance.salesforce.com/services/wsdl/class/AccountSOAPService`

## Platform Events

### Overview
- **Type**: Event-driven architecture
- **Pattern**: Publish-Subscribe messaging
- **Delivery**: Near real-time (within seconds)
- **Retention**: 72 hours (default), up to 7 days (High Volume)

### Use Cases
1. **System Integration**: Notify external systems of Salesforce changes
2. **Microservices**: Decouple services via event messaging
3. **Real-time Updates**: Push notifications to connected apps
4. **IoT Integration**: Process sensor data streams
5. **Audit Trail**: External audit logging

### Platform Event Definition

```xml
<!-- Platform Event: Order_Placed__e -->
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <deploymentStatus>Deployed</deploymentStatus>
    <eventType>HighVolume</eventType>
    <label>Order Placed</label>
    <pluralLabel>Orders Placed</pluralLabel>
    <fields>
        <fullName>Order_Id__c</fullName>
        <label>Order ID</label>
        <type>Text</type>
        <length>18</length>
        <required>true</required>
    </fields>
    <fields>
        <fullName>Customer_Id__c</fullName>
        <label>Customer ID</label>
        <type>Text</type>
        <length>18</length>
    </fields>
    <fields>
        <fullName>Total_Amount__c</fullName>
        <label>Total Amount</label>
        <type>Number</type>
        <precision>18</precision>
        <scale>2</scale>
    </fields>
</CustomObject>
```

### Publishing Events (Apex)

```apex
// Publish single event
public class OrderService {
    public static void notifyOrderPlaced(Order__c order) {
        Order_Placed__e event = new Order_Placed__e(
            Order_Id__c = order.Id,
            Customer_Id__c = order.Customer__c,
            Total_Amount__c = order.Total_Amount__c
        );

        Database.SaveResult result = EventBus.publish(event);

        if(!result.isSuccess()) {
            for(Database.Error error : result.getErrors()) {
                System.debug('Error: ' + error.getMessage());
            }
        }
    }

    // Publish bulk events
    public static void notifyMultipleOrders(List<Order__c> orders) {
        List<Order_Placed__e> events = new List<Order_Placed__e>();

        for(Order__c order : orders) {
            events.add(new Order_Placed__e(
                Order_Id__c = order.Id,
                Customer_Id__c = order.Customer__c,
                Total_Amount__c = order.Total_Amount__c
            ));
        }

        List<Database.SaveResult> results = EventBus.publish(events);

        // Check results
        for(Database.SaveResult result : results) {
            if(!result.isSuccess()) {
                // Handle error
            }
        }
    }
}
```

### Subscribing to Events

#### 1. Apex Trigger (Internal)
```apex
trigger OrderPlacedTrigger on Order_Placed__e (after insert) {
    List<Task> tasks = new List<Task>();

    for(Order_Placed__e event : Trigger.new) {
        tasks.add(new Task(
            Subject = 'Follow up on Order: ' + event.Order_Id__c,
            WhatId = event.Order_Id__c,
            Status = 'Not Started',
            Priority = 'Normal'
        ));
    }

    insert tasks;
}
```

#### 2. Lightning Component (LWC)
```javascript
import { LightningElement } from 'lwc';
import { subscribe, unsubscribe, onError } from 'lightning/empApi';

export default class OrderNotifications extends LightningElement {
    channelName = '/event/Order_Placed__e';
    subscription = {};

    connectedCallback() {
        this.handleSubscribe();
    }

    handleSubscribe() {
        const messageCallback = (response) => {
            console.log('Event received: ', JSON.stringify(response));
            // Process event
            const orderId = response.data.payload.Order_Id__c;
            const amount = response.data.payload.Total_Amount__c;
            // Update UI
        };

        subscribe(this.channelName, -1, messageCallback).then(response => {
            this.subscription = response;
        });

        onError(error => {
            console.error('Subscription error: ', error);
        });
    }

    disconnectedCallback() {
        unsubscribe(this.subscription);
    }
}
```

#### 3. External System (CometD)
```java
// Java client using CometD
public class SalesforceEventSubscriber {
    private final BayeuxClient client;

    public void subscribe() {
        client.handshake();
        client.getChannel("/event/Order_Placed__e").subscribe(
            (channel, message) -> {
                Map<String, Object> data = (Map<String, Object>) message.get("data");
                Map<String, Object> payload = (Map<String, Object>) data.get("payload");

                String orderId = (String) payload.get("Order_Id__c");
                Double amount = (Double) payload.get("Total_Amount__c");

                // Process event in external system
                processOrder(orderId, amount);
            }
        );
    }

    private void processOrder(String orderId, Double amount) {
        // External system logic
    }
}
```

## Change Data Capture (CDC)

### Overview
- **Type**: Change notification
- **Purpose**: Near real-time notifications of data changes
- **Delivery**: Asynchronous event messages
- **Scope**: Standard and custom objects

### How It Works
1. Enable CDC for objects
2. Salesforce publishes change events when records are created, updated, or deleted
3. Subscribers receive events via streaming API
4. Events contain before/after field values

### Enable CDC

**Setup UI**:
1. Setup → Integrations → Change Data Capture
2. Select objects to track
3. Save

**Metadata API**:
```xml
<!-- ChangeDataCaptureEnabled object -->
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Account</fullName>
    <changeDataCaptureEnabled>true</changeDataCaptureEnabled>
</CustomObject>
```

### Change Event Schema

**Channel**: `/data/ChangeEvents` (all objects) or `/data/AccountChangeEvent` (specific object)

**Event Payload**:
```json
{
  "data": {
    "schema": "...",
    "payload": {
      "ChangeEventHeader": {
        "commitNumber": 123456789,
        "commitUser": "005xx000001234",
        "sequenceNumber": 1,
        "entityName": "Account",
        "changeType": "UPDATE",
        "changedFields": ["Industry", "AnnualRevenue"],
        "changeOrigin": "com.salesforce.api.soap",
        "transactionKey": "...",
        "commitTimestamp": 1614556800000,
        "recordIds": ["001xx000003gBAA"]
      },
      "Industry": "Technology",
      "AnnualRevenue": 5000000,
      "LastModifiedDate": "2021-03-01T00:00:00.000Z"
    },
    "event": {
      "replayId": 12345678
    }
  }
}
```

### Subscribe to Change Events

```apex
// Apex trigger (internal processing)
trigger AccountChangeTrigger on AccountChangeEvent (after insert) {
    for(AccountChangeEvent event : Trigger.new) {
        EventBus.ChangeEventHeader header = event.ChangeEventHeader;

        if(header.changeType == 'UPDATE') {
            List<String> changedFields = header.changedFields;

            if(changedFields.contains('Industry')) {
                // Industry changed
                String newIndustry = event.Industry;
                // Process change
            }
        }
    }
}
```

```javascript
// LWC subscription
import { subscribe } from 'lightning/empApi';

export default class AccountChanges extends LightningElement {
    connectedCallback() {
        const messageCallback = (response) => {
            const payload = response.data.payload;
            const header = payload.ChangeEventHeader;

            if(header.changeType === 'UPDATE') {
                console.log('Account updated:', header.recordIds);
                console.log('Changed fields:', header.changedFields);
                // Update UI
            }
        };

        subscribe('/data/AccountChangeEvent', -1, messageCallback);
    }
}
```

## Outbound Messages

### Overview
- **Type**: SOAP-based notification
- **Trigger**: Workflow rules or Process Builder
- **Delivery**: Guaranteed delivery with retry
- **Format**: SOAP envelope

### Configuration

1. **Create Outbound Message** (Setup → Workflow Outbound Messages)
   - Select Object
   - Choose Fields to Send
   - Endpoint URL (external service)
   - User context

2. **Create Workflow Rule**
   - Evaluation Criteria: When record created/edited
   - Rule Criteria: Conditions
   - Immediate Workflow Action: Send Outbound Message

### Example Outbound Message

**SOAP Payload**:
```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:out="http://soap.sforce.com/2005/09/outbound">
   <soapenv:Body>
      <out:notifications>
         <out:OrganizationId>00Dxx0000001234</out:OrganizationId>
         <out:ActionId>04kxx0000000001</out:ActionId>
         <out:SessionId>...</out:SessionId>
         <out:EnterpriseUrl>https://instance.salesforce.com/services/Soap/c/58.0/...</out:EnterpriseUrl>
         <out:PartnerUrl>https://instance.salesforce.com/services/Soap/u/58.0/...</out:PartnerUrl>
         <out:Notification>
            <out:Id>04lxx0000000001</out:Id>
            <out:sObject xsi:type="sf:Account" xmlns:sf="urn:sobject.enterprise.soap.sforce.com">
               <sf:Id>001xx000003gBAA</sf:Id>
               <sf:Name>Acme Corporation</sf:Name>
               <sf:Industry>Technology</sf:Industry>
            </out:sObject>
         </out:Notification>
      </out:notifications>
   </soapenv:Body>
</soapenv:Envelope>
```

**Endpoint Response** (acknowledgment):
```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
   <soapenv:Body>
      <notificationsResponse xmlns="http://soap.sforce.com/2005/09/outbound">
         <Ack>true</Ack>
      </notificationsResponse>
   </soapenv:Body>
</soapenv:Envelope>
```

## External Services (Integration with REST APIs)

### Overview
- **Type**: Declarative integration
- **Purpose**: Call external REST APIs from Salesforce
- **Configuration**: Point-and-click, no code
- **Use Cases**: Weather APIs, mapping services, payment gateways

### Setup Process

1. **Import OpenAPI Spec** (Swagger/OpenAPI 2.0 or 3.0)
2. **Configure Authentication** (Named Credentials)
3. **Use in Flows or Apex**

### Example: Weather API Integration

**OpenAPI Spec** (simplified):
```yaml
openapi: 3.0.0
info:
  title: Weather API
  version: 1.0.0
servers:
  - url: https://api.weather.com/v1
paths:
  /current:
    get:
      operationId: getCurrentWeather
      parameters:
        - name: location
          in: query
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Weather data
          content:
            application/json:
              schema:
                type: object
                properties:
                  temperature:
                    type: number
                  conditions:
                    type: string
```

**Usage in Flow**:
1. Add "Action" element
2. Select "External Service: Get Current Weather"
3. Map input (location) from flow variable
4. Process output (temperature, conditions)

**Usage in Apex**:
```apex
// Auto-generated Apex stub class
ExternalService.WeatherAPI weatherAPI = new ExternalService.WeatherAPI();
ExternalService.WeatherAPI.getCurrentWeather_Request request =
    new ExternalService.WeatherAPI.getCurrentWeather_Request();
request.location = 'New York';

ExternalService.WeatherAPI.getCurrentWeather_Response response =
    weatherAPI.getCurrentWeather(request);

Decimal temperature = response.Code200.temperature;
String conditions = response.Code200.conditions;
```

## Comparison to Orienteer Integration (Apache Camel)

### Apache Camel Features vs. Salesforce

| Camel Feature | Salesforce Equivalent | Compatibility |
|--------------|----------------------|---------------|
| **Routes** | Apex Classes / Flows | ⚠️ Different paradigm |
| **Endpoints** | REST/SOAP APIs, External Services | ✅ Multiple options |
| **Processors** | Apex Transformation Logic | ✅ Custom logic supported |
| **Message Queue** | Platform Events | ✅ Pub-sub messaging |
| **Error Handling** | Try-catch, Error Flows | ✅ Error handling supported |
| **Retry Logic** | Outbound Messages, Queueable Apex | ✅ Retry mechanisms |
| **Transformation** | Apex / Flow Transform | ✅ Data transformation |
| **Routing** | Flow Decision / Apex Logic | ✅ Conditional routing |
| **Content-Based Routing** | Flow / Apex | ✅ Supported |
| **Splitting** | Apex Loops / Flow Loops | ✅ Iteration supported |
| **Aggregation** | Apex Collection Logic | ⚠️ Custom implementation |
| **File Processing** | ContentVersion / Attachments | ⚠️ Limited file handling |
| **Scheduling** | Scheduled Apex / Flow | ✅ Cron-based scheduling |
| **Monitoring** | Event Monitoring, Debug Logs | ⚠️ Different tooling |

### Migration Strategy: Camel Routes to Salesforce

#### Example Camel Route
```java
// Orienteer: Apache Camel Route
from("timer://orderProcessor?period=60000")
    .to("sql:SELECT * FROM orders WHERE status='NEW'?dataSource=#dataSource")
    .split(body())
    .process(new OrderProcessor())
    .choice()
        .when(simple("${body.amount} > 1000"))
            .to("direct:highValueOrder")
        .otherwise()
            .to("direct:standardOrder")
    .end()
    .to("jms:queue:orderProcessed");
```

#### Salesforce Equivalent

**Option 1: Scheduled Apex + Platform Events**
```apex
// Scheduled Apex (runs every minute via cron: 0 * * * * ?)
global class OrderProcessor implements Schedulable {
    global void execute(SchedulableContext sc) {
        List<Order__c> newOrders = [
            SELECT Id, Amount__c, Status__c
            FROM Order__c
            WHERE Status__c = 'New'
            LIMIT 200
        ];

        processOrders(newOrders);
    }

    @future
    private static void processOrders(List<Order__c> orders) {
        List<Order_Processed__e> events = new List<Order_Processed__e>();

        for(Order__c order : orders) {
            // Transform/process order
            transformOrder(order);

            // Route based on amount
            if(order.Amount__c > 1000) {
                handleHighValueOrder(order);
            } else {
                handleStandardOrder(order);
            }

            // Publish event (equivalent to JMS queue)
            events.add(new Order_Processed__e(
                Order_Id__c = order.Id,
                Amount__c = order.Amount__c
            ));
        }

        // Publish events
        EventBus.publish(events);
    }

    private static void transformOrder(Order__c order) {
        // Transformation logic (Camel Processor equivalent)
    }

    private static void handleHighValueOrder(Order__c order) {
        // High value processing
    }

    private static void handleStandardOrder(Order__c order) {
        // Standard processing
    }
}
```

**Option 2: Record-Triggered Flow**
```
Flow: Process New Orders
Trigger: Order__c record created or updated
Condition: Status = 'New'

1. Decision: Check Amount
   - If Amount > 1000 → High Value Path
   - Else → Standard Path

2. High Value Path:
   - Create Task (High Priority)
   - Send Email (Sales Manager)
   - Update Order Status

3. Standard Path:
   - Create Task (Normal Priority)
   - Send Email (Sales Team)
   - Update Order Status

4. Platform Event: Publish Order Processed Event
```

### Integration Patterns Mapping

| Pattern | Orienteer (Camel) | Salesforce | Migration Approach |
|---------|------------------|------------|-------------------|
| **Point-to-Point** | Direct endpoints | REST/SOAP API | Direct API calls |
| **Publish-Subscribe** | JMS/ActiveMQ | Platform Events | Use Platform Events |
| **Request-Reply** | HTTP/REST | REST API | REST callouts |
| **Message Queue** | JMS Queue | Platform Events | Async processing via events |
| **File Transfer** | File endpoints | ContentVersion | File upload/download APIs |
| **Database Polling** | SQL endpoint | Scheduled Apex | Schedule SOQL queries |
| **Web Services** | SOAP/REST | Apex Web Services | Expose Apex REST/SOAP |
| **FTP/SFTP** | FTP endpoint | External FTP + Apex | Custom integration |
| **Email** | Mail endpoint | Email Services | Inbound/Outbound email |

## API Limits and Governance

### Daily API Limits

| License Type | API Calls per 24 Hours |
|-------------|----------------------|
| Salesforce (Legacy) | 1,000 |
| Professional | 1,000 |
| Enterprise | 1,000 + (1,000 × licenses) |
| Performance | 1,000 + (2,000 × licenses) |
| Unlimited | 1,000 + (5,000 × licenses) |
| Developer Edition | 15,000 |
| Trial | 5,000 |

**Formula**: Base + (Multiplier × User Licenses)

**Example**: Enterprise with 100 users = 1,000 + (1,000 × 100) = 101,000 API calls/day

### API Call Optimization

**Best Practices**:
1. **Bulk Operations**: Use Composite API, Bulk API
2. **Caching**: Cache frequently accessed data
3. **Selective Queries**: Query only needed fields
4. **Platform Events**: Use for async notifications (don't count toward API limits)
5. **Change Data Capture**: Subscribe to changes instead of polling
6. **Batch Processing**: Combine multiple operations
7. **Governor Limit Monitoring**: Track API usage via Apex limits

### Monitoring API Usage

```apex
// Check API limits
System.debug('API Calls Used: ' + Limits.getCallouts());
System.debug('API Calls Limit: ' + Limits.getLimitCallouts());

// Organization-wide API usage
// Setup → System Overview → API Usage
```

## Integration Security

### Authentication Methods

#### 1. OAuth 2.0 (Recommended)
**Flow Types**:
- **Web Server Flow**: For web applications
- **User-Agent Flow**: For mobile/JavaScript apps
- **JWT Bearer Flow**: For server-to-server
- **Username-Password Flow**: For trusted apps (not recommended)
- **Device Flow**: For devices with limited input

**Example: JWT Bearer Flow**
```python
# Python example - Server-to-server integration
import jwt
import requests
import time

# JWT payload
payload = {
    'iss': 'your_consumer_key',
    'sub': 'user@example.com',
    'aud': 'https://login.salesforce.com',
    'exp': int(time.time()) + 300
}

# Sign JWT
assertion = jwt.encode(payload, private_key, algorithm='RS256')

# Request access token
response = requests.post(
    'https://login.salesforce.com/services/oauth2/token',
    data={
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        'assertion': assertion
    }
)

access_token = response.json()['access_token']
```

#### 2. Named Credentials
**Purpose**: Centralize authentication configuration

**Setup**:
1. Setup → Named Credentials
2. Configure:
   - URL
   - Authentication Protocol (OAuth 2.0, Password, JWT, etc.)
   - Certificates
   - Custom headers

**Usage in Apex**:
```apex
HttpRequest req = new HttpRequest();
req.setEndpoint('callout:MyNamedCredential/api/v1/resource');
req.setMethod('GET');

Http http = new Http();
HttpResponse res = http.send(req);
```

**Benefits**:
- Centralized credential management
- No hardcoded credentials
- Supports multiple auth protocols
- Automatic token refresh

#### 3. Session-Based Authentication
**Use Case**: Internal Salesforce API calls

```apex
// Get session ID
String sessionId = UserInfo.getSessionId();

HttpRequest req = new HttpRequest();
req.setHeader('Authorization', 'Bearer ' + sessionId);
req.setEndpoint(URL.getSalesforceBaseUrl().toExternalForm() +
    '/services/data/v58.0/sobjects/Account/001XXXXXXXXXXXXXXX');
req.setMethod('GET');
```

### IP Whitelisting
- **Trusted IP Ranges**: Restrict API access by IP
- **Setup**: Setup → Network Access
- **Enforcement**: Per user profile/permission set

### Certificate-Based Authentication
- **Mutual TLS**: Two-way SSL/TLS
- **Setup**: Upload certificates in Salesforce
- **Use Case**: High-security integrations

## Migration Recommendations

### Pre-Migration Assessment
1. **Document Camel Routes**: Inventory all integration routes
2. **Map Endpoints**: Identify all external systems
3. **Classify Integrations**:
   - Real-time vs. Batch
   - Inbound vs. Outbound
   - Synchronous vs. Asynchronous
4. **Estimate API Volume**: Calculate daily API call requirements
5. **Security Review**: Document authentication methods

### Migration Approach

#### Phase 1: Design
1. **Map Camel Routes to Salesforce Patterns**:
   - Polling → Scheduled Apex
   - JMS → Platform Events
   - HTTP endpoints → REST APIs
   - File processing → ContentVersion APIs
2. **Design Integration Architecture**
3. **Plan Authentication Strategy** (Named Credentials, OAuth)
4. **Review API Limits** and optimization strategies

#### Phase 2: Build
1. **Create External Services** (for REST APIs)
2. **Implement Apex REST/SOAP Services** (for inbound)
3. **Build Platform Events** (for async messaging)
4. **Develop Scheduled Apex** (for polling patterns)
5. **Configure Named Credentials**

#### Phase 3: Test
1. **Unit Testing**: Apex test classes (75% coverage required)
2. **Integration Testing**: End-to-end with external systems
3. **Performance Testing**: Verify API limits not exceeded
4. **Security Testing**: Validate authentication flows

#### Phase 4: Deploy
1. **Sandbox Deployment**: Test in sandbox
2. **Change Sets / SFDX**: Deploy to production
3. **Monitoring**: Setup API usage monitoring
4. **Documentation**: Document integration architecture

### Key Takeaways

**Strengths**:
1. ✅ **Multiple Integration Options**: REST, SOAP, Events, CDC
2. ✅ **Event-Driven Architecture**: Platform Events for pub-sub
3. ✅ **Declarative Integration**: External Services, Flow Builder
4. ✅ **Security**: OAuth, Named Credentials, IP restrictions
5. ✅ **Scalability**: Bulk API for large data volumes

**Limitations**:
1. ⚠️ **API Limits**: Daily API call restrictions
2. ⚠️ **No Native Message Queue**: Platform Events are pub-sub, not traditional queue
3. ⚠️ **File Handling**: Limited compared to Camel file endpoints
4. ⚠️ **Complexity**: More complex than Camel for some patterns
5. ⚠️ **Monitoring**: Different tooling than Camel

**Migration Complexity**: **Medium-High**
- Most Camel patterns can be replicated
- Requires rethinking integration architecture
- API limits may require optimization
- Event-driven patterns map well to Platform Events
- Some patterns require creative solutions

**Recommended Strategy**:
1. **Use Platform Events** for async messaging (Camel JMS replacement)
2. **Scheduled Apex** for polling patterns
3. **REST APIs** for synchronous integrations
4. **External Services** for calling external REST APIs
5. **Change Data Capture** for near real-time data sync
