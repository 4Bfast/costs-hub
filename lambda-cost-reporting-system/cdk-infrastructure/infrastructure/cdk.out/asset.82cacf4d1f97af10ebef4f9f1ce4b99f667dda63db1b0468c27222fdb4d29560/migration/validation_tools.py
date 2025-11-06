"""
Migration Validation Tools

This module provides comprehensive validation tools for data migration,
ensuring data integrity and accuracy during the migration process.
"""

import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
import boto3
from botocore.exceptions import ClientError
import psycopg2
from psycopg2.extras import RealDictCursor

from ..models.multi_cloud_models import (
    UnifiedCostRecord, validate_cost_record,
    CloudProvider, ServiceCategory
)


logger = logging.getLogger(__name__)


class MigrationValidator:
    """
    Comprehensive validation tools for data migration.
    """
    
    def __init__(self):
        """Initialize the migration validator."""
        self.validation_rules = {
            'cost_non_negative': True,
            'required_fields': True,
            'data_consistency': True,
            'total_cost_accuracy': True,
            'service_categorization': True
        }
    
    def validate_unified_record(self, record: UnifiedCostRecord) -> List[str]:
        """
        Validate a UnifiedCostRecord for migration accuracy.
        
        Args:
            record: The unified cost record to validate
            
        Returns:
            List of validation errors/warnings
        """
        errors = []
        
        # Use the built-in validation from the model
        model_errors = validate_cost_record(record)
        errors.extend(model_errors)
        
        # Additional migration-specific validations
        
        # Check for reasonable cost values
        if record.total_cost > Decimal('1000000'):  # $1M threshold
            errors.append(f"Unusually high total cost: ${record.total_cost}")
        
        # Check for empty service data
        if not record.services and record.total_cost > 0:
            errors.append("Record has cost but no service breakdown")
        
        # Check for empty account data
        if not record.accounts and record.total_cost > 0:
            errors.append("Record has cost but no account breakdown")
        
        # Validate service categories
        for service_name, service in record.services.items():
            if service.unified_category == ServiceCategory.OTHER:
                errors.append(f"Service '{service_name}' mapped to OTHER category")
        
        # Check data quality scores
        if record.data_quality:
            if record.data_quality.overall_score < 0.7:
                errors.append(f"Low data quality score: {record.data_quality.overall_score}")
        
        return errors
    
    async def validate_migration(
        self,
        postgres_config: Dict[str, str],
        dynamodb_config: Dict[str, str],
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Comprehensive validation of the entire migration.
        
        Args:
            postgres_config: PostgreSQL connection configuration
            dynamodb_config: DynamoDB configuration
            start_date: Start date for validation
            end_date: End date for validation
            
        Returns:
            Validation results and statistics
        """
        logger.info(f"Starting migration validation from {start_date} to {end_date}")
        
        validation_results = {
            'start_time': datetime.utcnow(),
            'end_time': None,
            'total_records_validated': 0,
            'errors': [],
            'warnings': [],
            'statistics': {
                'source_records': 0,
                'target_records': 0,
                'cost_variance': Decimal('0'),
                'missing_records': 0,
                'extra_records': 0
            },
            'validation_passed': False
        }
        
        try:
            # Step 1: Count source records
            source_stats = await self._get_source_statistics(postgres_config, start_date, end_date)
            validation_results['statistics']['source_records'] = source_stats['total_records']
            
            # Step 2: Count target records
            target_stats = await self._get_target_statistics(dynamodb_config, start_date, end_date)
            validation_results['statistics']['target_records'] = target_stats['total_records']
            
            # Step 3: Compare totals
            cost_comparison = await self._compare_cost_totals(
                postgres_config, dynamodb_config, start_date, end_date
            )
            validation_results['statistics']['cost_variance'] = cost_comparison['variance']
            
            # Step 4: Validate data integrity
            integrity_results = await self._validate_data_integrity(
                postgres_config, dynamodb_config, start_date, end_date
            )
            validation_results['errors'].extend(integrity_results['errors'])
            validation_results['warnings'].extend(integrity_results['warnings'])
            
            # Step 5: Sample validation
            sample_results = await self._validate_sample_records(
                postgres_config, dynamodb_config, start_date, end_date
            )
            validation_results['errors'].extend(sample_results['errors'])
            validation_results['warnings'].extend(sample_results['warnings'])
            
            # Determine if validation passed
            validation_results['validation_passed'] = (
                len(validation_results['errors']) == 0 and
                abs(validation_results['statistics']['cost_variance']) < Decimal('0.01')
            )
            
        except Exception as e:
            error_msg = f"Validation failed with error: {str(e)}"
            logger.error(error_msg)
            validation_results['errors'].append(error_msg)
        
        finally:
            validation_results['end_time'] = datetime.utcnow()
            duration = (validation_results['end_time'] - validation_results['start_time']).total_seconds()
            validation_results['duration_seconds'] = duration
        
        return validation_results
    
    async def _get_source_statistics(
        self,
        postgres_config: Dict[str, str],
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Get statistics from the source PostgreSQL database."""
        conn = None
        try:
            conn = psycopg2.connect(**postgres_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Count total records
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_records,
                    SUM(cost) as total_cost,
                    COUNT(DISTINCT member_account_id) as unique_accounts,
                    COUNT(DISTINCT aws_service) as unique_services,
                    MIN(usage_date) as min_date,
                    MAX(usage_date) as max_date
                FROM daily_focus_costs dfc
                JOIN member_accounts ma ON dfc.member_account_id = ma.id
                JOIN organizations o ON ma.organization_id = o.id
                WHERE o.status = 'ACTIVE'
                  AND dfc.usage_date >= %s
                  AND dfc.usage_date <= %s
            """, (start_date, end_date))
            
            result = cursor.fetchone()
            return dict(result) if result else {}
        
        finally:
            if conn:
                conn.close()
    
    async def _get_target_statistics(
        self,
        dynamodb_config: Dict[str, str],
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Get statistics from the target DynamoDB tables."""
        try:
            dynamodb = boto3.resource(
                'dynamodb',
                region_name=dynamodb_config.get('region', 'us-east-1'),
                aws_access_key_id=dynamodb_config.get('access_key_id'),
                aws_secret_access_key=dynamodb_config.get('secret_access_key')
            )
            
            table = dynamodb.Table(dynamodb_config.get('cost_table', 'cost-analytics-data'))
            
            # Scan table for records in date range (this is expensive but necessary for validation)
            total_records = 0
            total_cost = Decimal('0')
            unique_clients = set()
            
            # Use pagination to handle large datasets
            scan_kwargs = {
                'FilterExpression': boto3.dynamodb.conditions.Attr('date').between(
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
            }
            
            while True:
                response = table.scan(**scan_kwargs)
                
                for item in response['Items']:
                    total_records += 1
                    total_cost += Decimal(str(item.get('cost_data', {}).get('total_cost', 0)))
                    unique_clients.add(item.get('client_id'))
                
                if 'LastEvaluatedKey' not in response:
                    break
                scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
            
            return {
                'total_records': total_records,
                'total_cost': total_cost,
                'unique_clients': len(unique_clients)
            }
        
        except ClientError as e:
            logger.error(f"Failed to get target statistics: {str(e)}")
            return {'total_records': 0, 'total_cost': Decimal('0'), 'unique_clients': 0}
    
    async def _compare_cost_totals(
        self,
        postgres_config: Dict[str, str],
        dynamodb_config: Dict[str, str],
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Compare total costs between source and target."""
        source_stats = await self._get_source_statistics(postgres_config, start_date, end_date)
        target_stats = await self._get_target_statistics(dynamodb_config, start_date, end_date)
        
        source_total = Decimal(str(source_stats.get('total_cost', 0)))
        target_total = Decimal(str(target_stats.get('total_cost', 0)))
        
        variance = target_total - source_total
        variance_percentage = (variance / source_total * 100) if source_total > 0 else Decimal('0')
        
        return {
            'source_total': source_total,
            'target_total': target_total,
            'variance': variance,
            'variance_percentage': variance_percentage
        }
    
    async def _validate_data_integrity(
        self,
        postgres_config: Dict[str, str],
        dynamodb_config: Dict[str, str],
        start_date: date,
        end_date: date
    ) -> Dict[str, List[str]]:
        """Validate data integrity between source and target."""
        errors = []
        warnings = []
        
        try:
            # Check for missing organizations/clients
            source_orgs = await self._get_source_organizations(postgres_config)
            target_clients = await self._get_target_clients(dynamodb_config)
            
            if len(source_orgs) != len(target_clients):
                warnings.append(
                    f"Organization count mismatch: source={len(source_orgs)}, target={len(target_clients)}"
                )
            
            # Check for data consistency by date
            date_comparison = await self._compare_daily_totals(
                postgres_config, dynamodb_config, start_date, end_date
            )
            
            for date_str, comparison in date_comparison.items():
                variance = abs(comparison['variance'])
                if variance > Decimal('0.01'):
                    errors.append(
                        f"Cost variance on {date_str}: ${variance} "
                        f"(source: ${comparison['source']}, target: ${comparison['target']})"
                    )
        
        except Exception as e:
            errors.append(f"Data integrity validation failed: {str(e)}")
        
        return {'errors': errors, 'warnings': warnings}
    
    async def _validate_sample_records(
        self,
        postgres_config: Dict[str, str],
        dynamodb_config: Dict[str, str],
        start_date: date,
        end_date: date,
        sample_size: int = 100
    ) -> Dict[str, List[str]]:
        """Validate a sample of records for detailed accuracy."""
        errors = []
        warnings = []
        
        try:
            # Get sample records from source
            sample_records = await self._get_sample_source_records(
                postgres_config, start_date, end_date, sample_size
            )
            
            # Validate each sample record
            for record in sample_records:
                # Find corresponding target record
                target_record = await self._find_target_record(
                    dynamodb_config, record['org_id'], record['usage_date']
                )
                
                if not target_record:
                    errors.append(
                        f"Missing target record for org {record['org_id']} on {record['usage_date']}"
                    )
                    continue
                
                # Compare costs
                source_cost = Decimal(str(record['total_cost']))
                target_cost = Decimal(str(target_record.get('cost_data', {}).get('total_cost', 0)))
                
                if abs(source_cost - target_cost) > Decimal('0.01'):
                    errors.append(
                        f"Cost mismatch for org {record['org_id']} on {record['usage_date']}: "
                        f"source=${source_cost}, target=${target_cost}"
                    )
        
        except Exception as e:
            errors.append(f"Sample validation failed: {str(e)}")
        
        return {'errors': errors, 'warnings': warnings}
    
    async def _get_source_organizations(self, postgres_config: Dict[str, str]) -> List[Dict[str, Any]]:
        """Get list of organizations from source database."""
        conn = None
        try:
            conn = psycopg2.connect(**postgres_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT id, org_name, status
                FROM organizations
                WHERE status = 'ACTIVE'
            """)
            
            return [dict(row) for row in cursor.fetchall()]
        
        finally:
            if conn:
                conn.close()
    
    async def _get_target_clients(self, dynamodb_config: Dict[str, str]) -> List[str]:
        """Get list of client IDs from target database."""
        try:
            dynamodb = boto3.resource(
                'dynamodb',
                region_name=dynamodb_config.get('region', 'us-east-1'),
                aws_access_key_id=dynamodb_config.get('access_key_id'),
                aws_secret_access_key=dynamodb_config.get('secret_access_key')
            )
            
            table = dynamodb.Table(dynamodb_config.get('cost_table', 'cost-analytics-data'))
            
            # Scan for unique client IDs
            client_ids = set()
            scan_kwargs = {}
            
            while True:
                response = table.scan(**scan_kwargs)
                
                for item in response['Items']:
                    client_ids.add(item.get('client_id'))
                
                if 'LastEvaluatedKey' not in response:
                    break
                scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
            
            return list(client_ids)
        
        except ClientError as e:
            logger.error(f"Failed to get target clients: {str(e)}")
            return []
    
    async def _compare_daily_totals(
        self,
        postgres_config: Dict[str, str],
        dynamodb_config: Dict[str, str],
        start_date: date,
        end_date: date
    ) -> Dict[str, Dict[str, Decimal]]:
        """Compare daily cost totals between source and target."""
        # This is a simplified implementation
        # In practice, you'd want to implement detailed daily comparisons
        return {}
    
    async def _get_sample_source_records(
        self,
        postgres_config: Dict[str, str],
        start_date: date,
        end_date: date,
        sample_size: int
    ) -> List[Dict[str, Any]]:
        """Get sample records from source database."""
        conn = None
        try:
            conn = psycopg2.connect(**postgres_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT 
                    o.id as org_id,
                    dfc.usage_date,
                    SUM(dfc.cost) as total_cost
                FROM daily_focus_costs dfc
                JOIN member_accounts ma ON dfc.member_account_id = ma.id
                JOIN organizations o ON ma.organization_id = o.id
                WHERE o.status = 'ACTIVE'
                  AND dfc.usage_date >= %s
                  AND dfc.usage_date <= %s
                GROUP BY o.id, dfc.usage_date
                ORDER BY RANDOM()
                LIMIT %s
            """, (start_date, end_date, sample_size))
            
            return [dict(row) for row in cursor.fetchall()]
        
        finally:
            if conn:
                conn.close()
    
    async def _find_target_record(
        self,
        dynamodb_config: Dict[str, str],
        org_id: int,
        usage_date: date
    ) -> Optional[Dict[str, Any]]:
        """Find corresponding record in target database."""
        try:
            dynamodb = boto3.resource(
                'dynamodb',
                region_name=dynamodb_config.get('region', 'us-east-1'),
                aws_access_key_id=dynamodb_config.get('access_key_id'),
                aws_secret_access_key=dynamodb_config.get('secret_access_key')
            )
            
            table = dynamodb.Table(dynamodb_config.get('cost_table', 'cost-analytics-data'))
            
            # Convert org_id to client_id (this would need proper mapping)
            client_id = f"org-{org_id}"
            date_str = usage_date.strftime('%Y-%m-%d')
            
            response = table.get_item(
                Key={
                    'PK': f"CLIENT#{client_id}",
                    'SK': f"COST#AWS#{date_str}"
                }
            )
            
            return response.get('Item')
        
        except ClientError as e:
            logger.error(f"Failed to find target record: {str(e)}")
            return None
    
    def generate_validation_report(self, validation_results: Dict[str, Any]) -> str:
        """
        Generate a human-readable validation report.
        
        Args:
            validation_results: Results from validate_migration
            
        Returns:
            Formatted validation report
        """
        report = []
        report.append("=" * 60)
        report.append("DATA MIGRATION VALIDATION REPORT")
        report.append("=" * 60)
        report.append("")
        
        # Summary
        status = "PASSED" if validation_results['validation_passed'] else "FAILED"
        report.append(f"Overall Status: {status}")
        report.append(f"Validation Duration: {validation_results.get('duration_seconds', 0):.2f} seconds")
        report.append("")
        
        # Statistics
        stats = validation_results['statistics']
        report.append("STATISTICS:")
        report.append(f"  Source Records: {stats['source_records']:,}")
        report.append(f"  Target Records: {stats['target_records']:,}")
        report.append(f"  Cost Variance: ${stats['cost_variance']}")
        report.append("")
        
        # Errors
        if validation_results['errors']:
            report.append("ERRORS:")
            for error in validation_results['errors']:
                report.append(f"  - {error}")
            report.append("")
        
        # Warnings
        if validation_results['warnings']:
            report.append("WARNINGS:")
            for warning in validation_results['warnings']:
                report.append(f"  - {warning}")
            report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)