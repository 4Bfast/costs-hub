"""
Data Migration Engine

This module provides the main migration functionality to transform data from the existing
PostgreSQL-based system to the new multi-cloud DynamoDB structure.
"""

import logging
import asyncio
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
import boto3
from botocore.exceptions import ClientError
import psycopg2
from psycopg2.extras import RealDictCursor

from ..models.multi_cloud_models import (
    UnifiedCostRecord, ServiceCost, AccountCost, RegionCost,
    CloudProvider, ServiceCategory, Currency, DataQuality,
    CollectionMetadata, DataQualityLevel
)
from ..models.provider_models import ProviderType
from .transformation_engine import DataTransformationEngine
from .validation_tools import MigrationValidator


logger = logging.getLogger(__name__)


class DataMigrator:
    """
    Main data migration engine for transforming PostgreSQL data to DynamoDB.
    """
    
    def __init__(
        self,
        postgres_config: Dict[str, str],
        dynamodb_config: Dict[str, str],
        batch_size: int = 100
    ):
        """
        Initialize the data migrator.
        
        Args:
            postgres_config: PostgreSQL connection configuration
            dynamodb_config: DynamoDB configuration
            batch_size: Number of records to process in each batch
        """
        self.postgres_config = postgres_config
        self.dynamodb_config = dynamodb_config
        self.batch_size = batch_size
        
        # Initialize components
        self.transformer = DataTransformationEngine()
        self.validator = MigrationValidator()
        
        # Initialize AWS clients
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=dynamodb_config.get('region', 'us-east-1'),
            aws_access_key_id=dynamodb_config.get('access_key_id'),
            aws_secret_access_key=dynamodb_config.get('secret_access_key')
        )
        
        # DynamoDB tables
        self.cost_table = self.dynamodb.Table(
            dynamodb_config.get('cost_table', 'cost-analytics-data')
        )
        self.timeseries_table = self.dynamodb.Table(
            dynamodb_config.get('timeseries_table', 'cost-analytics-timeseries')
        )
        
        # Migration statistics
        self.stats = {
            'organizations_migrated': 0,
            'accounts_migrated': 0,
            'cost_records_migrated': 0,
            'errors': [],
            'warnings': [],
            'start_time': None,
            'end_time': None
        }
    
    async def migrate_all_data(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Migrate all data from PostgreSQL to DynamoDB.
        
        Args:
            start_date: Start date for cost data migration
            end_date: End date for cost data migration
            dry_run: If True, validate but don't write to DynamoDB
            
        Returns:
            Migration statistics and results
        """
        logger.info("Starting full data migration")
        self.stats['start_time'] = datetime.utcnow()
        
        try:
            # Step 1: Migrate organizations and accounts
            await self._migrate_organizations()
            
            # Step 2: Migrate cost data
            if start_date is None:
                start_date = date.today() - timedelta(days=365)  # Default to 1 year
            if end_date is None:
                end_date = date.today()
            
            await self._migrate_cost_data(start_date, end_date, dry_run)
            
            # Step 3: Validate migration
            validation_results = await self.validator.validate_migration(
                self.postgres_config,
                self.dynamodb_config,
                start_date,
                end_date
            )
            
            self.stats['validation_results'] = validation_results
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            self.stats['errors'].append(f"Migration failed: {str(e)}")
            raise
        
        finally:
            self.stats['end_time'] = datetime.utcnow()
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            self.stats['duration_seconds'] = duration
            
            logger.info(f"Migration completed in {duration:.2f} seconds")
            logger.info(f"Statistics: {self.stats}")
        
        return self.stats
    
    async def _migrate_organizations(self) -> None:
        """Migrate organizations and AWS accounts."""
        logger.info("Migrating organizations and accounts")
        
        conn = None
        try:
            conn = psycopg2.connect(**self.postgres_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get all active organizations
            cursor.execute("""
                SELECT o.id, o.org_name, o.created_at,
                       array_agg(
                           json_build_object(
                               'id', a.id,
                               'account_name', a.account_name,
                               'iam_role_arn', a.iam_role_arn,
                               'focus_s3_bucket_path', a.focus_s3_bucket_path,
                               'payer_account_id', a.payer_account_id,
                               'external_id', a.external_id,
                               'status', a.status,
                               'created_at', a.created_at
                           )
                       ) as aws_accounts
                FROM organizations o
                LEFT JOIN aws_accounts a ON o.id = a.organization_id
                WHERE o.status = 'ACTIVE'
                GROUP BY o.id, o.org_name, o.created_at
            """)
            
            organizations = cursor.fetchall()
            
            for org in organizations:
                try:
                    # Transform organization data
                    client_data = self.transformer.transform_organization(dict(org))
                    
                    # Store client configuration (this would go to a separate config table)
                    # For now, we'll log the transformation
                    logger.info(f"Transformed organization: {org['org_name']} -> {client_data['client_id']}")
                    
                    self.stats['organizations_migrated'] += 1
                    
                    # Count AWS accounts
                    if org['aws_accounts'] and org['aws_accounts'][0]:
                        valid_accounts = [acc for acc in org['aws_accounts'] if acc['id'] is not None]
                        self.stats['accounts_migrated'] += len(valid_accounts)
                    
                except Exception as e:
                    error_msg = f"Failed to migrate organization {org['org_name']}: {str(e)}"
                    logger.error(error_msg)
                    self.stats['errors'].append(error_msg)
        
        finally:
            if conn:
                conn.close()
    
    async def _migrate_cost_data(
        self,
        start_date: date,
        end_date: date,
        dry_run: bool = False
    ) -> None:
        """
        Migrate cost data from PostgreSQL to DynamoDB.
        
        Args:
            start_date: Start date for migration
            end_date: End date for migration
            dry_run: If True, validate but don't write to DynamoDB
        """
        logger.info(f"Migrating cost data from {start_date} to {end_date}")
        
        conn = None
        try:
            conn = psycopg2.connect(**self.postgres_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get cost data with organization and account information
            cursor.execute("""
                SELECT 
                    o.id as org_id,
                    o.org_name,
                    ma.aws_account_id,
                    ma.name as account_name,
                    ma.is_payer,
                    dfc.usage_date,
                    dfc.service_category,
                    dfc.aws_service,
                    dfc.charge_category,
                    dfc.cost
                FROM daily_focus_costs dfc
                JOIN member_accounts ma ON dfc.member_account_id = ma.id
                JOIN organizations o ON ma.organization_id = o.id
                WHERE o.status = 'ACTIVE'
                  AND dfc.usage_date >= %s
                  AND dfc.usage_date <= %s
                ORDER BY o.id, dfc.usage_date, ma.aws_account_id
            """, (start_date, end_date))
            
            # Process data in batches
            batch = []
            current_key = None
            current_record = None
            
            while True:
                rows = cursor.fetchmany(self.batch_size)
                if not rows:
                    # Process final batch
                    if current_record:
                        batch.append(current_record)
                    if batch:
                        await self._process_batch(batch, dry_run)
                    break
                
                for row in rows:
                    # Create a key for grouping (org_id + date)
                    key = (row['org_id'], row['usage_date'])
                    
                    if key != current_key:
                        # Save previous record if exists
                        if current_record:
                            batch.append(current_record)
                        
                        # Start new record
                        current_record = self._create_unified_record(row)
                        current_key = key
                        
                        # Process batch if it's full
                        if len(batch) >= self.batch_size:
                            await self._process_batch(batch, dry_run)
                            batch = []
                    
                    # Add service cost to current record
                    self._add_service_to_record(current_record, row)
        
        finally:
            if conn:
                conn.close()
    
    def _create_unified_record(self, row: Dict[str, Any]) -> UnifiedCostRecord:
        """Create a new UnifiedCostRecord from a database row."""
        client_id = f"org-{row['org_id']}"
        
        # Create collection metadata
        metadata = CollectionMetadata(
            collection_timestamp=datetime.utcnow(),
            collection_duration_seconds=0.0,
            api_calls_made=0,
            accounts_processed=1,
            services_discovered=1,
            data_freshness_hours=24.0,  # Assume daily data
            collection_method='migration',
            collector_version='1.0.0'
        )
        
        # Create data quality metrics
        data_quality = DataQuality(
            completeness_score=1.0,  # Assume complete for migrated data
            accuracy_score=0.95,     # High accuracy for existing data
            timeliness_score=0.8,    # Slightly lower for migrated data
            consistency_score=1.0,   # Consistent within migration
            confidence_level=DataQualityLevel.HIGH
        )
        
        return UnifiedCostRecord(
            client_id=client_id,
            provider=CloudProvider.AWS,  # All existing data is AWS
            date=row['usage_date'].strftime('%Y-%m-%d'),
            total_cost=Decimal('0'),
            currency=Currency.USD,
            collection_metadata=metadata,
            data_quality=data_quality
        )
    
    def _add_service_to_record(self, record: UnifiedCostRecord, row: Dict[str, Any]) -> None:
        """Add service cost data to a UnifiedCostRecord."""
        service_name = row['aws_service']
        cost = Decimal(str(row['cost']))
        
        # Map service to unified category
        category = self.transformer.map_aws_service_to_category(service_name)
        
        # Create or update service cost
        if service_name in record.services:
            record.services[service_name].cost += cost
        else:
            record.services[service_name] = ServiceCost(
                service_name=service_name,
                unified_category=category,
                cost=cost,
                currency=Currency.USD,
                provider_specific_data={
                    'charge_category': row['charge_category'],
                    'service_category': row['service_category']
                }
            )
        
        # Create or update account cost
        account_id = row['aws_account_id']
        if account_id not in record.accounts:
            record.accounts[account_id] = AccountCost(
                account_id=account_id,
                account_name=row['account_name'],
                cost=Decimal('0'),
                currency=Currency.USD
            )
        
        record.accounts[account_id].cost += cost
        record.accounts[account_id].add_service_cost(record.services[service_name])
        
        # Update total cost
        record.total_cost += cost
    
    async def _process_batch(self, batch: List[UnifiedCostRecord], dry_run: bool = False) -> None:
        """Process a batch of UnifiedCostRecords."""
        logger.info(f"Processing batch of {len(batch)} records")
        
        if dry_run:
            # Just validate the records
            for record in batch:
                validation_errors = self.validator.validate_unified_record(record)
                if validation_errors:
                    self.stats['warnings'].extend(validation_errors)
            return
        
        # Write to DynamoDB
        try:
            with self.cost_table.batch_writer() as batch_writer:
                for record in batch:
                    # Validate before writing
                    validation_errors = self.validator.validate_unified_record(record)
                    if validation_errors:
                        logger.warning(f"Record validation warnings: {validation_errors}")
                        self.stats['warnings'].extend(validation_errors)
                    
                    # Convert to DynamoDB item and write
                    item = record.to_dynamodb_item()
                    batch_writer.put_item(Item=item)
                    
                    self.stats['cost_records_migrated'] += 1
        
        except ClientError as e:
            error_msg = f"Failed to write batch to DynamoDB: {str(e)}"
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            raise
    
    async def migrate_incremental(
        self,
        since_date: date,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Perform incremental migration for new data since a specific date.
        
        Args:
            since_date: Only migrate data newer than this date
            dry_run: If True, validate but don't write to DynamoDB
            
        Returns:
            Migration statistics
        """
        logger.info(f"Starting incremental migration since {since_date}")
        
        return await self.migrate_all_data(
            start_date=since_date,
            end_date=date.today(),
            dry_run=dry_run
        )
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status and statistics."""
        return {
            'stats': self.stats,
            'is_running': self.stats['start_time'] is not None and self.stats['end_time'] is None,
            'progress': {
                'organizations': self.stats['organizations_migrated'],
                'accounts': self.stats['accounts_migrated'],
                'cost_records': self.stats['cost_records_migrated'],
                'errors': len(self.stats['errors']),
                'warnings': len(self.stats['warnings'])
            }
        }
    
    async def cleanup_migration(self) -> None:
        """Clean up resources after migration."""
        logger.info("Cleaning up migration resources")
        # Close any open connections, clear caches, etc.
        pass