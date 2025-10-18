#!/usr/bin/env python3
"""
Data Transformation Script

Transforms OrientDB data to Salesforce format using mapping rules.

Usage:
    python transform_data.py --input data/ --config ../../config/schema_mappings.yaml --output transformed/
"""

import argparse
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Any
import yaml
import re

logger = logging.getLogger(__name__)


class DataTransformer:
    """Transforms OrientDB data to Salesforce format"""

    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.mappings = {m['orientdb_class']: m for m in self.config['mappings']}
        self.external_id_cache = {}

    def transform_field(self, value: Any, field_config: Dict[str, Any]) -> Any:
        """Apply field-level transformations"""
        if value is None:
            return None

        transformation = field_config.get('transformation')

        transformations = {
            'trim_whitespace': lambda v: str(v).strip() if v else None,
            'to_uppercase': lambda v: str(v).upper() if v else None,
            'to_lowercase': lambda v: str(v).lower() if v else None,
            'to_email_format': lambda v: f"{v}@company.com" if '@' not in str(v) else v,
            'truncate': lambda v: str(v)[:field_config.get('max_length', 255)],
        }

        if transformation in transformations:
            return transformations[transformation](value)

        # Special transformations
        if transformation == 'lookup_foreign_key':
            return self._resolve_lookup(value, field_config)
        elif transformation == 'date_to_iso':
            return self._convert_date(value)

        return value

    def _resolve_lookup(self, orientdb_rid: str, field_config: Dict[str, Any]) -> str:
        """Convert OrientDB RID to Salesforce External ID"""
        if not orientdb_rid:
            return None

        # Generate external ID format: ORIENTDB_10_12345
        external_id = f"ORIENTDB_{orientdb_rid.replace('#', '').replace(':', '_')}"
        return external_id

    def _convert_date(self, value: Any) -> str:
        """Convert date to ISO format"""
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value)
                return dt.date().isoformat()
            except:
                return value
        return value

    def transform_record(self, record: Dict[str, Any], mapping_config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single record according to mapping rules"""
        transformed = {}

        # Add external ID for reference
        orientdb_rid = record.get('orientdb_rid', '')
        transformed['OrientDB_External_ID__c'] = f"ORIENTDB_{orientdb_rid.replace('#', '').replace(':', '_')}"

        # Transform each field
        for field_mapping in mapping_config['transformation_rules'].get('fields', []):
            orientdb_field = field_mapping['orientdb_field']
            salesforce_field = field_mapping['salesforce_field']

            value = record.get(orientdb_field)
            transformed_value = self.transform_field(value, field_mapping)

            # Apply validation
            if 'max_length' in field_mapping:
                if transformed_value and len(str(transformed_value)) > field_mapping['max_length']:
                    logger.warning(
                        f"Truncating {salesforce_field}: {len(str(transformed_value))} > {field_mapping['max_length']}"
                    )
                    transformed_value = str(transformed_value)[:field_mapping['max_length']]

            transformed[salesforce_field] = transformed_value

        # Handle relationships
        for rel_mapping in mapping_config['transformation_rules'].get('relationships', []):
            orientdb_property = rel_mapping['orientdb_property']
            salesforce_field = rel_mapping['salesforce_field']

            orientdb_rid = record.get(orientdb_property)
            if orientdb_rid:
                # Create external ID reference
                external_id = self._resolve_lookup(orientdb_rid, rel_mapping)
                transformed[salesforce_field] = external_id

        return transformed

    def validate_record(self, record: Dict[str, Any], mapping_config: Dict[str, Any]) -> List[str]:
        """Validate transformed record"""
        errors = []

        for field_mapping in mapping_config['transformation_rules'].get('fields', []):
            salesforce_field = field_mapping['salesforce_field']
            value = record.get(salesforce_field)

            # Check required fields
            if field_mapping.get('required', False) and not value:
                errors.append(f"Required field {salesforce_field} is null")

            # Check max length
            if 'max_length' in field_mapping and value:
                if len(str(value)) > field_mapping['max_length']:
                    errors.append(f"Field {salesforce_field} exceeds max length")

        return errors

    def transform_class_data(
        self,
        input_dir: str,
        class_name: str,
        output_dir: str
    ) -> Dict[str, Any]:
        """Transform all data for a specific class"""

        # Get mapping config
        mapping_config = self.mappings.get(class_name)
        if not mapping_config:
            logger.warning(f"No mapping found for class {class_name}, skipping")
            return None

        salesforce_object = mapping_config['salesforce_object']
        class_dir = os.path.join(input_dir, class_name)

        if not os.path.exists(class_dir):
            logger.warning(f"No data directory found for {class_name}")
            return None

        # Load manifest
        manifest_file = os.path.join(class_dir, 'manifest.json')
        if not os.path.exists(manifest_file):
            logger.error(f"No manifest found for {class_name}")
            return None

        with open(manifest_file, 'r') as f:
            manifest = json.load(f)

        # Create output directory
        output_class_dir = os.path.join(output_dir, salesforce_object)
        os.makedirs(output_class_dir, exist_ok=True)

        total_transformed = 0
        total_errors = 0
        transformation_errors = []

        # Process each batch
        for batch_info in manifest['batches']:
            batch_file = batch_info['file_path']

            with open(batch_file, 'r') as f:
                records = json.load(f)

            transformed_records = []
            for record in records:
                try:
                    transformed = self.transform_record(record, mapping_config)

                    # Validate
                    errors = self.validate_record(transformed, mapping_config)
                    if errors:
                        total_errors += 1
                        transformation_errors.append({
                            'record': record.get('orientdb_rid'),
                            'errors': errors
                        })
                        continue

                    transformed_records.append(transformed)
                    total_transformed += 1

                except Exception as e:
                    logger.error(f"Error transforming record {record.get('orientdb_rid')}: {e}")
                    total_errors += 1
                    transformation_errors.append({
                        'record': record.get('orientdb_rid'),
                        'error': str(e)
                    })

            # Save transformed batch
            output_batch_file = os.path.join(
                output_class_dir,
                f"batch_{batch_info['batch_id']}.json"
            )
            with open(output_batch_file, 'w') as f:
                json.dump(transformed_records, f, indent=2)

        # Save transformation metadata
        metadata = {
            'salesforce_object': salesforce_object,
            'source_class': class_name,
            'total_records': manifest['total_records'],
            'records_transformed': total_transformed,
            'records_failed': total_errors,
            'transformation_timestamp': datetime.now().isoformat(),
            'errors': transformation_errors[:100]  # First 100 errors
        }

        metadata_file = os.path.join(output_class_dir, 'transformation_metadata.json')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(
            f"Transformed {class_name} -> {salesforce_object}: "
            f"{total_transformed} success, {total_errors} errors"
        )

        return metadata

    def transform_all(self, input_dir: str, output_dir: str) -> Dict[str, Any]:
        """Transform all classes"""
        os.makedirs(output_dir, exist_ok=True)

        transformation_summary = {
            'transformation_started': datetime.now().isoformat(),
            'input_directory': input_dir,
            'output_directory': output_dir,
            'classes': []
        }

        # Transform each mapped class
        for class_name in self.mappings.keys():
            metadata = self.transform_class_data(input_dir, class_name, output_dir)
            if metadata:
                transformation_summary['classes'].append(metadata)

        transformation_summary['transformation_completed'] = datetime.now().isoformat()

        # Save summary
        summary_file = os.path.join(output_dir, 'transformation_summary.json')
        with open(summary_file, 'w') as f:
            json.dump(transformation_summary, f, indent=2)

        logger.info(f"Transformation complete. Summary saved to {summary_file}")
        return transformation_summary


def main():
    parser = argparse.ArgumentParser(description='Transform OrientDB data to Salesforce format')
    parser.add_argument('--input', required=True, help='Input data directory')
    parser.add_argument('--config', required=True, help='Path to schema mappings YAML')
    parser.add_argument('--output', required=True, help='Output directory for transformed data')
    parser.add_argument('--log-level', default='INFO')

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Transform data
    transformer = DataTransformer(args.config)
    summary = transformer.transform_all(args.input, args.output)

    # Print summary
    total_success = sum(c['records_transformed'] for c in summary['classes'])
    total_failed = sum(c['records_failed'] for c in summary['classes'])

    logger.info(f"Total records transformed: {total_success}")
    logger.info(f"Total records failed: {total_failed}")


if __name__ == '__main__':
    main()
