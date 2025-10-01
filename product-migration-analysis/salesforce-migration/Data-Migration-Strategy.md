# OrientDB to Salesforce Data Migration Strategy

## Executive Summary

This document outlines a comprehensive, automated data migration strategy for moving from OrientDB to Salesforce. The strategy is designed for a <500MB database with support for multiple test migrations, focusing on schema definitions and relationships while excluding graph traversal data.

## Migration Architecture

### High-Level Flow
```
OrientDB → Extraction → Transformation → Validation → Salesforce Loading
    ↓           ↓             ↓              ↓              ↓
 Schema    JSON/CSV      Mapping Rules   Data Quality   Bulk API
 Analysis   Export       Type Conversion  Checks        Error Handling
```

### Key Principles
1. **Idempotent Operations**: All scripts can be re-run safely
2. **Configuration-Driven**: Schema mappings defined in config files
3. **Dependency-Aware**: Load order respects relationships
4. **Validation-First**: Multiple checkpoints prevent data corruption
5. **Audit Trail**: Complete logging of all operations

---

## 1. Data Extraction Phase

### 1.1 Schema Discovery

**Objective**: Extract complete OrientDB schema definitions including classes, properties, and relationships.

#### Extraction Scripts

**Script: `extract_schema.py`**
```python
# Extract all class definitions, properties, and relationships
# Output: schema_definition.json
```

**OrientDB Query Patterns**:
```sql
-- Extract all classes
SELECT name, superClass, abstract, strictMode, clusterIds
FROM (SELECT expand(classes) FROM metadata:schema)

-- Extract all properties for each class
SELECT name, type, mandatory, notNull, min, max, regexp,
       linkedClass, linkedType, collate, defaultValue, readOnly
FROM (SELECT expand(properties) FROM metadata:schema
      WHERE name = :className)

-- Extract indexes
SELECT name, type, definition, metadata
FROM (SELECT expand(indexes) FROM metadata:indexmanager)

-- Extract relationships (LINK, LINKLIST, LINKSET, LINKMAP)
SELECT name, type, linkedClass
FROM (SELECT expand(properties) FROM metadata:schema)
WHERE type IN ['LINK', 'LINKLIST', 'LINKSET', 'LINKMAP']
```

#### Schema Metadata Output Structure
```json
{
  "extraction_timestamp": "2025-10-01T00:00:00Z",
  "database_size_mb": 450,
  "classes": [
    {
      "name": "OUser",
      "superClass": "OIdentity",
      "abstract": false,
      "properties": [
        {
          "name": "name",
          "type": "STRING",
          "mandatory": true,
          "notNull": true,
          "max": 255
        },
        {
          "name": "role",
          "type": "LINK",
          "linkedClass": "ORole",
          "mandatory": false
        }
      ],
      "indexes": [
        {
          "name": "OUser.name",
          "type": "UNIQUE",
          "fields": ["name"]
        }
      ],
      "record_count": 1234
    }
  ],
  "relationships": [
    {
      "from_class": "OUser",
      "property": "role",
      "to_class": "ORole",
      "cardinality": "many-to-one",
      "type": "LINK"
    }
  ]
}
```

### 1.2 Data Extraction

**Objective**: Export all data in a format suitable for transformation.

#### Export Strategy

**Approach**: Incremental batch export with dependency ordering

**Script: `extract_data.py`**
```python
# Export data in dependency order (referenced entities first)
# Output: data/[ClassName]/batch_[n].json
```

**OrientDB Query Patterns**:
```sql
-- Export with relationship expansion
SELECT *,
       @rid as orientdb_rid,
       @class as orientdb_class,
       @version as orientdb_version
FROM [ClassName]
WHERE @rid > :last_rid
ORDER BY @rid
LIMIT 1000

-- Export with LINK resolution (for mapping)
SELECT *,
       role.name as role_name,
       role.@rid as role_rid
FROM OUser
```

#### Export File Structure
```
migration_export/
├── schema_definition.json
├── extraction_metadata.json
├── data/
│   ├── OUser/
│   │   ├── batch_0001.json (1000 records)
│   │   ├── batch_0002.json
│   │   └── manifest.json
│   ├── ORole/
│   │   ├── batch_0001.json
│   │   └── manifest.json
│   └── [OtherClasses]/
└── relationships/
    ├── user_roles.json
    └── relationship_manifest.json
```

