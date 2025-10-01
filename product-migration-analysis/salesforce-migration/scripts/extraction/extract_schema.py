#!/usr/bin/env python3
"""
OrientDB Schema Extraction Script

Extracts complete schema definitions including:
- Classes and inheritance hierarchy
- Properties with types and constraints
- Indexes
- Relationships (LINK, LINKLIST, etc.)

Usage:
    python extract_schema.py --config ../../config/connection.yaml --output schema.json
"""

import argparse
import json
import logging
from datetime import datetime
from typing import Dict, List, Any
import pyorient

logger = logging.getLogger(__name__)


class SchemaExtractor:
    """Extracts schema metadata from OrientDB database"""

    def __init__(self, orientdb_config: Dict[str, Any]):
        self.config = orientdb_config
        self.client = None

    def connect(self):
        """Establish connection to OrientDB"""
        try:
            self.client = pyorient.OrientDB(
                self.config['host'],
                self.config['port']
            )
            session_id = self.client.connect(
                self.config['username'],
                self.config['password']
            )
            self.client.db_open(
                self.config['database'],
                self.config['username'],
                self.config['password']
            )
            logger.info(f"Connected to OrientDB: {self.config['database']}")
        except Exception as e:
            logger.error(f"Failed to connect to OrientDB: {e}")
            raise

    def extract_classes(self) -> List[Dict[str, Any]]:
        """Extract all class definitions"""
        query = """
        SELECT name, superClass, abstract, strictMode, clusterIds
        FROM (SELECT expand(classes) FROM metadata:schema)
        """
        result = self.client.command(query)

        classes = []
        for record in result:
            class_def = {
                'name': record.oRecordData.get('name'),
                'superClass': record.oRecordData.get('superClass'),
                'abstract': record.oRecordData.get('abstract', False),
                'strictMode': record.oRecordData.get('strictMode', False),
                'clusterIds': record.oRecordData.get('clusterIds', [])
            }

            # Get record count
            count_query = f"SELECT count(*) as count FROM {class_def['name']}"
            try:
                count_result = self.client.command(count_query)
                class_def['record_count'] = count_result[0].oRecordData.get('count', 0)
            except:
                class_def['record_count'] = 0

            classes.append(class_def)

        logger.info(f"Extracted {len(classes)} class definitions")
        return classes

    def extract_properties(self, class_name: str) -> List[Dict[str, Any]]:
        """Extract properties for a specific class"""
        query = f"""
        SELECT name, type, mandatory, notNull, min, max, regexp,
               linkedClass, linkedType, collate, defaultValue, readOnly
        FROM (SELECT expand(properties) FROM metadata:schema
              WHERE name = '{class_name}')
        """
        result = self.client.command(query)

        properties = []
        for record in result:
            prop_def = {
                'name': record.oRecordData.get('name'),
                'type': record.oRecordData.get('type'),
                'mandatory': record.oRecordData.get('mandatory', False),
                'notNull': record.oRecordData.get('notNull', False),
                'min': record.oRecordData.get('min'),
                'max': record.oRecordData.get('max'),
                'regexp': record.oRecordData.get('regexp'),
                'linkedClass': record.oRecordData.get('linkedClass'),
                'linkedType': record.oRecordData.get('linkedType'),
                'collate': record.oRecordData.get('collate'),
                'defaultValue': record.oRecordData.get('defaultValue'),
                'readOnly': record.oRecordData.get('readOnly', False)
            }
            properties.append(prop_def)

        return properties

    def extract_indexes(self, class_name: str) -> List[Dict[str, Any]]:
        """Extract indexes for a specific class"""
        query = f"""
        SELECT name, type, definition, metadata
        FROM (SELECT expand(indexes) FROM metadata:indexmanager)
        WHERE definition LIKE '%{class_name}%'
        """
        try:
            result = self.client.command(query)
            indexes = []
            for record in result:
                index_def = {
                    'name': record.oRecordData.get('name'),
                    'type': record.oRecordData.get('type'),
                    'definition': record.oRecordData.get('definition'),
                    'metadata': record.oRecordData.get('metadata', {})
                }
                indexes.append(index_def)
            return indexes
        except:
            return []

    def extract_relationships(self) -> List[Dict[str, Any]]:
        """Extract all relationship definitions"""
        query = """
        SELECT name, type, linkedClass
        FROM (SELECT expand(properties) FROM metadata:schema)
        WHERE type IN ['LINK', 'LINKLIST', 'LINKSET', 'LINKMAP']
        """
        result = self.client.command(query)

        relationships = []
        for record in result:
            rel_def = {
                'property': record.oRecordData.get('name'),
                'type': record.oRecordData.get('type'),
                'linkedClass': record.oRecordData.get('linkedClass'),
                'cardinality': self._determine_cardinality(record.oRecordData.get('type'))
            }
            relationships.append(rel_def)

        logger.info(f"Extracted {len(relationships)} relationship definitions")
        return relationships

    def _determine_cardinality(self, link_type: str) -> str:
        """Determine relationship cardinality from link type"""
        mapping = {
            'LINK': 'many-to-one',
            'LINKLIST': 'one-to-many',
            'LINKSET': 'one-to-many',
            'LINKMAP': 'one-to-many'
        }
        return mapping.get(link_type, 'unknown')

    def extract_full_schema(self) -> Dict[str, Any]:
        """Extract complete schema with all metadata"""
        self.connect()

        try:
            classes = self.extract_classes()

            # Add properties and indexes to each class
            for class_def in classes:
                class_name = class_def['name']
                class_def['properties'] = self.extract_properties(class_name)
                class_def['indexes'] = self.extract_indexes(class_name)

            relationships = self.extract_relationships()

            schema = {
                'extraction_timestamp': datetime.now().isoformat(),
                'database_name': self.config['database'],
                'total_classes': len(classes),
                'total_relationships': len(relationships),
                'classes': classes,
                'relationships': relationships,
                'database_size_mb': self._estimate_database_size(classes)
            }

            logger.info("Schema extraction completed successfully")
            return schema

        finally:
            if self.client:
                self.client.db_close()

    def _estimate_database_size(self, classes: List[Dict]) -> float:
        """Estimate total database size in MB"""
        # Simplified estimation based on record counts
        # In production, query actual cluster sizes
        total_records = sum(c.get('record_count', 0) for c in classes)
        estimated_mb = (total_records * 1024) / (1024 * 1024)  # Rough estimate
        return round(estimated_mb, 2)


def main():
    parser = argparse.ArgumentParser(description='Extract OrientDB schema')
    parser.add_argument('--config', required=True, help='Path to connection config')
    parser.add_argument('--output', required=True, help='Output JSON file path')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Load config
    import yaml
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    # Extract schema
    extractor = SchemaExtractor(config['orientdb'])
    schema = extractor.extract_full_schema()

    # Save to file
    with open(args.output, 'w') as f:
        json.dump(schema, f, indent=2)

    logger.info(f"Schema saved to {args.output}")
    logger.info(f"Total classes: {schema['total_classes']}")
    logger.info(f"Total relationships: {schema['total_relationships']}")
    logger.info(f"Estimated database size: {schema['database_size_mb']} MB")


if __name__ == '__main__':
    main()
