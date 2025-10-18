# OrientDB to Salesforce Migration Framework

Automated ETL framework for migrating OrientDB data to Salesforce.

## Quick Start

### Prerequisites
```bash
# Python 3.8+ required
python --version

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. **Create `.env` file** with your credentials:
```bash
# OrientDB
ORIENTDB_USER=admin
ORIENTDB_PASSWORD=your_password

# Salesforce (use sandbox for testing!)
SF_INSTANCE_URL=https://test.salesforce.com
SF_CLIENT_ID=your_client_id
SF_CLIENT_SECRET=your_client_secret
SF_USERNAME=your_username@company.com.sandbox
SF_PASSWORD=your_password
SF_SECURITY_TOKEN=your_security_token
```

2. **Configure schema mappings** in `config/schema_mappings.yaml`
   - Map OrientDB classes to Salesforce objects
   - Define field transformations
   - Set up relationship mappings

3. **Configure load order** in `config/load_order.yaml`
   - Define dependency phases
   - Set parallel execution rules

### Running Migration

**Test Migration (Recommended)**:
```bash
python migrate.py --config config/connection.yaml --mode test
```

**Production Migration**:
```bash
python migrate.py --config config/connection.yaml --mode production
```

**Resume from Transformation** (if extraction already complete):
```bash
python migrate.py --config config/connection.yaml --mode test --skip-extraction
```

## Architecture

```
OrientDB → Extraction → Transformation → Validation → Salesforce
    ↓           ↓             ↓              ↓              ↓
 Schema    JSON/CSV      Mapping Rules   Quality        Bulk API
 Analysis   Export       Type Conversion  Checks         Phased Load
```

## Migration Phases

### Phase 1: Schema Extraction
- Extract OrientDB class definitions
- Identify properties and types
- Map relationships
- **Output**: `data/migrations/{migration_id}/schema.json`

### Phase 2: Data Extraction
- Batch export (1000 records per batch)
- Dependency-aware ordering
- Relationship preservation
- **Output**: `data/migrations/{migration_id}/extracted/`

### Phase 3: Data Transformation
- Apply field mappings
- Convert data types
- Flatten relationships
- Data cleansing
- **Output**: `data/migrations/{migration_id}/transformed/`

### Phase 4: Pre-Load Validation
- Required field checks
- Length validation
- Type compatibility
- Relationship integrity

### Phase 5: Salesforce Loading
- Bulk API 2.0 (10k records/batch)
- Dependency-aware phased loading
- External ID for relationships
- Error handling with retry

### Phase 6: Post-Load Validation
- Record count verification
- Relationship validation
- Sample data checks

### Phase 7: Reporting
- Migration summary
- Error reports
- Validation results
- **Output**: `data/migrations/{migration_id}/reports/`

## Project Structure

```
salesforce-migration/
├── config/
│   ├── connection.yaml          # Database and API connections
│   ├── schema_mappings.yaml     # OrientDB → Salesforce mappings
│   └── load_order.yaml          # Dependency-aware load phases
├── scripts/
│   ├── extraction/
│   │   ├── extract_schema.py    # Schema discovery
│   │   └── extract_data.py      # Data extraction
│   ├── transformation/
│   │   └── transform_data.py    # Data transformation
│   └── loading/
│       └── load_data.py         # Salesforce bulk loading
├── data/
│   └── migrations/
│       └── MIGRATION_{timestamp}/
│           ├── schema.json
│           ├── extracted/       # Raw OrientDB data
│           ├── transformed/     # Salesforce-ready data
│           └── reports/         # Migration reports
├── logs/
│   └── MIGRATION_{timestamp}/   # Detailed logs
├── migrate.py                   # Main orchestrator
├── requirements.txt             # Python dependencies
├── Data-Migration-Strategy.md  # Detailed strategy document
└── README.md                    # This file
```

## Individual Script Usage

### Extract Schema Only
```bash
python scripts/extraction/extract_schema.py \
  --config config/connection.yaml \
  --output data/schema.json
```

### Extract Data Only
```bash
python scripts/extraction/extract_data.py \
  --config config/connection.yaml \
  --schema data/schema.json \
  --output-dir data/extracted/
```

### Transform Data Only
```bash
python scripts/transformation/transform_data.py \
  --input data/extracted/ \
  --config config/schema_mappings.yaml \
  --output data/transformed/
```

### Load Data Only
```bash
python scripts/loading/load_data.py \
  --input data/transformed/ \
  --config config/connection.yaml \
  --load-order config/load_order.yaml
```

## Key Features

### Automated & Repeatable
- Configuration-driven approach
- Idempotent operations (safe to re-run)
- Support for multiple test migrations

### Database Size Optimized
- Designed for <500MB databases
- Batch processing (1000 records)
- Efficient memory usage

### Dependency-Aware
- Automatic load order determination
- Preserves referential integrity
- Handles complex relationships

### Error Handling
- Pre/post-load validation
- Detailed error logging
- Rollback capability
- Retry logic for transient failures

### Salesforce Best Practices
- Bulk API 2.0 for performance
- External ID fields for relationships
- Respects API rate limits
- Sandbox-first approach

## Troubleshooting

### Connection Issues
- Verify OrientDB is running: `curl http://localhost:2480`
- Test Salesforce credentials with simple-salesforce
- Check firewall and network settings

### Validation Failures
- Review transformation errors in `transformed/{object}/transformation_metadata.json`
- Check schema mappings in `config/schema_mappings.yaml`
- Verify required fields are populated

### Load Failures
- Check Salesforce API limits
- Review failed records in `logs/{migration_id}/loading/failed_records/`
- Verify External ID fields exist in Salesforce
- Ensure all dependent objects are loaded first

### Performance Issues
- Reduce batch_size in `config/connection.yaml`
- Disable parallel processing temporarily
- Check OrientDB query performance

## Migration Checklist

### Before Migration
- [ ] OrientDB backup completed
- [ ] Salesforce sandbox created and clean
- [ ] Configuration files reviewed
- [ ] Schema mappings defined
- [ ] Test migration executed successfully
- [ ] Stakeholders notified

### During Migration
- [ ] Monitor logs for errors
- [ ] Track progress in console output
- [ ] Verify disk space availability
- [ ] Check Salesforce API usage

### After Migration
- [ ] Verify record counts match
- [ ] Test key relationships
- [ ] Run validation reports
- [ ] User acceptance testing
- [ ] Document any issues

## Support

For detailed strategy and design decisions, see:
- **Data-Migration-Strategy.md** - Comprehensive migration documentation
- **Migration-Requirements.md** - Original requirements

## License

Internal use only - Orienteer to Salesforce migration project.