#### Batch Manifest Structure
```json
{
  "class_name": "OUser",
  "total_records": 12450,
  "total_batches": 13,
  "batch_size": 1000,
  "extraction_started": "2025-10-01T10:00:00Z",
  "extraction_completed": "2025-10-01T10:15:23Z",
  "batches": [
    {
      "batch_id": "0001",
      "record_count": 1000,
      "start_rid": "#10:0",
      "end_rid": "#10:999",
      "file_size_kb": 245,
      "checksum": "sha256:abc123..."
    }
  ]
}
```

### 1.3 Relationship Extraction

**Objective**: Extract relationship data separately for validation and reference integrity.

```sql
-- Extract all LINK relationships
SELECT
    @rid as source_rid,
    @class as source_class,
    [property_name].@rid as target_rid,
    [property_name].@class as target_class,
    '[property_name]' as relationship_name
FROM [SourceClass]
WHERE [property_name] IS NOT NULL

-- Extract LINKLIST relationships
SELECT
    @rid as source_rid,
    @class as source_class,
    [property_name][0..10000].@rid as target_rids,
    '[property_name]' as relationship_name
FROM [SourceClass]
WHERE [property_name].size() > 0
```

---

## 2. Data Transformation Phase

### 2.1 Schema Mapping

**Objective**: Map OrientDB classes to Salesforce objects with field-level precision.

#### Mapping Configuration Structure

**File: `config/schema_mappings.yaml`**
```yaml
mappings:
  - orientdb_class: "OUser"
    salesforce_object: "User"
    mapping_type: "standard"
    transformation_rules:
      fields:
        - orientdb_field: "name"
          salesforce_field: "Username"
          transformation: "to_email_format"
          validation: "email_validator"

        - orientdb_field: "firstName"
          salesforce_field: "FirstName"
          transformation: "trim_whitespace"
          max_length: 40

        - orientdb_field: "role"
          salesforce_field: "UserRoleId"
          transformation: "lookup_foreign_key"
          lookup_table: "UserRole"
          lookup_field: "orientdb_external_id"

      relationships:
        - orientdb_property: "role"
          orientdb_linked_class: "ORole"
          salesforce_field: "UserRoleId"
          relationship_type: "lookup"
          required: false

  - orientdb_class: "CustomEntity"
    salesforce_object: "CustomEntity__c"
    mapping_type: "custom"
    create_if_missing: true
    transformation_rules:
      fields:
        - orientdb_field: "customField1"
          salesforce_field: "Custom_Field_1__c"
          type: "STRING(255)"
```

### 2.2 Data Type Conversion Matrix

| OrientDB Type | Salesforce Type | Transformation Rule | Notes |
|---------------|-----------------|---------------------|-------|
| STRING | Text(255) | Truncate if > 255 | Consider Text Area for long strings |
| INTEGER | Number(18,0) | Direct mapping | |
| LONG | Number(18,0) | Direct mapping | |
| FLOAT | Number(16,2) | Precision loss warning | |
| DOUBLE | Number(18,8) | Precision loss warning | |
| DECIMAL | Currency | Scale to 2 decimals | |
| DATE | Date | Convert to YYYY-MM-DD | |
| DATETIME | DateTime | Convert to ISO 8601 | Handle timezone |
| BOOLEAN | Checkbox | Direct mapping | |
| LINK | Lookup(Object) | Convert to External ID lookup | Dependency ordering |
| LINKLIST | Master-Detail | Create junction objects | Many-to-many |
| LINKSET | Master-Detail | Create junction objects | De-duplicate |
| LINKMAP | Text(Long) | Serialize to JSON | Not ideal - redesign |
| EMBEDDED | Text(Long) | Serialize to JSON | Consider separate object |
| EMBEDDEDLIST | Text(Long) | Serialize to JSON | Consider child records |
| EMBEDDEDMAP | Text(Long) | Serialize to JSON | Consider field mapping |
| BINARY | Attachment | Store in Salesforce Files | Size limits apply |

### 2.3 Transformation Pipeline

**Script: `transform_data.py`**

#### Stage 1: Field-Level Transformations
```python
def transform_field(value, field_config):
    """
    Apply field-level transformations
    """
    transformations = {
        'trim_whitespace': lambda v: v.strip() if v else None,
        'to_uppercase': lambda v: v.upper() if v else None,
        'to_lowercase': lambda v: v.lower() if v else None,
        'truncate': lambda v: v[:field_config.max_length] if v else None,
        'to_email_format': lambda v: f"{v}@company.com" if '@' not in v else v,
        'date_to_iso': lambda v: datetime.fromisoformat(v).date().isoformat(),
        'lookup_foreign_key': lambda v: resolve_external_id(v, field_config)
    }

    transform_func = transformations.get(field_config.transformation)
    return transform_func(value) if transform_func else value
```

