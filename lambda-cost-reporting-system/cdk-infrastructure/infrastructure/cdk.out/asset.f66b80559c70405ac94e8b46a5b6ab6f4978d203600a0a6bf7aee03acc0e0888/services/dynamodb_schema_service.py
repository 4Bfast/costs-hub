"""
DynamoDB Schema Service

This module provides the DynamoDB table definitions and management for the multi-cloud
cost analytics platform. It includes both the main cost data table and the time series
table optimized for ML analysis.
"""

import boto3
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DynamoDBSchemaService:
    """Service for managing DynamoDB schema and table operations."""
    
    def __init__(self, region_name: str = 'us-east-1'):
        """
        Initialize the DynamoDB schema service.
        
        Args:
            region_name: AWS region for DynamoDB tables
        """
        self.dynamodb = boto3.client('dynamodb', region_name=region_name)
        self.region_name = region_name
        
        # Table configurations
        self.cost_analytics_table = 'cost-analytics-data'
        self.timeseries_table = 'cost-analytics-timeseries'
    
    def create_cost_analytics_table(self) -> Dict[str, Any]:
        """
        Create the main cost analytics data table with GSI indexes.
        
        Table structure:
        - PK: CLIENT#{client_id}
        - SK: COST#{provider}#{date}
        - GSI1: Provider-Date index for cross-client queries
        - GSI2: Client-Provider index for client-specific provider queries
        
        Returns:
            Table creation response
        """
        table_definition = {
            'TableName': self.cost_analytics_table,
            'KeySchema': [
                {
                    'AttributeName': 'PK',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'SK',
                    'KeyType': 'RANGE'
                }
            ],
            'AttributeDefinitions': [
                {
                    'AttributeName': 'PK',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'SK',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'GSI1PK',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'GSI1SK',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'GSI2PK',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'GSI2SK',
                    'AttributeType': 'S'
                }
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'GSI1-ProviderDate',
                    'KeySchema': [
                        {
                            'AttributeName': 'GSI1PK',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'GSI1SK',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'BillingMode': 'PAY_PER_REQUEST'
                },
                {
                    'IndexName': 'GSI2-ClientProvider',
                    'KeySchema': [
                        {
                            'AttributeName': 'GSI2PK',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'GSI2SK',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'BillingMode': 'PAY_PER_REQUEST'
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST',
            'StreamSpecification': {
                'StreamEnabled': True,
                'StreamViewType': 'NEW_AND_OLD_IMAGES'
            },
            'Tags': [
                {
                    'Key': 'Environment',
                    'Value': 'production'
                },
                {
                    'Key': 'Service',
                    'Value': 'multi-cloud-cost-analytics'
                },
                {
                    'Key': 'Purpose',
                    'Value': 'cost-data-storage'
                }
            ]
        }
        
        try:
            response = self.dynamodb.create_table(**table_definition)
            logger.info(f"Created cost analytics table: {self.cost_analytics_table}")
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                logger.info(f"Table {self.cost_analytics_table} already exists")
                return self.dynamodb.describe_table(TableName=self.cost_analytics_table)
            else:
                logger.error(f"Error creating cost analytics table: {e}")
                raise
    
    def create_timeseries_table(self) -> Dict[str, Any]:
        """
        Create the time series table optimized for ML and trend analysis.
        
        Table structure:
        - PK: TIMESERIES#{client_id}
        - SK: DAILY#{date}
        - GSI1: Date-based index for cross-client time series analysis
        
        Returns:
            Table creation response
        """
        table_definition = {
            'TableName': self.timeseries_table,
            'KeySchema': [
                {
                    'AttributeName': 'PK',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'SK',
                    'KeyType': 'RANGE'
                }
            ],
            'AttributeDefinitions': [
                {
                    'AttributeName': 'PK',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'SK',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'GSI1PK',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'GSI1SK',
                    'AttributeType': 'S'
                }
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'GSI1-DateIndex',
                    'KeySchema': [
                        {
                            'AttributeName': 'GSI1PK',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'GSI1SK',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'BillingMode': 'PAY_PER_REQUEST'
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST',
            'StreamSpecification': {
                'StreamEnabled': True,
                'StreamViewType': 'NEW_AND_OLD_IMAGES'
            },
            'Tags': [
                {
                    'Key': 'Environment',
                    'Value': 'production'
                },
                {
                    'Key': 'Service',
                    'Value': 'multi-cloud-cost-analytics'
                },
                {
                    'Key': 'Purpose',
                    'Value': 'timeseries-ml-data'
                }
            ]
        }
        
        try:
            response = self.dynamodb.create_table(**table_definition)
            logger.info(f"Created time series table: {self.timeseries_table}")
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                logger.info(f"Table {self.timeseries_table} already exists")
                return self.dynamodb.describe_table(TableName=self.timeseries_table)
            else:
                logger.error(f"Error creating time series table: {e}")
                raise
    
    def enable_ttl(self, table_name: str, ttl_attribute: str = 'ttl') -> Dict[str, Any]:
        """
        Enable TTL (Time To Live) on a DynamoDB table for automatic data lifecycle.
        
        Args:
            table_name: Name of the table to enable TTL on
            ttl_attribute: Name of the TTL attribute (default: 'ttl')
            
        Returns:
            TTL configuration response
        """
        try:
            response = self.dynamodb.update_time_to_live(
                TableName=table_name,
                TimeToLiveSpecification={
                    'Enabled': True,
                    'AttributeName': ttl_attribute
                }
            )
            logger.info(f"Enabled TTL on table {table_name} with attribute {ttl_attribute}")
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationException':
                logger.info(f"TTL already enabled on table {table_name}")
                return self.dynamodb.describe_time_to_live(TableName=table_name)
            else:
                logger.error(f"Error enabling TTL on table {table_name}: {e}")
                raise
    
    def create_all_tables(self) -> Dict[str, Any]:
        """
        Create all required tables for the multi-cloud cost analytics platform.
        
        Returns:
            Dictionary with creation results for all tables
        """
        results = {}
        
        # Create main cost analytics table
        results['cost_analytics'] = self.create_cost_analytics_table()
        
        # Create time series table
        results['timeseries'] = self.create_timeseries_table()
        
        # Wait for tables to be active before enabling TTL
        self.wait_for_table_active(self.cost_analytics_table)
        self.wait_for_table_active(self.timeseries_table)
        
        # Enable TTL on both tables
        results['cost_analytics_ttl'] = self.enable_ttl(self.cost_analytics_table)
        results['timeseries_ttl'] = self.enable_ttl(self.timeseries_table)
        
        logger.info("All DynamoDB tables created successfully")
        return results
    
    def wait_for_table_active(self, table_name: str, max_wait_time: int = 300) -> None:
        """
        Wait for a DynamoDB table to become active.
        
        Args:
            table_name: Name of the table to wait for
            max_wait_time: Maximum time to wait in seconds
        """
        waiter = self.dynamodb.get_waiter('table_exists')
        try:
            waiter.wait(
                TableName=table_name,
                WaiterConfig={
                    'Delay': 5,
                    'MaxAttempts': max_wait_time // 5
                }
            )
            logger.info(f"Table {table_name} is now active")
        except Exception as e:
            logger.error(f"Error waiting for table {table_name} to become active: {e}")
            raise
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a DynamoDB table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Table description
        """
        try:
            response = self.dynamodb.describe_table(TableName=table_name)
            return response['Table']
        except ClientError as e:
            logger.error(f"Error describing table {table_name}: {e}")
            raise
    
    def list_tables(self) -> List[str]:
        """
        List all DynamoDB tables in the region.
        
        Returns:
            List of table names
        """
        try:
            response = self.dynamodb.list_tables()
            return response['TableNames']
        except ClientError as e:
            logger.error(f"Error listing tables: {e}")
            raise
    
    def delete_table(self, table_name: str) -> Dict[str, Any]:
        """
        Delete a DynamoDB table (use with caution).
        
        Args:
            table_name: Name of the table to delete
            
        Returns:
            Deletion response
        """
        try:
            response = self.dynamodb.delete_table(TableName=table_name)
            logger.warning(f"Deleted table: {table_name}")
            return response
        except ClientError as e:
            logger.error(f"Error deleting table {table_name}: {e}")
            raise
    
    def get_table_metrics(self, table_name: str) -> Dict[str, Any]:
        """
        Get CloudWatch metrics for a DynamoDB table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary with table metrics
        """
        cloudwatch = boto3.client('cloudwatch', region_name=self.region_name)
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)
        
        metrics = {}
        
        # Define metrics to retrieve
        metric_names = [
            'ConsumedReadCapacityUnits',
            'ConsumedWriteCapacityUnits',
            'ItemCount',
            'TableSizeBytes'
        ]
        
        for metric_name in metric_names:
            try:
                response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/DynamoDB',
                    MetricName=metric_name,
                    Dimensions=[
                        {
                            'Name': 'TableName',
                            'Value': table_name
                        }
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,  # 1 hour
                    Statistics=['Sum', 'Average', 'Maximum']
                )
                metrics[metric_name] = response['Datapoints']
            except ClientError as e:
                logger.warning(f"Could not retrieve metric {metric_name} for table {table_name}: {e}")
                metrics[metric_name] = []
        
        return metrics
    
    def validate_schema(self) -> Dict[str, bool]:
        """
        Validate that all required tables exist and have correct configuration.
        
        Returns:
            Dictionary with validation results
        """
        validation_results = {}
        
        required_tables = [
            self.cost_analytics_table,
            self.timeseries_table
        ]
        
        for table_name in required_tables:
            try:
                table_info = self.get_table_info(table_name)
                
                # Check if table exists and is active
                is_valid = (
                    table_info['TableStatus'] == 'ACTIVE' and
                    len(table_info.get('GlobalSecondaryIndexes', [])) > 0
                )
                
                validation_results[table_name] = is_valid
                
                if is_valid:
                    logger.info(f"Table {table_name} validation passed")
                else:
                    logger.warning(f"Table {table_name} validation failed")
                    
            except ClientError:
                validation_results[table_name] = False
                logger.error(f"Table {table_name} does not exist")
        
        return validation_results


class DynamoDBQueryHelper:
    """Helper class for common DynamoDB query patterns."""
    
    def __init__(self, region_name: str = 'us-east-1'):
        """
        Initialize the query helper.
        
        Args:
            region_name: AWS region for DynamoDB tables
        """
        self.dynamodb = boto3.resource('dynamodb', region_name=region_name)
        self.cost_table = self.dynamodb.Table('cost-analytics-data')
        self.timeseries_table = self.dynamodb.Table('cost-analytics-timeseries')
    
    def get_client_costs_by_date_range(
        self, 
        client_id: str, 
        start_date: str, 
        end_date: str,
        provider: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query cost data for a client within a date range.
        
        Args:
            client_id: Client identifier
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            provider: Optional provider filter
            
        Returns:
            List of cost records
        """
        try:
            if provider:
                # Query specific provider
                response = self.cost_table.query(
                    KeyConditionExpression='PK = :pk AND SK BETWEEN :start_sk AND :end_sk',
                    ExpressionAttributeValues={
                        ':pk': f'CLIENT#{client_id}',
                        ':start_sk': f'COST#{provider}#{start_date}',
                        ':end_sk': f'COST#{provider}#{end_date}'
                    }
                )
            else:
                # Query all providers
                response = self.cost_table.query(
                    KeyConditionExpression='PK = :pk AND SK BETWEEN :start_sk AND :end_sk',
                    FilterExpression='SK BETWEEN :date_start AND :date_end',
                    ExpressionAttributeValues={
                        ':pk': f'CLIENT#{client_id}',
                        ':start_sk': f'COST#',
                        ':end_sk': f'COST#~',
                        ':date_start': start_date,
                        ':date_end': end_date
                    }
                )
            
            return response.get('Items', [])
            
        except ClientError as e:
            logger.error(f"Error querying client costs: {e}")
            raise
    
    def get_provider_costs_by_date(
        self, 
        provider: str, 
        date: str
    ) -> List[Dict[str, Any]]:
        """
        Query all client costs for a specific provider and date.
        
        Args:
            provider: Cloud provider (AWS, GCP, AZURE)
            date: Date in YYYY-MM-DD format
            
        Returns:
            List of cost records
        """
        try:
            response = self.cost_table.query(
                IndexName='GSI1-ProviderDate',
                KeyConditionExpression='GSI1PK = :gsi1pk AND GSI1SK = :gsi1sk',
                ExpressionAttributeValues={
                    ':gsi1pk': f'PROVIDER#{provider}',
                    ':gsi1sk': f'DATE#{date}'
                }
            )
            
            return response.get('Items', [])
            
        except ClientError as e:
            logger.error(f"Error querying provider costs: {e}")
            raise
    
    def get_client_timeseries(
        self, 
        client_id: str, 
        start_date: str, 
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Query time series data for a client within a date range.
        
        Args:
            client_id: Client identifier
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of time series records
        """
        try:
            response = self.timeseries_table.query(
                KeyConditionExpression='PK = :pk AND SK BETWEEN :start_sk AND :end_sk',
                ExpressionAttributeValues={
                    ':pk': f'TIMESERIES#{client_id}',
                    ':start_sk': f'DAILY#{start_date}',
                    ':end_sk': f'DAILY#{end_date}'
                }
            )
            
            return response.get('Items', [])
            
        except ClientError as e:
            logger.error(f"Error querying time series data: {e}")
            raise


# Example usage and testing functions
def create_sample_data():
    """Create sample data for testing the schema."""
    from ..models.multi_cloud_models import (
        UnifiedCostRecord, CloudProvider, Currency, ServiceCost, 
        ServiceCategory, DataQuality, DataQualityLevel, CollectionMetadata
    )
    from decimal import Decimal
    
    # Create sample cost record
    sample_record = UnifiedCostRecord(
        client_id='test-client-123',
        provider=CloudProvider.AWS,
        date='2024-10-30',
        total_cost=Decimal('1500.50'),
        currency=Currency.USD
    )
    
    # Add sample service costs
    ec2_cost = ServiceCost(
        service_name='EC2',
        unified_category=ServiceCategory.COMPUTE,
        cost=Decimal('800.00'),
        currency=Currency.USD,
        usage_metrics={'instance_hours': 720, 'instances': 5},
        provider_specific_data={'instance_types': ['t3.medium', 't3.large']}
    )
    
    s3_cost = ServiceCost(
        service_name='S3',
        unified_category=ServiceCategory.STORAGE,
        cost=Decimal('200.50'),
        currency=Currency.USD,
        usage_metrics={'storage_gb': 1000, 'requests': 50000},
        provider_specific_data={'storage_classes': ['STANDARD', 'IA']}
    )
    
    sample_record.add_service_cost(ec2_cost)
    sample_record.add_service_cost(s3_cost)
    
    # Add metadata
    sample_record.collection_metadata = CollectionMetadata(
        collection_timestamp=datetime.utcnow(),
        collection_duration_seconds=45.2,
        api_calls_made=5,
        accounts_processed=2,
        services_discovered=15,
        data_freshness_hours=2.5,
        collection_method='api',
        collector_version='1.0.0'
    )
    
    # Add data quality
    sample_record.data_quality = DataQuality(
        completeness_score=0.95,
        accuracy_score=0.98,
        timeliness_score=0.92,
        consistency_score=0.96,
        confidence_level=DataQualityLevel.HIGH
    )
    
    return sample_record


def test_schema_operations():
    """Test basic schema operations."""
    # Initialize schema service
    schema_service = DynamoDBSchemaService()
    
    # Create tables
    print("Creating DynamoDB tables...")
    results = schema_service.create_all_tables()
    print(f"Table creation results: {results}")
    
    # Validate schema
    print("Validating schema...")
    validation = schema_service.validate_schema()
    print(f"Schema validation: {validation}")
    
    # Create sample data
    sample_record = create_sample_data()
    
    # Convert to DynamoDB format
    dynamodb_item = sample_record.to_dynamodb_item()
    print(f"Sample DynamoDB item: {dynamodb_item}")
    
    return True


if __name__ == '__main__':
    # Run tests
    test_schema_operations()