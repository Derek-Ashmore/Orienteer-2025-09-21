#!/usr/bin/env python3
"""
Main Migration Orchestrator

Coordinates the complete OrientDB to Salesforce migration process.

Usage:
    python migrate.py --config config/connection.yaml --mode test
    python migrate.py --config config/connection.yaml --mode production --skip-extraction
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any
import yaml

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from extraction.extract_schema import SchemaExtractor
from extraction.extract_data import DataExtractor
from transformation.transform_data import DataTransformer
from loading.load_data import SalesforceLoader


class MigrationOrchestrator:
    """Main orchestrator for the migration process"""

    def __init__(self, config_path: str, mode: str = 'test'):
        self.config_path = config_path
        self.mode = mode
        self.migration_id = f"MIGRATION_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Setup directories
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.base_dir, 'data', 'migrations', self.migration_id)
        self.log_dir = os.path.join(self.base_dir, 'logs', self.migration_id)

        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)

        self.setup_logging()

    def setup_logging(self):
        """Configure logging for the migration"""
        log_file = os.path.join(self.log_dir, 'migration.log')

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"{'='*80}")
        self.logger.info(f"Migration ID: {self.migration_id}")
        self.logger.info(f"Mode: {self.mode}")
        self.logger.info(f"Data directory: {self.data_dir}")
        self.logger.info(f"Log directory: {self.log_dir}")
        self.logger.info(f"{'='*80}")

    def execute_migration(self, skip_extraction=False, skip_validation=False):
        """Execute the complete migration pipeline"""
        try:
            self.logger.info("Starting OrientDB to Salesforce migration")

            # Phase 1: Schema Extraction
            if not skip_extraction:
                self.logger.info("\n[PHASE 1] Extracting schema from OrientDB...")
                schema = self.extract_schema()
                self.logger.info(f"Schema extraction complete. Found {len(schema['classes'])} classes")
            else:
                self.logger.info("[PHASE 1] Skipping schema extraction")
                schema_file = os.path.join(self.data_dir, 'schema.json')
                if os.path.exists(schema_file):
                    import json
                    with open(schema_file, 'r') as f:
                        schema = json.load(f)
                else:
                    raise FileNotFoundError("Schema file not found. Cannot skip extraction.")

            # Phase 2: Data Extraction
            if not skip_extraction:
                self.logger.info("\n[PHASE 2] Extracting data from OrientDB...")
                extraction_dir = os.path.join(self.data_dir, 'extracted')
                extraction_result = self.extract_data(schema, extraction_dir)
                self.logger.info(f"Data extraction complete")
            else:
                self.logger.info("[PHASE 2] Skipping data extraction")
                extraction_dir = os.path.join(self.data_dir, 'extracted')

            # Phase 3: Data Transformation
            self.logger.info("\n[PHASE 3] Transforming data for Salesforce...")
            transformation_dir = os.path.join(self.data_dir, 'transformed')
            transformation_result = self.transform_data(extraction_dir, transformation_dir)
            self.logger.info(f"Data transformation complete")

            # Phase 4: Pre-Load Validation
            if not skip_validation:
                self.logger.info("\n[PHASE 4] Validating transformed data...")
                validation_passed = self.validate_data(transformation_result)
                if not validation_passed:
                    raise ValueError("Pre-load validation failed")
                self.logger.info("Pre-load validation passed")
            else:
                self.logger.info("[PHASE 4] Skipping pre-load validation")

            # Phase 5: Data Loading
            self.logger.info("\n[PHASE 5] Loading data to Salesforce...")
            load_result = self.load_data(transformation_dir)
            self.logger.info(f"Data loading complete")

            # Phase 6: Post-Load Validation
            if not skip_validation:
                self.logger.info("\n[PHASE 6] Post-load validation...")
                post_validation_passed = self.validate_loaded_data(load_result)
                if not post_validation_passed:
                    self.logger.warning("Post-load validation found issues")
                else:
                    self.logger.info("Post-load validation passed")

            # Phase 7: Generate Reports
            self.logger.info("\n[PHASE 7] Generating migration reports...")
            self.generate_reports({
                'schema': schema,
                'extraction': extraction_result if not skip_extraction else None,
                'transformation': transformation_result,
                'load': load_result
            })

            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"Migration {self.migration_id} completed successfully!")
            self.logger.info(f"All logs saved to: {self.log_dir}")
            self.logger.info(f"All data saved to: {self.data_dir}")
            self.logger.info(f"{'='*80}")

        except Exception as e:
            self.logger.error(f"\n{'='*80}")
            self.logger.error(f"Migration failed: {str(e)}")
            self.logger.error(f"{'='*80}")
            self.handle_failure(e)
            raise

    def extract_schema(self) -> Dict[str, Any]:
        """Extract schema from OrientDB"""
        extractor = SchemaExtractor(self.config['orientdb'])
        schema = extractor.extract_full_schema()

        # Save schema
        import json
        schema_file = os.path.join(self.data_dir, 'schema.json')
        with open(schema_file, 'w') as f:
            json.dump(schema, f, indent=2)

        self.logger.info(f"Schema saved to {schema_file}")
        return schema

    def extract_data(self, schema: Dict[str, Any], output_dir: str) -> Dict[str, Any]:
        """Extract data from OrientDB"""
        extractor = DataExtractor(self.config['orientdb'], self.migration_id)
        result = extractor.extract_all_data(schema, output_dir)
        return result

    def transform_data(self, input_dir: str, output_dir: str) -> Dict[str, Any]:
        """Transform data for Salesforce"""
        mappings_file = os.path.join(self.base_dir, 'config', 'schema_mappings.yaml')
        transformer = DataTransformer(mappings_file)
        result = transformer.transform_all(input_dir, output_dir)
        return result

    def validate_data(self, transformation_result: Dict[str, Any]) -> bool:
        """Validate transformed data before loading"""
        total_records = sum(c['records_transformed'] for c in transformation_result['classes'])
        total_errors = sum(c['records_failed'] for c in transformation_result['classes'])

        error_rate = total_errors / total_records if total_records > 0 else 0

        self.logger.info(f"Validation summary:")
        self.logger.info(f"  Total records: {total_records}")
        self.logger.info(f"  Records with errors: {total_errors}")
        self.logger.info(f"  Error rate: {error_rate:.2%}")

        max_error_rate = 0.05  # 5%
        return error_rate <= max_error_rate

    def load_data(self, input_dir: str) -> Dict[str, Any]:
        """Load data to Salesforce"""
        load_order_file = os.path.join(self.base_dir, 'config', 'load_order.yaml')
        with open(load_order_file, 'r') as f:
            load_order = yaml.safe_load(f)

        loader = SalesforceLoader(self.config['salesforce'], self.migration_id)
        result = loader.load_in_order(input_dir, load_order)
        return result

    def validate_loaded_data(self, load_result: Dict[str, Any]) -> bool:
        """Validate data after loading to Salesforce"""
        # TODO: Implement actual post-load validation
        # Compare record counts, check relationships, etc.
        self.logger.info("Post-load validation not yet implemented")
        return True

    def generate_reports(self, results: Dict[str, Any]):
        """Generate migration reports"""
        import json

        report_dir = os.path.join(self.data_dir, 'reports')
        os.makedirs(report_dir, exist_ok=True)

        # Summary report
        summary = {
            'migration_id': self.migration_id,
            'mode': self.mode,
            'timestamp': datetime.now().isoformat(),
            'schema': {
                'total_classes': len(results['schema']['classes']),
                'total_relationships': len(results['schema']['relationships'])
            },
            'transformation': {
                'total_records': sum(
                    c['records_transformed'] for c in results['transformation']['classes']
                ),
                'total_errors': sum(
                    c['records_failed'] for c in results['transformation']['classes']
                )
            },
            'load': results['load']
        }

        summary_file = os.path.join(report_dir, 'migration_summary.json')
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        self.logger.info(f"Migration summary saved to {summary_file}")

    def handle_failure(self, error: Exception):
        """Handle migration failure"""
        self.logger.error("Migration failed. Options:")
        self.logger.error("1. Review logs and fix issues")
        self.logger.error("2. Run with --skip-extraction to resume from transformation")
        self.logger.error("3. Contact support if issue persists")

        if self.mode == 'test':
            self.logger.info("Test mode: Automatic cleanup recommended")
        else:
            response = input("\nAttempt rollback? (yes/no): ")
            if response.lower() == 'yes':
                self.logger.info("Rollback not yet implemented")


def main():
    parser = argparse.ArgumentParser(
        description='OrientDB to Salesforce Migration Orchestrator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test migration with full pipeline
  python migrate.py --config config/connection.yaml --mode test

  # Production migration skipping extraction phase
  python migrate.py --config config/connection.yaml --mode production --skip-extraction

  # Test migration without validation
  python migrate.py --config config/connection.yaml --mode test --skip-validation
        """
    )

    parser.add_argument(
        '--config',
        required=True,
        help='Path to connection configuration file'
    )

    parser.add_argument(
        '--mode',
        choices=['test', 'production'],
        default='test',
        help='Migration mode (default: test)'
    )

    parser.add_argument(
        '--skip-extraction',
        action='store_true',
        help='Skip extraction phase (use existing data)'
    )

    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip validation phases'
    )

    args = parser.parse_args()

    # Verify config file exists
    if not os.path.exists(args.config):
        print(f"Error: Configuration file not found: {args.config}")
        sys.exit(1)

    # Execute migration
    orchestrator = MigrationOrchestrator(args.config, args.mode)
    orchestrator.execute_migration(
        skip_extraction=args.skip_extraction,
        skip_validation=args.skip_validation
    )


if __name__ == '__main__':
    main()