#### Stage 2: Relationship Resolution
```python
def resolve_relationships(record, mapping_config):
    """
    Convert OrientDB RIDs to Salesforce External IDs
    """
    for rel in mapping_config.relationships:
        orientdb_rid = record.get(rel.orientdb_property)
        if orientdb_rid:
            # Lookup target record's Salesforce ID
            external_id = f"ORIENTDB_{orientdb_rid.replace('#', '_')}"
            record[rel.salesforce_field] = external_id

    return record
```

#### Stage 3: Data Validation
```python
def validate_record(record, salesforce_object_metadata):
    """
    Validate against Salesforce object rules
    """
    validations = []

    for field_name, field_value in record.items():
        field_meta = salesforce_object_metadata.fields[field_name]

        # Required field validation
        if field_meta.required and not field_value:
            validations.append(f"Required field {field_name} is null")

        # Length validation
        if field_meta.length and len(str(field_value)) > field_meta.length:
            validations.append(f"Field {field_name} exceeds max length")

        # Type validation
        if not validate_type(field_value, field_meta.type):
            validations.append(f"Field {field_name} type mismatch")

    return validations
```

#### Transformed Output Structure
```json
{
  "salesforce_object": "CustomEntity__c",
  "records": [
    {
      "OrientDB_External_ID__c": "ORIENTDB_10_12345",
      "Name": "Entity Name",
      "Custom_Field_1__c": "Value",
      "Related_Object__r": {
        "OrientDB_External_ID__c": "ORIENTDB_11_67890"
      }
    }
  ],
  "metadata": {
    "source_class": "CustomEntity",
    "source_batch": "batch_0001.json",
    "transformation_timestamp": "2025-10-01T11:30:00Z",
    "record_count": 1000,
    "validation_passed": 998,
    "validation_failed": 2,
    "validation_errors": "errors/batch_0001_errors.json"
  }
}
```

### 2.4 Relationship Flattening Strategy

#### Many-to-One Relationships
```yaml
# Direct lookup field
OUser.role (LINK to ORole) → User.UserRoleId (Lookup to UserRole)
```

#### One-to-Many Relationships
```yaml
# Master-detail or lookup from child
OAccount.contacts (LINKLIST to OContact) → Contact.AccountId (Master-Detail to Account)
```

#### Many-to-Many Relationships
```yaml
# Junction object pattern
OUser.permissions (LINKLIST to OPermission) →
  Junction Object: UserPermission__c
    - User__c (Master-Detail to User)
    - Permission__c (Master-Detail to Permission__c)
```

#### Complex Embedded Data
```yaml
# Strategy 1: Flatten to fields (if small, fixed structure)
embedded_address: {street, city, zip} →
  Street__c, City__c, Zip__c

# Strategy 2: Serialize to JSON (if complex, variable structure)
embedded_metadata: {key1: val1, ...} →
  Metadata_JSON__c (Text Area Long)

# Strategy 3: Create child object (if list of objects)
embedded_items: [{name, qty}, ...] →
  LineItem__c object with Master-Detail relationship
```

### 2.5 Data Cleansing Rules

**File: `config/cleansing_rules.yaml`**
```yaml
cleansing_rules:
  - rule_name: "remove_invalid_emails"
    field: "Email"
    validation: "email_regex"
    action: "set_null_if_invalid"

  - rule_name: "normalize_phone_numbers"
    field: "Phone"
    transformation: "strip_non_numeric"
    format: "US_PHONE_NUMBER"

  - rule_name: "deduplicate_names"
    fields: ["FirstName", "LastName", "Email"]
    action: "mark_duplicate"
    strategy: "keep_latest_by_modified_date"

  - rule_name: "fix_null_required_fields"
    fields: ["LastName"]
    default_value: "Unknown"

  - rule_name: "standardize_picklist_values"
    field: "Status__c"
    mapping:
      "active": "Active"
      "ACTIVE": "Active"
      "inactive": "Inactive"
      "INACTIVE": "Inactive"
    default: "Active"
```

---

## 3. Data Loading Phase

### 3.1 Salesforce Bulk API Strategy

**Objective**: Efficiently load large datasets using Salesforce Bulk API 2.0.

#### Load Architecture

**Technology**: Salesforce Bulk API 2.0
- **Batch Size**: 10,000 records per batch (API limit)
- **Parallelization**: Up to 5 concurrent jobs
- **Rate Limiting**: Respect Salesforce API limits

#### Load Order (Dependency Graph)

