#!/usr/bin/env python3
"""
OrientDB Data Extraction Script

Extracts data in batches with dependency ordering.

Usage:
    python extract_data.py --config ../../config/connection.yaml --schema schema.json --output-dir data/
"""

import argparse
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Any
import pyorient

logger = logging.getLogger(__name__)


class DataExtractor:
    """Extracts data from OrientDB in batches"""

    def __init__(self, orientdb_config: Dict[str, Any], migration_id: str):
        self.config = orientdb_config
        self.migration_id = migration_id
        self.client = None
        self.batch_size = 1000

    def connect(self):
        """Establish connection to OrientDB"""
        self.client = pyorient.OrientDB(self.config['host'], self.config['port'])
        self.client.connect(self.config['username'], self.config['password'])
        self.client.db_open(
            self.config['database'],
            self.config['username'],
            self.config['password']
        )
        logger.info(f"Connected to OrientDB: {self.config['database']}")

    def extract_class_data(self, class_name: str, output_dir: str) -> Dict[str, Any]:
        """Extract all records for a specific class in batches"""
        class_dir = os.path.join(output_dir, class_name)
        os.makedirs(class_dir, exist_ok=True)

        batch_num = 0
        total_records = 0
        batches = []
        last_rid = "#-1:-1"

        logger.info(f"Extracting data for class: {class_name}")

        while True:
            query = f"""
            SELECT *,
                   @rid as orientdb_rid,
                   @class as orientdb_class,
                   @version as orientdb_version
            FROM {class_name}
            WHERE @rid > {last_rid}
            ORDER BY @rid
            LIMIT {self.batch_size}
            """

            try:
                result = self.client.command(query)

                if not result or len(result) == 0:
                    break

                # Convert to JSON-serializable format
                records = []
                for record in result:
                    record_data = self._convert_record_to_dict(record)
                    records.append(record_data)

                # Save batch
                batch_num += 1
                batch_file = os.path.join(class_dir, f"batch_{batch_num:04d}.json")

                with open(batch_file, 'w') as f:
                    json.dump(records, f, indent=2, default=str)

                # Update tracking
                total_records += len(records)
                last_rid = records[-1]['orientdb_rid']

                batch_info = {
                    'batch_id': f"{batch_num:04d}",
                    'record_count': len(records),
                    'start_rid': records[0]['orientdb_rid'],
                    'end_rid': last_rid,
                    'file_path': batch_file
                }
                batches.append(batch_info)

                logger.info(f"  Batch {batch_num}: {len(records)} records")

            except Exception as e:
                logger.error(f"Error extracting batch {batch_num} for {class_name}: {e}")
                break

        # Create manifest
        manifest = {
            'class_name': class_name,
            'total_records': total_records,
            'total_batches': batch_num,
            'batch_size': self.batch_size,
            'extraction_started': datetime.now().isoformat(),
            'extraction_completed': datetime.now().isoformat(),
            'batches': batches
        }

        manifest_file = os.path.join(class_dir, 'manifest.json')
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Completed extraction for {class_name}: {total_records} records in {batch_num} batches")
        return manifest

    def _convert_record_to_dict(self, record) -> Dict[str, Any]:
        """Convert OrientDB record to dictionary"""
        data = {}

        for key, value in record.oRecordData.items():
            # Handle special types
            if isinstance(value, pyorient.types.OrientRecordLink):
                data[key] = str(value.get_hash())  # Store as RID string
            elif isinstance(value, list):
                data[key] = [self._convert_value(v) for v in value]
            elif isinstance(value, dict):
                data[key] = {k: self._convert_value(v) for k, v in value.items()}
            else:
                data[key] = self._convert_value(value)

        return data

    def _convert_value(self, value):
        """Convert individual value to JSON-serializable format"""
        if isinstance(value, pyorient.types.OrientRecordLink):
            return str(value.get_hash())
        elif isinstance(value, (datetime, )):
            return value.isoformat()
        else:
            return value

    def extract_relationships(self, class_name: str, property_name: str, output_dir: str):
        """Extract relationship data for a specific property"""
        rel_dir = os.path.join(output_dir, 'relationships')
        os.makedirs(rel_dir, exist_ok=True)

        query = f"""
        SELECT
            @rid as source_rid,
            @class as source_class,
            {property_name}.@rid as target_rid,
            {property_name}.@class as target_class,
            '{property_name}' as relationship_name
        FROM {class_name}
        WHERE {property_name} IS NOT NULL
        """

        try:
            result = self.client.command(query)
            relationships = []

            for record in result:
                relationships.append(self._convert_record_to_dict(record))

            # Save relationships
            rel_file = os.path.join(rel_dir, f"{class_name}_{property_name}.json")
            with open(rel_file, 'w') as f:
                json.dump(relationships, f, indent=2)

            logger.info(f"Extracted {len(relationships)} relationships for {class_name}.{property_name}")

        except Exception as e:
            logger.error(f"Error extracting relationships for {class_name}.{property_name}: {e}")

    def extract_all_data(self, schema: Dict[str, Any], output_dir: str) -> Dict[str, Any]:
        """Extract all data based on schema definition"""
        self.connect()

        try:
            extraction_metadata = {
                'migration_id': self.migration_id,
                'extraction_started': datetime.now().isoformat(),
                'database': self.config['database'],
                'classes': []
            }

            # Determine load order based on dependencies
            load_order = self._determine_load_order(schema)

            for class_name in load_order:
                manifest = self.extract_class_data(class_name, output_dir)
                extraction_metadata['classes'].append(manifest)

            # Extract relationships
            for rel in schema.get('relationships', []):
                if rel.get('type') in ['LINK', 'LINKLIST', 'LINKSET']:
                    # Determine source class from schema
                    source_class = self._find_class_for_property(
                        schema,
                        rel.get('property')
                    )
                    if source_class:
                        self.extract_relationships(
                            source_class,
                            rel.get('property'),
                            output_dir
                        )

            extraction_metadata['extraction_completed'] = datetime.now().isoformat()

            # Save metadata
            metadata_file = os.path.join(output_dir, 'extraction_metadata.json')
            with open(metadata_file, 'w') as f:
                json.dump(extraction_metadata, f, indent=2)

            logger.info("Data extraction completed successfully")
            return extraction_metadata

        finally:
            if self.client:
                self.client.db_close()

    def _determine_load_order(self, schema: Dict[str, Any]) -> List[str]:
        """Determine load order based on relationship dependencies"""
        # Simplified topological sort
        # In production, implement full dependency graph resolution

        classes = [c['name'] for c in schema['classes']]
        relationships = schema.get('relationships', [])

        # Build dependency map
        dependencies = {cls: set() for cls in classes}

        for rel in relationships:
            # Find source class
            source = self._find_class_for_property(schema, rel.get('property'))
            target = rel.get('linkedClass')

            if source and target and source in dependencies:
                dependencies[source].add(target)

        # Simple ordering: classes with no dependencies first
        no_deps = [cls for cls, deps in dependencies.items() if not deps]
        has_deps = [cls for cls, deps in dependencies.items() if deps]

        return no_deps + has_deps

    def _find_class_for_property(self, schema: Dict[str, Any], property_name: str) -> str:
        """Find which class contains a specific property"""
        for cls in schema['classes']:
            for prop in cls.get('properties', []):
                if prop['name'] == property_name:
                    return cls['name']
        return None


def main():
    parser = argparse.ArgumentParser(description='Extract OrientDB data')
    parser.add_argument('--config', required=True, help='Path to connection config')
    parser.add_argument('--schema', required=True, help='Path to schema JSON file')
    parser.add_argument('--output-dir', required=True, help='Output directory for data')
    parser.add_argument('--log-level', default='INFO')

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Load config and schema
    import yaml
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    with open(args.schema, 'r') as f:
        schema = json.load(f)

    # Create migration ID
    migration_id = f"MIGRATION_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Extract data
    extractor = DataExtractor(config['orientdb'], migration_id)
    metadata = extractor.extract_all_data(schema, args.output_dir)

    logger.info(f"Extraction complete. Metadata saved to {args.output_dir}/extraction_metadata.json")


if __name__ == '__main__':
    main()
