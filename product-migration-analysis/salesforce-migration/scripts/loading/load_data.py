#!/usr/bin/env python3
"""
Salesforce Data Loading Script

Loads transformed data to Salesforce using Bulk API 2.0.

Usage:
    python load_data.py --input transformed/ --config ../../config/connection.yaml --load-order ../../config/load_order.yaml
"""

import argparse
import json
import logging
import os
import time
import csv
from io import StringIO
from datetime import datetime
from typing import Dict, List, Any
import yaml
from simple_salesforce import Salesforce
from salesforce_bulk import SalesforceBulk

logger = logging.getLogger(__name__)


class SalesforceLoader:
    """Loads data to Salesforce using Bulk API"""

    def __init__(self, sf_config: Dict[str, Any], migration_id: str):
        self.config = sf_config
        self.migration_id = migration_id
        self.sf = None
        self.bulk = None

    def connect(self):
        """Establish connection to Salesforce"""
        try:
            self.sf = Salesforce(
                username=self.config['authentication']['username'],
                password=self.config['authentication']['password'],
                security_token=self.config['authentication']['security_token'],
                instance_url=self.config.get('instance_url'),
                version=self.config.get('api_version', '58.0')
            )
            self.bulk = SalesforceBulk(sessionId=self.sf.session_id, host=self.sf.sf_instance)
            logger.info("Connected to Salesforce successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Salesforce: {e}")
            raise

    def validate_environment(self) -> bool:
        """Validate Salesforce environment before loading"""
        checks = {
            'connection': self._check_connection(),
            'storage_available': self._check_storage(),
            'objects_exist': True  # TODO: Implement object existence check
        }

        all_passed = all(checks.values())
        if not all_passed:
            logger.error(f"Environment validation failed: {checks}")

        return all_passed

    def _check_connection(self) -> bool:
        """Verify Salesforce connection"""
        try:
            self.sf.query("SELECT Id FROM User LIMIT 1")
            return True
        except:
            return False

    def _check_storage(self) -> bool:
        """Check available data storage"""
        # TODO: Implement actual storage check via Limits API
        return True

    def convert_to_csv(self, records: List[Dict[str, Any]]) -> str:
        """Convert JSON records to CSV format for Bulk API"""
        if not records:
            return ""

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)

        return output.getvalue()

    def create_bulk_job(self, object_name: str, operation: str = 'insert') -> str:
        """Create Bulk API job"""
        job = self.bulk.create_insert_job(object_name, contentType='CSV')
        logger.info(f"Created bulk job {job} for {object_name}")
        return job

    def upload_batch(self, job_id: str, csv_data: str) -> str:
        """Upload CSV batch to Bulk API job"""
        batch = self.bulk.post_batch(job_id, csv_data)
        logger.info(f"Uploaded batch {batch} to job {job_id}")
        return batch

    def close_job(self, job_id: str):
        """Close Bulk API job"""
        self.bulk.close_job(job_id)
        logger.info(f"Closed job {job_id}")

    def monitor_batch(self, job_id: str, batch_id: str, timeout_minutes: int = 60) -> Dict[str, Any]:
        """Monitor bulk batch until completion"""
        start_time = time.time()
        poll_interval = 10  # seconds

        while True:
            try:
                batch_status = self.bulk.batch_status(batch_id, job_id)
                state = batch_status.get('state')

                logger.info(f"Batch {batch_id} status: {state}")

                if state in ['Completed', 'Failed']:
                    return batch_status

                if (time.time() - start_time) > (timeout_minutes * 60):
                    raise TimeoutError(f"Batch {batch_id} timed out after {timeout_minutes} minutes")

                time.sleep(poll_interval)

            except Exception as e:
                logger.error(f"Error monitoring batch {batch_id}: {e}")
                raise

    def get_batch_results(self, job_id: str, batch_id: str) -> Dict[str, Any]:
        """Retrieve results from completed batch"""
        try:
            results = self.bulk.get_batch_results(batch_id, job_id)
            return self._parse_batch_results(results)
        except Exception as e:
            logger.error(f"Error retrieving batch results: {e}")
            return {'successful': [], 'failed': []}

    def _parse_batch_results(self, results) -> Dict[str, Any]:
        """Parse batch results into successful and failed records"""
        # TODO: Implement actual result parsing based on Salesforce Bulk API response
        return {
            'successful': [],
            'failed': []
        }

    def load_object_data(self, object_name: str, input_dir: str) -> Dict[str, Any]:
        """Load all data for a specific Salesforce object"""
        object_dir = os.path.join(input_dir, object_name)

        if not os.path.exists(object_dir):
            logger.warning(f"No data directory found for {object_name}")
            return None

        # Load transformation metadata
        metadata_file = os.path.join(object_dir, 'transformation_metadata.json')
        if not os.path.exists(metadata_file):
            logger.error(f"No metadata found for {object_name}")
            return None

        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

        # Create bulk job
        job_id = self.create_bulk_job(object_name)

        total_loaded = 0
        total_failed = 0
        batch_results = []

        # Load each batch
        batch_files = sorted([f for f in os.listdir(object_dir) if f.startswith('batch_')])

        for batch_file in batch_files:
            batch_path = os.path.join(object_dir, batch_file)

            with open(batch_path, 'r') as f:
                records = json.load(f)

            if not records:
                continue

            # Convert to CSV
            csv_data = self.convert_to_csv(records)

            # Upload batch
            batch_id = self.upload_batch(job_id, csv_data)

            # Monitor batch
            batch_status = self.monitor_batch(job_id, batch_id)

            # Get results
            results = self.get_batch_results(job_id, batch_id)

            batch_result = {
                'batch_file': batch_file,
                'batch_id': batch_id,
                'records_processed': len(records),
                'records_successful': len(results['successful']),
                'records_failed': len(results['failed']),
                'status': batch_status.get('state')
            }

            batch_results.append(batch_result)
            total_loaded += len(results['successful'])
            total_failed += len(results['failed'])

            logger.info(
                f"Batch {batch_file}: {len(results['successful'])} success, "
                f"{len(results['failed'])} failed"
            )

        # Close job
        self.close_job(job_id)

        load_metadata = {
            'salesforce_object': object_name,
            'job_id': job_id,
            'total_records_loaded': total_loaded,
            'total_records_failed': total_failed,
            'load_timestamp': datetime.now().isoformat(),
            'batches': batch_results
        }

        # Save load metadata
        load_metadata_file = os.path.join(object_dir, 'load_metadata.json')
        with open(load_metadata_file, 'w') as f:
            json.dump(load_metadata, f, indent=2)

        logger.info(
            f"Loaded {object_name}: {total_loaded} success, {total_failed} failed"
        )

        return load_metadata

    def load_in_order(self, input_dir: str, load_order_config: Dict[str, Any]) -> Dict[str, Any]:
        """Load objects in dependency order"""
        self.connect()

        # Validate environment
        if not self.validate_environment():
            raise RuntimeError("Environment validation failed")

        load_summary = {
            'migration_id': self.migration_id,
            'load_started': datetime.now().isoformat(),
            'phases': []
        }

        # Process each phase
        for phase in load_order_config['load_phases']:
            phase_num = phase['phase']
            phase_objects = phase['objects']

            logger.info(f"Starting Phase {phase_num}: {phase['description']}")

            phase_results = []

            for obj_config in phase_objects:
                # Handle both string and dict object definitions
                if isinstance(obj_config, str):
                    object_name = obj_config
                elif isinstance(obj_config, dict):
                    object_name = list(obj_config.keys())[0]
                else:
                    continue

                metadata = self.load_object_data(object_name, input_dir)
                if metadata:
                    phase_results.append(metadata)

            load_summary['phases'].append({
                'phase': phase_num,
                'description': phase['description'],
                'results': phase_results
            })

        load_summary['load_completed'] = datetime.now().isoformat()

        # Save summary
        summary_file = os.path.join(input_dir, 'load_summary.json')
        with open(summary_file, 'w') as f:
            json.dump(load_summary, f, indent=2)

        logger.info(f"Load complete. Summary saved to {summary_file}")
        return load_summary


def main():
    parser = argparse.ArgumentParser(description='Load data to Salesforce')
    parser.add_argument('--input', required=True, help='Input directory with transformed data')
    parser.add_argument('--config', required=True, help='Path to connection config')
    parser.add_argument('--load-order', required=True, help='Path to load order config')
    parser.add_argument('--log-level', default='INFO')

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Load configs
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    with open(args.load_order, 'r') as f:
        load_order = yaml.safe_load(f)

    # Create migration ID
    migration_id = f"MIGRATION_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Load data
    loader = SalesforceLoader(config['salesforce'], migration_id)
    summary = loader.load_in_order(args.input, load_order)

    logger.info("Load complete!")


if __name__ == '__main__':
    main()