```
1. Independent Objects (no dependencies)
   - UserRole
   - RecordType
   - CustomSettings__c

2. Standard Objects (Level 1)
   - User
   - Account
   - Contact (depends on Account)

3. Custom Objects (Level 2)
   - CustomEntity__c (depends on User, Account)
   - RelatedEntity__c (depends on CustomEntity__c)

4. Junction Objects (Level 3)
   - UserPermission__c (depends on User, Permission__c)
   - EntityRelationship__c (depends on multiple entities)

5. Attachments and Files (Final)
   - ContentVersion
   - Attachment
```

**Script: `load_data.py`**

#### Stage 1: Pre-Load Validation
```python
def validate_salesforce_environment():
    """
    Validate Salesforce environment before loading
    """
    checks = {
        'sandbox_environment': True,  # Must be sandbox for test migrations
        'no_existing_data': True,     # Verify clean environment
        'sufficient_storage': True,   # Check data storage limits
        'api_access': True,           # Verify API credentials
        'objects_exist': True,        # Verify all target objects exist
        'fields_exist': True          # Verify all target fields exist
    }

    return all(checks.values())
```

#### Stage 2: Bulk Job Creation
```python
def create_bulk_job(object_name, operation='insert'):
    """
    Create Bulk API 2.0 job
    """
    job_request = {
        'object': object_name,
        'operation': operation,
        'lineEnding': 'LF',
        'columnDelimiter': 'COMMA',
        'contentType': 'CSV',
        'externalIdFieldName': 'OrientDB_External_ID__c'  # For upsert
    }

    response = salesforce_client.create_bulk_job(job_request)
    return response['id']
```

#### Stage 3: Data Upload
```python
def upload_batch(job_id, csv_data):
    """
    Upload CSV batch to Bulk API job
    """
    # Convert JSON to CSV format
    csv_content = convert_to_csv(csv_data)

    # Upload to Salesforce
    response = salesforce_client.upload_job_data(job_id, csv_content)

    # Close job for processing
    salesforce_client.close_job(job_id)

    return job_id
```

#### Stage 4: Job Monitoring
```python
def monitor_bulk_job(job_id, timeout_minutes=60):
    """
    Monitor bulk job until completion or timeout
    """
    start_time = time.time()

    while True:
        job_status = salesforce_client.get_job_status(job_id)

        if job_status['state'] in ['JobComplete', 'Failed', 'Aborted']:
            return job_status

        if (time.time() - start_time) > (timeout_minutes * 60):
            raise TimeoutError(f"Job {job_id} timed out")

        time.sleep(10)  # Poll every 10 seconds
```

#### Stage 5: Result Processing
```python
def process_bulk_results(job_id):
    """
    Retrieve and process bulk job results
    """
    results = {
        'successful': salesforce_client.get_successful_results(job_id),
        'failed': salesforce_client.get_failed_results(job_id),
        'unprocessed': salesforce_client.get_unprocessed_results(job_id)
    }

    # Log all failures
    for failure in results['failed']:
        log_error({
            'record': failure,
            'error': failure['sf__Error'],
            'job_id': job_id
        })

    return results
```

### 3.2 Error Handling and Rollback

#### Error Classification

**Level 1: Critical Errors (Stop Migration)**
- Authentication failures
- API rate limit exceeded (permanent)
- Object or field not found
- Insufficient permissions

**Level 2: Recoverable Errors (Retry)**
- Temporary network issues
- API rate limit exceeded (temporary)
- Lock contention
- Server timeouts

**Level 3: Record-Level Errors (Skip and Log)**
- Validation rule failures
- Duplicate record detection
- Required field missing
- Invalid foreign key reference

#### Rollback Strategy

**Approach**: Bulk delete using External ID

```python
def rollback_migration(migration_id):
    """
    Rollback entire migration using External ID
    """
    # Get all loaded objects
    loaded_objects = get_migration_manifest(migration_id)

    # Delete in reverse dependency order
    for obj in reversed(loaded_objects):
        delete_query = f"""
        SELECT Id FROM {obj.name}
        WHERE OrientDB_Migration_ID__c = '{migration_id}'
        """

        # Use Bulk API for delete
        job_id = create_bulk_job(obj.name, operation='delete')
        records = salesforce_client.query(delete_query)
        upload_batch(job_id, records)

        log_rollback_action(obj.name, len(records))
```

### 3.3 Validation Checkpoints

**Checkpoint 1: Pre-Load Validation**
```python
def validate_pre_load(transformed_data, salesforce_metadata):
    """
    Validate data before loading
    """
    checks = [
        validate_record_counts(),          # Match source counts
        validate_required_fields(),        # All required fields present
        validate_field_lengths(),          # No truncation errors
        validate_data_types(),             # Type compatibility
        validate_foreign_keys(),           # All references exist
        validate_unique_constraints()      # No duplicate violations
    ]

    return all(checks)
```

**Checkpoint 2: Post-Load Validation**
```python
def validate_post_load(migration_id):
    """
    Validate data after loading
    """
    validations = {
        'record_counts': compare_record_counts(),
        'relationship_integrity': validate_relationships(),
        'data_sampling': sample_random_records(count=100),
        'aggregate_calculations': compare_sum_avg_counts(),
        'orphan_records': check_for_orphans()
    }

    report = generate_validation_report(validations)
    return report
```

**Checkpoint 3: User Acceptance Validation**
```python
def prepare_uat_environment(migration_id):
    """
    Prepare environment for user testing
    """
    tasks = [
        create_test_users(),
        assign_permission_sets(),
        load_sample_dashboards(),
        configure_list_views(),
        enable_audit_trail(),
        create_validation_scripts()
    ]

    return all([task() for task in tasks])
```

---

## 4. Automation Framework

### 4.1 Framework Architecture

```
migration-framework/
├── config/
│   ├── connection.yaml          # Database connections
│   ├── schema_mappings.yaml     # Schema transformations
│   ├── cleansing_rules.yaml     # Data quality rules
│   └── load_order.yaml          # Dependency graph
├── scripts/
│   ├── extraction/
│   │   ├── extract_schema.py
│   │   ├── extract_data.py
│   │   └── extract_relationships.py
│   ├── transformation/
│   │   ├── transform_data.py
│   │   ├── validate_data.py
│   │   └── cleanse_data.py
│   └── loading/
│       ├── load_data.py
│       ├── monitor_jobs.py
│       └── validate_load.py
├── lib/
│   ├── orientdb_client.py       # OrientDB connection wrapper
│   ├── salesforce_client.py     # Salesforce API wrapper
│   ├── transformation_engine.py # Core transformation logic
│   └── validation_engine.py     # Validation framework
├── tests/
│   ├── test_extraction.py
│   ├── test_transformation.py
│   └── test_loading.py
├── logs/
│   └── [timestamp]/             # Per-migration logs
└── data/
    └── migrations/
        └── [migration_id]/      # Per-migration data
            ├── extracted/
            ├── transformed/
            └── results/
```

### 4.2 Configuration Management

**File: `config/connection.yaml`**
```yaml
orientdb:
  host: "localhost"
  port: 2424
  database: "orienteer_db"
  username: "${ORIENTDB_USER}"
  password: "${ORIENTDB_PASSWORD}"
  connection_pool_size: 10

salesforce:
  environment: "sandbox"  # sandbox | production
  instance_url: "${SF_INSTANCE_URL}"
  api_version: "58.0"
  authentication:
    type: "oauth2"
    client_id: "${SF_CLIENT_ID}"
    client_secret: "${SF_CLIENT_SECRET}"
    username: "${SF_USERNAME}"
    password: "${SF_PASSWORD}"
    security_token: "${SF_SECURITY_TOKEN}"

migration:
  batch_size: 1000
  max_parallel_jobs: 5
  retry_attempts: 3
  retry_delay_seconds: 30
  validation_sample_size: 100
  log_level: "INFO"
```

**File: `config/load_order.yaml`**
```yaml
load_phases:
  - phase: 1
    description: "Independent reference data"
    objects:
      - UserRole
      - RecordType
      - Profile
    parallel: true

  - phase: 2
    description: "Standard objects with Level 1 dependencies"
    objects:
      - User:
          depends_on: [UserRole, Profile]
      - Account
      - Contact:
          depends_on: [Account]
    parallel: true

  - phase: 3
    description: "Custom objects with Level 2 dependencies"
    objects:
      - CustomEntity__c:
          depends_on: [User, Account]
      - RelatedEntity__c:
          depends_on: [CustomEntity__c]
    parallel: true

  - phase: 4
    description: "Junction objects"
    objects:
      - UserPermission__c:
          depends_on: [User, Permission__c]
    parallel: true
```

### 4.3 Main Migration Orchestrator

**Script: `migrate.py`**
```python
#!/usr/bin/env python3
"""
Main migration orchestrator script
Usage: python migrate.py --config config/connection.yaml --mode [test|production]
"""

import argparse
import logging
from datetime import datetime
from lib.orientdb_client import OrientDBClient
from lib.salesforce_client import SalesforceClient
from scripts.extraction.extract_schema import SchemaExtractor
from scripts.extraction.extract_data import DataExtractor
from scripts.transformation.transform_data import DataTransformer
from scripts.loading.load_data import DataLoader

class MigrationOrchestrator:
    def __init__(self, config_path, mode='test'):
        self.config = self.load_config(config_path)
        self.mode = mode
        self.migration_id = f"MIGRATION_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.setup_logging()

    def setup_logging(self):
        log_dir = f"logs/{self.migration_id}"
        os.makedirs(log_dir, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f"{log_dir}/migration.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def execute_migration(self):
        """
        Execute full migration pipeline
        """
        try:
            self.logger.info(f"Starting migration {self.migration_id} in {self.mode} mode")

            # Phase 1: Extraction
            self.logger.info("Phase 1: Extracting data from OrientDB")
            extraction_result = self.extract_data()

            # Phase 2: Transformation
            self.logger.info("Phase 2: Transforming data")
            transformation_result = self.transform_data(extraction_result)

            # Phase 3: Validation
            self.logger.info("Phase 3: Validating transformed data")
            validation_result = self.validate_data(transformation_result)

            if not validation_result.passed:
                raise ValidationError("Data validation failed", validation_result.errors)

            # Phase 4: Loading
            self.logger.info("Phase 4: Loading data to Salesforce")
            load_result = self.load_data(transformation_result)

            # Phase 5: Post-Load Validation
            self.logger.info("Phase 5: Post-load validation")
            post_validation_result = self.validate_loaded_data(load_result)

            # Generate final report
            self.generate_migration_report({
                'extraction': extraction_result,
                'transformation': transformation_result,
                'validation': validation_result,
                'load': load_result,
                'post_validation': post_validation_result
            })

            self.logger.info(f"Migration {self.migration_id} completed successfully")

        except Exception as e:
            self.logger.error(f"Migration failed: {str(e)}")
            self.handle_migration_failure(e)
            raise

    def extract_data(self):
        orientdb_client = OrientDBClient(self.config['orientdb'])
        extractor = DataExtractor(orientdb_client, self.migration_id)

        # Extract schema
        schema = extractor.extract_schema()

        # Extract data in dependency order
        data = extractor.extract_data(schema)

        return {
            'schema': schema,
            'data': data,
            'metadata': extractor.get_metadata()
        }

    def transform_data(self, extraction_result):
        transformer = DataTransformer(self.config)

        transformed_data = {}
        for class_name, records in extraction_result['data'].items():
            transformed_data[class_name] = transformer.transform(
                records,
                extraction_result['schema'][class_name]
            )

        return transformed_data

    def validate_data(self, transformed_data):
        validator = DataValidator(self.config)
        return validator.validate_all(transformed_data)

    def load_data(self, transformed_data):
        sf_client = SalesforceClient(self.config['salesforce'])
        loader = DataLoader(sf_client, self.migration_id)

        return loader.load_in_order(
            transformed_data,
            self.config['load_order']
        )

    def validate_loaded_data(self, load_result):
        sf_client = SalesforceClient(self.config['salesforce'])
        validator = PostLoadValidator(sf_client, self.migration_id)

        return validator.validate_all(load_result)

    def handle_migration_failure(self, error):
        self.logger.error("Initiating rollback due to migration failure")

        if self.mode == 'test':
            # In test mode, always rollback
            self.rollback_migration()
        else:
            # In production, ask for confirmation
            response = input("Rollback migration? (yes/no): ")
            if response.lower() == 'yes':
                self.rollback_migration()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='OrientDB to Salesforce Migration')
    parser.add_argument('--config', required=True, help='Path to configuration file')
    parser.add_argument('--mode', choices=['test', 'production'], default='test')
    parser.add_argument('--skip-extraction', action='store_true', help='Skip extraction phase')
    parser.add_argument('--skip-validation', action='store_true', help='Skip validation phase')

    args = parser.parse_args()

    orchestrator = MigrationOrchestrator(args.config, args.mode)
    orchestrator.execute_migration()
```

### 4.4 Logging and Monitoring

**Log Structure**:
```
logs/
└── MIGRATION_20251001_120000/
    ├── migration.log               # Main log
    ├── extraction/
    │   ├── schema_extraction.log
    │   ├── data_extraction.log
    │   └── errors.log
    ├── transformation/
    │   ├── transformation.log
    │   ├── validation_errors.log
    │   └── cleansing_report.json
    ├── loading/
    │   ├── bulk_jobs.log
    │   ├── failed_records/
    │   │   ├── User_failures.csv
    │   │   └── CustomEntity__c_failures.csv
    │   └── job_status.json
    └── reports/
        ├── migration_summary.json
        ├── data_quality_report.html
        └── validation_report.pdf
```

**Monitoring Dashboard Data**:
```json
{
  "migration_id": "MIGRATION_20251001_120000",
  "status": "in_progress",
  "current_phase": "loading",
  "progress_percentage": 67,
  "start_time": "2025-10-01T12:00:00Z",
  "estimated_completion": "2025-10-01T14:30:00Z",
  "statistics": {
    "total_records_extracted": 125000,
    "total_records_transformed": 125000,
    "total_records_loaded": 84000,
    "total_errors": 123,
    "objects_completed": 8,
    "objects_remaining": 4
  },
  "current_operations": [
    {
      "object": "CustomEntity__c",
      "operation": "loading",
      "job_id": "750xx0000000001",
      "records_processed": 8400,
      "records_total": 12000,
      "status": "InProgress"
    }
  ]
}
```

### 4.5 Testing Strategy

**Unit Tests**: Test individual components
```python
# tests/test_transformation.py
def test_field_transformation():
    transformer = FieldTransformer()
    result = transformer.transform_field(
        value="  John Doe  ",
        config={'transformation': 'trim_whitespace'}
    )
    assert result == "John Doe"

def test_lookup_resolution():
    resolver = LookupResolver()
    result = resolver.resolve_lookup(
        orientdb_rid="#10:123",
        target_class="ORole"
    )
    assert result == "ORIENTDB_10_123"
```

**Integration Tests**: Test end-to-end workflows
```python
# tests/test_integration.py
def test_full_migration_workflow():
    # Use test database with known data
    orchestrator = MigrationOrchestrator(
        config='config/test_connection.yaml',
        mode='test'
    )

    result = orchestrator.execute_migration()

    assert result.extraction.record_count == 1000
    assert result.transformation.success_rate > 0.99
    assert result.load.success_rate > 0.99
```

**Load Tests**: Validate performance with large datasets
```python
# tests/test_performance.py
def test_bulk_load_performance():
    # Test with 100k records
    start_time = time.time()

    loader = DataLoader(sf_client, migration_id)
    result = loader.load_batch(generate_test_records(100000))

    duration = time.time() - start_time

    assert duration < 600  # Should complete in under 10 minutes
    assert result.success_rate > 0.99
```

---

## 5. Migration Execution Playbook

### 5.1 Pre-Migration Checklist

- [ ] **Environment Setup**
  - [ ] OrientDB connection tested
  - [ ] Salesforce sandbox created and accessible
  - [ ] API credentials configured
  - [ ] Python environment set up (Python 3.8+)
  - [ ] Required libraries installed (`pip install -r requirements.txt`)

- [ ] **Configuration Validation**
  - [ ] Schema mappings reviewed and approved
  - [ ] Load order dependencies verified
  - [ ] Data cleansing rules defined
  - [ ] Error handling thresholds set

- [ ] **Salesforce Preparation**
  - [ ] Custom objects created
  - [ ] Custom fields created
  - [ ] External ID fields added (OrientDB_External_ID__c)
  - [ ] Validation rules temporarily disabled
  - [ ] Workflow rules temporarily disabled
  - [ ] Triggers temporarily disabled

- [ ] **Backup and Safety**
  - [ ] OrientDB backup completed
  - [ ] Salesforce metadata backup (if applicable)
  - [ ] Rollback plan documented
  - [ ] Stakeholders notified of migration window

### 5.2 Migration Execution Steps

**Step 1: Test Migration #1 (Small Dataset)**
```bash
# Extract sample data (100 records per class)
python scripts/extraction/extract_data.py \
  --config config/connection.yaml \
  --sample-size 100 \
  --output data/migrations/test_001

# Transform
python scripts/transformation/transform_data.py \
  --input data/migrations/test_001 \
  --config config/schema_mappings.yaml \
  --output data/migrations/test_001/transformed

# Load
python scripts/loading/load_data.py \
  --input data/migrations/test_001/transformed \
  --config config/connection.yaml \
  --mode test

# Validate
python scripts/loading/validate_load.py \
  --migration-id test_001 \
  --config config/connection.yaml
```

**Step 2: Test Migration #2 (Medium Dataset)**
```bash
# Run full migration orchestrator with 10k records
python migrate.py \
  --config config/connection.yaml \
  --mode test \
  --limit 10000
```

**Step 3: Test Migration #3 (Full Dataset)**
```bash
# Run complete migration
python migrate.py \
  --config config/connection.yaml \
  --mode test
```

**Step 4: User Acceptance Testing**
- Provide users access to test Salesforce environment
- Execute UAT test scripts
- Collect feedback and iterate

**Step 5: Production Migration**
```bash
# Final production migration
python migrate.py \
  --config config/connection_prod.yaml \
  --mode production \
  --notify-stakeholders
```

### 5.3 Post-Migration Tasks

- [ ] **Data Validation**
  - [ ] Record counts match
  - [ ] Relationship integrity verified
  - [ ] Sample data spot-checked
  - [ ] Reports and dashboards functional

- [ ] **Salesforce Configuration**
  - [ ] Re-enable validation rules
  - [ ] Re-enable workflow rules
  - [ ] Re-enable triggers
  - [ ] Configure page layouts
  - [ ] Set up list views
  - [ ] Configure security and permissions

- [ ] **User Training**
  - [ ] Train users on new system
  - [ ] Provide documentation
  - [ ] Set up support channels

- [ ] **System Cutover**
  - [ ] Decommission OrientDB (after grace period)
  - [ ] Update integrations to point to Salesforce
  - [ ] Archive OrientDB data

---

## 6. Risk Mitigation

### 6.1 Identified Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Data loss during migration | High | Low | Multiple backups, validation checkpoints |
| Relationship integrity broken | High | Medium | Pre-load validation, post-load verification |
| API rate limits exceeded | Medium | Medium | Batch processing, rate limiting, retry logic |
| Data type incompatibilities | Medium | High | Comprehensive mapping, transformation testing |
| Migration timeout/failure | Medium | Low | Incremental loading, resume capability |
| User acceptance issues | High | Medium | Multiple test migrations, UAT phase |
| Performance degradation | Medium | Low | Load testing, optimization |

### 6.2 Contingency Plans

**Scenario 1: Critical Failure During Load**
- **Action**: Immediately stop all bulk jobs
- **Assessment**: Analyze error logs to determine root cause
- **Decision**: Rollback if >5% failure rate, otherwise fix and resume

**Scenario 2: Salesforce API Rate Limit**
- **Action**: Pause migration, implement exponential backoff
- **Resume**: Automatically retry after cool-down period
- **Prevention**: Implement request throttling

**Scenario 3: Data Validation Failures**
- **Action**: Isolate failed records, continue with successful ones
- **Analysis**: Review validation errors, adjust mappings
- **Remediation**: Fix and re-run failed records separately

---

## 7. Success Metrics

### 7.1 Key Performance Indicators

**Data Accuracy**:
- Record count match: 100%
- Data validation success rate: >99%
- Relationship integrity: 100%

**Performance**:
- Migration duration: <4 hours for 500MB
- Bulk job success rate: >99%
- API efficiency: <80% of rate limits

**Quality**:
- Zero critical data loss
- User acceptance: >90% satisfaction
- System uptime post-migration: >99.9%

### 7.2 Validation Queries

**Salesforce Validation Queries**:
```sql
-- Verify record counts
SELECT COUNT() FROM CustomEntity__c
-- Compare with: SELECT count(*) FROM CustomEntity in OrientDB

-- Verify relationships
SELECT COUNT()
FROM CustomEntity__c
WHERE Related_Object__c = null
  AND OrientDB_Had_Relationship__c = true
-- Should be 0

-- Check for orphaned records
SELECT Id, Name
FROM Contact
WHERE AccountId = null
  AND IsDeleted = false
-- Should match orphan count from OrientDB

-- Validate data integrity
SELECT COUNT()
FROM User
WHERE Email = null OR FirstName = null OR LastName = null
-- Should be 0 if fields are required
```

---

## Appendix A: Required Python Dependencies

**File: `requirements.txt`**
```
# Database connectors
pyorient==1.5.5
simple-salesforce==1.12.0
salesforce-bulk==2.2.0

# Data processing
pandas==2.0.0
numpy==1.24.0
pyyaml==6.0

# Utilities
python-dotenv==1.0.0
requests==2.31.0
jinja2==3.1.2

# Testing
pytest==7.3.0
pytest-cov==4.0.0
faker==18.9.0

# Logging and monitoring
structlog==23.1.0
```

---

## Appendix B: Memory Hook Storage

The migration strategy will be stored in memory for agent coordination:

**Memory Keys**:
- `migration/extraction/approach`: Schema and data extraction methodology
- `migration/transformation/rules`: Transformation and mapping rules
- `migration/loading/strategy`: Salesforce loading and validation strategy

---

## Document Control

**Version**: 1.0
**Last Updated**: 2025-10-01
**Author**: Migration Strategy Team
**Status**: Draft for Review
**Next Review**: After first test migration
